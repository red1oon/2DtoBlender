#!/usr/bin/env python3
"""
Fix 5 Missing/Corrupted LOD300 Objects

Strategy: Copy valid geometries from similar objects to the LOD300 versions

Fixes:
1. coffee_table_lod300 → use geometry from coffee_table
2. distribution_board_residential_lod300 → use geometry from distribution_board_residential
3. kitchen_sink_single_bowl_lod300 → use geometry from kitchen_sink_single_bowl
4. showerhead_fixed_lod300 → use geometry from showerhead_fixed
5. floor_mounted_toilet_lod300 → use geometry from asian_toilet_lod300 (already valid LOD300)

Usage:
    python3 fix_missing_5_objects.py <database_path> [--apply]
"""

import sqlite3
import sys

GEOMETRY_MAPPINGS = {
    'coffee_table_lod300': 'coffee_table',
    'distribution_board_residential_lod300': 'distribution_board_residential',
    'kitchen_sink_single_bowl_lod300': 'kitchen_sink_single_bowl',
    'showerhead_fixed_lod300': 'showerhead_fixed',
    'floor_mounted_toilet_lod300': 'asian_toilet_lod300',  # Use valid LOD300 toilet
}

def fix_missing_objects(db_path, apply=False):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=" * 80)
    print("FIXING 5 MISSING/CORRUPTED LOD300 OBJECTS")
    print("=" * 80)

    for target_type, source_type in GEOMETRY_MAPPINGS.items():
        print(f"\n{target_type}:")
        print(f"  Source: {source_type}")

        # Get source geometry hash
        cursor.execute("""
            SELECT bg.geometry_hash, bg.vertex_count, bg.face_count,
                   LENGTH(bg.vertices), LENGTH(bg.faces)
            FROM object_catalog oc
            JOIN base_geometries bg ON oc.geometry_hash = bg.geometry_hash
            WHERE oc.object_type = ?
            LIMIT 1
        """, (source_type,))

        source_row = cursor.fetchone()
        if not source_row:
            print(f"  ❌ ERROR: Source object '{source_type}' not found!")
            continue

        src_hash, v_count, f_count, v_size, f_size = source_row
        expected_f = f_count * 3 * 4

        # Validate source geometry
        if f_size != expected_f:
            print(f"  ❌ ERROR: Source geometry is corrupted! ({f_size}/{expected_f} bytes)")
            continue

        print(f"  ✅ Source geometry valid: {v_count} vertices, {f_count} faces")

        # Check if target already has correct geometry
        cursor.execute("""
            SELECT oc.geometry_hash
            FROM object_catalog oc
            WHERE oc.object_type = ?
        """, (target_type,))

        target_row = cursor.fetchone()
        if target_row and target_row[0] == src_hash:
            print(f"  ✅ Already fixed - geometry_hash matches")
            continue

        # Update object_catalog to point to source geometry_hash
        if apply:
            cursor.execute("""
                UPDATE object_catalog
                SET geometry_hash = ?
                WHERE object_type = ?
            """, (src_hash, target_type))

            rows_updated = cursor.rowcount
            if rows_updated > 0:
                print(f"  ✅ APPLIED: Updated {rows_updated} catalog entry(ies)")
            else:
                print(f"  ⚠️  No catalog entry to update - object_type might not exist")
        else:
            print(f"  ℹ️  Will update geometry_hash to: {src_hash[:16]}...")

    if apply:
        conn.commit()
        print("\n" + "=" * 80)
        print("CHANGES APPLIED")
        print("=" * 80)

        # Verify fixes
        print("\nVERIFYING FIXES:")
        for target_type in GEOMETRY_MAPPINGS.keys():
            cursor.execute("""
                SELECT
                    oc.object_type,
                    CASE WHEN bg.geometry_hash IS NULL THEN 'MISSING'
                         WHEN LENGTH(bg.faces) != bg.face_count * 3 * 4 THEN 'CORRUPTED'
                         ELSE 'VALID' END as status
                FROM object_catalog oc
                LEFT JOIN base_geometries bg ON oc.geometry_hash = bg.geometry_hash
                WHERE oc.object_type = ?
            """, (target_type,))

            row = cursor.fetchone()
            if row:
                obj_type, status = row
                icon = "✅" if status == "VALID" else "❌"
                print(f"  {icon} {obj_type}: {status}")
    else:
        print("\n" + "=" * 80)
        print("DRY RUN - No changes made")
        print("Run with --apply to apply fixes")
        print("=" * 80)

    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    db_path = sys.argv[1]
    apply = "--apply" in sys.argv

    fix_missing_objects(db_path, apply)
