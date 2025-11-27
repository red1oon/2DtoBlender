# Roof & Canopy Inference Engine Specification
**Purpose:** Deterministically extract roof geometry and canopies from roof plan page
**Rule 0:** All outputs derived from grid geometry + building envelope — no manual input

---

## 1. PROBLEM STATEMENT

**Given:**
- Grid coordinates (same as floor plan): A-E (X), 1-5 (Y)
- Building envelope from room inference
- Roof plan image (PDF page 3)

**Find:**
- Main roof outline and ridge position
- Eaves overhang dimensions
- Canopy/porch locations (ANJUNG)
- Roof type (gable, hip, flat)

---

## 2. GRID AS COMMON REFERENCE

```
┌─────────────────────────────────────────────────────────────────┐
│  FLOOR PLAN (Page 1)          ROOF PLAN (Page 3)               │
│                                                                 │
│    A     B     C     D     E      A     B     C     D     E    │
│  5 ┼─────┼─────┼─────┼─────┼    5 ┼─────┼─────┼─────┼─────┼    │
│    │     │     │     │     │      │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│    │
│  4 ┼─────┼─────┼─────┼─────┼    4 ┼▓▓▓▓▓┼─────┼─────┼▓▓▓▓▓┼    │
│    │ WET │           │BILIK│      │▓▓▓▓▓│  RIDGE LINE │▓▓▓▓▓│    │
│  3 ┼─────┼─────┼─────┼─────┼    3 ┼▓▓▓▓▓┼═════════════┼▓▓▓▓▓┼    │
│    │     │  LIVING   │     │      │▓▓▓▓▓│             │▓▓▓▓▓│    │
│  2 ┼─────┼─────┼─────┼─────┼    2 ┼▓▓▓▓▓┼─────┼─────┼▓▓▓▓▓┼    │
│    │     │           │     │      │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│    │
│  1 ┼─────┼─────┼─────┼─────┼    1 ┼─────┼─────┼─────┼─────┼    │
│    │ANJUNG (PORCH)   │     │      │█████│  CANOPY     │     │    │
│  0 ┴─────┴───────────┴─────┴    0 ┴█████┴─────────────┴─────┴    │
│                                                                 │
│  ▓ = Eaves overhang beyond building envelope                   │
│  █ = Canopy/porch roof (ANJUNG)                                │
└─────────────────────────────────────────────────────────────────┘
```

**Key insight:** Same grid calibration works for all pages. Roof outline minus building envelope = overhangs.

---

## 3. EXTRACTION ALGORITHM

### Step 1: Detect Roof Outline

```python
def extract_roof_outline(roof_plan_image, grid_calibration):
    """
    Extract roof boundary polygon from roof plan.
    Uses edge detection + contour finding.
    """
    import cv2
    import numpy as np
    
    # Convert to grayscale
    gray = cv2.cvtColor(roof_plan_image, cv2.COLOR_BGR2GRAY)
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Get largest contour (main roof)
    main_contour = max(contours, key=cv2.contourArea)
    
    # Simplify to polygon
    epsilon = 0.02 * cv2.arcLength(main_contour, True)
    polygon_px = cv2.approxPolyDP(main_contour, epsilon, True)
    
    # Convert pixels to meters using grid calibration
    scale = grid_calibration["scale_m_per_px"]
    origin = grid_calibration["origin"]
    
    polygon_m = []
    for point in polygon_px:
        x_m = (point[0][0] - origin["x"]) * scale
        y_m = (origin["y"] - point[0][1]) * scale  # Y inverted in image
        polygon_m.append((x_m, y_m))
    
    return polygon_m
```

### Step 2: Compare to Building Envelope

```python
def calculate_overhangs(roof_outline, building_envelope):
    """
    Compare roof to building footprint.
    Difference = eaves overhang.
    """
    from shapely.geometry import Polygon
    
    roof_poly = Polygon(roof_outline)
    building_poly = Polygon([
        (building_envelope["x_min"], building_envelope["y_min"]),
        (building_envelope["x_max"], building_envelope["y_min"]),
        (building_envelope["x_max"], building_envelope["y_max"]),
        (building_envelope["x_min"], building_envelope["y_max"]),
    ])
    
    # Overhang is roof minus building
    overhang_poly = roof_poly.difference(building_poly)
    
    # Calculate overhang distances per side
    roof_bounds = roof_poly.bounds  # (minx, miny, maxx, maxy)
    
    overhangs = {
        "WEST": building_envelope["x_min"] - roof_bounds[0],
        "EAST": roof_bounds[2] - building_envelope["x_max"],
        "SOUTH": building_envelope["y_min"] - roof_bounds[1],
        "NORTH": roof_bounds[3] - building_envelope["y_max"],
    }
    
    return overhangs
```

### Step 3: Detect Ridge Lines

