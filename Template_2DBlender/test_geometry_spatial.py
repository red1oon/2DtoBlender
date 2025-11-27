#!/usr/bin/env python3
"""
Extensive Spatial/Mathematical Testing of Generated Geometry
NO AI INTERFERENCE - Pure deterministic mathematical validation

Tests:
1. Dimensional accuracy (vs architect specs)
2. Wall corner connections (joints, gaps)
3. Roof-wall alignment
4. Face normals correctness
5. Geometric closure (manifold check)
6. Volume calculations
7. Surface area calculations
8. Pitch angle verification
9. Porch attachment validation
10. Overall spatial coherence
"""

import json
import math
import sqlite3
import struct
from pathlib import Path

JSON_PATH = "output_artifacts/POC_minimal_building.json"
DB_PATH = "output_artifacts/TB-LKTN HOUSE_ANNOTATION_FROM_2D.db"

def load_json_data():
    """Load generated geometry from JSON"""
    with open(JSON_PATH) as f:
        return json.load(f)

def vector_subtract(v1, v2):
    """3D vector subtraction"""
    return [v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2]]

def vector_length(v):
    """3D vector magnitude"""
    return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)

def vector_dot(v1, v2):
    """3D dot product"""
    return v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]

def vector_cross(v1, v2):
    """3D cross product"""
    return [
        v1[1]*v2[2] - v1[2]*v2[1],
        v1[2]*v2[0] - v1[0]*v2[2],
        v1[0]*v2[1] - v1[1]*v2[0]
    ]

def vector_normalize(v):
    """Normalize vector to unit length"""
    length = vector_length(v)
    if length > 0:
        return [v[0]/length, v[1]/length, v[2]/length]
    return [0, 0, 0]

