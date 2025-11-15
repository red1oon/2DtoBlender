#!/usr/bin/env python3
"""
DWG Parser Module

Reads DWG/DXF files and extracts entities for template matching.

Usage:
    python3 dwg_parser.py [dwg_file]

Example:
    python3 dwg_parser.py "2. BANGUNAN TERMINAL 1 .dwg"
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict

try:
    import ezdxf
except ImportError:
    print("❌ ERROR: ezdxf not installed")
    print("Install: pip install ezdxf")
    sys.exit(1)


@dataclass
class DWGEntity:
    """Represents a DWG entity."""
    entity_type: str      # INSERT (block), LINE, POLYLINE, etc.
    layer: str            # Layer name (ARC-WALL, FP-PIPE, etc.)
    block_name: Optional[str] = None  # For INSERT entities
    handle: Optional[str] = None      # DWG handle
    attributes: Dict = None           # Additional attributes

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


class DWGParser:
    """Parse DWG/DXF files."""

    def __init__(self, file_path: str):
        """
        Initialize parser.

        Args:
            file_path: Path to DWG or DXF file
        """
        self.file_path = Path(file_path)

        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        self.doc = None
        self.entities = []
        self.statistics = defaultdict(int)

    def parse(self) -> List[DWGEntity]:
        """
        Parse DWG/DXF file and extract entities.

        Returns:
            List of DWGEntity objects
        """
        print(f"📂 Opening: {self.file_path.name}")

        try:
            # Read DXF file (DWG must be converted to DXF first)
            self.doc = ezdxf.readfile(str(self.file_path))
            print(f"✅ Opened as DXF (version: {self.doc.dxfversion})")

        except Exception as e:
            print(f"❌ Error reading file: {e}")
            print(f"💡 If this is a DWG file, convert to DXF first using:")
            print(f"   - ODA File Converter (free): https://www.opendesign.com/guestfiles/oda_file_converter")
            print(f"   - Or use ezdxf.addons.odafc if ODA is installed")
            return []

        # Extract entities from modelspace
        print(f"📊 Analyzing modelspace...")
        modelspace = self.doc.modelspace()

        for entity in modelspace:
            dwg_entity = self._extract_entity(entity)
            if dwg_entity:
                self.entities.append(dwg_entity)
                self.statistics[dwg_entity.entity_type] += 1
                if dwg_entity.layer:
                    self.statistics[f"layer:{dwg_entity.layer}"] += 1

        print(f"✅ Found {len(self.entities)} entities")

        return self.entities

    def _extract_entity(self, entity) -> Optional[DWGEntity]:
        """
        Extract information from a single entity.

        Args:
            entity: ezdxf entity object

        Returns:
            DWGEntity or None
        """
        entity_type = entity.dxftype()
        layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else 'UNKNOWN'
        handle = entity.dxf.handle if hasattr(entity.dxf, 'handle') else None

        # Extract block name for INSERT entities
        block_name = None
        if entity_type == 'INSERT':
            block_name = entity.dxf.name if hasattr(entity.dxf, 'name') else None

        # Extract attributes (extended data, etc.)
        attributes = {}

        # Try to get position if available
        if hasattr(entity.dxf, 'insert'):
            attributes['position'] = (entity.dxf.insert.x, entity.dxf.insert.y, entity.dxf.insert.z)
        elif hasattr(entity.dxf, 'start'):
            attributes['start'] = (entity.dxf.start.x, entity.dxf.start.y, entity.dxf.start.z)

        return DWGEntity(
            entity_type=entity_type,
            layer=layer,
            block_name=block_name,
            handle=handle,
            attributes=attributes
        )

    def get_statistics(self) -> Dict:
        """
        Get parsing statistics.

        Returns:
            Dictionary with counts
        """
        return dict(self.statistics)

    def get_layers(self) -> List[str]:
        """
        Get unique layer names.

        Returns:
            List of layer names
        """
        layers = set()
        for entity in self.entities:
            if entity.layer:
                layers.add(entity.layer)
        return sorted(layers)

    def get_blocks(self) -> Dict[str, int]:
        """
        Get block names and counts.

        Returns:
            Dictionary: {block_name: count}
        """
        blocks = defaultdict(int)
        for entity in self.entities:
            if entity.block_name:
                blocks[entity.block_name] += 1
        return dict(blocks)

    def filter_by_layer(self, layer_pattern: str) -> List[DWGEntity]:
        """
        Filter entities by layer name pattern.

        Args:
            layer_pattern: Pattern to match (case-insensitive)

        Returns:
            List of matching entities
        """
        pattern = layer_pattern.upper()
        return [e for e in self.entities if pattern in e.layer.upper()]

    def filter_by_type(self, entity_type: str) -> List[DWGEntity]:
        """
        Filter entities by type.

        Args:
            entity_type: Type to match (INSERT, LINE, POLYLINE, etc.)

        Returns:
            List of matching entities
        """
        return [e for e in self.entities if e.entity_type == entity_type.upper()]

    def print_summary(self):
        """Print parsing summary."""
        print("\n" + "="*70)
        print("DWG Parsing Summary")
        print("="*70)

        print(f"\nFile: {self.file_path.name}")
        print(f"Total entities: {len(self.entities)}")

        # Entity types
        print(f"\nEntity Types:")
        entity_types = defaultdict(int)
        for entity in self.entities:
            entity_types[entity.entity_type] += 1

        for entity_type, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {entity_type:20s}: {count:6d}")

        if len(entity_types) > 10:
            print(f"  ... and {len(entity_types) - 10} more types")

        # Layers
        layers = self.get_layers()
        print(f"\nLayers: {len(layers)}")
        for layer in sorted(layers)[:10]:
            layer_entities = self.filter_by_layer(layer)
            print(f"  {layer:30s}: {len(layer_entities):6d} entities")

        if len(layers) > 10:
            print(f"  ... and {len(layers) - 10} more layers")

        # Blocks
        blocks = self.get_blocks()
        if blocks:
            print(f"\nBlock Inserts: {len(blocks)} unique blocks")
            for block_name, count in sorted(blocks.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {block_name[:40]:40s}: {count:6d} instances")

            if len(blocks) > 10:
                print(f"  ... and {len(blocks) - 10} more blocks")

        print("\n" + "="*70)


def main():
    """Main entry point."""

    if len(sys.argv) < 2:
        print("Usage: python3 dwg_parser.py [dwg_file]")
        print("\nExample:")
        print('  python3 dwg_parser.py "2. BANGUNAN TERMINAL 1 .dwg"')
        sys.exit(1)

    dwg_file = sys.argv[1]

    try:
        parser = DWGParser(dwg_file)
        entities = parser.parse()

        if entities:
            parser.print_summary()

            # Save results for later use
            print(f"\n💾 Results stored in memory ({len(entities)} entities)")
            print(f"   Use parser.filter_by_layer('ARC') for specific queries")

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
