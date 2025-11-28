#!/usr/bin/env python3
"""
Extraction Engine - Class-Based Architecture for 2D to Blender BIM

Orchestrator for PDF extraction pipeline.
Imports modular components from separate files.
"""

import math
import re
from datetime import datetime

# Import modular components
from src.core.calibration import CalibrationEngine
from src.core.geometry_validator import GeometryValidator


# =============================================================================
# WALL DETECTOR
# =============================================================================

# NOTE: CalibrationEngine and GeometryValidator moved to separate modules
# Keeping wall detection classes here temporarily (to be refactored next)

# =============================================================================
# GEOMETRY VALIDATOR
# =============================================================================

# =============================================================================
# WALL DETECTOR
# =============================================================================

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

class InferenceChain:
    """
    Inference chain for traceability and debugging

    Records every inference step with sources and confidence
    """

    def __init__(self):
        self.chain = []

    def add_inference(self, step, phase, source, input_data, inference, confidence, validated_by=None):
        """
        Add inference step to chain

        Args:
            step: Step name (e.g., 'door_dimension_analysis')
            phase: Phase identifier (e.g., '1D', '2')
            source: Data source (e.g., 'door_schedule', 'elevation_view')
            input_data: Input data dict
            inference: Inference description (string)
            confidence: Confidence score (0.0-1.0)
            validated_by: List of validation sources
        """
        self.chain.append({
            'step': step,
            'phase': phase,
            'source': source,
            'input': input_data,
            'inference': inference,
            'confidence': confidence,
            'validated_by': validated_by or [],
            'timestamp': datetime.now().isoformat()
        })

    def get_chain(self):
        """Get complete inference chain"""
        return self.chain

    def get_by_phase(self, phase):
        """Get inferences for specific phase"""
        return [inf for inf in self.chain if inf['phase'] == phase]

    def get_by_confidence(self, min_confidence):
        """Get inferences above confidence threshold"""
        return [inf for inf in self.chain if inf['confidence'] >= min_confidence]

    def to_markdown(self):
        """Export inference chain as markdown"""
        md = "# Inference Chain\n\n"

        by_phase = {}
        for inf in self.chain:
            phase = inf['phase']
            if phase not in by_phase:
                by_phase[phase] = []
            by_phase[phase].append(inf)

        for phase in sorted(by_phase.keys()):
            md += f"## Phase {phase}\n\n"
            for inf in by_phase[phase]:
                md += f"### {inf['step']}\n"
                md += f"- **Source:** {inf['source']}\n"
                md += f"- **Inference:** {inf['inference']}\n"
                md += f"- **Confidence:** {inf['confidence']*100:.0f}%\n"
                if inf['validated_by']:
                    md += f"- **Validated by:** {', '.join(inf['validated_by'])}\n"
                md += "\n"

        return md


# =============================================================================
# SCHEDULE EXTRACTOR
# =============================================================================

