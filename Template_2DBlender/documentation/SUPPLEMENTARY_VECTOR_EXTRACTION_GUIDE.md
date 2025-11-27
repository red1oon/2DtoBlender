# Supplementary Vector Semantic Extraction Guide
## MEP, Roof, Plumbing & Material Symbols

**Companion to:** VECTOR_SEMANTIC_EXTRACTION_GUIDE.md  
**Source:** TBLKTN_HOUSE.pdf (8 pages analyzed)

---

# PAGE MAP

| Page | Content | Extract Geometry | Extract Text |
|------|---------|------------------|--------------|
| 1 | Floor Plan | Doors, windows, fixtures | Room names, codes, legends |
| 2 | Electrical Plan | Clean walls, doors | Grid dimensions, FP codes |
| 3 | Roof Plan | Roof outline, slopes | Eave dimensions, drainage codes |
| 4 | Front/Rear Elevation | - | Heights, level markers |
| 5 | Side Elevations | - | Heights, material codes |
| 6 | Sections A-A, B-B | Roof profile | Heights, room labels |
| 7 | Plumbing Diagrams | Pipe routes | Pipe sizes, fixture names |
| 8 | Door/Window Schedule | Elevation drawings | Sizes, types, locations, quantities |

---

# 1. MEP SYMBOLS (Electrical - Page 2)

## 1.1 Symbol Legend Matching

**Strategy:** Extract legend from page, use as template library

```
LEGEND LOCATION: Right side of page 2 (x > 750px)
```

| Symbol | Code | Description | Shape Pattern |
|--------|------|-------------|---------------|
| ⓜ | M | Electricity Meter | Circle with M |
| ▬ | - | Fuse & Distribution Board | Filled rectangle |
| ○ | LC | Ceiling Light Point | Empty circle |
| ○⟲ | FP | Ceiling Fan Point | Circle with curved lines |
| ●●● | SW | One Way Switch 1,2,3 gang | Small filled circles |
| ⊐| | PP | 3 pin 13A power point | Rectangle with slots |
| △ | WL | Wall Mounted Light | Triangle on wall |

## 1.2 Detection Algorithm

```python
def extract_legend_templates(image, legend_roi):
    """
    Extract real symbol templates from legend area.
    
    Args:
        image: Full page image
        legend_roi: (x1, y1, x2, y2) of legend box
    
    Returns:
        dict of {code: template_image}
    """
    legend = image[legend_roi[1]:legend_roi[3], legend_roi[0]:legend_roi[2]]
    
    # OCR to find symbol codes
    text_boxes = tesseract_with_boxes(legend)
    
    templates = {}
    for box in text_boxes:
        code = box['text']
        if code in ['M', 'FP', 'LC', 'SW', 'PP', 'WL']:
            # Extract region left of text (symbol area)
            symbol_x = box['x'] - 40
            symbol_y = box['y']
            template = legend[symbol_y-15:symbol_y+15, symbol_x:symbol_x+30]
            templates[code] = template
    
    return templates

def match_mep_symbols(image, templates):
    """Match extracted legend templates across floor plan"""
    detections = []
    
    for code, template in templates.items():
        matches = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        locs = np.where(matches > 0.7)
        
        for pt in zip(*locs[::-1]):
            if is_in_drawing_area(pt[0], pt[1]):
                detections.append({
                    'code': code,
                    'x': pt[0],
                    'y': pt[1],
                    'confidence': matches[pt[1], pt[0]]
                })
    
    return nms(detections)
```

## 1.3 Fan Point (FP) Specific Detection

```
FP Symbol Anatomy:
    ╭─────╮
   ╱  ╭─╮  ╲    ← Curved blade lines (3)
  │  ╱   ╲  │
  │ │  ●  │ │   ← Center point
  │  ╲   ╱  │
   ╲  ╰─╯  ╱
    ╰─────╯
```

| Property | Method | Values |
|----------|--------|--------|
| Center | Circle detection | (x, y) |
| Type | Blade count | 3 or 4 blades |
| Associated room | Containment | Room polygon |

## 1.4 Output Schema

```json
{
  "id": "FP_001",
  "code": "FP",
  "description": "Ceiling Fan Point",
  "pixel": {"x": 350, "y": 420},
  "world": {"x": 4.8, "y": 5.2},
  "room": "RUANG TAMU",
  "source_page": 2
}
```

---

# 2. PLUMBING SYMBOLS (Pages 1, 7)

## 2.1 Fixture Symbols from Legend (Page 1)