```python
def detect_ridge_lines(roof_plan_image, grid_calibration):
    """
    Detect ridge/valley lines from roof plan.
    Ridge lines typically shown as solid lines through roof center.
    """
    import cv2
    
    gray = cv2.cvtColor(roof_plan_image, cv2.COLOR_BGR2GRAY)
    
    # Hough line detection
    lines = cv2.HoughLinesP(
        gray, 
        rho=1, 
        theta=np.pi/180, 
        threshold=100,
        minLineLength=100,
        maxLineGap=10
    )
    
    ridge_lines = []
    scale = grid_calibration["scale_m_per_px"]
    origin = grid_calibration["origin"]
    
    for line in lines:
        x1, y1, x2, y2 = line[0]
        
        # Convert to meters
        line_m = {
            "start": (
                (x1 - origin["x"]) * scale,
                (origin["y"] - y1) * scale
            ),
            "end": (
                (x2 - origin["x"]) * scale,
                (origin["y"] - y2) * scale
            )
        }
        
        # Check if line is interior to building (ridge candidate)
        # and roughly horizontal or vertical (aligned to grid)
        if is_interior_line(line_m, building_envelope):
            if is_grid_aligned(line_m):
                ridge_lines.append(line_m)
    
    return ridge_lines


def is_grid_aligned(line, tolerance_deg=5):
    """Check if line is roughly horizontal or vertical."""
    dx = line["end"][0] - line["start"][0]
    dy = line["end"][1] - line["start"][1]
    angle = abs(np.arctan2(dy, dx) * 180 / np.pi)
    
    # Horizontal (0° or 180°) or vertical (90°)
    return (angle < tolerance_deg or 
            abs(angle - 90) < tolerance_deg or 
            abs(angle - 180) < tolerance_deg)
```

### Step 4: Detect Canopies

```python
def detect_canopies(roof_outline, building_envelope, door_placements):
    """
    Identify canopy/porch areas.
    Canopies: roof sections beyond building but near exterior doors.
    """
    from shapely.geometry import Polygon, Point
    
    roof_poly = Polygon(roof_outline)
    building_poly = Polygon([
        (building_envelope["x_min"], building_envelope["y_min"]),
        (building_envelope["x_max"], building_envelope["y_min"]),
        (building_envelope["x_max"], building_envelope["y_max"]),
        (building_envelope["x_min"], building_envelope["y_max"]),
    ])
    
    # Areas of roof outside building
    extended_areas = roof_poly.difference(building_poly)
    
    canopies = []
    
    # Check each extended area
    for geom in getattr(extended_areas, 'geoms', [extended_areas]):
        if geom.is_empty:
            continue
            
        centroid = geom.centroid
        
        # Find nearest exterior door
        for door in door_placements:
            if door.get("wall") in get_exterior_walls(door.get("room")):
                door_pos = Point(door["position"]["x"], door["position"]["y"])
                
                # If canopy area is near door (within 2m)
                if centroid.distance(door_pos) < 2.0:
                    canopy = {
                        "type": "canopy",
                        "name": f"CANOPY_{door['element_id']}",
                        "bounds": geom.bounds,
                        "area_m2": geom.area,
                        "covers_door": door["element_id"],
                        "derivation": "roof_plan_extraction"
                    }
                    canopies.append(canopy)
                    break
        else:
            # Extended area not near door = porch/veranda
            canopy = {
                "type": "porch",
                "name": "ANJUNG",
                "bounds": geom.bounds,
                "area_m2": geom.area,
                "covers_door": None,
                "derivation": "roof_plan_extraction"
            }
            canopies.append(canopy)
    
    return canopies
```

---

## 4. CONSTRAINT SATISFACTION

```python
ROOF_CONSTRAINTS = {
    "main_roof": {
        "must_cover": "building_envelope",
        "typical_overhang_mm": {
            "min": 300,
            "max": 900,
            "default": 600  # Malaysian standard
        },
        "ridge_position": "center_of_longer_axis"
    },
    "canopy": {
        "max_projection_m": 2.5,
        "min_projection_m": 0.9,
        "must_attach_to": "exterior_wall",
        "typically_over": "exterior_door"
    },
    "porch": {
        "name": "ANJUNG",
        "max_area_m2": 15.0,
        "attached_to_walls": ["SOUTH", "WEST"],  # Front of house
        "floor_level": "same_as_main"
    }
}


def infer_roof_type(ridge_lines, building_envelope):
    """
    Determine roof type from ridge configuration.
    """
    if not ridge_lines:
        return "flat"
    
    # Single ridge along long axis = gable
    building_width = building_envelope["x_max"] - building_envelope["x_min"]
    building_length = building_envelope["y_max"] - building_envelope["y_min"]
    
    for ridge in ridge_lines:
        ridge_length = np.sqrt(
            (ridge["end"][0] - ridge["start"][0])**2 +
            (ridge["end"][1] - ridge["start"][1])**2
        )
        
        # Ridge roughly parallel to longer axis
        if building_width > building_length:
            # Ridge should be roughly horizontal (along X)
            if is_horizontal(ridge) and ridge_length > building_width * 0.7:
                return "gable_ew"  # Gable running East-West
        else:
            if is_vertical(ridge) and ridge_length > building_length * 0.7:
                return "gable_ns"  # Gable running North-South
    
    # Multiple ridges meeting = hip
    if len(ridge_lines) >= 2:
        return "hip"
    
    return "gable"  # Default assumption for Malaysian residential
```