class ScheduleExtractor:
    """
    Extract door/window schedules from PDF tables

    Accuracy: 95% (table extraction)
    """

    def __init__(self, pdf):
        self.pdf = pdf

    def extract_door_schedule(self, page_number=7):
        """Extract door schedule from Page 8 (0-indexed: 7) with error handling"""
        # ERROR HANDLING: Check if page exists
        try:
            page = self.pdf.pages[page_number]
            tables = page.extract_tables()
        except IndexError:
            print(f"⚠️  Page {page_number} not found, using default door schedule")
            return self._default_door_schedule()

        # ERROR HANDLING: Check if tables exist
        if not tables or len(tables) == 0:
            print(f"⚠️  No tables found on page {page_number}, using default door schedule")
            return self._default_door_schedule()

        door_schedule = {}

        for table in tables:
            if not table or len(table) < 3:
                continue

            # Look for header row with 'REFERENCES' and door refs
            for i, row in enumerate(table):
                if row and row[0] == 'REFERENCES':
                    door_refs = [cell for cell in row[1:] if cell and cell.startswith('D')]

                    # Find SIZE row
                    size_row = None
                    for j in range(i+1, min(i+5, len(table))):
                        if table[j] and table[j][0] == 'SIZE':
                            size_row = table[j]
                            break

                    if size_row:
                        for col_idx, ref in enumerate(door_refs):
                            cell_idx = col_idx + 1
                            if cell_idx < len(size_row):
                                size_text = size_row[cell_idx]
                                import re
                                size_match = re.search(r'(\d+)\s*MM\s*X\s*(\d+)\s*MM', size_text, re.IGNORECASE)
                                if size_match:
                                    width, height = size_match.groups()
                                    door_schedule[ref] = {
                                        'width': int(width) / 1000,
                                        'height': int(height) / 1000,
                                        'quantity': 1
                                    }
                    break

        return door_schedule

    def extract_window_schedule(self, page_number=7):
        """Extract window schedule from Page 8 (0-indexed: 7) with error handling"""
        # ERROR HANDLING: Check if page exists
        try:
            page = self.pdf.pages[page_number]
            tables = page.extract_tables()
        except IndexError:
            print(f"⚠️  Page {page_number} not found, using default window schedule")
            return self._default_window_schedule()

        # ERROR HANDLING: Check if tables exist
        if not tables or len(tables) == 0:
            print(f"⚠️  No tables found on page {page_number}, using default window schedule")
            return self._default_window_schedule()

        window_schedule = {}

        for table in tables:
            if not table or len(table) < 3:
                continue

            for i, row in enumerate(table):
                if row and row[0] == 'REFERENCES':
                    window_refs = [cell for cell in row[1:] if cell and cell.startswith('W')]

                    if not window_refs:
                        continue

                    size_row = None
                    units_row = None
                    for j in range(i+1, min(i+6, len(table))):
                        if table[j] and table[j][0] == 'SIZE':
                            size_row = table[j]
                        if table[j] and table[j][0] == 'UNITS':
                            units_row = table[j]

                    if size_row:
                        for col_idx, ref in enumerate(window_refs):
                            cell_idx = col_idx + 1
                            if cell_idx < len(size_row):
                                size_text = size_row[cell_idx]
                                import re
                                size_match = re.search(r'(\d+)\s*mm\s*X\s*(\d+)\s*mm', size_text, re.IGNORECASE)
                                if size_match:
                                    width, height = size_match.groups()
                                    qty = 1
                                    if units_row and cell_idx < len(units_row):
                                        qty_match = re.search(r'(\d+)\s*NOS', units_row[cell_idx])
                                        if qty_match:
                                            qty = int(qty_match.group(1))

                                    window_schedule[ref] = {
                                        'width': int(width) / 1000,
                                        'height': int(height) / 1000,
                                        'quantity': qty
                                    }
                    break

        return window_schedule

    def _default_door_schedule(self):
        """Default Malaysian house door dimensions (UBBL standards)"""
        return {
            'D1': {'width': 0.9, 'height': 2.1, 'quantity': 1},   # Main entrance/bedroom
            'D2': {'width': 0.9, 'height': 2.1, 'quantity': 1},   # Standard doors
            'D3': {'width': 0.75, 'height': 2.1, 'quantity': 1}   # Bathroom/utility
        }

    def _default_window_schedule(self):
        """Default Malaysian house window dimensions"""
        return {
            'W1': {'width': 1.8, 'height': 1.0, 'quantity': 1},   # Large living room windows
            'W2': {'width': 1.2, 'height': 1.0, 'quantity': 4},   # Standard bedroom windows
            'W3': {'width': 0.6, 'height': 0.5, 'quantity': 2}    # Small bathroom/kitchen windows
        }


# =============================================================================
# OPENING DETECTOR (Door/Window Positions)
# =============================================================================

class OpeningDetector:
    """
    Detect door/window positions from floor plan labels

    Accuracy: 90% (label matching)
    """

    def __init__(self, calibration_engine, door_schedule, window_schedule, outer_walls):
        self.calibration = calibration_engine
        self.door_schedule = door_schedule
        self.window_schedule = window_schedule
        self.outer_walls = outer_walls

    def extract_door_positions(self, page):
        """Extract door positions from D1, D2, D3 labels on floor plan with validation"""
        words = page.extract_words()
        door_positions = []

        for word in words:
            text = word['text'].strip().upper()
            if text in self.door_schedule.keys():
                # Get calibrated position
                x, y = self.calibration.transform_to_building(word['x0'], word['top'])

                # VALIDATION: Check if position is within building bounds
                if not self._is_valid_position(x, y):
                    print(f"⚠️  {text} position ({x:.2f}, {y:.2f}) outside building bounds, skipping")
                    continue

                # Get door dimensions
                door_data = self.door_schedule[text]

                door_positions.append({
                    'door_type': text,
                    'position': [x, y, 0.0],
                    'width': door_data['width'],
                    'height': door_data['height'],
                    'confidence': 90
                })

        return door_positions

    def _is_valid_position(self, x, y):
        """Validate position is within building bounds with margin"""
        margin = 1.0  # 1m margin for tolerance
        return (
            -margin <= x <= self.calibration.building_width + margin and
            -margin <= y <= self.calibration.building_length + margin
        )

    def extract_window_positions(self, page):
        """Extract window positions from W1, W2, W3 labels on floor plan with validation"""
        words = page.extract_words()
        window_positions = []

        for word in words:
            text = word['text'].strip().upper()
            if text in self.window_schedule.keys():
                # Get calibrated position
                x, y = self.calibration.transform_to_building(word['x0'], word['top'])

                # VALIDATION: Check if position is within building bounds
                if not self._is_valid_position(x, y):
                    print(f"⚠️  {text} position ({x:.2f}, {y:.2f}) outside building bounds, skipping")
                    continue

                # Get window dimensions
                window_data = self.window_schedule[text]

                # Default sill height (will be refined with elevation data later)
                sill_height = 1.0 if window_data['width'] >= 1.0 else 1.5

                window_positions.append({
                    'window_type': text,
                    'position': [x, y, sill_height],
                    'width': window_data['width'],
                    'height': window_data['height'],
                    'confidence': 85
                })

        return window_positions


# =============================================================================
# ROOM BOUNDARY DETECTOR
# =============================================================================

