#!/usr/bin/env python3
"""
Compute normals for geometry that has vertices/faces but missing normals.
"""

import sqlite3
import struct
from pathlib import Path

def compute_face_normal(v0, v1, v2):
    """Compute normal for a triangle face using cross product"""
    # Edge vectors
    e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
    e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])

    # Cross product
    nx = e1[1] * e2[2] - e1[2] * e2[1]
    ny = e1[2] * e2[0] - e1[0] * e2[2]
    nz = e1[0] * e2[1] - e1[1] * e2[0]

    # Normalize
    length = (nx*nx + ny*ny + nz*nz) ** 0.5
    if length > 0:
        nx, ny, nz = nx/length, ny/length, nz/length

    return (nx, ny, nz)

def compute_normals_for_geometry(geometry_hash: str, vertices_blob: bytes, faces_blob: bytes) -> bytes:
    """Compute normals from vertices and faces"""

    # Unpack vertices
    n_floats = len(vertices_blob) // 4
    vertices = struct.unpack(f'<{n_floats}f', vertices_blob)

    # Unpack faces (indices)
    n_indices = len(faces_blob) // 4
    faces = struct.unpack(f'<{n_indices}I', faces_blob)

    # Compute normals for each triangle
    normals = []
    for i in range(0, len(faces), 3):
        i0, i1, i2 = faces[i], faces[i+1], faces[i+2]

        v0 = (vertices[i0*3], vertices[i0*3+1], vertices[i0*3+2])
        v1 = (vertices[i1*3], vertices[i1*3+1], vertices[i1*3+2])
        v2 = (vertices[i2*3], vertices[i2*3+1], vertices[i2*3+2])

        nx, ny, nz = compute_face_normal(v0, v1, v2)

        # Each vertex gets the face normal
        normals.extend([nx, ny, nz, nx, ny, nz, nx, ny, nz])

    # Pack as binary
    return struct.pack(f'<{len(normals)}f', *normals)

def fix_missing_normals(db_path: Path):
    """Find and fix geometry with missing normals"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=" * 80)
    print("COMPUTING MISSING NORMALS")
    print("=" * 80)
    print()

    # Find geometry with vertices/faces but no normals
    cursor.execute("""
        SELECT geometry_hash, vertices, faces
        FROM base_geometries
        WHERE vertices IS NOT NULL
          AND faces IS NOT NULL
          AND normals IS NULL
    """)

    rows = cursor.fetchall()

    print(f"Found {len(rows)} geometries missing normals")
    print()

    fixed = []
    errors = []

    for geometry_hash, vertices, faces in rows:
        try:
            normals = compute_normals_for_geometry(geometry_hash, vertices, faces)

            cursor.execute("""
                UPDATE base_geometries
                SET normals = ?
                WHERE geometry_hash = ?
            """, (normals, geometry_hash))

            # Get object types using this geometry
            cursor.execute("""
                SELECT object_type FROM object_catalog
                WHERE geometry_hash = ?
            """, (geometry_hash,))

            object_types = [row[0] for row in cursor.fetchall()]

            fixed.append(f"{geometry_hash[:8]}... ({', '.join(object_types[:3])})")

        except Exception as e:
            errors.append(f"{geometry_hash[:8]}... (error: {e})")

    conn.commit()
    conn.close()

    print(f"✅ Fixed: {len(fixed)} geometries")
    for item in fixed:
        print(f"   ✓ {item}")

    if errors:
        print(f"\n❌ Errors: {len(errors)}")
        for item in errors:
            print(f"   ✗ {item}")

    print()
    print("=" * 80)
    print(f"SUMMARY: {len(fixed)} fixed, {len(errors)} errors")
    print("=" * 80)

if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "LocalLibrary/Ifc_Object_Library.db"

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        exit(1)

    fix_missing_normals(db_path)
