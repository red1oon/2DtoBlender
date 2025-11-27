#!/usr/bin/env python3
"""
Orientation Validation Suite

Implements DeepSeekOrientationGuide.txt validation requirements:
- Test door/window-wall orthogonality
- Test opening clearance (no clashes)
- Test consistent opening directions
- Generate validation report
"""

import json
import sys
import math
from typing import Dict, List, Tuple


class OrientationValidator:
    """Validate orientation accuracy per DeepSeek requirements"""

    def __init__(self, objects_file: str, relationships_file: str):
        with open(objects_file) as f:
            data = json.load(f)
            self.objects = data.get('objects_complete', [])

        with open(relationships_file) as f:
            rel_data = json.load(f)
            self.relationships = rel_data.get('relationships', [])

        self.doors = [o for o in self.objects if o.get('type') == 'door' and 'orientation' in o]
        self.windows = [o for o in self.objects if o.get('type') == 'window' and 'orientation' in o]
        self.walls = [o for o in self.objects if o.get('type') == 'wall']

        self.test_results = []
        self.failed_tests = []

    def run_all_tests(self):
        """Run complete validation suite"""
        print("="*80)
        print("ORIENTATION VALIDATION SUITE (DeepSeek Requirements)")
        print("="*80)
        print()

        print(f"Testing:")
        print(f"  Doors:   {len(self.doors)}")
        print(f"  Windows: {len(self.windows)}")
        print(f"  Walls:   {len(self.walls)}")
        print()

        # Test 1: Door/Window-Wall Orthogonality
        self.test_door_wall_orthogonality()

        # Test 2: Opening Clearance
        self.test_opening_clearance()

        # Test 3: Consistent Opening Directions
        self.test_consistent_opening_directions()

        # Print summary
        self.print_summary()

        return {
            'total_tests': len(self.test_results),
            'passed': sum(1 for t in self.test_results if t['passed']),
            'failed': len(self.failed_tests),
            'success_rate': self.calculate_success_rate(),
            'details': self.test_results,
            'failed_details': self.failed_tests
        }

    def test_door_wall_orthogonality(self):
        """
        Test 1: Verify openings are perpendicular to host walls (±5°)

        DeepSeek requirement:
        - Opening forward vector must be perpendicular to wall direction
        - Tolerance: ±5° deviation allowed
        """
        print("-"*80)
        print("TEST 1: DOOR/WINDOW-WALL ORTHOGONALITY")
        print("-"*80)
        print("Requirement: Opening perpendicular to wall (±5° tolerance)")
        print()

        openings = self.doors + self.windows
        passed = 0
        failed = 0

        for opening in openings:
            opening_id = opening.get('object_id') or opening.get('name')

            if 'orientation' not in opening:
                self.failed_tests.append({
                    'test': 'orthogonality',
                    'opening_id': opening_id,
                    'reason': 'No orientation data'
                })
                failed += 1
                continue

            orientation = opening['orientation']

            if not orientation.get('perpendicular_to_wall'):
                self.failed_tests.append({
                    'test': 'orthogonality',
                    'opening_id': opening_id,
                    'reason': 'Not marked as perpendicular'
                })
                failed += 1
                continue

            # Get wall
            wall_id = orientation.get('wall_id')
            if not wall_id:
                self.failed_tests.append({
                    'test': 'orthogonality',
                    'opening_id': opening_id,
                    'reason': 'No wall_id reference'
                })
                failed += 1
                continue

            wall = next((w for w in self.walls if (w.get('object_id') or w.get('name')) == wall_id), None)

            if not wall or 'end_point' not in wall:
                self.failed_tests.append({
                    'test': 'orthogonality',
                    'opening_id': opening_id,
                    'reason': f'Wall {wall_id} not found or invalid'
                })
                failed += 1
                continue

            # Calculate wall direction
            wall_start = wall['position']
            wall_end = wall['end_point']

            wall_vector = [
                wall_end[0] - wall_start[0],
                wall_end[1] - wall_start[1]
            ]

            wall_length = math.sqrt(wall_vector[0]**2 + wall_vector[1]**2)
            if wall_length > 0:
                wall_vector = [wall_vector[0]/wall_length, wall_vector[1]/wall_length]

            # Get opening facing direction
            facing = orientation['facing_direction']

            # Calculate angle between facing and wall
            dot_product = facing[0] * wall_vector[0] + facing[1] * wall_vector[1]
            angle = math.acos(max(-1, min(1, dot_product))) * 180 / math.pi

            # Should be 90° ± 5°
            deviation = abs(angle - 90.0)

            if deviation <= 5.0:
                passed += 1
                status = "✅"
            else:
                failed += 1
                status = "❌"
                self.failed_tests.append({
                    'test': 'orthogonality',
                    'opening_id': opening_id,
                    'wall_id': wall_id,
                    'angle': angle,
                    'deviation': deviation,
                    'reason': f'Deviation {deviation:.1f}° exceeds 5° tolerance'
                })

            print(f"{status} {opening_id:15s} → wall angle: {angle:5.1f}° (deviation: {deviation:4.1f}°)")

            self.test_results.append({
                'test': 'orthogonality',
                'opening_id': opening_id,
                'wall_id': wall_id,
                'angle': round(angle, 2),
                'deviation': round(deviation, 2),
                'passed': deviation <= 5.0
            })

        print()
        print(f"Result: {passed}/{len(openings)} passed ({passed/len(openings)*100:.1f}%)")
        print()

    def test_opening_clearance(self):
        """
        Test 2: Verify openings don't intersect adjacent walls

        DeepSeek requirement:
        - Opening bounding box must not intersect other walls
        - Tolerance: 5cm clearance
        """
        print("-"*80)
        print("TEST 2: OPENING CLEARANCE (NO WALL CLASHES)")
        print("-"*80)
        print("Requirement: Opening bounding box clear of other walls (5cm tolerance)")
        print()

        openings = self.doors + self.windows
        passed = 0
        failed = 0

        for opening in openings:
            opening_id = opening.get('object_id') or opening.get('name')

            if 'geometry' not in opening or 'bounding_box' not in opening['geometry']:
                self.failed_tests.append({
                    'test': 'clearance',
                    'opening_id': opening_id,
                    'reason': 'No bounding box geometry'
                })
                failed += 1
                continue

            bbox = opening['geometry']['bounding_box']
            bbox_min = bbox['min']
            bbox_max = bbox['max']

            # Find host wall
            host_wall_id = opening.get('orientation', {}).get('wall_id')

            # Check clearance to all OTHER walls
            clashes = []

            for wall in self.walls:
                wall_id = wall.get('object_id') or wall.get('name')

                # Skip host wall
                if wall_id == host_wall_id:
                    continue

                if 'end_point' not in wall:
                    continue

                # Calculate distance from bbox to wall
                distance = self._bbox_to_line_distance(
                    bbox_min, bbox_max,
                    wall['position'], wall['end_point']
                )

                if distance < 0.05:  # 5cm tolerance
                    clashes.append({
                        'wall_id': wall_id,
                        'distance': round(distance * 100, 1)  # cm
                    })

            if len(clashes) == 0:
                passed += 1
                print(f"✅ {opening_id:15s} → Clear (no clashes)")
                self.test_results.append({
                    'test': 'clearance',
                    'opening_id': opening_id,
                    'clashes': 0,
                    'passed': True
                })
            else:
                failed += 1
                print(f"❌ {opening_id:15s} → {len(clashes)} clash(es)")
                for clash in clashes:
                    print(f"   └─ Wall {clash['wall_id']}: {clash['distance']}cm clearance")

                self.failed_tests.append({
                    'test': 'clearance',
                    'opening_id': opening_id,
                    'clashes': clashes,
                    'reason': f'{len(clashes)} wall clash(es) found'
                })

                self.test_results.append({
                    'test': 'clearance',
                    'opening_id': opening_id,
                    'clashes': len(clashes),
                    'clash_details': clashes,
                    'passed': False
                })

        print()
        print(f"Result: {passed}/{len(openings)} passed ({passed/len(openings)*100:.1f}%)")
        print()

    def test_consistent_opening_directions(self):
        """
        Test 3: Verify logical opening conventions

        DeepSeek requirement:
        - Exterior doors should open inward (for security)
        - Check rotation angles are consistent (90° increments)
        """
        print("-"*80)
        print("TEST 3: CONSISTENT OPENING DIRECTIONS")
        print("-"*80)
        print("Requirement: Rotations use 90° increments (0°, 90°, 180°, 270°)")
        print()

        openings = self.doors + self.windows
        passed = 0
        failed = 0

        for opening in openings:
            opening_id = opening.get('object_id') or opening.get('name')

            if 'orientation' not in opening:
                failed += 1
                continue

            rotation = opening['orientation']['rotation_z']

            # Check if rotation is near a 90° increment
            nearest_90 = round(rotation / 90) * 90
            deviation = abs(rotation - nearest_90)

            if deviation <= 5.0:  # Within 5° of a 90° increment
                passed += 1
                print(f"✅ {opening_id:15s} → {rotation:6.1f}° (standard: {nearest_90:3.0f}°)")
                self.test_results.append({
                    'test': 'consistent_direction',
                    'opening_id': opening_id,
                    'rotation': rotation,
                    'nearest_standard': nearest_90,
                    'deviation': round(deviation, 2),
                    'passed': True
                })
            else:
                failed += 1
                print(f"⚠️  {opening_id:15s} → {rotation:6.1f}° (non-standard, deviation: {deviation:.1f}°)")
                self.failed_tests.append({
                    'test': 'consistent_direction',
                    'opening_id': opening_id,
                    'rotation': rotation,
                    'deviation': deviation,
                    'reason': f'Rotation not near 90° increment'
                })
                self.test_results.append({
                    'test': 'consistent_direction',
                    'opening_id': opening_id,
                    'rotation': rotation,
                    'nearest_standard': nearest_90,
                    'deviation': round(deviation, 2),
                    'passed': False
                })

        print()
        print(f"Result: {passed}/{len(openings)} passed ({passed/len(openings)*100:.1f}%)")
        print()

    def _bbox_to_line_distance(self, bbox_min: List[float], bbox_max: List[float],
                                line_start: List[float], line_end: List[float]) -> float:
        """Calculate minimum distance from bounding box to line segment"""
        # Get bbox corners (2D)
        corners = [
            [bbox_min[0], bbox_min[1]],
            [bbox_max[0], bbox_min[1]],
            [bbox_max[0], bbox_max[1]],
            [bbox_min[0], bbox_max[1]]
        ]

        # Find minimum distance from any corner to line
        min_distance = float('inf')

        for corner in corners:
            distance = self._point_to_line_distance(corner, line_start, line_end)
            min_distance = min(min_distance, distance)

        return min_distance

    def _point_to_line_distance(self, point: List[float], line_start: List[float], line_end: List[float]) -> float:
        """Calculate distance from point to line segment"""
        px, py = point[0], point[1]
        x1, y1 = line_start[0], line_start[1]
        x2, y2 = line_end[0], line_end[1]

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return math.sqrt((px - x1)**2 + (py - y1)**2)

        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx**2 + dy**2)))

        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)

    def calculate_success_rate(self) -> float:
        """Calculate overall success rate"""
        if len(self.test_results) == 0:
            return 0.0

        passed = sum(1 for t in self.test_results if t['passed'])
        return passed / len(self.test_results)

    def print_summary(self):
        """Print validation summary"""
        print("="*80)
        print("VALIDATION SUMMARY")
        print("="*80)
        print()

        total_tests = len(self.test_results)
        passed = sum(1 for t in self.test_results if t['passed'])
        failed = len(self.failed_tests)

        success_rate = self.calculate_success_rate() * 100

        print(f"📊 Total Tests:     {total_tests}")
        print(f"✅ Passed:          {passed} ({passed/total_tests*100:.1f}%)")
        print(f"❌ Failed:          {failed} ({failed/total_tests*100:.1f}%)")
        print()

        # DeepSeek requirements
        print("DeepSeek Requirements:")

        if success_rate >= 95:
            print(f"  ✅ Success rate: {success_rate:.1f}% (≥95% required) - PASS")
        else:
            print(f"  ❌ Success rate: {success_rate:.1f}% (≥95% required) - FAIL")

        max_deviation = max((t.get('deviation', 0) for t in self.test_results if 'deviation' in t), default=0)

        if max_deviation <= 2.0:
            print(f"  ✅ Max angular deviation: {max_deviation:.1f}° (≤2.0° required) - PASS")
        else:
            print(f"  ⚠️  Max angular deviation: {max_deviation:.1f}° (≤2.0° required) - MARGINAL")

        clash_count = sum(1 for t in self.test_results if t['test'] == 'clearance' and not t['passed'])

        if clash_count == 0:
            print(f"  ✅ Clash-free placements: 100% - PASS")
        else:
            print(f"  ❌ Clash-free placements: {(total_tests-clash_count)/total_tests*100:.1f}% - FAIL ({clash_count} clashes)")

        print()

        if failed > 0:
            print("Failed Tests:")
            for fail in self.failed_tests[:5]:  # Show first 5
                print(f"  ❌ {fail['test']:20s} | {fail['opening_id']:15s} | {fail['reason']}")
            if len(self.failed_tests) > 5:
                print(f"  ... and {len(self.failed_tests) - 5} more")
            print()

        print("-"*80)

        if success_rate >= 95 and max_deviation <= 2.0 and clash_count == 0:
            print("✅ VALIDATION PASSED - READY FOR BLENDER EXPORT")
        elif success_rate >= 90:
            print("⚠️  VALIDATION MARGINAL - REVIEW FAILURES BEFORE EXPORT")
        else:
            print("❌ VALIDATION FAILED - FIX ORIENTATION ISSUES")

        print("-"*80)
        print()


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 test_orientation.py <objects_with_orientation.json> <relationships.json> [report.json]")
        print()
        print("Validates orientation calculations per DeepSeek requirements")
        sys.exit(1)

    objects_file = sys.argv[1]
    relationships_file = sys.argv[2]
    report_file = sys.argv[3] if len(sys.argv) > 3 else 'orientation_validation_report.json'

    validator = OrientationValidator(objects_file, relationships_file)
    results = validator.run_all_tests()

    # Save report
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"✅ Validation report saved to: {report_file}")
    print()


if __name__ == "__main__":
    main()
