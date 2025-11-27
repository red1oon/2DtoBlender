# Vector Semantic Extraction Guide
## 2D Architectural Drawing Symbol Detection

**Purpose:** Extract raw geometric semantics from CAD-exported PDF floor plans  
**Tools:** OpenCV, NumPy  
**Input:** Page 2 (electrical plan) - cleanest linework

---

## 1. DOOR SYMBOLS

### 1.1 Door Anatomy
```
         Arc (swing path)
            ╭───╮
           ╱     ╲
          ╱       ╲
    ─────●─────────   ← Thick line (door leaf)
         │
         │ ← Thin line (wall/frame connection)
         │
    ─────┴─────────   ← Wall line
         
    ● = Hinge point (pivot)
```

### 1.2 Raw Semantics to Extract

| Property | Detection Method | Values |
|----------|------------------|--------|
| **Hinge position** | Arc center point | (x, y) pixels |
| **Swing radius** | Arc radius | ~25-40px at 1:100 |
| **Door leaf** | Thick line from hinge | Angle in degrees |
| **Swing direction** | Arc start/end angles | CW or CCW |
| **Opening side** | Leaf angle relative to wall | LEFT or RIGHT |
| **Door width** | Line length = arc radius | 750mm, 900mm |

### 1.3 Detection Algorithm
```python
def detect_door_symbol(image, roi):
    """
    Returns:
        hinge_point: (x, y) - pivot location
        swing_direction: 'CW' | 'CCW' 
        opening_side: 'LEFT' | 'RIGHT'
        leaf_angle: degrees from horizontal
        door_width_px: radius in pixels
    """
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    
    # 1. Find arc using HoughCircles (partial circles)
    circles = cv2.HoughCircles(edges, cv2.HOUGH_GRADIENT,
                                dp=1, minDist=30,
                                param1=50, param2=20,
                                minRadius=20, maxRadius=45)
    
    # 2. Find thick line (door leaf) - use line width detection
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 
                            threshold=20, minLineLength=20, maxLineGap=5)
    
    # 3. Classify line thickness
    for line in lines:
        x1, y1, x2, y2 = line[0]
        # Sample perpendicular profile to measure width
        thickness = measure_line_thickness(gray, x1, y1, x2, y2)
        if thickness > 2:  # Thick = door leaf
            leaf_line = line
        else:  # Thin = frame
            frame_line = line
    
    # 4. Determine hinge (intersection of leaf and arc center)
    hinge = find_arc_center(circles[0])
    
    # 5. Determine swing direction from arc quadrant
    arc_quadrant = get_arc_quadrant(edges, hinge, radius)
    # Quadrant determines: CW/CCW and LEFT/RIGHT
    
    return {
        'hinge': hinge,
        'radius_px': radius,
        'leaf_angle': calculate_angle(leaf_line),
        'swing': 'CW' if arc_quadrant in [1, 3] else 'CCW',
        'opens': 'LEFT' if arc_quadrant in [1, 4] else 'RIGHT'
    }
```

### 1.4 Swing Direction Matrix
```
Arc Quadrant → Swing + Opening Side

    Q2 │ Q1          Q1: CCW, opens RIGHT (into room)
   ────┼────         Q2: CW,  opens LEFT  (into room)
    Q3 │ Q4          Q3: CCW, opens LEFT  (into room)
                     Q4: CW,  opens RIGHT (into room)
       ● = hinge
```

### 1.5 Line Thickness Detection
```python
def measure_line_thickness(gray, x1, y1, x2, y2):
    """Measure line width by sampling perpendicular profile"""
    # Get perpendicular direction
    dx, dy = x2 - x1, y2 - y1
    length = np.sqrt(dx*dx + dy*dy)
    nx, ny = -dy/length, dx/length  # Normal vector
    
    # Sample along perpendicular at midpoint
    mx, my = (x1+x2)//2, (y1+y2)//2
    profile = []
    for t in range(-10, 11):
        px, py = int(mx + t*nx), int(my + t*ny)
        if 0 <= px < gray.shape[1] and 0 <= py < gray.shape[0]:
            profile.append(gray[py, px])
    
    # Count dark pixels (line width)
    threshold = 128
    width = sum(1 for p in profile if p < threshold)
    return width
```

