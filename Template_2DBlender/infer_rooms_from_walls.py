#!/usr/bin/env python3
"""
Infer room boundaries and generate interior walls from existing wall detection
NO AI - pure geometric spatial analysis
"""

import sqlite3
import struct
import json
from collections import defaultdict

DB_PATH = "output_artifacts/TB-LKTN HOUSE_ANNOTATION_FROM_2D.db"

def get_calibration():
    """Get calibration data from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT key, value FROM context_calibration")
    calib = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    return {
        'building_width': calib['building_width_m'],
        'building_length': calib['building_length_m'],
        'wall_height': calib.get('wall_height_m', 3.2),
        'wall_thickness': calib.get('wall_thickness_m', 0.15),
        'scale_m_per_pt': calib['scale_m_per_pt']
    }

def get_walls():
    """Get all detected walls from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT wall_id, wall_type, orientation,
               bbox_x0, bbox_y0, bbox_x1, bbox_y1, length
        FROM semantic_walls
        ORDER BY wall_id
    """)

    walls = []
    for row in cursor.fetchall():
        walls.append({
            'id': row[0],
            'type': row[1],
            'orientation': row[2],  # H or V
            'x0_pdf': row[3],
            'y0_pdf': row[4],
            'x1_pdf': row[5],
            'y1_pdf': row[6],
            'length_pdf': row[7]
        })

    conn.close()

    return walls

def convert_to_meters(walls, scale):
    """Convert PDF coordinates to meters"""

    import math

    for wall in walls:
        wall['x0_m'] = wall['x0_pdf'] * scale
        wall['y0_m'] = wall['y0_pdf'] * scale
        wall['x1_m'] = wall['x1_pdf'] * scale
        wall['y1_m'] = wall['y1_pdf'] * scale

        # Recalculate length from endpoints
        dx = wall['x1_m'] - wall['x0_m']
        dy = wall['y1_m'] - wall['y0_m']
        wall['length_m'] = math.sqrt(dx*dx + dy*dy)

    return walls

def create_wall_geometry(wall, calib):
    """
    Create 3D geometry for a wall segment
    Returns vertices (24 floats for 8 vertices) and faces (12 triangles)
    """

    # Wall goes from (x0, y0) to (x1, y1) in 2D
    x0, y0 = wall['x0_m'], wall['y0_m']
    x1, y1 = wall['x1_m'], wall['y1_m']

    # Determine wall direction and perpendicular offset for thickness
    import math
    dx = x1 - x0
    dy = y1 - y0
    length = math.sqrt(dx*dx + dy*dy)

    if length < 0.01:
        # Degenerate wall
        return None, None

    # Normalize direction
    dx /= length
    dy /= length

    # Perpendicular direction (90° rotation)
    perp_x = -dy
    perp_y = dx

    # Thickness offset
    thick = calib['wall_thickness'] / 2.0

    # Four corners at ground level (Z=0)
    # Bottom face (looking down from above, counter-clockwise)
    p0 = [x0 + perp_x * thick, y0 + perp_y * thick, 0.0]  # Left start
    p1 = [x1 + perp_x * thick, y1 + perp_y * thick, 0.0]  # Left end
    p2 = [x1 - perp_x * thick, y1 - perp_y * thick, 0.0]  # Right end
    p3 = [x0 - perp_x * thick, y0 - perp_y * thick, 0.0]  # Right start

    # Four corners at ceiling level (Z=wall_height)
    p4 = [x0 + perp_x * thick, y0 + perp_y * thick, calib['wall_height']]
    p5 = [x1 + perp_x * thick, y1 + perp_y * thick, calib['wall_height']]
    p6 = [x1 - perp_x * thick, y1 - perp_y * thick, calib['wall_height']]
    p7 = [x0 - perp_x * thick, y0 - perp_y * thick, calib['wall_height']]

    # Flatten to single array
    vertices = []
    for p in [p0, p1, p2, p3, p4, p5, p6, p7]:
        vertices.extend(p)

    # Faces (12 triangles for box)
    # Format: [v0, v1, v2] for each triangle
    faces = [
        # Bottom (Z=0)
        [0, 2, 1], [0, 3, 2],
        # Top (Z=height)
        [4, 5, 6], [4, 6, 7],
        # Side 1 (left edge)
        [0, 1, 5], [0, 5, 4],
        # Side 2 (far edge)
        [1, 2, 6], [1, 6, 5],
        # Side 3 (right edge)
        [2, 3, 7], [2, 7, 6],
        # Side 4 (near edge)
        [3, 0, 4], [3, 4, 7]
    ]

    return vertices, faces

def generate_room_geometries(walls, calib):
    """Generate 3D geometry for all interior walls"""

    geometries = []

    for wall in walls:
        if wall['type'] != 'interior':
            continue  # Only interior walls for room dividers

        verts, faces = create_wall_geometry(wall, calib)

        if verts is None:
            continue

        geometries.append({
            'name': f"interior_wall_{wall['id']}",
            'ifc_class': 'IfcWall',
            'wall_id': wall['id'],
            'orientation': wall['orientation'],
            'length_m': wall['length_m'],
            'vertices': verts,
            'faces': faces
        })

    return geometries

def store_in_database(geometries):
    """Store geometries in database"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interior_walls_geometry (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            ifc_class TEXT NOT NULL,
            wall_id INTEGER NOT NULL,
            orientation TEXT NOT NULL,
            length_m REAL NOT NULL,
            vertices BLOB NOT NULL,
            faces BLOB NOT NULL,
            vertex_count INTEGER NOT NULL,
            face_count INTEGER NOT NULL
        )
    """)

    # Clear existing data
    cursor.execute("DELETE FROM interior_walls_geometry")

    # Insert geometries
    for geom in geometries:
        verts_blob = struct.pack(f'<{len(geom["vertices"])}f', *geom['vertices'])
        faces_flat = [idx for face in geom['faces'] for idx in face]
        faces_blob = struct.pack(f'<{len(faces_flat)}I', *faces_flat)

        cursor.execute("""
            INSERT INTO interior_walls_geometry
            (name, ifc_class, wall_id, orientation, length_m, vertices, faces, vertex_count, face_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            geom['name'],
            geom['ifc_class'],
            geom['wall_id'],
            geom['orientation'],
            geom['length_m'],
            verts_blob,
            faces_blob,
            len(geom['vertices']) // 3,
            len(geom['faces'])
        ))

    conn.commit()
    conn.close()

