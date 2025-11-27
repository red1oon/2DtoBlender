# 2D to Blender BIM - Project Framework v2.0

**Project:** PDF Architectural Drawing → Blender BIM Model  
**Architecture:** OCR (text) + GridTruth (dimensions) → Placement Rules → Coordinates  
**Validated:** 2025-11-26 via TBLKTN HOUSE POC  
**Status:** PRODUCTION READY

---

# PART I: PROJECT RULES

## Rule 0: Fix Source Code Only

**If output is wrong → fix SOURCE code, not output.**

- ✅ TEXT-ONLY algorithms (no image recognition, no ML/AI)
- ✅ Hardcoded parameters in source code
- ✅ Same input → same output (deterministic)
- ✅ GridTruth as single source of dimensional truth
- ❌ NO manual tweaking of extraction results
- ❌ NO AI-assisted cleanup of outputs

---

## Rule 1: GridTruth Authority

**CRITICAL: GridTruth.json is the ONLY source of dimensional data.**

OCR CANNOT extract graphical dimension lines. This was proven by POC:
- Text extraction works for labels, schedules, room names
- Dimension lines (3100mm, 3700mm, etc.) are graphical, not text
- GridTruth provides pre-verified dimensions from manual measurement

```
OCR extracts: Labels, schedules, room names  ✓
GridTruth provides: Grid dimensions           ✓
Placement Rules: Element positions            ✓
```

---

## Rule 2: Two-Tier Architecture

**TIER 1:** `master_reference_template.json` - What to search for  
**TIER 2:** `poc_pipeline.py` - How to extract and position

**Data Flow:**
```
PDF/ZIP → OCR Classifier → spatial.json (labels/schedules)
                              ↓
GridTruth.json ──────────→ Coordinate Mapper
                              ↓
                        coordinated.json (positioned elements)
```

---

## Rule 3: Validation Requirements

Every pipeline run MUST validate:

| Check | Requirement |
|-------|-------------|
| Grid complete | A-E and 1-5 all found |
| Door count | placed == schedule |
| Window count | placed == schedule |
| Coordinates | all within grid bounds |
| Envelope | closed loop |

---

## Rule 4: No Tools Outside Framework

**Forbidden:**
- ❌ PDF coordinate extraction for dimensions
- ❌ Post-processing scripts that bypass validation
- ❌ Manual coordinate entry

**Allowed:**
- ✅ Enhance poc_pipeline.py
- ✅ Add new placement rules
- ✅ Expand GridTruth for new buildings

---

# PART II: PIPELINE ARCHITECTURE

## Pipeline Overview

```
Stage 0: GridTruth Loading (dimensional truth)
   ↓
Stage 1A: Text Extraction (PDF/ZIP → raw tokens)
Stage 1B: Classification (cheat-sheet patterns)
Stage 1C: Schedule Parsing (door/window dimensions)
   ↓
Stage 2A: Building Envelope (4 exterior walls)
Stage 2B: Roof Structure (pitch + footprint)
   ↓
Stage 3A: Door Placement (schedule + rules)
Stage 3B: Window Placement (schedule + rules)
   ↓
Stage 4: Plumbing Fixtures (room-type conventions)
Stage 5: Furniture (room-type conventions)
   ↓
Stage 6: Validation (quantities, coordinates, closure)
```

---

## Stage 0: GridTruth Loading

**Input:** GridTruth_v3_VERIFIED.json (or building-specific GridTruth)

**Critical Data:**
```python
GRID_TRUTH = {
    "horizontal": {"A": 0.0, "B": 1.3, "C": 4.4, "D": 8.1, "E": 11.2},
    "vertical": {"1": 0.0, "2": 2.3, "3": 5.4, "4": 7.0, "5": 8.5},
    "setback": 0.75,
    "elevations": {
        "ground": 0.0, "floor": 0.15, "sill_low": 0.9,
        "sill_high": 1.5, "door_head": 2.1, "ceiling": 3.0
    }
}
```

**Room Bounds (derived from grid):**
```python
ROOM_BOUNDS = {
    "RUANG TAMU":  {"grid": "A1-C3", "x": (0.0, 4.4), "y": (0.0, 5.4)},
    "DAPUR":       {"grid": "C2-E4", "x": (4.4, 11.2), "y": (2.3, 7.0)},
    "BILIK UTAMA": {"grid": "D4-E5", "x": (8.1, 11.2), "y": (7.0, 8.5)},
    # ... etc
}
```

**Validation:**
- Grid spans calculated correctly (cumulative)
- Room bounds within grid extent
- Setback applied consistently

---

## Stage 1A: Text Extraction

**Input:** PDF file or pre-extracted ZIP archive

**Method:**
- If PDF: Use pdfplumber for text extraction
- If ZIP: Read .txt files directly (faster, proven reliable)

**Output:** Raw token list
```json
{"page": 1, "token": "D1", "classifications": [...]}
```

**Validation:** min 400 tokens across 8 pages

---

## Stage 1B: Classification

