# Implementation Plan - Option 2 + 3 (Get Things Right First)

**Date:** 2025-11-24
**Approach:** Build solid foundation before Blender export
**Timeline:** ~2-3 days for both options

---

## 🎯 **IMPLEMENTATION SEQUENCE**

### **Phase A: Option 2 - Hardening (4-6 hours)**
Make extraction robust and production-ready

### **Phase B: Option 3 - Phase 1D (1-2 days)**
Add elevation data and room classification

### **Phase C: Option 1 - Blender Export (2 hours)**
One-shot complete export with all data

---

## 📋 **PHASE A: HARDENING (Option 2)**

### **A1. Error Handling (1 hour)**

**Location:** `extraction_engine.py`

**Changes:**

1. **CalibrationEngine - Graceful fallback**
```python
def extract_drain_perimeter(self, page_number=6):
    """Extract drain perimeter with fallback"""
    try:
        page = self.pdf.pages[page_number]
    except IndexError:
        print(f"⚠️  Page {page_number} not found, using default calibration")
        return self._default_calibration()

    lines = page.lines
    if not lines or len(lines) < 10:
        print(f"⚠️  Insufficient line data on page {page_number}, using default")
        return self._default_calibration()

    # ... existing logic

def _default_calibration(self):
    """Fallback calibration based on building dimensions"""
    return {
        'scale_x': 0.0353,  # Typical scale for A3 drawings
        'scale_y': 0.0353,
        'offset_x': 0.0,
        'offset_y': 0.0,
        'method': 'default_fallback',
        'confidence': 60,  # Lower confidence for defaults
        'pdf_bounds': {
            'min_x': 0, 'max_x': 800,
            'min_y': 0, 'max_y': 600
        }
    }
```

2. **ScheduleExtractor - Handle missing tables**
```python
def extract_door_schedule(self, page_number=7):
    """Extract door schedule with defaults"""
    try:
        page = self.pdf.pages[page_number]
        tables = page.extract_tables()
    except IndexError:
        print(f"⚠️  Page {page_number} not found, using default door schedule")
        return self._default_door_schedule()

    if not tables or len(tables) == 0:
        print(f"⚠️  No tables found on page {page_number}, using defaults")
        return self._default_door_schedule()

    # ... existing extraction logic

def _default_door_schedule(self):
    """Default Malaysian house door dimensions (UBBL standards)"""
    return {
        'D1': {'width': 0.9, 'height': 2.1, 'quantity': 1},
        'D2': {'width': 0.9, 'height': 2.1, 'quantity': 1},
        'D3': {'width': 0.75, 'height': 2.1, 'quantity': 1}
    }

def _default_window_schedule(self):
    """Default Malaysian house window dimensions"""
    return {
        'W1': {'width': 1.8, 'height': 1.0, 'quantity': 1},
        'W2': {'width': 1.2, 'height': 1.0, 'quantity': 4},
        'W3': {'width': 0.6, 'height': 0.5, 'quantity': 2}
    }
```

3. **OpeningDetector - Validate positions**
```python
def extract_door_positions(self, page):
    """Extract door positions with validation"""
    words = page.extract_words()
    door_positions = []

    for word in words:
        text = word['text'].strip()
        if text in self.door_schedule.keys():
            x, y = word['x0'], word['top']
            building_x, building_y = self.calibration.transform_to_building(x, y)

            # VALIDATE: Check if position is within building bounds
            if not self._is_valid_position(building_x, building_y):
                print(f"⚠️  {text} position ({building_x:.2f}, {building_y:.2f}) outside building, skipping")
                continue

            door_positions.append({
                'door_type': text,
                'position': [building_x, building_y, 0.0],
                'width': self.door_schedule[text]['width'],
                'height': self.door_schedule[text]['height'],
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
```

---

### **A2. Validation (1.5 hours)**

**Add validation class:**

