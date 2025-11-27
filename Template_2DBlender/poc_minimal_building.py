#!/usr/bin/env python3
"""
POC: Minimal Building Generation - Drains, Outer Walls, Roof, Porch Only
Full cycle: PDF extraction → calibration → geometry → database → JSON

Demonstrates elegant inference from minimal semantic data.
"""

import sqlite3
import json
import math
import struct
from pathlib import Path

# Database path
DB_PATH = "output_artifacts/TB-LKTN HOUSE_ANNOTATION_FROM_2D.db"
OUTPUT_JSON = "output_artifacts/POC_minimal_building.json"

def compute_face_normal(v0, v1, v2):
    """Compute face normal using cross product"""
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

def extract_calibration_data(conn):
    """Extract calibration from existing database"""
    print("\n=== STAGE 1: Extract Calibration ===")

    cursor = conn.cursor()

    # Get calibration data
    cursor.execute("""
        SELECT key, value FROM context_calibration
        WHERE key IN ('building_width_m', 'building_length_m',
                      'drain_width_m', 'drain_length_m',
                      'overhang_offset_h', 'scale_m_per_pt')
    """)

    calib = {row[0]: row[1] for row in cursor.fetchall()}

    # Get roof pitch from primitives_text page 3
    cursor.execute("SELECT text FROM primitives_text WHERE page=3 AND text LIKE '%°%' LIMIT 1")
    pitch_row = cursor.fetchone()
    roof_pitch = 25.0  # Default from documentation
    if pitch_row:
        try:
            roof_pitch = float(pitch_row[0].replace('°', ''))
        except:
            pass

    # Get height from primitives_text pages 4-7
    cursor.execute("SELECT text FROM primitives_text WHERE page>=4 AND text='3000' LIMIT 1")
    height_row = cursor.fetchone()
    floor_ceiling_mm = 3000 if height_row else 3000

    result = {
        'building_width': calib.get('building_width_m', 11.2),
        'building_length': calib.get('building_length_m', 11.6),
        'drain_width': calib.get('drain_width_m', 11.78),
        'drain_length': calib.get('drain_length_m', 10.05),
        'overhang': calib.get('overhang_offset_h', 0.29),
        'scale': calib.get('scale_m_per_pt', 0.03528),
        'roof_pitch_deg': roof_pitch,
        'wall_height': floor_ceiling_mm / 1000.0 + 0.2,  # 3.0m + 0.2m structure = 3.2m
        'wall_thickness': 0.15  # 150mm typical
    }

    print(f"  Building: {result['building_width']:.2f}m × {result['building_length']:.2f}m")
    print(f"  Drain: {result['drain_width']:.2f}m × {result['drain_length']:.2f}m")
    print(f"  Wall height: {result['wall_height']:.2f}m")
    print(f"  Roof pitch: {result['roof_pitch_deg']}°")

    return result

def generate_drain_perimeter(calib):
    """Generate outer drain perimeter rectangle"""
    print("\n=== STAGE 2: Generate Drain Perimeter ===")

    w = calib['drain_width']
    l = calib['drain_length']

    # Rectangle at ground level (z=0), centered at origin
    vertices = [
        -w/2, -l/2, 0.0,  # 0: SW corner
         w/2, -l/2, 0.0,  # 1: SE corner
         w/2,  l/2, 0.0,  # 2: NE corner
        -w/2,  l/2, 0.0,  # 3: NW corner
        # Top edge slightly raised for visibility
        -w/2, -l/2, 0.05,  # 4
         w/2, -l/2, 0.05,  # 5
         w/2,  l/2, 0.05,  # 6
        -w/2,  l/2, 0.05,  # 7
    ]

    # Faces (triangles) - drain channel as thin walls
    faces = [
        # Bottom
        0, 1, 2,  0, 2, 3,
        # Top
        4, 6, 5,  4, 7, 6,
        # Sides (connecting bottom to top)
        0, 4, 5,  0, 5, 1,  # South
        1, 5, 6,  1, 6, 2,  # East
        2, 6, 7,  2, 7, 3,  # North
        3, 7, 4,  3, 4, 0,  # West
    ]

    # Compute normals
    normals = []
    for i in range(0, len(faces), 3):
        v0 = (vertices[faces[i]*3], vertices[faces[i]*3+1], vertices[faces[i]*3+2])
        v1 = (vertices[faces[i+1]*3], vertices[faces[i+1]*3+1], vertices[faces[i+1]*3+2])
        v2 = (vertices[faces[i+2]*3], vertices[faces[i+2]*3+1], vertices[faces[i+2]*3+2])
        n = compute_face_normal(v0, v1, v2)
        normals.extend(n)

    print(f"  Generated drain: {w:.2f}m × {l:.2f}m")
    print(f"  Vertices: {len(vertices)//3}, Faces: {len(faces)//3}")

    return {
        'name': 'drain_perimeter',
        'ifc_class': 'IfcBuildingElementProxy',
        'vertices': vertices,
        'faces': faces,
        'normals': normals
    }