class RoomBoundaryDetector:
    """
    Detect room boundaries from wall network

    Simplified approach: Filter walls that form enclosures
    """

    def __init__(self, walls):
        self.walls = walls
        self.rooms = []

    def detect_rooms_simple(self):
        """
        Simplified room detection: Look for rectangular enclosures

        Returns walls that likely form room boundaries
        """
        # Build wall graph
        wall_endpoints = set()
        for wall in self.walls:
            start = (round(wall['start_point'][0], 1), round(wall['start_point'][1], 1))
            end = (round(wall['end_point'][0], 1), round(wall['end_point'][1], 1))
            wall_endpoints.add(start)
            wall_endpoints.add(end)

        # Find walls that connect to multiple walls (likely structural)
        room_walls = []
        for wall in self.walls:
            start = (round(wall['start_point'][0], 1), round(wall['start_point'][1], 1))
            end = (round(wall['end_point'][0], 1), round(wall['end_point'][1], 1))

            # Count how many other walls share endpoints
            start_connections = sum(1 for w in self.walls if w != wall and (
                self._point_matches(w['start_point'], wall['start_point']) or
                self._point_matches(w['end_point'], wall['start_point'])
            ))

            end_connections = sum(1 for w in self.walls if w != wall and (
                self._point_matches(w['start_point'], wall['end_point']) or
                self._point_matches(w['end_point'], wall['end_point'])
            ))

            # Wall is structural if both ends connect to other walls
            if start_connections >= 1 and end_connections >= 1:
                room_walls.append(wall)

        return room_walls

    def _point_matches(self, point1, point2, tolerance=0.2):
        """Check if two points match within tolerance"""
        dx = abs(point1[0] - point2[0])
        dy = abs(point1[1] - point2[1])
        return dx < tolerance and dy < tolerance


# =============================================================================
# ELEVATION EXTRACTOR (Phase 1D)
# =============================================================================

class ElevationExtractor:
    """
    Extract elevation data from elevation views using regex patterns

    Pages:
    - Page 3 (Front/Rear Elevation)
    - Page 4 (Left/Right Elevation)

    Extracts:
    - Floor levels (FFL)
    - Lintel levels (door/window tops)
    - Ceiling heights
    - Window sill heights
    """

    def __init__(self, pdf):
        self.pdf = pdf

        # Regex patterns for dimension extraction (TEMPLATE-DRIVEN)
        self.PATTERNS = {
            # Floor level: "FFL +0.150" or "FLOOR LEVEL +150mm"
            'floor_level': [
                (r'FFL\s*\+?\s*(\d+\.?\d*)\s*m(?!m)', 1.0),  # "FFL +0.150m" (meters)
                (r'FFL\s*\+?\s*(\d+)\s*mm', 0.001),           # "FFL +150mm" (convert to m)
                (r'FLOOR\s+LEVEL\s*\+?\s*(\d+\.?\d*)\s*m(?!m)', 1.0),
                (r'FINISHED\s+FLOOR\s+LEVEL\s*\+?\s*(\d+\.?\d*)', 1.0)
            ],

            # Lintel level: "LINTEL LEVEL 2100mm" or "LINTEL +2.1m"
            'lintel_level': [
                (r'LINTEL.*?(\d+\.?\d*)\s*m(?!m)', 1.0),      # "LINTEL +2.1m"
                (r'LINTEL.*?(\d+)\s*mm', 0.001),               # "LINTEL 2100mm"
                (r'LINTEL\s+LEVEL.*?(\d+\.?\d*)', 1.0),
                (r'DOOR\s+HEAD.*?(\d+\.?\d*)', 1.0)
            ],

            # Ceiling level: "CEILING LEVEL 3000mm"
            'ceiling_level': [
                (r'CEILING.*?(\d+\.?\d*)\s*m(?!m)', 1.0),
                (r'CEILING.*?(\d+)\s*mm', 0.001),
                (r'SOFFIT.*?(\d+\.?\d*)', 1.0),
                (r'ROOF\s+LEVEL.*?(\d+\.?\d*)', 1.0)
            ],

            # Window sill: "SILL 1000mm" or "W/S +1.0m"
            'window_sill': [
                (r'SILL.*?(\d+\.?\d*)\s*m(?!m)', 1.0),
                (r'SILL.*?(\d+)\s*mm', 0.001),
                (r'W/?S.*?(\d+\.?\d*)\s*m(?!m)', 1.0),
                (r'WINDOW\s+SILL.*?(\d+\.?\d*)', 1.0)
            ]
        }

    def extract_from_page(self, page_number=2):
        """
        Extract elevation data from elevation view page

        Args:
            page_number: 0-indexed (2 = Page 3, 3 = Page 4)

        Returns:
            dict: {floor_level, lintel_level, ceiling_level, window_sill}
        """
        try:
            page = self.pdf.pages[page_number]
        except IndexError:
            print(f"⚠️  Page {page_number} not found, using defaults")
            return self._default_elevations()

        words = page.extract_words()
        if not words:
            print(f"⚠️  No text on page {page_number}, using defaults")
            return self._default_elevations()

        # Concatenate all text for pattern matching
        full_text = ' '.join([w['text'] for w in words])

        elevations = {}

        for label, patterns in self.PATTERNS.items():
            value = self._extract_dimension(full_text, patterns)
            if value is not None:
                elevations[label] = value

        # Fill in missing values with defaults
        return self._fill_defaults(elevations)

    def _extract_dimension(self, text, patterns):
        """
        Extract dimension value from text using regex patterns

        Args:
            text: Full text content
            patterns: List of (regex, multiplier) tuples

        Returns:
            float: Dimension in meters, or None if not found
        """
        for pattern, multiplier in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1)
                value = float(value_str) * multiplier
                return value

        return None

    def _default_elevations(self):
        """Default elevation values for Malaysian houses (UBBL standards)"""
        return {
            'floor_level': 0.15,     # FFL +150mm (typical raised floor)
            'lintel_level': 2.1,     # 2100mm (standard door height)
            'ceiling_level': 3.0,    # 3000mm (typical residential ceiling)
            'window_sill': 1.0       # 1000mm (typical window sill height)
        }

    def _fill_defaults(self, elevations):
        """Fill missing elevation values with defaults"""
        defaults = self._default_elevations()

        for key, default_value in defaults.items():
            if key not in elevations:
                elevations[key] = default_value
                print(f"   ℹ️  {key} not found, using default: {default_value}m")

        return elevations

    def extract_complete(self):
        """
        Extract elevation data from all elevation pages

        Returns:
            dict: {elevations: {...}, confidence: {...}}
        """
        # Try Page 3 (Front/Rear Elevation)
        page3_data = self.extract_from_page(2)

        # Try Page 4 (Left/Right Elevation) for validation
        page4_data = self.extract_from_page(3)

        # Merge data (Page 3 takes precedence)
        combined = {}
        confidence_scores = {}

        for key in page3_data.keys():
            val3 = page3_data.get(key)
            val4 = page4_data.get(key)

            if val3 is not None and val4 is not None:
                # Both pages have value - check if they match
                if abs(val3 - val4) < 0.05:  # 50mm tolerance
                    combined[key] = val3
                    confidence_scores[key] = 95  # High confidence (validated)
                else:
                    combined[key] = val3  # Use Page 3
                    confidence_scores[key] = 75  # Medium confidence (mismatch)
                    print(f"   ⚠️  {key} mismatch: Page3={val3}m, Page4={val4}m (using Page3)")
            elif val3 is not None:
                combined[key] = val3
                confidence_scores[key] = 85  # Medium-high (single source)
            else:
                combined[key] = val4 or self._default_elevations()[key]
                confidence_scores[key] = 60  # Low (default used)

        return {
            'elevations': combined,
            'confidence': confidence_scores
        }