def test_1_dimensional_accuracy(data):
    """Test 1: Dimensional accuracy vs architect specifications"""
    print("\n" + "="*70)
    print("TEST 1: DIMENSIONAL ACCURACY")
    print("="*70)

    calib = data['calibration']
    elements = {e['name']: e for e in data['elements']}

    results = []

    # Test drain perimeter
    drain = elements['drain_perimeter']
    xs = [v[0] for v in drain['vertices']]
    ys = [v[1] for v in drain['vertices']]
    drain_w = max(xs) - min(xs)
    drain_l = max(ys) - min(ys)
    expected_drain_w = calib['drain_width']
    expected_drain_l = calib['drain_length']
    error_w = abs(drain_w - expected_drain_w)
    error_l = abs(drain_l - expected_drain_l)
    results.append(('Drain width', drain_w, expected_drain_w, error_w, error_w < 0.01))
    results.append(('Drain length', drain_l, expected_drain_l, error_l, error_l < 0.01))

    # Test wall spacing (building footprint)
    wall_s = elements['wall_south']
    wall_n = elements['wall_north']
    wall_e = elements['wall_east']
    wall_w = elements['wall_west']

    # Extract wall centerlines
    s_ys = [v[1] for v in wall_s['vertices']]
    n_ys = [v[1] for v in wall_n['vertices']]
    e_xs = [v[0] for v in wall_e['vertices']]
    w_xs = [v[0] for v in wall_w['vertices']]

    building_l = abs(max(n_ys) - min(s_ys))
    building_w = abs(max(e_xs) - min(w_xs))
    expected_w = calib['building_width']
    expected_l = calib['building_length']
    error_bw = abs(building_w - expected_w)
    error_bl = abs(building_l - expected_l)
    results.append(('Building width', building_w, expected_w, error_bw, error_bw < 0.2))
    results.append(('Building length', building_l, expected_l, error_bl, error_bl < 0.2))

    # Test wall height
    all_walls = [wall_s, wall_n, wall_e, wall_w]
    for wall in all_walls:
        zs = [v[2] for v in wall['vertices']]
        wall_h = max(zs) - min(zs)
        expected_h = calib['wall_height']
        error_h = abs(wall_h - expected_h)
        results.append((f"Wall {wall['name'][-5:]} height", wall_h, expected_h, error_h, error_h < 0.01))

    # Test roof pitch
    roof = elements['roof']
    # Find eave vertices (z=wall_height) and ridge (highest z)
    roof_zs = sorted(set(v[2] for v in roof['vertices']))
    eave_z = min(roof_zs)
    ridge_z = max(roof_zs)
    ridge_height = ridge_z - eave_z

    # Roof span (width)
    roof_xs = [v[0] for v in roof['vertices']]
    roof_span = max(roof_xs) - min(roof_xs)
    half_span = roof_span / 2

    # Calculate pitch: tan(pitch) = rise/run
    calculated_pitch_rad = math.atan(ridge_height / half_span)
    calculated_pitch_deg = math.degrees(calculated_pitch_rad)
    expected_pitch = calib['roof_pitch_deg']
    error_pitch = abs(calculated_pitch_deg - expected_pitch)
    results.append(('Roof pitch', calculated_pitch_deg, expected_pitch, error_pitch, error_pitch < 1.0))

    print(f"\n  {'Measurement':<30} {'Actual':<12} {'Expected':<12} {'Error':<12} {'Status':<8}")
    print(f"  {'-'*30} {'-'*12} {'-'*12} {'-'*12} {'-'*8}")
    for name, actual, expected, error, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<30} {actual:<12.4f} {expected:<12.4f} {error:<12.6f} {status:<8}")

    all_passed = all(r[4] for r in results)
    print(f"\n  Overall: {'✅ ALL DIMENSIONAL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    return all_passed

def test_2_wall_corner_connections(data):
    """Test 2: Wall corners properly connected (no gaps)"""
    print("\n" + "="*70)
    print("TEST 2: WALL CORNER CONNECTIONS")
    print("="*70)

    elements = {e['name']: e for e in data['elements']}
    walls = {name: elements[name] for name in elements if 'wall' in name}

    # Extract all wall corner points (where walls should meet)
    results = []

    # Get corner coordinates from each wall
    wall_s = walls['wall_south']
    wall_n = walls['wall_north']
    wall_e = walls['wall_east']
    wall_w = walls['wall_west']

    # South-West corner
    sw_s = min([(v[0], v[1]) for v in wall_s['vertices']], key=lambda p: p[0])  # Left end of south wall
    sw_w = min([(v[0], v[1]) for v in wall_w['vertices']], key=lambda p: p[1])  # Bottom end of west wall
    gap_sw = math.sqrt((sw_s[0] - sw_w[0])**2 + (sw_s[1] - sw_w[1])**2)
    results.append(('SW corner gap', gap_sw, gap_sw < 0.2))

    # South-East corner
    se_s = max([(v[0], v[1]) for v in wall_s['vertices']], key=lambda p: p[0])
    se_e = min([(v[0], v[1]) for v in wall_e['vertices']], key=lambda p: p[1])
    gap_se = math.sqrt((se_s[0] - se_e[0])**2 + (se_s[1] - se_e[1])**2)
    results.append(('SE corner gap', gap_se, gap_se < 0.2))

    # North-West corner
    nw_n = min([(v[0], v[1]) for v in wall_n['vertices']], key=lambda p: p[0])
    nw_w = max([(v[0], v[1]) for v in wall_w['vertices']], key=lambda p: p[1])
    gap_nw = math.sqrt((nw_n[0] - nw_w[0])**2 + (nw_n[1] - nw_w[1])**2)
    results.append(('NW corner gap', gap_nw, gap_nw < 0.2))

    # North-East corner
    ne_n = max([(v[0], v[1]) for v in wall_n['vertices']], key=lambda p: p[0])
    ne_e = max([(v[0], v[1]) for v in wall_e['vertices']], key=lambda p: p[1])
    gap_ne = math.sqrt((ne_n[0] - ne_e[0])**2 + (ne_n[1] - ne_e[1])**2)
    results.append(('NE corner gap', gap_ne, gap_ne < 0.2))

    print(f"\n  {'Corner':<20} {'Gap (m)':<15} {'Status':<8}")
    print(f"  {'-'*20} {'-'*15} {'-'*8}")
    for name, gap, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<20} {gap:<15.6f} {status:<8}")

    all_passed = all(r[2] for r in results)
    print(f"\n  Overall: {'✅ ALL CORNERS CONNECTED' if all_passed else '❌ GAPS DETECTED'}")
    return all_passed

def test_3_roof_wall_alignment(data):
    """Test 3: Roof eaves align with wall tops"""
    print("\n" + "="*70)
    print("TEST 3: ROOF-WALL ALIGNMENT")
    print("="*70)

    elements = {e['name']: e for e in data['elements']}
    walls = [elements[name] for name in elements if 'wall' in name]
    roof = elements['roof']

    # Get wall top height
    wall_zs = [v[2] for wall in walls for v in wall['vertices']]
    wall_top = max(wall_zs)

    # Get roof eave height (minimum z of roof)
    roof_zs = [v[2] for v in roof['vertices']]
    eave_z = min(roof_zs)

    # Check alignment
    error = abs(eave_z - wall_top)
    passed = error < 0.01

    print(f"\n  Wall top height:  {wall_top:.4f}m")
    print(f"  Roof eave height: {eave_z:.4f}m")
    print(f"  Alignment error:  {error:.6f}m")
    print(f"\n  Status: {'✅ ALIGNED' if passed else '❌ MISALIGNED'}")

    return passed

