#!/usr/bin/env python3
"""
Fix Bed Geometry Centering - One-time Database Fix
Re-centers bed geometries at origin to fix furniture bunching issue
"""

import sqlite3
import struct
import numpy as np
import sys

def recenter_geometry(db_path, object_types):
    """
    Re-center geometry vertices at origin

    Args:
        db_path: Path to Ifc_Object_Library.db
        object_types: List of object_type strings to re-center
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print(f"🔧 Re-centering {len(object_types)} geometry types...\n")

    for obj_type in object_types:
        # Get geometry_hash from object_catalog
        cur.execute("""
            SELECT geometry_hash
            FROM object_catalog
            WHERE object_type = ?
            LIMIT 1
        """, (obj_type,))

        row = cur.fetchone()
        if not row:
            print(f"❌ {obj_type}: Not found in object_catalog")
            continue

        geometry_hash = row[0]

        # Get vertices BLOB from base_geometries
        cur.execute("""
            SELECT vertices, faces, normals
            FROM base_geometries
            WHERE geometry_hash = ?
        """, (geometry_hash,))

        geo_row = cur.fetchone()
        if not geo_row:
            print(f"❌ {obj_type}: Geometry hash {geometry_hash} not found")
            continue

        vertices_blob, faces_blob, normals_blob = geo_row

        # Parse vertices blob (float32 array: [x1,y1,z1, x2,y2,z2, ...])
        float_count = len(vertices_blob) // 4
        floats = struct.unpack(f'<{float_count}f', vertices_blob)
        verts = np.array(floats).reshape(-1, 3)

        # Calculate center
        center = verts.mean(axis=0)
        offset_magnitude = np.linalg.norm(center)

        print(f"📦 {obj_type}:")
        print(f"   Vertices: {len(verts)}")
        print(f"   Current center: [{center[0]:.3f}, {center[1]:.3f}, {center[2]:.3f}]")
        print(f"   Offset magnitude: {offset_magnitude:.3f}m")

        if offset_magnitude < 0.01:
            print(f"   ✅ Already centered (offset < 0.01m)")
            continue

        # Re-center vertices
        verts_centered = verts - center

        # Verify centering
        new_center = verts_centered.mean(axis=0)
        print(f"   New center: [{new_center[0]:.6f}, {new_center[1]:.6f}, {new_center[2]:.6f}]")

        # Repack vertices blob
        new_vertices_blob = verts_centered.astype(np.float32).tobytes()

        # Update database
        cur.execute("""
            UPDATE base_geometries
            SET vertices = ?
            WHERE geometry_hash = ?
        """, (new_vertices_blob, geometry_hash))

        print(f"   ✅ Re-centered: shifted by [{center[0]:.3f}, {center[1]:.3f}, {center[2]:.3f}]")
        print()

    conn.commit()
    conn.close()
    print("✅ Database updated - all geometries re-centered")


if __name__ == "__main__":
    db_path = "LocalLibrary/Ifc_Object_Library.db"

    # Bed geometries identified as offset
    bed_types = [
        'bed_double_lod300',
        'bed_queen_lod300'
    ]

    print("=" * 60)
    print("BED GEOMETRY RE-CENTERING SCRIPT")
    print("=" * 60)
    print(f"Database: {db_path}")
    print(f"Targets: {', '.join(bed_types)}")
    print()

    response = input("Proceed with re-centering? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Aborted")
        sys.exit(0)

    print()
    recenter_geometry(db_path, bed_types)

    print("\n" + "=" * 60)
    print("✅ FIX COMPLETE")
    print("=" * 60)
    print("Next steps:")
    print("1. Run Blender import again")
    print("2. Verify furniture is properly spaced")
    print("3. Take screenshot to confirm all 3 issues fixed")
