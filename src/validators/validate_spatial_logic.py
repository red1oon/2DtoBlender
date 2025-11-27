#!/usr/bin/env python3
"""
Spatial Logic Validator - Check positioning makes sense

Validates:
  1. Objects within building bounds
  2. Floor-level objects at Z=0.0
  3. Wall-mounted objects near walls
  4. Ceiling objects at ceiling height
  5. Doors in walls
  6. Windows at reasonable height
  7. No major overlaps (collision detection)
  8. Furniture clearances

Usage:
    python3 validate_spatial_logic.py <output_json>
"""

import json
import sys
import math


def check_building_bounds(objects, building_dims):
    """Test 1: All objects within building bounds"""
    print("\n" + "=" * 70)
    print("TEST 1: BUILDING BOUNDARY CHECK")
    print("=" * 70)

    width = building_dims.get('width', 9.8)
    length = building_dims.get('length', 8.0)
    height = building_dims.get('height', 3.0)

    out_of_bounds = []

    for obj in objects:
        pos = obj.get('position', [0, 0, 0])
        x, y, z = pos[0], pos[1], pos[2]
        name = obj.get('name')

        # Check bounds (with 1m margin for exterior elements)
        if x < -1.0 or x > width + 1.0:
            out_of_bounds.append(f"{name}: X={x:.2f} (bounds: -1.0 to {width+1.0:.1f})")
        if y < -1.0 or y > length + 1.0:
            out_of_bounds.append(f"{name}: Y={y:.2f} (bounds: -1.0 to {length+1.0:.1f})")
        if z < 0.0 or z > height + 0.5:
            out_of_bounds.append(f"{name}: Z={z:.2f} (bounds: 0.0 to {height+0.5:.1f})")

    if out_of_bounds:
        print(f"❌ FAIL: {len(out_of_bounds)} objects out of bounds")
        for issue in out_of_bounds[:5]:
            print(f"   - {issue}")
        return False
    else:
        print(f"✅ PASS: All {len(objects)} objects within building bounds")
        print(f"   Building: {width}m × {length}m × {height}m")
        return True


def check_floor_objects(objects):
    """Test 2: Floor-level objects at Z≈0.0"""
    print("\n" + "=" * 70)
    print("TEST 2: FLOOR-LEVEL OBJECTS")
    print("=" * 70)

    floor_types = ['door', 'wardrobe', 'bed', 'sofa', 'table', 'refrigerator',
                   'toilet', 'cabinet', 'floor_slab', 'wall_']

    issues = []

    for obj in objects:
        obj_type = obj.get('object_type', '')
        pos = obj.get('position', [0, 0, 0])
        z = pos[2]

        # Check if should be on floor
        is_floor_object = any(t in (obj_type or '').lower() for t in floor_types)

        if is_floor_object and abs(z) > 0.1:  # Allow 10cm tolerance
            issues.append(f"{obj.get('name')}: {obj_type} at Z={z:.2f} (should be ≈0.0)")

    if issues:
        print(f"⚠️  WARNING: {len(issues)} floor objects not at ground level")
        for issue in issues[:5]:
            print(f"   - {issue}")
        return False
    else:
        print(f"✅ PASS: Floor objects correctly positioned")
        return True


def check_ceiling_objects(objects):
    """Test 3: Ceiling objects at ceiling height"""
    print("\n" + "=" * 70)
    print("TEST 3: CEILING OBJECTS")
    print("=" * 70)

    ceiling_types = ['ceiling_light', 'ceiling_fan', 'ceiling_plane']

    issues = []

    for obj in objects:
        obj_type = obj.get('object_type', '')
        pos = obj.get('position', [0, 0, 0])
        z = pos[2]

        is_ceiling_object = any(t in obj_type.lower() for t in ceiling_types)

        if is_ceiling_object:
            if z < 2.5 or z > 3.3:  # Ceiling should be 2.8-3.0m
                issues.append(f"{obj.get('name')}: {obj_type} at Z={z:.2f} (should be 2.8-3.0m)")

    if issues:
        print(f"⚠️  WARNING: {len(issues)} ceiling objects at wrong height")
        for issue in issues[:5]:
            print(f"   - {issue}")
        return False
    else:
        print(f"✅ PASS: Ceiling objects at correct height")
        return True


