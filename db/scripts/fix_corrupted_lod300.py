#!/usr/bin/env python3
"""
Quick Fix for 2 Corrupted LOD300 Objects

Fixes:
1. table_study_lod300: Update face_count from 30 to 40 (blob is correct, count is wrong)
2. floor_mounted_toilet_lod300: Needs manual re-extraction (2/3 of face data missing)

Usage:
    python3 fix_corrupted_lod300.py <database_path> [--apply]
"""

import sqlite3
import sys

def analyze_and_fix(db_path, apply=False):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=" * 80)
    print("ANALYZING CORRUPTED LOD300 OBJECTS")
    print("=" * 80)

    # Check table_study_lod300
    print("\n1. table_study_lod300:")
    cursor.execute("""
        SELECT bg.geometry_hash, bg.face_count, LENGTH(bg.faces) as f_bytes
        FROM base_geometries bg
        JOIN object_catalog oc ON bg.geometry_hash = oc.geometry_hash
        WHERE oc.object_type = 'table_study_lod300'
    """)
    row = cursor.fetchone()
    if row:
        hash, face_count, f_bytes = row
        actual_faces = (f_bytes // 4) // 3  # uint32 count / 3
        print(f"   Current face_count: {face_count}")
        print(f"   Faces in blob: {actual_faces} (calculated from {f_bytes} bytes)")

        if actual_faces == 40 and face_count == 30:
            print(f"   ✅ FIX AVAILABLE: Update face_count to {actual_faces}")
            if apply:
                cursor.execute("""
                    UPDATE base_geometries
                    SET face_count = ?
                    WHERE geometry_hash = ?
                """, (actual_faces, hash))
                print(f"   ✅ APPLIED: face_count updated to {actual_faces}")
            else:
                print(f"   ℹ️  Run with --apply to fix")
        else:
            print(f"   ⚠️  Unexpected values - manual check needed")

    # Check floor_mounted_toilet_lod300
    print("\n2. floor_mounted_toilet_lod300:")
    cursor.execute("""
        SELECT bg.geometry_hash, bg.face_count, LENGTH(bg.faces) as f_bytes
        FROM base_geometries bg
        JOIN object_catalog oc ON bg.geometry_hash = oc.geometry_hash
        WHERE oc.object_type = 'floor_mounted_toilet_lod300'
    """)
    row = cursor.fetchone()
    if row:
        hash, face_count, f_bytes = row
        expected_bytes = face_count * 3 * 4
        print(f"   face_count: {face_count} faces")
        print(f"   Expected blob: {expected_bytes} bytes")
        print(f"   Actual blob: {f_bytes} bytes")
        print(f"   Missing: {expected_bytes - f_bytes} bytes ({100 * (expected_bytes - f_bytes) / expected_bytes:.1f}%)")
        print(f"   ❌ CANNOT AUTO-FIX: Requires re-extraction from source IFC")
        print(f"   Recommendation: Re-generate geometry from IFC or use fallback")

    if apply:
        conn.commit()
        print("\n" + "=" * 80)
        print("CHANGES APPLIED")
        print("=" * 80)
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

    analyze_and_fix(db_path, apply)