| Symbol | Description | Qty | Shape Pattern |
|--------|-------------|-----|---------------|
| ⊠ | Aluminium Kitchen Sink | 1 | Rectangle with X |
| ◻ | Basin | 1 | Small rectangle |
| ◻● | Water Closet (Seating) | 1 | Rectangle + circle |
| ═══ | Shower | 1 | Rectangle with lines |
| ⊗ | Floor Trap | 3 | Circle with X |
| ╋ | Tap | 4 | Cross/plus |
| ▭ | Gully Trap | 2 | Small rectangle |

## 2.2 Detection Patterns

```python
PLUMBING_PATTERNS = {
    'kitchen_sink': {
        'shape': 'rectangle_with_x',
        'size_range': (30, 50),  # pixels
        'aspect': (1.2, 2.0),
        'internal': 'diagonal_cross'
    },
    'wc': {
        'shape': 'oval_plus_rectangle',
        'size_range': (25, 40),
        'components': ['ellipse', 'rectangle']
    },
    'basin': {
        'shape': 'small_rectangle',
        'size_range': (15, 25),
        'aspect': (0.8, 1.2)
    },
    'floor_trap': {
        'shape': 'circle_with_x',
        'radius_range': (8, 15),
        'internal': 'cross'
    },
    'tap': {
        'shape': 'cross',
        'size_range': (10, 20)
    },
    'shower': {
        'shape': 'rectangle_with_parallel_lines',
        'size_range': (35, 50)
    }
}
```

## 2.3 Pipe Symbols (Page 7 - Diagrammatic)

| Symbol | Code | Description | Detection |
|--------|------|-------------|-----------|
| ⓜ | m | Water Meter | Circle with 'm' |
| ─┬─ | tap | Tap Point | T-junction |
| ⊘SC | SC | Stop Cock | Circle with SC |
| ⊠ | - | Bollafix Valve | Rectangle with X |

### Pipe Sizes (from labels)
```
Cold Water:
- 20 ø Upvc distribution pipe
- 15 ø Upvc pipe (branches)
- 20 ø pressure relief pipe

Sanitary:
- 100 ø Upvc soil pipe
- 75 ø Upvc waste pipe  
- 50 ø Upvc vent pipe
- 50 ø anti-syphonage pipe
```

## 2.4 Pipe Route Detection

```python
def detect_pipe_routes(image):
    """
    Detect pipe lines and junctions from plumbing diagram.
    Page 7 is DIAGRAMMATIC (not to scale) - extract topology only.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    
    # Detect lines
    lines = cv2.HoughLinesP(edges, 1, np.pi/180,
                            threshold=30, minLineLength=20, maxLineGap=10)
    
    # Find T-junctions and L-junctions
    junctions = find_line_intersections(lines)
    
    # OCR for pipe sizes
    text = tesseract_psm12(image)
    pipe_sizes = re.findall(r'(\d+)\s*[øo]\s*(\w+)', text)
    
    return {
        'lines': lines,
        'junctions': junctions,
        'pipe_sizes': pipe_sizes
    }
```

---

# 3. ROOF PLAN (Page 3)

## 3.1 Roof Semantics

```
Roof Plan Anatomy:
                    
    ╔═══════════════════════════════╗
    ║   ╱╲      RIDGE      ╱╲      ║  ← Eave line (outer)
    ║  ╱  ╲              ╱   ╲     ║
    ║ ╱    ╲────────────╱     ╲    ║  ← Ridge line
    ║╱      ╲  SLOPE   ╱       ╲   ║
    ║        ╲        ╱   25°   ║  ← Slope indicator
    ║         ╲      ╱          ║
    ╚═══════════════════════════════╝
    
    ←─────────── 700 ─────────────→   ← Eave overhang
```

## 3.2 Elements to Extract

| Element | Method | Output |
|---------|--------|--------|
| Eave outline | Contour detection | Polygon vertices |
| Ridge lines | Hough lines + angle filter | Line segments |
| Slope direction | Hatching pattern analysis | N/S/E/W |
| Slope angle | OCR | 25° (from text) |
| Eave overhang | OCR dimension | 700mm |
| Vent stacks | Circle detection | (x, y) positions |

## 3.3 Roof-Porch Relationship

From Page 3 and 6 (Section):
```
                    Main Roof
                      /\
                     /  \
    ________________/____\________________  ← Roof level
    |              |      |              |
    |    PORCH     | MAIN |    PORCH    |  
    |    750mm     |      |    750mm    |
    |______________|______|_____________|  ← Floor level
    
    Total width = 750 + 9900 + 750 = 11400mm (with porch)
    Building width = 9900mm (without porch)
```