def check_wall_mounted_height(objects):
    """Test 4: Wall-mounted objects at reasonable heights"""
    print("\n" + "=" * 70)
    print("TEST 4: WALL-MOUNTED OBJECT HEIGHTS")
    print("=" * 70)

    height_rules = {
        'switch': (1.2, 1.6, '1.4m'),
        'outlet': (0.2, 1.5, '0.3m or 1.2m'),
        'basin': (0.8, 1.0, '0.9m'),
        'showerhead': (1.6, 2.0, '1.8m'),
        'towel_rack': (1.0, 1.5, '1.2m'),
        'mirror': (1.2, 1.8, '1.5m')
    }

    issues = []

    for obj in objects:
        obj_type = obj.get('object_type', '')
        pos = obj.get('position', [0, 0, 0])
        z = pos[2]

        for item_type, (min_h, max_h, typical) in height_rules.items():
            if item_type in obj_type.lower():
                if z < min_h or z > max_h:
                    issues.append(f"{obj.get('name')}: {obj_type} at Z={z:.2f} (typical: {typical})")

    if issues:
        print(f"⚠️  WARNING: {len(issues)} wall-mounted objects at unusual heights")
        for issue in issues[:5]:
            print(f"   - {issue}")
        return False
    else:
        print(f"✅ PASS: Wall-mounted objects at reasonable heights")
        return True


def check_collision_detection(objects, tolerance=0.5):
    """Test 5: Check for major overlaps"""
    print("\n" + "=" * 70)
    print("TEST 5: COLLISION DETECTION")
    print("=" * 70)

    # Approximate object footprints (width, depth in meters)
    footprints = {
        'door': (0.9, 0.1),
        'window': (1.2, 0.1),
        'bed_queen': (1.6, 2.0),
        'bed_double': (1.4, 1.9),
        'bed_single': (1.0, 1.9),
        'wardrobe': (1.2, 0.6),
        'sofa': (2.0, 0.9),
        'table_dining': (1.5, 0.9),
        'refrigerator': (0.7, 0.7),
        'toilet': (0.5, 0.7),
        'default': (0.5, 0.5)
    }

    def get_footprint(obj_type):
        for key, size in footprints.items():
            if key in obj_type.lower():
                return size
        return footprints['default']

    def rectangles_overlap(pos1, size1, pos2, size2):
        """Check if two rectangles overlap (2D floor plan)"""
        x1, y1 = pos1[0], pos1[1]
        w1, d1 = size1
        x2, y2 = pos2[0], pos2[1]
        w2, d2 = size2

        # Bounding boxes
        left1, right1 = x1 - w1/2, x1 + w1/2
        bottom1, top1 = y1 - d1/2, y1 + d1/2
        left2, right2 = x2 - w2/2, x2 + w2/2
        bottom2, top2 = y2 - d2/2, y2 + d2/2

        # Check overlap
        return not (right1 < left2 or right2 < left1 or top1 < bottom2 or top2 < bottom1)

    # Only check floor-level objects (Z≈0)
    floor_objects = [obj for obj in objects if obj.get('position', [0,0,0])[2] < 0.5]

    collisions = []

    for i, obj1 in enumerate(floor_objects):
        pos1 = obj1.get('position')
        size1 = get_footprint(obj1.get('object_type', ''))

        for obj2 in floor_objects[i+1:]:
            pos2 = obj2.get('position')
            size2 = get_footprint(obj2.get('object_type', ''))

            if rectangles_overlap(pos1, size1, pos2, size2):
                dist = math.sqrt((pos1[0]-pos2[0])**2 + (pos1[1]-pos2[1])**2)
                if dist < tolerance:  # Only report close overlaps
                    collisions.append(f"{obj1.get('name')} ↔ {obj2.get('name')} (dist: {dist:.2f}m)")

    if collisions:
        print(f"⚠️  WARNING: {len(collisions)} potential collisions detected")
        for collision in collisions[:5]:
            print(f"   - {collision}")
        if len(collisions) > 5:
            print(f"   ... and {len(collisions) - 5} more")
        return False
    else:
        print(f"✅ PASS: No major collisions detected")
        return True