# =============================================================================
# ROOM LABEL EXTRACTOR (Phase 1D)
# =============================================================================

class RoomLabelExtractor:
    """
    Extract room labels from floor plan (Malay text)

    Pattern matching for Malaysian house room labels
    """

    def __init__(self, calibration_engine):
        self.calibration = calibration_engine

        # Malay room label patterns (TEMPLATE-DRIVEN)
        self.ROOM_PATTERNS = {
            # Bedrooms
            r'BILIK\s*TIDUR\s*(\d+)': lambda m: f'bedroom_{m.group(1)}',
            r'B\.?\s*TIDUR\s*(\d+)': lambda m: f'bedroom_{m.group(1)}',
            r'BILIK\s*TIDUR\s*UTAMA': 'master_bedroom',
            r'B\.?\s*T\.?\s*UTAMA': 'master_bedroom',

            # Bathrooms
            r'BILIK\s*AIR\s*(\d+)': lambda m: f'bathroom_{m.group(1)}',
            r'B\.?\s*AIR\s*(\d+)': lambda m: f'bathroom_{m.group(1)}',
            r'TANDAS\s*(\d+)?': lambda m: f'toilet_{m.group(1)}' if m.group(1) else 'toilet',
            r'W\.?C\.?': 'toilet',

            # Kitchen
            r'DAPUR': 'kitchen',
            r'KITCHEN': 'kitchen',

            # Living areas
            r'RUANG\s*TAMU': 'living_room',
            r'R\.?\s*TAMU': 'living_room',
            r'RUANG\s*MAKAN': 'dining_room',
            r'R\.?\s*MAKAN': 'dining_room',
            r'LIVING': 'living_room',
            r'DINING': 'dining_room',

            # Utility areas
            r'STOR': 'storage',
            r'STORE': 'storage',
            r'CUCIAN': 'laundry',
            r'LAUNDRY': 'laundry',
            r'UTILITY': 'utility_room',

            # Other
            r'KORIDOR': 'corridor',
            r'CORRIDOR': 'corridor',
            r'BALKONI': 'balcony',
            r'BALCONY': 'balcony',
            r'BERANDA': 'porch',
            r'PORCH': 'porch'
        }

    def extract_room_labels(self, page):
        """
        Extract room labels from floor plan page

        Args:
            page: pdfplumber page object

        Returns:
            list: Room data with positions and classifications
        """
        words = page.extract_words()
        rooms = []

        for word in words:
            text = word['text'].upper().strip()

            # Skip empty or very short text
            if len(text) < 2:
                continue

            # Try each pattern
            for pattern, room_type in self.ROOM_PATTERNS.items():
                match = re.search(pattern, text)
                if match:
                    # Get room type (might be function result)
                    if callable(room_type):
                        type_name = room_type(match)
                    else:
                        type_name = room_type

                    # Convert PDF coordinates to building coordinates
                    pdf_x, pdf_y = word['x0'], word['top']
                    building_x, building_y = self.calibration.transform_to_building(pdf_x, pdf_y)

                    rooms.append({
                        'name': word['text'],  # Original text (Malay)
                        'type': type_name,     # Standardized type (English)
                        'position': [building_x, building_y, 0.0],
                        'pdf_bbox': {
                            'x0': word['x0'], 'top': word['top'],
                            'x1': word['x1'], 'bottom': word['bottom']
                        },
                        'confidence': 90
                    })
                    break  # Found match, stop searching patterns

        return rooms