```python
class GeometryValidator:
    """Validate extracted geometry for physical plausibility"""

    def __init__(self, building_dims):
        self.building_width = building_dims['width']
        self.building_length = building_dims['length']

    def validate_wall(self, wall):
        """
        Validate wall geometry

        Raises:
            ValueError: If wall geometry is invalid

        Returns:
            list: Warning messages (non-critical issues)
        """
        warnings = []

        # Check 1: Minimum wall length
        if wall['length'] < 0.3:
            raise ValueError(
                f"Wall {wall['wall_id']} too short: {wall['length']:.2f}m "
                f"(minimum 0.3m for structural wall)"
            )

        # Check 2: Maximum wall length (sanity check)
        max_length = max(self.building_width, self.building_length) * 1.5
        if wall['length'] > max_length:
            warnings.append(
                f"Wall {wall['wall_id']} unusually long: {wall['length']:.2f}m "
                f"(building max dimension: {max_length:.2f}m)"
            )

        # Check 3: Wall thickness range
        if wall['thickness'] < 0.05:
            raise ValueError(
                f"Wall {wall['wall_id']} too thin: {wall['thickness']:.2f}m "
                f"(minimum 50mm)"
            )
        if wall['thickness'] > 0.5:
            warnings.append(
                f"Wall {wall['wall_id']} very thick: {wall['thickness']:.2f}m "
                f"(typical: 100-200mm)"
            )

        # Check 4: Zero-length wall (start == end)
        dx = wall['end_point'][0] - wall['start_point'][0]
        dy = wall['end_point'][1] - wall['start_point'][1]
        if abs(dx) < 0.01 and abs(dy) < 0.01:
            raise ValueError(
                f"Wall {wall['wall_id']} has zero length "
                f"(start == end point)"
            )

        # Check 5: Wall within building bounds
        for point in [wall['start_point'], wall['end_point']]:
            if not self._point_in_bounds(point):
                warnings.append(
                    f"Wall {wall['wall_id']} extends outside building bounds: "
                    f"({point[0]:.2f}, {point[1]:.2f})"
                )

        return warnings

    def validate_opening(self, opening, opening_type='door'):
        """Validate door/window dimensions"""
        warnings = []

        # Typical ranges
        if opening_type == 'door':
            min_width, max_width = 0.6, 1.2  # 600mm to 1200mm
            min_height, max_height = 2.0, 2.4  # 2000mm to 2400mm
        else:  # window
            min_width, max_width = 0.3, 3.0  # 300mm to 3000mm
            min_height, max_height = 0.3, 2.0  # 300mm to 2000mm

        # Check width
        if opening['width'] < min_width:
            raise ValueError(
                f"{opening_type.title()} {opening.get('door_type', opening.get('window_type'))} "
                f"too narrow: {opening['width']:.2f}m (min: {min_width}m)"
            )
        if opening['width'] > max_width:
            warnings.append(
                f"{opening_type.title()} {opening.get('door_type', opening.get('window_type'))} "
                f"very wide: {opening['width']:.2f}m (typical max: {max_width}m)"
            )

        # Check height
        if opening['height'] < min_height:
            warnings.append(
                f"{opening_type.title()} height unusually low: {opening['height']:.2f}m"
            )
        if opening['height'] > max_height:
            warnings.append(
                f"{opening_type.title()} height unusually high: {opening['height']:.2f}m"
            )

        # Check position
        pos = opening['position']
        if not self._point_in_bounds(pos):
            warnings.append(
                f"{opening_type.title()} position outside building: "
                f"({pos[0]:.2f}, {pos[1]:.2f})"
            )

        return warnings

    def _point_in_bounds(self, point, margin=1.0):
        """Check if point is within building bounds with margin"""
        x, y = point[0], point[1]
        return (
            -margin <= x <= self.building_width + margin and
            -margin <= y <= self.building_length + margin
        )
```

---

### **A3. Robust Duplicate Detection (1 hour)**

**Enhance WallDetector:**