**Cheat-Sheet Patterns:**
```python
CHEAT_SHEET = {
    "grid_horizontal": ["A", "B", "C", "D", "E"],
    "grid_vertical": ["1", "2", "3", "4", "5"],
    "door_codes": ["D1", "D2", "D3"],
    "window_codes": ["W1", "W2", "W3", "W4"],
    "room_names": ["RUANG TAMU", "DAPUR", "BILIK UTAMA", ...],
    "markers": ["DISCHARGE", "FFL", "CEILING", ...],
    "plumbing": ["WC", "SINK", "BASIN", ...],
    "scale": "1:100"
}
```

**Output:** spatial.json with classified elements

**Validation:**
- Grid labels: A-E and 1-5 all found
- Door codes: D1, D2, D3 found
- Window codes: W1, W2, W3 found
- Rooms: ≥7 identified

---

## Stage 1C: Schedule Parsing

**Source:** Page 8 (schedule page) or full text search

**Pattern Matching:**
```python
# Door: CODE ... NNNmm X NNNmm
"D1.*?(\d{3,4})MM?\s*X\s*(\d{3,4})MM?"

# Window: CODE ... NNNmm X NNNmm  
"W1.*?(\d{3,4})mm?\s*X\s*(\d{3,4})mm?"
```

**Expected Output (TBLKTN HOUSE):**
```json
{
  "doors": {
    "D1": {"width": 900, "height": 2100, "qty": 2},
    "D2": {"width": 900, "height": 2100, "qty": 3},
    "D3": {"width": 750, "height": 2100, "qty": 2}
  },
  "windows": {
    "W1": {"width": 1800, "height": 1000, "qty": 1},
    "W2": {"width": 1200, "height": 1000, "qty": 4},
    "W3": {"width": 600, "height": 500, "qty": 2}
  }
}
```

---

## Stage 2A: Building Envelope

**Method:** Calculate from GridTruth bounds + setback

**Algorithm:**
```python
setback = GRID_TRUTH["setback"]  # 0.75m
max_x = GRID_TRUTH["horizontal"]["E"]  # 11.2m
max_y = GRID_TRUTH["vertical"]["5"]  # 8.5m

walls = [
    {"id": "WALL_SOUTH", "start": [setback, setback], "end": [max_x-setback, setback]},
    {"id": "WALL_EAST",  "start": [max_x-setback, setback], "end": [max_x-setback, max_y-setback]},
    {"id": "WALL_NORTH", "start": [max_x-setback, max_y-setback], "end": [setback, max_y-setback]},
    {"id": "WALL_WEST",  "start": [setback, max_y-setback], "end": [setback, setback]}
]
```

**Output:**
- 4 exterior wall segments
- Perimeter: 33.4m
- Area: 67.9 m²

**Validation:** closed_loop = true

---

## Stage 2B: Roof Structure

**Source:**
- Footprint: Building bounds + eave overhang (0.3m)
- Pitch: OCR extracted (25°)
- Base Z: GridTruth ceiling level (3.0m)

**Output:**
```json
{
  "type": "gable",
  "pitch_degrees": 25,
  "base_z": 3.0,
  "eave_overhang": 0.3,
  "ridge_direction": "east_west"
}
```

---

## Stage 3A: Door Placement

**Method:** Schedule dimensions + Placement Rules

**Placement Rules:**
```python
DOOR_PLACEMENT_RULES = {
    "D1": {  # Exterior doors
        "locations": [
            {"room": "RUANG TAMU", "wall": "SOUTH"},  # Main entrance
            {"room": "DAPUR", "wall": "EAST"}         # Service entrance
        ]
    },
    "D2": {  # Internal doors
        "locations": [
            {"room": "DAPUR", "wall": "WEST"},        # Living-kitchen
            {"room": "BILIK UTAMA", "wall": "SOUTH"}, # Master bedroom
            {"room": "BILIK 2", "wall": "SOUTH"}      # Bedroom 2
        ]
    },
    "D3": {  # Bathroom doors
        "locations": [
            {"room": "BILIK MANDI", "wall": "EAST"},
            {"room": "TANDAS", "wall": "EAST"}
        ]
    }
}
```

**Coordinate Calculation:**
```python
def get_wall_coordinate(room, wall):
    bounds = ROOM_BOUNDS[room]
    x_min, x_max = bounds["x"]
    y_min, y_max = bounds["y"]
    
    if wall == "SOUTH": return ((x_min+x_max)/2, y_min)
    if wall == "NORTH": return ((x_min+x_max)/2, y_max)
    if wall == "EAST":  return (x_max, (y_min+y_max)/2)
    if wall == "WEST":  return (x_min, (y_min+y_max)/2)
```

**Validation:** placed count == schedule qty (7 doors)

---

## Stage 3B: Window Placement

**Placement Rules:**
```python
WINDOW_PLACEMENT_RULES = {
    "W1": {"sill": 0.9, "locations": [{"room": "RUANG TAMU", "wall": "WEST"}]},
    "W2": {"sill": 0.9, "locations": [
        {"room": "RUANG TAMU", "wall": "SOUTH"},
        {"room": "BILIK UTAMA", "wall": "EAST"},
        {"room": "BILIK 2", "wall": "NORTH"},
        {"room": "DAPUR", "wall": "SOUTH"}
    ]},
    "W3": {"sill": 1.5, "locations": [  # High sill for privacy
        {"room": "TANDAS", "wall": "WEST"},
        {"room": "BILIK MANDI", "wall": "WEST"}
    ]}
}
```