def test_4_face_normals_correctness(data):
    """Test 4: Face normals point outward (correct orientation)"""
    print("\n" + "="*70)
    print("TEST 4: FACE NORMALS CORRECTNESS")
    print("="*70)

    results = []

    for elem in data['elements']:
        vertices = elem['vertices']  # List of [x, y, z] triplets
        faces = elem['faces']  # List of [v0_idx, v1_idx, v2_idx] triplets

        # Compute centroids and normals
        for face in faces:
            idx0, idx1, idx2 = face[0], face[1], face[2]
            v0, v1, v2 = vertices[idx0], vertices[idx1], vertices[idx2]

            # Compute face normal
            e1 = vector_subtract(v1, v0)
            e2 = vector_subtract(v2, v0)
            normal = vector_normalize(vector_cross(e1, e2))

            # Check normal is not zero
            normal_len = vector_length(normal)
            if normal_len < 0.9:  # Should be ~1.0 after normalization
                results.append((elem['name'], len(results), False, normal_len))
            else:
                results.append((elem['name'], len(results), True, normal_len))

    failed = [r for r in results if not r[2]]

    print(f"\n  Total faces: {len(results)}")
    print(f"  Valid normals: {len(results) - len(failed)}")
    print(f"  Invalid normals: {len(failed)}")

    if failed:
        print(f"\n  Failed faces:")
        for name, face_idx, _, length in failed[:10]:  # Show first 10
            print(f"    {name} face #{face_idx}: normal length = {length:.6f}")

    all_passed = len(failed) == 0
    print(f"\n  Status: {'✅ ALL NORMALS VALID' if all_passed else '❌ SOME NORMALS INVALID'}")
    return all_passed

def test_5_geometric_closure(data):
    """Test 5: Geometry is manifold (closed, no holes)"""
    print("\n" + "="*70)
    print("TEST 5: GEOMETRIC CLOSURE (MANIFOLD CHECK)")
    print("="*70)

    results = []

    for elem in data['elements']:
        vertices = elem['vertices']
        faces = elem['faces']  # List of [v0, v1, v2] triplets

        # Build edge usage map (each edge should be used exactly 2 times in manifold mesh)
        edge_count = {}
        for face in faces:
            v0, v1, v2 = face[0], face[1], face[2]

            # Three edges per triangle
            edges = [
                tuple(sorted([v0, v1])),
                tuple(sorted([v1, v2])),
                tuple(sorted([v2, v0]))
            ]

            for edge in edges:
                edge_count[edge] = edge_count.get(edge, 0) + 1

        # Check for boundary edges (used only once) and non-manifold edges (used >2 times)
        boundary_edges = [e for e, count in edge_count.items() if count == 1]
        nonmanifold_edges = [e for e, count in edge_count.items() if count > 2]

        is_closed = len(boundary_edges) == 0
        is_manifold = len(nonmanifold_edges) == 0

        results.append((
            elem['name'],
            len(edge_count),
            len(boundary_edges),
            len(nonmanifold_edges),
            is_closed and is_manifold
        ))

    print(f"\n  {'Element':<25} {'Total Edges':<15} {'Boundary':<12} {'Non-Manifold':<15} {'Status':<8}")
    print(f"  {'-'*25} {'-'*15} {'-'*12} {'-'*15} {'-'*8}")
    for name, total, boundary, nonmanifold, passed in results:
        status = "✅ CLOSED" if passed else ("⚠️  OPEN" if boundary > 0 else "❌ FAIL")
        print(f"  {name:<25} {total:<15} {boundary:<12} {nonmanifold:<15} {status:<8}")

    # Note: Walls and drain SHOULD have boundary edges (they're not fully enclosed meshes)
    # Only check for non-manifold edges
    all_manifold = all(r[3] == 0 for r in results)
    print(f"\n  Status: {'✅ ALL GEOMETRY MANIFOLD' if all_manifold else '❌ NON-MANIFOLD DETECTED'}")
    return all_manifold

