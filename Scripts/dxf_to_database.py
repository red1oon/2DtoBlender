#!/usr/bin/env python3
"""
DXF to Database Converter

Parses DXF files and populates database with same schema as IFC extraction.
This bypasses IFC generation and template matching - we go directly from 2D CAD to database.

Usage:
    python3 dxf_to_database.py [dxf_file] [output_db] [template_library_db]

Example:
    python3 dxf_to_database.py "Terminal1.dxf" Generated_Terminal1.db terminal_base_v1.0/template_library.db
"""

import sys
import sqlite3
import uuid
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

try:
    import ezdxf
except ImportError:
    print("❌ ERROR: ezdxf not installed")
    print("Install: pip install ezdxf")
    sys.exit(1)


@dataclass
class DXFEntity:
    """Represents a DXF entity to be converted to database entry."""
    entity_type: str          # INSERT, LINE, POLYLINE, etc.
    layer: str                # Layer name
    block_name: Optional[str] = None
    handle: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    attributes: Dict = field(default_factory=dict)

    # Derived fields (populated by template matching)
    discipline: Optional[str] = None
    ifc_class: Optional[str] = None
    element_name: Optional[str] = None


class TemplateLibrary:
    """Loads and manages templates for entity matching."""

    def __init__(self, template_db_path: str, layer_mappings_path: Optional[str] = None):
        """Load templates from database and optional layer mappings."""
        self.template_db_path = Path(template_db_path)
        self.templates = []
        self.layer_mapping = {}  # layer name → discipline
        self.layer_mappings_path = layer_mappings_path

        # Discipline code mappings (short → full name)
        self.discipline_map = {
            'FP': 'Fire_Protection',
            'ARC': 'Seating',  # Templates use 'Seating' for architecture
            'ACMV': 'ACMV',
            'SP': 'Plumbing',
            'CW': 'Chilled_Water',
            'LPG': 'LPG',
            'ELEC': 'Electrical',
            'STR': 'Structure',
            'REB': 'Reinforcement'
        }

        if not self.template_db_path.exists():
            raise FileNotFoundError(f"Template library not found: {template_db_path}")

        self._load_templates()

        # Load smart layer mappings if provided
        if layer_mappings_path and Path(layer_mappings_path).exists():
            self._load_layer_mappings(layer_mappings_path)
            print(f"✅ Loaded smart layer mappings from {Path(layer_mappings_path).name}")
        else:
            self._build_layer_mapping()  # Fallback to basic mapping

    def _load_templates(self):
        """Load all active templates from database."""
        conn = sqlite3.connect(str(self.template_db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT template_name, ifc_class, category
            FROM element_templates
            WHERE status = 'active'
        """)

        for row in cursor.fetchall():
            self.templates.append({
                'template_name': row[0],
                'ifc_class': row[1],
                'discipline': row[2]
            })

        conn.close()
        print(f"✅ Loaded {len(self.templates)} templates")

    def _load_layer_mappings(self, mappings_path: str):
        """Load smart layer mappings from JSON file."""
        with open(mappings_path, 'r') as f:
            data = json.load(f)

        # Extract layer → discipline mappings
        self.layer_mapping = {}
        for layer_name, mapping_info in data.get('mappings', {}).items():
            discipline = mapping_info.get('discipline')
            confidence = mapping_info.get('confidence', 0.0)

            # Only use high-confidence mappings (≥60%)
            if confidence >= 0.6:
                self.layer_mapping[layer_name] = discipline

        print(f"   Loaded {len(self.layer_mapping)} layer mappings (≥60% confidence)")

    def _build_layer_mapping(self):
        """Build mapping from layer prefixes to disciplines (fallback)."""
        # Common layer naming conventions
        self.layer_mapping = {
            'ARC': 'ARC',
            'FP': 'FP',
            'ELEC': 'ELEC',
            'ACMV': 'ACMV',
            'SP': 'SP',
            'STR': 'STR',
            'CW': 'CW',
            'LPG': 'LPG',
        }

    def match_entity(self, entity: DXFEntity) -> Optional[Dict]:
        """
        Match DXF entity to template.

        Strategy:
        1. Extract discipline from layer name (e.g., "FP-PIPE" → "FP")
        2. For INSERT entities, match block name to template
        3. For other entities, use entity type + layer pattern

        Returns:
            Template dict or None
        """
        # Extract discipline from layer
        discipline = self._extract_discipline_from_layer(entity.layer)

        if not discipline:
            return None

        # For INSERT entities, try to match block name
        if entity.entity_type == 'INSERT' and entity.block_name:
            template = self._match_by_block_name(entity.block_name, discipline)
            if template:
                return template

        # For other entities, match by entity type and layer
        template = self._match_by_entity_type(entity.entity_type, entity.layer, discipline)
        return template

    def _extract_discipline_from_layer(self, layer: str) -> Optional[str]:
        """Extract discipline code from layer name."""
        # Try exact layer name match first (from smart mappings)
        if layer in self.layer_mapping:
            return self.layer_mapping[layer]

        # Fallback: try prefix match (for basic mapping)
        layer_upper = layer.upper()
        for prefix, disc in self.layer_mapping.items():
            if layer_upper.startswith(prefix):
                return disc

        return None

    def _match_by_block_name(self, block_name: str, discipline: str) -> Optional[Dict]:
        """Match by block name fuzzy matching."""
        block_upper = block_name.upper()

        # Common block name patterns
        block_patterns = {
            'SPRINKLER': 'IfcFireSuppressionTerminal',
            'ALARM': 'IfcAlarm',
            'LIGHT': 'IfcLightFixture',
            'CHAIR': 'IfcFurniture',
            'TABLE': 'IfcFurniture',
            'SEAT': 'IfcFurniture',
            'DIFFUSER': 'IfcAirTerminal',
            'GRILLE': 'IfcAirTerminal',
        }

        for pattern, ifc_class in block_patterns.items():
            if pattern in block_upper:
                # Find matching template
                for template in self.templates:
                    if template['discipline'] == discipline and template['ifc_class'] == ifc_class:
                        return template

        return None

    def _match_by_entity_type(self, entity_type: str, layer: str, discipline: str) -> Optional[Dict]:
        """Match by entity type and layer pattern."""
        layer_upper = layer.upper()

        # Common layer patterns
        if 'PIPE' in layer_upper:
            ifc_class = 'IfcPipeSegment'
        elif 'DUCT' in layer_upper:
            ifc_class = 'IfcDuctSegment'
        elif 'WALL' in layer_upper:
            ifc_class = 'IfcWall'
        elif 'DOOR' in layer_upper:
            ifc_class = 'IfcDoor'
        elif 'WIN' in layer_upper:  # Match WIN, WINDOW, etc.
            ifc_class = 'IfcWindow'
        elif 'SLAB' in layer_upper or 'FLOOR' in layer_upper:
            ifc_class = 'IfcSlab'
        elif 'BEAM' in layer_upper:
            ifc_class = 'IfcBeam'
        elif 'COL' in layer_upper:  # Match COL, COLUMN, etc.
            ifc_class = 'IfcColumn'
        else:
            ifc_class = 'IfcBuildingElementProxy'  # Default

        # Map discipline short code to full name
        discipline_full = self.discipline_map.get(discipline, discipline)

        # Find matching template
        for template in self.templates:
            if template['discipline'] == discipline_full and template['ifc_class'] == ifc_class:
                return template

        return None


class DXFToDatabase:
    """Convert DXF file to database."""

    def __init__(self, dxf_path: str, output_db: str, template_library: TemplateLibrary):
        """Initialize converter."""
        self.dxf_path = Path(dxf_path)
        self.output_db = Path(output_db)
        self.template_library = template_library

        if not self.dxf_path.exists():
            raise FileNotFoundError(f"DXF file not found: {dxf_path}")

        self.entities = []
        self.statistics = defaultdict(int)

    def parse_dxf(self) -> List[DXFEntity]:
        """Parse DXF file and extract entities."""
        print(f"📂 Opening DXF: {self.dxf_path.name}")

        try:
            doc = ezdxf.readfile(str(self.dxf_path))
            print(f"✅ Opened DXF (version: {doc.dxfversion})")
        except Exception as e:
            print(f"❌ Error reading DXF: {e}")
            return []

        modelspace = doc.modelspace()
        print(f"📊 Extracting entities...")

        for entity in modelspace:
            dxf_entity = self._extract_entity(entity)
            if dxf_entity:
                self.entities.append(dxf_entity)
                self.statistics[dxf_entity.entity_type] += 1
                self.statistics[f"layer:{dxf_entity.layer}"] += 1

        print(f"✅ Extracted {len(self.entities)} entities")
        return self.entities

    def _extract_entity(self, entity) -> Optional[DXFEntity]:
        """Extract entity information."""
        entity_type = entity.dxftype()
        layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else 'UNKNOWN'
        handle = entity.dxf.handle if hasattr(entity.dxf, 'handle') else str(uuid.uuid4())[:8]

        # Extract position
        # NOTE: Force Z=0 initially since 2D DXF files have junk Z-values
        #       Intelligent Z-heights will be assigned later based on discipline/IFC class
        position = (0.0, 0.0, 0.0)

        # Try different position attributes depending on entity type
        if hasattr(entity.dxf, 'insert'):  # INSERT, BLOCK_REFERENCE
            position = (entity.dxf.insert.x, entity.dxf.insert.y, 0.0)
        elif hasattr(entity.dxf, 'start'):  # LINE, ARC
            position = (entity.dxf.start.x, entity.dxf.start.y, 0.0)
        elif hasattr(entity.dxf, 'center'):  # CIRCLE, ELLIPSE
            position = (entity.dxf.center.x, entity.dxf.center.y, 0.0)
        elif hasattr(entity, 'get_points'):  # LWPOLYLINE, POLYLINE, HATCH, SOLID
            try:
                points = list(entity.get_points())
                if points:
                    position = (points[0][0], points[0][1], 0.0)  # First point
            except:
                pass  # Keep default (0, 0, 0)
        elif hasattr(entity.dxf, 'defpoint'):  # DIMENSION, LEADER
            position = (entity.dxf.defpoint.x, entity.dxf.defpoint.y, 0.0)

        # Extract block name for INSERT entities
        block_name = None
        if entity_type == 'INSERT':
            block_name = entity.dxf.name if hasattr(entity.dxf, 'name') else None

        return DXFEntity(
            entity_type=entity_type,
            layer=layer,
            block_name=block_name,
            handle=handle,
            position=position
        )

    def match_templates(self):
        """Match entities to templates."""
        print(f"🎯 Matching {len(self.entities)} entities to templates...")

        matched = 0
        for entity in self.entities:
            template = self.template_library.match_entity(entity)
            if template:
                entity.discipline = template['discipline']
                entity.ifc_class = template['ifc_class']
                entity.element_name = template['template_name']
                matched += 1

        print(f"✅ Matched {matched}/{len(self.entities)} entities ({matched/len(self.entities)*100:.1f}%)")
        return matched

    def detect_elevation_views(self) -> bool:
        """
        Detect if DXF contains VALID elevation/section views (not just plan view).

        Heuristics:
        1. >10% of entities have non-zero Z-coordinates
        2. Z-range is reasonable (0-100m typical building height)
        3. Multiple distinct Z-levels (not just noise)

        Returns:
            True if valid elevation views detected, False if plan-only or junk data
        """
        z_values = []
        for entity in self.entities:
            z_values.append(entity.position[2])

        # Check if Z values are diverse (indicative of elevation views)
        non_zero_z = [z for z in z_values if abs(z) > 0.01]
        unique_z = len(set([round(z, 1) for z in z_values]))

        # Calculate Z-range
        if len(non_zero_z) > 0:
            z_min, z_max = min(z_values), max(z_values)
            z_range = z_max - z_min
        else:
            z_range = 0.0

        # Elevation data is valid if:
        # 1. >10% entities have Z != 0
        # 2. Z-range is reasonable (0.5m to 200m) - typical building heights
        # 3. Multiple distinct levels (>10)
        has_valid_elevations = (
            len(non_zero_z) > len(self.entities) * 0.1
            and 0.5 < z_range < 200
            and unique_z > 10
        )

        if has_valid_elevations:
            print(f"   ✅ Detected VALID elevation views: {len(non_zero_z)} entities with Z != 0")
            print(f"   Unique Z levels: {unique_z}, Range: {z_range:.1f}m")
        elif len(non_zero_z) > 0:
            print(f"   ❌ Elevation data detected but INVALID (range: {z_range:.1f}m)")
            print(f"   Falling back to rule-based assignment...")
        else:
            print(f"   Plan view only: All entities at Z=0")

        return has_valid_elevations

    def assign_intelligent_z_heights(self, building_type: str = "airport", use_elevation_data: bool = False):
        """
        Assign intelligent Z-heights to all entities based on discipline and IFC class.
        Phase 1 of Intelligent Anticipation Strategy: Rule-based vertical layering.

        This prevents 500+ false clashes by vertically separating disciplines before 3D generation.

        Args:
            building_type: Building type for ceiling height estimation (airport, office, hospital, etc.)
            use_elevation_data: If True, preserve existing Z-coordinates from elevation views
        """
        print(f"🎯 Assigning intelligent Z-heights for building type: {building_type}...")

        # Auto-detect elevation views if not specified
        if not use_elevation_data:
            use_elevation_data = self.detect_elevation_views()

        if use_elevation_data:
            print(f"   Strategy: Preserving Z-coordinates from elevation views")

            # Sanity check: Normalize Z-coordinates if they're in wrong units/datum
            # Building heights typically 0-100m, anything outside suggests datum shift
            z_values = [e.position[2] for e in self.entities if e.discipline and e.ifc_class]
            z_min, z_max = min(z_values), max(z_values)

            # If Z range suggests wrong datum (e.g., survey coordinates), normalize to floor=0
            if z_min < -1000 or z_max > 1000:
                print(f"   Warning: Z-coordinates out of range ({z_min:.1f} to {z_max:.1f})")
                print(f"   Normalizing to floor=0 datum...")

                # Shift all Z-coordinates so minimum is at 0
                for entity in self.entities:
                    if entity.discipline and entity.ifc_class:
                        x, y, z = entity.position
                        entity.position = (x, y, z - z_min)

                print(f"   Normalized range: 0.0 to {z_max - z_min:.1f}m")

            assigned = sum(1 for e in self.entities if e.discipline and e.ifc_class)
            print(f"✅ Preserved {assigned} elements with elevation Z-coordinates")
            return assigned
        else:
            print(f"   Strategy: Rule-based assignment (plan view only)")


        # Ceiling heights by building type (in meters)
        ceiling_heights = {
            "airport": 4.5,      # High ceilings for terminals
            "office": 3.5,       # Standard office
            "hospital": 3.8,     # Higher for medical equipment
            "industrial": 5.0,   # Very high for warehouse
            "residential": 2.7,  # Standard residential
        }

        ceiling = ceiling_heights.get(building_type, 3.5)

        # Discipline-based Z-height rules
        # Format: (discipline, ifc_class) → Z-height offset
        # Heights are measured from floor (0.0m)
        discipline_heights = {
            # Structure (lowest - embedded in floor/walls/ceiling)
            ("Structure", "IfcBeam"): 0.3,                    # Below ceiling
            ("Structure", "IfcColumn"): 0.0,                  # Floor level
            ("Structure", "IfcSlab"): 0.0,                    # Floor level
            ("Structure", "IfcWall"): 0.0,                    # Floor level
            ("Reinforcement", "IfcReinforcingBar"): 0.1,      # Embedded in concrete

            # ACMV (below ceiling, needs clearance)
            ("ACMV", "IfcDuctSegment"): ceiling - 0.6,        # 600mm below ceiling
            ("ACMV", "IfcAirTerminal"): ceiling - 0.4,        # Diffusers closer to ceiling

            # Electrical (higher up, less clearance needed)
            ("Electrical", "IfcCableCarrierSegment"): ceiling - 0.2,  # Cable trays high
            ("Electrical", "IfcLightFixture"): ceiling - 0.1,          # Lights at ceiling

            # Fire Protection (highest priority - cannot be obstructed)
            ("Fire_Protection", "IfcPipeSegment"): ceiling - 0.1,              # Sprinkler pipes highest
            ("Fire_Protection", "IfcFireSuppressionTerminal"): ceiling - 0.05, # Sprinkler heads at ceiling

            # Plumbing (varies by function)
            ("Plumbing", "IfcPipeSegment"): ceiling - 0.5,    # Below ACMV

            # Chilled Water (similar to plumbing)
            ("Chilled_Water", "IfcPipeSegment"): ceiling - 0.5,

            # Furniture/Seating (floor level)
            ("Seating", "IfcFurniture"): 0.0,                 # On floor

            # Default fallback for unknown combinations
            ("default", "default"): 1.5,                       # Mid-height as safe default
        }

        assigned = 0
        for entity in self.entities:
            if not entity.discipline or not entity.ifc_class:
                continue  # Skip unmatched entities

            # Lookup Z-height rule
            key = (entity.discipline, entity.ifc_class)
            z_height = discipline_heights.get(key)

            # Fallback to discipline-level defaults
            if z_height is None:
                discipline_defaults = {
                    "Structure": 0.0,
                    "ACMV": ceiling - 0.6,
                    "Electrical": ceiling - 0.2,
                    "Fire_Protection": ceiling - 0.1,
                    "Plumbing": ceiling - 0.5,
                    "Chilled_Water": ceiling - 0.5,
                    "Seating": 0.0,
                }
                z_height = discipline_defaults.get(entity.discipline, 1.5)

            # Add small random offset to prevent exact overlaps (0-50mm)
            import random
            z_offset = random.uniform(0.0, 0.05)

            # Update entity position with intelligent Z-height
            x, y, _ = entity.position  # Ignore original Z (always 0.0 from 2D)
            entity.position = (x, y, z_height + z_offset)
            assigned += 1

        print(f"✅ Assigned Z-heights to {assigned} elements")
        print(f"   Ceiling height: {ceiling}m")
        print(f"   Building type: {building_type}")
        return assigned

    def apply_vertical_separation(self, grid_size: float = 0.5):
        """
        Apply vertical separation to prevent elements from overlapping.
        Phase 1 of Intelligent Anticipation Strategy: Auto-nudge elements in same XY space.

        This prevents elements at same XY coordinates from clashing by auto-nudging them vertically.

        Args:
            grid_size: XY grid cell size in meters (0.5m = 500mm cells)
        """
        print(f"🎯 Applying vertical separation (grid size: {grid_size}m)...")

        # Minimum vertical clearance by discipline pair (in meters)
        # Format: (discipline1, discipline2) → minimum clearance
        clearance_rules = {
            ("ACMV", "Electrical"): 0.15,           # 150mm between duct and cable tray
            ("ACMV", "Fire_Protection"): 0.20,      # 200mm - fire protection priority
            ("ACMV", "Plumbing"): 0.15,             # 150mm clearance
            ("Electrical", "Fire_Protection"): 0.10, # 100mm clearance
            ("Plumbing", "Fire_Protection"): 0.15,  # 150mm clearance
            ("ACMV", "ACMV"): 0.20,                 # 200mm between ducts
            ("Electrical", "Electrical"): 0.10,     # 100mm between cable trays
        }

        # Default clearance for unknown pairs
        default_clearance = 0.10  # 100mm

        # Build spatial grid (XY plane divided into cells)
        from collections import defaultdict
        grid = defaultdict(list)  # (grid_x, grid_y) → [list of entities]

        for entity in self.entities:
            if not entity.discipline or not entity.ifc_class:
                continue

            x, y, z = entity.position
            grid_x = int(x / grid_size)
            grid_y = int(y / grid_size)
            grid[(grid_x, grid_y)].append(entity)

        # Process each grid cell
        adjustments = 0
        for cell_entities in grid.values():
            if len(cell_entities) <= 1:
                continue  # No overlap possible

            # Sort by current Z-height (lowest first)
            cell_entities.sort(key=lambda e: e.position[2])

            # Check each pair and apply vertical separation
            for i in range(len(cell_entities) - 1):
                lower = cell_entities[i]
                upper = cell_entities[i + 1]

                # Get required clearance
                key1 = (lower.discipline, upper.discipline)
                key2 = (upper.discipline, lower.discipline)
                required_clearance = clearance_rules.get(key1) or clearance_rules.get(key2) or default_clearance

                # Calculate actual vertical distance
                actual_distance = upper.position[2] - lower.position[2]

                # If too close, nudge upper element up
                if actual_distance < required_clearance:
                    nudge = required_clearance - actual_distance + 0.01  # Add 10mm safety margin
                    x, y, z = upper.position
                    upper.position = (x, y, z + nudge)
                    adjustments += 1

        print(f"✅ Applied {adjustments} vertical adjustments")
        return adjustments

    def predict_potential_clashes(self, tolerance: float = 0.05) -> Dict:
        """
        Predict potential clashes BEFORE 3D generation.
        Phase 1 of Intelligent Anticipation Strategy: Early warning system.

        This allows GUI to show warnings like:
        "⚠️ Predicted 12 potential clashes between ACMV and Electrical"

        Args:
            tolerance: Minimum clearance threshold in meters (0.05m = 50mm)

        Returns:
            Dictionary with clash statistics and warnings
        """
        print(f"🎯 Predicting potential clashes (tolerance: {tolerance}m)...")

        from collections import defaultdict
        clash_predictions = defaultdict(int)  # (discipline1, discipline2) → clash count
        high_risk_zones = []  # List of (x, y, clash_count) for hotspot visualization

        # Build spatial grid for fast proximity checks
        grid_size = 0.5  # 500mm grid cells
        grid = defaultdict(list)

        for entity in self.entities:
            if not entity.discipline or not entity.ifc_class:
                continue

            x, y, z = entity.position
            grid_x = int(x / grid_size)
            grid_y = int(y / grid_size)
            grid[(grid_x, grid_y)].append(entity)

        # Check each grid cell for potential clashes
        total_clashes = 0
        for (grid_x, grid_y), cell_entities in grid.items():
            if len(cell_entities) <= 1:
                continue

            cell_clashes = 0
            # Check all pairs in this cell
            for i in range(len(cell_entities)):
                for j in range(i + 1, len(cell_entities)):
                    e1, e2 = cell_entities[i], cell_entities[j]

                    # Calculate vertical distance
                    z_distance = abs(e1.position[2] - e2.position[2])

                    # Potential clash if too close
                    if z_distance < tolerance:
                        # Record clash between disciplines
                        disc_pair = tuple(sorted([e1.discipline, e2.discipline]))
                        clash_predictions[disc_pair] += 1
                        total_clashes += 1
                        cell_clashes += 1

            # Record high-risk zone if multiple clashes in same cell
            if cell_clashes >= 3:
                center_x = grid_x * grid_size + grid_size / 2
                center_y = grid_y * grid_size + grid_size / 2
                high_risk_zones.append((center_x, center_y, cell_clashes))

        # Generate summary
        summary = {
            "total_predicted_clashes": total_clashes,
            "clash_by_discipline": dict(clash_predictions),
            "high_risk_zones": high_risk_zones,
            "worst_pair": None,
            "warnings": []
        }

        # Find worst discipline pair
        if clash_predictions:
            worst_pair = max(clash_predictions.items(), key=lambda x: x[1])
            summary["worst_pair"] = {"disciplines": worst_pair[0], "count": worst_pair[1]}

        # Generate warnings for GUI
        if total_clashes == 0:
            summary["warnings"].append("✅ No predicted clashes - excellent coordination!")
        elif total_clashes < 10:
            summary["warnings"].append(f"⚠️  {total_clashes} potential clashes predicted (acceptable)")
        elif total_clashes < 50:
            summary["warnings"].append(f"⚠️  {total_clashes} potential clashes predicted (review recommended)")
        else:
            summary["warnings"].append(f"❌ {total_clashes} potential clashes predicted (coordination needed)")

        # Add discipline-specific warnings
        for (disc1, disc2), count in sorted(clash_predictions.items(), key=lambda x: x[1], reverse=True)[:3]:
            summary["warnings"].append(f"   • {disc1} ↔ {disc2}: {count} clashes")

        # High-risk zone warnings
        if high_risk_zones:
            summary["warnings"].append(f"   • {len(high_risk_zones)} high-risk zones detected")

        print(f"✅ Clash prediction complete:")
        print(f"   Total predicted clashes: {total_clashes}")
        for warning in summary["warnings"]:
            print(f"   {warning}")

        return summary

    def create_database(self):
        """Create output database with extraction schema."""
        print(f"💾 Creating database: {self.output_db.name}")

        # Delete if exists
        if self.output_db.exists():
            self.output_db.unlink()

        conn = sqlite3.connect(str(self.output_db))
        cursor = conn.cursor()

        # Create minimal schema (elements_meta table)
        cursor.execute("""
            CREATE TABLE elements_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guid TEXT UNIQUE NOT NULL,
                discipline TEXT NOT NULL,
                ifc_class TEXT NOT NULL,
                filepath TEXT,
                element_name TEXT,
                element_type TEXT,
                element_description TEXT,
                storey TEXT,
                material_name TEXT,
                material_rgba TEXT
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX idx_elements_meta_guid ON elements_meta(guid)")
        cursor.execute("CREATE INDEX idx_elements_meta_discipline ON elements_meta(discipline)")
        cursor.execute("CREATE INDEX idx_elements_meta_ifc_class ON elements_meta(ifc_class)")

        # Create element_transforms table (simplified)
        cursor.execute("""
            CREATE TABLE element_transforms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guid TEXT NOT NULL,
                center_x REAL,
                center_y REAL,
                center_z REAL
            )
        """)

        # Create global_offset table (required by Bonsai Federation)
        # Will be populated during coordinate normalization
        cursor.execute("""
            CREATE TABLE global_offset (
                offset_x REAL NOT NULL,
                offset_y REAL NOT NULL,
                offset_z REAL NOT NULL,
                extent_x REAL,
                extent_y REAL,
                extent_z REAL
            )
        """)

        # Create base_geometries table (stores unique geometry blobs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS base_geometries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guid TEXT UNIQUE,
                geometry_hash TEXT,
                vertices BLOB,
                faces BLOB,
                normals BLOB
            )
        """)

        # Create element_geometry VIEW (required by Bonsai Federation)
        # This is a view, not a table, matching the IFC extraction pattern
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS element_geometry AS
            SELECT
                guid,
                geometry_hash,
                vertices,
                faces,
                normals
            FROM base_geometries
        """)

        # Create virtual spatial index table (R-tree)
        # Required by Bonsai Federation for spatial queries
        # NOTE: Must use camelCase column names (minX not min_x) to match Bonsai expectations
        cursor.execute("""
            CREATE VIRTUAL TABLE elements_rtree USING rtree(
                id,
                minX, maxX,
                minY, maxY,
                minZ, maxZ
            )
        """)

        conn.commit()
        conn.close()
        print(f"✅ Database schema created (Bonsai Federation compatible)")

    def calculate_coordinate_offset(self):
        """
        Calculate coordinate offset to normalize to local origin.

        DXF files often use large coordinates (e.g., survey coordinates in mm).
        This calculates the bounding box center to shift everything to a local origin.

        Returns:
            Tuple[float, float, float]: Offset to subtract from coordinates (offset_x, offset_y, offset_z)
        """
        matched_entities = [e for e in self.entities if e.discipline and e.ifc_class]

        if not matched_entities:
            return (0.0, 0.0, 0.0)

        # Get bounding box
        x_coords = [e.position[0] for e in matched_entities]
        y_coords = [e.position[1] for e in matched_entities]
        z_coords = [e.position[2] for e in matched_entities]

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        min_z, max_z = min(z_coords), max(z_coords)

        # Use bounding box minimum as offset (shifts to origin)
        offset_x = min_x
        offset_y = min_y

        # DO NOT offset Z if intelligent heights were assigned (range 0-10m typical)
        # Only offset Z if values suggest wrong datum (e.g., >100m or negative)
        if min_z < -10 or max_z > 100:
            offset_z = min_z  # Shift to floor=0
            print(f"   Z-coordinates out of typical range ({min_z:.1f} to {max_z:.1f}m) - normalizing to floor=0")
        else:
            offset_z = 0.0  # Keep intelligent Z-heights as-is
            print(f"   Z-coordinates in valid range ({min_z:.2f} to {max_z:.2f}m) - preserving intelligent heights")

        # Check DXF units and apply appropriate scaling
        # DXF INSUNITS=4 means millimeters, so we need mm→m conversion
        unit_scale = 1.0
        if abs(max_x - min_x) > 10000 or abs(max_y - min_y) > 10000:
            print(f"   ⚠️  Large coordinates detected")
            print(f"   Range: X=[{min_x:.0f}, {max_x:.0f}], Y=[{min_y:.0f}, {max_y:.0f}]")
            unit_scale = 0.001  # Convert mm → m (DXF units are millimeters)
            print(f"   Applying mm→m conversion (scale: {unit_scale})")

        print(f"   Coordinate offset: X={offset_x:.2f}, Y={offset_y:.2f}, Z={offset_z:.2f}")
        print(f"   Unit scale: {unit_scale}")

        return (offset_x, offset_y, offset_z, unit_scale)

    def populate_database(self):
        """Populate database with matched entities."""
        print(f"📝 Populating database...")

        # Calculate coordinate normalization
        print(f"🎯 Calculating coordinate normalization...")
        offset_x, offset_y, offset_z, unit_scale = self.calculate_coordinate_offset()

        conn = sqlite3.connect(str(self.output_db))
        cursor = conn.cursor()

        # Store coordinate offset in database metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coordinate_metadata (
                id INTEGER PRIMARY KEY,
                offset_x REAL,
                offset_y REAL,
                offset_z REAL,
                unit_scale REAL,
                description TEXT
            )
        """)

        cursor.execute("""
            INSERT INTO coordinate_metadata (offset_x, offset_y, offset_z, unit_scale, description)
            VALUES (?, ?, ?, ?, ?)
        """, (offset_x, offset_y, offset_z, unit_scale,
              "Coordinate normalization: subtracted from original DXF coordinates and scaled"))

        inserted = 0
        for entity in self.entities:
            if not entity.discipline or not entity.ifc_class:
                continue  # Skip unmatched entities

            # Generate GUID
            guid = str(uuid.uuid4())

            # Insert into elements_meta
            cursor.execute("""
                INSERT INTO elements_meta
                (guid, discipline, ifc_class, filepath, element_name, element_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                guid,
                entity.discipline,
                entity.ifc_class,
                str(self.dxf_path.name),
                entity.element_name,
                entity.block_name or entity.entity_type
            ))

            # Normalize coordinates: subtract offset and apply unit scale
            # Note: unit_scale only applies to X/Y (for mm→m conversion)
            #       Z-coordinates are already in meters from intelligent assignment
            normalized_x = (entity.position[0] - offset_x) * unit_scale
            normalized_y = (entity.position[1] - offset_y) * unit_scale
            normalized_z = (entity.position[2] - offset_z)  # Z already in meters

            # Insert position
            cursor.execute("""
                INSERT INTO element_transforms
                (guid, center_x, center_y, center_z)
                VALUES (?, ?, ?, ?)
            """, (guid, normalized_x, normalized_y, normalized_z))

            inserted += 1

        # Populate global_offset table (required by Bonsai Federation)
        print(f"🌐 Populating global_offset table...")
        cursor.execute("""
            SELECT
                MIN(center_x), MAX(center_x),
                MIN(center_y), MAX(center_y),
                MIN(center_z), MAX(center_z)
            FROM element_transforms
        """)
        min_x, max_x, min_y, max_y, min_z, max_z = cursor.fetchone()

        # Store as negative offset (Bonsai convention: offset to ADD, not subtract)
        cursor.execute("""
            INSERT INTO global_offset (offset_x, offset_y, offset_z, extent_x, extent_y, extent_z)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            -min_x,  # Negative because Bonsai adds this offset
            -min_y,
            -min_z,
            max_x - min_x,
            max_y - min_y,
            max_z - min_z
        ))

        # Populate elements_rtree spatial index (required by Bonsai Federation)
        # NOTE: R-tree stores coordinates in METERS (same as element_transforms)
        #       Creating 1m placeholder bounding boxes around each center point
        print(f"🗺️  Building spatial index (R-tree)...")
        cursor.execute("""
            INSERT INTO elements_rtree (id, minX, maxX, minY, maxY, minZ, maxZ)
            SELECT
                t.id,
                t.center_x - 0.5, t.center_x + 0.5,
                t.center_y - 0.5, t.center_y + 0.5,
                t.center_z - 0.5, t.center_z + 0.5
            FROM element_transforms t
        """)

        print(f"   Indexed {inserted} elements in R-tree")

        conn.commit()
        conn.close()

        print(f"✅ Inserted {inserted} elements into database (coordinates normalized)")
        return inserted

    def generate_statistics(self):
        """Generate conversion statistics."""
        conn = sqlite3.connect(str(self.output_db))
        cursor = conn.cursor()

        print("\n" + "="*70)
        print("Conversion Statistics")
        print("="*70)

        cursor.execute("SELECT COUNT(*) FROM elements_meta")
        total = cursor.fetchone()[0]
        print(f"\nTotal elements: {total}")

        print(f"\nBy Discipline:")
        cursor.execute("""
            SELECT discipline, COUNT(*) as count
            FROM elements_meta
            GROUP BY discipline
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]:10s}: {row[1]:6d}")

        print(f"\nBy IFC Class (top 10):")
        cursor.execute("""
            SELECT ifc_class, COUNT(*) as count
            FROM elements_meta
            GROUP BY ifc_class
            ORDER BY count DESC
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]:40s}: {row[1]:6d}")

        conn.close()
        print("\n" + "="*70)


def main():
    """Main entry point."""

    if len(sys.argv) < 4:
        print("Usage: python3 dxf_to_database.py [dxf_file] [output_db] [template_library_db] [layer_mappings_json (optional)]")
        print("\nExample:")
        print('  python3 dxf_to_database.py "Terminal1.dxf" Generated_Terminal1.db template_library.db layer_mappings.json')
        sys.exit(1)

    dxf_file = sys.argv[1]
    output_db = sys.argv[2]
    template_db = sys.argv[3]
    layer_mappings = sys.argv[4] if len(sys.argv) > 4 else None

    try:
        # Load templates
        print("="*70)
        print("DXF to Database Converter")
        print("="*70 + "\n")

        template_library = TemplateLibrary(template_db, layer_mappings_path=layer_mappings)

        # Create converter
        converter = DXFToDatabase(dxf_file, output_db, template_library)

        # Step 1: Parse DXF
        entities = converter.parse_dxf()
        if not entities:
            print("❌ No entities extracted")
            sys.exit(1)

        # Step 2: Match templates
        matched = converter.match_templates()
        if matched == 0:
            print("⚠️  Warning: No entities matched to templates")

        # Step 2.5: Assign intelligent Z-heights (Intelligent Anticipation Strategy - Phase 1)
        converter.assign_intelligent_z_heights(building_type="airport")

        # Step 2.6: Apply vertical separation to prevent overlaps
        converter.apply_vertical_separation(grid_size=0.5)

        # Step 2.7: Predict potential clashes for early warning
        clash_summary = converter.predict_potential_clashes(tolerance=0.05)

        # Step 3: Create database
        converter.create_database()

        # Step 4: Populate database
        inserted = converter.populate_database()

        # Step 5: Show statistics
        converter.generate_statistics()

        print(f"\n✅ SUCCESS: Database created at {output_db}")
        print(f"   Total elements: {inserted}")
        print(f"   Match rate: {matched/len(entities)*100:.1f}%")
        print(f"\n📊 Clash Prediction Summary:")
        print(f"   Predicted clashes: {clash_summary['total_predicted_clashes']}")
        if clash_summary['worst_pair']:
            worst = clash_summary['worst_pair']
            print(f"   Worst pair: {worst['disciplines'][0]} ↔ {worst['disciplines'][1]} ({worst['count']} clashes)")

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
