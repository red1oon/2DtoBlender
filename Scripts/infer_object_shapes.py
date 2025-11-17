#!/usr/bin/env python3
"""
Infer object shapes from DXF layer names, block names, and position heuristics.
Updates database with inferred_shape_type for use in geometry generation.

Strategy:
1. Layer name patterns (FURNITURE, SAN, EL, etc.)
2. Block name keywords (EME LIGHT, detector, sink, etc.)
3. Position/Z-height heuristics (near ceiling = lights/sprinklers)
4. Discipline context (FP near ceiling = sprinklers, EL near ceiling = lights)
5. Size heuristics (small objects = fixtures, large = furniture)
"""

import sys
import sqlite3
from pathlib import Path
from collections import Counter


# Shape type mappings to shape_library.py functions
SHAPE_TYPES = {
    # Furniture
    'chair': 'chair',
    'table': 'table',

    # Sanitary/Plumbing
    'toilet': 'toilet',
    'sink': 'sink',

    # Fire Protection
    'sprinkler': 'sprinkler_head',
    'fire_alarm': 'alarm',
    'detector': 'detector',

    # Electrical
    'light_fixture': 'light_panel',
    'panel': 'electrical_panel',
    'outlet': 'box',  # Small box

    # HVAC
    'diffuser': 'hvac_diffuser',
    'grille': 'hvac_diffuser',
    'duct': 'box',  # Rectangular duct

    # Default shapes
    'box': 'box',
    'frame': 'frame',
    'cylinder': 'cylinder',
}


def infer_shape_from_layer(layer_name):
    """Infer shape type from DXF layer name."""
    layer_lower = layer_name.lower()

    # Furniture
    if 'furniture' in layer_lower or 'chair' in layer_lower or 'table' in layer_lower:
        if 'chair' in layer_lower:
            return 'chair'
        elif 'table' in layer_lower:
            return 'table'
        return 'chair'  # Default furniture = chair

    # Sanitary
    if 'san' in layer_lower or 'toilet' in layer_lower or 'wc' in layer_lower:
        if 'sink' in layer_lower or 'basin' in layer_lower:
            return 'sink'
        return 'toilet'

    # Electrical
    if 'el' in layer_lower or 'elec' in layer_lower or 'light' in layer_lower:
        if 'panel' in layer_lower:
            return 'panel'
        return 'light_fixture'

    # Fire protection
    if 'fire' in layer_lower or 'sprinkler' in layer_lower or 'fp' in layer_lower:
        if 'alarm' in layer_lower or 'detect' in layer_lower:
            return 'detector'
        return 'sprinkler'

    # HVAC
    if 'acmv' in layer_lower or 'hvac' in layer_lower or 'ac' in layer_lower:
        if 'diffuser' in layer_lower or 'grille' in layer_lower:
            return 'diffuser'
        return 'box'  # Default HVAC equipment

    return None


def infer_shape_from_block_name(block_name):
    """Infer shape type from DXF block name."""
    if not block_name:
        return None

    block_lower = block_name.lower()

    # Specific keyword matches
    if 'light' in block_lower:
        return 'light_fixture'
    if 'detector' in block_lower or 'smoke' in block_lower or 'heat' in block_lower:
        return 'detector'
    if 'sprinkler' in block_lower:
        return 'sprinkler'
    if 'chair' in block_lower or 'seat' in block_lower:
        return 'chair'
    if 'table' in block_lower or 'desk' in block_lower:
        return 'table'
    if 'toilet' in block_lower or 'wc' in block_lower:
        return 'toilet'
    if 'sink' in block_lower or 'basin' in block_lower:
        return 'sink'
    if 'alarm' in block_lower:
        return 'fire_alarm'
    if 'diffuser' in block_lower or 'grille' in block_lower:
        return 'diffuser'
    if 'panel' in block_lower and 'elec' in block_lower:
        return 'panel'

    return None


def infer_shape_from_position(z_height, discipline, ifc_class):
    """Infer shape type from Z-position and discipline context."""

    # Near ceiling (Z > 3.5m typically)
    if z_height > 3.0:
        if discipline in ('FP', 'Fire_Protection'):
            return 'sprinkler'
        elif discipline in ('ELEC', 'Electrical'):
            return 'light_fixture'
        elif discipline in ('ACMV', 'HVAC'):
            return 'diffuser'

    # Floor level (Z < 1m)
    elif z_height < 1.0:
        if discipline in ('ARC', 'Seating'):
            if ifc_class == 'IfcFurniture':
                return 'chair'  # Default furniture at floor = chairs
        elif discipline in ('SP', 'Plumbing'):
            return 'toilet'  # Plumbing at floor likely toilets

    # Mid-height (1-3m) - walls, equipment
    else:
        if discipline in ('ELEC', 'Electrical'):
            return 'panel'  # Mid-height electrical = panels/switches

    return None


def infer_shape_from_size(length, width, height):
    """Infer shape type from element dimensions."""

    # Very small objects (< 0.5m all dimensions) = fixtures/outlets
    if length < 0.5 and width < 0.5 and height < 0.5:
        return 'outlet'  # Small box

    # Tall narrow objects = columns (already handled by IFC class)
    if height > 2.5 and length < 1.0 and width < 1.0:
        return 'cylinder'  # Likely column

    # Wide flat objects = tables
    if length > 1.0 and width > 0.5 and height < 1.0:
        return 'table'

    # Cube-ish medium objects = chairs/furniture
    if 0.4 < length < 1.0 and 0.4 < width < 1.0 and 0.4 < height < 1.2:
        return 'chair'

    return None