---

## 2. WINDOW SYMBOLS

### 2.1 Window Anatomy
```
    ═══════════════════   ← Outer frame (thick)
    │     │     │     │   ← Glass pane dividers (thin)
    │     │     │     │
    ═══════════════════   ← Outer frame (thick)
    
    Single pane:  ═══════════
    Double pane:  ═════╪═════
    Triple pane:  ═══╪═══╪═══
```

### 2.2 Raw Semantics to Extract

| Property | Detection Method | Values |
|----------|------------------|--------|
| **Position** | Rectangle center | (x, y) pixels |
| **Width** | Rectangle long edge | 600-1800mm |
| **Pane count** | Internal divider lines | 1, 2, 3 panels |
| **Orientation** | Long axis direction | HORIZONTAL or VERTICAL |
| **Wall alignment** | Parallel to nearest wall | N/S/E/W |

### 2.3 Detection Algorithm
```python
def detect_window_symbol(image, roi):
    """
    Returns:
        center: (x, y)
        width_px: window width
        height_px: window height (wall thickness)
        pane_count: 1, 2, or 3
        orientation: 'H' or 'V'
    """
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # 1. Find rectangles (window frame)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, 
                                    cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        # Approximate to polygon
        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        
        if len(approx) == 4:  # Rectangle
            x, y, w, h = cv2.boundingRect(approx)
            aspect = max(w, h) / min(w, h)
            
            # Windows are elongated rectangles
            if 2.0 < aspect < 6.0:
                # 2. Count internal dividers
                roi_window = gray[y:y+h, x:x+w]
                internal_lines = detect_internal_lines(roi_window)
                pane_count = len(internal_lines) + 1
                
                return {
                    'center': (x + w//2, y + h//2),
                    'width_px': max(w, h),
                    'height_px': min(w, h),
                    'panes': pane_count,
                    'orientation': 'H' if w > h else 'V'
                }
```

---

## 3. WALL LINES

### 3.1 Wall Semantics

| Property | Detection Method | Values |
|----------|------------------|--------|
| **Start/end points** | HoughLinesP | (x1,y1), (x2,y2) |
| **Wall type** | Line thickness | Exterior (thick) vs Interior (thin) |
| **Length** | Euclidean distance | In pixels → convert to mm |
| **Orientation** | Angle | Horizontal, Vertical, or degrees |
| **Openings** | Gap detection | Door/window locations |

### 3.2 Detection Algorithm
```python
def detect_walls(image):
    """
    Returns list of wall segments with properties
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    
    # Detect lines
    lines = cv2.HoughLinesP(edges, 1, np.pi/180,
                            threshold=50,
                            minLineLength=50,  # Ignore short lines
                            maxLineGap=10)     # Merge nearby segments
    
    walls = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        
        # Measure thickness
        thickness = measure_line_thickness(gray, x1, y1, x2, y2)
        
        # Calculate properties
        length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
        angle = np.degrees(np.arctan2(y2-y1, x2-x1))
        
        # Classify wall type
        if thickness >= 3:
            wall_type = 'EXTERIOR'
        elif thickness >= 2:
            wall_type = 'INTERIOR'
        else:
            continue  # Skip annotation lines
        
        # Snap to orthogonal if close
        if abs(angle) < 5 or abs(angle) > 175:
            orientation = 'HORIZONTAL'
        elif 85 < abs(angle) < 95:
            orientation = 'VERTICAL'
        else:
            orientation = f'{angle:.1f}°'
        
        walls.append({
            'start': (x1, y1),
            'end': (x2, y2),
            'length_px': length,
            'thickness_px': thickness,
            'type': wall_type,
            'orientation': orientation
        })
    
    return merge_collinear_walls(walls)
```

### 3.3 Opening Detection
```python
def detect_openings_in_wall(wall, all_walls):
    """Find gaps in wall line (door/window openings)"""
    x1, y1, x2, y2 = wall['start'] + wall['end']
    
    # Project all walls onto this wall's axis
    # Find gaps > 500px (minimum opening)
    
    openings = []
    # ... gap detection logic ...
    
    return openings  # List of (start_pos, end_pos, width)
```

