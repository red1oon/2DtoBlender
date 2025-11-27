#!/usr/bin/env python3
"""
Add Gutter Corner Connector to Library
=======================================

Creates a 90-degree gutter corner elbow and adds it to Ifc_Object_Library.db.

Usage:
    python3 add_gutter_corner.py DatabaseFiles/Ifc_Object_Library.db
"""

import sys
import sqlite3
import struct
import math
from pathlib import Path


def compute_face_normal(v0, v1, v2):
    """Compute normal vector for a triangle face."""
    # Edge vectors
    e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
    e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
    # Cross product
    nx = e1[1] * e2[2] - e1[2] * e2[1]
    ny = e1[2] * e2[0] - e1[0] * e2[2]
    nz = e1[0] * e2[1] - e1[1] * e2[0]
    # Normalize
    length = math.sqrt(nx*nx + ny*ny + nz*nz)
    if length > 0:
        return (nx/length, ny/length, nz/length)
    return (0, 0, 1)


def generate_gutter_corner_90():
    """
    Generate 90-degree gutter corner connector (L-shaped elbow).

    Dimensions:
    - Gutter width: 100mm (0.1m)
    - Gutter depth: 80mm (0.08m)
    - Wall thickness: 3mm (0.003m)
    - Each leg length: 150mm (0.15m) from corner

    Returns:
        (vertices, faces, normals)
    """
    # Gutter dimensions (meters)
    width = 0.100      # 100mm wide
    depth = 0.080      # 80mm deep
    wall = 0.003       # 3mm wall thickness
    leg_len = 0.150    # 150mm each leg from corner

    vertices = []
    faces = []

    # SECTION 1: Horizontal gutter (along +X axis, 0 to leg_len)
    # Outer profile (top open, U-shape)
    # Bottom outer
    vertices.extend([
        (0, -width/2, 0),           # 0
        (leg_len, -width/2, 0),     # 1
        (leg_len, width/2, 0),      # 2
        (0, width/2, 0),            # 3
    ])
    # Sides outer
    vertices.extend([
        (0, -width/2, depth),       # 4
        (leg_len, -width/2, depth), # 5
        (leg_len, width/2, depth),  # 6
        (0, width/2, depth),        # 7
    ])

    # Inner profile (hollow inside)
    inner_w = width - 2*wall
    inner_d = depth - wall
    # Bottom inner
    vertices.extend([
        (wall, -inner_w/2, wall),           # 8
        (leg_len-wall, -inner_w/2, wall),   # 9
        (leg_len-wall, inner_w/2, wall),    # 10
        (wall, inner_w/2, wall),            # 11
    ])
    # Sides inner
    vertices.extend([
        (wall, -inner_w/2, inner_d),        # 12
        (leg_len-wall, -inner_w/2, inner_d),# 13
        (leg_len-wall, inner_w/2, inner_d), # 14
        (wall, inner_w/2, inner_d),         # 15
    ])

    # Faces for horizontal section
    # Outer surfaces
    faces.extend([
        # Bottom
        (0, 1, 2), (0, 2, 3),
        # Left side
        (0, 4, 5), (0, 5, 1),
        # Right side
        (3, 2, 6), (3, 6, 7),
        # Front end
        (1, 5, 6), (1, 6, 2),
    ])
    # Inner surfaces
    faces.extend([
        # Bottom inner
        (8, 10, 9), (8, 11, 10),
        # Left side inner
        (8, 9, 13), (8, 13, 12),
        # Right side inner
        (11, 14, 10), (11, 15, 14),
        # Front end inner
        (9, 10, 14), (9, 14, 13),
    ])
    # Connect outer to inner (wall thickness)
    faces.extend([
        # Left wall
        (0, 12, 4), (0, 8, 12),
        # Right wall
        (3, 7, 15), (3, 15, 11),
        # Bottom wall at back
        (0, 3, 11), (0, 11, 8),
    ])

    # SECTION 2: Vertical gutter (along +Y axis, 0 to leg_len)
    base = len(vertices)
    # Outer profile
    vertices.extend([
        (0, 0, 0),              # 16
        (0, leg_len, 0),        # 17
        (-width, leg_len, 0),   # 18
        (-width, 0, 0),         # 19
    ])
    vertices.extend([
        (0, 0, depth),          # 20
        (0, leg_len, depth),    # 21
        (-width, leg_len, depth),# 22
        (-width, 0, depth),     # 23
    ])

    # Inner profile
    vertices.extend([
        (-wall, wall, wall),            # 24
        (-wall, leg_len-wall, wall),    # 25
        (-width+wall, leg_len-wall, wall),# 26
        (-width+wall, wall, wall),      # 27
    ])
    vertices.extend([
        (-wall, wall, inner_d),         # 28
        (-wall, leg_len-wall, inner_d), # 29
        (-width+wall, leg_len-wall, inner_d),# 30
        (-width+wall, wall, inner_d),   # 31
    ])

    # Faces for vertical section
    # Outer surfaces
    faces.extend([
        # Bottom
        (16, 18, 17), (16, 19, 18),
        # Front side
        (16, 17, 21), (16, 21, 20),
        # Back side
        (19, 23, 22), (19, 22, 18),
        # Far end
        (17, 18, 22), (17, 22, 21),
    ])
    # Inner surfaces
    faces.extend([
        # Bottom inner
        (24, 25, 26), (24, 26, 27),
        # Front side inner
        (24, 28, 29), (24, 29, 25),
        # Back side inner
        (27, 26, 30), (27, 30, 31),
        # Far end inner
        (25, 29, 30), (25, 30, 26),
    ])
    # Connect outer to inner
    faces.extend([
        # Front wall
        (16, 20, 28), (16, 28, 24),
        # Back wall
        (19, 27, 31), (19, 31, 23),
        # Bottom wall at corner
        (16, 24, 27), (16, 27, 19),
    ])

    # CORNER JUNCTION: Connect the two sections
    # Bridge between horizontal and vertical gutters at origin
    # (simplified - just close the gap)
    faces.extend([
        # Connect horizontal start to vertical start
        (0, 16, 20), (0, 20, 4),
        (3, 7, 23), (3, 23, 19),
    ])

    # Compute normals
    normals = []
    for face in faces:
        v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
        normals.append(compute_face_normal(v0, v1, v2))

    return (vertices, faces, normals)