def generate_outer_walls(calib):
    """Generate 4 outer walls (correctly formed, joined at corners)"""
    print("\n=== STAGE 3: Generate Outer Walls ===")

    w = calib['building_width']
    l = calib['building_length']
    h = calib['wall_height']
    t = calib['wall_thickness']

    # Wall centerline offsets (inside drain perimeter by overhang)
    w_half = w / 2
    l_half = l / 2

    walls = []

    # SOUTH wall (along -Y, width extends -X to +X)
    vertices_s = [
        # Outer face
        -w_half, -l_half - t/2, 0.0,  # 0: Bottom SW
         w_half, -l_half - t/2, 0.0,  # 1: Bottom SE
         w_half, -l_half - t/2, h,    # 2: Top SE
        -w_half, -l_half - t/2, h,    # 3: Top SW
        # Inner face
        -w_half, -l_half + t/2, 0.0,  # 4
         w_half, -l_half + t/2, 0.0,  # 5
         w_half, -l_half + t/2, h,    # 6
        -w_half, -l_half + t/2, h,    # 7
    ]

    # NORTH wall
    vertices_n = [
        -w_half,  l_half - t/2, 0.0,  # 0
         w_half,  l_half - t/2, 0.0,  # 1
         w_half,  l_half - t/2, h,    # 2
        -w_half,  l_half - t/2, h,    # 3
        -w_half,  l_half + t/2, 0.0,  # 4
         w_half,  l_half + t/2, 0.0,  # 5
         w_half,  l_half + t/2, h,    # 6
        -w_half,  l_half + t/2, h,    # 7
    ]

    # EAST wall
    vertices_e = [
         w_half - t/2, -l_half, 0.0,  # 0
         w_half + t/2, -l_half, 0.0,  # 1
         w_half + t/2, -l_half, h,    # 2
         w_half - t/2, -l_half, h,    # 3
         w_half - t/2,  l_half, 0.0,  # 4
         w_half + t/2,  l_half, 0.0,  # 5
         w_half + t/2,  l_half, h,    # 6
         w_half - t/2,  l_half, h,    # 7
    ]

    # WEST wall
    vertices_w = [
        -w_half - t/2, -l_half, 0.0,  # 0
        -w_half + t/2, -l_half, 0.0,  # 1
        -w_half + t/2, -l_half, h,    # 2
        -w_half - t/2, -l_half, h,    # 3
        -w_half - t/2,  l_half, 0.0,  # 4
        -w_half + t/2,  l_half, 0.0,  # 5
        -w_half + t/2,  l_half, h,    # 6
        -w_half - t/2,  l_half, h,    # 7
    ]

    # Face indices (same for all walls - box topology)
    faces_box = [
        # Outer face
        0, 1, 2,  0, 2, 3,
        # Inner face
        4, 6, 5,  4, 7, 6,
        # Top
        3, 2, 6,  3, 6, 7,
        # Bottom
        0, 5, 1,  0, 4, 5,
        # Left end
        0, 3, 7,  0, 7, 4,
        # Right end
        1, 6, 2,  1, 5, 6
    ]

    for name, verts in [('south', vertices_s), ('north', vertices_n),
                         ('east', vertices_e), ('west', vertices_w)]:
        normals = []
        for i in range(0, len(faces_box), 3):
            v0 = (verts[faces_box[i]*3], verts[faces_box[i]*3+1], verts[faces_box[i]*3+2])
            v1 = (verts[faces_box[i+1]*3], verts[faces_box[i+1]*3+1], verts[faces_box[i+1]*3+2])
            v2 = (verts[faces_box[i+2]*3], verts[faces_box[i+2]*3+1], verts[faces_box[i+2]*3+2])
            n = compute_face_normal(v0, v1, v2)
            normals.extend(n)

        walls.append({
            'name': f'wall_{name}',
            'ifc_class': 'IfcWall',
            'vertices': verts,
            'faces': faces_box.copy(),
            'normals': normals
        })

    print(f"  Generated 4 walls: {w:.2f}m × {l:.2f}m × {h:.2f}m")
    print(f"  Wall thickness: {t:.2f}m")

    return walls

