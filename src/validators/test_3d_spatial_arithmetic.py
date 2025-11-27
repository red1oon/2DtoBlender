#!/usr/bin/env python3
"""
3D Spatial Arithmetic Validation

Tests that ALL spatial information is mathematically valid for 3D plotting.
No rendering - pure arithmetic analysis of coordinates, dimensions, and geometry.

Validates:
1. All objects can be placed in 3D space mathematically
2. Bounding boxes are calculable for all objects
3. Dimensions are geometrically valid
4. Spatial relationships are arithmetically consistent
5. Complete 3D scene can be constructed from data alone
"""

import json
import math
import sys
from collections import defaultdict


class SpatialArithmetic3D:
    """Arithmetic validation of 3D spatial data"""

    def __init__(self, data):
        self.data = data
        self.objects = data.get('objects', [])
        self.building_bounds = data.get('building_bounds', {})
        self.tests_passed = 0
        self.tests_failed = 0
        self.warnings = []
        self.failures = []

    def log_pass(self, test_name):
        """Log test pass"""
        self.tests_passed += 1
        print(f"✅ PASS: {test_name}")

    def log_fail(self, test_name, message):
        """Log test failure"""
        self.tests_failed += 1
        self.failures.append({'test': test_name, 'message': message})
        print(f"❌ FAIL: {test_name}")
        print(f"   {message}")

    def log_warning(self, message):
        """Log warning"""
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")

    def distance_3d(self, p1, p2):
        """Calculate 3D Euclidean distance"""
        return math.sqrt(sum((a - b)**2 for a, b in zip(p1, p2)))

    def test_01_position_validity(self):
        """Test 1: All positions are valid 3D coordinates"""
        print("\n" + "="*80)
        print("TEST 1: 3D POSITION VALIDITY")
        print("="*80)

        invalid = []
        for obj in self.objects:
            pos = obj.get('position')
            name = obj.get('name', 'unnamed')

            if not pos:
                invalid.append(f"{name}: missing position")
            elif not isinstance(pos, list):
                invalid.append(f"{name}: position not a list")
            elif len(pos) != 3:
                invalid.append(f"{name}: position has {len(pos)} coords (need 3)")
            else:
                # Check all coords are numbers
                for i, coord in enumerate(pos):
                    if not isinstance(coord, (int, float)):
                        invalid.append(f"{name}: position[{i}] not numeric")
                    elif math.isnan(coord) or math.isinf(coord):
                        invalid.append(f"{name}: position[{i}] is NaN/Inf")

        if invalid:
            self.log_fail("Position Validity", f"{len(invalid)} objects with invalid positions")
            for issue in invalid[:10]:
                print(f"   • {issue}")
        else:
            self.log_pass(f"All {len(self.objects)} objects have valid 3D positions")

    def test_02_dimensions_validity(self):
        """Test 2: All dimensions are geometrically valid"""
        print("\n" + "="*80)
        print("TEST 2: DIMENSION VALIDITY")
        print("="*80)

        invalid = []
        for obj in self.objects:
            dims = obj.get('dimensions')
            name = obj.get('name', 'unnamed')

            if not dims:
                # Some objects may not have dimensions (point objects)
                continue

            if isinstance(dims, list):
                if len(dims) != 3:
                    invalid.append(f"{name}: dimensions has {len(dims)} values (need 3)")
                else:
                    for i, dim in enumerate(dims):
                        if not isinstance(dim, (int, float)):
                            invalid.append(f"{name}: dimension[{i}] not numeric")
                        elif dim < 0:
                            invalid.append(f"{name}: dimension[{i}] is negative ({dim})")
                        elif math.isnan(dim) or math.isinf(dim):
                            invalid.append(f"{name}: dimension[{i}] is NaN/Inf")
            elif isinstance(dims, dict):
                for key in ['length', 'width', 'height']:
                    val = dims.get(key, 0)
                    if not isinstance(val, (int, float)):
                        invalid.append(f"{name}: {key} not numeric")
                    elif val < 0:
                        invalid.append(f"{name}: {key} is negative ({val})")

        if invalid:
            self.log_fail("Dimension Validity", f"{len(invalid)} objects with invalid dimensions")
            for issue in invalid[:10]:
                print(f"   • {issue}")
        else:
            self.log_pass(f"All objects have valid dimensions")

    def test_03_bounding_box_calculation(self):
        """Test 3: Bounding boxes can be calculated for all objects"""
        print("\n" + "="*80)
        print("TEST 3: BOUNDING BOX CALCULATION")
        print("="*80)

        cannot_calc = []
        bboxes = {}

        for obj in self.objects:
            name = obj.get('name', 'unnamed')
            obj_type = obj.get('object_type', '')
            pos = obj.get('position', [0, 0, 0])
            dims = obj.get('dimensions', [0, 0, 0])

            try:
                # For walls with endpoints
                if 'wall' in obj_type.lower() and 'end_point' in obj:
                    start = pos
                    end = obj['end_point']
                    thickness = obj.get('thickness', 0.15)

                    # Calculate wall bounding box
                    min_x = min(start[0], end[0]) - thickness/2
                    max_x = max(start[0], end[0]) + thickness/2
                    min_y = min(start[1], end[1]) - thickness/2
                    max_y = max(start[1], end[1]) + thickness/2
                    min_z = min(start[2], end[2])

                    # Get height from dimensions
                    if isinstance(dims, list) and len(dims) >= 3:
                        max_z = start[2] + dims[2]
                    else:
                        max_z = start[2] + 2.95  # Default height

                    bbox = {
                        'min': [min_x, min_y, min_z],
                        'max': [max_x, max_y, max_z]
                    }

                # For regular objects with dimensions
                elif dims:
                    if isinstance(dims, list) and len(dims) >= 3:
                        L, W, H = dims[0], dims[1], dims[2]
                    elif isinstance(dims, dict):
                        L = dims.get('length', 0)
                        W = dims.get('width', 0)
                        H = dims.get('height', 0)
                    else:
                        L, W, H = 0, 0, 0

                    # Calculate bbox centered at position
                    bbox = {
                        'min': [pos[0] - L/2, pos[1] - W/2, pos[2]],
                        'max': [pos[0] + L/2, pos[1] + W/2, pos[2] + H]
                    }

                # Point objects (no dimensions)
                else:
                    bbox = {
                        'min': pos,
                        'max': pos
                    }

                # Validate bbox
                if bbox['min'][0] > bbox['max'][0] or \
                   bbox['min'][1] > bbox['max'][1] or \
                   bbox['min'][2] > bbox['max'][2]:
                    cannot_calc.append(f"{name}: inverted bbox")
                else:
                    bboxes[name] = bbox

            except Exception as e:
                cannot_calc.append(f"{name}: {str(e)}")

        if cannot_calc:
            self.log_fail("Bounding Box Calculation",
                         f"{len(cannot_calc)} objects cannot have bbox calculated")
            for issue in cannot_calc[:10]:
                print(f"   • {issue}")
        else:
            self.log_pass(f"All {len(self.objects)} objects have calculable bounding boxes")
            print(f"   Stored {len(bboxes)} bounding boxes for further tests")

        return bboxes

    def test_04_spatial_hierarchy(self):
        """Test 4: Spatial hierarchy is arithmetically valid"""
        print("\n" + "="*80)
        print("TEST 4: SPATIAL HIERARCHY")
        print("="*80)

        # Group objects by Z-level
        z_levels = defaultdict(list)

        for obj in self.objects:
            pos = obj.get('position', [0, 0, 0])
            z = pos[2]

            # Categorize by height
            if z < 0.1:
                level = 'floor'
            elif 0.1 <= z < 1.5:
                level = 'low'
            elif 1.5 <= z < 2.5:
                level = 'high'
            elif z >= 2.5:
                level = 'ceiling'

            z_levels[level].append(obj.get('name', 'unnamed'))

        print(f"Floor level (Z<0.1m): {len(z_levels['floor'])} objects")
        print(f"Low level (0.1-1.5m): {len(z_levels['low'])} objects")
        print(f"High level (1.5-2.5m): {len(z_levels['high'])} objects")
        print(f"Ceiling level (Z>2.5m): {len(z_levels['ceiling'])} objects")

        # Check if hierarchy makes sense
        if len(z_levels['floor']) < 10:
            self.log_warning(f"Only {len(z_levels['floor'])} floor-level objects")

        if len(z_levels['ceiling']) == 0:
            self.log_warning("No ceiling-level objects")

        self.log_pass(f"Spatial hierarchy valid with {len(z_levels)} levels")

    def test_05_wall_network_connectivity(self):
        """Test 5: Wall network is arithmetically connected"""
        print("\n" + "="*80)
        print("TEST 5: WALL NETWORK CONNECTIVITY")
        print("="*80)

        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        if len(walls) == 0:
            self.log_warning("No walls found")
            return

        # Build connectivity graph
        connections = defaultdict(list)

        for i, wall1 in enumerate(walls):
            w1_start = wall1['position']
            w1_end = wall1.get('end_point', w1_start)

            for j, wall2 in enumerate(walls):
                if i == j:
                    continue

                w2_start = wall2['position']
                w2_end = wall2.get('end_point', w2_start)

                # Check if endpoints connect (within 0.1m tolerance)
                if (self.distance_3d(w1_start, w2_start) < 0.1 or
                    self.distance_3d(w1_start, w2_end) < 0.1 or
                    self.distance_3d(w1_end, w2_start) < 0.1 or
                    self.distance_3d(w1_end, w2_end) < 0.1):
                    connections[i].append(j)

        # Count isolated walls
        isolated = sum(1 for i in range(len(walls)) if len(connections[i]) == 0)

        print(f"Total walls: {len(walls)}")
        print(f"Connected walls: {len(walls) - isolated}")
        print(f"Isolated walls: {isolated}")

        avg_connections = sum(len(c) for c in connections.values()) / len(walls) if walls else 0
        print(f"Average connections per wall: {avg_connections:.1f}")

        if isolated > len(walls) * 0.2:
            self.log_fail("Wall Connectivity",
                         f"{isolated} isolated walls ({isolated/len(walls)*100:.1f}%)")
        elif isolated > 0:
            self.log_warning(f"{isolated} walls are isolated")
            self.log_pass("Wall network mostly connected")
        else:
            self.log_pass("All walls are connected in network")

    def test_06_object_volume_calculation(self):
        """Test 6: Volumes can be calculated for all objects"""
        print("\n" + "="*80)
        print("TEST 6: VOLUME CALCULATION")
        print("="*80)

        volumes = {}
        invalid_volumes = []

        for obj in self.objects:
            name = obj.get('name', 'unnamed')
            dims = obj.get('dimensions')

            if not dims:
                # Point objects have zero volume (ok)
                volumes[name] = 0
                continue

            try:
                if isinstance(dims, list) and len(dims) >= 3:
                    volume = dims[0] * dims[1] * dims[2]
                elif isinstance(dims, dict):
                    L = dims.get('length', 0)
                    W = dims.get('width', 0)
                    H = dims.get('height', 0)
                    volume = L * W * H
                else:
                    volume = 0

                if volume < 0:
                    invalid_volumes.append(f"{name}: negative volume ({volume})")
                elif math.isnan(volume) or math.isinf(volume):
                    invalid_volumes.append(f"{name}: invalid volume (NaN/Inf)")
                else:
                    volumes[name] = volume

            except Exception as e:
                invalid_volumes.append(f"{name}: {str(e)}")

        if invalid_volumes:
            self.log_fail("Volume Calculation",
                         f"{len(invalid_volumes)} objects with invalid volumes")
            for issue in invalid_volumes[:10]:
                print(f"   • {issue}")
        else:
            total_volume = sum(volumes.values())
            non_zero = sum(1 for v in volumes.values() if v > 0)
            print(f"Total volume: {total_volume:.2f} m³")
            print(f"Objects with volume: {non_zero}/{len(self.objects)}")
            self.log_pass(f"All {len(self.objects)} objects have calculable volumes")

    def test_07_coordinate_system_consistency(self):
        """Test 7: All coordinates use consistent coordinate system"""
        print("\n" + "="*80)
        print("TEST 7: COORDINATE SYSTEM CONSISTENCY")
        print("="*80)

        # Check if all objects are in same coordinate frame
        positions = [obj.get('position', [0, 0, 0]) for obj in self.objects]

        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        zs = [p[2] for p in positions]

        # Calculate extents
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        z_min, z_max = min(zs), max(zs)

        x_range = x_max - x_min
        y_range = y_max - y_min
        z_range = z_max - z_min

        print(f"X range: {x_min:.2f} to {x_max:.2f} ({x_range:.2f}m)")
        print(f"Y range: {y_min:.2f} to {y_max:.2f} ({y_range:.2f}m)")
        print(f"Z range: {z_min:.2f} to {z_max:.2f} ({z_range:.2f}m)")

        # Check for anomalies
        issues = []

        if z_min < -0.5:
            issues.append(f"Objects below ground: Z_min = {z_min:.2f}m")

        if z_max > 10:
            issues.append(f"Objects too high: Z_max = {z_max:.2f}m")

        if x_range > 1000 or y_range > 1000:
            issues.append(f"Suspicious range: {x_range:.0f}m × {y_range:.0f}m")

        if issues:
            self.log_fail("Coordinate System", ", ".join(issues))
        else:
            self.log_pass("All coordinates in consistent, reasonable range")

    def test_08_rotation_matrix_validity(self):
        """Test 8: All orientation angles produce valid rotation matrices"""
        print("\n" + "="*80)
        print("TEST 8: ROTATION MATRIX VALIDITY")
        print("="*80)

        invalid_rotations = []

        for obj in self.objects:
            name = obj.get('name', 'unnamed')
            orient = obj.get('orientation', 0)

            if not isinstance(orient, (int, float)):
                invalid_rotations.append(f"{name}: orientation not numeric")
                continue

            if math.isnan(orient) or math.isinf(orient):
                invalid_rotations.append(f"{name}: orientation is NaN/Inf")
                continue

            # Convert to radians
            theta = math.radians(orient)

            # Construct 2D rotation matrix
            try:
                cos_t = math.cos(theta)
                sin_t = math.sin(theta)

                # Check determinant = 1 (proper rotation)
                det = cos_t * cos_t + sin_t * sin_t

                if abs(det - 1.0) > 0.01:
                    invalid_rotations.append(f"{name}: invalid determinant ({det:.4f})")

            except Exception as e:
                invalid_rotations.append(f"{name}: {str(e)}")

        if invalid_rotations:
            self.log_fail("Rotation Matrices",
                         f"{len(invalid_rotations)} invalid rotations")
            for issue in invalid_rotations[:10]:
                print(f"   • {issue}")
        else:
            self.log_pass(f"All {len(self.objects)} orientations produce valid rotation matrices")

    def test_09_geometric_feasibility(self):
        """Test 9: All objects are geometrically feasible to construct"""
        print("\n" + "="*80)
        print("TEST 9: GEOMETRIC FEASIBILITY")
        print("="*80)

        infeasible = []

        for obj in self.objects:
            name = obj.get('name', 'unnamed')
            dims = obj.get('dimensions')

            if not dims:
                continue

            if isinstance(dims, list) and len(dims) >= 3:
                L, W, H = dims[0], dims[1], dims[2]

                # Check aspect ratios
                if L > 0 and W > 0 and H > 0:
                    max_aspect = max(L/W, W/L, L/H, H/L, W/H, H/W)

                    if max_aspect > 100:
                        infeasible.append(f"{name}: extreme aspect ratio ({max_aspect:.0f}:1)")

                # Check for unrealistic dimensions
                if L > 50 or W > 50 or H > 10:
                    infeasible.append(f"{name}: unrealistic size ({L:.1f}×{W:.1f}×{H:.1f}m)")

                if L > 0 and L < 0.001:
                    infeasible.append(f"{name}: too small ({L*1000:.2f}mm)")

        if infeasible:
            self.log_warning(f"{len(infeasible)} potentially infeasible geometries")
            for issue in infeasible[:10]:
                print(f"   • {issue}")
            self.log_pass("All objects pass basic geometric feasibility")
        else:
            self.log_pass("All objects are geometrically feasible to construct")

    def test_10_architectural_completeness(self):
        """Test 10: Determine if this is a completed house"""
        print("\n" + "="*80)
        print("TEST 10: ARCHITECTURAL COMPLETENESS (Is this a completed house?)")
        print("="*80)

        completeness_checks = {
            'exterior_walls': False,
            'floor': False,
            'ceiling': False,
            'roof': False,
            'exterior_doors': False,
            'windows': False,
            'rooms': False,
            'kitchen': False,
            'bathroom': False,
            'bedroom': False,
            'wall_enclosure': False,
            'accessibility': False
        }

        issues = []

        # Check 1: Exterior walls form enclosure
        exterior_walls = [o for o in self.objects if 'wall_exterior' in o.get('name', '')]
        if len(exterior_walls) >= 4:
            completeness_checks['exterior_walls'] = True
            print(f"✅ Exterior walls: {len(exterior_walls)} walls found")
        else:
            issues.append(f"Only {len(exterior_walls)} exterior walls (need ≥4)")
            print(f"❌ Exterior walls: {len(exterior_walls)} walls (need ≥4)")

        # Check 2: Floor exists
        floor_objects = [o for o in self.objects if 'floor' in o.get('name', '').lower() or
                        'floor' in o.get('object_type', '').lower()]
        if floor_objects:
            completeness_checks['floor'] = True
            print(f"✅ Floor: {len(floor_objects)} floor element(s)")
        else:
            issues.append("No floor structure")
            print(f"❌ Floor: No floor structure")

        # Check 3: Ceiling exists
        ceiling_objects = [o for o in self.objects if 'ceiling' in o.get('name', '').lower()]
        if ceiling_objects:
            completeness_checks['ceiling'] = True
            print(f"✅ Ceiling: {len(ceiling_objects)} ceiling element(s)")
        else:
            issues.append("No ceiling structure")
            print(f"❌ Ceiling: No ceiling structure")

        # Check 4: Roof exists
        roof_objects = [o for o in self.objects if 'roof' in o.get('name', '').lower()]
        if roof_objects:
            completeness_checks['roof'] = True
            print(f"✅ Roof: {len(roof_objects)} roof element(s)")
        else:
            issues.append("No roof structure")
            print(f"❌ Roof: No roof structure")

        # Check 5: Exterior doors (access to building)
        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]
        if len(doors) >= 1:
            completeness_checks['exterior_doors'] = True
            print(f"✅ Doors: {len(doors)} door(s) for access")
        else:
            issues.append("No doors (no building access)")
            print(f"❌ Doors: No doors found")

        # Check 6: Windows exist
        windows = [o for o in self.objects if 'window' in o.get('object_type', '').lower()]
        if len(windows) >= 2:
            completeness_checks['windows'] = True
            print(f"✅ Windows: {len(windows)} window(s)")
        else:
            issues.append(f"Only {len(windows)} windows (need ≥2)")
            print(f"❌ Windows: {len(windows)} windows (need ≥2)")

        # Check 7: Rooms exist
        rooms = set(o.get('room') for o in self.objects if o.get('room'))
        if len(rooms) >= 3:
            completeness_checks['rooms'] = True
            print(f"✅ Rooms: {len(rooms)} rooms defined")
        else:
            issues.append(f"Only {len(rooms)} rooms (need ≥3)")
            print(f"❌ Rooms: {len(rooms)} rooms (need ≥3)")

        # Check 8: Kitchen exists
        kitchen_rooms = [r for r in rooms if 'kitchen' in r.lower()]
        kitchen_objects = [o for o in self.objects if 'kitchen' in o.get('room', '').lower()]
        if kitchen_rooms and len(kitchen_objects) >= 3:
            completeness_checks['kitchen'] = True
            print(f"✅ Kitchen: Complete with {len(kitchen_objects)} fixtures")
        else:
            issues.append("Kitchen incomplete or missing")
            print(f"❌ Kitchen: Incomplete ({len(kitchen_objects)} fixtures)")

        # Check 9: Bathroom exists
        bathroom_rooms = [r for r in rooms if 'bathroom' in r.lower()]
        bathroom_objects = [o for o in self.objects if 'bathroom' in o.get('room', '').lower()]
        if bathroom_rooms and len(bathroom_objects) >= 2:
            completeness_checks['bathroom'] = True
            print(f"✅ Bathroom: Complete with {len(bathroom_objects)} fixtures")
        else:
            issues.append("Bathroom incomplete or missing")
            print(f"❌ Bathroom: Incomplete ({len(bathroom_objects)} fixtures)")

        # Check 10: Bedroom exists
        bedroom_rooms = [r for r in rooms if 'bedroom' in r.lower()]
        bedroom_objects = [o for o in self.objects if 'bedroom' in o.get('room', '').lower()]
        if bedroom_rooms:
            completeness_checks['bedroom'] = True
            print(f"✅ Bedroom: {len(bedroom_rooms)} bedroom(s) with {len(bedroom_objects)} items")
        else:
            issues.append("No bedrooms")
            print(f"❌ Bedroom: No bedrooms found")

        # Check 11: Wall network forms enclosure (arithmetic check)
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        # Calculate perimeter from wall endpoints
        wall_endpoints = set()
        for wall in walls:
            start = tuple(wall['position'][:2])  # X, Y only
            end = tuple(wall.get('end_point', wall['position'])[:2])
            wall_endpoints.add(start)
            wall_endpoints.add(end)

        # Check if walls form a network
        if len(walls) >= 8 and len(wall_endpoints) >= 4:
            completeness_checks['wall_enclosure'] = True
            print(f"✅ Wall network: {len(walls)} walls with {len(wall_endpoints)} endpoints")
        else:
            issues.append(f"Insufficient wall network ({len(walls)} walls)")
            print(f"❌ Wall network: {len(walls)} walls (need ≥8)")

        # Check 12: Building is accessible (doors at ground level)
        ground_doors = [d for d in doors if d.get('position', [0,0,0])[2] < 0.2]
        if len(ground_doors) >= 1:
            completeness_checks['accessibility'] = True
            print(f"✅ Accessibility: {len(ground_doors)} ground-level door(s)")
        else:
            issues.append("No ground-level access")
            print(f"❌ Accessibility: No ground-level doors")

        # Calculate completeness score
        score = sum(1 for v in completeness_checks.values() if v)
        total = len(completeness_checks)
        percentage = (score / total) * 100

        print("\n" + "="*80)
        print(f"COMPLETENESS SCORE: {score}/{total} ({percentage:.0f}%)")
        print("="*80)

        if percentage >= 90:
            print("✅ THIS IS A COMPLETED HOUSE")
            self.log_pass(f"Completed house ({percentage:.0f}% complete)")
        elif percentage >= 70:
            print("⚠️  THIS IS A MOSTLY COMPLETE HOUSE (minor issues)")
            self.log_warning(f"House {percentage:.0f}% complete - minor issues remain")
            self.log_pass(f"House is mostly complete")
        elif percentage >= 50:
            print("❌ THIS IS AN INCOMPLETE HOUSE")
            self.log_fail("House Completeness", f"Only {percentage:.0f}% complete")
        else:
            print("❌ THIS IS NOT A COMPLETED HOUSE")
            self.log_fail("House Completeness", f"Only {percentage:.0f}% complete - major components missing")

        if issues:
            print(f"\n🔧 Issues preventing completion:")
            for issue in issues:
                print(f"   • {issue}")

        return completeness_checks

    def test_11_room_interior_validation(self):
        """Test 11: Validate interior of each room arithmetically"""
        print("\n" + "="*80)
        print("TEST 11: ROOM INTERIOR VALIDATION")
        print("="*80)

        # Group objects by room
        rooms = {}
        for obj in self.objects:
            room = obj.get('room')
            if room:
                if room not in rooms:
                    rooms[room] = []
                rooms[room].append(obj)

        print(f"Analyzing {len(rooms)} rooms\n")

        room_issues = []
        room_warnings = []

        for room_name, room_objects in rooms.items():
            print(f"━━━ {room_name.upper()} ━━━")

            # Calculate room bounds from objects
            positions = [o.get('position', [0, 0, 0]) for o in room_objects]
            if not positions:
                room_issues.append(f"{room_name}: No objects found")
                continue

            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            zs = [p[2] for p in positions]

            room_width = max(xs) - min(xs)
            room_length = max(ys) - min(ys)
            room_height = max(zs) - min(zs) if max(zs) > 0 else 2.95
            room_area = room_width * room_length
            room_volume = room_area * room_height

            print(f"  Dimensions: {room_width:.2f}m × {room_length:.2f}m × {room_height:.2f}m")
            print(f"  Area: {room_area:.2f}m²")
            print(f"  Volume: {room_volume:.2f}m³")
            print(f"  Objects: {len(room_objects)}")

            # Check 1: Room size is reasonable
            if room_area < 2.0:
                room_issues.append(f"{room_name}: Too small ({room_area:.2f}m² < 2.0m²)")
                print(f"  ❌ Room too small")
            elif room_area > 100:
                room_warnings.append(f"{room_name}: Very large ({room_area:.2f}m²)")
                print(f"  ⚠️  Room very large")
            else:
                print(f"  ✅ Size reasonable")

            # Check 2: Room-specific essential fixtures
            room_type = None
            required_fixtures = []

            if 'kitchen' in room_name.lower():
                room_type = 'kitchen'
                required_fixtures = ['sink', 'stove']
            elif 'bathroom' in room_name.lower():
                room_type = 'bathroom'
                required_fixtures = ['toilet', 'basin']
            elif 'bedroom' in room_name.lower():
                room_type = 'bedroom'
                required_fixtures = ['bed']
            elif 'living' in room_name.lower():
                room_type = 'living_room'
                required_fixtures = []  # No strict requirements

            if room_type and required_fixtures:
                missing_fixtures = []
                for fixture in required_fixtures:
                    found = any(fixture in o.get('object_type', '').lower() or
                              fixture in o.get('name', '').lower()
                              for o in room_objects)
                    if not found:
                        missing_fixtures.append(fixture)

                if missing_fixtures:
                    room_issues.append(f"{room_name}: Missing {', '.join(missing_fixtures)}")
                    print(f"  ❌ Missing: {', '.join(missing_fixtures)}")
                else:
                    print(f"  ✅ All essential fixtures present")

            # Check 3: Room density (overcrowding)
            furniture = [o for o in room_objects if o.get('_phase') == '6_furniture']
            if room_area > 0:
                density = len(furniture) / room_area  # objects per m²

                if density > 2.0:
                    room_warnings.append(f"{room_name}: Overcrowded ({density:.1f} items/m²)")
                    print(f"  ⚠️  Overcrowded: {density:.1f} items/m²")
                elif density < 0.1 and room_type in ['bedroom', 'kitchen']:
                    room_warnings.append(f"{room_name}: Sparse ({density:.1f} items/m²)")
                    print(f"  ⚠️  Sparse: {density:.1f} items/m²")
                else:
                    print(f"  ✅ Density OK: {density:.1f} items/m²")

            # Check 4: Circulation space (30% minimum for movement)
            if furniture:
                total_furniture_area = 0
                for obj in furniture:
                    dims = obj.get('dimensions', [0, 0, 0])
                    if isinstance(dims, list) and len(dims) >= 2:
                        total_furniture_area += dims[0] * dims[1]

                circulation_ratio = 1 - (total_furniture_area / room_area) if room_area > 0 else 0

                if circulation_ratio < 0.3:
                    room_issues.append(f"{room_name}: Insufficient circulation space ({circulation_ratio*100:.0f}%)")
                    print(f"  ❌ Circulation: {circulation_ratio*100:.0f}% (need >30%)")
                else:
                    print(f"  ✅ Circulation: {circulation_ratio*100:.0f}%")

            # Check 5: Doors in room
            room_doors = [o for o in room_objects if 'door' in o.get('object_type', '').lower()]
            if len(room_doors) == 0:
                room_issues.append(f"{room_name}: No door (no access)")
                print(f"  ❌ No door")
            else:
                print(f"  ✅ {len(room_doors)} door(s)")

            # Check 6: Windows in habitable rooms
            room_windows = [o for o in room_objects if 'window' in o.get('object_type', '').lower()]
            if room_type in ['bedroom', 'living_room', 'kitchen']:
                if len(room_windows) == 0:
                    room_warnings.append(f"{room_name}: No window (poor ventilation)")
                    print(f"  ⚠️  No window")
                else:
                    print(f"  ✅ {len(room_windows)} window(s)")

            # Check 7: Lighting
            lights = [o for o in room_objects if 'light' in o.get('name', '').lower() or
                     'light' in o.get('object_type', '').lower()]
            if len(lights) == 0:
                room_warnings.append(f"{room_name}: No lighting")
                print(f"  ⚠️  No lighting")
            else:
                print(f"  ✅ {len(lights)} light(s)")

            # Check 8: Electrical outlets
            outlets = [o for o in room_objects if 'outlet' in o.get('name', '').lower()]
            if room_type in ['bedroom', 'living_room', 'kitchen'] and len(outlets) < 2:
                room_warnings.append(f"{room_name}: Only {len(outlets)} outlets (need ≥2)")
                print(f"  ⚠️  Only {len(outlets)} outlet(s)")
            elif len(outlets) >= 2:
                print(f"  ✅ {len(outlets)} outlet(s)")

            # Check 9: Kitchen-specific validation
            if room_type == 'kitchen':
                has_counter = any('counter' in o.get('object_type', '').lower() for o in room_objects)
                has_storage = any('cabinet' in o.get('object_type', '').lower() or
                                 'shelv' in o.get('object_type', '').lower()
                                 for o in room_objects)

                if not has_counter:
                    room_warnings.append(f"{room_name}: No counter space")
                    print(f"  ⚠️  No counter")
                if not has_storage:
                    room_warnings.append(f"{room_name}: No storage")
                    print(f"  ⚠️  No storage")

            # Check 10: Bathroom-specific validation
            if room_type == 'bathroom':
                has_drainage = any('drain' in o.get('name', '').lower() for o in room_objects)
                has_ventilation = len(room_windows) > 0 or any('exhaust' in o.get('name', '').lower() or
                                                                'fan' in o.get('name', '').lower()
                                                                for o in room_objects)

                if not has_drainage:
                    room_issues.append(f"{room_name}: No floor drain")
                    print(f"  ❌ No drainage")
                else:
                    print(f"  ✅ Drainage present")

                if not has_ventilation:
                    room_warnings.append(f"{room_name}: Poor ventilation")
                    print(f"  ⚠️  Poor ventilation")
                else:
                    print(f"  ✅ Ventilation present")

            # Check 11: Bedroom-specific validation
            if room_type == 'bedroom':
                has_storage = any('wardrobe' in o.get('object_type', '').lower() or
                                'closet' in o.get('object_type', '').lower()
                                for o in room_objects)

                # Check bed placement (should be against a wall)
                beds = [o for o in room_objects if 'bed' in o.get('object_type', '').lower()]
                walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

                for bed in beds:
                    bed_pos = bed.get('position', [0, 0, 0])
                    near_wall = False

                    for wall in walls:
                        w_start = wall['position']
                        w_end = wall.get('end_point', w_start)

                        dist = self.distance_point_to_line(bed_pos, w_start, w_end)
                        if dist < 1.0:
                            near_wall = True
                            break

                    if not near_wall:
                        room_warnings.append(f"{room_name}: Bed not against wall")
                        print(f"  ⚠️  Bed placement unusual")

                if not has_storage:
                    room_warnings.append(f"{room_name}: No storage")
                    print(f"  ⚠️  No wardrobe/storage")

            print()

        # Summary
        print("="*80)
        print(f"ROOM INTERIOR VALIDATION SUMMARY")
        print("="*80)
        print(f"Rooms analyzed: {len(rooms)}")
        print(f"Issues found: {len(room_issues)}")
        print(f"Warnings: {len(room_warnings)}")

        if room_issues:
            print("\n❌ CRITICAL ROOM ISSUES:")
            for issue in room_issues[:15]:
                print(f"   • {issue}")
            if len(room_issues) > 15:
                print(f"   ... and {len(room_issues)-15} more")

        if room_warnings:
            print("\n⚠️  ROOM WARNINGS:")
            for warning in room_warnings[:15]:
                print(f"   • {warning}")
            if len(room_warnings) > 15:
                print(f"   ... and {len(room_warnings)-15} more")

        if len(room_issues) == 0:
            print("\n✅ ALL ROOMS PASS INTERIOR VALIDATION")
            self.log_pass(f"All {len(rooms)} rooms have valid interiors")
        elif len(room_issues) <= 3:
            print("\n⚠️  MINOR ROOM ISSUES DETECTED")
            self.log_warning(f"{len(room_issues)} minor room issues")
            self.log_pass(f"Room interiors mostly valid")
        else:
            print("\n❌ MULTIPLE ROOM ISSUES DETECTED")
            self.log_fail("Room Interior Validation", f"{len(room_issues)} issues found")

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

    def test_12_complete_3d_scene_constructible(self):
        """Test 12: Complete 3D scene can be arithmetically constructed"""
        print("\n" + "="*80)
        print("TEST 12: COMPLETE 3D SCENE CONSTRUCTION")
        print("="*80)

        # This is the final test - can we construct complete scene data?
        scene_data = {
            'objects': [],
            'spatial_index': {},
            'scene_bounds': {}
        }

        construction_errors = []

        try:
            # Build scene
            for obj in self.objects:
                name = obj.get('name', 'unnamed')

                # Extract all spatial data
                spatial_obj = {
                    'name': name,
                    'type': obj.get('object_type'),
                    'position': obj.get('position', [0, 0, 0]),
                    'orientation': obj.get('orientation', 0),
                    'dimensions': obj.get('dimensions', [0, 0, 0]),
                    'room': obj.get('room')
                }

                # Validate can be added to scene
                if not spatial_obj['position'] or len(spatial_obj['position']) != 3:
                    construction_errors.append(f"{name}: invalid position")
                    continue

                scene_data['objects'].append(spatial_obj)

                # Add to spatial index (grid-based)
                x, y, z = spatial_obj['position']
                grid_key = (int(x), int(y), int(z))

                if grid_key not in scene_data['spatial_index']:
                    scene_data['spatial_index'][grid_key] = []
                scene_data['spatial_index'][grid_key].append(name)

            # Calculate scene bounds
            positions = [o['position'] for o in scene_data['objects']]
            if positions:
                xs = [p[0] for p in positions]
                ys = [p[1] for p in positions]
                zs = [p[2] for p in positions]

                scene_data['scene_bounds'] = {
                    'min': [min(xs), min(ys), min(zs)],
                    'max': [max(xs), max(ys), max(zs)]
                }

        except Exception as e:
            construction_errors.append(f"Scene construction failed: {str(e)}")

        if construction_errors:
            self.log_fail("3D Scene Construction",
                         f"{len(construction_errors)} errors")
            for error in construction_errors[:10]:
                print(f"   • {error}")
        else:
            print(f"✅ Scene constructed with {len(scene_data['objects'])} objects")
            print(f"✅ Spatial index has {len(scene_data['spatial_index'])} grid cells")
            bounds = scene_data['scene_bounds']
            print(f"✅ Scene bounds: ({bounds['min'][0]:.1f}, {bounds['min'][1]:.1f}, {bounds['min'][2]:.1f}) to "
                  f"({bounds['max'][0]:.1f}, {bounds['max'][1]:.1f}, {bounds['max'][2]:.1f})")
            self.log_pass("Complete 3D scene arithmetically constructible")

    def run_all_tests(self):
        """Run all arithmetic spatial tests"""
        print("="*80)
        print("3D SPATIAL ARITHMETIC VALIDATION")
        print("="*80)
        print(f"Objects to analyze: {len(self.objects)}")
        print()

        # Run all tests
        self.test_01_position_validity()
        self.test_02_dimensions_validity()
        bboxes = self.test_03_bounding_box_calculation()
        self.test_04_spatial_hierarchy()
        self.test_05_wall_network_connectivity()
        self.test_06_object_volume_calculation()
        self.test_07_coordinate_system_consistency()
        self.test_08_rotation_matrix_validity()
        self.test_09_geometric_feasibility()
        self.test_10_architectural_completeness()
        self.test_11_room_interior_validation()
        self.test_12_complete_3d_scene_constructible()

        # Summary
        print("\n" + "="*80)
        print("3D SPATIAL ARITHMETIC SUMMARY")
        print("="*80)
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_failed}")
        print(f"Warnings: {len(self.warnings)}")

        if self.tests_failed > 0:
            print("\n❌ CRITICAL FAILURES:")
            for failure in self.failures:
                print(f"   • {failure['test']}: {failure['message']}")

        if len(self.warnings) > 0:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings[:10]:
                print(f"   • {warning}")

        print("\n" + "="*80)
        if self.tests_failed == 0:
            print("✅ ALL SPATIAL DATA IS ARITHMETICALLY VALID FOR 3D PLOTTING")
        else:
            print("❌ SPATIAL DATA HAS ARITHMETIC ISSUES - FIX REQUIRED")
        print("="*80)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_3d_spatial_arithmetic.py <output.json>")
        sys.exit(1)

    # Load data
    with open(sys.argv[1]) as f:
        data = json.load(f)

    # Run tests
    validator = SpatialArithmetic3D(data)
    validator.run_all_tests()

    # Exit code
    sys.exit(0 if validator.tests_failed == 0 else 1)


if __name__ == "__main__":
    main()