# =============================================================================
# WINDOW SILL HEIGHT INFERENCE (Phase 1D)
# =============================================================================

def infer_window_sill_heights(windows, elevations, window_schedule):
    """
    Infer window sill heights based on window types and elevations

    Logic:
    - W1 (large windows): Sill at 1.0m (living room, bedroom)
    - W2 (standard windows): Sill at 1.0m (bedrooms)
    - W3 (small windows): Sill at 1.5m (bathrooms, ventilation)

    Args:
        windows: List of window positions
        elevations: Elevation data with window_sill height
        window_schedule: Window dimensions by type

    Returns:
        list: Windows with sill_height and lintel_height added
    """
    default_sill = elevations.get('window_sill', 1.0)

    for window in windows:
        window_type = window['window_type']
        width = window_schedule[window_type]['width']
        height = window_schedule[window_type]['height']

        # Inference rules based on window size
        if width >= 1.8:
            # Large windows (W1) - living room, low sill for view
            sill_height = min(default_sill, 1.0)
        elif width >= 1.2:
            # Standard windows (W2) - bedrooms, standard sill
            sill_height = default_sill
        elif width >= 0.6:
            # Small windows (W3) - bathrooms, high sill for privacy
            sill_height = max(default_sill, 1.5)
        else:
            # Very small - ventilation only
            sill_height = 2.0

        window['sill_height'] = sill_height
        window['lintel_height'] = sill_height + height

        # Update Z position to sill height
        window['position'][2] = sill_height

    return windows


# =============================================================================
# MAIN ORCHESTRATOR - TWO-TIER EXTRACTION PIPELINE
# =============================================================================

