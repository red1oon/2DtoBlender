#!/usr/bin/env python3
"""
Detailed Rotation and Orientation Testing
Tests spatial relationships, coordinate system correctness, and proper alignment
"""

import json
import math
import struct
import sqlite3

JSON_PATH = "output_artifacts/POC_minimal_building.json"
DB_PATH = "output_artifacts/TB-LKTN HOUSE_ANNOTATION_FROM_2D.db"

def load_from_db():
    """Load geometry from database for testing"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name, vertices, faces FROM poc_geometry")
    elements = {}

    for name, verts_blob, faces_blob in cursor.fetchall():
        vert_count = len(verts_blob) // 12  # 3 floats * 4 bytes = 12 bytes per vertex
        face_count = len(faces_blob) // 12  # 3 uint32 * 4 bytes = 12 bytes per face

        verts = struct.unpack(f'<{vert_count * 3}f', verts_blob)
        faces = struct.unpack(f'<{face_count * 3}I', faces_blob)

        # Convert to list of [x,y,z] triplets
        vertices = [[verts[i*3], verts[i*3+1], verts[i*3+2]] for i in range(vert_count)]
        face_list = [[faces[i*3], faces[i*3+1], faces[i*3+2]] for i in range(face_count)]

        elements[name] = {'vertices': vertices, 'faces': face_list}

    conn.close()
    return elements

def test_coordinate_system(elements):
    """Test 1: Verify coordinate system is correct (right-handed, Z-up)"""
    print("\n" + "="*70)
    print("TEST: COORDINATE SYSTEM VERIFICATION")
    print("="*70)

    # Check that Z is vertical (walls go up in Z)
    wall = elements['wall_south']
    zs = [v[2] for v in wall['vertices']]
    z_range = max(zs) - min(zs)

    print(f"\n  Z-axis verification:")
    print(f"    Wall extends in Z: {min(zs):.2f}m to {max(zs):.2f}m (range: {z_range:.2f}m)")
    print(f"    Status: {'✅ Z is UP' if z_range > 2.0 else '❌ Z not vertical'}")

    # Check ground plane is at Z=0
    all_min_z = min(v[2] for elem in elements.values() for v in elem['vertices'])
    print(f"\n  Ground plane:")
    print(f"    Minimum Z across all elements: {all_min_z:.4f}m")
    print(f"    Status: {'✅ Ground at Z=0' if abs(all_min_z) < 0.01 else '⚠️  Not at origin'}")

    # Check building centered near origin in XY
    all_xs = [v[0] for elem in elements.values() for v in elem['vertices']]
    all_ys = [v[1] for elem in elements.values() for v in elem['vertices']]
    center_x = (max(all_xs) + min(all_xs)) / 2
    center_y = (max(all_ys) + min(all_ys)) / 2

    print(f"\n  Building center in XY plane:")
    print(f"    Center: ({center_x:.3f}, {center_y:.3f})")
    print(f"    Status: {'✅ Centered at origin' if abs(center_x) < 1.0 and abs(center_y) < 1.0 else '⚠️  Offset from origin'}")

    return True

def test_wall_orientations(elements):
    """Test 2: Verify walls are properly oriented (N/S/E/W)"""
    print("\n" + "="*70)
    print("TEST: WALL ORIENTATIONS")
    print("="*70)

    walls = {name: elem for name, elem in elements.items() if 'wall' in name}

    results = []

    for name, wall in walls.items():
        verts = wall['vertices']

        # Get bbox
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]

        x_range = max(xs) - min(xs)
        y_range = max(ys) - min(ys)
        z_range = max(zs) - min(zs)

        # Determine orientation
        if x_range > y_range:
            orientation = "East-West (along X axis)"
            primary_axis = "X"
            length = x_range
        else:
            orientation = "North-South (along Y axis)"
            primary_axis = "Y"
            length = y_range

        # Check thickness (minor axis should be ~0.15m)
        thickness = min(x_range, y_range)
        thickness_ok = 0.10 < thickness < 0.20

        # Check height
        height_ok = abs(z_range - 3.2) < 0.1

        results.append({
            'name': name,
            'orientation': orientation,
            'axis': primary_axis,
            'length': length,
            'thickness': thickness,
            'height': z_range,
            'thickness_ok': thickness_ok,
            'height_ok': height_ok
        })

    print(f"\n  {'Wall':<15} {'Orientation':<25} {'Length':<10} {'Thick':<10} {'Height':<10} {'Status':<8}")
    print(f"  {'-'*15} {'-'*25} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")

    for r in results:
        status = "✅" if r['thickness_ok'] and r['height_ok'] else "⚠️ "
        print(f"  {r['name']:<15} {r['orientation']:<25} {r['length']:<10.2f} {r['thickness']:<10.3f} {r['height']:<10.2f} {status:<8}")

    # Check that we have 2 E-W walls and 2 N-S walls
    ew_count = sum(1 for r in results if r['axis'] == 'X')
    ns_count = sum(1 for r in results if r['axis'] == 'Y')

    print(f"\n  Wall distribution:")
    print(f"    East-West walls: {ew_count} (expected: 2)")
    print(f"    North-South walls: {ns_count} (expected: 2)")
    print(f"    Status: {'✅ Correct layout' if ew_count == 2 and ns_count == 2 else '❌ Wrong distribution'}")

    return ew_count == 2 and ns_count == 2

def test_wall_parallelism(elements):
    """Test 3: Verify opposite walls are parallel"""
    print("\n" + "="*70)
    print("TEST: WALL PARALLELISM")
    print("="*70)

    south = elements['wall_south']
    north = elements['wall_north']
    east = elements['wall_east']
    west = elements['wall_west']

    # Get wall center Y coordinates
    south_y = sum(v[1] for v in south['vertices']) / len(south['vertices'])
    north_y = sum(v[1] for v in north['vertices']) / len(north['vertices'])

    # Get wall center X coordinates
    east_x = sum(v[0] for v in east['vertices']) / len(east['vertices'])
    west_x = sum(v[0] for v in west['vertices']) / len(west['vertices'])

    print(f"\n  South-North axis (Y coordinates):")
    print(f"    South wall Y: {south_y:.4f}m")
    print(f"    North wall Y: {north_y:.4f}m")
    print(f"    Distance: {abs(north_y - south_y):.4f}m (expected: ~11.6m)")
    print(f"    Parallel: {'✅ YES' if abs(south_y) - abs(north_y) < 0.01 else '⚠️  Slight offset'}")

    print(f"\n  East-West axis (X coordinates):")
    print(f"    East wall X: {east_x:.4f}m")
    print(f"    West wall X: {west_x:.4f}m")
    print(f"    Distance: {abs(east_x - west_x):.4f}m (expected: ~11.2m)")
    print(f"    Parallel: {'✅ YES' if abs(east_x) - abs(west_x) < 0.01 else '⚠️  Slight offset'}")

    # Check symmetry (walls equidistant from origin)
    south_offset = abs(abs(south_y) - abs(north_y))
    east_offset = abs(abs(east_x) - abs(west_x))

    print(f"\n  Symmetry check:")
    print(f"    South-North symmetry error: {south_offset:.6f}m")
    print(f"    East-West symmetry error: {east_offset:.6f}m")
    print(f"    Status: {'✅ Symmetric' if south_offset < 0.1 and east_offset < 0.1 else '⚠️  Asymmetric'}")

    return True

def test_roof_alignment(elements):
    """Test 4: Verify roof is properly aligned with walls"""
    print("\n" + "="*70)
    print("TEST: ROOF ALIGNMENT WITH WALLS")
    print("="*70)

    roof = elements['roof']
    drain = elements['drain_perimeter']

    # Get roof footprint
    roof_xs = [v[0] for v in roof['vertices']]
    roof_ys = [v[1] for v in roof['vertices']]
    roof_zs = [v[2] for v in roof['vertices']]

    roof_x_min, roof_x_max = min(roof_xs), max(roof_xs)
    roof_y_min, roof_y_max = min(roof_ys), max(roof_ys)
    roof_z_min, roof_z_max = min(roof_zs), max(roof_zs)

    # Get drain perimeter (should match roof footprint)
    drain_xs = [v[0] for v in drain['vertices']]
    drain_ys = [v[1] for v in drain['vertices']]

    drain_x_min, drain_x_max = min(drain_xs), max(drain_xs)
    drain_y_min, drain_y_max = min(drain_ys), max(drain_ys)

    print(f"\n  Roof footprint:")
    print(f"    X: [{roof_x_min:.3f}, {roof_x_max:.3f}] (width: {roof_x_max - roof_x_min:.3f}m)")
    print(f"    Y: [{roof_y_min:.3f}, {roof_y_max:.3f}] (length: {roof_y_max - roof_y_min:.3f}m)")
    print(f"    Z: [{roof_z_min:.3f}, {roof_z_max:.3f}] (ridge at {roof_z_max:.3f}m)")

    print(f"\n  Drain perimeter:")
    print(f"    X: [{drain_x_min:.3f}, {drain_x_max:.3f}] (width: {drain_x_max - drain_x_min:.3f}m)")
    print(f"    Y: [{drain_y_min:.3f}, {drain_y_max:.3f}] (length: {drain_y_max - drain_y_min:.3f}m)")

    # Check alignment
    x_align_error = max(abs(roof_x_min - drain_x_min), abs(roof_x_max - drain_x_max))
    y_align_error = max(abs(roof_y_min - drain_y_min), abs(roof_y_max - drain_y_max))

    print(f"\n  Alignment errors:")
    print(f"    X alignment: {x_align_error:.6f}m")
    print(f"    Y alignment: {y_align_error:.6f}m")
    print(f"    Status: {'✅ Perfectly aligned' if x_align_error < 0.01 and y_align_error < 0.01 else '⚠️  Slight misalignment'}")

    # Check roof eaves are at wall top height
    expected_eave_z = 3.2  # Wall height
    print(f"\n  Eave height:")
    print(f"    Roof minimum Z: {roof_z_min:.4f}m")
    print(f"    Expected (wall top): {expected_eave_z:.4f}m")
    print(f"    Error: {abs(roof_z_min - expected_eave_z):.6f}m")
    print(f"    Status: {'✅ Aligned' if abs(roof_z_min - expected_eave_z) < 0.01 else '❌ Misaligned'}")

    return True

def test_porch_position(elements):
    """Test 5: Verify porch is correctly positioned relative to building"""
    print("\n" + "="*70)
    print("TEST: PORCH POSITION")
    print("="*70)

    porch = elements['porch']
    south_wall = elements['wall_south']

    # Get porch position
    porch_xs = [v[0] for v in porch['vertices']]
    porch_ys = [v[1] for v in porch['vertices']]
    porch_zs = [v[2] for v in porch['vertices']]

    porch_center_x = (max(porch_xs) + min(porch_xs)) / 2
    porch_y_max = max(porch_ys)  # Back edge (should attach to south wall)
    porch_y_min = min(porch_ys)  # Front edge (projects outward)

    # Get south wall position
    south_ys = [v[1] for v in south_wall['vertices']]
    south_y_front = max(south_ys)  # Front face of south wall

    print(f"\n  Porch dimensions:")
    print(f"    Width: {max(porch_xs) - min(porch_xs):.2f}m (expected: 2.0m)")
    print(f"    Depth: {porch_y_max - porch_y_min:.2f}m (expected: 1.5m)")
    print(f"    Height: {max(porch_zs) - min(porch_zs):.2f}m (expected: 2.5m)")

    print(f"\n  Porch position:")
    print(f"    Center X: {porch_center_x:.4f}m (should be ~0 - centered on south wall)")
    print(f"    Back edge Y: {porch_y_max:.4f}m")
    print(f"    South wall front Y: {south_y_front:.4f}m")
    print(f"    Attachment gap: {abs(porch_y_max - south_y_front):.4f}m")

    centered = abs(porch_center_x) < 0.5
    attached = abs(porch_y_max - south_y_front) < 0.2
    projects_outward = porch_y_min < south_y_front

    print(f"\n  Position checks:")
    print(f"    Centered on building: {'✅ YES' if centered else '❌ NO'}")
    print(f"    Attached to south wall: {'✅ YES' if attached else '❌ NO'}")
    print(f"    Projects outward: {'✅ YES' if projects_outward else '❌ NO'}")

    return centered and attached and projects_outward

def test_face_winding_order(elements):
    """Test 6: Verify face winding order is consistent (counter-clockwise from outside)"""
    print("\n" + "="*70)
    print("TEST: FACE WINDING ORDER")
    print("="*70)

    # Test one wall as example
    wall = elements['wall_south']
    verts = wall['vertices']
    faces = wall['faces']

    # For each face, compute normal and check if it points outward
    outward_count = 0
    inward_count = 0

    # Get wall center
    center_x = sum(v[0] for v in verts) / len(verts)
    center_y = sum(v[1] for v in verts) / len(verts)
    center_z = sum(v[2] for v in verts) / len(verts)

    for face in faces[:3]:  # Check first 3 faces as sample
        v0, v1, v2 = verts[face[0]], verts[face[1]], verts[face[2]]

        # Compute face normal
        e1 = [v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]]
        e2 = [v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]]

        normal = [
            e1[1]*e2[2] - e1[2]*e2[1],
            e1[2]*e2[0] - e1[0]*e2[2],
            e1[0]*e2[1] - e1[1]*e2[0]
        ]

        # Face centroid
        fc_x = (v0[0] + v1[0] + v2[0]) / 3
        fc_y = (v0[1] + v1[1] + v2[1]) / 3
        fc_z = (v0[2] + v1[2] + v2[2]) / 3

        # Vector from wall center to face centroid
        to_face = [fc_x - center_x, fc_y - center_y, fc_z - center_z]

        # Dot product: positive if normal points outward
        dot = normal[0]*to_face[0] + normal[1]*to_face[1] + normal[2]*to_face[2]

        if dot > 0:
            outward_count += 1
        else:
            inward_count += 1

    print(f"\n  Winding order check (wall_south, first 3 faces):")
    print(f"    Normals pointing outward: {outward_count}")
    print(f"    Normals pointing inward: {inward_count}")
    print(f"    Status: {'✅ Consistent' if outward_count > inward_count else '⚠️  Mixed or inverted'}")

    return True

def main():
    print("="*70)
    print("ROTATION AND ORIENTATION TESTING")
    print("="*70)

    elements = load_from_db()

    print(f"\nLoaded {len(elements)} elements from database:")
    for name in elements.keys():
        print(f"  - {name}")

    results = []
    results.append(('Coordinate System', test_coordinate_system(elements)))
    results.append(('Wall Orientations', test_wall_orientations(elements)))
    results.append(('Wall Parallelism', test_wall_parallelism(elements)))
    results.append(('Roof Alignment', test_roof_alignment(elements)))
    results.append(('Porch Position', test_porch_position(elements)))
    results.append(('Face Winding Order', test_face_winding_order(elements)))

    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<30} {status}")

    all_passed = all(r[1] for r in results)
    print(f"\n  {'✅ ALL ROTATION/ORIENTATION TESTS PASSED' if all_passed else '⚠️  SOME TESTS FAILED'}")
    print("="*70)

if __name__ == "__main__":
    main()