---

## 4. SANITARY FIXTURES

### 4.1 WC (Toilet) Symbol
```
      ╭───╮       ← Tank (rectangle)
      │   │
    ╭─┴───┴─╮     ← Bowl (ellipse/oval)
    │       │
    ╰───────╯
```

| Property | Method | Values |
|----------|--------|--------|
| **Position** | Centroid | (x, y) |
| **Orientation** | Tank direction | N/S/E/W (faces wall) |
| **Type** | Shape analysis | Floor-mounted, Wall-hung |

### 4.2 Basin Symbol
```
    ╭─────────╮    ← Basin outline (rounded rectangle or oval)
    │    ○    │    ← Drain (small circle)
    │  ──┬──  │    ← Faucet marks
    ╰────┴────╯
```

### 4.3 Shower Symbol
```
    ┌─────────┐    ← Square/rectangle outline
    │  ╲   ╱  │    ← Diagonal lines or spray pattern
    │   ╲ ╱   │
    │    ○    │    ← Drain
    └─────────┘
```

### 4.4 Detection Strategy
```python
FIXTURE_TEMPLATES = {
    'wc': {
        'pattern': 'ellipse + rectangle',
        'size_range': (30, 50),  # pixels
        'aspect': (1.5, 2.0)
    },
    'basin': {
        'pattern': 'rounded_rectangle + center_circle',
        'size_range': (20, 35),
        'aspect': (1.0, 1.5)
    },
    'shower': {
        'pattern': 'square + diagonal_lines',
        'size_range': (40, 60),
        'aspect': (0.9, 1.1)
    }
}
```

---

## 5. ELECTRICAL SYMBOLS

### 5.1 Common Symbols
```
Fan Point (FP):     ○ with 3 curved lines (blades)
Light Point (LC):   ○ with X inside
Switch (SW):        Small rectangle on wall line
Power Point (PP):   Rectangle with 2-3 slots
```

### 5.2 Detection
```python
# Template matching is most reliable for these
# Extract real templates from known locations in drawing
```

---

## 6. GRID & DIMENSION ANNOTATIONS

### 6.1 Grid Circle Markers
```
    ╭───╮
    │ A │    ← Grid label inside circle
    ╰───╯
```

| Property | Method | Values |
|----------|--------|--------|
| **Position** | HoughCircles | (x, y) |
| **Label** | OCR inside circle | A-E, 1-5 |
| **Type** | Location | HORIZONTAL (top/bottom), VERTICAL (left/right) |

### 6.2 Dimension Annotations
```
    ←───── 3100 ─────→    ← Leader lines + number
    │                 │
```

| Property | Method |
|----------|--------|
| **Value** | Tesseract PSM 12, filter `\d{3,4}` |
| **Position** | Text bounding box |
| **Associated grids** | Nearest grid circles |

---

## 7. COORDINATE TRANSFORMATION

### 7.1 Pixel to World Coordinates
```python
# Drawing bounds (empirically determined from page 2)
DRAW_BOUNDS = {
    'x1': 100,   # Left margin
    'x2': 680,   # Right edge of drawing
    'y1': 130,   # Top margin
    'y2': 710    # Bottom edge of drawing
}

# Grid extent from GridTruth
GRID_EXTENT = {
    'x_max': 11.2,  # meters
    'y_max': 8.5    # meters
}

def pixel_to_world(px, py):
    """Convert pixel coords to world coords (meters)"""
    wx = ((px - DRAW_BOUNDS['x1']) / 
          (DRAW_BOUNDS['x2'] - DRAW_BOUNDS['x1'])) * GRID_EXTENT['x_max']
    
    # Y is inverted (image origin top-left, world origin bottom-left)
    wy = GRID_EXTENT['y_max'] - (
         (py - DRAW_BOUNDS['y1']) / 
         (DRAW_BOUNDS['y2'] - DRAW_BOUNDS['y1'])) * GRID_EXTENT['y_max']
    
    return round(wx, 2), round(wy, 2)
```

---

## 8. FILTERING FALSE POSITIVES

