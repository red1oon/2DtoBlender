#!/usr/bin/env python3
"""
Bug Hunter - Aggressive edge case and anomaly detection

Tests specifically designed to find bugs:
- Numerical edge cases (NaN, Inf, division by zero)
- Geometric anomalies (degenerate shapes, self-intersection)
- Logic errors (impossible states, contradictions)
- Data corruption (type mismatches, missing references)
- Edge cases that break assumptions
"""

import json
import math
import sys
import re
from collections import defaultdict


class BugHunter:
    """Aggressive testing to find bugs and edge cases"""

    def __init__(self, data):
        self.data = data
        self.objects = data.get('objects', [])
        self.metadata = data.get('extraction_metadata', {})
        self.bugs_found = []
        self.test_count = 0
        self.bug_count = 0

    def log_bug(self, test_name, severity, message, evidence=None):
        """Log a discovered bug"""
        self.bug_count += 1
        self.bugs_found.append({
            'test': test_name,
            'severity': severity,  # CRITICAL, HIGH, MEDIUM, LOW
            'message': message,
            'evidence': evidence or []
        })

    def test_result(self, passed):
        """Record test result"""
        self.test_count += 1
        if not passed:
            return "🐛 BUG FOUND"
        return "✅ PASS"

    # =========================================================================
    # NUMERICAL EDGE CASES
    # =========================================================================

    def test_nan_infinity_values(self):
        """Test for NaN and Infinity in numerical fields"""
        print("\n🔍 TEST: NaN/Infinity Detection")
        print("-" * 80)

        bugs = []

        for obj in self.objects:
            # Check position
            pos = obj.get('position', [])
            if isinstance(pos, list):
                for i, coord in enumerate(pos):
                    if isinstance(coord, (int, float)):
                        if math.isnan(coord):
                            bugs.append(f"{obj['name']}: position[{i}] is NaN")
                        elif math.isinf(coord):
                            bugs.append(f"{obj['name']}: position[{i}] is Infinity")

            # Check orientation
            orient = obj.get('orientation')
            if isinstance(orient, (int, float)):
                if math.isnan(orient):
                    bugs.append(f"{obj['name']}: orientation is NaN")
                elif math.isinf(orient):
                    bugs.append(f"{obj['name']}: orientation is Infinity")

            # Check dimensions
            dims = obj.get('dimensions', [])
            if isinstance(dims, list):
                for i, dim in enumerate(dims):
                    if isinstance(dim, (int, float)):
                        if math.isnan(dim):
                            bugs.append(f"{obj['name']}: dimensions[{i}] is NaN")
                        elif math.isinf(dim):
                            bugs.append(f"{obj['name']}: dimensions[{i}] is Infinity")

        if bugs:
            self.log_bug('NaN/Infinity', 'CRITICAL',
                        f'{len(bugs)} objects with invalid numerical values', bugs[:10])
            print(f"{self.test_result(False)}: {len(bugs)} invalid values")
            for bug in bugs[:5]:
                print(f"  • {bug}")
        else:
            print(f"{self.test_result(True)}: No NaN/Inf values")

    def test_division_by_zero_risks(self):
        """Test for conditions that could cause division by zero"""
        print("\n🔍 TEST: Division by Zero Risks")
        print("-" * 80)

        bugs = []

        # Check for zero-length walls
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]
        for wall in walls:
            start = wall.get('position', [0, 0, 0])
            end = wall.get('end_point', start)

            length = math.sqrt(sum((a - b)**2 for a, b in zip(start, end)))
            if length < 1e-10:  # Effectively zero
                bugs.append(f"{wall['name']}: zero-length wall (causes division by zero in orientation calc)")

        # Check for zero-area rooms
        rooms = defaultdict(list)
        for obj in self.objects:
            room = obj.get('room')
            if room:
                rooms[room].append(obj)

        for room_name, room_objects in rooms.items():
            positions = [o.get('position', [0, 0, 0]) for o in room_objects]
            if len(positions) > 1:
                xs = [p[0] for p in positions]
                ys = [p[1] for p in positions]

                width = max(xs) - min(xs)
                length = max(ys) - min(ys)
                area = width * length

                if area < 1e-6:  # ~1mm²
                    bugs.append(f"{room_name}: zero area ({area:.10f}m²) - division by zero in density calc")

        if bugs:
            self.log_bug('Division by Zero', 'HIGH',
                        f'{len(bugs)} conditions that could cause division by zero', bugs)
            print(f"{self.test_result(False)}: {len(bugs)} risky conditions")
            for bug in bugs[:5]:
                print(f"  • {bug}")
        else:
            print(f"{self.test_result(True)}: No division by zero risks")

    def test_floating_point_precision(self):
        """Test for floating point precision errors"""
        print("\n🔍 TEST: Floating Point Precision Errors")
        print("-" * 80)

        bugs = []

        # Check for values very close to zero (should be exactly zero)
        for obj in self.objects:
            pos = obj.get('position', [0, 0, 0])

            for i, coord in enumerate(pos):
                if isinstance(coord, (int, float)):
                    # If value is very small but not zero, it's likely a precision error
                    if 0 < abs(coord) < 1e-10:
                        bugs.append(f"{obj['name']}: position[{i}]={coord:.15e} (precision error, should be 0)")

        # Check for equality comparisons that might fail
        # Find objects at "same" position
        positions = {}
        for obj in self.objects:
            pos = tuple(obj.get('position', [0, 0, 0]))
            if pos in positions:
                positions[pos].append(obj['name'])
            else:
                positions[pos] = [obj['name']]

        # Now check for positions that are ALMOST the same but not exactly
        pos_list = list(positions.keys())
        for i in range(len(pos_list)):
            for j in range(i + 1, len(pos_list)):
                dist = math.sqrt(sum((a - b)**2 for a, b in zip(pos_list[i], pos_list[j])))
                if 0 < dist < 1e-6:  # Within 1 micron but not equal
                    bugs.append(f"Positions {pos_list[i]} and {pos_list[j]} differ by {dist:.10e}m (precision error)")

        if bugs:
            self.log_bug('Floating Point', 'MEDIUM',
                        f'{len(bugs)} floating point precision issues', bugs[:10])
            print(f"{self.test_result(False)}: {len(bugs)} precision errors")
            for bug in bugs[:5]:
                print(f"  • {bug}")
        else:
            print(f"{self.test_result(True)}: No precision errors")

    # =========================================================================
    # GEOMETRIC ANOMALIES
    # =========================================================================

    def test_degenerate_geometry(self):
        """Test for degenerate geometric shapes"""
        print("\n🔍 TEST: Degenerate Geometry")
        print("-" * 80)

        bugs = []

        # Check for walls with same start and end point
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]
        for wall in walls:
            start = wall.get('position', [0, 0, 0])
            end = wall.get('end_point', [0, 0, 0])

            if start == end:
                bugs.append(f"{wall['name']}: degenerate wall (start == end)")

        # Check for objects with zero dimensions
        for obj in self.objects:
            dims = obj.get('dimensions', [])
            if isinstance(dims, list) and len(dims) > 0:
                if any(d == 0 for d in dims):
                    bugs.append(f"{obj['name']}: zero dimension {dims}")
                if any(d < 0 for d in dims):
                    bugs.append(f"{obj['name']}: negative dimension {dims}")

        # Check for colinear walls (multiple walls on same line)
        for i in range(len(walls)):
            for j in range(i + 1, len(walls)):
                w1_start = walls[i].get('position', [0, 0, 0])
                w1_end = walls[i].get('end_point', [0, 0, 0])
                w2_start = walls[j].get('position', [0, 0, 0])
                w2_end = walls[j].get('end_point', [0, 0, 0])

                # Check if all four points are colinear
                # Using cross product: if (p2-p1) × (p3-p1) = 0, they're colinear
                v1 = (w1_end[0] - w1_start[0], w1_end[1] - w1_start[1])
                v2 = (w2_start[0] - w1_start[0], w2_start[1] - w1_start[1])
                v3 = (w2_end[0] - w1_start[0], w2_end[1] - w1_start[1])

                cross1 = v1[0] * v2[1] - v1[1] * v2[0]
                cross2 = v1[0] * v3[1] - v1[1] * v3[0]

                if abs(cross1) < 1e-6 and abs(cross2) < 1e-6:
                    bugs.append(f"{walls[i]['name']} and {walls[j]['name']}: colinear walls")

        if bugs:
            self.log_bug('Degenerate Geometry', 'HIGH',
                        f'{len(bugs)} degenerate shapes', bugs[:10])
            print(f"{self.test_result(False)}: {len(bugs)} degenerate shapes")
            for bug in bugs[:5]:
                print(f"  • {bug}")
        else:
            print(f"{self.test_result(True)}: No degenerate geometry")

    def test_self_intersecting_walls(self):
        """Test for walls that intersect with themselves"""
        print("\n🔍 TEST: Self-Intersecting Walls")
        print("-" * 80)

        bugs = []

        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        # Check if any wall segment intersects with non-adjacent walls
        for i in range(len(walls)):
            for j in range(i + 2, len(walls)):  # Skip adjacent walls
                if self._segments_intersect(walls[i], walls[j]):
                    bugs.append(f"{walls[i]['name']} intersects with {walls[j]['name']}")

        if bugs:
            self.log_bug('Self-Intersection', 'HIGH',
                        f'{len(bugs)} wall intersections', bugs[:10])
            print(f"{self.test_result(False)}: {len(bugs)} intersections")
            for bug in bugs[:5]:
                print(f"  • {bug}")
        else:
            print(f"{self.test_result(True)}: No self-intersections")

    def test_impossible_orientations(self):
        """Test for physically impossible orientations"""
        print("\n🔍 TEST: Impossible Orientations")
        print("-" * 80)

        bugs = []

        # Check for doors/windows with vertical orientation (should be in walls)
        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]
        windows = [o for o in self.objects if 'window' in o.get('object_type', '').lower()]

        for obj in doors + windows:
            orient = obj.get('orientation', 0)

            # Doors/windows should have horizontal orientations (0, 90, 180, 270)
            # Not vertical orientations
            if orient not in [0, 90, 180, 270]:
                bugs.append(f"{obj['name']}: unusual orientation {orient}° (not aligned to walls)")

        # Check for ceiling objects pointing down
        ceiling_objs = [o for o in self.objects
                       if 'ceiling' in o.get('object_type', '').lower()
                       or 'light' in o.get('object_type', '').lower()]

        for obj in ceiling_objs:
            pos = obj.get('position', [0, 0, 0])
            if pos[2] < 1.0:  # Ceiling object below 1m
                bugs.append(f"{obj['name']}: ceiling object at Z={pos[2]}m (should be near ceiling)")

        if bugs:
            self.log_bug('Impossible Orientations', 'MEDIUM',
                        f'{len(bugs)} orientation issues', bugs[:10])
            print(f"{self.test_result(False)}: {len(bugs)} issues")
            for bug in bugs[:5]:
                print(f"  • {bug}")
        else:
            print(f"{self.test_result(True)}: All orientations valid")

    # =========================================================================
    # LOGIC ERRORS
    # =========================================================================

    def test_impossible_states(self):
        """Test for logically impossible states"""
        print("\n🔍 TEST: Impossible States")
        print("-" * 80)

        bugs = []

        # Test 1: Objects marked as placed but still at origin
        for obj in self.objects:
            if obj.get('placed', False):
                pos = obj.get('position', [0, 0, 0])
                if pos == [0, 0, 0]:
                    bugs.append(f"{obj['name']}: marked as placed but at origin")

        # Test 2: Doors without walls
        doors = [o for o in self.objects if 'door' in o.get('object_type', '').lower()]
        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        if len(doors) > 0 and len(walls) == 0:
            bugs.append(f"Building has {len(doors)} doors but no walls")

        # Test 3: Windows higher than building
        windows = [o for o in self.objects if 'window' in o.get('object_type', '').lower()]
        building_height = self.metadata.get('building_dimensions', {}).get('height', 3.0)

        for window in windows:
            pos = window.get('position', [0, 0, 0])
            if pos[2] > building_height:
                bugs.append(f"{window['name']}: window above building (Z={pos[2]}m, height={building_height}m)")

        # Test 4: Toilets without plumbing
        toilets = [o for o in self.objects if 'toilet' in o.get('object_type', '').lower()]
        drains = [o for o in self.objects if 'drain' in o.get('object_type', '').lower()]

        if len(toilets) > 0 and len(drains) == 0:
            bugs.append(f"Building has {len(toilets)} toilets but no drainage system")

        # Test 5: Rooms with furniture but no floor
        floor = [o for o in self.objects if 'floor' in o.get('object_type', '').lower()]
        furniture = [o for o in self.objects if 'bed' in o.get('object_type', '').lower()
                    or 'sofa' in o.get('object_type', '').lower()]

        if len(furniture) > 0 and len(floor) == 0:
            bugs.append(f"Building has {len(furniture)} furniture items but no floor")

        # Test 6: Electrical fixtures without distribution
        lights = [o for o in self.objects if 'light' in o.get('object_type', '').lower()]
        switches = [o for o in self.objects if 'switch' in o.get('object_type', '').lower()]
        db = [o for o in self.objects if 'distribution' in o.get('object_type', '').lower()]

        if len(lights) > 0 and len(db) == 0:
            self.log_bug('Impossible States', 'LOW',
                        'Lights without distribution board (may be acceptable)')

        if bugs:
            self.log_bug('Impossible States', 'HIGH',
                        f'{len(bugs)} logically impossible states', bugs)
            print(f"{self.test_result(False)}: {len(bugs)} impossible states")
            for bug in bugs:
                print(f"  • {bug}")
        else:
            print(f"{self.test_result(True)}: No impossible states")

    def test_contradictory_data(self):
        """Test for contradictory information"""
        print("\n🔍 TEST: Contradictory Data")
        print("-" * 80)

        bugs = []

        # Test 1: Object_type vs name mismatch
        for obj in self.objects:
            name = obj.get('name', '').lower()
            obj_type = obj.get('object_type', '').lower()

            # Extract key words from both
            name_words = set(re.findall(r'\w+', name))
            type_words = set(re.findall(r'\w+', obj_type))

            # Check for obvious contradictions
            contradictions = [
                ('door', 'window'),
                ('wall', 'floor'),
                ('toilet', 'basin'),
                ('ceiling', 'floor')
            ]

            for word1, word2 in contradictions:
                if word1 in name_words and word2 in type_words:
                    bugs.append(f"{obj['name']}: name suggests '{word1}' but type is '{word2}'")
                if word2 in name_words and word1 in type_words:
                    bugs.append(f"{obj['name']}: name suggests '{word2}' but type is '{word1}'")

        # Test 2: Room assignment contradictions
        rooms = defaultdict(list)
        for obj in self.objects:
            room = obj.get('room')
            if room:
                rooms[room].append(obj)

        # Check for exterior objects in interior rooms
        for room_name, room_objects in rooms.items():
            if 'exterior' in room_name.lower():
                interior_objects = [o for o in room_objects
                                  if 'interior' in o.get('name', '').lower()]
                if interior_objects:
                    bugs.append(f"{room_name}: contains interior objects {[o['name'] for o in interior_objects[:3]]}")

        # Test 3: Phase contradictions
        for obj in self.objects:
            phase = obj.get('_phase', '')
            obj_type = obj.get('object_type', '')

            # Furniture in early phases
            if 'furniture' in obj_type and phase in ['1A_schedules', '1B_calibration', '1C_walls']:
                bugs.append(f"{obj['name']}: furniture in early phase {phase}")

            # Walls in late phases
            if 'wall' in obj_type and phase in ['6_furniture']:
                bugs.append(f"{obj['name']}: wall in late phase {phase}")

        if bugs:
            self.log_bug('Contradictory Data', 'MEDIUM',
                        f'{len(bugs)} data contradictions', bugs[:10])
            print(f"{self.test_result(False)}: {len(bugs)} contradictions")
            for bug in bugs[:5]:
                print(f"  • {bug}")
        else:
            print(f"{self.test_result(True)}: No contradictions")

    def test_circular_dependencies(self):
        """Test for circular reference problems"""
        print("\n🔍 TEST: Circular Dependencies")
        print("-" * 80)

        bugs = []

        # Test 1: Objects referencing each other
        references = defaultdict(list)
        for obj in self.objects:
            obj_id = obj.get('name')

            # Check for references in various fields
            for key, value in obj.items():
                if isinstance(value, str) and value in [o.get('name') for o in self.objects]:
                    references[obj_id].append(value)

        # Check for cycles
        for obj_id in references:
            visited = set()
            current = obj_id

            while current in references and current not in visited:
                visited.add(current)
                if references[current]:
                    current = references[current][0]
                else:
                    break

            if current in visited and current == obj_id:
                bugs.append(f"Circular reference: {obj_id} references itself through {visited}")

        if bugs:
            self.log_bug('Circular Dependencies', 'MEDIUM',
                        f'{len(bugs)} circular references', bugs)
            print(f"{self.test_result(False)}: {len(bugs)} circular dependencies")
            for bug in bugs:
                print(f"  • {bug}")
        else:
            print(f"{self.test_result(True)}: No circular dependencies")

    # =========================================================================
    # DATA CORRUPTION
    # =========================================================================

    def test_type_mismatches(self):
        """Test for wrong data types"""
        print("\n🔍 TEST: Type Mismatches")
        print("-" * 80)

        bugs = []

        for obj in self.objects:
            # Position should be array of 3 numbers
            pos = obj.get('position')
            if pos is not None:
                if not isinstance(pos, list):
                    bugs.append(f"{obj['name']}: position is {type(pos).__name__}, not list")
                elif len(pos) != 3:
                    bugs.append(f"{obj['name']}: position has {len(pos)} elements, not 3")
                elif not all(isinstance(x, (int, float)) for x in pos):
                    bugs.append(f"{obj['name']}: position contains non-numeric values")

            # Orientation should be number
            orient = obj.get('orientation')
            if orient is not None and not isinstance(orient, (int, float)):
                bugs.append(f"{obj['name']}: orientation is {type(orient).__name__}, not number")

            # Placed should be boolean
            placed = obj.get('placed')
            if placed is not None and not isinstance(placed, bool):
                bugs.append(f"{obj['name']}: placed is {type(placed).__name__}, not boolean")

            # Name should be string
            name = obj.get('name')
            if name is not None and not isinstance(name, str):
                bugs.append(f"Object has name of type {type(name).__name__}, not string")

        if bugs:
            self.log_bug('Type Mismatches', 'CRITICAL',
                        f'{len(bugs)} type errors', bugs[:10])
            print(f"{self.test_result(False)}: {len(bugs)} type mismatches")
            for bug in bugs[:5]:
                print(f"  • {bug}")
        else:
            print(f"{self.test_result(True)}: All types correct")

    def test_missing_required_references(self):
        """Test for broken references"""
        print("\n🔍 TEST: Missing References")
        print("-" * 80)

        bugs = []

        # Check if all rooms referenced actually exist
        room_names = set(o.get('room') for o in self.objects if o.get('room'))

        # Check if room definitions exist (rooms should have walls)
        for room_name in room_names:
            room_objects = [o for o in self.objects if o.get('room') == room_name]
            room_walls = [o for o in room_objects if 'wall' in o.get('object_type', '').lower()]

            if len(room_objects) > 0 and len(room_walls) == 0:
                bugs.append(f"Room '{room_name}' referenced but has no walls (may not exist)")

        # Check for parent-child relationships
        # E.g., switches should have corresponding lights
        switches = [o for o in self.objects if 'switch' in o.get('object_type', '').lower()]
        lights = [o for o in self.objects if 'light' in o.get('object_type', '').lower()]

        for switch in switches:
            switch_room = switch.get('room')
            room_lights = [l for l in lights if l.get('room') == switch_room]

            if len(room_lights) == 0:
                bugs.append(f"{switch['name']}: switch in {switch_room} but no lights in that room")

        if bugs:
            self.log_bug('Missing References', 'MEDIUM',
                        f'{len(bugs)} broken references', bugs[:10])
            print(f"{self.test_result(False)}: {len(bugs)} missing references")
            for bug in bugs[:5]:
                print(f"  • {bug}")
        else:
            print(f"{self.test_result(True)}: All references valid")

    def test_empty_or_null_values(self):
        """Test for empty/null values where data is required"""
        print("\n🔍 TEST: Empty/Null Values")
        print("-" * 80)

        bugs = []

        for obj in self.objects:
            # Check for empty name
            name = obj.get('name')
            if not name or (isinstance(name, str) and name.strip() == ''):
                bugs.append(f"Object at index {self.objects.index(obj)}: empty name")

            # Check for empty object_type
            obj_type = obj.get('object_type')
            if not obj_type or (isinstance(obj_type, str) and obj_type.strip() == ''):
                bugs.append(f"{obj.get('name', 'unnamed')}: empty object_type")

            # Check for empty position array
            pos = obj.get('position')
            if isinstance(pos, list) and len(pos) == 0:
                bugs.append(f"{obj['name']}: empty position array")

        # Check for empty metadata
        if not self.metadata or len(self.metadata) == 0:
            bugs.append("Metadata is empty or missing")

        if bugs:
            self.log_bug('Empty Values', 'HIGH',
                        f'{len(bugs)} empty/null values', bugs[:10])
            print(f"{self.test_result(False)}: {len(bugs)} empty values")
            for bug in bugs[:5]:
                print(f"  • {bug}")
        else:
            print(f"{self.test_result(True)}: No empty values")

    # =========================================================================
    # STRING VALIDATION
    # =========================================================================

    def test_invalid_characters(self):
        """Test for invalid characters in strings"""
        print("\n🔍 TEST: Invalid Characters")
        print("-" * 80)

        bugs = []

        # Characters that cause problems in IFC, file systems, or databases
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\n', '\r', '\t', '\0']

        for obj in self.objects:
            name = obj.get('name', '')
            if isinstance(name, str):
                for char in invalid_chars:
                    if char in name:
                        bugs.append(f"{name}: contains invalid character '{repr(char)}'")
                        break

            obj_type = obj.get('object_type', '')
            if isinstance(obj_type, str):
                for char in invalid_chars:
                    if char in obj_type:
                        bugs.append(f"{obj['name']}: object_type contains invalid character '{repr(char)}'")
                        break

        if bugs:
            self.log_bug('Invalid Characters', 'MEDIUM',
                        f'{len(bugs)} invalid characters', bugs[:10])
            print(f"{self.test_result(False)}: {len(bugs)} invalid characters")
            for bug in bugs[:5]:
                print(f"  • {bug}")
        else:
            print(f"{self.test_result(True)}: No invalid characters")

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _segments_intersect(self, wall1, wall2):
        """Check if two line segments intersect"""
        p1 = wall1.get('position', [0, 0, 0])
        p2 = wall1.get('end_point', [0, 0, 0])
        p3 = wall2.get('position', [0, 0, 0])
        p4 = wall2.get('end_point', [0, 0, 0])

        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================

    def run_all_tests(self):
        """Execute all bug hunting tests"""
        print("=" * 80)
        print("🐛 BUG HUNTER - Aggressive Edge Case Detection")
        print("=" * 80)
        print("Testing for bugs, edge cases, and anomalies")
        print(f"Objects: {len(self.objects)}")
        print()

        # Run all tests
        self.test_nan_infinity_values()
        self.test_division_by_zero_risks()
        self.test_floating_point_precision()
        self.test_degenerate_geometry()
        self.test_self_intersecting_walls()
        self.test_impossible_orientations()
        self.test_impossible_states()
        self.test_contradictory_data()
        self.test_circular_dependencies()
        self.test_type_mismatches()
        self.test_missing_required_references()
        self.test_empty_or_null_values()
        self.test_invalid_characters()

        # Summary
        print("\n" + "=" * 80)
        print("🐛 BUG HUNTING SUMMARY")
        print("=" * 80)
        print(f"Tests Run: {self.test_count}")
        print(f"Bugs Found: {self.bug_count}")
        print()

        if self.bug_count > 0:
            # Group by severity
            by_severity = defaultdict(list)
            for bug in self.bugs_found:
                by_severity[bug['severity']].append(bug)

            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                bugs = by_severity[severity]
                if bugs:
                    print(f"\n{severity} SEVERITY: {len(bugs)} bugs")
                    print("-" * 80)
                    for bug in bugs:
                        print(f"\n{bug['test']}: {bug['message']}")
                        if bug['evidence']:
                            for evidence in bug['evidence'][:5]:
                                print(f"  • {evidence}")
                            if len(bug['evidence']) > 5:
                                print(f"  ... and {len(bug['evidence']) - 5} more")

        print("\n" + "=" * 80)
        if self.bug_count == 0:
            print("✅ NO BUGS FOUND - System is robust")
        else:
            print(f"🐛 {self.bug_count} BUGS DISCOVERED - Fix required")
        print("=" * 80)

        return 0 if self.bug_count == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_bug_hunter.py <output.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    hunter = BugHunter(data)
    sys.exit(hunter.run_all_tests())