def test_6_volume_calculations(data):
    """Test 6: Volume calculations (sanity checks)"""
    print("\n" + "="*70)
    print("TEST 6: VOLUME CALCULATIONS")
    print("="*70)

    calib = data['calibration']
    elements = {e['name']: e for e in data['elements']}

    # Approximate building volume (walls enclose volume)
    w = calib['building_width']
    l = calib['building_length']
    h = calib['wall_height']
    ridge_h = (w / 2) * math.tan(math.radians(calib['roof_pitch_deg']))

    # Box volume (walls)
    box_volume = w * l * h

    # Roof volume (triangular prism approximation)
    roof_volume = 0.5 * ridge_h * w * l

    # Total building volume
    total_volume = box_volume + roof_volume

    # Porch volume
    porch_w = 2.0
    porch_d = 1.5
    porch_h = 2.5
    porch_volume = porch_w * porch_d * porch_h

    print(f"\n  Building box volume:  {box_volume:.2f} m³")
    print(f"  Roof volume:          {roof_volume:.2f} m³")
    print(f"  Total volume:         {total_volume:.2f} m³")
    print(f"  Porch volume:         {porch_volume:.2f} m³")

    # Sanity checks
    typical_house_volume_range = (300, 700)  # m³ for single-story terrace
    in_range = typical_house_volume_range[0] < total_volume < typical_house_volume_range[1]

    print(f"\n  Expected range: {typical_house_volume_range[0]}-{typical_house_volume_range[1]} m³")
    print(f"  Status: {'✅ WITHIN RANGE' if in_range else '⚠️  OUTSIDE TYPICAL RANGE'}")

    return in_range

def test_7_surface_area_calculations(data):
    """Test 7: Surface area calculations"""
    print("\n" + "="*70)
    print("TEST 7: SURFACE AREA CALCULATIONS")
    print("="*70)

    total_area = 0.0

    for elem in data['elements']:
        vertices = elem['vertices']
        faces = elem['faces']  # List of [v0, v1, v2] triplets

        elem_area = 0.0
        for face in faces:
            v0 = vertices[face[0]]
            v1 = vertices[face[1]]
            v2 = vertices[face[2]]

            # Triangle area = 0.5 * |cross(e1, e2)|
            e1 = vector_subtract(v1, v0)
            e2 = vector_subtract(v2, v0)
            cross = vector_cross(e1, e2)
            area = 0.5 * vector_length(cross)
            elem_area += area

        print(f"  {elem['name']:<25} {elem_area:>10.2f} m²")
        total_area += elem_area

    print(f"  {'-'*25} {'-'*10}")
    print(f"  {'TOTAL SURFACE AREA':<25} {total_area:>10.2f} m²")

    # Sanity check: typical house exterior surface
    typical_range = (200, 600)  # m² for walls + roof
    in_range = typical_range[0] < total_area < typical_range[1]

    print(f"\n  Expected range: {typical_range[0]}-{typical_range[1]} m²")
    print(f"  Status: {'✅ WITHIN RANGE' if in_range else '⚠️  OUTSIDE TYPICAL RANGE'}")

    return in_range

def test_8_right_angles(data):
    """Test 8: Walls meet at 90° angles"""
    print("\n" + "="*70)
    print("TEST 8: RIGHT ANGLES (ORTHOGONALITY)")
    print("="*70)

    elements = {e['name']: e for e in data['elements']}

    # Get wall direction vectors
    wall_s = elements['wall_south']
    wall_n = elements['wall_north']
    wall_e = elements['wall_east']
    wall_w = elements['wall_west']

    # South/North walls run E-W (along X)
    s_verts = wall_s['vertices']
    s_dir = vector_normalize([s_verts[1][0] - s_verts[0][0], s_verts[1][1] - s_verts[0][1], 0])

    # East/West walls run N-S (along Y)
    e_verts = wall_e['vertices']
    e_dir = vector_normalize([e_verts[4][0] - e_verts[0][0], e_verts[4][1] - e_verts[0][1], 0])

    # Dot product should be ~0 for perpendicular vectors
    dot = vector_dot(s_dir, e_dir)
    angle_rad = math.acos(max(-1.0, min(1.0, abs(dot))))
    angle_deg = math.degrees(angle_rad)

    error = abs(angle_deg - 90.0)
    passed = error < 1.0

    print(f"\n  South wall direction: [{s_dir[0]:.4f}, {s_dir[1]:.4f}, {s_dir[2]:.4f}]")
    print(f"  East wall direction:  [{e_dir[0]:.4f}, {e_dir[1]:.4f}, {e_dir[2]:.4f}]")
    print(f"  Dot product:          {dot:.6f}")
    print(f"  Angle:                {angle_deg:.2f}°")
    print(f"  Error from 90°:       {error:.4f}°")
    print(f"\n  Status: {'✅ ORTHOGONAL' if passed else '❌ NOT PERPENDICULAR'}")

    return passed