## 3.4 Detection Algorithm

```python
def detect_roof_elements(image):
    """Extract roof plan semantics"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 1. Detect eave outline (outermost rectangle)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, 
                                    cv2.CHAIN_APPROX_SIMPLE)
    eave_contour = max(contours, key=cv2.contourArea)
    
    # 2. Detect ridge lines (diagonal lines inside roof)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, 
                            minLineLength=100, maxLineGap=10)
    ridge_lines = [l for l in lines if is_diagonal(l)]
    
    # 3. Detect slope hatching direction
    # Hatching lines are short parallel lines indicating slope
    hatch_lines = [l for l in lines if 20 < line_length(l) < 50]
    slope_direction = analyze_hatch_direction(hatch_lines)
    
    # 4. OCR for dimensions and angles
    text = tesseract_psm12(image)
    angles = re.findall(r'(\d+)°', text)  # e.g., "25°"
    overhangs = re.findall(r'(\d+)\s*$', text)  # e.g., "700"
    
    return {
        'eave_polygon': eave_contour,
        'ridge_lines': ridge_lines,
        'slope_directions': slope_direction,
        'pitch_angle': angles[0] if angles else None,
        'eave_overhang_mm': 700  # From dimension
    }

def is_diagonal(line):
    """Check if line is diagonal (not H or V)"""
    x1, y1, x2, y2 = line[0]
    angle = abs(np.degrees(np.arctan2(y2-y1, x2-x1)))
    return 20 < angle < 70 or 110 < angle < 160
```

## 3.5 Drainage/Plumbing Stacks on Roof

From Page 3 legend:

| Code | Description |
|------|-------------|
| G1 | R.C beams, Ground slabs & footing |
| G2 | Soil Pipe discharged to IST |
| G3 | Waste Pipe |
| G4 | Manhole |
| G5 | 230mm ø half p.c perimeter drain |
| G6 | 250gal HDPE Water Tank location |
| G7 | Dotted lines = waterproofing |
| G8 | Dotted lines = damp proof membrane |
| G9 | 50 ø Upvc vent pipe |
| G10 | 50mm working counter top |

```python
def detect_roof_stacks(image):
    """Detect plumbing stacks penetrating roof"""
    # Small circles with G-codes nearby
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT,
                                dp=1, minDist=20,
                                param1=50, param2=25,
                                minRadius=5, maxRadius=15)
    
    stacks = []
    for circle in circles:
        x, y, r = circle
        # OCR nearby for G-code
        roi = image[y-30:y+30, x-30:x+30]
        text = tesseract(roi)
        code = re.search(r'G\d+', text)
        if code:
            stacks.append({
                'position': (x, y),
                'code': code.group(),
                'type': DRAINAGE_CODES.get(code.group())
            })
    
    return stacks
```

---

# 4. ELEVATION ELEMENTS (Pages 4, 5, 6)

## 4.1 Level Markers

```
Level Marker Anatomy:
    
    ─────────────────────────  ← Level line
           ╲ BEAM/CEILING LEVEL
            ╲
             ▽
```

| Level | Height | Code |
|-------|--------|------|
| GRD. LEVEL | 0 | Ground reference |
| APRON LEVEL | +150mm | Concrete apron |
| GRD. FLOOR LEVEL | +150mm | FFL (Finished Floor Level) |
| BEAM/CEILING LEVEL | +3150mm | Ceiling height |
| ROOF BEAM LEVEL | varies | Roof structure |

## 4.2 Detection Algorithm

```python
def detect_level_markers(image):
    """Extract level markers from elevation/section views"""
    
    # Level markers have specific pattern:
    # - Horizontal line
    # - Diagonal leader line
    # - Triangle pointer
    # - Text label
    
    text = tesseract_psm12(image)
    
    LEVEL_PATTERNS = [
        r'GRD\.?\s*LEVEL',
        r'GRD\.?\s*FLOOR\s*LEVEL',
        r'APRON\s*LEVEL', 
        r'BEAM.*CEILING\s*LEVEL',
        r'ROOF.*LEVEL',
        r'FFL'
    ]
    
    levels = []
    for pattern in LEVEL_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            # Get bounding box from tesseract
            levels.append({
                'name': m.group(),
                'y_pixel': get_text_y_position(m),
                'height_mm': LEVEL_HEIGHTS.get(m.group())
            })
    
    return levels

LEVEL_HEIGHTS = {
    'GRD. LEVEL': 0,
    'APRON LEVEL': 150,
    'GRD. FLOOR LEVEL': 150,
    'BEAM/CEILING LEVEL': 3150,
}
```

