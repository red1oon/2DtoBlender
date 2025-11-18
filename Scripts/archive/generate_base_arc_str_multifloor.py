#!/usr/bin/env python3
"""
Multi-Floor DXF to Database Converter (ARC + STR Only)

Config-driven workflow that generates complete building structure
 across all floors from building_config.json.

Features:
- Processes all floors defined in building_config.json
- Replicates ARC entities at each floor elevation
- Processes STR DXF per floor
- Generates floor and ceiling slabs at each level
- Comprehensive logging for self-debugging

Usage:
    python3 generate_base_arc_str_multifloor.py

Output:
    BASE_ARC_STR.db - Complete building structure (all floors)
"""

import sys
import sqlite3
import uuid
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict
import logging
from datetime import datetime

try:
    import ezdxf
except ImportError:
    print("❌ ERROR: ezdxf not installed")
    print("Install: pip install ezdxf")
    sys.exit(1)

# Import geometry generators
try:
    from geometry_generator import generate_element_geometry
    from enhanced_geometry_generator import generate_element_geometry_enhanced
except ImportError:
    # Try importing from Scripts directory
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from geometry_generator import generate_element_geometry
    from enhanced_geometry_generator import generate_element_geometry_enhanced

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Setup comprehensive logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    return logging.getLogger(__name__)

logger = setup_logging()


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class BuildingElement:
    """Represents a building element (wall, column, slab, etc.)"""
    guid: str
    discipline: str  # ARC, STR
    ifc_class: str   # IfcWall, IfcColumn, IfcSlab, etc.
    element_name: str
    element_type: str
    floor_id: str    # 1F, 2F, etc.

    # Position (normalized, in meters)
    x: float
    y: float
    z: float

    # Dimensions (in meters)
    length: float = 1.0
    width: float = 1.0
    height: float = 3.5

    # Source info
    source_file: str = ""
    source_layer: str = ""

    # Enhanced geometry (actual DXF entity shape data)
    entity_geom: Optional[Dict] = None


# ============================================================================
# MULTI-FLOOR PROCESSOR
# ============================================================================