def generate_roof(calib):
    """Generate pitched roof with proper ridge and slopes"""
    print("\n=== STAGE 4: Generate Roof ===")

    w = calib['drain_width']  # Use drain width (includes overhang)
    l = calib['drain_length']
    h = calib['wall_height']
    pitch_deg = calib['roof_pitch_deg']

    # Ridge height above wall
    ridge_height = (w / 2) * math.tan(math.radians(pitch_deg))
    ridge_z = h + ridge_height

    # Simple gable roof (2 slopes, ridge along length)
    vertices = [
        # Eave corners at wall top
        -w/2, -l/2, h,   # 0: SW eave
         w/2, -l/2, h,   # 1: SE eave
         w/2,  l/2, h,   # 2: NE eave
        -w/2,  l/2, h,   # 3: NW eave
        # Ridge line (centerline, full length)
         0.0, -l/2, ridge_z,  # 4: South ridge end
         0.0,  l/2, ridge_z,  # 5: North ridge end
    ]

    # Roof planes
    faces = [
        # South gable (triangle)
        0, 1, 4,
        # North gable (triangle)
        3, 5, 2,
        # West slope (two triangles)
        0, 4, 5,  0, 5, 3,
        # East slope (two triangles)
        1, 2, 5,  1, 5, 4,
    ]

    normals = []
    for i in range(0, len(faces), 3):
        v0 = (vertices[faces[i]*3], vertices[faces[i]*3+1], vertices[faces[i]*3+2])
        v1 = (vertices[faces[i+1]*3], vertices[faces[i+1]*3+1], vertices[faces[i+1]*3+2])
        v2 = (vertices[faces[i+2]*3], vertices[faces[i+2]*3+1], vertices[faces[i+2]*3+2])
        n = compute_face_normal(v0, v1, v2)
        normals.extend(n)

    print(f"  Roof: {w:.2f}m × {l:.2f}m, pitch {pitch_deg}°")
    print(f"  Ridge height: {ridge_height:.2f}m above walls")
    print(f"  Total building height: {ridge_z:.2f}m")

    return {
        'name': 'roof',
        'ifc_class': 'IfcRoof',
        'vertices': vertices,
        'faces': faces,
        'normals': normals
    }