## 4.3 Height Dimensions

From Page 4/6:
- Floor to ceiling: **3000mm**
- Ceiling to ridge: **1722mm** (from section)
- Apron height: **150mm**

---

# 5. MATERIAL CODES (All Pages)

## 5.1 Floor Finishes (Page 1 Legend)

| Code | Description |
|------|-------------|
| CT | Ceramic tiles as per Manuf's Spec |
| CR | Cement render (smooth) |

## 5.2 Wall Finishes (Page 1 Legend)

| Code | Description |
|------|-------------|
| TB | 100mm thk Tasblock Wall System |
| TB (thin) | 4mm thk Tasblock Single Wall |
| TB+RC | Tasblock infill concrete column |
| CW | 1500mm (h) Ceramic wall tiles |
| CP | 100mm Lightweight Copping |

## 5.3 Ceiling Finishes

| Code | Description |
|------|-------------|
| GB | Gypsum Board w/o cornice |

## 5.4 Roof Finishes

| Code | Description |
|------|-------------|
| MR | Metal Roofing with pre-fab trusses |
| GF | GI flashing gauge |

## 5.5 Exterior Finishes (Elevations)

| Code | Description | Location |
|------|-------------|----------|
| FG | Fair-faced / exposed | Walls |
| CP | Copping/capping | Wall tops |
| MR | Metal roof | Roof |

## 5.6 Detection Algorithm

```python
MATERIAL_CODES = {
    'CT': 'Ceramic Tiles',
    'CR': 'Cement Render',
    'TB': 'Tasblock Wall',
    'CW': 'Ceramic Wall Tiles',
    'CP': 'Copping',
    'GB': 'Gypsum Board',
    'MR': 'Metal Roofing',
    'GF': 'GI Flashing',
    'FG': 'Fair-faced'
}

def detect_material_codes(image, page_num):
    """Extract material codes from floor plan or elevations"""
    text = tesseract_psm12(image)
    
    found_codes = []
    for code, desc in MATERIAL_CODES.items():
        matches = re.finditer(rf'\b{code}\b', text)
        for m in matches:
            found_codes.append({
                'code': code,
                'description': desc,
                'page': page_num,
                'context': get_surrounding_text(text, m.start())
            })
    
    return found_codes
```

---

# 6. SECTION MARKERS (Pages 1, 6)

## 6.1 Section Line Symbol

```
Section Marker:
    
    ○──────────────────────────○
    A                          A
    
    Arrow indicates viewing direction
```

| Property | Method |
|----------|--------|
| Line | Dashed line detection |
| Endpoints | Circle detection |
| Label | OCR (A-A, B-B) |
| Direction | Arrow detection |

## 6.2 Detection

```python
def detect_section_markers(image):
    """Find section cut lines on floor plan"""
    
    # Section lines are dashed/chain lines
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Find circles at line ends
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT,
                                dp=1, minDist=50,
                                param1=50, param2=30,
                                minRadius=10, maxRadius=25)
    
    # OCR for section labels
    text_boxes = tesseract_with_boxes(image)
    section_labels = [b for b in text_boxes 
                      if re.match(r'^[A-Z]$', b['text'])]
    
    # Match circles with labels
    sections = []
    for label in section_labels:
        nearby_circles = find_nearby_circles(circles, label['x'], label['y'])
        if len(nearby_circles) >= 2:
            sections.append({
                'name': f"{label['text']}-{label['text']}",
                'start': nearby_circles[0],
                'end': nearby_circles[1]
            })
    
    return sections
```

---

# 7. DOOR/WINDOW SCHEDULE (Page 8)

## 7.1 Table Structure

```
┌────────────┬─────────────────────┬─────────────────────┬──────────────────┐
│ REFERENCES │         D1          │         D2          │        D3        │
├────────────┼─────────────────────┼─────────────────────┼──────────────────┤
│ TYPE       │ Metal frame, timber │ Flush door gloss    │ Flush door gloss │
├────────────┼─────────────────────┼─────────────────────┼──────────────────┤
│ SIZE       │ 900MM X 2100MM      │ 900MM X 2100MM      │ 750MM X 2100MM   │
├────────────┼─────────────────────┼─────────────────────┼──────────────────┤
│ LOCATION   │ Ruang Tamu & Dapur  │ Bilik Utama,2,3     │ Bilik Mandi,Tandas│
├────────────┼─────────────────────┼─────────────────────┼──────────────────┤
│ UNITS      │ 2 NOS               │ 3 NOS               │ 2 NOS            │
└────────────┴─────────────────────┴─────────────────────┴──────────────────┘
```

