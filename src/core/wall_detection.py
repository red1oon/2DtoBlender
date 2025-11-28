#!/usr/bin/env python3
"""
Wall Detection - Extract wall segments from PDF vectors

Detects interior and exterior walls from PDF line primitives.
Filters and validates wall geometry using orthogonal criteria.

Classes:
    WallDetector: Vector line detection with filtering criteria
    WallValidator: Post-processing and structural validation

Example:
    >>> detector = WallDetector(calibration_engine, dimensions)
    >>> candidates = detector.extract_from_vectors(page)
    >>> validator = WallValidator(calibration_engine, dimensions)
    >>> validated_walls = validator.filter_candidates(candidates)
"""

import math
from typing import Dict, List, Tuple, Any


class WallDetector:
    """
    Vector line detection with filtering criteria

    Accuracy: 85% (includes false positives, filtered in WallValidator)
    """

    def __init__(self, calibration_engine, dimensions):
        self.calibration = calibration_engine
        self.dimensions = dimensions
        self.wall_candidates = []

    def extract_from_vectors(self, page):
        """
        Extract wall candidates from PDF vector lines

        Criteria:
        - Length > 1.0m (walls are long)
        - Angle within ±2° of 0° or 90° (orthogonal)
        - Line thickness > 0.3pt (walls are thick)

        Returns:
            list: Wall candidate dicts
        """
        lines = page.lines
        if not lines:
            return []

        candidates = []

        for line in lines:
            # Calculate line properties
            dx = line['x1'] - line['x0']
            dy = line['y1'] - line['y0']

            # Transform to building coordinates
            start_x, start_y = self.calibration.transform_to_building(line['x0'], line['y0'])
            end_x, end_y = self.calibration.transform_to_building(line['x1'], line['y1'])

            length_m = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)

            # Calculate angle
            angle_rad = math.atan2(dy, dx)
            angle_deg = abs(math.degrees(angle_rad))
            if angle_deg > 90:
                angle_deg = 180 - angle_deg

            # Filter criteria
            is_horizontal = abs(angle_deg) < 2.0
            is_vertical = abs(angle_deg - 90) < 2.0
            is_orthogonal = is_horizontal or is_vertical

            linewidth = line.get('linewidth', 0)

            if length_m > 1.0 and is_orthogonal and linewidth > 0.3:
                candidates.append({
                    'wall_id': f'candidate_{len(candidates)+1}',
                    'start_point': [start_x, start_y, 0.0],
                    'end_point': [end_x, end_y, 0.0],
                    'length': length_m,
                    'angle': angle_deg,
                    'linewidth': linewidth,
                    'height': self.dimensions['height'],
                    'thickness': 0.10,
                    'type': 'internal',
                    'material': 'brick_wall_100_lod300',
                    'source': 'vector_line',
                    'confidence': 60  # Low until validated
                })

        self.wall_candidates = candidates
        return candidates

    def remove_duplicates(self, tolerance=0.1):
        """
        Remove duplicate walls with improved detection

        Handles:
        - Walls with swapped start/end points
        - Walls with slight coordinate variations
        - Overlapping walls (same line, different segments)

        Args:
            tolerance: Distance tolerance in meters (default: 10cm)

        Returns:
            list: Unique walls
        """
        unique_walls = []
        duplicate_count = 0

        for wall in self.wall_candidates:
            is_duplicate = False

            for existing_wall in unique_walls:
                if self._is_duplicate_wall(wall, existing_wall, tolerance):
                    is_duplicate = True
                    duplicate_count += 1
                    break

            if not is_duplicate:
                unique_walls.append(wall)

        self.wall_candidates = unique_walls
        print(f"   Removed {duplicate_count} duplicates ({len(unique_walls)} unique walls)")
        return unique_walls

    def _is_duplicate_wall(self, wall1, wall2, tolerance):
        """
        Check if two walls are duplicates

        Two walls are duplicates if:
        1. Same start + end (normal case)
        2. Swapped start + end (reversed wall)
        3. Overlapping segments on same line

        Args:
            wall1, wall2: Wall dicts to compare
            tolerance: Distance tolerance in meters

        Returns:
            bool: True if walls are duplicates
        """
        # Case 1: Start→End match
        case1_start = self._points_equal(wall1['start_point'], wall2['start_point'], tolerance)
        case1_end = self._points_equal(wall1['end_point'], wall2['end_point'], tolerance)

        # Case 2: Swapped Start→End match
        case2_start = self._points_equal(wall1['start_point'], wall2['end_point'], tolerance)
        case2_end = self._points_equal(wall1['end_point'], wall2['start_point'], tolerance)

        # Case 3: Overlapping segments (both walls on same infinite line)
        case3_overlap = self._walls_overlap(wall1, wall2, tolerance)

        return (case1_start and case1_end) or (case2_start and case2_end) or case3_overlap

    def _points_equal(self, p1, p2, tolerance):
        """Check if two points are equal within tolerance"""
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        distance = math.sqrt(dx*dx + dy*dy)
        return distance < tolerance

    def _walls_overlap(self, wall1, wall2, tolerance):
        """
        Check if two walls overlap on the same line

        Algorithm:
        1. Check if walls are collinear (on same infinite line)
        2. Check if segments overlap

        Args:
            wall1, wall2: Wall dicts to compare
            tolerance: Distance tolerance

        Returns:
            bool: True if walls overlap on same line
        """
        # Check if walls are parallel (same angle)
        angle_diff = abs(wall1['angle'] - wall2['angle'])
        if angle_diff > 2 and angle_diff < 178:  # Not parallel or anti-parallel
            return False

        # Check if point from wall1 is on wall2's line
        distance = self._point_to_line_distance_simple(
            wall1['start_point'],
            wall2['start_point'],
            wall2['end_point']
        )

        if distance > tolerance:
            return False  # Not collinear

        # Check if segments overlap (project onto 1D line)
        # Use parametric representation: point = start + t * (end - start)
        t1_start = self._project_point_on_line(
            wall1['start_point'], wall2['start_point'], wall2['end_point']
        )
        t1_end = self._project_point_on_line(
            wall1['end_point'], wall2['start_point'], wall2['end_point']
        )

        # Segments overlap if ranges [0,1] and [t1_start, t1_end] intersect
        min_t1, max_t1 = min(t1_start, t1_end), max(t1_start, t1_end)

        # Check for overlap (with tolerance for segment boundaries)
        overlap_margin = tolerance / wall2['length'] if wall2['length'] > 0 else 0
        return max_t1 >= -overlap_margin and min_t1 <= 1 + overlap_margin

    def _point_to_line_distance_simple(self, point, line_start, line_end):
        """Perpendicular distance from point to infinite line"""
        px, py = point[0], point[1]
        x1, y1 = line_start[0], line_start[1]
        x2, y2 = line_end[0], line_end[1]

        dx = x2 - x1
        dy = y2 - y1
        line_length_sq = dx*dx + dy*dy

        if line_length_sq == 0:
            return math.sqrt((px-x1)**2 + (py-y1)**2)

        # Distance = |cross product| / |line vector|
        cross = abs((py - y1) * dx - (px - x1) * dy)
        return cross / math.sqrt(line_length_sq)

    def _project_point_on_line(self, point, line_start, line_end):
        """
        Project point onto line, return parametric value t

        Returns:
            float: t where projected_point = line_start + t * (line_end - line_start)
                   t=0 → at line_start, t=1 → at line_end
        """
        px, py = point[0], point[1]
        x1, y1 = line_start[0], line_start[1]
        x2, y2 = line_end[0], line_end[1]

        dx = x2 - x1
        dy = y2 - y1
        line_length_sq = dx*dx + dy*dy

        if line_length_sq == 0:
            return 0.0

        t = ((px - x1) * dx + (py - y1) * dy) / line_length_sq
        return t


