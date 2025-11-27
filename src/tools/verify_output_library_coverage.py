#!/usr/bin/env python3
"""
Verify that all object_types in output JSON exist in LocalLibrary
"""

import json
import sqlite3
from pathlib import Path

def verify_library_coverage(output_json_path, library_db_path):
    """Check if all object_types in output exist in library"""

    # Load output JSON
    with open(output_json_path) as f:
        data = json.load(f)

    # Get unique object types
    object_types = set()
    for obj in data.get('objects', []):
        if 'object_type' in obj:
            object_types.add(obj['object_type'])

    # Connect to library
    conn = sqlite3.connect(library_db_path)
    cursor = conn.cursor()

    print("=" * 80)
    print("LIBRARY COVERAGE VERIFICATION")
    print("=" * 80)
    print()
    print(f"Output JSON: {output_json_path}")
    print(f"Library DB: {library_db_path}")
    print(f"Total unique object_types: {len(object_types)}")
    print()

    found = []
    missing = []
    no_normals = []

    for obj_type in sorted(object_types):
        # Check if exists
        cursor.execute("""
            SELECT oc.object_type,
                   CASE WHEN bg.normals IS NOT NULL THEN 1 ELSE 0 END as has_normals
            FROM object_catalog oc
            LEFT JOIN base_geometries bg ON oc.geometry_hash = bg.geometry_hash
            WHERE oc.object_type = ?
            LIMIT 1
        """, (obj_type,))

        row = cursor.fetchone()

        if row:
            if row[1]:  # has normals
                found.append(obj_type)
                print(f"✅ {obj_type}")
            else:
                no_normals.append(obj_type)
                print(f"⚠️  {obj_type} (NO NORMALS)")
        else:
            missing.append(obj_type)
            print(f"❌ {obj_type} (NOT FOUND)")

    conn.close()

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Found with normals: {len(found)}/{len(object_types)}")
    print(f"⚠️  Found without normals: {len(no_normals)}/{len(object_types)}")
    print(f"❌ Missing: {len(missing)}/{len(object_types)}")
    print()

    if missing:
        print("MISSING OBJECTS:")
        for obj_type in missing:
            print(f"  - {obj_type}")
        print()

    if no_normals:
        print("OBJECTS WITHOUT NORMALS:")
        for obj_type in no_normals:
            print(f"  - {obj_type}")
        print()

    # Calculate coverage
    coverage = (len(found) / len(object_types)) * 100 if object_types else 0

    if coverage == 100:
        print("✅ 100% LIBRARY COVERAGE - ALL OBJECTS READY FOR BLENDER")
    else:
        print(f"⚠️  {coverage:.1f}% LIBRARY COVERAGE - SOME OBJECTS MISSING/INCOMPLETE")

    return len(missing) == 0 and len(no_normals) == 0


if __name__ == "__main__":
    import sys

    script_dir = Path(__file__).parent.parent

    if len(sys.argv) >= 2:
        output_path = Path(sys.argv[1])
    else:
        output_path = script_dir / "output_artifacts/TB-LKTN_HOUSE_OUTPUT_20251127_094224_FINAL.json"

    library_path = script_dir / "LocalLibrary/Ifc_Object_Library.db"

    if not output_path.exists():
        print(f"❌ Output JSON not found: {output_path}")
        sys.exit(1)

    if not library_path.exists():
        print(f"❌ Library DB not found: {library_path}")
        sys.exit(1)

    success = verify_library_coverage(output_path, library_path)
    sys.exit(0 if success else 1)
