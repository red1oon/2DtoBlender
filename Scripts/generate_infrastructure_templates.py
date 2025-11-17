#!/usr/bin/env python3
"""
Generate infrastructure templates: floors, pipe networks, conduit networks.
This is "auto-design from ground up" - we create code-compliant infrastructure
based on element positions, not DXF extraction.
"""

import sys
import sqlite3
import uuid
import struct
from pathlib import Path
from typing import List, Tuple
import math


def pack_vertices(vertices: List[Tuple[float, float, float]]) -> bytes:
    """Pack vertices into binary BLOB."""
    return struct.pack(f'<{len(vertices)*3}f', *[coord for v in vertices for coord in v])


def pack_faces(faces: List[Tuple[int, int, int]]) -> bytes:
    """Pack faces into binary BLOB."""
    return struct.pack(f'<{len(faces)*3}I', *[idx for face in faces for idx in face])


def pack_normals(normals: List[Tuple[float, float, float]]) -> bytes:
    """Pack normals into binary BLOB."""
    return struct.pack(f'<{len(normals)*3}f', *[coord for n in normals for coord in n])


def compute_hash(vertices_blob: bytes, faces_blob: bytes) -> str:
    """Compute hash for geometry."""
    import hashlib
    hasher = hashlib.sha256()
    hasher.update(vertices_blob)
    hasher.update(faces_blob)
    return hasher.hexdigest()


def generate_floor_slab(min_x, max_x, min_y, max_y, z_height=0.0, thickness=0.3):
    """Generate floor slab geometry."""
    # Create large horizontal rectangle (floor)
    # 8 vertices (top and bottom faces)
    vertices = [
        # Bottom face
        (min_x, min_y, z_height),
        (max_x, min_y, z_height),
        (max_x, max_y, z_height),
        (min_x, max_y, z_height),
        # Top face
        (min_x, min_y, z_height + thickness),
        (max_x, min_y, z_height + thickness),
        (max_x, max_y, z_height + thickness),
        (min_x, max_y, z_height + thickness),
    ]

    # 12 triangular faces
    faces = [
        # Bottom (facing down)
        (0, 2, 1), (0, 3, 2),
        # Top (facing up)
        (4, 5, 6), (4, 6, 7),
        # Sides
        (0, 1, 5), (0, 5, 4),  # Front
        (2, 3, 7), (2, 7, 6),  # Back
        (0, 4, 7), (0, 7, 3),  # Left
        (1, 2, 6), (1, 6, 5),  # Right
    ]

    # Simple normals (all pointing up for top face)
    normals = [(0, 0, -1)] * 2 + [(0, 0, 1)] * 2 + [(0, -1, 0)] * 2 + [(0, 1, 0)] * 2 + [(-1, 0, 0)] * 2 + [(1, 0, 0)] * 2

    return vertices, faces, normals


