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
        position = (0.0, 0.0, 0.0)
        if hasattr(entity.dxf, 'insert'):
            position = (entity.dxf.insert.x, entity.dxf.insert.y, entity.dxf.insert.z)
        elif hasattr(entity.dxf, 'start'):
            position = (entity.dxf.start.x, entity.dxf.start.y, entity.dxf.start.z)

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

        conn.commit()
        conn.close()
        print(f"✅ Database schema created")

    def populate_database(self):
        """Populate database with matched entities."""
        print(f"📝 Populating database...")

        conn = sqlite3.connect(str(self.output_db))
        cursor = conn.cursor()

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

            # Insert position
            cursor.execute("""
                INSERT INTO element_transforms
                (guid, center_x, center_y, center_z)
                VALUES (?, ?, ?, ?)
            """, (guid, entity.position[0], entity.position[1], entity.position[2]))

            inserted += 1

        conn.commit()
        conn.close()

        print(f"✅ Inserted {inserted} elements into database")
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
        print("Usage: python3 dxf_to_database.py [dxf_file] [output_db] [template_library_db]")
        print("\nExample:")
        print('  python3 dxf_to_database.py "Terminal1.dxf" Generated_Terminal1.db terminal_base_v1.0/template_library.db')
        sys.exit(1)

    dxf_file = sys.argv[1]
    output_db = sys.argv[2]
    template_db = sys.argv[3]

    try:
        # Load templates
        print("="*70)
        print("DXF to Database Converter")
        print("="*70 + "\n")

        template_library = TemplateLibrary(template_db)

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

        # Step 3: Create database
        converter.create_database()

        # Step 4: Populate database
        inserted = converter.populate_database()

        # Step 5: Show statistics
        converter.generate_statistics()

        print(f"\n✅ SUCCESS: Database created at {output_db}")
        print(f"   Total elements: {inserted}")
        print(f"   Match rate: {matched/len(entities)*100:.1f}%")

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
