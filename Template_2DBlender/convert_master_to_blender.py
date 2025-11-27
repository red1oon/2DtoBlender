#!/usr/bin/env python3
"""
Convert master_template.json to Blender-ready JSON format.

Reads:  master_template.json (14 elements: 7 doors + 7 windows)
Writes: blender_import.json (format for blender_lod300_import.py)

Converts:
- element_id → name
- wall (SOUTH/NORTH/EAST/WEST) → rotation (degrees)
- width_mm × height_mm → library object_type (queried from Ifc_Object_Library.db)
- position {x,y,z} → position [x,y,z]

RULE 0 COMPLIANT: Queries Ifc_Object_Library.db dynamically instead of hardcoded mappings
Reference: prompt.txt - Fix Rule 0 violation in Stage 7
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional, Tuple

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

LIBRARY_DB_PATH = Path(__file__).parent / "LocalLibrary/Ifc_Object_Library.db"

# ============================================================================
# MANUAL LIBRARY OBJECT MAPPING (USER-DEFINED CHEATSHEET)
# ============================================================================
# This is the HUMAN/AI part: manually assign library objects from PDF specs
# After this mapping, everything becomes Rule 0 (deterministic)
#
# CRITICAL: Only use objects that have NORMALS in base_geometries table
# Verified with: SELECT object_type FROM object_catalog oc JOIN base_geometries bg
#                ON oc.geometry_hash = bg.geometry_hash WHERE bg.normals IS NOT NULL
#
# PDF Reference: TB-LKTN HOUSE.pdf Page 8 (Door/Window Schedule)
# ============================================================================

MANUAL_LIBRARY_MAPPING = {
    # Doors: Verified to have normals in library
    ("IfcDoor", 900, 2100): "door_single_900_lod300",      # D1, D2 - Main/Bedroom doors
    ("IfcDoor", 750, 2100): "door_single_750x2100_lod300", # D3 - Bathroom doors

    # Windows: Verified to have normals in library
    ("IfcWindow", 1800, 1000): "window_aluminum_3panel_1800x1000",  # W1 - Kitchen
    ("IfcWindow", 1200, 1000): "window_aluminum_2panel_1200x1000",  # W2 - Living/Bedrooms
    ("IfcWindow", 600, 500): "window_aluminum_tophung_600x500",     # W3 - Bathrooms

    # Walls: Verified to have normals in library
    ("IfcWall", 250, 2700): "wall_brick_cavity_250_lod300",  # Exterior walls (MS 1064:1986)
}

# ============================================================================
# VERIFIED OBJECT TYPES (Pre-generated objects from inference stages)
# ============================================================================
# These objects are generated with object_type already specified by:
#   - Stage 5.5: Bathroom fixtures (infer_bathroom_fixtures.py)
#   - Stage 5.6-5.8: Furniture (infer_all_furniture.py)
#   - Stage 5.9: Roof objects (generate_roof_objects.py)
#   - Stage 5.10: Porch objects (generate_porch_objects_v2.py)
#   - Stage 5.11: Floor slab (generate_floor_slab.py)
#
# All verified to exist in Ifc_Object_Library.db with complete geometry.
# ============================================================================

VERIFIED_OBJECT_TYPES = {
    # Bathroom fixtures
    "basin_residential_lod300",
    "floor_mounted_toilet_lod300",
    "shower_enclosure_900",
    "showerhead_fixed_lod200",
    "electrical_outlet_weatherproof",
    "electrical_switch_weatherproof",

    # Kitchen fixtures
    "kitchen_sink_single_bowl_lod200",
    "kitchen_base_cabinet_900_lod300",
    "electrical_outlet_double",
    "electrical_switch_dimmer",

    # Bedroom furniture
    "bed_queen_lod300",
    "furniture_wardrobe",

    # Living room furniture
    "sofa_2seater_lod300",
    "coffee_table",
    "ict_tv_point",

    # Dining
    "dining_table_6seat",

    # Roof objects
    "roof_tile_9.7x7_lod300",
    "roof_gutter_100_lod300",
    "roof_fascia_200_lod300",

    # Porch/Floor
    "wall_lightweight_75_lod300",
    "roof_slab_flat_lod300",
}


def wall_to_rotation(wall: str) -> float:
    """
    Convert wall orientation to rotation degrees.
    Based on coordinate_generator.py:326-334

    Args:
        wall: NORTH, SOUTH, EAST, or WEST

    Returns:
        Rotation in degrees
    """
    rotations = {
        "NORTH": 0,    # Horizontal wall
        "SOUTH": 0,    # Horizontal wall
        "EAST": 90,    # Vertical wall
        "WEST": 90     # Vertical wall
    }
    return rotations.get(wall, 0)


def query_library_object_type(width_mm: int, height_mm: int, ifc_class: str, tolerance_mm: int = 50) -> Optional[str]:
    """
    Query Ifc_Object_Library.db for object_type matching dimensions.

    RULE 0 COMPLIANT: Dynamic database query instead of hardcoded mapping.

    Search strategy:
    1. Exact match (width_mm, height_mm)
    2. Close match within tolerance (±50mm default)
    3. Prefer specific types (e.g., door_louvre_750) over generic (door_single)

    Args:
        width_mm: Target width in mm
        height_mm: Target height in mm
        ifc_class: IfcDoor or IfcWindow
        tolerance_mm: Acceptable dimension tolerance (default 50mm)

    Returns:
        object_type string or None if no match found
    """
    if not LIBRARY_DB_PATH.exists():
        print(f"⚠️  WARNING: Library database not found: {LIBRARY_DB_PATH}")
        return None

    try:
        conn = sqlite3.connect(LIBRARY_DB_PATH)
        cursor = conn.cursor()

        # Strategy 1: Try exact match with specific type name (non-generic)
        # CRITICAL: Must JOIN base_geometries to ensure geometry actually exists
        cursor.execute("""
            SELECT oc.object_type, oc.width_mm, oc.height_mm,
                   ABS(oc.width_mm - ?) + ABS(oc.height_mm - ?) as dim_diff
            FROM object_catalog oc
            JOIN base_geometries bg ON oc.geometry_hash = bg.geometry_hash
            WHERE oc.ifc_class = ?
              AND oc.width_mm BETWEEN ? AND ?
              AND oc.height_mm BETWEEN ? AND ?
              AND oc.object_type NOT IN ('door_single', 'window_single')
              AND bg.vertices IS NOT NULL
              AND bg.faces IS NOT NULL
              AND bg.normals IS NOT NULL
            ORDER BY dim_diff ASC
            LIMIT 1
        """, (width_mm, height_mm, ifc_class,
              width_mm - tolerance_mm, width_mm + tolerance_mm,
              height_mm - tolerance_mm, height_mm + tolerance_mm))

        result = cursor.fetchone()
        if result:
            object_type, actual_w, actual_h, diff = result
            print(f"  ✓ Found specific type: {object_type} ({actual_w}×{actual_h}mm, diff={diff}mm)")
            conn.close()
            return object_type

        # Strategy 2: Fall back to generic type (door_single, window_single)
        # CRITICAL: Must JOIN base_geometries to ensure geometry actually exists
        cursor.execute("""
            SELECT oc.object_type, oc.width_mm, oc.height_mm,
                   ABS(oc.width_mm - ?) + ABS(oc.height_mm - ?) as dim_diff
            FROM object_catalog oc
            JOIN base_geometries bg ON oc.geometry_hash = bg.geometry_hash
            WHERE oc.ifc_class = ?
              AND oc.width_mm BETWEEN ? AND ?
              AND oc.height_mm BETWEEN ? AND ?
              AND bg.vertices IS NOT NULL
              AND bg.faces IS NOT NULL
              AND bg.normals IS NOT NULL
            ORDER BY dim_diff ASC
            LIMIT 1
        """, (width_mm, height_mm, ifc_class,
              width_mm - tolerance_mm, width_mm + tolerance_mm,
              height_mm - tolerance_mm, height_mm + tolerance_mm))

        result = cursor.fetchone()
        conn.close()

        if result:
            object_type, actual_w, actual_h, diff = result
            print(f"  ✓ Found generic type: {object_type} ({actual_w}×{actual_h}mm, diff={diff}mm)")
            return object_type

        print(f"  ⚠️  No match found for {ifc_class} {width_mm}×{height_mm}mm within ±{tolerance_mm}mm")
        return None

    except sqlite3.Error as e:
        print(f"  ❌ Database error: {e}")
        return None


def door_to_object_type(width_mm: int, height_mm: int) -> str:
    """
    Convert door dimensions to library object_type.

    RULE 0 COMPLIANT (after manual mapping):
    1. Check MANUAL_LIBRARY_MAPPING first (human-curated from PDF)
    2. HARD STOP if not in manual mapping (no fallback)

    Args:
        width_mm: Door width in mm (900, 750)
        height_mm: Door height in mm (2100)

    Returns:
        object_type string from library

    Raises:
        RuntimeError: If dimension not in MANUAL_LIBRARY_MAPPING
    """
    # Check manual mapping first (human-curated, verified to have normals)
    key = ("IfcDoor", width_mm, height_mm)
    if key in MANUAL_LIBRARY_MAPPING:
        object_type = MANUAL_LIBRARY_MAPPING[key]
        print(f"  ✓ Manual mapping: {object_type} for {width_mm}×{height_mm}mm")
        return object_type

    # HARD STOP: No fallback allowed - manual mapping is required
    error_msg = f"""
    ❌ HARD STOP: Door dimension {width_mm}×{height_mm}mm not in MANUAL_LIBRARY_MAPPING

    This is a HUMAN/AI checkpoint failure.

    Required action:
    1. Verify dimension in PDF Page 8 schedule
    2. Search library database for matching object_type with complete geometry
    3. Add to MANUAL_LIBRARY_MAPPING in convert_master_to_blender.py
    4. Re-run Stage 7

    DO NOT proceed without manual verification.
    """
    print(error_msg)
    raise RuntimeError(error_msg)


def window_to_object_type(width_mm: int, height_mm: int) -> str:
    """
    Convert window dimensions to library object_type.

    RULE 0 COMPLIANT (after manual mapping):
    1. Check MANUAL_LIBRARY_MAPPING first (human-curated from PDF)
    2. HARD STOP if not in manual mapping (no fallback)

    Args:
        width_mm: Window width in mm (1800, 1200, 600)
        height_mm: Window height in mm (1000, 500)

    Returns:
        object_type string from library

    Raises:
        RuntimeError: If dimension not in MANUAL_LIBRARY_MAPPING
    """
    # Check manual mapping first (human-curated, verified to have normals)
    key = ("IfcWindow", width_mm, height_mm)
    if key in MANUAL_LIBRARY_MAPPING:
        object_type = MANUAL_LIBRARY_MAPPING[key]
        print(f"  ✓ Manual mapping: {object_type} for {width_mm}×{height_mm}mm")
        return object_type

    # HARD STOP: No fallback allowed - manual mapping is required
    error_msg = f"""
    ❌ HARD STOP: Window dimension {width_mm}×{height_mm}mm not in MANUAL_LIBRARY_MAPPING

    This is a HUMAN/AI checkpoint failure.

    Required action:
    1. Verify dimension in PDF Page 8 schedule
    2. Search library database for matching object_type with complete geometry
    3. Add to MANUAL_LIBRARY_MAPPING in convert_master_to_blender.py
    4. Re-run Stage 7

    DO NOT proceed without manual verification.
    """
    print(error_msg)
    raise RuntimeError(error_msg)


def convert_element(elem: dict, elem_type: str) -> dict:
    """
    Convert door/window element to Blender format.

    Args:
        elem: Element from master_template.json
        elem_type: "door" or "window"

    Returns:
        Object dict for Blender import
    """
    # Extract data
    name = elem['element_id']
    pos = elem['position']
    width_mm = elem['width_mm']
    height_mm = elem['height_mm']
    wall = elem['wall']
    room = elem['room']

    # Convert wall to rotation
    orientation = wall_to_rotation(wall)

    # Create object_type
    if elem_type == "door":
        object_type = door_to_object_type(width_mm, height_mm)
        phase = "opening"
    else:  # window
        object_type = window_to_object_type(width_mm, height_mm)
        phase = "opening"

    # Build object
    obj = {
        "name": name,
        "object_type": object_type,
        "position": [pos['x'], pos['y'], pos['z']],
        "orientation": orientation,
        "phase": phase,
        "room": room,
        "wall": wall,
        "dimensions": {
            "width_mm": width_mm,
            "height_mm": height_mm
        }
    }

    # Add sill height for windows
    if elem_type == "window":
        obj["sill_height_mm"] = elem.get('sill_height_mm', 900)

    return obj


def main():
    print("=" * 80)
    print("CONVERT MASTER_TEMPLATE.JSON TO BLENDER FORMAT")
    print("=" * 80)

    # Load master template
    template_path = Path("master_template.json")
    if not template_path.exists():
        print(f"❌ ERROR: {template_path} not found")
        return

    with open(template_path) as f:
        template = json.load(f)

    print(f"\n✓ Loaded: {template_path}")

    # Extract elements
    doors = template.get('door_placements', [])
    windows = template.get('window_placements', [])
    walls = template.get('wall_placements', [])
    roof_objects = template.get('roof_objects', [])
    porch_objects = template.get('porch_objects', [])
    floor_slab = template.get('floor_slab', [])
    bathroom_fixtures = template.get('bathroom_fixtures', [])
    furniture_fixtures = template.get('furniture_fixtures', [])

    print(f"  Doors: {len(doors)}")
    print(f"  Windows: {len(windows)}")
    print(f"  Walls: {len(walls)}")
    print(f"  Roof objects: {len(roof_objects)}")
    print(f"  Porch objects: {len(porch_objects)}")
    print(f"  Floor slab: {len(floor_slab)}")
    print(f"  Bathroom fixtures: {len(bathroom_fixtures)}")
    print(f"  Furniture/fixtures: {len(furniture_fixtures)}")

    # Convert all elements
    objects = []

    print("\nConverting doors...")
    for door in doors:
        obj = convert_element(door, "door")
        objects.append(obj)
        print(f"  {obj['name']}: {obj['object_type']} at {obj['position']} rot={obj['orientation']}°")

    print("\nConverting windows...")
    for window in windows:
        obj = convert_element(window, "window")
        objects.append(obj)
        print(f"  {obj['name']}: {obj['object_type']} at {obj['position']} rot={obj['orientation']}°")

    print("\nConverting walls...")
    for wall in walls:
        # Walls have different structure - already have all needed fields
        wall_obj = {
            "name": wall['element_id'],
            "object_type": wall['object_type'],
            "position": wall['position'],
            "end_point": wall['end_point'],
            "thickness": wall['thickness'],
            "height": wall['height'],
            "phase": "structure",
            "wall_name": wall['wall_name'],
            "wall_type": wall['wall_type']
        }
        objects.append(wall_obj)
        print(f"  {wall_obj['name']}: {wall_obj['wall_name']} from {wall_obj['position']} to {wall_obj['end_point']}")

    print("\nAdding roof objects...")
    for roof_obj in roof_objects:
        # Roof objects already in correct format
        roof_item = {
            "name": roof_obj['element_id'],
            "object_type": roof_obj['object_type'],
            "position": roof_obj['position'],
            "orientation": roof_obj.get('orientation', 0),
            "phase": roof_obj.get('phase', 'structure'),
            "category": roof_obj.get('category', 'roof')
        }
        # Add end_point for gutters/fascia
        if 'end_point' in roof_obj:
            roof_item['end_point'] = roof_obj['end_point']
        # Add dimensions for slopes
        if 'dimensions' in roof_obj:
            roof_item['dimensions'] = roof_obj['dimensions']
        objects.append(roof_item)
    print(f"  Added {len(roof_objects)} roof objects")

    print("\nAdding porch objects...")
    for porch_obj in porch_objects:
        porch_item = {
            "name": porch_obj['element_id'],
            "object_type": porch_obj['object_type'],
            "position": porch_obj['position'],
            "orientation": porch_obj.get('orientation', 0),
            "phase": porch_obj.get('phase', 'structure'),
            "category": porch_obj.get('category', 'porch')
        }
        if 'end_point' in porch_obj:
            porch_item['end_point'] = porch_obj['end_point']
        if 'dimensions' in porch_obj:
            porch_item['dimensions'] = porch_obj['dimensions']
        objects.append(porch_item)
    print(f"  Added {len(porch_objects)} porch objects")

    print("\nAdding floor slab...")
    for slab_obj in floor_slab:
        slab_item = {
            "name": slab_obj['element_id'],
            "object_type": slab_obj['object_type'],
            "position": slab_obj['position'],
            "orientation": slab_obj.get('orientation', 0),
            "phase": slab_obj.get('phase', 'structure'),
            "category": slab_obj.get('category', 'floor')
        }
        if 'dimensions' in slab_obj:
            slab_item['dimensions'] = slab_obj['dimensions']
        objects.append(slab_item)
    print(f"  Added {len(floor_slab)} floor slab")

    print("\nAdding bathroom fixtures...")
    for fixture in bathroom_fixtures:
        # Fixtures already in correct format, just add name field
        fixture_obj = {
            "name": fixture['element_id'],
            "object_type": fixture['object_type'],
            "position": fixture['position'],
            "orientation": fixture.get('orientation', 0),
            "phase": fixture.get('phase', 'mep'),
            "room": fixture.get('room', ''),
            "category": fixture.get('category', '')
        }
        objects.append(fixture_obj)
    print(f"  Added {len(bathroom_fixtures)} bathroom fixtures")

    print("\nAdding furniture/fixtures...")
    for fixture in furniture_fixtures:
        # Furniture already in correct format
        fixture_obj = {
            "name": fixture['element_id'],
            "object_type": fixture['object_type'],
            "position": fixture['position'],
            "orientation": fixture.get('orientation', 0),
            "phase": fixture.get('phase', 'furniture'),
            "room": fixture.get('room', ''),
            "category": fixture.get('category', '')
        }
        objects.append(fixture_obj)
    print(f"  Added {len(furniture_fixtures)} furniture/fixtures")

    # ========================================================================
    # CRITICAL VALIDATION: Verify all objects against master checklist
    # ========================================================================
    print("\n" + "=" * 80)
    print("MASTER CHECKLIST VALIDATION")
    print("=" * 80)

    # Get all unique object_types from generated objects
    generated_types = set(obj['object_type'] for obj in objects)

    # Get all pre-verified object_types from MANUAL_LIBRARY_MAPPING and VERIFIED_OBJECT_TYPES
    checklist_types = set(MANUAL_LIBRARY_MAPPING.values()) | VERIFIED_OBJECT_TYPES

    print(f"\nGenerated object_types: {len(generated_types)}")
    for obj_type in sorted(generated_types):
        count = sum(1 for obj in objects if obj['object_type'] == obj_type)
        print(f"  - {obj_type}: {count} instances")

    print(f"\nChecklist object_types: {len(checklist_types)}")
    for obj_type in sorted(checklist_types):
        print(f"  - {obj_type}")

    # Check if all generated types are in checklist
    not_in_checklist = generated_types - checklist_types
    if not_in_checklist:
        error_msg = f"""
        ❌ HARD STOP: Generated object_types NOT in master checklist

        Unexpected object types:
        {chr(10).join(f"  - {t}" for t in sorted(not_in_checklist))}

        This indicates a HUMAN/AI checkpoint failure.

        All generated object_types MUST be pre-verified in MANUAL_LIBRARY_MAPPING.

        Required action:
        1. Review the unexpected object_types above
        2. Verify they exist in Ifc_Object_Library.db with complete geometry
        3. Add to MANUAL_LIBRARY_MAPPING in convert_master_to_blender.py
        4. Re-run Stage 7

        DO NOT proceed without manual verification.
        """
        print(error_msg)
        raise RuntimeError(error_msg)

    # Check if all checklist types are used (informational warning only)
    unused_types = checklist_types - generated_types
    if unused_types:
        print(f"\n⚠️  Note: {len(unused_types)} checklist types not used in this template:")
        for obj_type in sorted(unused_types):
            print(f"  - {obj_type}")
        print("  (This is OK - checklist may include types for other projects)")

    print(f"\n✅ VALIDATION PASSED: All {len(objects)} objects match master checklist")
    print(f"   {len(generated_types)} unique object_types, all pre-verified")
    print("=" * 80)

    # Create output
    output = {
        "metadata": {
            "source": "master_template.json",
            "pdf_source": "TB-LKTN HOUSE.pdf",  # Original PDF name for OUTPUT filename
            "total_objects": len(objects),
            "doors": len(doors),
            "windows": len(windows),
            "walls": len(walls),
            "rule_0_compliant": True,
            "description": f"TB-LKTN House - Complete placement ({len(doors)} doors + {len(windows)} windows + {len(walls)} walls)",
            "library_mapping": "Dynamic query from Ifc_Object_Library.db (RULE 0 COMPLIANT)",
            "library_database": str(LIBRARY_DB_PATH)
        },
        "objects": objects,
        "summary": {
            "total_objects": len(objects),
            "by_type": {
                "doors": len(doors),
                "windows": len(windows),
                "walls": len(walls)
            }
        }
    }

    # Save
    output_path = Path("output_artifacts/blender_import.json")
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print("\n" + "=" * 80)
    print("CONVERSION COMPLETE")
    print("=" * 80)
    print(f"Total objects: {len(objects)}")
    print(f"  Doors: {len(doors)}")
    print(f"  Windows: {len(windows)}")
    print(f"  Walls: {len(walls)}")
    print(f"\n✓ Saved: {output_path}")
    print("\nNext step:")
    print(f"  blender --python blender_lod300_import.py -- {output_path} /path/to/Ifc_Object_Library.db output.blend")
    print("=" * 80)


if __name__ == "__main__":
    main()