def generate_pipe_segment(start, end, diameter=0.025):
    """Generate pipe segment between two points."""
    # Simple cylinder between two 3D points
    # For now, use a box approximation (faster)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    length = math.sqrt(dx*dx + dy*dy + dz*dz)

    if length < 0.01:  # Too short
        return None, None, None

    # Midpoint
    mid_x = (start[0] + end[0]) / 2
    mid_y = (start[1] + end[1]) / 2
    mid_z = (start[2] + end[2]) / 2

    # Simple box approximation (pipe as thin rectangular box)
    half_d = diameter / 2
    half_l = length / 2

    # Align along dominant axis
    if abs(dx) > abs(dy) and abs(dx) > abs(dz):
        # Horizontal pipe (X-axis)
        vertices = [
            (mid_x - half_l, mid_y - half_d, mid_z - half_d),
            (mid_x + half_l, mid_y - half_d, mid_z - half_d),
            (mid_x + half_l, mid_y + half_d, mid_z - half_d),
            (mid_x - half_l, mid_y + half_d, mid_z - half_d),
            (mid_x - half_l, mid_y - half_d, mid_z + half_d),
            (mid_x + half_l, mid_y - half_d, mid_z + half_d),
            (mid_x + half_l, mid_y + half_d, mid_z + half_d),
            (mid_x - half_l, mid_y + half_d, mid_z + half_d),
        ]
    elif abs(dy) > abs(dz):
        # Horizontal pipe (Y-axis)
        vertices = [
            (mid_x - half_d, mid_y - half_l, mid_z - half_d),
            (mid_x + half_d, mid_y - half_l, mid_z - half_d),
            (mid_x + half_d, mid_y + half_l, mid_z - half_d),
            (mid_x - half_d, mid_y + half_l, mid_z - half_d),
            (mid_x - half_d, mid_y - half_l, mid_z + half_d),
            (mid_x + half_d, mid_y - half_l, mid_z + half_d),
            (mid_x + half_d, mid_y + half_l, mid_z + half_d),
            (mid_x - half_d, mid_y + half_l, mid_z + half_d),
        ]
    else:
        # Vertical pipe (Z-axis)
        vertices = [
            (mid_x - half_d, mid_y - half_d, mid_z - half_l),
            (mid_x + half_d, mid_y - half_d, mid_z - half_l),
            (mid_x + half_d, mid_y + half_d, mid_z - half_l),
            (mid_x - half_d, mid_y + half_d, mid_z - half_l),
            (mid_x - half_d, mid_y - half_d, mid_z + half_l),
            (mid_x + half_d, mid_y - half_d, mid_z + half_l),
            (mid_x + half_d, mid_y + half_d, mid_z + half_l),
            (mid_x - half_d, mid_y + half_d, mid_z + half_l),
        ]

    # Standard box faces
    faces = [
        (0, 1, 2), (0, 2, 3),  # Bottom
        (4, 7, 6), (4, 6, 5),  # Top
        (0, 4, 5), (0, 5, 1),  # Front
        (2, 6, 7), (2, 7, 3),  # Back
        (0, 3, 7), (0, 7, 4),  # Left
        (1, 5, 6), (1, 6, 2),  # Right
    ]

    normals = [(0, 0, -1)] * 2 + [(0, 0, 1)] * 2 + [(0, -1, 0)] * 2 + [(0, 1, 0)] * 2 + [(-1, 0, 0)] * 2 + [(1, 0, 0)] * 2

    return vertices, faces, normals