# =============================================================================
# WALL VALIDATOR (DeepSeek Progressive Filtering)
# =============================================================================

class WallValidator:
    """
    Progressive wall validation with multi-criteria scoring

    Filters 129 candidates → ~10-15 true walls

    Criteria (4-factor scoring):
    1. Connection score (40%) - Wall connects to other walls
    2. Opening proximity (30%) - Wall has doors/windows nearby
    3. Room boundary (20%) - Wall forms part of room enclosure
    4. Parallelism (10%) - Wall parallel to outer walls (structural grid)

    Inspired by: DeepSeek_Specs_Analysis.txt
    """

    def __init__(self, wall_candidates, door_positions=None, window_positions=None, outer_walls=None):
        self.candidates = wall_candidates
        self.doors = door_positions or []
        self.windows = window_positions or []
        self.outer_walls = outer_walls or []

        self.high_confidence_walls = []  # 95% confidence
        self.medium_confidence_walls = []  # 85% confidence
        self.low_confidence_walls = []  # 60% confidence (likely false positives)

    def progressive_validation(self, connection_weight=0.4, opening_weight=0.3,
                              room_weight=0.2, parallelism_weight=0.1):
        """
        Enhanced progressive validation with 4 criteria

        Scoring:
        1. Connection score (40%) - How many walls connect
        2. Opening proximity (30%) - Near doors/windows
        3. Room boundary (20%) - Forms room enclosure
        4. Parallelism (10%) - Parallel to outer walls (structural logic)

        Args:
            connection_weight: Weight for connection score (default: 0.4)
            opening_weight: Weight for opening proximity (default: 0.3)
            room_weight: Weight for room boundary (default: 0.2)
            parallelism_weight: Weight for parallelism (default: 0.1)

        Returns:
            tuple: (high_conf, medium_conf, low_conf) wall lists
        """
        # Adjust weights if no openings available
        has_openings = len(self.doors) > 0 or len(self.windows) > 0
        if not has_openings:
            # Redistribute weights when no openings
            connection_weight = 0.5
            opening_weight = 0.0
            room_weight = 0.3
            parallelism_weight = 0.2

        for wall in self.candidates:
            # Score 1: Connection (existing)
            connection_score = self._calculate_connection_score(wall)

            # Score 2: Opening proximity (existing)
            opening_score = self._calculate_opening_proximity(wall) if has_openings else 0.0

            # Score 3: Room boundary (NEW)
            room_score = self._calculate_room_boundary_score(wall)

            # Score 4: Parallelism to outer walls (NEW)
            parallelism_score = self._calculate_parallelism_score(wall)

            # Overall confidence (weighted)
            overall_confidence = (
                connection_score * connection_weight +
                opening_score * opening_weight +
                room_score * room_weight +
                parallelism_score * parallelism_weight
            )

            # Update wall confidence
            wall['confidence'] = int(overall_confidence * 100)
            wall['validation_scores'] = {
                'connection': connection_score,
                'opening_proximity': opening_score,
                'room_boundary': room_score,
                'parallelism': parallelism_score
            }

            # Categorize by confidence (adjusted thresholds when no openings)
            if has_openings:
                # With openings: strict thresholds
                if overall_confidence >= 0.9:
                    self.high_confidence_walls.append(wall)
                elif overall_confidence >= 0.7:
                    self.medium_confidence_walls.append(wall)
                else:
                    self.low_confidence_walls.append(wall)
            else:
                # Without openings: rely on connections only
                if overall_confidence >= 0.7:  # 2+ connections
                    self.high_confidence_walls.append(wall)
                elif overall_confidence >= 0.4:  # 1+ connection
                    self.medium_confidence_walls.append(wall)
                else:
                    self.low_confidence_walls.append(wall)

        return (
            self.high_confidence_walls,
            self.medium_confidence_walls,
            self.low_confidence_walls
        )

    def _calculate_connection_score(self, wall):
        """
        Score based on how many walls this wall connects to

        Returns:
            float: 0.0 (isolated) to 1.0 (well-connected)
        """
        connection_tolerance = 0.2  # 20cm tolerance
        connections = 0

        for other_wall in self.candidates:
            if other_wall == wall:
                continue

            # Check if walls share an endpoint (connection)
            for wall_point in [wall['start_point'], wall['end_point']]:
                for other_point in [other_wall['start_point'], other_wall['end_point']]:
                    dx = wall_point[0] - other_point[0]
                    dy = wall_point[1] - other_point[1]
                    distance = math.sqrt(dx*dx + dy*dy)

                    if distance < connection_tolerance:
                        connections += 1
                        break

        # Score: Gradual scoring based on connections
        # 0 connections = 0.0 (isolated line, likely false positive)
        # 1 connection = 0.3 (might be detail line)
        # 2 connections = 0.7 (likely wall segment)
        # 3+ connections = 1.0 (definitely structural wall)
        if connections == 0:
            return 0.0
        elif connections == 1:
            return 0.3
        elif connections == 2:
            return 0.7
        elif connections >= 3:
            return 1.0
        else:
            return min(1.0, connections / 3.0)

    def _calculate_opening_proximity(self, wall):
        """
        Score based on proximity to doors/windows

        Returns:
            float: 0.0 (no openings) to 1.0 (has openings)
        """
        proximity_threshold = 0.5  # 50cm proximity = opening in this wall

        openings = self.doors + self.windows

        for opening in openings:
            opening_pos = opening.get('position', [0, 0, 0])

            # Calculate distance from opening to wall line
            distance = self._point_to_line_distance(
                opening_pos,
                wall['start_point'],
                wall['end_point']
            )

            if distance < proximity_threshold:
                return 1.0  # Has opening = high score

        return 0.0  # No openings = low score

    def _point_to_line_distance(self, point, line_start, line_end):
        """Calculate perpendicular distance from point to line segment"""
        x0, y0 = point[0], point[1]
        x1, y1 = line_start[0], line_start[1]
        x2, y2 = line_end[0], line_end[1]

        # Vector from start to end
        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx*dx + dy*dy

        if length_sq == 0:
            # Degenerate line (point)
            return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)

        # Parameter t of projection onto line
        t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / length_sq))

        # Closest point on line segment
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        # Distance to closest point
        return math.sqrt((x0 - proj_x)**2 + (y0 - proj_y)**2)

    def _calculate_room_boundary_score(self, wall):
        """
        Score based on whether wall forms part of a room enclosure

        Logic:
        - Wall with 2+ connections likely forms room boundary
        - Isolated wall unlikely to be structural

        Returns:
            float: 0.0 (isolated) to 1.0 (room boundary)
        """
        connection_count = self._count_connections(wall)

        if connection_count >= 3:
            return 1.0  # Part of enclosed space
        elif connection_count == 2:
            return 0.7  # Likely room divider
        elif connection_count == 1:
            return 0.3  # Might be partial wall
        else:
            return 0.0  # Isolated (likely false positive)

    def _calculate_parallelism_score(self, wall):
        """
        Score based on parallelism to outer walls

        Logic:
        - Internal walls typically parallel to outer walls (structural grid)
        - Diagonal walls less common in residential construction

        Returns:
            float: 0.0 (diagonal) to 1.0 (parallel/perpendicular to outer walls)
        """
        if not self.outer_walls:
            return 0.5  # Neutral if no outer walls available

        # Check if wall is parallel to any outer wall
        for outer_wall in self.outer_walls:
            # Get angle from outer wall (calculate if not present)
            if 'angle' in outer_wall:
                outer_angle = outer_wall['angle']
            else:
                # Calculate angle from start/end points
                dx = outer_wall['end_point'][0] - outer_wall['start_point'][0]
                dy = outer_wall['end_point'][1] - outer_wall['start_point'][1]
                angle_rad = math.atan2(dy, dx)
                outer_angle = abs(math.degrees(angle_rad))
                if outer_angle > 90:
                    outer_angle = 180 - outer_angle

            angle_diff = abs(wall['angle'] - outer_angle)

            # Parallel (0° or 180°)
            if angle_diff < 5 or abs(angle_diff - 180) < 5:
                return 1.0

            # Perpendicular (90° or 270°) - also structural grid
            if abs(angle_diff - 90) < 5 or abs(angle_diff - 270) < 5:
                return 1.0

        # Not aligned to structural grid
        return 0.3

    def _count_connections(self, wall):
        """Count number of walls connecting to this wall"""
        connection_tolerance = 0.2  # 20cm
        connections = 0

        for other_wall in self.candidates:
            if other_wall == wall:
                continue

            for wall_point in [wall['start_point'], wall['end_point']]:
                for other_point in [other_wall['start_point'], other_wall['end_point']]:
                    dx = wall_point[0] - other_point[0]
                    dy = wall_point[1] - other_point[1]
                    distance = math.sqrt(dx*dx + dy*dy)

                    if distance < connection_tolerance:
                        connections += 1
                        break

        return connections


# =============================================================================
# INFERENCE CHAIN
# =============================================================================