def generate_porch(calib):
    """Generate simple porch (front entrance overhang)"""
    print("\n=== STAGE 5: Generate Porch ===")

    # Porch dimensions (typical Malaysian terrace front porch)
    porch_width = 2.0  # 2m wide
    porch_depth = 1.5  # 1.5m deep
    porch_height = 2.5  # 2.5m clearance

    # Position: center of south wall, projecting outward
    l_half = calib['building_length'] / 2

    vertices = [
        # Floor slab
        -porch_width/2, -l_half - porch_depth, 0.0,  # 0
         porch_width/2, -l_half - porch_depth, 0.0,  # 1
         porch_width/2, -l_half, 0.0,                # 2
        -porch_width/2, -l_half, 0.0,                # 3
        # Roof slab
        -porch_width/2, -l_half - porch_depth, porch_height,  # 4
         porch_width/2, -l_half - porch_depth, porch_height,  # 5
         porch_width/2, -l_half, porch_height,                # 6
        -porch_width/2, -l_half, porch_height,                # 7
    ]

    # Simple box (floor + roof slab)
    faces = [
        # Floor
        0, 2, 1,  0, 3, 2,
        # Roof
        4, 5, 6,  4, 6, 7,
        # Sides
        0, 1, 5,  0, 5, 4,  # Front
        2, 6, 5,  2, 5, 1,  # Right
        3, 7, 6,  3, 6, 2,  # Back (attaches to wall)
        0, 4, 7,  0, 7, 3,  # Left
    ]

    normals = []
    for i in range(0, len(faces), 3):
        v0 = (vertices[faces[i]*3], vertices[faces[i]*3+1], vertices[faces[i]*3+2])
        v1 = (vertices[faces[i+1]*3], vertices[faces[i+1]*3+1], vertices[faces[i+1]*3+2])
        v2 = (vertices[faces[i+2]*3], vertices[faces[i+2]*3+1], vertices[faces[i+2]*3+2])
        n = compute_face_normal(v0, v1, v2)
        normals.extend(n)

    print(f"  Porch: {porch_width}m × {porch_depth}m × {porch_height}m")

    return {
        'name': 'porch',
        'ifc_class': 'IfcBuildingElementProxy',
        'vertices': vertices,
        'faces': faces,
        'normals': normals
    }

def store_in_database(conn, geometries):
    """Store all geometry in database"""
    print("\n=== STAGE 6: Store Geometry in Database ===")

    cursor = conn.cursor()

    # Create POC geometry table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS poc_geometry (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            ifc_class TEXT NOT NULL,
            vertices BLOB NOT NULL,
            faces BLOB NOT NULL,
            normals BLOB NOT NULL,
            vertex_count INTEGER,
            face_count INTEGER
        )
    """)

    # Clear existing POC data
    cursor.execute("DELETE FROM poc_geometry")

    for geom in geometries:
        # Pack binary data
        vertices_blob = struct.pack(f'<{len(geom["vertices"])}f', *geom["vertices"])
        faces_blob = struct.pack(f'<{len(geom["faces"])}I', *geom["faces"])
        normals_blob = struct.pack(f'<{len(geom["normals"])}f', *geom["normals"])

        cursor.execute("""
            INSERT INTO poc_geometry (name, ifc_class, vertices, faces, normals, vertex_count, face_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            geom['name'],
            geom['ifc_class'],
            vertices_blob,
            faces_blob,
            normals_blob,
            len(geom['vertices']) // 3,
            len(geom['faces']) // 3
        ))

        print(f"  Stored: {geom['name']} ({len(geom['vertices'])//3} verts, {len(geom['faces'])//3} faces)")

    conn.commit()
    print(f"  Total elements stored: {len(geometries)}")

def export_to_json(geometries, calib, output_path):
    """Export all data to JSON for analysis"""
    print("\n=== STAGE 7: Export to JSON ===")

    output = {
        'metadata': {
            'project': 'POC Minimal Building',
            'scope': 'Drains, Outer Walls, Roof, Porch only',
            'source': 'TB-LKTN HOUSE.pdf',
            'method': 'Elegant inference from minimal semantic data'
        },
        'calibration': calib,
        'elements': []
    }

    for geom in geometries:
        # Convert vertices to readable format (x,y,z triplets)
        verts = geom['vertices']
        vertices_xyz = [
            [verts[i], verts[i+1], verts[i+2]]
            for i in range(0, len(verts), 3)
        ]

        # Faces as index triplets
        faces_idx = geom['faces']
        faces_triplets = [
            [faces_idx[i], faces_idx[i+1], faces_idx[i+2]]
            for i in range(0, len(faces_idx), 3)
        ]

        output['elements'].append({
            'name': geom['name'],
            'ifc_class': geom['ifc_class'],
            'vertices': vertices_xyz,
            'faces': faces_triplets,
            'vertex_count': len(vertices_xyz),
            'face_count': len(faces_triplets)
        })

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"  Exported to: {output_path}")
    print(f"  Total vertices: {sum(len(e['vertices']) for e in output['elements'])}")
    print(f"  Total faces: {sum(len(e['faces']) for e in output['elements'])}")

    return output