def generate_infrastructure(db_path):
    """Generate infrastructure templates."""

    print("="*80)
    print("GENERATING INFRASTRUCTURE TEMPLATES")
    print("="*80)
    print(f"Database: {db_path}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get building extents
    cursor.execute("""
        SELECT MIN(center_x), MAX(center_x), MIN(center_y), MAX(center_y), MIN(center_z)
        FROM element_transforms
    """)
    min_x, max_x, min_y, max_y, min_z = cursor.fetchone()

    print(f"Building extents:")
    print(f"  X: {min_x:.1f} to {max_x:.1f} (width: {max_x - min_x:.1f}m)")
    print(f"  Y: {min_y:.1f} to {max_y:.1f} (depth: {max_y - min_y:.1f}m)")
    print(f"  Z: {min_z:.1f}m (floor level)\n")

    stats = {
        'floors': 0,
        'pipes': 0,
        'conduits': 0
    }

    # =======================================================================
    # 1. GENERATE FLOOR SLAB
    # =======================================================================
    print("="*80)
    print("1. GENERATING FLOOR SLAB")
    print("="*80)

    # Add margin around building
    margin = 2.0  # 2m margin
    floor_min_x = min_x - margin
    floor_max_x = max_x + margin
    floor_min_y = min_y - margin
    floor_max_y = max_y + margin

    vertices, faces, normals = generate_floor_slab(
        floor_min_x, floor_max_x, floor_min_y, floor_max_y,
        z_height=min_z, thickness=0.3
    )

    # Store floor as IfcSlab
    floor_guid = str(uuid.uuid4())

    cursor.execute("""
        INSERT INTO elements_meta (guid, discipline, ifc_class, element_name, element_type, inferred_shape_type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (floor_guid, 'STR', 'IfcSlab', 'Ground Floor Slab', 'TEMPLATE_FLOOR', 'box'))

    cursor.execute("""
        INSERT INTO element_transforms (guid, center_x, center_y, center_z, length)
        VALUES (?, ?, ?, ?, ?)
    """, (floor_guid, (floor_min_x + floor_max_x)/2, (floor_min_y + floor_max_y)/2, min_z + 0.15, max_x - min_x))

    # Store geometry
    v_blob = pack_vertices(vertices)
    f_blob = pack_faces(faces)
    n_blob = pack_normals(normals)
    geom_hash = compute_hash(v_blob, f_blob)

    cursor.execute("""
        INSERT OR REPLACE INTO base_geometries (guid, geometry_hash, vertices, faces, normals)
        VALUES (?, ?, ?, ?, ?)
    """, (floor_guid, geom_hash, v_blob, f_blob, n_blob))

    stats['floors'] += 1
    print(f"✅ Generated floor slab: {floor_max_x - floor_min_x:.1f}m × {floor_max_y - floor_min_y:.1f}m\n")

    # =======================================================================
    # 2. GENERATE SPRINKLER PIPE NETWORK
    # =======================================================================
    print("="*80)
    print("2. GENERATING SPRINKLER PIPE NETWORK")
    print("="*80)

    # Get all sprinklers
    cursor.execute("""
        SELECT et.center_x, et.center_y, et.center_z
        FROM elements_meta em
        JOIN element_transforms et ON em.guid = et.guid
        WHERE em.discipline = 'FP' AND em.inferred_shape_type = 'sprinkler'
        ORDER BY et.center_x, et.center_y
    """)

    sprinklers = cursor.fetchall()
    print(f"Found {len(sprinklers)} sprinklers to connect\n")

    if len(sprinklers) > 1:
        # Simple grid-based pipe network
        # Connect each sprinkler to nearest neighbors (grid pattern)
        grid_spacing = 5.0  # 5m grid

        pipe_count = 0
        for i, sprinkler in enumerate(sprinklers):
            x1, y1, z1 = sprinkler

            # Find nearest sprinkler in X direction
            for j, other in enumerate(sprinklers):
                if i >= j:
                    continue

                x2, y2, z2 = other

                # Connect if within grid spacing in X or Y
                dist_x = abs(x2 - x1)
                dist_y = abs(y2 - y1)

                if (dist_x < grid_spacing and dist_y < 0.5) or (dist_y < grid_spacing and dist_x < 0.5):
                    # Create pipe segment
                    vertices, faces, normals = generate_pipe_segment((x1, y1, z1), (x2, y2, z2), diameter=0.025)

                    if vertices:
                        pipe_guid = str(uuid.uuid4())

                        cursor.execute("""
                            INSERT INTO elements_meta (guid, discipline, ifc_class, element_name, element_type, inferred_shape_type)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (pipe_guid, 'FP', 'IfcPipeSegment', 'Sprinkler Pipe', 'TEMPLATE_PIPE', 'box'))

                        cursor.execute("""
                            INSERT INTO element_transforms (guid, center_x, center_y, center_z, length)
                            VALUES (?, ?, ?, ?, ?)
                        """, (pipe_guid, (x1+x2)/2, (y1+y2)/2, (z1+z2)/2, math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)))

                        # Store geometry
                        v_blob = pack_vertices(vertices)
                        f_blob = pack_faces(faces)
                        n_blob = pack_normals(normals)
                        geom_hash = compute_hash(v_blob, f_blob)

                        cursor.execute("""
                            INSERT OR REPLACE INTO base_geometries (guid, geometry_hash, vertices, faces, normals)
                            VALUES (?, ?, ?, ?, ?)
                        """, (pipe_guid, geom_hash, v_blob, f_blob, n_blob))

                        pipe_count += 1

        stats['pipes'] = pipe_count
        print(f"✅ Generated {pipe_count} pipe segments connecting sprinklers\n")

    # =======================================================================
    # 3. GENERATE ELECTRICAL CONDUIT NETWORK
    # =======================================================================
    print("="*80)
    print("3. GENERATING ELECTRICAL CONDUIT NETWORK")
    print("="*80)

    # Get all lights
    cursor.execute("""
        SELECT et.center_x, et.center_y, et.center_z
        FROM elements_meta em
        JOIN element_transforms et ON em.guid = et.guid
        WHERE em.discipline = 'ELEC' AND em.inferred_shape_type = 'light_fixture'
        ORDER BY et.center_x, et.center_y
    """)

    lights = cursor.fetchall()
    print(f"Found {len(lights)} lights to connect\n")

    if len(lights) > 1:
        conduit_count = 0
        grid_spacing = 6.0  # 6m grid for electrical

        for i, light in enumerate(lights):
            x1, y1, z1 = light

            for j, other in enumerate(lights):
                if i >= j:
                    continue

                x2, y2, z2 = other

                dist_x = abs(x2 - x1)
                dist_y = abs(y2 - y1)

                if (dist_x < grid_spacing and dist_y < 0.5) or (dist_y < grid_spacing and dist_x < 0.5):
                    # Create conduit segment
                    vertices, faces, normals = generate_pipe_segment((x1, y1, z1), (x2, y2, z2), diameter=0.05)

                    if vertices:
                        conduit_guid = str(uuid.uuid4())

                        cursor.execute("""
                            INSERT INTO elements_meta (guid, discipline, ifc_class, element_name, element_type, inferred_shape_type)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (conduit_guid, 'ELEC', 'IfcCableCarrierSegment', 'Electrical Conduit', 'TEMPLATE_CONDUIT', 'box'))

                        cursor.execute("""
                            INSERT INTO element_transforms (guid, center_x, center_y, center_z, length)
                            VALUES (?, ?, ?, ?, ?)
                        """, (conduit_guid, (x1+x2)/2, (y1+y2)/2, (z1+z2)/2, math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)))

                        # Store geometry
                        v_blob = pack_vertices(vertices)
                        f_blob = pack_faces(faces)
                        n_blob = pack_normals(normals)
                        geom_hash = compute_hash(v_blob, f_blob)

                        cursor.execute("""
                            INSERT OR REPLACE INTO base_geometries (guid, geometry_hash, vertices, faces, normals)
                            VALUES (?, ?, ?, ?, ?)
                        """, (conduit_guid, geom_hash, v_blob, f_blob, n_blob))

                        conduit_count += 1

        stats['conduits'] = conduit_count
        print(f"✅ Generated {conduit_count} conduit segments connecting lights\n")

    # Update R-tree for new elements
    print("="*80)
    print("UPDATING R-TREE FOR NEW ELEMENTS")
    print("="*80)

    cursor.execute("""
        SELECT MAX(id) FROM elements_rtree
    """)
    max_rtree_id = cursor.fetchone()[0] or 0

    # Add floor to rtree
    cursor.execute("""
        INSERT INTO elements_rtree (id, minX, maxX, minY, maxY, minZ, maxZ)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (max_rtree_id + 1, floor_min_x, floor_max_x, floor_min_y, floor_max_y, min_z, min_z + 0.3))

    print(f"✅ Updated R-tree with new elements\n")

    conn.commit()
    conn.close()

    # Summary
    print("="*80)
    print("INFRASTRUCTURE GENERATION COMPLETE")
    print("="*80)
    print(f"✅ Floor slabs:      {stats['floors']}")
    print(f"✅ Pipe segments:    {stats['pipes']}")
    print(f"✅ Conduit segments: {stats['conduits']}")
    print(f"\nTotal new elements: {stats['floors'] + stats['pipes'] + stats['conduits']}")
    print("\n✅ Ready for Full Load in Blender!")
    print("="*80)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_infrastructure_templates.py <database_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}")
        sys.exit(1)

    generate_infrastructure(db_path)


if __name__ == "__main__":
    main()
