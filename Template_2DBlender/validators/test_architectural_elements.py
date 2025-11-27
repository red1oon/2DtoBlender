#!/usr/bin/env python3
"""
Architectural Elements Validator - Critical building components

Specific tests for:
1. Roof - complete coverage, drainage, structure
2. Envelope Walls - closure, doors/windows placement
3. Porch - access, coverage, connection
4. Sanitary - fixtures, drainage, ventilation

These tests ensure the building is architecturally complete and functional.
"""

import json
import math
import sys
from collections import defaultdict


class ArchitecturalElementsTester:
    """Specialized tests for critical architectural elements"""

    def __init__(self, data):
        self.data = data
        self.objects = data.get('objects', [])
        self.metadata = data.get('extraction_metadata', {})
        self.building_dims = self.metadata.get('building_dimensions', {})
        self.errors = []
        self.warnings = []
        self.passed = 0
        self.failed = 0

    def log_error(self, test_name, message, details=None):
        """Log critical failure"""
        self.failed += 1
        self.errors.append({
            'test': test_name,
            'message': message,
            'details': details or []
        })

    def log_warning(self, test_name, message, details=None):
        """Log warning"""
        self.warnings.append({
            'test': test_name,
            'message': message,
            'details': details or []
        })

    def log_pass(self, test_name):
        """Log success"""
        self.passed += 1

    # =========================================================================
    # ROOF TESTS
    # =========================================================================

    def test_01_roof_presence(self):
        """Test 1: Roof structure exists"""
        print("\n" + "=" * 80)
        print("🏠 TEST 1: ROOF PRESENCE")
        print("=" * 80)

        roofs = [o for o in self.objects if 'roof' in o.get('object_type', '').lower()]

        if not roofs:
            self.log_error('Roof Presence',
                          'No roof structure found - building incomplete')
            print("❌ FAIL: No roof found")
        else:
            print(f"✅ PASS: {len(roofs)} roof element(s) found")
            for roof in roofs:
                print(f"   • {roof['name']}: {roof['object_type']}")
            self.log_pass('Roof Presence')

    def test_02_roof_coverage(self):
        """Test 2: Roof covers entire building footprint"""
        print("\n" + "=" * 80)
        print("🏠 TEST 2: ROOF COVERAGE")
        print("=" * 80)

        roofs = [o for o in self.objects if 'roof' in o.get('object_type', '').lower()]

        if not roofs:
            print("⚠️  SKIP: No roof to validate")
            return

        length = self.building_dims.get('length', 10.0)
        breadth = self.building_dims.get('breadth', 10.0)
        building_area = length * breadth

        for roof in roofs:
            dimensions = roof.get('dimensions', [])
            if len(dimensions) >= 2:
                roof_area = dimensions[0] * dimensions[1]
                coverage = (roof_area / building_area) * 100

                print(f"Building footprint: {length:.2f}m × {breadth:.2f}m = {building_area:.2f}m²")
                print(f"Roof area: {dimensions[0]:.2f}m × {dimensions[1]:.2f}m = {roof_area:.2f}m²")
                print(f"Coverage: {coverage:.1f}%")

                if coverage < 95:
                    self.log_error('Roof Coverage',
                                  f'Roof only covers {coverage:.1f}% of building (need >95%)')
                    print(f"❌ FAIL: Insufficient coverage")
                else:
                    print(f"✅ PASS: Complete coverage")
                    self.log_pass('Roof Coverage')
            else:
                self.log_warning('Roof Coverage',
                               'Roof dimensions not specified')
                print("⚠️  WARNING: Roof dimensions missing")

    def test_03_roof_drainage(self):
        """Test 3: Roof drainage system present"""
        print("\n" + "=" * 80)
        print("🏠 TEST 3: ROOF DRAINAGE")
        print("=" * 80)

        drains = [o for o in self.objects if 'drain' in o.get('object_type', '').lower()
                  and 'discharge' in o.get('object_type', '').lower()]
        gutters = [o for o in self.objects if 'gutter' in o.get('object_type', '').lower()]

        print(f"Discharge drains: {len(drains)}")
        print(f"Gutters: {len(gutters)}")

        if not drains and not gutters:
            self.log_error('Roof Drainage',
                          'No drainage system found - water damage risk')
            print("❌ FAIL: No drainage system")
        else:
            print("✅ PASS: Drainage system present")
            for drain in drains:
                print(f"   • {drain['name']}: {drain['object_type']}")
            self.log_pass('Roof Drainage')

    # =========================================================================
    # ENVELOPE WALL TESTS
    # =========================================================================

    def test_04_exterior_walls(self):
        """Test 4: Complete exterior wall enclosure"""
        print("\n" + "=" * 80)
        print("🧱 TEST 4: EXTERIOR WALL ENCLOSURE")
        print("=" * 80)

        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]
        exterior_walls = [w for w in walls if 'exterior' in w.get('name', '').lower()]

        print(f"Total walls: {len(walls)}")
        print(f"Exterior walls: {len(exterior_walls)}")

        if len(exterior_walls) < 4:
            self.log_error('Exterior Walls',
                          f'Only {len(exterior_walls)} exterior walls (need at least 4 for closure)')
            print(f"❌ FAIL: Incomplete enclosure")
        else:
            # Check if walls form a perimeter
            length = self.building_dims.get('length', 10.0)
            breadth = self.building_dims.get('breadth', 10.0)
            perimeter = 2 * (length + breadth)

            total_wall_length = 0
            for wall in exterior_walls:
                start = wall.get('position', [0, 0, 0])
                end = wall.get('end_point', [0, 0, 0])
                wall_length = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
                total_wall_length += wall_length

            coverage = (total_wall_length / perimeter) * 100
            print(f"Building perimeter: {perimeter:.2f}m")
            print(f"Total wall length: {total_wall_length:.2f}m")
            print(f"Coverage: {coverage:.1f}%")

            if coverage < 80:  # Allow for doors/windows
                self.log_warning('Exterior Walls',
                               f'Wall coverage only {coverage:.1f}% (gaps may exist)')
                print(f"⚠️  WARNING: Low wall coverage")
            else:
                print(f"✅ PASS: Complete enclosure")
                self.log_pass('Exterior Walls')

    def test_05_doors_in_walls(self):
        """Test 5: All doors positioned in walls (not free-standing)"""
        print("\n" + "=" * 80)
        print("🚪 TEST 5: DOORS IN WALLS")
        print("=" * 80)

        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        print(f"Total doors: {len(doors)}")
        print(f"Total walls: {len(walls)}")

        orphan_doors = []

        for door in doors:
            door_pos = door.get('position', [0, 0, 0])
            on_wall = False

            for wall in walls:
                w_start = wall.get('position', [0, 0, 0])
                w_end = wall.get('end_point', [0, 0, 0])

                dist = self._point_to_line_distance(door_pos, w_start, w_end)
                if dist < 0.3:  # Within 30cm of wall
                    on_wall = True
                    break

            if not on_wall:
                orphan_doors.append(door['name'])

        if orphan_doors:
            self.log_error('Doors in Walls',
                          f'{len(orphan_doors)} doors not in walls - structural issue',
                          orphan_doors)
            print(f"❌ FAIL: {len(orphan_doors)} orphan doors")
            for door in orphan_doors:
                print(f"   • {door}")
        else:
            print(f"✅ PASS: All {len(doors)} doors in walls")
            self.log_pass('Doors in Walls')

    def test_06_windows_in_walls(self):
        """Test 6: All windows positioned in walls"""
        print("\n" + "=" * 80)
        print("🪟 TEST 6: WINDOWS IN WALLS")
        print("=" * 80)

        windows = [o for o in self.objects if 'window' in o.get('object_type', '').lower()]
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        print(f"Total windows: {len(windows)}")
        print(f"Total walls: {len(walls)}")

        orphan_windows = []

        for window in windows:
            win_pos = window.get('position', [0, 0, 0])
            on_wall = False

            for wall in walls:
                w_start = wall.get('position', [0, 0, 0])
                w_end = wall.get('end_point', [0, 0, 0])

                dist = self._point_to_line_distance(win_pos, w_start, w_end)
                if dist < 0.3:
                    on_wall = True
                    break

            if not on_wall:
                orphan_windows.append(window['name'])

        if orphan_windows:
            self.log_error('Windows in Walls',
                          f'{len(orphan_windows)} windows not in walls',
                          orphan_windows)
            print(f"❌ FAIL: {len(orphan_windows)} orphan windows")
            for window in orphan_windows:
                print(f"   • {window}")
        else:
            print(f"✅ PASS: All {len(windows)} windows in walls")
            self.log_pass('Windows in Walls')

    def test_07_envelope_openings_ratio(self):
        """Test 7: Reasonable door/window to wall ratio"""
        print("\n" + "=" * 80)
        print("🏠 TEST 7: ENVELOPE OPENINGS RATIO")
        print("=" * 80)

        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]
        windows = [o for o in self.objects if 'window' in o.get('object_type', '').lower()]
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        total_openings = len(doors) + len(windows)

        print(f"Doors: {len(doors)}")
        print(f"Windows: {len(windows)}")
        print(f"Total openings: {total_openings}")
        print(f"Walls: {len(walls)}")

        if len(walls) > 0:
            ratio = total_openings / len(walls)
            print(f"Openings per wall: {ratio:.2f}")

            if ratio < 0.1:
                self.log_warning('Openings Ratio',
                               'Very few openings - ventilation concern')
                print("⚠️  WARNING: Too few openings")
            elif ratio > 2.0:
                self.log_warning('Openings Ratio',
                               'Many openings - structural concern')
                print("⚠️  WARNING: Too many openings")
            else:
                print("✅ PASS: Reasonable openings ratio")
                self.log_pass('Openings Ratio')
        else:
            print("⚠️  SKIP: No walls to compare")

    # =========================================================================
    # PORCH TESTS
    # =========================================================================

    def test_08_porch_presence(self):
        """Test 8: Porch or entrance canopy present"""
        print("\n" + "=" * 80)
        print("🏠 TEST 8: PORCH/ENTRANCE COVERAGE")
        print("=" * 80)

        porches = [o for o in self.objects if 'porch' in o.get('object_type', '').lower()
                   or 'canopy' in o.get('object_type', '').lower()
                   or 'porch' in o.get('name', '').lower()]

        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]

        if porches:
            print(f"✅ PASS: {len(porches)} porch/canopy found")
            for porch in porches:
                print(f"   • {porch['name']}: {porch['object_type']}")
            self.log_pass('Porch Presence')
        else:
            print(f"⚠️  INFO: No porch found (optional but recommended)")
            print(f"   Main entrance doors: {len(doors)}")
            self.log_warning('Porch Presence',
                           'No porch/canopy - weather exposure risk')

    def test_09_entrance_access(self):
        """Test 9: Main entrance accessible"""
        print("\n" + "=" * 80)
        print("🚪 TEST 9: ENTRANCE ACCESSIBILITY")
        print("=" * 80)

        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]

        if not doors:
            self.log_error('Entrance Access',
                          'No doors found - no building access')
            print("❌ FAIL: No entrance doors")
            return

        # Find main entrance (lowest Y coordinate = front of building)
        main_door = min(doors, key=lambda d: d.get('position', [0, 0, 0])[1])

        print(f"Total doors: {len(doors)}")
        print(f"Main entrance: {main_door['name']}")
        print(f"Position: {main_door.get('position', [0, 0, 0])}")

        # Check if main door is at ground level
        door_z = main_door.get('position', [0, 0, 0])[2]

        if door_z > 0.5:
            self.log_warning('Entrance Access',
                           f'Main door elevated ({door_z:.2f}m) - may need ramp/stairs')
            print(f"⚠️  WARNING: Elevated entrance")
        else:
            print(f"✅ PASS: Ground-level access")
            self.log_pass('Entrance Access')

    # =========================================================================
    # SANITARY TESTS
    # =========================================================================

    def test_10_sanitary_fixtures_complete(self):
        """Test 10: Complete sanitary fixture set"""
        print("\n" + "=" * 80)
        print("🚽 TEST 10: SANITARY FIXTURES COMPLETENESS")
        print("=" * 80)

        # Required fixtures for residential
        toilets = [o for o in self.objects if 'toilet' in o.get('object_type', '').lower()]
        basins = [o for o in self.objects if 'basin' in o.get('object_type', '').lower()]
        showers = [o for o in self.objects if 'shower' in o.get('object_type', '').lower()]

        print(f"Toilets: {len(toilets)}")
        print(f"Basins: {len(basins)}")
        print(f"Showers/baths: {len(showers)}")

        missing = []
        if len(toilets) == 0:
            missing.append('toilet')
        if len(basins) == 0:
            missing.append('basin')
        if len(showers) == 0:
            missing.append('shower')

        if missing:
            self.log_error('Sanitary Fixtures',
                          f'Missing fixtures: {", ".join(missing)}',
                          missing)
            print(f"❌ FAIL: Incomplete sanitary fixtures")
        else:
            print(f"✅ PASS: All essential fixtures present")
            self.log_pass('Sanitary Fixtures')

    def test_11_sanitary_drainage(self):
        """Test 11: Sanitary drainage system"""
        print("\n" + "=" * 80)
        print("🚽 TEST 11: SANITARY DRAINAGE")
        print("=" * 80)

        floor_drains = [o for o in self.objects if 'floor_drain' in o.get('object_type', '').lower()]
        toilets = [o for o in self.objects if 'toilet' in o.get('object_type', '').lower()]

        print(f"Floor drains: {len(floor_drains)}")
        print(f"Toilets (require drainage): {len(toilets)}")

        if len(toilets) > 0 and len(floor_drains) == 0:
            self.log_warning('Sanitary Drainage',
                           'No floor drains - water accumulation risk')
            print("⚠️  WARNING: No floor drains")
        else:
            print(f"✅ PASS: Drainage present")
            self.log_pass('Sanitary Drainage')

    def test_12_sanitary_ventilation(self):
        """Test 12: Bathroom ventilation"""
        print("\n" + "=" * 80)
        print("🚽 TEST 12: SANITARY VENTILATION")
        print("=" * 80)

        # Check for windows or exhaust fans in bathrooms
        windows = [o for o in self.objects if 'window' in o.get('object_type', '').lower()
                   and 'bathroom' in o.get('room', '').lower()]

        exhaust_fans = [o for o in self.objects if 'exhaust' in o.get('object_type', '').lower()
                        or 'fan' in o.get('object_type', '').lower()]

        print(f"Bathroom windows: {len(windows)}")
        print(f"Exhaust fans: {len(exhaust_fans)}")

        if len(windows) == 0 and len(exhaust_fans) == 0:
            self.log_warning('Sanitary Ventilation',
                           'No bathroom ventilation - humidity/mold risk')
            print("⚠️  WARNING: No ventilation")
        else:
            print(f"✅ PASS: Ventilation present")
            self.log_pass('Sanitary Ventilation')

    def test_13_water_supply_points(self):
        """Test 13: Water supply connection points"""
        print("\n" + "=" * 80)
        print("🚽 TEST 13: WATER SUPPLY POINTS")
        print("=" * 80)

        # Count fixtures requiring water supply
        toilets = [o for o in self.objects if 'toilet' in o.get('object_type', '').lower()]
        basins = [o for o in self.objects if 'basin' in o.get('object_type', '').lower()]
        showers = [o for o in self.objects if 'shower' in o.get('object_type', '').lower()]
        kitchen_sink = [o for o in self.objects if 'sink' in o.get('object_type', '').lower()
                        and 'kitchen' in o.get('object_type', '').lower()]

        total_supply_points = len(toilets) + len(basins) + len(showers) + len(kitchen_sink)

        print(f"Total water supply points needed: {total_supply_points}")
        print(f"   Toilets: {len(toilets)}")
        print(f"   Basins: {len(basins)}")
        print(f"   Showers: {len(showers)}")
        print(f"   Kitchen sinks: {len(kitchen_sink)}")

        if total_supply_points == 0:
            self.log_error('Water Supply',
                          'No water supply points - plumbing incomplete')
            print("❌ FAIL: No water fixtures")
        else:
            print(f"✅ PASS: {total_supply_points} supply points")
            self.log_pass('Water Supply')

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _point_to_line_distance(self, point, line_start, line_end):
        """Calculate perpendicular distance from point to line segment"""
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
        """Execute all 13 architectural element tests"""
        print("=" * 80)
        print("🏛️  ARCHITECTURAL ELEMENTS VALIDATOR")
        print("=" * 80)
        print("Critical building components: Roof, Walls, Porch, Sanitary")
        print(f"Total objects: {len(self.objects)}")
        print()

        # Run all tests
        self.test_01_roof_presence()
        self.test_02_roof_coverage()
        self.test_03_roof_drainage()
        self.test_04_exterior_walls()
        self.test_05_doors_in_walls()
        self.test_06_windows_in_walls()
        self.test_07_envelope_openings_ratio()
        self.test_08_porch_presence()
        self.test_09_entrance_access()
        self.test_10_sanitary_fixtures_complete()
        self.test_11_sanitary_drainage()
        self.test_12_sanitary_ventilation()
        self.test_13_water_supply_points()

        # Summary
        print("\n" + "=" * 80)
        print("📊 ARCHITECTURAL VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Total Tests: 13")
        print(f"  ✅ Passed: {self.passed}")
        print(f"  ❌ Failed: {self.failed}")
        print(f"  ⚠️  Warnings: {len(self.warnings)}")

        if self.errors:
            print("\n" + "=" * 80)
            print("❌ CRITICAL FAILURES")
            print("=" * 80)
            for error in self.errors:
                print(f"\n{error['test']}: {error['message']}")
                if error['details']:
                    for detail in error['details'][:5]:
                        print(f"  • {detail}")

        if self.warnings:
            print("\n" + "=" * 80)
            print("⚠️  WARNINGS")
            print("=" * 80)
            for warning in self.warnings:
                print(f"\n{warning['test']}: {warning['message']}")

        print("\n" + "=" * 80)
        if self.failed == 0:
            print("✅ ALL ARCHITECTURAL ELEMENTS VALIDATED")
            print("Building is structurally complete and functional")
        else:
            print("❌ CRITICAL ARCHITECTURAL ISSUES FOUND")
            print("Building may be incomplete or non-functional")
        print("=" * 80)

        return 0 if self.failed == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_architectural_elements.py <output.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    tester = ArchitecturalElementsTester(data)
    sys.exit(tester.run_all_tests())