def complete_pdf_extraction(pdf_path, building_width=9.8, building_length=8.0, building_height=3.0):
    """
    Complete PDF → OUTPUT.json extraction pipeline (Two-Tier Architecture)

    NEW APPROACH (corrected):
    1. Load master_reference_template.json (TIER 1 - high-level instructions)
    2. For each item in extraction_sequence:
       - Lookup detection_id in vector_patterns.py (TIER 2 - low-level execution)
       - Execute pattern matching
       - If found → add to objects array with "placed": false
       - If not found → skip
    3. Generate output JSON: metadata + summary (hash total) + objects

    Args:
        pdf_path: Path to PDF file
        building_width: Building width in meters
        building_length: Building length in meters
        building_height: Building height in meters

    Returns:
        dict: Output JSON with metadata + summary + objects (placed: false)
    """
    import pdfplumber
    import json
    from datetime import datetime
    import os

    print(f"🔧 Starting TWO-TIER extraction from: {pdf_path}")
    print("=" * 80)

    # STEP 1: Load Master Reference Template (TIER 1)
    print("\n📖 STEP 1: Loading Master Reference Template...")
    master_template_path = os.path.join(os.path.dirname(__file__), "master_reference_template.json")

    try:
        with open(master_template_path, 'r') as f:
            master_template = json.load(f)
            extraction_sequence = master_template['extraction_sequence']
            print(f"  ✅ Loaded {len(extraction_sequence)} items from master template")
    except FileNotFoundError:
        print(f"  ❌ ERROR: master_reference_template.json not found at {master_template_path}")
        return None

    # STEP 2: Initialize extraction components
    print("\n🔧 STEP 2: Initializing extraction components...")

    with pdfplumber.open(pdf_path) as pdf:
        # Initialize calibration engine (needed for all coordinate transforms)
        calibration_engine = CalibrationEngine(pdf, building_width, building_length)

        # Initialize vector pattern executor (TIER 2)
        from vector_patterns import VectorPatternExecutor
        vector_executor = VectorPatternExecutor(pdf, calibration_engine)

        print("  ✅ Calibration engine initialized")
        print("  ✅ Vector pattern executor initialized")

        # STEP 3: Sequential extraction following master template
        print("\n🔍 STEP 3: Sequential extraction (following master template order)...")

        objects = []  # Will be populated with found objects
        calibration_data = None  # Will be set after calibration
        extraction_context = {}  # Shared context between extraction phases

        # Pre-extract walls for orientation calculation
        print("\n  🧱 Pre-extracting walls for orientation calculation...")
        dimensions = {"length": building_width, "breadth": building_length, "height": building_height}
        wall_detector = WallDetector(calibration_engine, dimensions)

        # Extract walls from first page after calibration is available
        # Note: This will run after calibration is done in the sequence

        # Track expected vs actual objects for debugging
        expected_lod300_objects = []
        found_lod300_objects = []
        failed_lod300_objects = []

        # Iterate through extraction sequence
        for idx, item in enumerate(extraction_sequence, 1):
            phase = item.get('_phase', 'unknown')
            item_name = item['item']
            detection_id = item['detection_id']
            search_text = item.get('search_text', [])
            pages = item.get('pages', [0])
            object_type = item.get('object_type')

            # Track expected LOD300 objects
            if object_type and 'lod300' in object_type.lower():
                expected_lod300_objects.append({
                    'item': item_name,
                    'object_type': object_type,
                    'detection_id': detection_id,
                    'search_text': search_text
                })

            print(f"\n  [{idx}/{len(extraction_sequence)}] {phase}: {item_name}")
            print(f"    Detection ID: {detection_id}")
            if object_type:
                print(f"    Object Type: {object_type}")
            if search_text:
                print(f"    Search Text: {search_text}")

            try:
                # Execute pattern matching via VectorPatternExecutor
                result = vector_executor.execute(
                    detection_id=detection_id,
                    search_text=search_text,
                    pages=pages,
                    object_type=object_type,
                    context=extraction_context
                )

                # Handle result based on detection type
                if result:
                    if detection_id == "CALIBRATION_DRAIN_PERIMETER":
                        # Store calibration data
                        calibration_data = result
                        extraction_context['calibration'] = calibration_data
                        print(f"    ✅ Calibration: scale_x={calibration_data['scale_x']:.6f}, scale_y={calibration_data['scale_y']:.6f}")

                        # Extract walls immediately after calibration for orientation calculation
                        print(f"\n  🧱 Extracting walls (needed for orientation)...")
                        try:
                            internal_walls = wall_detector.extract_from_vectors(pdf.pages[0])
                            # Generate outer walls from building dimensions
                            outer_walls = [
                                {"start_point": [0, 0, 0], "end_point": [building_width, 0, 0]},  # North
                                {"start_point": [0, building_length, 0], "end_point": [building_width, building_length, 0]},  # South
                                {"start_point": [0, 0, 0], "end_point": [0, building_length, 0]},  # East
                                {"start_point": [building_width, 0, 0], "end_point": [building_width, building_length, 0]}   # West
                            ]
                            all_walls = outer_walls + internal_walls
                            extraction_context['walls'] = all_walls
                            print(f"    ✅ Walls extracted: {len(outer_walls)} exterior + {len(internal_walls)} interior = {len(all_walls)} total")
                        except Exception as e:
                            print(f"    ⚠️  Wall extraction failed: {str(e)}")
                            extraction_context['walls'] = []

                        # Calibration succeeded - now generate drain objects via GridTruth
                        # (calibration is just coord transform metadata, we need actual drain objects)
                        if object_type and item.get('mandatory', False):
                            print(f"    📍 Generating discharge drain objects from GridTruth...")
                            try:
                                from gridtruth_generator import generate_item as gridtruth_generate
                                pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
                                grid_truth_path = os.path.join(pdf_dir, 'GridTruth.json')

                                drain_objects = gridtruth_generate(item, grid_truth_path, extraction_context)
                                if drain_objects:
                                    for obj in drain_objects:
                                        obj['_phase'] = phase
                                        obj['placed'] = False
                                        objects.append(obj)
                                    print(f"    ✅ Generated {len(drain_objects)} discharge drains from GridTruth")
                            except Exception as e:
                                print(f"    ⚠️  Drain generation failed: {str(e)}")

                    elif detection_id == "ELEVATION_TEXT_REGEX":
                        # Store elevation data
                        if 'elevations' not in extraction_context:
                            extraction_context['elevations'] = {}
                        elevation_key = item_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
                        extraction_context['elevations'][elevation_key] = result
                        print(f"    ✅ {item_name}: {result}m")

                    elif detection_id == "SCHEDULE_TABLE_EXTRACTION":
                        # Store schedule data
                        if 'door' in item_name.lower():
                            extraction_context['door_schedule'] = result
                            print(f"    ✅ Found {len(result)} door types")
                        elif 'window' in item_name.lower():
                            extraction_context['window_schedule'] = result
                            print(f"    ✅ Found {len(result)} window types")

                    elif object_type:
                        # Add to objects array with "placed": false
                        if isinstance(result, list):
                            for obj in result:
                                obj['_phase'] = phase
                                obj['placed'] = False
                                objects.append(obj)

                                # Track LOD300 objects
                                if 'lod300' in object_type.lower():
                                    found_lod300_objects.append({
                                        'item': item_name,
                                        'object_type': object_type,
                                        'name': obj.get('name'),
                                        'position': obj.get('position'),
                                        'orientation': obj.get('orientation')
                                    })

                            print(f"    ✅ Found {len(result)} instances")
                        else:
                            result['_phase'] = phase
                            result['placed'] = False
                            objects.append(result)

                            # Track LOD300 objects
                            if 'lod300' in object_type.lower():
                                found_lod300_objects.append({
                                    'item': item_name,
                                    'object_type': object_type,
                                    'name': result.get('name'),
                                    'position': result.get('position'),
                                    'orientation': result.get('orientation')
                                })

                            print(f"    ✅ Found 1 instance")
                    else:
                        # Result found but no object_type (metadata only, e.g., door labels)
                        # Check if mandatory - may need GridTruth generation
                        is_mandatory = item.get('mandatory', False)

                        if is_mandatory:
                            print(f"    ✅ Extracted successfully (metadata only)")
                            print(f"    ⚠️  No objects created (object_type=null) - trying GridTruth fallback (MANDATORY)")

                            try:
                                from gridtruth_generator import generate_item as gridtruth_generate
                                pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
                                grid_truth_path = os.path.join(pdf_dir, 'GridTruth.json')

                                generated_objects = gridtruth_generate(item, grid_truth_path, extraction_context)

                                if generated_objects:
                                    for obj in generated_objects:
                                        obj['_phase'] = phase
                                        obj['placed'] = False
                                        objects.append(obj)
                                    print(f"    ✅ GridTruth fallback SUCCESS: {len(generated_objects)} items generated")
                                else:
                                    print(f"    ⚠️  GridTruth fallback returned no objects")
                            except Exception as e:
                                print(f"    ⚠️  GridTruth fallback failed: {str(e)}")
                        else:
                            print(f"    ✅ Extracted successfully (metadata only)")
                else:
                    # TEMPLATE CONTRACT ENFORCEMENT
                    # Check if this is a mandatory item
                    is_mandatory = item.get('mandatory', False)

                    if is_mandatory:
                        # Mandatory item failed PDF extraction - try GridTruth fallback
                        print(f"    ⚠️  PDF extraction failed - trying GridTruth fallback (MANDATORY)")

                        try:
                            from gridtruth_generator import generate_item as gridtruth_generate

                            # Determine GridTruth path from PDF location
                            pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
                            grid_truth_path = os.path.join(pdf_dir, 'GridTruth.json')

                            # Try to generate from GridTruth (pass context for door_schedule, etc.)
                            generated_objects = gridtruth_generate(item, grid_truth_path, extraction_context)

                            if generated_objects:
                                # Success! Add to output
                                objects.extend(generated_objects)
                                print(f"    ✅ GridTruth fallback SUCCESS: {len(generated_objects)} items generated")
                            else:
                                # Both PDF and GridTruth failed for mandatory item
                                error_msg = (
                                    f"\n{'='*80}\n"
                                    f"❌ PIPELINE FAILURE: MANDATORY ITEM NOT FULFILLED\n"
                                    f"{'='*80}\n"
                                    f"Template item: {item_name}\n"
                                    f"Object type: {object_type}\n"
                                    f"Phase: {item.get('_phase', 'unknown')}\n"
                                    f"\n"
                                    f"  • PDF extraction: FAILED (not found)\n"
                                    f"  • GridTruth fallback: FAILED (cannot generate)\n"
                                    f"\n"
                                    f"Action required:\n"
                                    f"  1. Verify GridTruth.json exists at: {grid_truth_path}\n"
                                    f"  2. Verify GridTruth has required sections (room_bounds, building_envelope)\n"
                                    f"  3. Verify template item is correctly marked as mandatory\n"
                                    f"{'='*80}\n"
                                )
                                raise RuntimeError(error_msg)
                        except ImportError:
                            raise RuntimeError("gridtruth_generator module not found - cannot fallback")
                        except Exception as e:
                            raise RuntimeError(f"GridTruth fallback failed: {str(e)}")
                    else:
                        # Optional item - just log and skip
                        if object_type and 'lod300' in object_type.lower():
                            failed_lod300_objects.append({
                                'item': item_name,
                                'object_type': object_type,
                                'detection_id': detection_id,
                                'search_text': search_text,
                                'reason': 'Not found in PDF (optional)'
                            })
                            print(f"    ⚠️  Optional item not found - skipping")
                        else:
                            print(f"    ⚠️  Not found - skipping")

            except Exception as e:
                # Track LOD300 failures
                if object_type and 'lod300' in object_type.lower():
                    failed_lod300_objects.append({
                        'item': item_name,
                        'object_type': object_type,
                        'detection_id': detection_id,
                        'error': str(e)
                    })
                    print(f"    ❌ EXTRACTION FAILED - LOD300 object error: {str(e)}")
                else:
                    print(f"    ❌ Error: {str(e)}")
                continue

        # STEP 3.5: LOD300 OBJECTS DEBUG SUMMARY
        print("\n" + "=" * 80)
        print("🔍 LOD300 OBJECTS DEBUG SUMMARY (Master Template = Reference of Truth)")
        print("=" * 80)
        print(f"\nExpected LOD300 objects from master template: {len(expected_lod300_objects)}")
        print(f"Found: {len(found_lod300_objects)}")
        print(f"Failed/Missing: {len(failed_lod300_objects)}")

        if found_lod300_objects:
            print(f"\n✅ FOUND LOD300 OBJECTS ({len(found_lod300_objects)}):")
            for obj in found_lod300_objects:
                pos = obj.get('position', [0,0,0])
                orient = obj.get('orientation', 0.0)
                print(f"  ✅ {obj['item']}: {obj['name']} ({obj['object_type']})")
                print(f"     Position: [{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]  Orientation: {orient:.1f}°")

        if failed_lod300_objects:
            print(f"\n❌ FAILED/MISSING LOD300 OBJECTS ({len(failed_lod300_objects)}):")
            for obj in failed_lod300_objects:
                print(f"  ❌ {obj['item']} ({obj['object_type']})")
                print(f"     Detection ID: {obj['detection_id']}")
                print(f"     Search Text: {obj.get('search_text', 'N/A')}")
                print(f"     Reason: {obj.get('reason', obj.get('error', 'Unknown'))}")

        # Calculate success rate
        success_rate = (len(found_lod300_objects) / max(len(expected_lod300_objects), 1)) * 100
        print(f"\n📊 LOD300 Extraction Success Rate: {success_rate:.1f}% ({len(found_lod300_objects)}/{len(expected_lod300_objects)})")

        if success_rate < 100:
            print(f"⚠️  WARNING: Some LOD300 objects from master template were not extracted!")
            print(f"   Action Required: Review failed objects and fix detection patterns")
        else:
            print(f"✅ SUCCESS: All LOD300 objects from master template were extracted!")

        print("=" * 80)

        # STEP 4: Generate output JSON with new structure
        print("\n📊 STEP 4: Generating output JSON...")

        # Count objects by phase
        by_phase = {}
        for obj in objects:
            phase = obj.get('_phase', 'unknown')
            by_phase[phase] = by_phase.get(phase, 0) + 1

        # Build output JSON structure
        output_json = {
            "extraction_metadata": {
                "extracted_by": "extraction_engine.py v2.0 (two-tier)",
                "extraction_date": datetime.now().strftime("%Y-%m-%d"),
                "extraction_time": datetime.now().strftime("%H:%M:%S"),
                "pdf_source": os.path.basename(pdf_path),
                "extraction_version": "2.0_two_tier",
                "calibration": extraction_context.get('calibration', {
                    "method": "default_fallback",
                    "scale_x": 0.0353,
                    "scale_y": 0.0353,
                    "confidence": 60
                })
            },

            "summary": {
                "total_objects": len(objects),
                "by_phase": by_phase
            },

            "objects": objects
        }

        print(f"  ✅ Total objects found: {len(objects)}")
        print(f"  ✅ Objects by phase:")
        for phase, count in sorted(by_phase.items()):
            print(f"     - {phase}: {count}")

        print("\n" + "=" * 80)
        print("✅ TWO-TIER EXTRACTION COMPLETE")
        print("=" * 80)
        print(f"\nOutput JSON structure:")
        print(f"  • extraction_metadata (who, when, calibration)")
        print(f"  • summary (hash total: {len(objects)} objects)")
        print(f"  • objects array ({len(objects)} items with 'placed': false)")
        print(f"\n💡 Next steps:")
        print(f"  1. Validate library references (validate_library_references.py)")
        print(f"  2. Place in Blender (mark 'placed': true)")
        print(f"  3. Verify hash total (summary.total_objects == count(placed))")

        return output_json


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys
    import json
    import os

    if len(sys.argv) < 2:
        print("Usage: python3 extraction_engine.py <pdf_path> [output_json] [--building-width W] [--building-length L]")
        print("\nExample:")
        print("  python3 extraction_engine.py 'TB-LKTN HOUSE.pdf'")
        print("  python3 extraction_engine.py 'TB-LKTN HOUSE.pdf' --building-width 9.8 --building-length 8.0")
        print("  python3 extraction_engine.py 'TB-LKTN HOUSE.pdf' custom_output.json")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Parse optional building dimensions
    building_width = 9.8
    building_length = 8.0
    building_height = 3.0
    output_path = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--building-width' and i + 1 < len(sys.argv):
            building_width = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--building-length' and i + 1 < len(sys.argv):
            building_length = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--building-height' and i + 1 < len(sys.argv):
            building_height = float(sys.argv[i + 1])
            i += 2
        elif not sys.argv[i].startswith('--'):
            output_path = sys.argv[i]
            i += 1
        else:
            i += 1

    # Default output to output_artifacts folder with timestamp
    if not output_path:
        # Create output_artifacts folder if it doesn't exist
        os.makedirs("output_artifacts", exist_ok=True)

        # Generate timestamped filename following pattern: <PDFname>_OUTPUT_<timestamp>.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_name = os.path.basename(pdf_path).replace('.pdf', '').replace(' ', '_')
        output_path = f"output_artifacts/{pdf_name}_OUTPUT_{timestamp}.json"

    # Run complete two-tier extraction
    output_json = complete_pdf_extraction(pdf_path, building_width, building_length, building_height)

    if output_json:
        # Save to JSON
        with open(output_path, 'w') as f:
            json.dump(output_json, f, indent=2)

        print(f"\n💾 Saved to: {output_path}")
        print(f"📁 Full path: {os.path.abspath(output_path)}")
        print(f"\n✅ Output JSON structure:")
        print(f"   • extraction_metadata: calibration data + timestamps")
        print(f"   • summary: hash total ({output_json['summary']['total_objects']} objects)")
        print(f"   • objects: all found items with 'placed': false")
    else:
        print("\n❌ Extraction failed - see errors above")
        sys.exit(1)