def export_to_json(geometries, walls, calib):
    """Export to JSON for analysis"""

    output = {
        'metadata': {
            'project': 'TB-LKTN House Interior Walls',
            'scope': 'Interior walls inferred from wall detection',
            'element_count': len(geometries)
        },
        'calibration': {
            'building_width': calib['building_width'],
            'building_length': calib['building_length'],
            'wall_height': calib['wall_height'],
            'wall_thickness': calib['wall_thickness'],
            'scale_m_per_pt': calib['scale_m_per_pt']
        },
        'walls': [],
        'elements': []
    }

    # Add wall information
    for wall in walls:
        if wall['type'] == 'interior':
            output['walls'].append({
                'wall_id': wall['id'],
                'orientation': wall['orientation'],
                'length_m': round(wall['length_m'], 3),
                'position': {
                    'x0_m': round(wall['x0_m'], 3),
                    'y0_m': round(wall['y0_m'], 3),
                    'x1_m': round(wall['x1_m'], 3),
                    'y1_m': round(wall['y1_m'], 3)
                }
            })

    # Add geometry information
    for geom in geometries:
        output['elements'].append({
            'name': geom['name'],
            'ifc_class': geom['ifc_class'],
            'wall_id': geom['wall_id'],
            'orientation': geom['orientation'],
            'length_m': round(geom['length_m'], 3),
            'vertex_count': len(geom['vertices']) // 3,
            'face_count': len(geom['faces'])
        })

    with open('output_artifacts/interior_walls.json', 'w') as f:
        json.dump(output, f, indent=2)

def print_summary(walls, geometries, calib):
    """Print summary"""

    print("\n" + "="*70)
    print(" INTERIOR WALL INFERENCE SUMMARY ".center(70, "="))
    print("="*70)

    print(f"\nTotal walls detected: {len(walls)}")
    print(f"  Exterior walls: {sum(1 for w in walls if w['type'] == 'exterior')}")
    print(f"  Interior walls: {sum(1 for w in walls if w['type'] == 'interior')}")

    print(f"\n3D Geometries generated: {len(geometries)}")

    print(f"\nInterior wall details:")
    h_walls = [w for w in walls if w['type'] == 'interior' and w['orientation'] == 'H']
    v_walls = [w for w in walls if w['type'] == 'interior' and w['orientation'] == 'V']

    print(f"  Horizontal walls: {len(h_walls)}")
    for w in h_walls:
        print(f"    Wall {w['id']}: {w['length_m']:.2f}m at Y={w['y0_m']:.2f}m")

    print(f"  Vertical walls: {len(v_walls)}")
    for w in v_walls:
        print(f"    Wall {w['id']}: {w['length_m']:.2f}m at X={w['x0_m']:.2f}m")

    print(f"\nCalibration used:")
    print(f"  Building: {calib['building_width']:.2f}m × {calib['building_length']:.2f}m")
    print(f"  Wall height: {calib['wall_height']:.2f}m")
    print(f"  Wall thickness: {calib['wall_thickness']:.2f}m")
    print(f"  Scale: {calib['scale_m_per_pt']:.4f} m/pt")

    print("\n" + "="*70)
    print("✅ Interior walls inferred and stored in database")
    print("✅ Geometries exported to output_artifacts/interior_walls.json")
    print("="*70 + "\n")

if __name__ == "__main__":
    print("Inferring room boundaries from detected walls...")

    # Get data
    calib = get_calibration()
    walls = get_walls()

    # Convert to meters
    walls = convert_to_meters(walls, calib['scale_m_per_pt'])

    # Generate geometries
    geometries = generate_room_geometries(walls, calib)

    # Store and export
    store_in_database(geometries)
    export_to_json(geometries, walls, calib)

    # Print summary
    print_summary(walls, geometries, calib)