def infer_all_shapes(db_path):
    """Infer shapes for all elements in database."""

    print("="*80)
    print("INFERRING OBJECT SHAPES FROM DXF METADATA")
    print("="*80)
    print(f"Database: {db_path}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add inferred_shape_type column if not exists
    try:
        cursor.execute("ALTER TABLE elements_meta ADD COLUMN inferred_shape_type TEXT")
        print("✅ Added inferred_shape_type column\n")
    except:
        print("✅ inferred_shape_type column already exists\n")

    # Get all elements with metadata
    cursor.execute("""
        SELECT
            em.guid,
            em.ifc_class,
            em.discipline,
            em.element_type,
            em.dimensions,
            et.center_z
        FROM elements_meta em
        JOIN element_transforms et ON em.guid = et.guid
    """)

    elements = cursor.fetchall()
    print(f"Found {len(elements)} elements to analyze\n")

    # Parse layer/block names from element_type column
    # element_type contains either block_name (for INSERT) or entity_type (for others)

    stats = {
        'total': len(elements),
        'inferred': 0,
        'from_layer': 0,
        'from_block': 0,
        'from_position': 0,
        'from_size': 0,
        'default': 0,
        'by_shape': Counter()
    }

    import json

    for guid, ifc_class, discipline, element_type, dimensions_json, z_height in elements:
        inferred_shape = None
        inference_source = None

        # Parse dimensions
        dims = {}
        if dimensions_json:
            try:
                dims = json.loads(dimensions_json)
            except:
                pass

        # Strategy 1: Try block name (element_type for INSERT entities)
        if element_type and element_type not in ('LWPOLYLINE', 'LINE', 'CIRCLE', 'POLYLINE'):
            inferred_shape = infer_shape_from_block_name(element_type)
            if inferred_shape:
                inference_source = 'block_name'
                stats['from_block'] += 1

        # Strategy 2: Try position heuristics
        if not inferred_shape:
            inferred_shape = infer_shape_from_position(z_height, discipline, ifc_class)
            if inferred_shape:
                inference_source = 'position'
                stats['from_position'] += 1

        # Strategy 3: Try size heuristics
        if not inferred_shape and dims:
            length = dims.get('length', 0)
            width = dims.get('width', 0)
            height = dims.get('height', 0)
            inferred_shape = infer_shape_from_size(length, width, height)
            if inferred_shape:
                inference_source = 'size'
                stats['from_size'] += 1

        # Strategy 4: Use IFC class defaults
        if not inferred_shape:
            if ifc_class == 'IfcColumn':
                inferred_shape = 'cylinder'
            elif ifc_class in ('IfcDoor', 'IfcWindow'):
                inferred_shape = 'frame'
            else:
                inferred_shape = 'box'  # Default
            inference_source = 'default'
            stats['default'] += 1

        # Update database
        if inferred_shape:
            cursor.execute("""
                UPDATE elements_meta
                SET inferred_shape_type = ?
                WHERE guid = ?
            """, (inferred_shape, guid))

            stats['inferred'] += 1
            stats['by_shape'][inferred_shape] += 1

    conn.commit()

    # Print statistics
    print("="*80)
    print("INFERENCE COMPLETE")
    print("="*80)
    print(f"Total elements:      {stats['total']}")
    print(f"Shapes inferred:     {stats['inferred']} ({stats['inferred']/stats['total']*100:.1f}%)")
    print(f"\nInference sources:")
    print(f"  From block names:  {stats['from_block']}")
    print(f"  From position:     {stats['from_position']}")
    print(f"  From size:         {stats['from_size']}")
    print(f"  Default (IFC):     {stats['default']}")
    print(f"\nShape distribution:")
    for shape, count in stats['by_shape'].most_common():
        pct = count / stats['total'] * 100
        print(f"  {shape:20} {count:5,} ({pct:4.1f}%)")

    # Verification queries
    print("\n" + "="*80)
    print("VERIFICATION BY DISCIPLINE")
    print("="*80)

    cursor.execute("""
        SELECT discipline, inferred_shape_type, COUNT(*) as count
        FROM elements_meta
        WHERE inferred_shape_type IS NOT NULL
        GROUP BY discipline, inferred_shape_type
        ORDER BY discipline, count DESC
    """)

    current_disc = None
    for discipline, shape, count in cursor.fetchall():
        if discipline != current_disc:
            print(f"\n{discipline}:")
            current_disc = discipline
        print(f"  {shape:20} {count:5,}")

    conn.close()

    print("\n" + "="*80)
    print("✅ SUCCESS: Shape inference complete!")
    print("="*80)
    print("\nNext step: Regenerate geometry with inferred shapes")
    print("  python3 Scripts/generate_3d_geometry.py Terminal1_MainBuilding_FILTERED.db")
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 infer_object_shapes.py <database_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}")
        sys.exit(1)

    infer_all_shapes(db_path)


if __name__ == "__main__":
    main()