### 8.1 Page Selection
```python
PAGE_USAGE = {
    1: {'geometry': False, 'text': True},   # Labels only (cluttered)
    2: {'geometry': True,  'text': True},   # Best for CV (clean)
    3: {'geometry': True,  'text': True},   # Roof
    8: {'geometry': False, 'text': True}    # Schedules
}
```

### 8.2 Region Filtering
```python
# Exclude margins, title block, legend
VALID_DRAWING_AREA = {
    'x_min': 100,
    'x_max': 700,
    'y_min': 130,
    'y_max': 720
}

def is_in_drawing_area(x, y):
    return (VALID_DRAWING_AREA['x_min'] < x < VALID_DRAWING_AREA['x_max'] and
            VALID_DRAWING_AREA['y_min'] < y < VALID_DRAWING_AREA['y_max'])
```

### 8.3 Confidence Thresholds
```python
THRESHOLDS = {
    'template_match': 0.60,   # Minimum correlation
    'nms_distance': 40,       # Pixels between detections
    'min_line_length': 50,    # Ignore short segments
    'min_line_thickness': 1.5 # Ignore thin annotations
}
```

---

## 9. OUTPUT SCHEMA

### 9.1 Door Detection Output
```json
{
  "id": "DOOR_001",
  "pixel": {"x": 262, "y": 326},
  "world": {"x": 2.6, "y": 6.0},
  "properties": {
    "hinge": {"x": 262, "y": 326},
    "radius_px": 35,
    "width_mm": 900,
    "leaf_angle_deg": 0,
    "swing": "CCW",
    "opens": "LEFT",
    "orientation": "NORTH"
  },
  "confidence": 0.85,
  "source_page": 2
}
```

### 9.2 Window Detection Output
```json
{
  "id": "WINDOW_001",
  "pixel": {"x": 450, "y": 280},
  "world": {"x": 6.2, "y": 6.5},
  "properties": {
    "width_mm": 1200,
    "pane_count": 2,
    "orientation": "HORIZONTAL",
    "wall": "NORTH"
  },
  "confidence": 0.78,
  "source_page": 2
}
```

### 9.3 Wall Detection Output
```json
{
  "id": "WALL_001",
  "start": {"x": 0.75, "y": 0.75},
  "end": {"x": 10.45, "y": 0.75},
  "properties": {
    "length_m": 9.7,
    "type": "EXTERIOR",
    "orientation": "HORIZONTAL",
    "openings": [
      {"position": 2.2, "width_mm": 900, "type": "DOOR"},
      {"position": 5.5, "width_mm": 1200, "type": "WINDOW"}
    ]
  }
}
```

---

## 10. PIPELINE INTEGRATION

```python
def extract_all_semantics(pdf_path):
    """
    Full extraction pipeline
    """
    # Stage 1: OCR
    text_data = tesseract_extract(pdf_path, page=2, psm=12)
    dimensions = parse_dimensions(text_data)
    
    # Stage 2: Geometry
    image = load_page_image(pdf_path, page=2)
    
    doors = detect_doors(image)
    windows = detect_windows(image)
    walls = detect_walls(image)
    fixtures = detect_fixtures(image)
    
    # Stage 3: Correlation
    doors = correlate_with_labels(doors, text_data)
    walls = assign_openings(walls, doors, windows)
    
    # Stage 4: Coordinate transform
    for element in doors + windows + fixtures:
        element['world'] = pixel_to_world(element['pixel'])
    
    return {
        'dimensions': dimensions,
        'doors': doors,
        'windows': windows,
        'walls': walls,
        'fixtures': fixtures
    }
```

---

## 11. KNOWN LIMITATIONS

| Issue | Workaround |
|-------|------------|
| Multiple door sizes | Multi-scale templates (750, 900, 1000mm) |
| Rotated symbols | 4-orientation templates (0°, 90°, 180°, 270°) |
| Broken lines | Morphological closing before detection |
| Overlapping symbols | NMS with IoU threshold |
| Low contrast | Adaptive thresholding |
| SHX fonts | Tesseract PSM 12 instead of pdfplumber |

---

**Document Version:** 1.0  
**For:** Dev Team - Vector Semantic Extraction  
**Dependencies:** OpenCV 4.x, NumPy, Tesseract 4.x, Python 3.8+