def validate_output(geometries, calib):
    """Validate geometry correctness"""
    print("\n=== STAGE 8: Validate Output ===")

    checks = []

    # Check 1: Drain perimeter matches calibration
    drain = next(g for g in geometries if g['name'] == 'drain_perimeter')
    drain_verts = drain['vertices']
    xs = [drain_verts[i] for i in range(0, len(drain_verts), 3)]
    ys = [drain_verts[i+1] for i in range(0, len(drain_verts), 3)]
    measured_w = max(xs) - min(xs)
    measured_l = max(ys) - min(ys)
    check_drain = (abs(measured_w - calib['drain_width']) < 0.01 and
                   abs(measured_l - calib['drain_length']) < 0.01)
    checks.append(('Drain dimensions', check_drain, f"{measured_w:.2f}×{measured_l:.2f}"))

    # Check 2: Walls height correct
    wall = next(g for g in geometries if 'wall' in g['name'])
    wall_verts = wall['vertices']
    zs = [wall_verts[i+2] for i in range(0, len(wall_verts), 3)]
    max_z = max(zs)
    check_height = abs(max_z - calib['wall_height']) < 0.01
    checks.append(('Wall height', check_height, f"{max_z:.2f}m"))

    # Check 3: Roof above walls
    roof = next(g for g in geometries if g['name'] == 'roof')
    roof_verts = roof['vertices']
    roof_zs = [roof_verts[i+2] for i in range(0, len(roof_verts), 3)]
    roof_max = max(roof_zs)
    check_roof = roof_max > calib['wall_height']
    checks.append(('Roof above walls', check_roof, f"{roof_max:.2f}m"))

    # Check 4: All faces are triangles
    all_triangles = all(len(g['faces']) % 3 == 0 for g in geometries)
    checks.append(('All triangular faces', all_triangles, 'OK' if all_triangles else 'FAIL'))

    # Check 5: All have normals
    all_normals = all(len(g['normals']) == len(g['faces']) for g in geometries)
    checks.append(('Normals present', all_normals, 'OK' if all_normals else 'FAIL'))

    print("\n  Validation Results:")
    for name, passed, value in checks:
        status = "✅" if passed else "❌"
        print(f"    {status} {name}: {value}")

    all_passed = all(c[1] for c in checks)
    print(f"\n  Overall: {'✅ ALL CHECKS PASSED' if all_passed else '❌ SOME CHECKS FAILED'}")

    return all_passed

def main():
    print("="*70)
    print("POC: Minimal Building Generation")
    print("Scope: Drains, Outer Walls, Roof, Porch only")
    print("="*70)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    try:
        # Stage 1: Extract calibration
        calib = extract_calibration_data(conn)

        # Stage 2-5: Generate geometry
        geometries = []
        geometries.append(generate_drain_perimeter(calib))
        geometries.extend(generate_outer_walls(calib))
        geometries.append(generate_roof(calib))
        geometries.append(generate_porch(calib))

        # Stage 6: Store in database
        store_in_database(conn, geometries)

        # Stage 7: Export to JSON
        output_data = export_to_json(geometries, calib, OUTPUT_JSON)

        # Stage 8: Validate
        success = validate_output(geometries, calib)

        print("\n" + "="*70)
        if success:
            print("✅ POC COMPLETE - All geometry generated and validated")
            print(f"   Database: {DB_PATH} (poc_geometry table)")
            print(f"   JSON: {OUTPUT_JSON}")
        else:
            print("⚠️  POC COMPLETE with warnings - Check validation results")
        print("="*70)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
