#!/usr/bin/env python3
"""
Analyze DXF file to extract all block names, layers, and metadata.
This helps identify what object types exist and how to map them to shapes.
"""

import sys
from pathlib import Path
from collections import defaultdict, Counter
import json

try:
    import ezdxf
except ImportError:
    print("❌ ERROR: ezdxf not installed")
    print("Install: pip install ezdxf")
    sys.exit(1)


def analyze_dxf(dxf_path):
    """Analyze DXF file and extract all block names, layers, attributes."""

    print("="*80)
    print("DXF BLOCK & LAYER ANALYSIS")
    print("="*80)
    print(f"File: {dxf_path}\n")

    # Open DXF
    try:
        doc = ezdxf.readfile(str(dxf_path))
        print(f"✅ Opened DXF (version: {doc.dxfversion})\n")
    except Exception as e:
        print(f"❌ Error reading DXF: {e}")
        return

    modelspace = doc.modelspace()

    # Data structures
    block_names = Counter()
    layer_names = Counter()
    block_by_layer = defaultdict(Counter)
    entity_types = Counter()
    attributes_found = defaultdict(set)  # block_name -> set of attribute tags
    xdata_found = defaultdict(int)  # block_name -> count with XDATA

    # Analyze all entities
    print("🔍 Scanning entities...")
    total_entities = 0

    for entity in modelspace:
        total_entities += 1
        entity_type = entity.dxftype()
        layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else 'UNKNOWN'

        entity_types[entity_type] += 1
        layer_names[layer] += 1

        # For INSERT entities (blocks)
        if entity_type == 'INSERT':
            if hasattr(entity.dxf, 'name'):
                block_name = entity.dxf.name
                block_names[block_name] += 1
                block_by_layer[layer][block_name] += 1

                # Check for attributes
                if hasattr(entity, 'attribs'):
                    for attr in entity.attribs:
                        tag = attr.dxf.tag if hasattr(attr.dxf, 'tag') else 'UNKNOWN'
                        attributes_found[block_name].add(tag)

                # Check for XDATA
                if hasattr(entity, 'has_xdata') and entity.has_xdata:
                    xdata_found[block_name] += 1

    print(f"✅ Scanned {total_entities:,} entities\n")

    # =========================================================================
    # REPORT: Entity Types
    # =========================================================================
    print("="*80)
    print("ENTITY TYPES")
    print("="*80)
    for entity_type, count in entity_types.most_common(20):
        print(f"  {entity_type:20} {count:6,} entities")
    print()

    # =========================================================================
    # REPORT: Layers
    # =========================================================================
    print("="*80)
    print("LAYERS (Top 30)")
    print("="*80)
    for layer, count in layer_names.most_common(30):
        print(f"  {layer:40} {count:6,} entities")
    print()

    # =========================================================================
    # REPORT: Block Names (INSERT entities)
    # =========================================================================
    print("="*80)
    print(f"BLOCK NAMES (Total unique: {len(block_names)})")
    print("="*80)

    # Group by discipline prefix
    discipline_blocks = defaultdict(list)
    unknown_blocks = []

    for block_name, count in block_names.most_common():
        # Extract discipline prefix (before first hyphen or underscore)
        parts = block_name.replace('_', '-').split('-')
        if parts:
            prefix = parts[0].upper()
            if prefix in ('FP', 'ARC', 'ELEC', 'ACMV', 'SP', 'STR', 'CW', 'LPG'):
                discipline_blocks[prefix].append((block_name, count))
            else:
                unknown_blocks.append((block_name, count))
        else:
            unknown_blocks.append((block_name, count))

    # Print by discipline
    for discipline in sorted(discipline_blocks.keys()):
        print(f"\n{discipline} Blocks ({len(discipline_blocks[discipline])} types):")
        print("-"*80)
        for block_name, count in discipline_blocks[discipline][:20]:  # Top 20 per discipline
            attrs = ", ".join(sorted(attributes_found.get(block_name, [])))
            xdata_count = xdata_found.get(block_name, 0)
            xdata_str = f" [XDATA: {xdata_count}]" if xdata_count > 0 else ""
            attr_str = f" (attrs: {attrs})" if attrs else ""
            print(f"  {block_name:50} {count:5,}{xdata_str}{attr_str}")

    # Unknown/Other blocks
    if unknown_blocks:
        print(f"\nOther/Unknown Blocks ({len(unknown_blocks)} types):")
        print("-"*80)
        for block_name, count in unknown_blocks[:30]:  # Top 30
            attrs = ", ".join(sorted(attributes_found.get(block_name, [])))
            xdata_count = xdata_found.get(block_name, 0)
            xdata_str = f" [XDATA: {xdata_count}]" if xdata_count > 0 else ""
            attr_str = f" (attrs: {attrs})" if attrs else ""
            print(f"  {block_name:50} {count:5,}{xdata_str}{attr_str}")

    # =========================================================================
    # REPORT: Block Name Patterns (for shape mapping)
    # =========================================================================
    print("\n" + "="*80)
    print("BLOCK NAME PATTERNS (for shape inference)")
    print("="*80)

    # Common keywords for object types
    keywords = {
        'sprinkler': [],
        'light': [],
        'chair': [],
        'table': [],
        'toilet': [],
        'sink': [],
        'door': [],
        'window': [],
        'column': [],
        'beam': [],
        'diffuser': [],
        'grille': [],
        'panel': [],
        'alarm': [],
        'detector': [],
        'outlet': [],
        'switch': [],
    }

    for block_name in block_names.keys():
        block_lower = block_name.lower()
        for keyword in keywords.keys():
            if keyword in block_lower:
                keywords[keyword].append(block_name)

    for keyword, blocks in sorted(keywords.items()):
        if blocks:
            total_count = sum(block_names[b] for b in blocks)
            print(f"\n{keyword.upper()} ({len(blocks)} types, {total_count} instances):")
            for block_name in blocks[:10]:  # Show first 10
                print(f"  - {block_name} ({block_names[block_name]} instances)")

    # =========================================================================
    # EXPORT: JSON mapping for shape inference
    # =========================================================================
    output_file = "dxf_block_analysis.json"

    analysis_data = {
        "summary": {
            "total_entities": total_entities,
            "total_blocks": len(block_names),
            "total_layers": len(layer_names),
            "blocks_with_attributes": len(attributes_found),
            "blocks_with_xdata": len(xdata_found)
        },
        "blocks_by_discipline": {
            discipline: [
                {"name": name, "count": count}
                for name, count in blocks
            ]
            for discipline, blocks in discipline_blocks.items()
        },
        "keyword_patterns": {
            keyword: [
                {"name": name, "count": block_names[name]}
                for name in blocks
            ]
            for keyword, blocks in keywords.items() if blocks
        },
        "block_attributes": {
            block: list(attrs)
            for block, attrs in attributes_found.items()
        }
    }

    with open(output_file, 'w') as f:
        json.dump(analysis_data, f, indent=2)

    print("\n" + "="*80)
    print(f"✅ Analysis complete! Exported to: {output_file}")
    print("="*80)
    print("\nNext steps:")
    print("1. Review keyword patterns above")
    print("2. Create block_name -> shape mapping rules")
    print("3. Update dxf_to_database.py to infer object types")
    print("4. Regenerate database with accurate shapes")
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_dxf_blocks.py <dxf_file>")
        print("\nExample:")
        print('  python3 analyze_dxf_blocks.py "2. BANGUNAN TERMINAL 1.dxf"')
        sys.exit(1)

    dxf_path = Path(sys.argv[1])
    if not dxf_path.exists():
        print(f"❌ ERROR: DXF file not found: {dxf_path}")
        sys.exit(1)

    analyze_dxf(dxf_path)


if __name__ == "__main__":
    main()
