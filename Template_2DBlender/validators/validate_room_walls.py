#!/usr/bin/env python3
"""
Room and Wall Validator - Check walls enclosing rooms properly with no duplicates

Validates:
1. Rooms are enclosed by walls (no gaps)
2. Doors connect rooms properly
3. No duplicate walls (overlapping wall segments)
4. No duplicate doors in same location
"""

import json
import math
import sys
from collections import defaultdict


def distance_point_to_line(point, line_start, line_end):
    """Calculate perpendicular distance from point to line segment"""
    x0, y0 = point[0], point[1]
    x1, y1 = line_start[0], line_start[1]
    x2, y2 = line_end[0], line_end[1]

    # Vector from line start to end
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        # Degenerate line (point)
        return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)

    # Parameter t for projection onto line
    t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx**2 + dy**2)))

    # Closest point on line segment
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy

    # Distance
    return math.sqrt((x0 - closest_x)**2 + (y0 - closest_y)**2)


def walls_overlap(wall1, wall2, tolerance=0.1):
    """Check if two walls overlap (parallel and close together)"""
    w1_start = wall1['position']
    w1_end = wall1.get('end_point', w1_start)

    w2_start = wall2['position']
    w2_end = wall2.get('end_point', w2_start)

    # Check if line segments are parallel
    dx1 = w1_end[0] - w1_start[0]
    dy1 = w1_end[1] - w1_start[1]
    dx2 = w2_end[0] - w2_start[0]
    dy2 = w2_end[1] - w2_start[1]

    angle1 = math.atan2(dy1, dx1)
    angle2 = math.atan2(dy2, dx2)
    angle_diff = abs(angle1 - angle2)

    # Parallel if angle difference < 5 degrees
    if not (angle_diff < math.radians(5) or abs(angle_diff - math.pi) < math.radians(5)):
        return False

    # Check if walls are close (within tolerance)
    dist1 = distance_point_to_line(w1_start, w2_start, w2_end)
    dist2 = distance_point_to_line(w1_end, w2_start, w2_end)
    dist3 = distance_point_to_line(w2_start, w1_start, w1_end)
    dist4 = distance_point_to_line(w2_end, w1_start, w1_end)

    avg_dist = (dist1 + dist2 + dist3 + dist4) / 4

    return avg_dist < tolerance


def doors_overlap(door1, door2, tolerance=0.5):
    """Check if two doors are at the same location"""
    pos1 = door1['position']
    pos2 = door2['position']

    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    distance = math.sqrt(dx*dx + dy*dy)

    return distance < tolerance


def get_room_bounds(walls):
    """Calculate bounding box for room from walls"""
    if not walls:
        return None

    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')

    for wall in walls:
        start = wall['position']
        end = wall.get('end_point', start)

        min_x = min(min_x, start[0], end[0])
        min_y = min(min_y, start[1], end[1])
        max_x = max(max_x, start[0], end[0])
        max_y = max(max_y, start[1], end[1])

    return {
        'min_x': min_x,
        'max_x': max_x,
        'min_y': min_y,
        'max_y': max_y,
        'width': max_x - min_x,
        'height': max_y - min_y
    }


def check_room_enclosure(walls, doors, tolerance=0.3):
    """Check if walls properly enclose rooms with doors connecting them"""
    issues = []

    # Group walls by connectivity
    wall_groups = []
    used_walls = set()

    for i, wall in enumerate(walls):
        if i in used_walls:
            continue

        group = [wall]
        used_walls.add(i)

        # Find connected walls
        changed = True
        while changed:
            changed = False
            for j, other_wall in enumerate(walls):
                if j in used_walls:
                    continue

                # Check if other_wall connects to any wall in group
                for gwall in group:
                    g_start = gwall['position']
                    g_end = gwall.get('end_point', g_start)
                    o_start = other_wall['position']
                    o_end = other_wall.get('end_point', o_start)

                    # Check all endpoint combinations
                    for gp in [g_start, g_end]:
                        for op in [o_start, o_end]:
                            dx = gp[0] - op[0]
                            dy = gp[1] - op[1]
                            dist = math.sqrt(dx*dx + dy*dy)

                            if dist < tolerance:
                                group.append(other_wall)
                                used_walls.add(j)
                                changed = True
                                break
                        if changed:
                            break
                    if changed:
                        break
                if changed:
                    break

        wall_groups.append(group)

    # Check each room (wall group)
    for i, group in enumerate(wall_groups):
        if len(group) < 3:
            issues.append(f"Room {i+1}: Only {len(group)} walls (need at least 3-4 for enclosure)")
            continue

        bounds = get_room_bounds(group)
        perimeter = 2 * (bounds['width'] + bounds['height'])
        total_wall_length = sum([
            math.sqrt(
                (w.get('end_point', w['position'])[0] - w['position'][0])**2 +
                (w.get('end_point', w['position'])[1] - w['position'][1])**2
            )
            for w in group
        ])

        # Check if total wall length approximately equals perimeter
        # (allowing for door openings)
        coverage = total_wall_length / perimeter if perimeter > 0 else 0

        if coverage < 0.6:
            issues.append(f"Room {i+1}: Low wall coverage ({coverage*100:.1f}%) - possible gaps")
        elif coverage > 1.3:
            issues.append(f"Room {i+1}: Excessive walls ({coverage*100:.1f}%) - possible duplicates")

    return issues