```python
def remove_duplicates(self, tolerance=0.1):
    """
    Remove duplicate walls with improved detection

    Handles:
    - Walls with swapped start/end points
    - Walls with slight coordinate variations
    - Overlapping walls (same line, different segments)
    """
    unique_walls = []
    duplicate_count = 0

    for wall in self.candidates:
        is_duplicate = False

        for existing_wall in unique_walls:
            if self._is_duplicate_wall(wall, existing_wall, tolerance):
                is_duplicate = True
                duplicate_count += 1
                break

        if not is_duplicate:
            unique_walls.append(wall)

    self.candidates = unique_walls
    print(f"   Removed {duplicate_count} duplicates ({len(unique_walls)} unique)")
    return unique_walls

def _is_duplicate_wall(self, wall1, wall2, tolerance):
    """
    Check if two walls are duplicates

    Two walls are duplicates if:
    1. Same start + end (normal case)
    2. Swapped start + end (reversed wall)
    3. Overlapping segments on same line
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
    """
    # Check if walls are parallel (same angle)
    angle_diff = abs(wall1['angle'] - wall2['angle'])
    if angle_diff > 2 and angle_diff < 178:  # Not parallel or anti-parallel
        return False

    # Check if point from wall1 is on wall2's line
    distance = self._point_to_line_distance(
        wall1['start_point'],
        wall2['start_point'],
        wall2['end_point']
    )

    if distance > tolerance:
        return False  # Not collinear

    # Check if segments overlap (project onto 1D line)
    # Use parametric representation: point = start + t * (end - start)
    # Check if t values overlap

    # Project wall1 points onto wall2 line
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

def _point_to_line_distance(self, point, line_start, line_end):
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
```

---

### **A4. Improved Confidence Scoring (1.5 hours)**

**Enhance WallValidator:**

```python
def progressive_validation(self, connection_weight=0.4, opening_weight=0.3,
                          room_weight=0.2, parallelism_weight=0.1):
    """
    Enhanced progressive validation with 4 criteria

    Scoring:
    1. Connection score (40%) - How many walls connect
    2. Opening proximity (30%) - Near doors/windows
    3. Room boundary (20%) - Forms room enclosure
    4. Parallelism (10%) - Parallel to outer walls (structural logic)
    """
    # ... existing code ...

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

        wall['confidence'] = int(overall_confidence * 100)
        wall['validation_scores'] = {
            'connection': connection_score,
            'opening_proximity': opening_score,
            'room_boundary': room_score,
            'parallelism': parallelism_score
        }

        # ... categorize by confidence ...

def _calculate_room_boundary_score(self, wall):
    """
    Score based on whether wall forms part of a room enclosure

    Logic:
    - Wall with 2+ connections likely forms room boundary
    - Isolated wall unlikely to be structural
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
    """
    if not hasattr(self, 'outer_walls'):
        return 0.5  # Neutral if no outer walls available

    # Check if wall is parallel to any outer wall
    for outer_wall in self.outer_walls:
        angle_diff = abs(wall['angle'] - outer_wall['angle'])

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
    connection_tolerance = 0.2
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
```

---

## 📋 **PHASE B: PHASE 1D - ELEVATION DATA (Option 3)**

### **B1. Elevation Extractor Class (2-3 hours)**

**Add to extraction_engine.py:**

```python
class ElevationExtractor:
    """
    Extract elevation data from elevation views

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

        # Regex patterns for dimension extraction
        self.PATTERNS = {
            # Floor level: "FFL +0.150" or "FLOOR LEVEL +150mm"
            'floor_level': [
                r'FFL\s*\+?\s*(\d+\.?\d*)\s*m(?!m)',  # "FFL +0.150m"
                r'FFL\s*\+?\s*(\d+)\s*mm',             # "FFL +150mm" (convert to m)
                r'FLOOR\s+LEVEL\s*\+?\s*(\d+\.?\d*)\s*m(?!m)',
                r'FINISHED\s+FLOOR\s+LEVEL\s*\+?\s*(\d+\.?\d*)'
            ],

            # Lintel level: "LINTEL LEVEL 2100mm" or "LINTEL +2.1m"
            'lintel_level': [
                r'LINTEL.*?(\d+\.?\d*)\s*m(?!m)',      # "LINTEL +2.1m"
                r'LINTEL.*?(\d+)\s*mm',                 # "LINTEL 2100mm"
                r'LINTEL\s+LEVEL.*?(\d+\.?\d*)',
                r'DOOR\s+HEAD.*?(\d+\.?\d*)'
            ],

            # Ceiling level: "CEILING LEVEL 3000mm"
            'ceiling_level': [
                r'CEILING.*?(\d+\.?\d*)\s*m(?!m)',
                r'CEILING.*?(\d+)\s*mm',
                r'SOFFIT.*?(\d+\.?\d*)',
                r'ROOF\s+LEVEL.*?(\d+\.?\d*)'
            ],

            # Window sill: "SILL 1000mm" or "W/S +1.0m"
            'window_sill': [
                r'SILL.*?(\d+\.?\d*)\s*m(?!m)',
                r'SILL.*?(\d+)\s*mm',
                r'W/?S.*?(\d+\.?\d*)\s*m(?!m)',
                r'WINDOW\s+SILL.*?(\d+\.?\d*)'
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
            patterns: List of regex patterns to try

        Returns:
            float: Dimension in meters, or None if not found
        """
        import re

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1)
                value = float(value_str)

                # Convert mm to m if pattern ends with 'mm'
                if 'mm' in pattern and 'mm' in match.group(0):
                    value = value / 1000.0

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
            dict: Combined elevation data with confidence scores
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
```