class MultiFloorProcessor:
    """
    Processes multiple floors from config-driven workflow.

    Strategy:
    1. Load building_config.json
    2. For each floor:
       - Process STR DXF (columns, beams) at floor elevation
       - Replicate ARC entities at floor elevation
       - Generate floor slab
       - Generate ceiling slab
    3. Output: Complete BASE_ARC_STR.db
    """

    def __init__(self, config_path: str, source_dir: Path, output_db: Path):
        """Initialize processor."""
        self.config_path = Path(config_path)
        self.source_dir = Path(source_dir)
        self.output_db = Path(output_db)

        self.config = None
        self.elements = []  # List of BuildingElement
        self.arc_template_entities = []  # ARC entities to replicate across floors

        # Coordinate normalization params (calculated from all entities)
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.unit_scale = 0.001  # mm → m

        # Building bounds (for slab generation)
        self.building_bounds = None

        # Spatial filters (from config)
        self.spatial_filter = None  # Legacy single filter
        self.spatial_filter_arc = None  # Per-discipline ARC filter
        self.spatial_filter_str = None  # Per-discipline STR filter

        # Coordinate alignment offset (from config)
        self.arc_offset_x = 0.0
        self.arc_offset_y = 0.0

        # GPS alignment (applied after extraction)
        self.gps_alignment = None

    def load_config(self):
        """Load building_config.json."""
        logger.info("=" * 80)
        logger.info("LOADING CONFIGURATION")
        logger.info("=" * 80)

        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            self.config = json.load(f)

        logger.info(f"✅ Config loaded: {self.config_path.name}")
        logger.info(f"   Building: {self.config['building_info']['name']}")
        logger.info(f"   Total floors: {self.config['building_info']['total_floors']}")

        # List floors to process
        floor_levels = self.config['floor_levels']
        logger.info(f"   Floors defined: {len(floor_levels)}")

        for floor in floor_levels:
            level_id = floor['level_id']
            elevation = floor['elevation']
            active = floor.get('active', False)
            status = "✓ ACTIVE" if active else "○ inactive"
            logger.info(f"      {level_id}: {elevation:5.1f}m {status}")

        # Per-discipline spatial filters
        spatial_filter_config = self.config.get('spatial_filter', {})
        if spatial_filter_config.get('enabled', False):
            strategy = spatial_filter_config.get('strategy', 'manual')
            if strategy == 'per_discipline':
                self.spatial_filter_arc = spatial_filter_config.get('ARC', {})
                self.spatial_filter_str = spatial_filter_config.get('STR', {})
                logger.info(f"\n📍 Spatial Filter Strategy: Per-Discipline (native coords)")
                logger.info(f"   ARC: X=[{self.spatial_filter_arc.get('min_x')}, {self.spatial_filter_arc.get('max_x')}]")
                logger.info(f"        Y=[{self.spatial_filter_arc.get('min_y')}, {self.spatial_filter_arc.get('max_y')}]")
                logger.info(f"   STR: X=[{self.spatial_filter_str.get('min_x')}, {self.spatial_filter_str.get('max_x')}]")
                logger.info(f"        Y=[{self.spatial_filter_str.get('min_y')}, {self.spatial_filter_str.get('max_y')}]")
            else:
                # Legacy single filter (for backward compat)
                self.spatial_filter = {
                    'min_x': spatial_filter_config['min_x'],
                    'max_x': spatial_filter_config['max_x'],
                    'min_y': spatial_filter_config['min_y'],
                    'max_y': spatial_filter_config['max_y']
                }
                logger.info(f"\n📍 Spatial Filter Strategy: Manual (legacy)")
                logger.info(f"   X: [{self.spatial_filter['min_x']}, {self.spatial_filter['max_x']}]")
                logger.info(f"   Y: [{self.spatial_filter['min_y']}, {self.spatial_filter['max_y']}]")
        else:
            logger.info(f"\n⚠️  Spatial filter disabled - processing entire DXF")

        # Load coordinate alignment config
        alignment_config = self.config.get('coordinate_alignment', {})
        if alignment_config.get('enabled', False):
            strategy = alignment_config.get('strategy', 'manual')
            if strategy == 'grid_corner':
                logger.info(f"\n📐 Coordinate Alignment: Dynamic (grid corner)")
                logger.info(f"   Will auto-detect common grid labels and calculate offset")
            else:
                # Manual offset from config (try both naming conventions)
                self.arc_offset_x = alignment_config.get('offset_x_mm', alignment_config.get('arc_offset_x', 0.0))
                self.arc_offset_y = alignment_config.get('offset_y_mm', alignment_config.get('arc_offset_y', 0.0))
                logger.info(f"\n📐 Coordinate Alignment: Manual")
                logger.info(f"   ARC Offset: ({self.arc_offset_x:.0f}, {self.arc_offset_y:.0f}) mm")
        else:
            logger.info(f"\n⚠️  Coordinate alignment disabled")

        return self.config

    def calculate_grid_alignment(self):
        """
        Auto-calculate coordinate alignment by finding common structural grid labels.

        Strategy:
        1. Extract grid labels from ARC DXF (grid layer)
        2. Extract grid labels from STR DXF (axis label layer)
        3. Find common labels (e.g., "10", "11", "A", "B")
        4. Calculate offset to align them
        """
        logger.info("\n" + "=" * 80)
        logger.info("AUTO-CALCULATING COORDINATE ALIGNMENT (Grid Corner Method)")
        logger.info("=" * 80)

        # Get ARC DXF path
        arc_dxf_path = None
        for floor in self.config['floor_levels']:
            dxf_sources = floor.get('dxf_sources', {})
            arc_file = dxf_sources.get('ARC')
            if arc_file:
                project_root = self.config_path.parent
                arc_dxf_path = project_root / arc_file
                break

        if not arc_dxf_path or not arc_dxf_path.exists():
            logger.warning("⚠️  ARC DXF not found - cannot calculate alignment")
            return False

        # Get STR DXF path (use first available)
        str_dxf_path = None
        for floor_config in self.config['floor_levels']:
            str_path = self._get_str_dxf_path(floor_config)
            if str_path and str_path.exists():
                str_dxf_path = str_path
                break

        if not str_dxf_path:
            logger.warning("⚠️  STR DXF not found - cannot calculate alignment")
            return False

        logger.info(f"📂 ARC DXF: {arc_dxf_path.name}")
        logger.info(f"📂 STR DXF: {str_dxf_path.name}")

        # Extract grid labels from ARC
        arc_labels = self._extract_grid_labels(arc_dxf_path, layer_keyword='GRID')
        logger.info(f"   Found {len(arc_labels)} ARC grid labels")

        # Extract grid labels from STR
        str_labels = self._extract_grid_labels(str_dxf_path, layer_keyword='AXIS LABEL')
        logger.info(f"   Found {len(str_labels)} STR grid labels")

        # Find common labels
        common_labels = set(arc_labels.keys()) & set(str_labels.keys())
        if not common_labels:
            logger.warning("⚠️  No common grid labels found - cannot auto-align")
            return False

        logger.info(f"   Common grid labels: {len(common_labels)}")
        logger.info(f"   Sample: {sorted(list(common_labels))[:10]}")

        # Calculate offset from common labels
        offset_x_list = []
        offset_y_list = []

        for label in common_labels:
            arc_x, arc_y = arc_labels[label]
            str_x, str_y = str_labels[label]
            offset_x_list.append(str_x - arc_x)
            offset_y_list.append(str_y - arc_y)

        # Use median offset (more robust than average)
        offset_x_list.sort()
        offset_y_list.sort()
        median_idx = len(offset_x_list) // 2
        self.arc_offset_x = offset_x_list[median_idx]
        self.arc_offset_y = offset_y_list[median_idx]

        logger.info(f"\n✅ Coordinate Alignment Calculated:")
        logger.info(f"   ARC Offset: ({self.arc_offset_x:.0f}, {self.arc_offset_y:.0f}) mm")
        logger.info(f"   This offset will be added to all ARC coordinates")
        logger.info(f"   Reference: {len(common_labels)} common grid points")

        return True

    def _extract_grid_labels(self, dxf_path: Path, layer_keyword: str) -> Dict[str, Tuple[float, float]]:
        """Extract grid labels and their coordinates from DXF."""
        try:
            doc = ezdxf.readfile(str(dxf_path))
        except:
            return {}

        labels = {}

        for entity in doc.modelspace():
            if entity.dxftype() not in ['TEXT', 'MTEXT']:
                continue

            if hasattr(entity.dxf, 'layer'):
                layer = entity.dxf.layer.upper()
                if layer_keyword.upper() not in layer:
                    continue

                text = entity.dxf.text if hasattr(entity.dxf, 'text') else ''

                # Get position
                if hasattr(entity.dxf, 'insert'):
                    x, y = entity.dxf.insert.x, entity.dxf.insert.y
                elif hasattr(entity.dxf, 'start'):
                    x, y = entity.dxf.start.x, entity.dxf.start.y
                else:
                    continue

                # Clean text (grid labels are short)
                text = text.strip().upper()
                if text and len(text) <= 3:
                    labels[text] = (x, y)

        return labels

    def calculate_str_bounds(self):
        """
        Calculate spatial bounds from ALL STR DXF files (after alignment).
        This defines the main building extent and filters out auxiliary structures.
        """
        logger.info("\n" + "=" * 80)
        logger.info("CALCULATING STR BOUNDS (Main Building Extent)")
        logger.info("=" * 80)

        all_str_x = []
        all_str_y = []

        for floor_config in self.config['floor_levels']:
            str_dxf_path = self._get_str_dxf_path(floor_config)
            if not str_dxf_path or not str_dxf_path.exists():
                continue

            floor_id = floor_config['level_id']

            # Skip outlier floors (Basement/Roof often have auxiliary structures)
            # Use only main floors (1F-6F) for building extent
            if floor_id in ['GB', 'RF']:
                logger.info(f"   Skipping {floor_id} (outlier floor)")
                continue

            logger.info(f"   Processing {floor_id}: {str_dxf_path.name}")

            try:
                doc = ezdxf.readfile(str(str_dxf_path))
            except:
                continue

            for entity in doc.modelspace():
                layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else '0'
                layer_upper = layer.upper()

                # Only process STR entities (columns/beams)
                if not ('COLUMN' in layer_upper or 'COL' in layer_upper or 'BEAM' in layer_upper):
                    continue

                x, y = self._extract_xy_position(entity)
                if x is not None:
                    all_str_x.append(x)
                    all_str_y.append(y)

        if not all_str_x:
            logger.warning("⚠️  No STR entities found - cannot calculate bounds")
            return None

        # Get margin from config
        spatial_config = self.config.get('spatial_filter', {})
        margin_percent = spatial_config.get('margin_percent', 20) / 100.0

        min_x, max_x = min(all_str_x), max(all_str_x)
        min_y, max_y = min(all_str_y), max(all_str_y)

        x_margin = (max_x - min_x) * margin_percent
        y_margin = (max_y - min_y) * margin_percent

        # Filter in aligned space = STR bounds (no offset, STR is reference) + margin
        # ARC will be aligned to STR by adding arc_offset, then compared against this filter
        self.spatial_filter = {
            'min_x': min_x - x_margin,
            'max_x': max_x + x_margin,
            'min_y': min_y - y_margin,
            'max_y': max_y + y_margin
        }

        logger.info(f"✅ STR Bounds Calculated (with {margin_percent*100:.0f}% margin):")
        logger.info(f"   STR Raw: X=[{min_x:.0f}, {max_x:.0f}], Y=[{min_y:.0f}, {max_y:.0f}]")
        logger.info(f"   STR + Alignment: X=[{min_x + self.arc_offset_x:.0f}, {max_x + self.arc_offset_x:.0f}]")
        logger.info(f"   Filter (with margin): X=[{self.spatial_filter['min_x']:.0f}, {self.spatial_filter['max_x']:.0f}]")
        logger.info(f"   Filter (with margin): Y=[{self.spatial_filter['min_y']:.0f}, {self.spatial_filter['max_y']:.0f}]")
        logger.info(f"   Building size: {(max_x - min_x)/1000:.1f}km x {(max_y - min_y)/1000:.1f}km")
        logger.info(f"   This filter will extract only ARC within STR building extent")

        return self.spatial_filter

    def parse_arc_template(self):
        """
        Parse ARC DXF once to get template entities.
        These will be replicated at each floor elevation.
        """
        logger.info("\n" + "=" * 80)
        logger.info("PARSING ARC TEMPLATE (Single DXF for all floors)")
        logger.info("=" * 80)

        # Get ARC DXF path from first floor config
        # Note: Paths in config are relative to project root, not source_dir
        arc_dxf_path = None
        for floor in self.config['floor_levels']:
            dxf_sources = floor.get('dxf_sources', {})
            arc_file = dxf_sources.get('ARC')
            if arc_file:
                # Config paths are relative to project root
                project_root = self.config_path.parent
                arc_dxf_path = project_root / arc_file
                break

        if not arc_dxf_path or not arc_dxf_path.exists():
            logger.warning(f"⚠️  ARC DXF not found, skipping ARC entities")
            return []

        logger.info(f"File: {arc_dxf_path.name}")
        logger.info(f"Size: {arc_dxf_path.stat().st_size / (1024*1024):.1f} MB")

        try:
            doc = ezdxf.readfile(str(arc_dxf_path))
            logger.info(f"✅ Opened DXF (version: {doc.dxfversion}, units: {doc.units})")
        except Exception as e:
            logger.error(f"❌ Failed to open DXF: {e}")
            return []

        modelspace = doc.modelspace()
        total_entities = len(modelspace)
        logger.info(f"📊 Total entities in modelspace: {total_entities}")

        # Extract entities and classify
        arc_entities = []
        layer_counts = defaultdict(int)
        entity_type_counts = defaultdict(int)

        processed = 0
        for entity in modelspace:
            entity_type = entity.dxftype()
            layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else '0'

            # Skip annotation entities (not actual geometry)
            if entity_type in ('DIMENSION', 'LEADER', 'MLEADER', 'TEXT', 'MTEXT', 'ATTDEF', 'ATTRIB', 'HATCH', 'SPLINE', 'VIEWPORT'):
                continue

            # Extract position (X, Y only - Z will be set per floor)
            x, y = self._extract_xy_position(entity)
            if x is None:
                continue  # Skip entities without position

            # Apply ARC-specific spatial filter in native DXF coordinates
            if self.spatial_filter_arc:
                if not (self.spatial_filter_arc['min_x'] <= x <= self.spatial_filter_arc['max_x'] and
                        self.spatial_filter_arc['min_y'] <= y <= self.spatial_filter_arc['max_y']):
                    continue  # Entity outside Terminal 1 bounds - skip it
            elif self.spatial_filter:
                # Legacy filter with alignment (backward compat)
                aligned_x = x + self.arc_offset_x
                aligned_y = y + self.arc_offset_y
                if not (self.spatial_filter['min_x'] <= aligned_x <= self.spatial_filter['max_x'] and
                        self.spatial_filter['min_y'] <= aligned_y <= self.spatial_filter['max_y']):
                    continue  # Entity outside bounding box - skip it

            # Classify by layer
            ifc_class = self._classify_arc_entity(layer, entity_type)
            if not ifc_class:
                continue  # Skip non-ARC entities

            # Extract bounding box dimensions
            length, width, height = self._extract_bbox_dimensions(entity)

            # Extract actual entity geometry (Phase 1: CIRCLE radius, etc.)
            entity_geom = self._extract_entity_geometry(entity)

            arc_entities.append({
                'x': x,
                'y': y,
                'layer': layer,
                'entity_type': entity_type,
                'ifc_class': ifc_class,
                'length': length,
                'width': width,
                'height': height,
                'entity_geom': entity_geom  # Enhanced geometry data
            })

            layer_counts[layer] += 1
            entity_type_counts[entity_type] += 1

            processed += 1
            if processed % 5000 == 0:
                logger.info(f"   Progress: {processed}/{total_entities} ({processed/total_entities*100:.1f}%)")

        logger.info(f"✅ Extracted {len(arc_entities)} ARC entities ({len(arc_entities)/total_entities*100:.1f}%)")

        # DEBUG: Show coordinate samples
        if arc_entities:
            sample_coords = [(e['x'], e['y']) for e in arc_entities[:5]]
            logger.info(f"\n🔍 DEBUG: Sample ARC coordinates (first 5, DXF units):")
            for i, (x, y) in enumerate(sample_coords, 1):
                logger.info(f"   {i}. X={x:.1f}, Y={y:.1f}")

            # Show coordinate ranges
            all_x = [e['x'] for e in arc_entities]
            all_y = [e['y'] for e in arc_entities]
            logger.info(f"\n🔍 DEBUG: ARC coordinate range (DXF units):")
            logger.info(f"   X: [{min(all_x):.0f}, {max(all_x):.0f}] (range: {max(all_x)-min(all_x):.0f})")
            logger.info(f"   Y: [{min(all_y):.0f}, {max(all_y):.0f}] (range: {max(all_y)-min(all_y):.0f})")

        # Log entity breakdown
        logger.info(f"\n📊 ARC Entity Type Breakdown:")
        for etype, count in sorted(entity_type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"   {etype:20s}: {count:6d}")

        logger.info(f"\n📊 ARC Layer Breakdown (top 15):")
        for layer, count in sorted(layer_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
            logger.info(f"   {layer:30s}: {count:6d}")

        self.arc_template_entities = arc_entities
        return arc_entities

    def _extract_xy_position(self, entity) -> Tuple[Optional[float], Optional[float]]:
        """Extract X,Y position from DXF entity (Z ignored)."""
        try:
            if hasattr(entity.dxf, 'insert'):
                return (entity.dxf.insert.x, entity.dxf.insert.y)
            elif hasattr(entity.dxf, 'start'):
                return (entity.dxf.start.x, entity.dxf.start.y)
            elif hasattr(entity.dxf, 'center'):
                return (entity.dxf.center.x, entity.dxf.center.y)
            elif hasattr(entity, 'get_points'):
                points = list(entity.get_points())
                if points:
                    return (points[0][0], points[0][1])
        except:
            pass
        return (None, None)

    def _extract_bbox_dimensions(self, entity) -> Tuple[float, float, float]:
        """
        Extract bounding box dimensions from DXF entity.

        Returns:
            (length, width, height) in DXF units (typically mm)
            Defaults to (1000, 1000, 3500) if extraction fails (1m × 1m × 3.5m in mm)
        """
        try:
            # Try using ezdxf's bounding box method if available
            if hasattr(entity, 'bounding_box'):
                try:
                    bbox = entity.bounding_box()
                    if bbox:
                        length = abs(bbox.extmax.x - bbox.extmin.x)
                        width = abs(bbox.extmax.y - bbox.extmin.y)
                        height = abs(bbox.extmax.z - bbox.extmin.z) if hasattr(bbox.extmax, 'z') else 3500.0

                        # Sanity check (reasonable building element sizes: 50mm - 20000mm)
                        if 50 <= length <= 20000 and 50 <= width <= 20000:
                            return (length, width, max(height, 100.0))  # Min height 100mm
                except:
                    pass

            # Fallback: Manual bbox calculation based on entity type
            entity_type = entity.dxftype()

            # INSERT (block instances) - use block definition bbox if available
            if entity_type == 'INSERT':
                try:
                    # Get block definition
                    block_name = entity.dxf.name
                    doc = entity.doc
                    if doc and block_name in doc.blocks:
                        block = doc.blocks[block_name]

                        # Calculate bbox from block entities
                        xs, ys, zs = [], [], []
                        for bent in block:
                            if hasattr(bent, 'get_points'):
                                for pt in bent.get_points():
                                    xs.append(pt[0])
                                    ys.append(pt[1])
                                    if len(pt) > 2:
                                        zs.append(pt[2])

                        if xs and ys:
                            # Apply block scale
                            scale_x = getattr(entity.dxf, 'xscale', 1.0)
                            scale_y = getattr(entity.dxf, 'yscale', 1.0)
                            scale_z = getattr(entity.dxf, 'zscale', 1.0)

                            length = (max(xs) - min(xs)) * abs(scale_x)
                            width = (max(ys) - min(ys)) * abs(scale_y)
                            height = ((max(zs) - min(zs)) * abs(scale_z)) if zs else 3500.0

                            if 50 <= length <= 20000 and 50 <= width <= 20000:
                                return (length, width, max(height, 100.0))
                except:
                    pass

            # LWPOLYLINE, POLYLINE - calculate from vertices
            elif entity_type in ('LWPOLYLINE', 'POLYLINE'):
                try:
                    points = list(entity.get_points())
                    if points:
                        xs = [pt[0] for pt in points]
                        ys = [pt[1] for pt in points]

                        dx = max(xs) - min(xs)
                        dy = max(ys) - min(ys)

                        # For centerline representations (beams, columns), assume typical cross-section
                        # If one dimension is 0 or very small, it's a centerline
                        if dx < 50:  # Vertical or near-vertical element
                            length = max(dy, 100.0)  # Length is Y extent
                            width = 300.0  # Assume 300mm cross-section for beams/columns
                        elif dy < 50:  # Horizontal or near-horizontal element
                            length = max(dx, 100.0)  # Length is X extent
                            width = 300.0  # Assume 300mm cross-section
                        else:
                            # Both dimensions significant - actual bbox
                            length = dx
                            width = dy

                        # For polylines, assume typical wall/element height
                        height = 3500.0

                        if 50 <= length <= 20000 and 50 <= width <= 20000:
                            return (length, width, height)
                except:
                    pass

            # LINE - calculate length, assume typical width
            elif entity_type == 'LINE':
                try:
                    start = entity.dxf.start
                    end = entity.dxf.end

                    dx = abs(end.x - start.x)
                    dy = abs(end.y - start.y)

                    # For centerline representations
                    if dx < 50:  # Vertical line
                        length = max(dy, 100.0)
                        width = 200.0  # Assume wall/element thickness
                    elif dy < 50:  # Horizontal line
                        length = max(dx, 100.0)
                        width = 200.0
                    else:
                        # Diagonal or both dimensions significant
                        length = max(dx, dy)
                        width = min(dx, dy) if min(dx, dy) >= 50 else 200.0

                    height = 3500.0

                    if 50 <= length <= 20000:
                        return (length, max(width, 50.0), height)
                except:
                    pass

            # CIRCLE - use diameter
            elif entity_type == 'CIRCLE':
                try:
                    radius = entity.dxf.radius
                    diameter = radius * 2

                    if 50 <= diameter <= 2000:  # Column size range
                        return (diameter, diameter, 3500.0)
                except:
                    pass

            # ARC - use radius
            elif entity_type == 'ARC':
                try:
                    radius = entity.dxf.radius
                    diameter = radius * 2

                    if 50 <= diameter <= 2000:
                        return (diameter, diameter, 3500.0)
                except:
                    pass

        except Exception as e:
            # Silent fallback - logging would be too verbose
            pass

        # Default fallback (1m × 1m × 3.5m in mm)
        return (1000.0, 1000.0, 3500.0)

    def _extract_entity_geometry(self, entity) -> Optional[Dict[str, Any]]:
        """
        Extract actual geometry shape data from DXF entity.

        Returns shape in RELATIVE coordinates (mm), NOT absolute position.
        Key concept: DXF vertices define SHAPE, not position.

        Returns:
            Dict with entity_type and shape data, or None if not extractable
        """
        try:
            entity_type = entity.dxftype()

            # Phase 1: CIRCLE - Extract radius
            if entity_type == 'CIRCLE':
                radius = entity.dxf.radius  # In mm (DXF units)
                return {
                    'entity_type': 'CIRCLE',
                    'radius': radius  # Just a dimension, no coordinates
                }

            # Phase 2: LWPOLYLINE - Extract vertices relative to center (TODO: will implement in Phase 2)
            elif entity_type == 'LWPOLYLINE':
                points = list(entity.get_points())
                if not points or len(points) < 2:
                    return None

                # Calculate bounding box center (becomes local origin)
                xs = [pt[0] for pt in points]
                ys = [pt[1] for pt in points]
                center_x = (min(xs) + max(xs)) / 2.0
                center_y = (min(ys) + max(ys)) / 2.0

                # Make vertices RELATIVE to center (shape only, no position)
                vertices_2d_relative = []
                for pt in points:
                    rel_x = pt[0] - center_x
                    rel_y = pt[1] - center_y
                    vertices_2d_relative.append((rel_x, rel_y))

                return {
                    'entity_type': 'LWPOLYLINE',
                    'vertices_2d': vertices_2d_relative  # RELATIVE coordinates in mm
                }

            # Phase 3: LINE - Extract as relative to midpoint (TODO: will implement in Phase 3)
            elif entity_type == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                mid_x = (start.x + end.x) / 2.0
                mid_y = (start.y + end.y) / 2.0

                rel_start_x = start.x - mid_x
                rel_start_y = start.y - mid_y
                rel_end_x = end.x - mid_x
                rel_end_y = end.y - mid_y

                return {
                    'entity_type': 'LINE',
                    'start_point': (rel_start_x, rel_start_y),
                    'end_point': (rel_end_x, rel_end_y)
                }

        except Exception as e:
            # Silent fallback - entity doesn't support geometry extraction
            pass

        return None

    def _classify_arc_entity(self, layer: str, entity_type: str) -> Optional[str]:
        """Classify ARC entity to IFC class based on layer name."""
        layer_upper = layer.upper()

        # Wall patterns
        if any(pattern in layer_upper for pattern in ['WALL', 'DINDING', 'PARTITION']):
            return 'IfcWall'

        # Door patterns
        if any(pattern in layer_upper for pattern in ['DOOR', 'PINTU']):
            return 'IfcDoor'

        # Window patterns
        if any(pattern in layer_upper for pattern in ['WIN', 'WINDOW', 'TINGKAP']):
            return 'IfcWindow'

        # Roof/Dome patterns (CRITICAL for Terminal 1 dome extraction)
        if any(pattern in layer_upper for pattern in ['ROOF', 'ATAP', 'DOME', 'CANOPY']):
            return 'IfcPlate'  # Dome panels represented as plates (matches IFC)

        # Column patterns (for completeness)
        if any(pattern in layer_upper for pattern in ['COL', 'COLUMN', 'TIANG']):
            return 'IfcColumn'

        # Furniture (skip for now - focus on structure)
        # if any(pattern in layer_upper for pattern in ['CHAIR', 'TABLE', 'FURNITURE']):
        #     return 'IfcFurniture'

        # Only extract walls, doors, windows, roof/dome, columns for now
        return None

    def process_floor(self, floor_config: dict):
        """
        Process a single floor: STR DXF + ARC replication + slabs.

        Args:
            floor_config: Floor configuration dict from building_config.json
        """
        floor_id = floor_config['level_id']
        elevation = floor_config['elevation']
        slab_thickness = floor_config.get('slab_thickness', 0.3)

        logger.info("\n" + "=" * 80)
        logger.info(f"PROCESSING FLOOR: {floor_id} @ {elevation:.1f}m")
        logger.info("=" * 80)

        floor_elements = []

        # Step 1: Process STR DXF for this floor
        str_dxf_path = self._get_str_dxf_path(floor_config)
        if str_dxf_path and str_dxf_path.exists():
            logger.info(f"📂 STR DXF: {str_dxf_path.name}")
            str_elements = self._process_str_dxf(str_dxf_path, floor_id, elevation)
            floor_elements.extend(str_elements)
            logger.info(f"   ✅ Extracted {len(str_elements)} STR elements")
        else:
            logger.info(f"   ⚠️  No STR DXF for this floor")

        # Step 2: Replicate ARC entities at this floor elevation
        logger.info(f"📐 Replicating ARC entities at elevation {elevation:.1f}m")
        arc_elements = self._replicate_arc_entities(floor_id, elevation)
        floor_elements.extend(arc_elements)
        logger.info(f"   ✅ Replicated {len(arc_elements)} ARC elements")

        # Step 3: Generate floor slab
        logger.info(f"🟦 Generating floor slab (thickness: {slab_thickness}m)")
        floor_slab = self._generate_floor_slab(floor_id, elevation, slab_thickness)
        if floor_slab:
            floor_elements.append(floor_slab)
            logger.info(f"   ✅ Floor slab created")

        # Step 4: Generate ceiling slab (at top of floor)
        floor_height = self.config['building_info'].get('floor_to_floor_height', 4.0)
        ceiling_elevation = elevation + floor_height
        logger.info(f"🟦 Generating ceiling slab at {ceiling_elevation:.1f}m")
        ceiling_slab = self._generate_ceiling_slab(floor_id, ceiling_elevation, slab_thickness)
        if ceiling_slab:
            floor_elements.append(ceiling_slab)
            logger.info(f"   ✅ Ceiling slab created")

        # Summary
        logger.info(f"\n📊 Floor {floor_id} Summary:")
        logger.info(f"   Total elements: {len(floor_elements)}")

        # Count by discipline
        disc_counts = defaultdict(int)
        for elem in floor_elements:
            disc_counts[elem.discipline] += 1
        for disc, count in sorted(disc_counts.items()):
            logger.info(f"      {disc}: {count}")

        # DEBUG: Show coordinate samples after alignment
        if floor_elements:
            arc_samples = [e for e in floor_elements if e.discipline == 'ARC'][:3]
            str_samples = [e for e in floor_elements if e.discipline == 'STR'][:3]

            if arc_samples:
                logger.info(f"\n🔍 DEBUG: ARC coordinates after alignment (DXF units):")
                for i, elem in enumerate(arc_samples, 1):
                    logger.info(f"   {i}. X={elem.x:.1f}, Y={elem.y:.1f}, Z={elem.z:.1f}")

            if str_samples:
                logger.info(f"🔍 DEBUG: STR coordinates (DXF units):")
                for i, elem in enumerate(str_samples, 1):
                    logger.info(f"   {i}. X={elem.x:.1f}, Y={elem.y:.1f}, Z={elem.z:.1f}")

        self.elements.extend(floor_elements)
        return floor_elements

    def _get_str_dxf_path(self, floor_config: dict) -> Optional[Path]:
        """Get STR DXF path for floor."""
        dxf_sources = floor_config.get('dxf_sources', {})
        str_file = dxf_sources.get('STR')
        if str_file:
            # Config paths are relative to project root
            project_root = self.config_path.parent
            return project_root / str_file
        return None

    def _process_str_dxf(self, dxf_path: Path, floor_id: str, elevation: float) -> List[BuildingElement]:
        """Process STR DXF and extract columns/beams."""
        try:
            doc = ezdxf.readfile(str(dxf_path))
        except Exception as e:
            logger.error(f"   ❌ Failed to open STR DXF: {e}")
            return []

        modelspace = doc.modelspace()
        str_elements = []

        for entity in modelspace:
            layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else '0'
            layer_upper = layer.upper()

            # Classify as column or beam
            ifc_class = None
            if 'COLUMN' in layer_upper or 'COL' in layer_upper:
                ifc_class = 'IfcColumn'
            elif 'BEAM' in layer_upper:
                ifc_class = 'IfcBeam'

            if not ifc_class:
                continue

            # Extract position
            x, y = self._extract_xy_position(entity)
            if x is None:
                continue

            # Apply STR-specific spatial filter in native DXF coordinates
            if self.spatial_filter_str:
                if not (self.spatial_filter_str['min_x'] <= x <= self.spatial_filter_str['max_x'] and
                        self.spatial_filter_str['min_y'] <= y <= self.spatial_filter_str['max_y']):
                    continue  # STR entity outside Terminal 1 bounds - skip it
            elif self.spatial_filter:
                # Legacy single filter (backward compat)
                if not (self.spatial_filter['min_x'] <= x <= self.spatial_filter['max_x'] and
                        self.spatial_filter['min_y'] <= y <= self.spatial_filter['max_y']):
                    continue  # STR entity outside Terminal 1 bounds - skip it

            # Extract bounding box dimensions
            length, width, height = self._extract_bbox_dimensions(entity)

            # Extract actual entity geometry (Phase 1: CIRCLE radius, etc.)
            entity_geom = self._extract_entity_geometry(entity)

            # Create element
            elem = BuildingElement(
                guid=str(uuid.uuid4()),
                discipline='STR',
                ifc_class=ifc_class,
                element_name=f"{ifc_class}_{floor_id}",
                element_type=entity.dxftype(),
                floor_id=floor_id,
                x=x,
                y=y,
                z=elevation,  # Floor elevation
                length=length,
                width=width,
                height=height,
                source_file=dxf_path.name,
                source_layer=layer,
                entity_geom=entity_geom  # Enhanced geometry data
            )

            str_elements.append(elem)

        return str_elements

    def _replicate_arc_entities(self, floor_id: str, elevation: float) -> List[BuildingElement]:
        """Replicate ARC template entities at this floor elevation."""
        arc_elements = []

        for template in self.arc_template_entities:
            # Apply coordinate alignment offset to ARC coordinates
            aligned_x = template['x'] + self.arc_offset_x
            aligned_y = template['y'] + self.arc_offset_y

            elem = BuildingElement(
                guid=str(uuid.uuid4()),
                discipline='ARC',
                ifc_class=template['ifc_class'],
                element_name=f"{template['ifc_class']}_{floor_id}",
                element_type=template['entity_type'],
                floor_id=floor_id,
                x=aligned_x,  # Aligned with STR coordinate system
                y=aligned_y,  # Aligned with STR coordinate system
                z=elevation,  # Floor elevation
                length=template['length'],
                width=template['width'],
                height=template['height'],
                source_layer=template['layer'],
                entity_geom=template.get('entity_geom')  # Enhanced geometry data
            )
            arc_elements.append(elem)

        return arc_elements

    def _generate_floor_slab(self, floor_id: str, elevation: float, thickness: float) -> Optional[BuildingElement]:
        """Generate floor slab element."""
        if not self.building_bounds:
            self._calculate_building_bounds()

        if not self.building_bounds:
            return None

        elem = BuildingElement(
            guid=str(uuid.uuid4()),
            discipline='ARC',
            ifc_class='IfcSlab',
            element_name=f"FloorSlab_{floor_id}",
            element_type='GENERATED_SLAB',
            floor_id=floor_id,
            x=(self.building_bounds['min_x'] + self.building_bounds['max_x']) / 2,
            y=(self.building_bounds['min_y'] + self.building_bounds['max_y']) / 2,
            z=elevation,
            length=self.building_bounds['max_x'] - self.building_bounds['min_x'],
            width=self.building_bounds['max_y'] - self.building_bounds['min_y'],
            height=thickness * 1000.0  # Convert meters to mm (config has thickness in meters)
        )

        return elem

    def _generate_ceiling_slab(self, floor_id: str, elevation: float, thickness: float) -> Optional[BuildingElement]:
        """Generate ceiling slab element."""
        if not self.building_bounds:
            self._calculate_building_bounds()

        if not self.building_bounds:
            return None

        elem = BuildingElement(
            guid=str(uuid.uuid4()),
            discipline='ARC',
            ifc_class='IfcSlab',
            element_name=f"CeilingSlab_{floor_id}",
            element_type='GENERATED_SLAB',
            floor_id=floor_id,
            x=(self.building_bounds['min_x'] + self.building_bounds['max_x']) / 2,
            y=(self.building_bounds['min_y'] + self.building_bounds['max_y']) / 2,
            z=elevation,
            length=self.building_bounds['max_x'] - self.building_bounds['min_x'],
            width=self.building_bounds['max_y'] - self.building_bounds['min_y'],
            height=thickness * 1000.0  # Convert meters to mm (config has thickness in meters)
        )

        return elem

    def _calculate_building_bounds(self):
        """Calculate building bounds from all entities (with alignment applied)."""
        if not self.arc_template_entities:
            return

        # Apply alignment offset to get actual aligned coordinates
        x_coords = [e['x'] + self.arc_offset_x for e in self.arc_template_entities]
        y_coords = [e['y'] + self.arc_offset_y for e in self.arc_template_entities]

        self.building_bounds = {
            'min_x': min(x_coords),
            'max_x': max(x_coords),
            'min_y': min(y_coords),
            'max_y': max(y_coords)
        }

        logger.info(f"\n📐 Building Bounds (XY plane, aligned, DXF units):")
        logger.info(f"   X: [{self.building_bounds['min_x']:.1f}, {self.building_bounds['max_x']:.1f}]")
        logger.info(f"   Y: [{self.building_bounds['min_y']:.1f}, {self.building_bounds['max_y']:.1f}]")

    def calculate_normalization(self):
        """Calculate coordinate normalization parameters."""
        logger.info("\n" + "=" * 80)
        logger.info("COORDINATE NORMALIZATION")
        logger.info("=" * 80)

        if not self.elements:
            logger.warning("⚠️  No elements to normalize")
            return

        # Get all X,Y coordinates
        x_coords = [e.x for e in self.elements]
        y_coords = [e.y for e in self.elements]

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        # Check if coordinates are in mm (large numbers)
        coord_range_x = abs(max_x - min_x)
        coord_range_y = abs(max_y - min_y)

        if coord_range_x > 10000 or coord_range_y > 10000:
            logger.info(f"📊 Large coordinates detected (likely millimeters)")
            logger.info(f"   X range: {coord_range_x:.0f}")
            logger.info(f"   Y range: {coord_range_y:.0f}")
            self.unit_scale = 0.001  # mm → m
            logger.info(f"   ✅ Applying mm→m conversion (scale: {self.unit_scale})")
        else:
            logger.info(f"📊 Coordinates already in reasonable range (meters)")
            logger.info(f"   X range: {coord_range_x:.2f}m")
            logger.info(f"   Y range: {coord_range_y:.2f}m")
            self.unit_scale = 1.0

        # Use minimum as offset (shift to origin)
        self.offset_x = min_x
        self.offset_y = min_y

        logger.info(f"📍 Normalization parameters:")
        logger.info(f"   Offset X: {self.offset_x:.2f}")
        logger.info(f"   Offset Y: {self.offset_y:.2f}")
        logger.info(f"   Unit scale: {self.unit_scale}")

        # DEBUG: Show what normalized coordinates will look like
        if self.elements:
            sample = self.elements[0]
            norm_x = (sample.x - self.offset_x) * self.unit_scale
            norm_y = (sample.y - self.offset_y) * self.unit_scale
            norm_z = sample.z
            logger.info(f"\n🔍 DEBUG: Sample normalization:")
            logger.info(f"   Original: X={sample.x:.2f}, Y={sample.y:.2f}, Z={sample.z:.2f}")
            logger.info(f"   After offset: X={sample.x - self.offset_x:.2f}, Y={sample.y - self.offset_y:.2f}")
            logger.info(f"   After scale: X={norm_x:.2f}m, Y={norm_y:.2f}m, Z={norm_z:.2f}m")

    def create_database(self):
        """Create output database with Bonsai-compatible schema."""
        logger.info("\n" + "=" * 80)
        logger.info(f"CREATING DATABASE: {self.output_db.name}")
        logger.info("=" * 80)

        # Delete if exists
        if self.output_db.exists():
            self.output_db.unlink()
            logger.info("   🗑️  Deleted existing database")

        conn = sqlite3.connect(str(self.output_db))
        cursor = conn.cursor()

        # Create elements_meta table
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
                storey TEXT
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX idx_elements_meta_guid ON elements_meta(guid)")
        cursor.execute("CREATE INDEX idx_elements_meta_discipline ON elements_meta(discipline)")

        # Create element_transforms table
        cursor.execute("""
            CREATE TABLE element_transforms (
                guid TEXT PRIMARY KEY,
                center_x REAL NOT NULL,
                center_y REAL NOT NULL,
                center_z REAL NOT NULL,
                bbox_length REAL,
                bbox_width REAL,
                bbox_height REAL,
                transform_source TEXT DEFAULT 'dxf_multifloor',
                FOREIGN KEY (guid) REFERENCES elements_meta(guid)
            )
        """)

        # Create global_offset table
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

        # Create base_geometries table
        cursor.execute("""
            CREATE TABLE base_geometries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guid TEXT UNIQUE,
                geometry_hash TEXT,
                vertices BLOB,
                faces BLOB,
                normals BLOB
            )
        """)

        # Create element_geometry view
        cursor.execute("""
            CREATE VIEW element_geometry AS
            SELECT guid, geometry_hash, vertices, faces, normals
            FROM base_geometries
        """)

        # Create R-tree spatial index
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

        logger.info("   ✅ Database schema created (Bonsai-compatible)")

    def calculate_gps_alignment(self):
        """Calculate GPS alignment offsets for each discipline."""
        logger.info("\n" + "=" * 80)
        logger.info("CALCULATING GPS ALIGNMENT")
        logger.info("=" * 80)

        gps_config = self.config.get('gps_alignment', {})
        if not gps_config.get('enabled', False):
            logger.info("⚠️  GPS alignment disabled")
            return

        target_gps = gps_config.get('target_gps_bounds', {})

        # Calculate offsets for each discipline
        for discipline in ['ARC', 'STR']:
            # Get extracted elements for this discipline
            disc_elems = [e for e in self.elements if e.discipline == discipline]
            if not disc_elems:
                continue

            # Calculate DXF native bounds (in mm)
            dxf_xs = [e.x for e in disc_elems]
            dxf_ys = [e.y for e in disc_elems]
            dxf_min_x, dxf_max_x = min(dxf_xs), max(dxf_xs)
            dxf_min_y, dxf_max_y = min(dxf_ys), max(dxf_ys)
            dxf_center_x = (dxf_min_x + dxf_max_x) / 2
            dxf_center_y = (dxf_min_y + dxf_max_y) / 2

            # Get GPS target bounds (in meters)
            gps_bounds = target_gps.get(discipline, {})
            if not gps_bounds:
                continue

            gps_min_x = gps_bounds.get('min_x', 0)
            gps_max_x = gps_bounds.get('max_x', 0)
            gps_min_y = gps_bounds.get('min_y', 0)
            gps_max_y = gps_bounds.get('max_y', 0)
            gps_center_x = (gps_min_x + gps_max_x) / 2
            gps_center_y = (gps_min_y + gps_max_y) / 2

            # Calculate offset: GPS_m = (DXF_mm * 0.001) + offset
            # So: offset = GPS_m - (DXF_mm * 0.001)
            offset_x = gps_center_x - (dxf_center_x * 0.001)
            offset_y = gps_center_y - (dxf_center_y * 0.001)

            # Store in each element for later use
            for elem in disc_elems:
                elem.gps_offset_x = offset_x
                elem.gps_offset_y = offset_y

            logger.info(f"✅ {discipline} GPS alignment:")
            logger.info(f"   DXF native center: ({dxf_center_x:.1f}, {dxf_center_y:.1f}) mm")
            logger.info(f"   GPS target center: ({gps_center_x:.2f}, {gps_center_y:.2f}) m")
            logger.info(f"   GPS offset: ({offset_x:.2f}, {offset_y:.2f}) m")

    def populate_base_geometries(self):
        """Generate and populate base_geometries table with mesh data."""
        logger.info("\n" + "=" * 80)
        logger.info("GENERATING GEOMETRY")
        logger.info("=" * 80)

        conn = sqlite3.connect(str(self.output_db))
        cursor = conn.cursor()

        # Calculate global_offset FIRST (before generating geometry)
        # This allows us to generate geometry relative to model center
        cursor.execute("""
            SELECT
                MIN(center_x), MAX(center_x),
                MIN(center_y), MAX(center_y),
                MIN(center_z), MAX(center_z)
            FROM element_transforms
        """)
        min_x, max_x, min_y, max_y, min_z, max_z = cursor.fetchone()

        # Global offset = center of bounding box (for Blender viewport centering)
        global_offset_x = (min_x + max_x) / 2.0
        global_offset_y = (min_y + max_y) / 2.0
        global_offset_z = (min_z + max_z) / 2.0

        logger.info(f"📍 Global offset (model center): ({global_offset_x:.2f}, {global_offset_y:.2f}, {global_offset_z:.2f}) m")
        logger.info(f"   Geometry will be generated relative to this center")

        # Track unique geometries (geometry deduplication via hash)
        geometry_cache = {}  # hash → (vertices, faces, normals)
        generated = 0
        cached = 0

        # Debug: Track coordinate ranges
        first_5_coords = []

        for elem in self.elements:
            # Convert dimensions to meters
            length_m = elem.length * self.unit_scale
            width_m = elem.width * self.unit_scale
            height_m = elem.height * self.unit_scale

            # Get world position (from element_transforms, already calculated)
            x_m = elem.x * self.unit_scale
            y_m = elem.y * self.unit_scale

            # Apply GPS alignment if available
            if hasattr(elem, 'gps_offset_x'):
                x_m += elem.gps_offset_x
                y_m += elem.gps_offset_y

            # Apply legacy offset normalization
            norm_x = x_m - (self.offset_x * self.unit_scale)
            norm_y = y_m - (self.offset_y * self.unit_scale)
            norm_z = elem.z  # Already in meters

            # Apply global_offset to center geometry around origin (for Blender viewport)
            viewport_x = norm_x - global_offset_x
            viewport_y = norm_y - global_offset_y
            viewport_z = norm_z - global_offset_z

            # Generate geometry at viewport-relative position (enhanced with actual DXF shapes)
            vertices_blob, faces_blob, normals_blob, geom_hash = generate_element_geometry_enhanced(
                entity_geom=elem.entity_geom,  # Actual DXF entity geometry (CIRCLE radius, etc.)
                ifc_class=elem.ifc_class,
                length=length_m,
                width=width_m,
                height=height_m,
                center_x=viewport_x,
                center_y=viewport_y,
                center_z=viewport_z
            )

            # Debug: Log first 5 elements
            if len(first_5_coords) < 5:
                import struct
                first_vertex = struct.unpack('3f', vertices_blob[:12])
                first_5_coords.append({
                    'disc': elem.discipline,
                    'ifc_class': elem.ifc_class,
                    'center': (norm_x, norm_y, norm_z),
                    'dims': (length_m, width_m, height_m),
                    'first_vertex': first_vertex
                })

            # Check if this geometry already exists
            if geom_hash not in geometry_cache:
                # New unique geometry - insert into base_geometries
                cursor.execute("""
                    INSERT OR IGNORE INTO base_geometries
                    (guid, geometry_hash, vertices, faces, normals)
                    VALUES (?, ?, ?, ?, ?)
                """, (elem.guid, geom_hash, vertices_blob, faces_blob, normals_blob))

                geometry_cache[geom_hash] = (vertices_blob, faces_blob, normals_blob)
                generated += 1
            else:
                # Duplicate geometry - still need to link guid to hash
                cursor.execute("""
                    INSERT OR IGNORE INTO base_geometries
                    (guid, geometry_hash, vertices, faces, normals)
                    VALUES (?, ?, ?, ?, ?)
                """, (elem.guid, geom_hash, vertices_blob, faces_blob, normals_blob))
                cached += 1

            if (generated + cached) % 1000 == 0:
                logger.info(f"   Progress: {generated + cached}/{len(self.elements)} ({generated} unique, {cached} duplicates)")

        conn.commit()
        conn.close()

        logger.info(f"✅ Generated geometry for {len(self.elements)} elements")
        logger.info(f"   Unique geometries: {len(geometry_cache)}")
        logger.info(f"   Deduplication ratio: {(1 - len(geometry_cache)/len(self.elements))*100:.1f}%")

        # Debug output
        logger.info("\n🔍 DEBUG: First 5 elements geometry:")
        for i, elem_data in enumerate(first_5_coords):
            logger.info(f"   {i+1}. {elem_data['disc']}/{elem_data['ifc_class']}")
            logger.info(f"      Center: ({elem_data['center'][0]:.2f}, {elem_data['center'][1]:.2f}, {elem_data['center'][2]:.2f}) m")
            logger.info(f"      Dimensions: {elem_data['dims'][0]:.2f} × {elem_data['dims'][1]:.2f} × {elem_data['dims'][2]:.2f} m")
            logger.info(f"      First vertex: ({elem_data['first_vertex'][0]:.2f}, {elem_data['first_vertex'][1]:.2f}, {elem_data['first_vertex'][2]:.2f}) m")

    def populate_database(self):
        """Populate database with all elements."""
        logger.info("\n" + "=" * 80)
        logger.info("POPULATING DATABASE")
        logger.info("=" * 80)

        conn = sqlite3.connect(str(self.output_db))
        cursor = conn.cursor()

        inserted = 0
        for elem in self.elements:
            # Convert DXF mm to meters
            x_m = elem.x * self.unit_scale
            y_m = elem.y * self.unit_scale

            # Apply GPS alignment if available
            if hasattr(elem, 'gps_offset_x'):
                x_m += elem.gps_offset_x
                y_m += elem.gps_offset_y

            # Apply legacy offset normalization (for backward compat)
            norm_x = x_m - (self.offset_x * self.unit_scale)
            norm_y = y_m - (self.offset_y * self.unit_scale)
            norm_z = elem.z  # Already in meters

            # Insert into elements_meta
            cursor.execute("""
                INSERT INTO elements_meta
                (guid, discipline, ifc_class, filepath, element_name, element_type, storey)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                elem.guid,
                elem.discipline,
                elem.ifc_class,
                elem.source_file,
                elem.element_name,
                elem.element_type,
                elem.floor_id
            ))

            # Convert dimensions from mm to meters
            length_m = elem.length * self.unit_scale
            width_m = elem.width * self.unit_scale
            height_m = elem.height * self.unit_scale

            # Insert into element_transforms
            cursor.execute("""
                INSERT INTO element_transforms
                (guid, center_x, center_y, center_z, bbox_length, bbox_width, bbox_height)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (elem.guid, norm_x, norm_y, norm_z, length_m, width_m, height_m))

            inserted += 1

            if inserted % 1000 == 0:
                logger.info(f"   Progress: {inserted}/{len(self.elements)}")

        logger.info(f"✅ Inserted {inserted} elements")

        # DEBUG: Show sample of what was written
        cursor.execute("""
            SELECT em.guid, em.discipline, em.ifc_class, et.center_x, et.center_y, et.center_z
            FROM elements_meta em
            JOIN element_transforms et ON em.guid = et.guid
            LIMIT 3
        """)
        samples = cursor.fetchall()
        logger.info(f"\n🔍 DEBUG: Sample database entries (normalized, meters):")
        for guid, disc, ifc_class, x, y, z in samples:
            logger.info(f"   {disc}/{ifc_class}: X={x:.2f}m, Y={y:.2f}m, Z={z:.2f}m")

        # Populate global_offset
        # Calculate bounds from element_transforms to get center
        cursor.execute("""
            SELECT
                MIN(center_x), MAX(center_x),
                MIN(center_y), MAX(center_y),
                MIN(center_z), MAX(center_z)
            FROM element_transforms
        """)
        min_x, max_x, min_y, max_y, min_z, max_z = cursor.fetchone()

        # Global offset = center of bounding box (CENTER PATTERN - proven working)
        global_offset_x = (min_x + max_x) / 2.0
        global_offset_y = (min_y + max_y) / 2.0
        global_offset_z = (min_z + max_z) / 2.0

        extent_x = max_x - min_x
        extent_y = max_y - min_y
        extent_z = max_z - min_z

        logger.info(f"📍 Global offset (model center): ({global_offset_x:.2f}, {global_offset_y:.2f}, {global_offset_z:.2f}) m")
        logger.info(f"   Model extent: {extent_x:.2f} × {extent_y:.2f} × {extent_z:.2f} m")

        cursor.execute("""
            INSERT INTO global_offset (offset_x, offset_y, offset_z, extent_x, extent_y, extent_z)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (global_offset_x, global_offset_y, global_offset_z, extent_x, extent_y, extent_z))

        # Populate R-tree
        logger.info("   Building spatial index...")
        cursor.execute("""
            INSERT INTO elements_rtree (id, minX, maxX, minY, maxY, minZ, maxZ)
            SELECT
                t.rowid,
                t.center_x - (t.bbox_length / 2.0), t.center_x + (t.bbox_length / 2.0),
                t.center_y - (t.bbox_width / 2.0), t.center_y + (t.bbox_width / 2.0),
                t.center_z - (t.bbox_height / 2.0), t.center_z + (t.bbox_height / 2.0)
            FROM element_transforms t
        """)

        conn.commit()
        conn.close()

        logger.info("✅ Database populated")

    def generate_statistics(self):
        """Generate and display statistics."""
        logger.info("\n" + "=" * 80)
        logger.info("DATABASE STATISTICS")
        logger.info("=" * 80)

        conn = sqlite3.connect(str(self.output_db))
        cursor = conn.cursor()

        # Total elements
        cursor.execute("SELECT COUNT(*) FROM elements_meta")
        total = cursor.fetchone()[0]
        logger.info(f"\n📊 Total elements: {total}")

        # By floor
        logger.info(f"\n📊 By Floor:")
        cursor.execute("""
            SELECT storey, COUNT(*) as count
            FROM elements_meta
            GROUP BY storey
            ORDER BY storey
        """)
        for row in cursor.fetchall():
            logger.info(f"   {row[0]:5s}: {row[1]:6d}")

        # By discipline
        logger.info(f"\n📊 By Discipline:")
        cursor.execute("""
            SELECT discipline, COUNT(*) as count
            FROM elements_meta
            GROUP BY discipline
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            logger.info(f"   {row[0]:5s}: {row[1]:6d}")

        # By IFC class
        logger.info(f"\n📊 By IFC Class:")
        cursor.execute("""
            SELECT ifc_class, COUNT(*) as count
            FROM elements_meta
            GROUP BY ifc_class
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            logger.info(f"   {row[0]:30s}: {row[1]:6d}")

        conn.close()

        logger.info("\n" + "=" * 80)
        logger.info("✅ COMPLETE")
        logger.info("=" * 80)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""

    # Hardcoded paths (config-driven)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    config_path = project_root / "building_config.json"
    source_dir = project_root / "SourceFiles" / "TERMINAL1DXF"
    output_db = project_root / "BASE_ARC_STR.db"

    logger.info("=" * 80)
    logger.info("MULTI-FLOOR DXF TO DATABASE CONVERTER")
    logger.info("Config-Driven ARC + STR Processor")
    logger.info("=" * 80)
    logger.info(f"Config: {config_path}")
    logger.info(f"Source: {source_dir}")
    logger.info(f"Output: {output_db}")
    logger.info("")

    try:
        processor = MultiFloorProcessor(config_path, source_dir, output_db)

        # Step 1: Load config
        processor.load_config()

        # Step 2: Calculate coordinate alignment
        alignment_config = processor.config.get('coordinate_alignment', {})
        if alignment_config.get('enabled', False):
            strategy = alignment_config.get('strategy')
            if strategy == 'grid_corner':
                processor.calculate_grid_alignment()
            elif strategy == 'manual_offset':
                processor.arc_offset_x = alignment_config.get('offset_x_mm', 0)
                processor.arc_offset_y = alignment_config.get('offset_y_mm', 0)
                logger.info(f"\n✅ Using Manual Alignment Offset:")
                logger.info(f"   ARC Offset: ({processor.arc_offset_x:.0f}, {processor.arc_offset_y:.0f}) mm")
                logger.info(f"   Strategy: Density-based building center alignment")

        # Step 3: Calculate STR bounds (for spatial filter)
        spatial_config = processor.config.get('spatial_filter', {})
        if spatial_config.get('enabled', False) and spatial_config.get('strategy') == 'use_str_bounds':
            processor.calculate_str_bounds()

        # Step 4: Parse ARC template (with spatial filter and alignment applied)
        processor.parse_arc_template()

        # Step 5: Process each floor
        for floor_config in processor.config['floor_levels']:
            # Process ALL floors (ignore active flag for now - we want complete building)
            processor.process_floor(floor_config)

        # Step 6: Calculate normalization
        processor.calculate_normalization()

        # Step 6.5: Calculate GPS alignment (per-discipline offsets)
        processor.calculate_gps_alignment()

        # Step 7: Create database
        processor.create_database()

        # Step 8: Populate database
        processor.populate_database()

        # Step 9: Generate and populate geometry
        processor.populate_base_geometries()

        # Step 10: Statistics
        processor.generate_statistics()

        logger.info(f"\n✅ SUCCESS: Database created at {output_db}")
        logger.info(f"   Total elements: {len(processor.elements)}")
        logger.info(f"   Total floors: {len(processor.config['floor_levels'])}")

    except FileNotFoundError as e:
        logger.error(f"\n❌ ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