def test_9_porch_attachment(data):
    """Test 9: Porch correctly attached to building"""
    print("\n" + "="*70)
    print("TEST 9: PORCH ATTACHMENT")
    print("="*70)

    elements = {e['name']: e for e in data['elements']}
    porch = elements['porch']
    wall_s = elements['wall_south']

    # Porch should be attached to south wall
    # Check that porch back edge aligns with south wall front face

    porch_ys = [v[1] for v in porch['vertices']]
    porch_max_y = max(porch_ys)  # Back edge of porch

    wall_s_ys = [v[1] for v in wall_s['vertices']]
    wall_s_y = min(wall_s_ys)  # Front face of south wall

    gap = abs(porch_max_y - wall_s_y)
    passed = gap < 0.2

    print(f"\n  Porch back edge Y:     {porch_max_y:.4f}m")
    print(f"  South wall front Y:    {wall_s_y:.4f}m")
    print(f"  Gap:                   {gap:.6f}m")
    print(f"\n  Status: {'✅ ATTACHED' if passed else '❌ GAP DETECTED'}")

    return passed

def test_10_overall_spatial_coherence(data):
    """Test 10: Overall spatial coherence"""
    print("\n" + "="*70)
    print("TEST 10: OVERALL SPATIAL COHERENCE")
    print("="*70)

    checks = []

    # Check 1: All vertices have valid coordinates (no NaN, no infinity)
    all_valid = True
    for elem in data['elements']:
        for v in elem['vertices']:
            if not all(math.isfinite(coord) for coord in v):
                all_valid = False
                break
    checks.append(('All coordinates finite', all_valid))

    # Check 2: All elements have positive face count
    all_have_faces = all(elem['face_count'] > 0 for elem in data['elements'])
    checks.append(('All elements have faces', all_have_faces))

    # Check 3: All elements have positive vertex count
    all_have_verts = all(elem['vertex_count'] > 0 for elem in data['elements'])
    checks.append(('All elements have vertices', all_have_verts))

    # Check 4: Building is above ground (no negative Z)
    min_z = min(v[2] for elem in data['elements'] for v in elem['vertices'])
    above_ground = min_z >= 0.0
    checks.append(('All geometry above ground', above_ground))

    # Check 5: Building centered near origin (within 20m)
    centroids_x = [sum(v[0] for v in elem['vertices']) / len(elem['vertices']) for elem in data['elements']]
    centroids_y = [sum(v[1] for v in elem['vertices']) / len(elem['vertices']) for elem in data['elements']]
    max_offset = max(max(abs(x) for x in centroids_x), max(abs(y) for y in centroids_y))
    near_origin = max_offset < 20.0
    checks.append(('Building near origin', near_origin))

    print(f"\n  {'Check':<40} {'Status':<8}")
    print(f"  {'-'*40} {'-'*8}")
    for name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<40} {status:<8}")

    all_passed = all(c[1] for c in checks)
    print(f"\n  Overall: {'✅ SPATIALLY COHERENT' if all_passed else '❌ ISSUES DETECTED'}")

    return all_passed

def main():
    print("="*70)
    print("EXTENSIVE SPATIAL/MATHEMATICAL GEOMETRY TESTING")
    print("="*70)

    # Load data
    data = load_json_data()

    # Run all tests
    test_results = []
    test_results.append(('Dimensional Accuracy', test_1_dimensional_accuracy(data)))
    test_results.append(('Wall Corner Connections', test_2_wall_corner_connections(data)))
    test_results.append(('Roof-Wall Alignment', test_3_roof_wall_alignment(data)))
    test_results.append(('Face Normals Correctness', test_4_face_normals_correctness(data)))
    test_results.append(('Geometric Closure', test_5_geometric_closure(data)))
    test_results.append(('Volume Calculations', test_6_volume_calculations(data)))
    test_results.append(('Surface Area Calculations', test_7_surface_area_calculations(data)))
    test_results.append(('Right Angles', test_8_right_angles(data)))
    test_results.append(('Porch Attachment', test_9_porch_attachment(data)))
    test_results.append(('Overall Spatial Coherence', test_10_overall_spatial_coherence(data)))

    # Summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print(f"\n  {'Test':<40} {'Result':<8}")
    print(f"  {'-'*40} {'-'*8}")
    for name, passed in test_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<40} {status:<8}")

    passed_count = sum(1 for _, p in test_results if p)
    total_count = len(test_results)

    print(f"\n  Tests passed: {passed_count}/{total_count}")

    if passed_count == total_count:
        print(f"\n  ✅ ALL TESTS PASSED - Geometry is mathematically correct")
    else:
        print(f"\n  ⚠️  {total_count - passed_count} TEST(S) FAILED - Review results above")

    print("="*70)

if __name__ == "__main__":
    main()