---

### **B2. Room Label Extractor (2-3 hours)**

**Add to extraction_engine.py:**

```python
class RoomLabelExtractor:
    """
    Extract room labels from floor plan (Malay text)

    Pattern matching for Malaysian house room labels
    """

    def __init__(self, calibration_engine):
        self.calibration = calibration_engine

        # Malay room label patterns
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

        import re

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
```

---

### **B3. Window Sill Height Inference (1 hour)**

**Add to extraction_engine.py:**

```python
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
        list: Windows with sill_height added
    """
    default_sill = elevations.get('window_sill', 1.0)

    for window in windows:
        window_type = window['window_type']
        width = window_schedule[window_type]['width']

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
        window['lintel_height'] = sill_height + window['height']

    return windows
```

---

## 📋 **IMPLEMENTATION TIMELINE**

### **Day 1: Hardening (4-6 hours)**
- Hour 1: Error handling (CalibrationEngine, ScheduleExtractor, OpeningDetector)
- Hour 2-3: Validation class (GeometryValidator)
- Hour 4: Robust duplicate detection (WallDetector)
- Hour 5-6: Improved confidence scoring (WallValidator)

### **Day 2: Phase 1D Part 1 (6-8 hours)**
- Hour 1-3: ElevationExtractor class with regex patterns
- Hour 4-6: RoomLabelExtractor with Malay patterns
- Hour 7-8: Window sill height inference

### **Day 3: Integration + Testing (4-6 hours)**
- Hour 1-2: Integration of all new components
- Hour 3: Create comprehensive test script
- Hour 4: Run complete pipeline test
- Hour 5-6: Fix any issues, validate results

---

## ✅ **SUCCESS CRITERIA**

After implementation, we should have:

1. ✅ **Robust extraction** - Handles missing tables, pages, malformed data
2. ✅ **Validated geometry** - All walls/openings pass physical validation
3. ✅ **No duplicates** - Robust duplicate detection (normal + swapped + overlapping)
4. ✅ **Better confidence** - 4-criteria scoring (connection + opening + room + parallelism)
5. ✅ **Elevation data** - Ceiling heights, window sills, lintel levels
6. ✅ **Room classification** - Malay labels → English room types

**Output JSON will have:**
```json
{
  "elevations": {
    "floor_level": 0.15,
    "lintel_level": 2.1,
    "ceiling_level": 3.0,
    "window_sill": 1.0
  },
  "rooms": [
    {"name": "BILIK TIDUR 1", "type": "bedroom_1", "position": [...]},
    {"name": "TANDAS", "type": "toilet", "position": [...]}
  ],
  "windows": [
    {
      "window_type": "W1",
      "position": [...],
      "sill_height": 1.0,      // NEW
      "lintel_height": 2.0     // NEW
    }
  ],
  "walls": [
    {
      "wall_id": "candidate_27",
      "validation_scores": {
        "connection": 1.0,
        "opening_proximity": 1.0,
        "room_boundary": 0.7,    // NEW
        "parallelism": 1.0       // NEW
      }
    }
  ]
}
```

---

**Ready to implement?**
- Day 1: Hardening
- Day 2: Phase 1D (elevations + rooms)
- Day 3: Integration + testing
- Then: One-shot Blender export with complete data ✅
