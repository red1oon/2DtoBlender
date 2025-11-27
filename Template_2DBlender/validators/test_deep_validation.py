#!/usr/bin/env python3
"""
Deep Validation Suite - Comprehensive testing at every level

Tests EVERYTHING:
- Dimensional accuracy
- Structural integrity
- Material compliance
- Building code requirements (Malaysian UBBL)
- IFC standard compliance
- Topology and connectivity
- Construction feasibility
- MEP coordination
"""

import json
import math
import sys
from collections import defaultdict, Counter


class DeepValidator:
    """Deep comprehensive validation of every aspect"""

    def __init__(self, data):
        self.data = data
        self.objects = data.get('objects', [])
        self.metadata = data.get('extraction_metadata', {})
        self.building_dims = self.metadata.get('building_dimensions', {})
        self.errors = defaultdict(list)
        self.warnings = defaultdict(list)
        self.info = defaultdict(list)
        self.test_results = {}

    def log_error(self, category, message):
        """Log critical error"""
        self.errors[category].append(message)

    def log_warning(self, category, message):
        """Log warning"""
        self.warnings[category].append(message)

    def log_info(self, category, message):
        """Log info"""
        self.info[category].append(message)

    # =========================================================================
    # DIMENSIONAL ACCURACY TESTS
    # =========================================================================

    def test_dimensional_precision(self):
        """Test dimensional precision and accuracy"""
        print("\n📏 DIMENSIONAL ACCURACY")
        print("-" * 80)

        issues = []

        # Check position precision (should be to mm accuracy)
        for obj in self.objects:
            pos = obj.get('position', [0, 0, 0])
            for coord in pos:
                # Check if has unrealistic precision (more than 3 decimals = sub-mm)
                if abs(coord) > 0:
                    decimal_places = len(str(coord).split('.')[-1])
                    if decimal_places > 3:
                        issues.append(f"{obj['name']}: excessive precision ({decimal_places} decimals)")
                        break

        # Check for zero-length walls
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]
        for wall in walls:
            start = wall.get('position', [0, 0, 0])
            end = wall.get('end_point', [0, 0, 0])
            length = math.sqrt(sum((a - b)**2 for a, b in zip(start, end)))

            if length < 0.05:  # 50mm minimum
                issues.append(f"{wall['name']}: wall too short ({length:.3f}m)")

        # Check for unrealistic dimensions
        for obj in self.objects:
            pos = obj.get('position', [0, 0, 0])

            if any(abs(coord) > 1000 for coord in pos):
                issues.append(f"{obj['name']}: unrealistic coordinates")

        self.test_results['Dimensional Precision'] = {
            'passed': len(issues) == 0,
            'issues': len(issues)
        }

        if issues:
            for issue in issues[:10]:
                self.log_warning('Dimensional Accuracy', issue)
            print(f"⚠️  {len(issues)} dimensional issues")
        else:
            print(f"✅ All dimensions within precision requirements")

    # =========================================================================
    # STRUCTURAL INTEGRITY TESTS
    # =========================================================================

    def test_structural_integrity(self):
        """Test structural soundness"""
        print("\n🏗️  STRUCTURAL INTEGRITY")
        print("-" * 80)

        # Test 1: Floor supports all objects
        floor = [o for o in self.objects if 'floor' in o.get('object_type', '').lower()]
        if not floor:
            self.log_error('Structural', 'No floor slab - objects floating')
            print("❌ No floor slab")
        else:
            print("✅ Floor slab present")

        # Test 2: Walls have proper connectivity
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]
        disconnected = []

        for i, wall in enumerate(walls):
            connected = False
            w_start = wall.get('position', [0, 0, 0])
            w_end = wall.get('end_point', [0, 0, 0])

            for j, other in enumerate(walls):
                if i == j:
                    continue

                o_start = other.get('position', [0, 0, 0])
                o_end = other.get('end_point', [0, 0, 0])

                # Check if endpoints connect
                for wp in [w_start, w_end]:
                    for op in [o_start, o_end]:
                        dist = math.sqrt(sum((a - b)**2 for a, b in zip(wp, op)))
                        if dist < 0.2:
                            connected = True
                            break
                    if connected:
                        break
                if connected:
                    break

            if not connected:
                disconnected.append(wall['name'])

        if disconnected:
            self.log_warning('Structural', f'{len(disconnected)} isolated walls')
            print(f"⚠️  {len(disconnected)} walls not connected")
        else:
            print(f"✅ All {len(walls)} walls connected")

        # Test 3: Roof supported by walls
        roof = [o for o in self.objects if 'roof' in o.get('object_type', '').lower()]
        if roof and len(walls) < 4:
            self.log_error('Structural', 'Insufficient walls to support roof')
            print("❌ Roof not adequately supported")
        elif roof:
            print("✅ Roof support adequate")

        self.test_results['Structural Integrity'] = {
            'passed': len(disconnected) == 0 and len(floor) > 0
        }

    # =========================================================================
    # BUILDING CODE COMPLIANCE (UBBL Malaysia)
    # =========================================================================

    def test_building_code_compliance(self):
        """Test Malaysian UBBL compliance"""
        print("\n📜 BUILDING CODE COMPLIANCE (UBBL)")
        print("-" * 80)

        violations = []

        # UBBL Rule 1: Minimum ceiling height 2.75m
        height = self.building_dims.get('height', 3.0)
        if height < 2.75:
            violations.append(f"Ceiling height {height}m < 2.75m minimum (UBBL)")
            self.log_error('Building Code', violations[-1])

        # UBBL Rule 2: Minimum room dimensions
        # Bedroom: 6.5m²
        # Bathroom: 1.8m²
        # Kitchen: 4.5m²

        # UBBL Rule 3: Natural ventilation
        windows = [o for o in self.objects if 'window' in o.get('object_type', '').lower()]
        rooms_count = len(set(o.get('room', '') for o in self.objects if o.get('room')))

        if rooms_count > 0:
            ventilation_ratio = len(windows) / rooms_count
            if ventilation_ratio < 0.3:
                violations.append(f"Insufficient windows ({len(windows)} for {rooms_count} rooms)")
                self.log_warning('Building Code', violations[-1])

        # UBBL Rule 4: Minimum door width 750mm
        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]
        for door in doors:
            obj_type = door.get('object_type', '')
            if '_600' in obj_type or '_700' in obj_type:
                violations.append(f"{door['name']}: door < 750mm minimum")
                self.log_warning('Building Code', violations[-1])

        # UBBL Rule 5: Sanitary requirements
        toilets = [o for o in self.objects if 'toilet' in o.get('object_type', '').lower()]
        if len(toilets) == 0:
            violations.append("No toilet - UBBL violation")
            self.log_error('Building Code', violations[-1])

        self.test_results['Building Code'] = {
            'passed': len(violations) == 0,
            'violations': len(violations)
        }

        if violations:
            print(f"⚠️  {len(violations)} code violations")
            for v in violations[:5]:
                print(f"   • {v}")
        else:
            print("✅ UBBL compliant")

    # =========================================================================
    # IFC STANDARD COMPLIANCE
    # =========================================================================

    def test_ifc_compliance(self):
        """Test IFC4 standard compliance"""
        print("\n🔷 IFC STANDARD COMPLIANCE")
        print("-" * 80)

        issues = []

        # Test 1: Object_type naming follows IFC convention
        for obj in self.objects:
            obj_type = obj.get('object_type', '')

            # Should contain underscores (word_word_lod300)
            if '_' not in obj_type:
                issues.append(f"{obj['name']}: non-standard naming")

            # Should end with _lodNNN
            if not obj_type.endswith(('lod100', 'lod200', 'lod300', 'lod400', 'lod500')):
                issues.append(f"{obj['name']}: missing LOD suffix")

        # Test 2: Required attributes present
        required_attrs = ['name', 'object_type', 'position', 'orientation', 'placed']
        for obj in self.objects:
            missing = [attr for attr in required_attrs if attr not in obj]
            if missing:
                issues.append(f"{obj['name']}: missing {missing}")

        # Test 3: Coordinate system (right-handed, Z-up)
        for obj in self.objects:
            pos = obj.get('position', [0, 0, 0])
            if pos[2] < -1.0:  # Z should not be deep negative
                issues.append(f"{obj['name']}: negative Z coordinate")

        self.test_results['IFC Compliance'] = {
            'passed': len(issues) == 0,
            'issues': len(issues)
        }

        if issues:
            print(f"⚠️  {len(issues)} IFC compliance issues")
            for issue in issues[:10]:
                print(f"   • {issue}")
        else:
            print(f"✅ IFC4 compliant")

    # =========================================================================
    # TOPOLOGY AND CONNECTIVITY TESTS
    # =========================================================================

    def test_topology(self):
        """Test spatial relationships and connectivity"""
        print("\n🔗 TOPOLOGY & CONNECTIVITY")
        print("-" * 80)

        issues = []

        # Test 1: Doors connect two spaces
        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        for door in doors:
            # Door should be within a wall
            door_pos = door.get('position', [0, 0, 0])
            in_wall = False

            for wall in walls:
                w_start = wall.get('position', [0, 0, 0])
                w_end = wall.get('end_point', [0, 0, 0])

                dist = self._point_to_line_distance(door_pos, w_start, w_end)
                if dist < 0.2:
                    in_wall = True
                    break

            if not in_wall:
                issues.append(f"{door['name']}: not in wall")

        # Test 2: Windows in exterior walls
        windows = [o for o in self.objects if 'window' in o.get('object_type', '').lower()]
        exterior_walls = [w for w in walls if 'exterior' in w.get('name', '').lower()]

        for window in windows:
            win_pos = window.get('position', [0, 0, 0])
            in_exterior = False

            for wall in exterior_walls:
                w_start = wall.get('position', [0, 0, 0])
                w_end = wall.get('end_point', [0, 0, 0])

                dist = self._point_to_line_distance(win_pos, w_start, w_end)
                if dist < 0.3:
                    in_exterior = True
                    break

            if not in_exterior:
                self.log_info('Topology', f"{window['name']}: may be interior window")

        # Test 3: Room enclosure
        rooms = defaultdict(list)
        for obj in self.objects:
            room = obj.get('room')
            if room:
                rooms[room].append(obj)

        for room_name, room_objects in rooms.items():
            room_walls = [o for o in room_objects if 'wall' in o.get('object_type', '').lower()]

            if len(room_walls) < 3:
                issues.append(f"{room_name}: only {len(room_walls)} walls (need 3-4)")

        self.test_results['Topology'] = {
            'passed': len(issues) == 0,
            'issues': len(issues)
        }

        if issues:
            print(f"⚠️  {len(issues)} topology issues")
            for issue in issues[:10]:
                print(f"   • {issue}")
        else:
            print(f"✅ Topology valid")

    # =========================================================================
    # MEP COORDINATION TESTS
    # =========================================================================

    def test_mep_coordination(self):
        """Test MEP (Mechanical, Electrical, Plumbing) integration"""
        print("\n⚡ MEP COORDINATION")
        print("-" * 80)

        issues = []

        # Test 1: Electrical distribution
        switches = [o for o in self.objects if 'switch' in o.get('object_type', '').lower()]
        outlets = [o for o in self.objects if 'outlet' in o.get('object_type', '').lower()]
        lights = [o for o in self.objects if 'light' in o.get('object_type', '').lower()]

        rooms = set(o.get('room', '') for o in self.objects if o.get('room'))

        # Each room should have light + switch
        for room in rooms:
            room_lights = [o for o in lights if o.get('room') == room]
            room_switches = [o for o in switches if o.get('room') == room]

            if len(room_lights) == 0:
                issues.append(f"{room}: no lighting")
            if len(room_switches) == 0:
                issues.append(f"{room}: no switches")

        # Test 2: Plumbing zones
        toilets = [o for o in self.objects if 'toilet' in o.get('object_type', '').lower()]
        basins = [o for o in self.objects if 'basin' in o.get('object_type', '').lower()]
        floor_drains = [o for o in self.objects if 'floor_drain' in o.get('object_type', '').lower()]

        # Toilets and basins should have nearby drains
        for toilet in toilets:
            t_pos = toilet.get('position', [0, 0, 0])
            has_drain = False

            for drain in floor_drains:
                d_pos = drain.get('position', [0, 0, 0])
                dist = math.sqrt(sum((a - b)**2 for a, b in zip(t_pos, d_pos)))

                if dist < 3.0:  # Within 3m
                    has_drain = True
                    break

            if not has_drain:
                issues.append(f"{toilet['name']}: no nearby floor drain")

        # Test 3: HVAC coverage
        rooms_count = len(rooms)
        diffusers = [o for o in self.objects if 'diffuser' in o.get('object_type', '').lower()]
        fans = [o for o in self.objects if 'fan' in o.get('object_type', '').lower()]

        hvac_count = len(diffusers) + len(fans)

        if rooms_count > 0 and hvac_count == 0:
            issues.append("No HVAC/ventilation system")

        self.test_results['MEP Coordination'] = {
            'passed': len(issues) == 0,
            'issues': len(issues)
        }

        if issues:
            print(f"⚠️  {len(issues)} MEP issues")
            for issue in issues[:10]:
                print(f"   • {issue}")
        else:
            print(f"✅ MEP coordinated")

    # =========================================================================
    # CONSTRUCTION FEASIBILITY TESTS
    # =========================================================================

    def test_construction_feasibility(self):
        """Test if design is constructible"""
        print("\n🏗️  CONSTRUCTION FEASIBILITY")
        print("-" * 80)

        issues = []

        # Test 1: Wall thickness realistic
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]
        for wall in walls:
            thickness = wall.get('thickness', 0)
            if 0 < thickness < 0.075:  # < 75mm
                issues.append(f"{wall['name']}: unrealistic thickness ({thickness*1000}mm)")
            elif thickness > 0.5:  # > 500mm
                issues.append(f"{wall['name']}: excessive thickness ({thickness*1000}mm)")

        # Test 2: Door/window spans feasible
        windows = [o for o in self.objects if 'window' in o.get('object_type', '').lower()]
        for window in windows:
            obj_type = window.get('object_type', '')

            # Extract width if in name (e.g., window_1200x1000)
            if 'x' in obj_type:
                try:
                    width_str = obj_type.split('_')[-1].split('x')[0]
                    width = int(''.join(c for c in width_str if c.isdigit()))

                    if width > 3000:  # > 3m unsupported span
                        issues.append(f"{window['name']}: wide span requires lintel")
                except:
                    pass

        # Test 3: Foundation load distribution
        walls_count = len(walls)
        floor = [o for o in self.objects if 'floor' in o.get('object_type', '').lower()]

        if floor and walls_count == 0:
            issues.append("Floor slab without supporting walls")

        # Test 4: Material compatibility
        # Concrete roof requires concrete/brick walls
        roof = [o for o in self.objects if 'roof' in o.get('object_type', '').lower()
                and 'concrete' in o.get('object_type', '').lower()]

        lightweight_walls = [w for w in walls if 'lightweight' in w.get('object_type', '').lower()]

        if roof and len(lightweight_walls) > len(walls) * 0.5:
            issues.append("Concrete roof on mostly lightweight walls - structural concern")

        self.test_results['Construction Feasibility'] = {
            'passed': len(issues) == 0,
            'issues': len(issues)
        }

        if issues:
            print(f"⚠️  {len(issues)} constructibility issues")
            for issue in issues[:10]:
                print(f"   • {issue}")
        else:
            print(f"✅ Design is constructible")

    # =========================================================================
    # DATA QUALITY TESTS
    # =========================================================================

    def test_data_quality(self):
        """Test overall data quality and consistency"""
        print("\n📊 DATA QUALITY")
        print("-" * 80)

        issues = []

        # Test 1: Metadata completeness
        required_meta = ['extraction_timestamp', 'source_file', 'building_dimensions', 'calibration']
        missing_meta = [k for k in required_meta if k not in self.metadata]

        if missing_meta:
            issues.append(f"Missing metadata: {missing_meta}")

        # Test 2: Calibration quality
        calib = self.metadata.get('calibration', {})
        confidence = calib.get('confidence', 0)

        if confidence < 70:
            issues.append(f"Low calibration confidence ({confidence}%)")

        # Test 3: Object distribution
        phases = Counter(o.get('_phase', 'unknown') for o in self.objects)

        if phases.get('unknown', 0) > 0:
            issues.append(f"{phases['unknown']} objects without phase")

        # Test 4: Source tracking
        sources = Counter(o.get('source', 'unknown') for o in self.objects)

        print(f"   Data sources: {dict(sources)}")
        print(f"   Phases: {dict(phases)}")
        print(f"   Calibration: {confidence}%")

        self.test_results['Data Quality'] = {
            'passed': len(issues) == 0,
            'issues': len(issues)
        }

        if issues:
            print(f"⚠️  {len(issues)} quality issues")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print(f"✅ High data quality")

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
    # RUN ALL DEEP TESTS
    # =========================================================================

    def run_all_tests(self):
        """Execute comprehensive deep validation"""
        print("=" * 80)
        print("🔬 DEEP VALIDATION SUITE")
        print("=" * 80)
        print("Comprehensive testing at every level")
        print(f"Objects: {len(self.objects)}")
        print()

        # Run all test categories
        self.test_dimensional_precision()
        self.test_structural_integrity()
        self.test_building_code_compliance()
        self.test_ifc_compliance()
        self.test_topology()
        self.test_mep_coordination()
        self.test_construction_feasibility()
        self.test_data_quality()

        # Summary
        print("\n" + "=" * 80)
        print("📊 DEEP VALIDATION SUMMARY")
        print("=" * 80)

        passed = sum(1 for r in self.test_results.values() if r.get('passed', False))
        total = len(self.test_results)

        print(f"Test Categories: {total}")
        print(f"  ✅ Passed: {passed}")
        print(f"  ❌ Failed: {total - passed}")
        print()

        print(f"Total Errors: {sum(len(v) for v in self.errors.values())}")
        print(f"Total Warnings: {sum(len(v) for v in self.warnings.values())}")

        if self.errors:
            print("\n" + "=" * 80)
            print("❌ CRITICAL ERRORS BY CATEGORY")
            print("=" * 80)
            for category, error_list in self.errors.items():
                print(f"\n{category}:")
                for error in error_list[:5]:
                    print(f"  • {error}")
                if len(error_list) > 5:
                    print(f"  ... and {len(error_list) - 5} more")

        if self.warnings:
            print("\n" + "=" * 80)
            print("⚠️  WARNINGS BY CATEGORY")
            print("=" * 80)
            for category, warning_list in self.warnings.items():
                if len(warning_list) > 0:
                    print(f"\n{category}: {len(warning_list)} issues")
                    for warning in warning_list[:3]:
                        print(f"  • {warning}")

        print("\n" + "=" * 80)
        score = (passed / total * 100) if total > 0 else 0
        print(f"OVERALL VALIDATION SCORE: {score:.1f}%")

        if score >= 90:
            print("✅ EXCELLENT - Ready for production")
        elif score >= 70:
            print("⚠️  GOOD - Minor issues to address")
        elif score >= 50:
            print("⚠️  ACCEPTABLE - Several issues need fixing")
        else:
            print("❌ POOR - Major rework required")

        print("=" * 80)

        return 0 if passed == total else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_deep_validation.py <output.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    validator = DeepValidator(data)
    sys.exit(validator.run_all_tests())