def add_to_library(db_path):
    """Add gutter corner to library database."""

    print(f"Generating gutter corner geometry...")
    vertices, faces, normals = generate_gutter_corner_90()

    print(f"  Generated: {len(vertices)} vertices, {len(faces)} faces")

    # Pack binary blobs
    vertices_blob = struct.pack(f'<{len(vertices)*3}f',
                                *[c for v in vertices for c in v])
    faces_blob = struct.pack(f'<{len(faces)*3}I',
                            *[idx for f in faces for idx in f])
    normals_blob = struct.pack(f'<{len(normals)*3}f',
                              *[c for n in normals for c in n])

    # Compute hash (simple checksum)
    geometry_hash = f"gutter_corner_90_{len(vertices)}v_{len(faces)}f"

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if already exists
    cursor.execute("""
        SELECT COUNT(*) FROM object_catalog
        WHERE object_type = 'roof_gutter_corner_90_lod300'
    """)
    if cursor.fetchone()[0] > 0:
        print("  ⚠️  Object already exists in library. Skipping.")
        conn.close()
        return

    # Add to base_geometries
    cursor.execute("""
        INSERT INTO base_geometries (
            geometry_hash, vertices, faces, normals,
            vertex_count, face_count
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (geometry_hash, vertices_blob, faces_blob, normals_blob,
          len(vertices), len(faces)))

    # Add to object_catalog
    cursor.execute("""
        INSERT INTO object_catalog (
            object_type, object_name, ifc_class, category, sub_category,
            width_mm, depth_mm, height_mm, description,
            geometry_hash, construction_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'roof_gutter_corner_90_lod300',
        'Roof Gutter Corner 90°',
        'IfcPipeFitting',
        'Drainage',
        'Roof_Drainage',
        100,  # width_mm
        100,  # depth_mm
        80,   # height_mm (depth of gutter)
        '90-degree gutter corner elbow connector for perimeter drainage (MS 1229 compliant)',
        geometry_hash,
        'universal'
    ))

    conn.commit()
    conn.close()

    print(f"✅ Added 'roof_gutter_corner_90_lod300' to library")
    print(f"   IFC Class: IfcPipeFitting")
    print(f"   Dimensions: 100mm x 100mm x 80mm")
    print(f"   Geometry: {len(vertices)} vertices, {len(faces)} faces")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 add_gutter_corner.py <path_to_Ifc_Object_Library.db>")
        sys.exit(1)

    db_path = sys.argv[1]
    if not Path(db_path).exists():
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)

    add_to_library(db_path)
    print("\n✅ Gutter corner connector added successfully!")