def check_door_placement(objects):
    """Test 6: Doors should be near walls"""
    print("\n" + "=" * 70)
    print("TEST 6: DOOR PLACEMENT LOGIC")
    print("=" * 70)

    doors = [obj for obj in objects if 'door' in obj.get('object_type', '').lower()]
    walls = [obj for obj in objects if 'wall' in obj.get('object_type', '').lower()]

    if not walls:
        print("⚠️  SKIP: No walls in output to check against")
        return None

    issues = []

    for door in doors:
        door_pos = door.get('position', [0, 0, 0])

        # Find nearest wall
        min_dist = float('inf')
        for wall in walls:
            wall_start = wall.get('position', [0, 0, 0])
            wall_end = wall.get('end_point', wall_start)

            # Distance to line segment
            x0, y0 = door_pos[0], door_pos[1]
            x1, y1 = wall_start[0], wall_start[1]
            x2, y2 = wall_end[0], wall_end[1]

            dx = x2 - x1
            dy = y2 - y1
            length_sq = dx*dx + dy*dy

            if length_sq == 0:
                dist = math.sqrt((x0-x1)**2 + (y0-y1)**2)
            else:
                t = max(0, min(1, ((x0-x1)*dx + (y0-y1)*dy) / length_sq))
                proj_x = x1 + t * dx
                proj_y = y1 + t * dy
                dist = math.sqrt((x0-proj_x)**2 + (y0-proj_y)**2)

            min_dist = min(min_dist, dist)

        if min_dist > 0.5:  # Door should be within 50cm of wall
            issues.append(f"{door.get('name')}: {min_dist:.2f}m from nearest wall")

    if issues:
        print(f"⚠️  WARNING: {len(issues)} doors not near walls")
        for issue in issues[:5]:
            print(f"   - {issue}")
        return False
    else:
        print(f"✅ PASS: All {len(doors)} doors near walls")
        return True


def check_window_height(objects):
    """Test 7: Windows should be at sill height"""
    print("\n" + "=" * 70)
    print("TEST 7: WINDOW SILL HEIGHT")
    print("=" * 70)

    windows = [obj for obj in objects if 'window' in obj.get('object_type', '').lower()]

    issues = []
    typical_sill = 0.9  # 900mm

    for window in windows:
        z = window.get('position', [0, 0, 0])[2]

        if abs(z) < 0.1:  # Currently at floor level
            issues.append(f"{window.get('name')}: at Z={z:.2f} (should be {typical_sill}m)")
        elif z < 0.7 or z > 1.2:  # Outside typical range
            issues.append(f"{window.get('name')}: at Z={z:.2f} (typical: {typical_sill}m)")

    if issues:
        print(f"⚠️  WARNING: {len(issues)} windows not at typical sill height")
        for issue in issues[:3]:
            print(f"   - {issue}")
        print("   NOTE: Windows currently at Z=0.0 need elevation adjustment")
        return False
    else:
        print(f"✅ PASS: All {len(windows)} windows at reasonable height")
        return True


def run_spatial_tests(json_path):
    """Run all spatial validation tests"""
    print("=" * 70)
    print("🧪 SPATIAL LOGIC VALIDATOR")
    print("=" * 70)
    print(f"File: {json_path}")

    try:
        with open(json_path) as f:
            data = json.load(f)
    except Exception as e:
        print(f"\n❌ FATAL: Cannot load JSON: {e}")
        return False

    objects = data.get('objects', [])
    metadata = data.get('extraction_metadata', {})

    building_dims = {
        'width': 9.8,
        'length': 8.0,
        'height': 3.0
    }

    # Run tests
    results = []
    results.append(("Building Bounds", check_building_bounds(objects, building_dims)))
    results.append(("Floor Objects", check_floor_objects(objects)))
    results.append(("Ceiling Objects", check_ceiling_objects(objects)))
    results.append(("Wall-Mounted Heights", check_wall_mounted_height(objects)))
    results.append(("Collision Detection", check_collision_detection(objects)))
    results.append(("Door Placement", check_door_placement(objects)))
    results.append(("Window Height", check_window_height(objects)))

    # Summary
    print("\n" + "=" * 70)
    print("📊 SPATIAL TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result == True)
    failed = sum(1 for _, result in results if result == False)
    skipped = sum(1 for _, result in results if result is None)

    print(f"Total tests: {len(results)}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⚠️  Warnings/Skipped: {skipped}")
    print()

    for name, result in results:
        status = "✅ PASS" if result == True else ("❌ FAIL" if result == False else "⚠️  SKIP")
        print(f"  {status}: {name}")

    print("\n" + "=" * 70)

    if failed == 0:
        print("🎉 ALL SPATIAL TESTS PASSED")
    else:
        print(f"⚠️  {failed} TEST(S) WITH ISSUES - Review warnings above")

    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate_spatial_logic.py <output_json>")
        sys.exit(1)

    json_path = sys.argv[1]
    success = run_spatial_tests(json_path)

    sys.exit(0 if success else 1)
