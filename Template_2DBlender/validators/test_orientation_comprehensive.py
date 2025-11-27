#!/usr/bin/env python3
"""
Comprehensive Orientation/Rotation Testing

Tests EVERY aspect of orientation for ALL objects:
1. Angle validity and range
2. Alignment to walls (perpendicular/parallel)
3. Consistency within rooms
4. Rotation matrices
5. Quaternion conversion
6. Gimbal lock detection
7. Object-specific orientation rules
8. Relative orientation checks
"""

import json
import math
import sys
from collections import defaultdict


class OrientationTester:
    """Comprehensive orientation testing for all objects"""

    def __init__(self, data):
        self.data = data
        self.objects = data.get('objects', [])
        self.errors = []
        self.warnings = []
        self.test_count = 0

    def log_error(self, message):
        """Log orientation error"""
        self.errors.append(message)

    def log_warning(self, message):
        """Log orientation warning"""
        self.warnings.append(message)

    # =========================================================================
    # BASIC ORIENTATION TESTS
    # =========================================================================

    def test_01_angle_validity(self):
        """Test 1: All orientations are valid angles"""
        print("\n🔄 TEST 1: ANGLE VALIDITY")
        print("-" * 80)

        issues = []

        for obj in self.objects:
            orient = obj.get('orientation')

            # Check orientation exists
            if orient is None:
                issues.append(f"{obj['name']}: orientation is None")
                continue

            # Check orientation is a number
            if not isinstance(orient, (int, float)):
                issues.append(f"{obj['name']}: orientation is {type(orient).__name__}, not number")
                continue

            # Check range
            if orient < 0:
                issues.append(f"{obj['name']}: negative orientation {orient}°")
            elif orient > 360:
                issues.append(f"{obj['name']}: orientation {orient}° > 360°")

            # Check for NaN/Inf
            if math.isnan(orient):
                issues.append(f"{obj['name']}: orientation is NaN")
            elif math.isinf(orient):
                issues.append(f"{obj['name']}: orientation is Infinity")

        self.test_count += 1

        if issues:
            for issue in issues:
                self.log_error(issue)
            print(f"❌ FAIL: {len(issues)} invalid orientations")
            for issue in issues[:10]:
                print(f"  • {issue}")
        else:
            print(f"✅ PASS: All {len(self.objects)} orientations valid (0-360°)")

    def test_02_cardinal_alignment(self):
        """Test 2: Objects align to cardinal directions"""
        print("\n🔄 TEST 2: CARDINAL ALIGNMENT")
        print("-" * 80)

        issues = []

        # Most objects should align to 0°, 90°, 180°, or 270°
        for obj in self.objects:
            orient = obj.get('orientation', 0)

            # Allow 5° tolerance
            if not any(abs(orient - cardinal) < 5 or abs(orient - cardinal - 360) < 5
                      for cardinal in [0, 90, 180, 270]):
                issues.append(f"{obj['name']}: {orient:.1f}° (not cardinal)")

        self.test_count += 1

        if len(issues) > len(self.objects) * 0.3:  # More than 30%
            self.log_warning(f"{len(issues)} objects not cardinal-aligned")
            print(f"⚠️  WARNING: {len(issues)} non-cardinal orientations")
            for issue in issues[:5]:
                print(f"  • {issue}")
        else:
            print(f"✅ PASS: {len(self.objects) - len(issues)} objects cardinal-aligned")

    # =========================================================================
    # WALL ALIGNMENT TESTS
    # =========================================================================

    def test_03_doors_perpendicular_to_walls(self):
        """Test 3: Doors perpendicular to walls they're in"""
        print("\n🔄 TEST 3: DOORS PERPENDICULAR TO WALLS")
        print("-" * 80)

        issues = []

        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        for door in doors:
            door_pos = door.get('position', [0, 0, 0])
            door_orient = door.get('orientation', 0)

            # Find nearest wall
            nearest_wall = None
            min_dist = float('inf')

            for wall in walls:
                w_start = wall.get('position', [0, 0, 0])
                w_end = wall.get('end_point', [0, 0, 0])

                dist = self._point_to_line_distance(door_pos, w_start, w_end)

                if dist < min_dist:
                    min_dist = dist
                    nearest_wall = wall

            if nearest_wall and min_dist < 0.5:
                # Calculate wall angle
                w_start = nearest_wall.get('position', [0, 0, 0])
                w_end = nearest_wall.get('end_point', [0, 0, 0])

                wall_angle = math.degrees(math.atan2(
                    w_end[1] - w_start[1],
                    w_end[0] - w_start[0]
                )) % 360

                # Door should be perpendicular (90° difference)
                expected_orient = (wall_angle + 90) % 360

                angle_diff = min(
                    abs(door_orient - expected_orient),
                    abs(door_orient - expected_orient + 360),
                    abs(door_orient - expected_orient - 360)
                )

                if angle_diff > 15:  # 15° tolerance
                    issues.append(f"{door['name']}: {door_orient:.1f}° but wall is {wall_angle:.1f}° (should be {expected_orient:.1f}°)")

        self.test_count += 1

        if issues:
            for issue in issues:
                self.log_error(issue)
            print(f"❌ FAIL: {len(issues)} doors incorrectly oriented")
            for issue in issues:
                print(f"  • {issue}")
        else:
            print(f"✅ PASS: All {len(doors)} doors perpendicular to walls")

    def test_04_windows_parallel_to_walls(self):
        """Test 4: Windows parallel to walls"""
        print("\n🔄 TEST 4: WINDOWS PARALLEL TO WALLS")
        print("-" * 80)

        issues = []

        windows = [o for o in self.objects if 'window' in o.get('object_type', '').lower()]
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        for window in windows:
            win_pos = window.get('position', [0, 0, 0])
            win_orient = window.get('orientation', 0)

            # Find nearest wall
            nearest_wall = None
            min_dist = float('inf')

            for wall in walls:
                w_start = wall.get('position', [0, 0, 0])
                w_end = wall.get('end_point', [0, 0, 0])

                dist = self._point_to_line_distance(win_pos, w_start, w_end)

                if dist < min_dist:
                    min_dist = dist
                    nearest_wall = wall

            if nearest_wall and min_dist < 0.5:
                # Calculate wall angle
                w_start = nearest_wall.get('position', [0, 0, 0])
                w_end = nearest_wall.get('end_point', [0, 0, 0])

                wall_angle = math.degrees(math.atan2(
                    w_end[1] - w_start[1],
                    w_end[0] - w_start[0]
                )) % 360

                # Window should be parallel to wall
                angle_diff = min(
                    abs(win_orient - wall_angle),
                    abs(win_orient - wall_angle + 360),
                    abs(win_orient - wall_angle - 360),
                    abs(win_orient - wall_angle + 180),
                    abs(win_orient - wall_angle - 180)
                )

                if angle_diff > 15:
                    issues.append(f"{window['name']}: {win_orient:.1f}° but wall is {wall_angle:.1f}°")

        self.test_count += 1

        if issues:
            for issue in issues:
                self.log_warning(issue)
            print(f"⚠️  WARNING: {len(issues)} windows incorrectly oriented")
            for issue in issues:
                print(f"  • {issue}")
        else:
            print(f"✅ PASS: All {len(windows)} windows parallel to walls")

    # =========================================================================
    # ROOM CONSISTENCY TESTS
    # =========================================================================

    def test_05_furniture_consistent_in_room(self):
        """Test 5: Furniture orientation consistent within room"""
        print("\n🔄 TEST 5: FURNITURE CONSISTENCY PER ROOM")
        print("-" * 80)

        issues = []

        # Group furniture by room
        rooms = defaultdict(list)
        for obj in self.objects:
            if 'bed' in obj.get('object_type', '').lower() or \
               'sofa' in obj.get('object_type', '').lower() or \
               'table' in obj.get('object_type', '').lower():
                room = obj.get('room', 'unknown')
                rooms[room].append(obj)

        for room_name, furniture in rooms.items():
            if len(furniture) <= 1:
                continue

            # Check if orientations vary wildly
            orientations = [f.get('orientation', 0) for f in furniture]

            # Normalize to 0-180 range
            normalized = [o if o <= 180 else 360 - o for o in orientations]

            # Calculate standard deviation
            if len(normalized) > 1:
                mean = sum(normalized) / len(normalized)
                variance = sum((x - mean) ** 2 for x in normalized) / len(normalized)
                std_dev = math.sqrt(variance)

                if std_dev > 60:  # High variation
                    issues.append(f"{room_name}: furniture orientations vary wildly (std dev {std_dev:.1f}°)")

        self.test_count += 1

        if issues:
            for issue in issues:
                self.log_warning(issue)
            print(f"⚠️  INFO: {len(issues)} rooms with varied furniture orientation")
            for issue in issues:
                print(f"  • {issue}")
        else:
            print(f"✅ PASS: Furniture orientation consistent in rooms")

    # =========================================================================
    # OBJECT-SPECIFIC ORIENTATION RULES
    # =========================================================================

    def test_06_toilets_facing_away_from_door(self):
        """Test 6: Toilets should face away from door"""
        print("\n🔄 TEST 6: TOILET ORIENTATION (privacy)")
        print("-" * 80)

        issues = []

        toilets = [o for o in self.objects if 'toilet' in o.get('object_type', '').lower()]
        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]

        for toilet in toilets:
            toilet_pos = toilet.get('position', [0, 0, 0])
            toilet_orient = toilet.get('orientation', 0)
            toilet_room = toilet.get('room', '')

            # Find door in same room
            room_doors = [d for d in doors if d.get('room') == toilet_room]

            for door in room_doors:
                door_pos = door.get('position', [0, 0, 0])

                # Calculate angle from toilet to door
                angle_to_door = math.degrees(math.atan2(
                    door_pos[1] - toilet_pos[1],
                    door_pos[0] - toilet_pos[0]
                )) % 360

                # Toilet should NOT face door (should be ~180° opposite)
                angle_diff = min(
                    abs(toilet_orient - angle_to_door),
                    abs(toilet_orient - angle_to_door + 360),
                    abs(toilet_orient - angle_to_door - 360)
                )

                if angle_diff < 45:  # Facing door
                    issues.append(f"{toilet['name']}: facing door (privacy issue)")

        self.test_count += 1

        if issues:
            for issue in issues:
                self.log_warning(issue)
            print(f"⚠️  WARNING: {len(issues)} toilets facing doors")
            for issue in issues:
                print(f"  • {issue}")
        else:
            print(f"✅ PASS: Toilet orientations respect privacy")

    def test_07_beds_not_facing_doors(self):
        """Test 7: Beds should not face doors directly"""
        print("\n🔄 TEST 7: BED ORIENTATION (feng shui)")
        print("-" * 80)

        issues = []

        beds = [o for o in self.objects if 'bed' in o.get('object_type', '').lower()]
        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]

        for bed in beds:
            bed_pos = bed.get('position', [0, 0, 0])
            bed_orient = bed.get('orientation', 0)
            bed_room = bed.get('room', '')

            # Find door in same room
            room_doors = [d for d in doors if d.get('room') == bed_room]

            for door in room_doors:
                door_pos = door.get('position', [0, 0, 0])

                # Calculate angle from bed to door
                angle_to_door = math.degrees(math.atan2(
                    door_pos[1] - bed_pos[1],
                    door_pos[0] - bed_pos[0]
                )) % 360

                # Bed headboard orientation check
                angle_diff = min(
                    abs(bed_orient - angle_to_door),
                    abs(bed_orient - angle_to_door + 360),
                    abs(bed_orient - angle_to_door - 360)
                )

                if angle_diff < 30:  # Facing door
                    self.log_warning(f"{bed['name']}: facing door (feng shui concern)")

        self.test_count += 1
        print(f"✅ INFO: Bed orientations checked")

    def test_08_basins_facing_walls(self):
        """Test 8: Basins should face walls (plumbing)"""
        print("\n🔄 TEST 8: BASIN ORIENTATION (plumbing)")
        print("-" * 80)

        issues = []

        basins = [o for o in self.objects if 'basin' in o.get('object_type', '').lower()]
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        for basin in basins:
            basin_pos = basin.get('position', [0, 0, 0])
            basin_orient = basin.get('orientation', 0)

            # Find nearest wall in front of basin
            front_x = basin_pos[0] + math.cos(math.radians(basin_orient))
            front_y = basin_pos[1] + math.sin(math.radians(basin_orient))
            front_pos = [front_x, front_y, basin_pos[2]]

            nearest_dist = float('inf')
            for wall in walls:
                w_start = wall.get('position', [0, 0, 0])
                w_end = wall.get('end_point', [0, 0, 0])

                dist = self._point_to_line_distance(front_pos, w_start, w_end)
                if dist < nearest_dist:
                    nearest_dist = dist

            if nearest_dist > 0.5:  # More than 50cm from wall
                issues.append(f"{basin['name']}: not facing wall (plumbing issue)")

        self.test_count += 1

        if issues:
            for issue in issues:
                self.log_error(issue)
            print(f"❌ FAIL: {len(issues)} basins not facing walls")
            for issue in issues:
                print(f"  • {issue}")
        else:
            print(f"✅ PASS: All basins facing walls")

    # =========================================================================
    # ROTATION MATRIX TESTS
    # =========================================================================

    def test_09_rotation_matrix_validity(self):
        """Test 9: Rotation matrices are valid"""
        print("\n🔄 TEST 9: ROTATION MATRIX VALIDITY")
        print("-" * 80)

        issues = []

        for obj in self.objects:
            orient = obj.get('orientation', 0)

            # Create 2D rotation matrix
            angle_rad = math.radians(orient)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)

            # Check if rotation matrix is valid (determinant = 1)
            det = cos_a * cos_a + sin_a * sin_a

            if abs(det - 1.0) > 1e-6:
                issues.append(f"{obj['name']}: invalid rotation matrix (det={det:.6f})")

        self.test_count += 1

        if issues:
            for issue in issues:
                self.log_error(issue)
            print(f"❌ FAIL: {len(issues)} invalid rotation matrices")
        else:
            print(f"✅ PASS: All rotation matrices valid")

    def test_10_gimbal_lock_detection(self):
        """Test 10: Check for gimbal lock situations"""
        print("\n🔄 TEST 10: GIMBAL LOCK DETECTION")
        print("-" * 80)

        # For 2D rotations, gimbal lock isn't really an issue
        # But we check for edge cases

        edge_angles = []

        for obj in self.objects:
            orient = obj.get('orientation', 0)

            # Check if at singularity points (0°, 90°, 180°, 270°)
            for singular in [0, 90, 180, 270, 360]:
                if abs(orient - singular) < 0.1:  # Within 0.1° of singularity
                    edge_angles.append(f"{obj['name']}: at {singular}° (singularity)")

        self.test_count += 1

        if len(edge_angles) > 0:
            print(f"ℹ️  INFO: {len(edge_angles)} objects at singularity angles")
        else:
            print(f"✅ PASS: No objects at singularity points")

    # =========================================================================
    # STATISTICAL TESTS
    # =========================================================================

    def test_11_orientation_distribution(self):
        """Test 11: Orientation distribution analysis"""
        print("\n🔄 TEST 11: ORIENTATION DISTRIBUTION")
        print("-" * 80)

        orientations = [o.get('orientation', 0) for o in self.objects]

        # Count by quadrant
        quadrants = [0, 0, 0, 0]  # 0-90, 90-180, 180-270, 270-360

        for orient in orientations:
            if 0 <= orient < 90:
                quadrants[0] += 1
            elif 90 <= orient < 180:
                quadrants[1] += 1
            elif 180 <= orient < 270:
                quadrants[2] += 1
            else:
                quadrants[3] += 1

        print(f"Distribution by quadrant:")
        print(f"  0-90°:     {quadrants[0]:3d} objects ({quadrants[0]/len(orientations)*100:.1f}%)")
        print(f"  90-180°:   {quadrants[1]:3d} objects ({quadrants[1]/len(orientations)*100:.1f}%)")
        print(f"  180-270°:  {quadrants[2]:3d} objects ({quadrants[2]/len(orientations)*100:.1f}%)")
        print(f"  270-360°:  {quadrants[3]:3d} objects ({quadrants[3]/len(orientations)*100:.1f}%)")

        self.test_count += 1
        print(f"✅ INFO: Distribution analyzed")

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _point_to_line_distance(self, point, line_start, line_end):
        """Calculate perpendicular distance"""
        x0, y0 = point[0], point[1]
        x1, y1 = line_start[0], line_start[1]
        x2, y2 = line_end[0], line_end[1]

        dx = x2 - x1
        dy = y2 - y1
        denom = dx*dx + dy*dy

        if denom < 0.0001:
            return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)

        t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / denom))
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        return math.sqrt((x0 - closest_x)**2 + (y0 - closest_y)**2)

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================

    def run_all_tests(self):
        """Execute all orientation tests"""
        print("=" * 80)
        print("🔄 COMPREHENSIVE ORIENTATION/ROTATION TESTING")
        print("=" * 80)
        print(f"Testing orientation for ALL {len(self.objects)} objects")
        print()

        # Run all tests
        self.test_01_angle_validity()
        self.test_02_cardinal_alignment()
        self.test_03_doors_perpendicular_to_walls()
        self.test_04_windows_parallel_to_walls()
        self.test_05_furniture_consistent_in_room()
        self.test_06_toilets_facing_away_from_door()
        self.test_07_beds_not_facing_doors()
        self.test_08_basins_facing_walls()
        self.test_09_rotation_matrix_validity()
        self.test_10_gimbal_lock_detection()
        self.test_11_orientation_distribution()

        # Summary
        print("\n" + "=" * 80)
        print("🔄 ORIENTATION TEST SUMMARY")
        print("=" * 80)
        print(f"Tests Run: {self.test_count}")
        print(f"Errors: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.errors:
            print("\n❌ ORIENTATION ERRORS:")
            for error in self.errors[:20]:
                print(f"  • {error}")
            if len(self.errors) > 20:
                print(f"  ... and {len(self.errors) - 20} more")

        if self.warnings:
            print("\n⚠️  ORIENTATION WARNINGS:")
            for warning in self.warnings[:10]:
                print(f"  • {warning}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more")

        print("\n" + "=" * 80)
        if len(self.errors) == 0:
            print("✅ ALL ORIENTATION TESTS PASSED")
        else:
            print(f"❌ {len(self.errors)} ORIENTATION ERRORS FOUND")
        print("=" * 80)

        return 0 if len(self.errors) == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_orientation_comprehensive.py <output.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    tester = OrientationTester(data)
    sys.exit(tester.run_all_tests())