## 7.2 Elevation Drawing Semantics

Above schedule table, door elevation drawings show:

| Element | Detection | Data |
|---------|-----------|------|
| Door width | Dimension text | 900, 750 |
| Door height | Dimension text | 2100 |
| Panel pattern | Diagonal line (glass) | Glazed vs solid |
| Handle position | Small circle | Left or right side |
| Swing direction | Arc in plan inset | If shown |

## 7.3 Table Extraction

```python
def extract_schedule_table(image):
    """Extract door/window schedule from page 8"""
    
    # Use pdfplumber for table structure (better than OCR for tables)
    # Or use Tesseract with table detection
    
    text = tesseract_psm6(image)  # PSM 6 = uniform block of text
    
    # Parse table rows
    schedule = {
        'doors': {},
        'windows': {}
    }
    
    # Door schedule patterns
    door_pattern = r'(D\d)\s+.*?(\d{3,4})MM?\s*X\s*(\d{3,4})MM?\s+.*?(\d)\s*NOS'
    for m in re.finditer(door_pattern, text, re.IGNORECASE):
        code, width, height, qty = m.groups()
        schedule['doors'][code] = {
            'width_mm': int(width),
            'height_mm': int(height),
            'quantity': int(qty)
        }
    
    # Window schedule patterns
    window_pattern = r'(W\d)\s+.*?(\d{3,4})mm?\s*X\s*(\d{3,4})mm?\s+.*?(\d)\s*NOS'
    for m in re.finditer(window_pattern, text, re.IGNORECASE):
        code, width, height, qty = m.groups()
        schedule['windows'][code] = {
            'width_mm': int(width),
            'height_mm': int(height),
            'quantity': int(qty)
        }
    
    return schedule
```

---

# 8. CONSOLIDATED OUTPUT SCHEMA

```json
{
  "project": "TBLKTN_HOUSE",
  "scale": "1:100",
  
  "grids": {
    "horizontal": {"A": 0.0, "B": 1.3, "C": 4.4, "D": 8.1, "E": 11.2},
    "vertical": {"1": 0.0, "2": 2.3, "3": 5.4, "4": 7.0, "5": 8.5}
  },
  
  "building_envelope": {
    "main_width_mm": 9900,
    "main_depth_mm": 8500,
    "porch_width_mm": 750,
    "total_width_mm": 11400
  },
  
  "levels": {
    "ground": 0,
    "floor": 150,
    "ceiling": 3150,
    "ridge": 4872
  },
  
  "roof": {
    "type": "gable",
    "pitch_degrees": 25,
    "eave_overhang_mm": 700,
    "ridge_direction": "east_west"
  },
  
  "doors": [...],
  "windows": [...],
  
  "mep": {
    "electrical": {
      "fan_points": [...],
      "light_points": [...],
      "switches": [...],
      "power_points": [...]
    },
    "plumbing": {
      "fixtures": [...],
      "pipes": {...}
    }
  },
  
  "materials": {
    "floor": {"CT": [...], "CR": [...]},
    "wall": {"TB": [...], "CW": [...]},
    "ceiling": {"GB": [...]},
    "roof": {"MR": [...]}
  }
}
```

---

# 9. TOOL SELECTION SUMMARY

| Data Type | Primary Tool | Fallback |
|-----------|--------------|----------|
| Grid dimensions | Tesseract PSM 12 | Manual GridTruth |
| Text labels | pdfplumber | Tesseract PSM 6 |
| Door/window symbols | OpenCV template match | Placement rules |
| MEP symbols | OpenCV (legend templates) | OCR codes |
| Wall lines | OpenCV Hough lines | - |
| Roof outline | OpenCV contours | - |
| Level markers | Tesseract + regex | - |
| Material codes | Tesseract + regex | - |
| Schedule tables | pdfplumber tables | Tesseract PSM 6 |
| Pipe routes | OpenCV (diagram only) | - |

---

**Document Version:** 1.0  
**Companion to:** VECTOR_SEMANTIC_EXTRACTION_GUIDE.md  
**Source PDF:** TBLKTN_HOUSE.pdf (RUMAH RAKYAT, April 2024)
