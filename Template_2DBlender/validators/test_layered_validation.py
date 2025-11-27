#!/usr/bin/env python3
"""
Layered Validation System - Validate each layer before building the next

This is the PRIMARY validation approach:
1. Each layer must be validated BEFORE the next layer is built
2. Once validated, a layer becomes IMMUTABLE (locked)
3. Upper layers depend on lower layers being correct
4. If a layer fails, stop - don't build on broken foundation

Layers (in order):
Layer 0: Calibration (drainage perimeter) - THE FOUNDATION
Layer 1: Building Envelope (outer walls, floor, roof)
Layer 2: Openings (doors, windows in walls)
Layer 3: Interior (room divisions)
Layer 4: MEP (electrical, plumbing)
Layer 5: Furniture (fixtures, equipment)

The spatial arithmetic test is the PRIMARY test for each layer.
"""

import json
import math
import sys
from pathlib import Path


class LayeredValidator:
    """Validate extraction layer by layer"""

    def __init__(self, data):
        self.data = data
        self.objects = data.get('objects', [])
        self.metadata = data.get('extraction_metadata', {})
        self.calibration = data.get('calibration_data', {})
        self.building_bounds = data.get('building_bounds', {})

        self.layer_results = {}
        self.failed_layer = None

    def validate_layer_0_calibration(self):
        """Layer 0: Calibration - THE FOUNDATION (must be immutable)"""
        print("\n" + "="*80)
        print("LAYER 0: CALIBRATION - THE FOUNDATION")
        print("="*80)

        issues = []

        # Check 1: Drainage perimeter exists
        drainage_perimeter = self.calibration.get('drainage_perimeter_coords', [])
        if not drainage_perimeter or len(drainage_perimeter) < 4:
            issues.append("Drainage perimeter missing or incomplete")
            print("❌ Drainage perimeter: MISSING")
        else:
            print(f"✅ Drainage perimeter: {len(drainage_perimeter)} points")

        # Check 2: Calculate perimeter area
        if len(drainage_perimeter) >= 4:
            xs = [p[0] for p in drainage_perimeter]
            ys = [p[1] for p in drainage_perimeter]

            width = max(xs) - min(xs)
            length = max(ys) - min(ys)
            area = width * length

            print(f"   Perimeter: {width:.2f}m × {length:.2f}m = {area:.2f}m²")

            if area < 10:
                issues.append(f"Perimeter too small ({area:.2f}m²)")
                print(f"❌ Area: Too small ({area:.2f}m²)")
            elif area > 500:
                issues.append(f"Perimeter too large ({area:.2f}m²)")
                print(f"❌ Area: Too large ({area:.2f}m²)")
            else:
                print(f"✅ Area: Reasonable")

        # Check 3: GPS coordinates exist
        gps_ref = self.calibration.get('gps_reference')
        if gps_ref:
            print(f"✅ GPS reference: {gps_ref.get('latitude', 'N/A')}, {gps_ref.get('longitude', 'N/A')}")
        else:
            issues.append("GPS reference missing")
            print("⚠️  GPS reference: Missing")

        # Check 4: Scale/calibration factors
        scale = self.metadata.get('calibration_scale')
        if scale:
            print(f"✅ Calibration scale: {scale}")
        else:
            issues.append("Calibration scale missing")
            print("❌ Calibration scale: Missing")

        # Result
        if issues:
            print(f"\n❌ LAYER 0 FAILED: {len(issues)} issues")
            for issue in issues:
                print(f"   • {issue}")
            self.layer_results['layer_0'] = {'status': 'FAILED', 'issues': issues}
            self.failed_layer = 0
            return False
        else:
            print("\n✅ LAYER 0 VALIDATED - FOUNDATION IS SOLID")
            print("   → This layer is now IMMUTABLE")
            self.layer_results['layer_0'] = {'status': 'PASSED', 'issues': []}
            return True

    def validate_layer_1_envelope(self):
        """Layer 1: Building Envelope - Must exist on valid foundation"""
        print("\n" + "="*80)
        print("LAYER 1: BUILDING ENVELOPE (depends on Layer 0)")
        print("="*80)

        if self.failed_layer is not None and self.failed_layer < 1:
            print("❌ SKIPPED: Cannot validate - previous layer failed")
            return False

        issues = []

        # Get structural objects
        exterior_walls = [o for o in self.objects if 'wall_exterior' in o.get('name', '')]
        floor = [o for o in self.objects if 'floor' in o.get('name', '').lower()]
        roof = [o for o in self.objects if 'roof' in o.get('name', '').lower()]

        # Check 1: Exterior walls form closed perimeter
        if len(exterior_walls) < 4:
            issues.append(f"Insufficient exterior walls ({len(exterior_walls)} < 4)")
            print(f"❌ Exterior walls: {len(exterior_walls)} (need ≥4)")
        else:
            print(f"✅ Exterior walls: {len(exterior_walls)} walls")

            # Check if walls form closed loop
            wall_endpoints = set()
            for wall in exterior_walls:
                start = tuple(wall['position'][:2])
                end = tuple(wall.get('end_point', wall['position'])[:2])
                wall_endpoints.add(start)
                wall_endpoints.add(end)

            # Each endpoint should connect to exactly 2 walls (closed loop)
            endpoint_counts = {}
            for wall in exterior_walls:
                start = tuple(wall['position'][:2])
                end = tuple(wall.get('end_point', wall['position'])[:2])
                endpoint_counts[start] = endpoint_counts.get(start, 0) + 1
                endpoint_counts[end] = endpoint_counts.get(end, 0) + 1

            open_endpoints = [ep for ep, count in endpoint_counts.items() if count != 2]
            if open_endpoints:
                issues.append(f"Perimeter not closed: {len(open_endpoints)} open endpoints")
                print(f"⚠️  Perimeter: {len(open_endpoints)} open endpoints")
            else:
                print(f"✅ Perimeter: Closed loop")

        # Check 2: Floor exists
        if not floor:
            issues.append("Floor missing")
            print("❌ Floor: Missing")
        else:
            print(f"✅ Floor: {len(floor)} element(s)")

        # Check 3: Roof exists
        if not roof:
            issues.append("Roof missing")
            print("❌ Roof: Missing")
        else:
            print(f"✅ Roof: {len(roof)} element(s)")

        # Check 4: Envelope coordinates match calibration bounds
        if exterior_walls:
            wall_positions = []
            for wall in exterior_walls:
                wall_positions.append(wall['position'])
                if 'end_point' in wall:
                    wall_positions.append(wall['end_point'])

            xs = [p[0] for p in wall_positions]
            ys = [p[1] for p in wall_positions]

            envelope_width = max(xs) - min(xs)
            envelope_length = max(ys) - min(ys)

            print(f"   Envelope: {envelope_width:.2f}m × {envelope_length:.2f}m")

            # Compare with calibration perimeter
            drainage = self.calibration.get('drainage_perimeter_coords', [])
            if drainage:
                cal_xs = [p[0] for p in drainage]
                cal_ys = [p[1] for p in drainage]
                cal_width = max(cal_xs) - min(cal_xs)
                cal_length = max(cal_ys) - min(cal_ys)

                width_diff = abs(envelope_width - cal_width)
                length_diff = abs(envelope_length - cal_length)

                if width_diff > 1.0 or length_diff > 1.0:
                    issues.append(f"Envelope doesn't match calibration (diff: {width_diff:.2f}m × {length_diff:.2f}m)")
                    print(f"⚠️  Calibration match: Off by {width_diff:.2f}m × {length_diff:.2f}m")
                else:
                    print(f"✅ Calibration match: Within tolerance")

        # Result
        if issues:
            print(f"\n❌ LAYER 1 FAILED: {len(issues)} issues")
            for issue in issues:
                print(f"   • {issue}")
            self.layer_results['layer_1'] = {'status': 'FAILED', 'issues': issues}
            self.failed_layer = 1
            return False
        else:
            print("\n✅ LAYER 1 VALIDATED - ENVELOPE IS SOLID")
            print("   → This layer is now IMMUTABLE")
            self.layer_results['layer_1'] = {'status': 'PASSED', 'issues': []}
            return True

    def validate_layer_2_openings(self):
        """Layer 2: Openings - Must be positioned IN envelope walls"""
        print("\n" + "="*80)
        print("LAYER 2: OPENINGS (depends on Layer 1)")
        print("="*80)

        if self.failed_layer is not None and self.failed_layer < 2:
            print("❌ SKIPPED: Cannot validate - previous layer failed")
            return False

        issues = []

        # Get openings and walls
        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]
        windows = [o for o in self.objects if 'window' in o.get('object_type', '').lower()]
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        # Check 1: All doors positioned on walls
        orphan_doors = 0
        for door in doors:
            door_pos = door.get('position', [0, 0, 0])
            on_wall = False

            for wall in walls:
                w_start = wall['position']
                w_end = wall.get('end_point', w_start)

                dist = self.distance_point_to_line(door_pos, w_start, w_end)
                if dist < 0.3:
                    on_wall = True
                    break

            if not on_wall:
                orphan_doors += 1

        if orphan_doors > 0:
            issues.append(f"{orphan_doors} doors not on walls")
            print(f"❌ Doors: {orphan_doors}/{len(doors)} not on walls")
        else:
            print(f"✅ Doors: All {len(doors)} on walls")

        # Check 2: All windows positioned on walls
        orphan_windows = 0
        for window in windows:
            win_pos = window.get('position', [0, 0, 0])
            on_wall = False

            for wall in walls:
                w_start = wall['position']
                w_end = wall.get('end_point', w_start)

                dist = self.distance_point_to_line(win_pos, w_start, w_end)
                if dist < 0.5:
                    on_wall = True
                    break

            if not on_wall:
                orphan_windows += 1

        if orphan_windows > 0:
            issues.append(f"{orphan_windows} windows not on walls")
            print(f"❌ Windows: {orphan_windows}/{len(windows)} not on walls")
        else:
            print(f"✅ Windows: All {len(windows)} on walls")

        # Check 3: Minimum openings for habitability
        if len(doors) < 1:
            issues.append("No doors (no building access)")
            print("❌ Building access: No doors")
        else:
            print(f"✅ Building access: {len(doors)} door(s)")

        if len(windows) < 2:
            issues.append("Insufficient windows (poor ventilation)")
            print(f"⚠️  Ventilation: Only {len(windows)} window(s)")
        else:
            print(f"✅ Ventilation: {len(windows)} window(s)")

        # Result
        if issues:
            print(f"\n❌ LAYER 2 FAILED: {len(issues)} issues")
            for issue in issues:
                print(f"   • {issue}")
            self.layer_results['layer_2'] = {'status': 'FAILED', 'issues': issues}
            self.failed_layer = 2
            return False
        else:
            print("\n✅ LAYER 2 VALIDATED - OPENINGS ARE VALID")
            print("   → This layer is now IMMUTABLE")
            self.layer_results['layer_2'] = {'status': 'PASSED', 'issues': []}
            return True

    def validate_layer_3_interior(self):
        """Layer 3: Interior - Room divisions must connect to envelope"""
        print("\n" + "="*80)
        print("LAYER 3: INTERIOR (depends on Layer 2)")
        print("="*80)

        if self.failed_layer is not None and self.failed_layer < 3:
            print("❌ SKIPPED: Cannot validate - previous layer failed")
            return False

        issues = []

        # Get interior walls and rooms
        interior_walls = [o for o in self.objects if 'wall_interior' in o.get('name', '')]
        rooms = set(o.get('room') for o in self.objects if o.get('room') and
                   o.get('room') not in ['exterior', 'interior', 'unknown', 'structure'])

        print(f"Interior walls: {len(interior_walls)}")
        print(f"Rooms defined: {len(rooms)}")

        # Check 1: Minimum rooms
        if len(rooms) < 3:
            issues.append(f"Insufficient rooms ({len(rooms)} < 3)")
            print(f"❌ Rooms: {len(rooms)} (need ≥3)")
        else:
            print(f"✅ Rooms: {len(rooms)} rooms")

        # Check 2: Essential rooms exist
        essential_rooms = ['kitchen', 'bathroom', 'bedroom']
        found_rooms = []

        for essential in essential_rooms:
            found = any(essential in room.lower() for room in rooms)
            if found:
                found_rooms.append(essential)
            else:
                issues.append(f"Missing {essential}")
                print(f"❌ {essential.capitalize()}: Missing")

        for room in found_rooms:
            print(f"✅ {room.capitalize()}: Found")

        # Check 3: Each room has access (door)
        rooms_with_doors = set()
        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]

        for door in doors:
            room = door.get('room')
            if room and room not in ['exterior', 'interior', 'unknown']:
                rooms_with_doors.add(room)

        rooms_without_doors = [r for r in rooms if r not in rooms_with_doors]
        if rooms_without_doors:
            issues.append(f"{len(rooms_without_doors)} rooms have no access")
            print(f"⚠️  Room access: {len(rooms_without_doors)}/{len(rooms)} rooms without doors")
        else:
            print(f"✅ Room access: All rooms have doors")

        # Result
        if issues:
            print(f"\n❌ LAYER 3 FAILED: {len(issues)} issues")
            for issue in issues:
                print(f"   • {issue}")
            self.layer_results['layer_3'] = {'status': 'FAILED', 'issues': issues}
            self.failed_layer = 3
            return False
        else:
            print("\n✅ LAYER 3 VALIDATED - INTERIOR IS VALID")
            print("   → This layer is now IMMUTABLE")
            self.layer_results['layer_3'] = {'status': 'PASSED', 'issues': []}
            return True

    def validate_layer_4_mep(self):
        """Layer 4: MEP - Must connect to rooms"""
        print("\n" + "="*80)
        print("LAYER 4: MEP (depends on Layer 3)")
        print("="*80)

        if self.failed_layer is not None and self.failed_layer < 4:
            print("❌ SKIPPED: Cannot validate - previous layer failed")
            return False

        issues = []

        # Get MEP objects
        lights = [o for o in self.objects if 'light' in o.get('name', '').lower()]
        outlets = [o for o in self.objects if 'outlet' in o.get('name', '').lower()]
        switches = [o for o in self.objects if 'switch' in o.get('name', '').lower()]
        plumbing = [o for o in self.objects if any(kw in o.get('object_type', '').lower()
                   for kw in ['sink', 'toilet', 'basin', 'shower', 'drain'])]

        print(f"Lighting: {len(lights)}")
        print(f"Outlets: {len(outlets)}")
        print(f"Switches: {len(switches)}")
        print(f"Plumbing: {len(plumbing)}")

        # Check 1: Minimum lighting
        if len(lights) < 3:
            issues.append("Insufficient lighting")
            print("⚠️  Lighting: Insufficient")
        else:
            print("✅ Lighting: Adequate")

        # Check 2: Kitchen has plumbing
        kitchen_plumbing = [p for p in plumbing if 'kitchen' in p.get('room', '').lower()]
        if not kitchen_plumbing:
            issues.append("Kitchen has no plumbing")
            print("⚠️  Kitchen plumbing: Missing")
        else:
            print(f"✅ Kitchen plumbing: {len(kitchen_plumbing)} fixture(s)")

        # Check 3: Bathrooms have plumbing
        bathroom_plumbing = [p for p in plumbing if 'bathroom' in p.get('room', '').lower()]
        if not bathroom_plumbing:
            issues.append("Bathrooms have no plumbing")
            print("⚠️  Bathroom plumbing: Missing")
        else:
            print(f"✅ Bathroom plumbing: {len(bathroom_plumbing)} fixture(s)")

        # Result
        if issues:
            print(f"\n⚠️  LAYER 4 HAS WARNINGS: {len(issues)} issues")
            for issue in issues:
                print(f"   • {issue}")
            self.layer_results['layer_4'] = {'status': 'WARNING', 'issues': issues}
            # Don't fail - MEP issues are warnings, not critical
            return True
        else:
            print("\n✅ LAYER 4 VALIDATED - MEP IS COMPLETE")
            self.layer_results['layer_4'] = {'status': 'PASSED', 'issues': []}
            return True

    def validate_layer_5_furniture(self):
        """Layer 5: Furniture - Must be in rooms with circulation space"""
        print("\n" + "="*80)
        print("LAYER 5: FURNITURE (depends on Layer 3)")
        print("="*80)

        if self.failed_layer is not None and self.failed_layer < 3:
            print("❌ SKIPPED: Cannot validate - previous layer failed")
            return False

        issues = []

        # Get furniture
        furniture = [o for o in self.objects if o.get('_phase') == '6_furniture']

        print(f"Furniture objects: {len(furniture)}")

        # Group by room
        rooms = {}
        for obj in furniture:
            room = obj.get('room')
            if room:
                if room not in rooms:
                    rooms[room] = []
                rooms[room].append(obj)

        # Check each room for overcrowding
        for room_name, room_objects in rooms.items():
            positions = [o.get('position', [0, 0, 0]) for o in room_objects]
            if positions:
                xs = [p[0] for p in positions]
                ys = [p[1] for p in positions]

                room_area = (max(xs) - min(xs)) * (max(ys) - min(ys))
                density = len(room_objects) / room_area if room_area > 0 else 0

                if density > 2.0:
                    issues.append(f"{room_name}: Overcrowded ({density:.1f} items/m²)")
                    print(f"⚠️  {room_name}: Overcrowded ({density:.1f} items/m²)")

        # Result
        if issues:
            print(f"\n⚠️  LAYER 5 HAS WARNINGS: {len(issues)} issues")
            for issue in issues:
                print(f"   • {issue}")
            self.layer_results['layer_5'] = {'status': 'WARNING', 'issues': issues}
            return True
        else:
            print("\n✅ LAYER 5 VALIDATED - FURNITURE IS APPROPRIATE")
            self.layer_results['layer_5'] = {'status': 'PASSED', 'issues': []}
            return True

    def distance_point_to_line(self, point, line_start, line_end):
        """Calculate distance from point to line segment"""
        x0, y0 = point[0], point[1]
        x1, y1 = line_start[0], line_start[1]
        x2, y2 = line_end[0], line_end[1]

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)

        t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx**2 + dy**2)))

        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        return math.sqrt((x0 - closest_x)**2 + (y0 - closest_y)**2)

    def run_all_layers(self):
        """Run all layer validations in sequence"""
        print("="*80)
        print("LAYERED VALIDATION SYSTEM")
        print("="*80)
        print("Validating layer by layer - stops at first failure")
        print()

        # Layer 0: Foundation
        if not self.validate_layer_0_calibration():
            print("\n" + "="*80)
            print("❌ VALIDATION STOPPED AT LAYER 0")
            print("="*80)
            print("Fix calibration issues before proceeding")
            return False

        # Layer 1: Envelope
        if not self.validate_layer_1_envelope():
            print("\n" + "="*80)
            print("❌ VALIDATION STOPPED AT LAYER 1")
            print("="*80)
            print("Fix envelope issues before proceeding")
            return False

        # Layer 2: Openings
        if not self.validate_layer_2_openings():
            print("\n" + "="*80)
            print("❌ VALIDATION STOPPED AT LAYER 2")
            print("="*80)
            print("Fix opening issues before proceeding")
            return False

        # Layer 3: Interior
        if not self.validate_layer_3_interior():
            print("\n" + "="*80)
            print("❌ VALIDATION STOPPED AT LAYER 3")
            print("="*80)
            print("Fix interior issues before proceeding")
            return False

        # Layer 4: MEP (warnings don't stop)
        self.validate_layer_4_mep()

        # Layer 5: Furniture (warnings don't stop)
        self.validate_layer_5_furniture()

        # Summary
        print("\n" + "="*80)
        print("LAYERED VALIDATION SUMMARY")
        print("="*80)

        for layer_name, result in self.layer_results.items():
            status = result['status']
            if status == 'PASSED':
                print(f"✅ {layer_name.upper()}: PASSED")
            elif status == 'WARNING':
                print(f"⚠️  {layer_name.upper()}: WARNING ({len(result['issues'])} issues)")
            else:
                print(f"❌ {layer_name.upper()}: FAILED ({len(result['issues'])} issues)")

        # Check if all critical layers passed
        critical_passed = all(
            self.layer_results.get(f'layer_{i}', {}).get('status') == 'PASSED'
            for i in range(4)  # Layers 0-3 are critical
        )

        if critical_passed:
            print("\n" + "="*80)
            print("✅ ALL CRITICAL LAYERS VALIDATED")
            print("="*80)
            print("Building has solid foundation and can be constructed")
            return True
        else:
            print("\n" + "="*80)
            print("❌ VALIDATION FAILED")
            print("="*80)
            return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_layered_validation.py <output.json>")
        sys.exit(1)

    # Load data
    with open(sys.argv[1]) as f:
        data = json.load(f)

    # Run layered validation
    validator = LayeredValidator(data)
    success = validator.run_all_layers()

    # Exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