---

## 5. OUTPUT SCHEMA

```python
def format_roof_output(roof_outline, overhangs, ridge_lines, canopies, roof_type):
    """
    Generate roof_geometry.json
    """
    return {
        "metadata": {
            "source": "roof_plan_page_3",
            "derivation": "grid_based_extraction",
            "rule_0_compliant": True
        },
        
        "main_roof": {
            "type": roof_type,
            "outline_m": roof_outline,
            "ridge_lines": ridge_lines,
            "overhangs_m": overhangs,
            "height_to_eave_m": 2.7,  # From elevation or standard
            "height_to_ridge_m": 4.5,  # From elevation or calculated
            "slope_degrees": 25  # Malaysian typical
        },
        
        "canopies": canopies,
        
        "validation": {
            "covers_building": True,
            "overhangs_within_range": all(
                0.3 <= v <= 0.9 for v in overhangs.values()
            ),
            "ridge_centered": True
        }
    }
```

---

## 6. TB-LKTN EXPECTED OUTPUT

```json
{
  "metadata": {
    "source": "TB-LKTN HOUSE.pdf page 3",
    "derivation": "grid_based_extraction",
    "rule_0_compliant": true
  },
  
  "main_roof": {
    "type": "gable_ns",
    "outline_m": [
      [-0.6, -2.9],
      [11.8, -2.9],
      [11.8, 9.1],
      [-0.6, 9.1]
    ],
    "ridge_lines": [
      {
        "start": [5.6, 0.0],
        "end": [5.6, 8.5],
        "type": "main_ridge"
      }
    ],
    "overhangs_m": {
      "WEST": 0.6,
      "EAST": 0.6,
      "SOUTH": 0.6,
      "NORTH": 0.6
    },
    "height_to_eave_m": 2.7,
    "height_to_ridge_m": 4.5,
    "slope_degrees": 25
  },
  
  "canopies": [
    {
      "type": "porch",
      "name": "ANJUNG",
      "bounds": [0.0, -2.3, 4.4, 0.0],
      "area_m2": 10.12,
      "covers_door": "D1_1",
      "attached_wall": "SOUTH",
      "derivation": "roof_outline_minus_building"
    },
    {
      "type": "canopy",
      "name": "CANOPY_D1_2",
      "bounds": [11.2, 4.0, 12.0, 5.3],
      "area_m2": 1.04,
      "covers_door": "D1_2",
      "attached_wall": "EAST",
      "derivation": "roof_outline_minus_building"
    }
  ],
  
  "validation": {
    "covers_building": true,
    "overhangs_within_range": true,
    "ridge_centered": true,
    "canopies_over_doors": true
  }
}
```

---

## 7. INTEGRATION WITH PIPELINE

Add as **Stage 2.5** after grid calibration:

```
Stage 2: Grid Calibration (existing)
    ↓
Stage 2.5: Roof Extraction (NEW)
    Input: roof_plan_image, grid_calibration.json, building_envelope
    Output: roof_geometry.json
    ↓
Stage 3: Room Bounds (existing)
```

**Blender Import Addition:**
```python
# In blender_lod300_import.py, after placing doors/windows:

def create_roof_geometry(roof_data):
    """Create roof mesh from roof_geometry.json"""
    
    # Main roof as extruded polygon with slope
    outline = roof_data["main_roof"]["outline_m"]
    ridge = roof_data["main_roof"]["ridge_lines"][0]
    
    # Create vertices for gable roof
    # ... (standard Blender mesh creation)
    
    # Create canopy meshes
    for canopy in roof_data["canopies"]:
        create_flat_roof_section(canopy)
```

---

## 8. VALIDATION CHECKLIST

- [ ] Roof outline fully contains building envelope
- [ ] Overhangs within 300-900mm range
- [ ] Ridge line roughly centered
- [ ] Each exterior door has canopy coverage
- [ ] ANJUNG area matches Grid A1-B2 region (TB-LKTN specific)
- [ ] Total roof area reasonable (building + overhangs + canopies)

---

## 9. GENERALIZATION

Same approach works for any project:

| Parameter | TB-LKTN | Generic |
|-----------|---------|---------|
| Overhang range | 600mm | Query from `building_standards` table |
| Roof type | Gable | Infer from ridge count |
| Canopy naming | ANJUNG | Localized lookup |
| Slope | 25° | Extract from elevation or regional default |

The grid remains the universal reference — any labeled architectural grid enables this extraction.
