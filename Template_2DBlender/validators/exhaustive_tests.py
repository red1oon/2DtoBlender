#!/usr/bin/env python3
"""
Exhaustive Test Suite - Catch all potential failures before they happen

20+ comprehensive tests covering:
- Data integrity
- Geometric validity
- LOD compliance
- Spatial relationships
- Naming conventions
- IFC compatibility
- Blender readiness
"""

import json
import math
import sys
from pathlib import Path
from collections import Counter, defaultdict


class ExhaustiveTester:
    """Comprehensive testing with detailed error reporting"""

    def __init__(self, data):
        self.data = data
        self.objects = data.get('objects', [])
        self.metadata = data.get('extraction_metadata', {})
        self.summary = data.get('summary', {})
        self.errors = []
        self.warnings = []
        self.passed = 0
        self.failed = 0

    def log_error(self, test_name, message, details=None):
        """Log test failure with details"""
        self.failed += 1
        self.errors.append({
            'test': test_name,
            'message': message,
            'details': details or []
        })

    def log_warning(self, test_name, message, details=None):
        """Log test warning"""
        self.warnings.append({
            'test': test_name,
            'message': message,
            'details': details or []
        })

    def log_pass(self, test_name):
        """Log test success"""
        self.passed += 1

    # =========================================================================
    # DATA STRUCTURE TESTS
    # =========================================================================

    def test_01_json_structure(self):
        """Test 1: Validate complete JSON structure"""
        required_top = ['extraction_metadata', 'summary', 'objects']
        missing = [k for k in required_top if k not in self.data]

        if missing:
            self.log_error('JSON Structure',
                          f'Missing top-level keys: {missing}')
            return

        required_meta = ['extraction_timestamp', 'source_file', 'building_dimensions']
        missing_meta = [k for k in required_meta if k not in self.metadata]

        if missing_meta:
            self.log_error('JSON Structure',
                          f'Missing metadata keys: {missing_meta}')
            return

        self.log_pass('JSON Structure')

    def test_02_object_fields(self):
        """Test 2: Every object has ALL required fields"""
        required = ['name', 'object_type', 'position', 'orientation', 'placed', '_phase']

        incomplete = []
        for i, obj in enumerate(self.objects):
            missing = [f for f in required if f not in obj]
            if missing:
                incomplete.append(f"Object {i} ({obj.get('name', 'unnamed')}): missing {missing}")

        if incomplete:
            self.log_error('Object Fields',
                          f'{len(incomplete)} objects missing required fields',
                          incomplete[:10])
        else:
            self.log_pass('Object Fields')

    def test_03_hash_total_integrity(self):
        """Test 3: Hash total matches object count (data integrity)"""
        summary_total = self.summary.get('total_objects', 0)
        actual_count = len(self.objects)

        if summary_total != actual_count:
            self.log_error('Hash Total',
                          f'Summary says {summary_total} but found {actual_count} objects')
        else:
            self.log_pass('Hash Total')

    # =========================================================================
    # LOD300 COMPLIANCE TESTS
    # =========================================================================

    def test_04_lod300_compliance(self):
        """Test 4: 100% LOD300 compliance (CRITICAL)"""
        non_lod300 = []

        for obj in self.objects:
            obj_type = obj.get('object_type', '')
            if '_lod300' not in obj_type.lower():
                non_lod300.append(f"{obj['name']}: {obj_type}")

        if non_lod300:
            self.log_error('LOD300 Compliance',
                          f'{len(non_lod300)} objects not LOD300',
                          non_lod300[:20])
        else:
            self.log_pass('LOD300 Compliance')

    def test_05_object_type_naming(self):
        """Test 5: All object_types follow naming convention"""
        invalid = []

        for obj in self.objects:
            obj_type = obj.get('object_type', '')

            # Must contain _lod and end with number
            if not obj_type:
                invalid.append(f"{obj['name']}: empty object_type")
            elif '_lod' not in obj_type:
                invalid.append(f"{obj['name']}: {obj_type} (no LOD)")
            elif not obj_type[-1].isdigit():
                invalid.append(f"{obj['name']}: {obj_type} (doesn't end with number)")

        if invalid:
            self.log_error('Object Type Naming',
                          f'{len(invalid)} invalid object_types',
                          invalid[:20])
        else:
            self.log_pass('Object Type Naming')

    # =========================================================================
    # GEOMETRIC VALIDITY TESTS
    # =========================================================================

    def test_06_position_validity(self):
        """Test 6: All positions are valid 3D coordinates"""
        invalid = []

        for obj in self.objects:
            pos = obj.get('position')

            if not pos:
                invalid.append(f"{obj['name']}: no position")
            elif not isinstance(pos, list):
                invalid.append(f"{obj['name']}: position not array")
            elif len(pos) != 3:
                invalid.append(f"{obj['name']}: position not [X,Y,Z]")
            elif not all(isinstance(x, (int, float)) for x in pos):
                invalid.append(f"{obj['name']}: position contains non-numeric")
            elif any(math.isnan(x) or math.isinf(x) for x in pos):
                invalid.append(f"{obj['name']}: position contains NaN/Inf")

        if invalid:
            self.log_error('Position Validity',
                          f'{len(invalid)} invalid positions',
                          invalid[:20])
        else:
            self.log_pass('Position Validity')

    def test_07_orientation_validity(self):
        """Test 7: All orientations are valid degrees (0-360)"""
        invalid = []

        for obj in self.objects:
            orient = obj.get('orientation')

            if orient is None:
                invalid.append(f"{obj['name']}: no orientation")
            elif not isinstance(orient, (int, float)):
                invalid.append(f"{obj['name']}: orientation not numeric")
            elif math.isnan(orient) or math.isinf(orient):
                invalid.append(f"{obj['name']}: orientation is NaN/Inf")
            elif orient < 0 or orient > 360:
                invalid.append(f"{obj['name']}: orientation {orient}° out of range")

        if invalid:
            self.log_error('Orientation Validity',
                          f'{len(invalid)} invalid orientations',
                          invalid[:20])
        else:
            self.log_pass('Orientation Validity')

    def test_08_building_bounds(self):
        """Test 8: All objects within building boundaries"""
        dims = self.metadata.get('building_dimensions', {})
        length = dims.get('length', 10.0)
        breadth = dims.get('breadth', 10.0)
        height = dims.get('height', 3.0)

        out_of_bounds = []

        for obj in self.objects:
            pos = obj.get('position', [0, 0, 0])
            name = obj['name']

            if pos[0] < -1 or pos[0] > length + 1:
                out_of_bounds.append(f"{name}: X={pos[0]:.2f} (bounds: 0-{length})")
            if pos[1] < -1 or pos[1] > breadth + 1:
                out_of_bounds.append(f"{name}: Y={pos[1]:.2f} (bounds: 0-{breadth})")
            if pos[2] < -0.5 or pos[2] > height + 0.5:
                out_of_bounds.append(f"{name}: Z={pos[2]:.2f} (bounds: 0-{height})")

        if out_of_bounds:
            self.log_error('Building Bounds',
                          f'{len(out_of_bounds)} objects out of bounds',
                          out_of_bounds[:20])
        else:
            self.log_pass('Building Bounds')

    # =========================================================================
    # HEIGHT AND ELEVATION TESTS
    # =========================================================================

    def test_09_floor_objects(self):
        """Test 9: Floor-level objects at Z≈0"""
        floor_types = ['bed', 'wardrobe', 'sofa', 'table', 'floor', 'toilet', 'basin']
        incorrect = []

        for obj in self.objects:
            obj_type = obj.get('object_type', '').lower()
            pos = obj.get('position', [0, 0, 0])

            if any(t in obj_type for t in floor_types):
                if pos[2] > 0.2:  # Should be near ground
                    incorrect.append(f"{obj['name']}: {obj_type} at Z={pos[2]:.2f}")

        if incorrect:
            self.log_warning('Floor Objects',
                           f'{len(incorrect)} floor objects elevated',
                           incorrect[:15])
        else:
            self.log_pass('Floor Objects')

    def test_10_ceiling_objects(self):
        """Test 10: Ceiling objects at ceiling height"""
        ceiling_types = ['ceiling_light', 'ceiling_fan', 'ceiling_']
        incorrect = []
        ceiling_h = 2.8

        for obj in self.objects:
            obj_type = obj.get('object_type', '').lower()
            pos = obj.get('position', [0, 0, 0])

            if any(t in obj_type for t in ceiling_types):
                if abs(pos[2] - ceiling_h) > 0.5:
                    incorrect.append(f"{obj['name']}: {obj_type} at Z={pos[2]:.2f} (expected ~{ceiling_h}m)")

        if incorrect:
            self.log_warning('Ceiling Objects',
                           f'{len(incorrect)} ceiling objects at wrong height',
                           incorrect[:15])
        else:
            self.log_pass('Ceiling Objects')

    def test_11_wall_mounted_heights(self):
        """Test 11: Wall-mounted objects at reasonable heights"""
        height_rules = {
            'switch': (1.2, 1.6),
            'outlet': (0.2, 1.5),
            'basin': (0.8, 1.0),
            'towel': (1.0, 1.5),
            'showerhead': (1.6, 2.1),
            'mirror': (1.2, 1.8)
        }

        incorrect = []

        for obj in self.objects:
            obj_type = obj.get('object_type', '').lower()
            pos = obj.get('position', [0, 0, 0])

            for keyword, (min_h, max_h) in height_rules.items():
                if keyword in obj_type:
                    if not (min_h <= pos[2] <= max_h):
                        incorrect.append(f"{obj['name']}: {obj_type} at Z={pos[2]:.2f} (expected {min_h}-{max_h}m)")

        if incorrect:
            self.log_warning('Wall-Mounted Heights',
                           f'{len(incorrect)} objects at unusual heights',
                           incorrect[:15])
        else:
            self.log_pass('Wall-Mounted Heights')

    # =========================================================================
    # DUPLICATE DETECTION TESTS
    # =========================================================================

    def test_12_unique_names(self):
        """Test 12: All object names are unique"""
        names = [obj['name'] for obj in self.objects]
        name_counts = Counter(names)
        duplicates = [(name, count) for name, count in name_counts.items() if count > 1]

        if duplicates:
            self.log_error('Unique Names',
                          f'{len(duplicates)} duplicate names found',
                          [f"{name} (×{count})" for name, count in duplicates[:20]])
        else:
            self.log_pass('Unique Names')

    def test_13_duplicate_positions(self):
        """Test 13: No two non-wall objects at exactly same position"""
        positions = defaultdict(list)

        for obj in self.objects:
            if 'wall' in obj.get('object_type', '').lower():
                continue

            pos = tuple(round(x, 2) for x in obj.get('position', [0, 0, 0]))
            positions[pos].append(obj['name'])

        duplicates = [(pos, names) for pos, names in positions.items() if len(names) > 1]

        if duplicates:
            self.log_warning('Duplicate Positions',
                           f'{len(duplicates)} positions with multiple objects',
                           [f"{pos}: {names}" for pos, names in duplicates[:10]])
        else:
            self.log_pass('Duplicate Positions')

    # =========================================================================
    # WALL-SPECIFIC TESTS
    # =========================================================================

    def test_14_wall_endpoints(self):
        """Test 14: All walls have valid endpoints"""
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]
        invalid = []

        for wall in walls:
            start = wall.get('position')
            end = wall.get('end_point')

            if not end:
                invalid.append(f"{wall['name']}: no end_point")
            elif len(end) != 3:
                invalid.append(f"{wall['name']}: end_point not [X,Y,Z]")
            elif start and end:
                # Check length
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                length = math.sqrt(dx*dx + dy*dy)

                if length < 0.1:
                    invalid.append(f"{wall['name']}: too short ({length:.2f}m)")
                elif length > 20:
                    invalid.append(f"{wall['name']}: too long ({length:.2f}m)")

        if invalid:
            self.log_warning('Wall Endpoints',
                           f'{len(invalid)} walls with endpoint issues',
                           invalid[:15])
        else:
            self.log_pass('Wall Endpoints')

    def test_15_overlapping_walls(self):
        """Test 15: No completely overlapping walls"""
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]
        overlaps = []

        for i in range(len(walls)):
            for j in range(i + 1, len(walls)):
                w1 = walls[i]
                w2 = walls[j]

                # Check if start/end points are very close
                dist = self._wall_distance(w1, w2)
                if dist < 0.1:
                    overlaps.append(f"{w1['name']} ↔ {w2['name']}")

        if len(overlaps) > 5:  # Allow a few junctions
            self.log_warning('Overlapping Walls',
                           f'{len(overlaps)} wall overlaps detected',
                           overlaps[:10])
        else:
            self.log_pass('Overlapping Walls')

    def _wall_distance(self, w1, w2):
        """Calculate average distance between two walls"""
        p1s = w1.get('position', [0, 0, 0])
        p1e = w1.get('end_point', [0, 0, 0])
        p2s = w2.get('position', [0, 0, 0])
        p2e = w2.get('end_point', [0, 0, 0])

        distances = [
            math.sqrt(sum((a - b)**2 for a, b in zip(p1s, p2s))),
            math.sqrt(sum((a - b)**2 for a, b in zip(p1s, p2e))),
            math.sqrt(sum((a - b)**2 for a, b in zip(p1e, p2s))),
            math.sqrt(sum((a - b)**2 for a, b in zip(p1e, p2e)))
        ]

        return min(distances)

    # =========================================================================
    # DOOR AND WINDOW TESTS
    # =========================================================================

    def test_16_doors_on_walls(self):
        """Test 16: All doors positioned on walls"""
        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        orphans = []

        for door in doors:
            door_pos = door.get('position', [0, 0, 0])
            on_wall = False

            for wall in walls:
                w_start = wall.get('position', [0, 0, 0])
                w_end = wall.get('end_point', [0, 0, 0])

                dist = self._point_to_line_distance(door_pos, w_start, w_end)
                if dist < 0.4:
                    on_wall = True
                    break

            if not on_wall:
                orphans.append(door['name'])

        if orphans:
            self.log_warning('Doors on Walls',
                           f'{len(orphans)} doors not on walls',
                           orphans)
        else:
            self.log_pass('Doors on Walls')

    def _point_to_line_distance(self, point, line_start, line_end):
        """Calculate point-to-line segment distance"""
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

    def test_17_window_heights(self):
        """Test 17: Windows at reasonable sill heights"""
        windows = [o for o in self.objects if 'window' in o.get('object_type', '').lower()]
        incorrect = []

        for window in windows:
            pos = window.get('position', [0, 0, 0])
            if pos[2] < 0.5 or pos[2] > 1.5:
                incorrect.append(f"{window['name']}: sill at Z={pos[2]:.2f}m")

        if incorrect:
            self.log_warning('Window Heights',
                           f'{len(incorrect)} windows at unusual sill heights',
                           incorrect[:15])
        else:
            self.log_pass('Window Heights')

    # =========================================================================
    # PHASE AND CATEGORY TESTS
    # =========================================================================

    def test_18_phase_distribution(self):
        """Test 18: Objects properly distributed across phases"""
        phase_counts = Counter(obj.get('_phase', 'unknown') for obj in self.objects)

        if 'unknown' in phase_counts:
            self.log_warning('Phase Distribution',
                           f'{phase_counts["unknown"]} objects with unknown phase')

        # Check for expected phases
        expected_phases = ['1B_calibration', '1C_walls', '1C_structure',
                          '2_openings', '3_electrical', '4_plumbing', '6_furniture']

        missing = [p for p in expected_phases if p not in phase_counts]

        if missing:
            self.log_warning('Phase Distribution',
                           f'Missing phases: {missing}')
        else:
            self.log_pass('Phase Distribution')

    def test_19_room_assignment(self):
        """Test 19: All objects assigned to rooms"""
        no_room = [obj['name'] for obj in self.objects if not obj.get('room')]

        if no_room:
            self.log_warning('Room Assignment',
                           f'{len(no_room)} objects without room',
                           no_room[:20])
        else:
            self.log_pass('Room Assignment')

    # =========================================================================
    # BLENDER COMPATIBILITY TESTS
    # =========================================================================

    def test_20_placed_flags(self):
        """Test 20: All objects have placed=false before Blender"""
        incorrectly_placed = [obj['name'] for obj in self.objects if obj.get('placed', False)]

        if incorrectly_placed:
            self.log_error('Placed Flags',
                          f'{len(incorrectly_placed)} objects marked as placed',
                          incorrectly_placed[:20])
        else:
            self.log_pass('Placed Flags')

    def test_21_calibration_data(self):
        """Test 21: Valid calibration data present"""
        calib = self.metadata.get('calibration', {})

        required = ['scale_x', 'scale_y', 'offset_x', 'offset_y', 'confidence']
        missing = [k for k in required if k not in calib]

        if missing:
            self.log_error('Calibration Data',
                          f'Missing calibration fields: {missing}')
        elif calib.get('confidence', 0) < 50:
            self.log_warning('Calibration Data',
                           f'Low confidence: {calib["confidence"]}%')
        else:
            self.log_pass('Calibration Data')

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================

    def run_all_tests(self):
        """Execute all 21 tests"""
        tests = [
            self.test_01_json_structure,
            self.test_02_object_fields,
            self.test_03_hash_total_integrity,
            self.test_04_lod300_compliance,
            self.test_05_object_type_naming,
            self.test_06_position_validity,
            self.test_07_orientation_validity,
            self.test_08_building_bounds,
            self.test_09_floor_objects,
            self.test_10_ceiling_objects,
            self.test_11_wall_mounted_heights,
            self.test_12_unique_names,
            self.test_13_duplicate_positions,
            self.test_14_wall_endpoints,
            self.test_15_overlapping_walls,
            self.test_16_doors_on_walls,
            self.test_17_window_heights,
            self.test_18_phase_distribution,
            self.test_19_room_assignment,
            self.test_20_placed_flags,
            self.test_21_calibration_data
        ]

        print("=" * 80)
        print("🧪 EXHAUSTIVE TEST SUITE (21 Comprehensive Tests)")
        print("=" * 80)
        print(f"File: {sys.argv[1] if len(sys.argv) > 1 else 'N/A'}")
        print(f"Objects: {len(self.objects)}")
        print()

        for i, test in enumerate(tests, 1):
            test_name = test.__doc__.split(':')[1].strip() if ':' in test.__doc__ else test.__name__
            print(f"Running Test {i}/21: {test_name}...", end=' ')
            test()

            if self.errors and self.errors[-1]['test'] == test.__doc__.split(':')[0].strip():
                print("❌ FAIL")
            elif self.warnings and self.warnings[-1]['test'] == test.__doc__.split(':')[0].strip():
                print("⚠️  WARNING")
            else:
                print("✅ PASS")

        # Print detailed results
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS")
        print("=" * 80)
        print(f"Total Tests: 21")
        print(f"  ✅ Passed: {self.passed}")
        print(f"  ❌ Failed: {self.failed}")
        print(f"  ⚠️  Warnings: {len(self.warnings)}")

        if self.errors:
            print("\n" + "=" * 80)
            print("❌ FAILURES")
            print("=" * 80)
            for error in self.errors:
                print(f"\n{error['test']}: {error['message']}")
                if error['details']:
                    for detail in error['details'][:5]:
                        print(f"  • {detail}")
                    if len(error['details']) > 5:
                        print(f"  ... and {len(error['details']) - 5} more")

        if self.warnings:
            print("\n" + "=" * 80)
            print("⚠️  WARNINGS")
            print("=" * 80)
            for warning in self.warnings:
                print(f"\n{warning['test']}: {warning['message']}")
                if warning['details']:
                    for detail in warning['details'][:3]:
                        print(f"  • {detail}")
                    if len(warning['details']) > 3:
                        print(f"  ... and {len(warning['details']) - 3} more")

        print("\n" + "=" * 80)
        if self.failed == 0:
            print("✅ ALL CRITICAL TESTS PASSED")
        else:
            print("❌ CRITICAL FAILURES DETECTED - FIX REQUIRED")
        print("=" * 80)

        return 0 if self.failed == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 exhaustive_tests.py <output.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    tester = ExhaustiveTester(data)
    sys.exit(tester.run_all_tests())