**Validation:** placed count == schedule qty (7 windows)

---

## Stage 4: Plumbing Fixtures

**Room-Type Conventions:**
```python
PLUMBING_RULES = {
    "wc": {"rooms": ["TANDAS", "BILIK MANDI"], "position": "corner"},
    "basin": {"rooms": ["BILIK MANDI"], "position": "near_door"},
    "sink": {"rooms": ["DAPUR"], "position": "under_window"},
    "shower": {"rooms": ["BILIK MANDI"], "position": "corner_opposite_door"}
}
```

---

## Stage 5: Furniture

**Room-Type Conventions:**
```python
FURNITURE_RULES = {
    "bedroom": {
        "bed": {"position": "opposite_door_wall", "clearance": 0.6},
        "wardrobe": {"position": "perpendicular_to_bed", "clearance": 0.9}
    },
    "living_room": {
        "sofa": {"position": "facing_entrance", "clearance": 0.5}
    },
    "kitchen": {
        "base_cabinet": {"position": "along_walls", "height": 0.85},
        "wall_cabinet": {"position": "above_base", "z_offset": 1.4}
    }
}
```

---

## Stage 6: Validation

**Mandatory Checks:**
```python
validation = {
    "doors_placed": len(doors),
    "doors_expected": sum(schedule.doors.qty),
    "doors_match": doors_placed == doors_expected,
    
    "windows_placed": len(windows),
    "windows_expected": sum(schedule.windows.qty),
    "windows_match": windows_placed == windows_expected,
    
    "coordinate_errors": validate_all_within_grid(elements),
    "all_within_grid": len(coordinate_errors) == 0,
    
    "envelope_closed": is_closed_loop(walls)
}
```

**Pass Criteria:**
- doors_match: ✓
- windows_match: ✓
- all_within_grid: ✓
- envelope_closed: ✓

---

# PART III: FILE STRUCTURE

```
project/
├── GridTruth_v3_VERIFIED.json    # Dimensional truth (manual)
├── master_reference_template.json # Extraction instructions
├── poc_pipeline.py               # Main extraction code
│
├── input/
│   └── TBLKTN_HOUSE.pdf          # Source drawing (or .zip)
│
├── output/
│   ├── raw.json                  # Stage 1A output
│   ├── spatial.json              # Stage 1B output
│   └── coordinated.json          # Final output
│
└── validators/
    └── validate_coordinates.py   # Validation utilities
```

---

# PART IV: ADDING NEW BUILDINGS

## Step 1: Create GridTruth

Manually measure grid dimensions from PDF:
```json
{
  "horizontal": {"A": 0.0, "B": 1.5, "C": 4.8, ...},
  "vertical": {"1": 0.0, "2": 3.0, ...},
  "setback": 0.75,
  "elevations": {"floor": 0.15, "ceiling": 3.0, ...}
}
```

## Step 2: Define Room Bounds

Map rooms to grid cells:
```json
{
  "LIVING": {"grid": "A1-C3", "x": [0.0, 4.8], "y": [0.0, 6.0]},
  ...
}
```

## Step 3: Define Placement Rules

Add building-specific door/window placements:
```python
DOOR_PLACEMENT_RULES = {
    "D1": {"locations": [{"room": "LIVING", "wall": "SOUTH"}]},
    ...
}
```

## Step 4: Run Pipeline

```bash
python3 poc_pipeline.py input/NEW_BUILDING.pdf
```

## Step 5: Validate Output

Check coordinated.json validation block:
- All counts match schedules
- All coordinates within grid
- Envelope closed

---

# PART V: SUCCESS METRICS

**POC Achieved (TBLKTN HOUSE):**

| Metric | Target | Achieved |
|--------|--------|----------|
| Door count | 7 | 7 ✓ |
| Window count | 7 | 7 ✓ |
| Coordinates valid | 100% | 100% ✓ |
| Envelope closed | Yes | Yes ✓ |
| Building area | ~68 m² | 67.9 m² ✓ |

**Production Target:**
- Position accuracy: 98% (<10cm error)
- Schedule match: 100%
- Coordinate validity: 100%

---

# PART VI: TROUBLESHOOTING

## Issue: Grid labels not found
**Cause:** PDF text extraction failed  
**Fix:** Check if PDF is actually ZIP archive (pre-processed)

## Issue: Schedule not parsed
**Cause:** Schedule on unexpected page  
**Fix:** Search full text instead of page 8 only

## Issue: Coordinates outside grid
**Cause:** Room bounds incorrect  
**Fix:** Verify ROOM_BOUNDS against GridTruth

## Issue: Count mismatch
**Cause:** Placement rules incomplete  
**Fix:** Add missing location rules for element type

---

**Document Status:** v2.0 PRODUCTION READY  
**Last Updated:** 2025-11-26  
**Validated By:** POC pipeline on TBLKTN HOUSE