def check_duplicate_walls(walls, tolerance=0.1):
    """Check for duplicate wall segments"""
    duplicates = []

    for i in range(len(walls)):
        for j in range(i+1, len(walls)):
            if walls_overlap(walls[i], walls[j], tolerance):
                duplicates.append((walls[i]['name'], walls[j]['name']))

    return duplicates


def check_duplicate_doors(doors, tolerance=0.5):
    """Check for doors at same location"""
    duplicates = []

    for i in range(len(doors)):
        for j in range(i+1, len(doors)):
            if doors_overlap(doors[i], doors[j], tolerance):
                duplicates.append((doors[i]['name'], doors[j]['name']))

    return duplicates


def check_doors_on_walls(doors, walls, tolerance=0.3):
    """Check that all doors are positioned on walls"""
    orphan_doors = []

    for door in doors:
        door_pos = door['position']
        on_wall = False

        for wall in walls:
            w_start = wall['position']
            w_end = wall.get('end_point', w_start)

            dist = distance_point_to_line(door_pos, w_start, w_end)
            if dist < tolerance:
                on_wall = True
                break

        if not on_wall:
            orphan_doors.append(door['name'])

    return orphan_doors


def validate_room_walls(data):
    """Main validation function"""
    print("=" * 80)
    print("🏠 ROOM AND WALL VALIDATOR")
    print("=" * 80)

    objects = data.get('objects', [])

    # Filter walls and doors
    walls = [o for o in objects if 'wall' in o.get('object_type', '').lower()]
    doors = [o for o in objects if 'door' in o.get('object_type', '').lower()]

    print(f"\nFound {len(walls)} walls and {len(doors)} doors")

    all_passed = True

    # Test 1: Check duplicate walls
    print("\n" + "=" * 80)
    print("TEST 1: DUPLICATE WALL DETECTION")
    print("=" * 80)

    dup_walls = check_duplicate_walls(walls, tolerance=0.1)

    if dup_walls:
        print(f"❌ FAIL: {len(dup_walls)} duplicate wall pairs found:")
        for w1, w2 in dup_walls[:10]:
            print(f"   - {w1} ↔ {w2}")
        if len(dup_walls) > 10:
            print(f"   ... and {len(dup_walls) - 10} more")
        all_passed = False
    else:
        print("✅ PASS: No duplicate walls detected")

    # Test 2: Check duplicate doors
    print("\n" + "=" * 80)
    print("TEST 2: DUPLICATE DOOR DETECTION")
    print("=" * 80)

    dup_doors = check_duplicate_doors(doors, tolerance=0.5)

    if dup_doors:
        print(f"❌ FAIL: {len(dup_doors)} duplicate door pairs found:")
        for d1, d2 in dup_doors:
            print(f"   - {d1} ↔ {d2}")
        all_passed = False
    else:
        print("✅ PASS: No duplicate doors detected")

    # Test 3: Check doors on walls
    print("\n" + "=" * 80)
    print("TEST 3: DOORS POSITIONED ON WALLS")
    print("=" * 80)

    orphan_doors = check_doors_on_walls(doors, walls, tolerance=0.3)

    if orphan_doors:
        print(f"❌ FAIL: {len(orphan_doors)} doors not on walls:")
        for d in orphan_doors:
            print(f"   - {d}")
        all_passed = False
    else:
        print("✅ PASS: All doors positioned on walls")

    # Test 4: Check room enclosure
    print("\n" + "=" * 80)
    print("TEST 4: ROOM ENCLOSURE CHECK")
    print("=" * 80)

    enclosure_issues = check_room_enclosure(walls, doors, tolerance=0.3)

    if enclosure_issues:
        print(f"⚠️  WARNING: {len(enclosure_issues)} room enclosure issues:")
        for issue in enclosure_issues:
            print(f"   - {issue}")
    else:
        print("✅ PASS: Rooms properly enclosed by walls")

    # Summary
    print("\n" + "=" * 80)
    print("📊 VALIDATION SUMMARY")
    print("=" * 80)

    if all_passed and not enclosure_issues:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("⚠️  SOME ISSUES FOUND - Review above")
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate_room_walls.py <output.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    sys.exit(validate_room_walls(data))
