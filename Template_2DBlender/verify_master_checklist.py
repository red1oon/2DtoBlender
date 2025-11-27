#!/usr/bin/env python3
"""
Master Checklist Verification Script
=====================================
Verifies ALL object_types against Ifc_Object_Library.db to create
an immutable master checklist for OUTPUT JSON resolution.

This ensures no fetching errors occur during Blender import.
"""

import sqlite3
import json
import sys
from pathlib import Path

# Database path
LIBRARY_DB = Path(__file__).parent / "LocalLibrary/Ifc_Object_Library.db"

# Sources to verify
MASTER_REFERENCE_TEMPLATE = "master_reference_template.json"
CONVERT_SCRIPT_TYPES = {
    # From MANUAL_LIBRARY_MAPPING
    "door_single_900_lod300",
    "door_single_750x2100_lod300",
    "window_aluminum_3panel_1800x1000",
    "window_aluminum_2panel_1200x1000",
    "window_aluminum_tophung_600x500",
    "wall_brick_cavity_250_lod300",

    # From VERIFIED_OBJECT_TYPES
    "basin_residential_lod300",
    "floor_mounted_toilet_lod300",
    "shower_enclosure_900",
    "showerhead_fixed_lod200",
    "electrical_outlet_weatherproof",
    "electrical_switch_weatherproof",
    "kitchen_sink_single_bowl_lod200",
    "kitchen_base_cabinet_900_lod300",
    "electrical_outlet_double",
    "electrical_switch_dimmer",
    "bed_queen_lod300",
    "furniture_wardrobe",
    "sofa_2seater_lod300",
    "coffee_table",
    "ict_tv_point",
    "dining_table_6seat",
    "roof_tile_9.7x7_lod300",
    "roof_gutter_100_lod300",
    "roof_fascia_200_lod300",
    "wall_lightweight_75_lod300",
    "roof_slab_flat_lod300",
}


def verify_object_type(cursor, object_type: str) -> dict:
    """
    Verify object_type exists in library with complete geometry.

    Returns:
        dict with keys: exists, has_vertices, has_faces, has_normals, dimensions
    """
    query = """
    SELECT
        oc.object_type,
        oc.ifc_class,
        oc.width_mm,
        oc.depth_mm,
        oc.height_mm,
        LENGTH(bg.vertices) as v_bytes,
        LENGTH(bg.faces) as f_bytes,
        LENGTH(bg.normals) as n_bytes
    FROM object_catalog oc
    LEFT JOIN base_geometries bg ON oc.geometry_hash = bg.geometry_hash
    WHERE oc.object_type = ?
    """

    cursor.execute(query, (object_type,))
    row = cursor.fetchone()

    if not row:
        return {
            "exists": False,
            "has_vertices": False,
            "has_faces": False,
            "has_normals": False,
            "dimensions": None,
            "ifc_class": None
        }

    return {
        "exists": True,
        "ifc_class": row[1],
        "has_vertices": row[5] is not None and row[5] > 0,
        "has_faces": row[6] is not None and row[6] > 0,
        "has_normals": row[7] is not None and row[7] > 0,
        "dimensions": {
            "width_mm": row[2],
            "depth_mm": row[3],
            "height_mm": row[4]
        },
        "geometry_bytes": {
            "vertices": row[5] or 0,
            "faces": row[6] or 0,
            "normals": row[7] or 0
        }
    }


def main():
    print("=" * 80)
    print("MASTER CHECKLIST VERIFICATION")
    print("=" * 80)
    print()

    # Connect to library
    if not LIBRARY_DB.exists():
        print(f"❌ ERROR: Library database not found at {LIBRARY_DB}")
        sys.exit(1)

    conn = sqlite3.connect(str(LIBRARY_DB))
    cursor = conn.cursor()

    # Load master_reference_template.json
    with open(MASTER_REFERENCE_TEMPLATE, 'r') as f:
        master_ref = json.load(f)

    master_ref_types = set()
    for item in master_ref['extraction_sequence']:
        obj_type = item.get('object_type')
        if obj_type:
            master_ref_types.add(obj_type)

    print(f"📋 Master Reference Template: {len(master_ref_types)} object types")
    print(f"📋 Convert Script Types: {len(CONVERT_SCRIPT_TYPES)} object types")
    print()

    # Combine all types
    all_types = master_ref_types | CONVERT_SCRIPT_TYPES
    print(f"📋 TOTAL UNIQUE TYPES: {len(all_types)}")
    print()

    # Verify each type
    verified = []
    missing = []
    incomplete = []

    print("Verifying...")
    print("-" * 80)

    for obj_type in sorted(all_types):
        result = verify_object_type(cursor, obj_type)

        status = "✅"
        notes = []

        if not result['exists']:
            status = "❌ MISSING"
            missing.append(obj_type)
            notes.append("NOT FOUND")
        elif not result['has_vertices'] or not result['has_faces']:
            status = "⚠️ INCOMPLETE"
            incomplete.append(obj_type)
            notes.append("NO GEOMETRY")
        elif not result['has_normals']:
            status = "⚠️ WARNING"
            notes.append("NO NORMALS")
        else:
            verified.append({
                "object_type": obj_type,
                "ifc_class": result['ifc_class'],
                "dimensions": result['dimensions'],
                "geometry_bytes": result['geometry_bytes']
            })

        # Determine source
        in_master = obj_type in master_ref_types
        in_convert = obj_type in CONVERT_SCRIPT_TYPES

        source_tags = []
        if in_master:
            source_tags.append("MASTER_REF")
        if in_convert:
            source_tags.append("CONVERT_SCRIPT")

        source = " + ".join(source_tags)

        print(f"{status:15} {obj_type:50} [{source}] {' '.join(notes)}")

    print("-" * 80)
    print()

    # Summary
    print("SUMMARY:")
    print(f"  ✅ Verified: {len(verified)}")
    print(f"  ❌ Missing: {len(missing)}")
    print(f"  ⚠️ Incomplete: {len(incomplete)}")
    print()

    if missing:
        print("MISSING OBJECTS (need to be added to library or removed from checklist):")
        for obj in missing:
            print(f"  - {obj}")
        print()

    if incomplete:
        print("INCOMPLETE OBJECTS (missing geometry):")
        for obj in incomplete:
            print(f"  - {obj}")
        print()

    # Save verified checklist
    output = {
        "_description": "IMMUTABLE MASTER CHECKLIST - All object_types verified in library",
        "_purpose": "Single source of truth for OUTPUT JSON resolution - prevents fetching errors",
        "_verification_date": "2025-11-26",
        "_verification_source": "verify_master_checklist.py",
        "_total_verified": len(verified),
        "verified_object_types": verified
    }

    output_file = "output_artifacts/MASTER_CHECKLIST_VERIFIED.json"
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"✅ Verified checklist saved to: {output_file}")
    print()

    # Exit code
    if missing or incomplete:
        print("⚠️ WARNING: Some object types are missing or incomplete.")
        print("   Review and update master_reference_template.json or library database.")
        sys.exit(1)
    else:
        print("✅ ALL OBJECT TYPES VERIFIED SUCCESSFULLY")
        sys.exit(0)

    conn.close()


if __name__ == "__main__":
    main()
