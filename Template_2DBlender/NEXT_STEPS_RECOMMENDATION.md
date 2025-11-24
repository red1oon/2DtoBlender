# Next Steps Recommendation - Phase 2 to Blender

**Date:** 2025-11-24
**Current Status:** Phase 2 Complete (95% wall accuracy)
**Critical Gap:** Openings not assigned to walls

---

## 🎯 **THE CRITICAL GAP**

### **What We Have:**
```json
// Doors with XY positions (floating in space)
{
  "door_type": "D1",
  "position": [6.75, 5.74, 0.0],
  "width": 0.9,
  "height": 2.1
}

// Walls with start/end coordinates
{
  "wall_id": "candidate_27",
  "start_point": [11.5, 8.1, 0.0],
  "end_point": [14.5, 8.1, 0.0]
}
```

### **What's Missing:**
```json
// Doors need to know WHICH WALL they belong to
{
  "door_type": "D1",
  "position": [6.75, 5.74, 0.0],
  "wall_id": "candidate_27",        // ❌ MISSING
  "position_on_wall": 0.42,         // ❌ MISSING (42% along wall)
  "orientation": 90                 // ❌ MISSING (swing direction)
}
```

### **Impact in Blender:**
Without wall assignment:
- ❌ Doors/windows float in air at XY coordinates
- ❌ Cannot create openings in walls
- ❌ No parametric wall-opening relationship

With wall assignment:
- ✅ Doors/windows embedded in walls
- ✅ Can use Boolean operations in Blender
- ✅ Parametric: move wall → openings follow

---

## 📋 **THREE OPTIONS**

### **Option 1: Quick Blender Export (1-2 hours)** ⭐ RECOMMENDED

**What to do:**
1. **Opening-to-Wall Assignment** (1 hour)
   - Find nearest wall for each door/window
   - Calculate position along wall (0.0 → 1.0 parameter)

2. **Simple Blender Export** (1 hour)
   - Export 14 walls as boxes
   - Export 17 openings embedded in walls
   - Add parametric floor slab (27.7m × 19.7m)

**Code to write:**
```python
# Add to extraction_engine.py
class OpeningWallAssigner:
    def assign_openings_to_walls(self, walls, doors, windows):
        """
        For each opening, find nearest wall and calculate position on wall
        """
        for door in doors:
            # Find closest wall
            nearest_wall, min_distance = None, float('inf')
            for wall in walls:
                dist = point_to_line_distance(
                    door['position'],
                    wall['start_point'],
                    wall['end_point']
                )
                if dist < min_distance:
                    min_distance = dist
                    nearest_wall = wall

            # Calculate parametric position (0.0 to 1.0 along wall)
            wall_vector = (
                nearest_wall['end_point'][0] - nearest_wall['start_point'][0],
                nearest_wall['end_point'][1] - nearest_wall['start_point'][1]
            )
            door_vector = (
                door['position'][0] - nearest_wall['start_point'][0],
                door['position'][1] - nearest_wall['start_point'][1]
            )
            wall_length = math.sqrt(wall_vector[0]**2 + wall_vector[1]**2)
            projection = (
                door_vector[0] * wall_vector[0] +
                door_vector[1] * wall_vector[1]
            ) / wall_length
            position_on_wall = projection / wall_length

            # Assign to door
            door['wall_id'] = nearest_wall['wall_id']
            door['position_on_wall'] = position_on_wall
            door['distance_to_wall'] = min_distance

        return doors, windows

# Create new test_export_to_blender.py
def export_phase2_to_blender():
    # Load phase2_complete_results.json
    results = json.load(open('output_artifacts/phase2_complete_results.json'))

    # Assign openings to walls
    assigner = OpeningWallAssigner()
    doors, windows = assigner.assign_openings_to_walls(
        results['final_walls']['internal_walls'] + results['final_walls']['outer_walls'],
        results['openings']['doors'],
        results['openings']['windows']
    )

    # Export to Blender
    # ... create walls with embedded openings
```

**Result:**
- ✅ See your TB-LKTN house in Blender TODAY
- ✅ 14 walls with 17 embedded openings
- ✅ Complete building footprint
- ⚠️ All openings at Z=0 (floor level - doors OK, windows wrong)
- ⚠️ No roof (can add parametric roof later)

**Time:** 2 hours
**Value:** HIGH - immediate 3D visualization

---

### **Option 2: Hardening Phase 2 (4-6 hours)**

**What "Hardening" Means:**

#### **1. Error Handling**
```python
# Current: Assumes schedule table always exists
tables = page.extract_tables()
door_schedule = tables[0]  # ❌ Crashes if no tables found

# Hardened: Graceful fallback
tables = page.extract_tables()
if not tables or len(tables) == 0:
    print("⚠️  No schedule tables found, using defaults")
    door_schedule = {
        'D1': {'width': 0.9, 'height': 2.1, 'quantity': 1},
        'D2': {'width': 0.9, 'height': 2.1, 'quantity': 1},
        'D3': {'width': 0.75, 'height': 2.1, 'quantity': 1}
    }
else:
    door_schedule = extract_from_table(tables[0])
```

#### **2. Validation**
```python
# Validate wall geometry
def validate_wall(wall):
    if wall['length'] < 0.5:
        raise ValueError(f"Wall {wall['wall_id']} too short: {wall['length']}m")
    if wall['thickness'] < 0.05 or wall['thickness'] > 0.5:
        raise ValueError(f"Wall {wall['wall_id']} invalid thickness: {wall['thickness']}m")
    if wall['start_point'] == wall['end_point']:
        raise ValueError(f"Wall {wall['wall_id']} has zero length")

# Validate opening positions
def validate_opening(opening, building_bounds):
    x, y, z = opening['position']
    if x < 0 or x > building_bounds['width']:
        raise ValueError(f"Opening {opening['door_type']} outside building (X={x})")
    if y < 0 or y > building_bounds['length']:
        raise ValueError(f"Opening {opening['door_type']} outside building (Y={y})")
```

#### **3. Robust Duplicate Detection**
```python
# Current: Simple tolerance-based
if abs(wall1['start'][0] - wall2['start'][0]) < 0.1:
    # Duplicate

# Hardened: Multiple criteria
def is_duplicate_wall(wall1, wall2, tolerance=0.1):
    # Check both start→start + end→end AND start→end + end→start
    case1 = (
        point_distance(wall1['start'], wall2['start']) < tolerance and
        point_distance(wall1['end'], wall2['end']) < tolerance
    )
    case2 = (
        point_distance(wall1['start'], wall2['end']) < tolerance and
        point_distance(wall1['end'], wall2['start']) < tolerance
    )
    return case1 or case2
```

#### **4. Confidence Scoring Improvements**
```python
# Add more validation criteria
def calculate_wall_confidence(wall, context):
    scores = []

    # Connection score (existing)
    scores.append(connection_score * 0.4)

    # Opening proximity (existing)
    scores.append(opening_score * 0.3)

    # NEW: Room boundary score
    if wall_forms_room_boundary(wall, context['rooms']):
        scores.append(1.0 * 0.2)
    else:
        scores.append(0.0 * 0.2)

    # NEW: Parallelism to outer walls
    if parallel_to_outer_wall(wall, context['outer_walls']):
        scores.append(1.0 * 0.1)
    else:
        scores.append(0.5 * 0.1)

    return sum(scores)
```

**Result:**
- ✅ Robust to PDF variations (missing tables, malformed data)
- ✅ Better error messages
- ✅ Higher confidence in extracted data
- ⚠️ Still doesn't get you to Blender visualization

**Time:** 4-6 hours
**Value:** MEDIUM - makes system more production-ready

---

### **Option 3: Phase 1D - Elevation Data Extraction (1 week)**

**What "Regex" Would Be For:**

#### **1. Dimension Text Parsing**
```python
# Extract heights from elevation views (Page 3-4)
DIMENSION_PATTERNS = {
    # Floor level: "FFL +0.150" or "FLOOR LEVEL +150mm"
    r'FFL\s*\+\s*(\d+\.?\d*)\s*m?m?': 'floor_level',
    r'FLOOR\s+LEVEL\s*\+?\s*(\d+\.?\d*)\s*m?m?': 'floor_level',

    # Lintel level: "LINTEL LEVEL 2100mm" or "LINTEL +2.1m"
    r'LINTEL.*?(\d+\.?\d*)\s*mm': lambda x: float(x)/1000,  # Convert mm → m
    r'LINTEL.*?(\d+\.?\d*)\s*m(?!m)': 'lintel_height',

    # Ceiling height: "CEILING LEVEL 3000mm"
    r'CEILING.*?(\d+\.?\d*)\s*mm': lambda x: float(x)/1000,
    r'CEILING.*?(\d+\.?\d*)\s*m(?!m)': 'ceiling_height',

    # Window sill: "SILL 1000mm" or "W/S +1.0m"
    r'SILL.*?(\d+\.?\d*)\s*mm': lambda x: float(x)/1000,
    r'W/?S.*?(\d+\.?\d*)\s*m(?!m)': 'window_sill'
}

def extract_elevations(pdf, page_number=2):
    page = pdf.pages[page_number]
    words = page.extract_words()
    text = ' '.join([w['text'] for w in words])

    elevations = {}
    for pattern, label in DIMENSION_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            # Convert mm to m if needed
            if callable(label):
                value = label(value)
                label = match.lastgroup or 'unknown'
            elevations[label] = value

    return elevations

# Example output:
{
  'floor_level': 0.15,    # FFL +0.150m
  'lintel_height': 2.1,   # LINTEL LEVEL 2100mm
  'ceiling_height': 3.0,  # CEILING LEVEL 3000mm
  'window_sill': 1.0      # SILL 1000mm
}
```

#### **2. Room Label Extraction (Malay Text)**
```python
# Extract room labels from floor plan (Page 1)
MALAYSIAN_ROOM_PATTERNS = {
    # Bedroom
    r'BILIK\s*TIDUR\s*(\d+)': lambda m: f'bedroom_{m.group(1)}',
    r'B\.TIDUR\s*(\d+)': lambda m: f'bedroom_{m.group(1)}',

    # Bathroom
    r'BILIK\s*AIR\s*(\d+)': lambda m: f'bathroom_{m.group(1)}',
    r'B\.AIR\s*(\d+)': lambda m: f'bathroom_{m.group(1)}',
    r'TANDAS': 'toilet',

    # Kitchen
    r'DAPUR': 'kitchen',

    # Living areas
    r'RUANG\s*TAMU': 'living_room',
    r'RUANG\s*MAKAN': 'dining_room',
    r'R\.TAMU': 'living_room',
    r'R\.MAKAN': 'dining_room',

    # Utility
    r'STOR': 'storage',
    r'CUCIAN': 'laundry'
}

def extract_room_labels(page):
    words = page.extract_words()
    rooms = []

    for word in words:
        text = word['text'].upper()

        for pattern, room_type in MALAYSIAN_ROOM_PATTERNS.items():
            match = re.search(pattern, text)
            if match:
                if callable(room_type):
                    room_name = room_type(match)
                else:
                    room_name = room_type

                rooms.append({
                    'name': word['text'],  # Original Malay text
                    'type': room_name,     # Standardized English type
                    'position': (word['x0'], word['top']),
                    'confidence': 90
                })

    return rooms

# Example output:
[
  {'name': 'BILIK TIDUR 1', 'type': 'bedroom_1', 'position': (100, 200)},
  {'name': 'TANDAS', 'type': 'toilet', 'position': (150, 250)},
  {'name': 'DAPUR', 'type': 'kitchen', 'position': (200, 180)}
]
```

**Implementation Plan:**
1. **Day 1-2:** Elevation extraction (regex patterns)
2. **Day 3:** Room label extraction (Malay patterns)
3. **Day 4:** Window sill height inference
4. **Day 5:** Integration with Phase 2 data
5. **Day 6-7:** Testing and validation

**Result:**
- ✅ Accurate ceiling heights (3.0m, 2.7m, etc.)
- ✅ Window sill heights (1.0m, 1.5m)
- ✅ Room classification (bedroom, bathroom, kitchen)
- ✅ Ready for accurate Blender export

**Time:** 1 week
**Value:** HIGH - complete accurate model, but delayed gratification

---

## 🎯 **MY RECOMMENDATION**

### **Go with Option 1 (Quick Blender Export)**

**Why:**
1. ✅ **2 hours work** vs 1 week for Option 3
2. ✅ **See results in Blender TODAY**
3. ✅ **Validates all Phase 2 work** in 3D
4. ✅ **Foundation for Phase 1D** - can enhance heights later
5. ✅ **Immediate client value** - 3D visualization

**Then follow up with:**
- Option 2 (Hardening) - Make system robust
- Option 3 (Phase 1D) - Add elevation data for accuracy

**Implementation Order:**
```
TODAY (2 hours):
├── Opening-to-wall assignment
├── Simple Blender export
└── Validate in Blender viewport

THIS WEEK (4-6 hours):
├── Hardening (error handling)
├── Validation improvements
└── Robust duplicate detection

NEXT WEEK (1 week):
├── Elevation data extraction (regex)
├── Room label extraction (Malay patterns)
└── Complete Phase 1D
```

---

## 📝 **OPTION 1 - DETAILED IMPLEMENTATION**

### **File 1: Enhanced extraction_engine.py** (30 min)

Add `OpeningWallAssigner` class:
```python
class OpeningWallAssigner:
    """Assign doors/windows to nearest walls"""

    def __init__(self, walls):
        self.walls = walls

    def assign_openings_to_walls(self, doors, windows):
        """Find nearest wall for each opening"""
        for opening in doors + windows:
            self._assign_to_wall(opening)
        return doors, windows

    def _assign_to_wall(self, opening):
        """Find nearest wall and calculate position on wall"""
        min_distance = float('inf')
        nearest_wall = None
        position_on_wall = 0.0

        for wall in self.walls:
            # Calculate distance from opening to wall line
            distance, param = self._point_to_line_distance(
                opening['position'],
                wall['start_point'],
                wall['end_point']
            )

            if distance < min_distance:
                min_distance = distance
                nearest_wall = wall
                position_on_wall = param

        # Assign to opening
        opening['wall_id'] = nearest_wall['wall_id']
        opening['position_on_wall'] = position_on_wall
        opening['distance_to_wall'] = min_distance

    def _point_to_line_distance(self, point, line_start, line_end):
        """
        Calculate perpendicular distance from point to line segment
        Returns: (distance, parameter) where parameter is 0.0→1.0 along line
        """
        px, py = point[0], point[1]
        x1, y1 = line_start[0], line_start[1]
        x2, y2 = line_end[0], line_end[1]

        # Line vector
        dx = x2 - x1
        dy = y2 - y1
        line_length_sq = dx*dx + dy*dy

        if line_length_sq == 0:
            # Line is a point
            distance = math.sqrt((px-x1)**2 + (py-y1)**2)
            return distance, 0.0

        # Project point onto line
        t = max(0, min(1, ((px-x1)*dx + (py-y1)*dy) / line_length_sq))

        # Closest point on line
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        # Distance
        distance = math.sqrt((px-closest_x)**2 + (py-closest_y)**2)

        return distance, t
```

### **File 2: export_phase2_to_blender.py** (1 hour)

```python
#!/usr/bin/env python3
"""
Export Phase 2 results to Blender
- Loads phase2_complete_results.json
- Assigns openings to walls
- Creates Blender .blend file
"""

import json
import sys
sys.path.append('/home/red1/blender-4.2.14/4.2/python/lib/python3.11/site-packages')

import bpy
from mathutils import Vector
from extraction_engine import OpeningWallAssigner


def load_phase2_results(json_path):
    with open(json_path, 'r') as f:
        return json.load(f)


def create_wall_with_opening(wall, openings):
    """
    Create wall mesh with Boolean subtraction for openings
    """
    # Create wall box
    wall_length = wall['length']
    wall_height = wall['height']
    wall_thickness = wall['thickness']

    # Create mesh
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    wall_obj = bpy.context.active_object
    wall_obj.name = wall['wall_id']

    # Scale to wall dimensions
    wall_obj.scale = (wall_length/2, wall_thickness/2, wall_height/2)

    # Position at wall midpoint
    mid_x = (wall['start_point'][0] + wall['end_point'][0]) / 2
    mid_y = (wall['start_point'][1] + wall['end_point'][1]) / 2
    wall_obj.location = Vector((mid_x, mid_y, wall_height/2))

    # Rotate if vertical wall
    if abs(wall['angle'] - 90) < 5:
        wall_obj.rotation_euler[2] = math.radians(90)

    # Create openings as Boolean cutters
    for opening in openings:
        if opening.get('wall_id') == wall['wall_id']:
            # Create opening box
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            opening_obj = bpy.context.active_object
            opening_obj.name = f"{opening['door_type']}_cutter"

            # Scale to opening dimensions
            opening_obj.scale = (
                opening['width']/2,
                wall_thickness,  # Extend through wall
                opening['height']/2
            )

            # Position on wall
            position_x = (
                wall['start_point'][0] +
                opening['position_on_wall'] * (wall['end_point'][0] - wall['start_point'][0])
            )
            position_y = (
                wall['start_point'][1] +
                opening['position_on_wall'] * (wall['end_point'][1] - wall['start_point'][1])
            )
            opening_obj.location = Vector((
                position_x,
                position_y,
                opening['height']/2  # Bottom of opening at floor level
            ))

            # Add Boolean modifier to wall
            mod = wall_obj.modifiers.new(name=f"Boolean_{opening['door_type']}", type='BOOLEAN')
            mod.operation = 'DIFFERENCE'
            mod.object = opening_obj

            # Hide cutter
            opening_obj.hide_render = True
            opening_obj.hide_viewport = True

    return wall_obj


def export_to_blender(results_path, output_blend_path):
    """Main export function"""
    print("="*60)
    print("PHASE 2 BLENDER EXPORT")
    print("="*60)

    # Load results
    print(f"\n✅ Loading: {results_path}")
    results = load_phase2_results(results_path)

    # Clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Assign openings to walls
    print(f"\n✅ Assigning {len(results['openings']['doors'])} doors to walls...")
    print(f"✅ Assigning {len(results['openings']['windows'])} windows to walls...")

    all_walls = results['final_walls']['outer_walls'] + results['final_walls']['internal_walls']
    assigner = OpeningWallAssigner(all_walls)

    doors, windows = assigner.assign_openings_to_walls(
        results['openings']['doors'],
        results['openings']['windows']
    )

    # Create walls
    print(f"\n✅ Creating {len(all_walls)} walls in Blender...")
    for wall in all_walls:
        wall_obj = create_wall_with_opening(wall, doors + windows)
        print(f"   • {wall['wall_id']}: {wall['length']:.2f}m")

    # Create floor slab
    print(f"\n✅ Creating floor slab...")
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    floor = bpy.context.active_object
    floor.name = "Floor_Slab"
    floor.scale = (27.7/2, 19.7/2, 0.15/2)
    floor.location = Vector((27.7/2, 19.7/2, -0.15/2))

    # Save
    print(f"\n✅ Saving to: {output_blend_path}")
    bpy.ops.wm.save_as_mainfile(filepath=output_blend_path)

    # Summary
    print("\n" + "="*60)
    print("EXPORT COMPLETE")
    print("="*60)
    print(f"✅ Walls: {len(all_walls)}")
    print(f"✅ Doors: {len(doors)}")
    print(f"✅ Windows: {len(windows)}")
    print(f"✅ Floor: 1")
    print(f"\n📁 Open in Blender: {output_blend_path}")
    print("="*60)


if __name__ == "__main__":
    results_path = "output_artifacts/phase2_complete_results.json"
    output_blend_path = "output_artifacts/TB_LKTN_Phase2.blend"

    export_to_blender(results_path, output_blend_path)
```

### **File 3: test_opening_assignment.py** (30 min)

Quick test before Blender export:
```python
#!/usr/bin/env python3
"""Test opening-to-wall assignment"""

import json
from extraction_engine import OpeningWallAssigner

# Load Phase 2 results
with open('output_artifacts/phase2_complete_results.json', 'r') as f:
    results = json.load(f)

# Get all walls
all_walls = results['final_walls']['outer_walls'] + results['final_walls']['internal_walls']

# Assign openings
assigner = OpeningWallAssigner(all_walls)
doors, windows = assigner.assign_openings_to_walls(
    results['openings']['doors'],
    results['openings']['windows']
)

# Print results
print("="*60)
print("OPENING-TO-WALL ASSIGNMENT TEST")
print("="*60)

print(f"\n📊 Doors assigned:")
for door in doors:
    print(f"   • {door['door_type']} at ({door['position'][0]:.2f}, {door['position'][1]:.2f})")
    print(f"     → Wall: {door['wall_id']}")
    print(f"     → Position on wall: {door['position_on_wall']:.2f} ({door['position_on_wall']*100:.0f}%)")
    print(f"     → Distance to wall: {door['distance_to_wall']:.3f}m")

print(f"\n📊 Windows assigned:")
for window in windows[:5]:  # First 5
    print(f"   • {window['window_type']} at ({window['position'][0]:.2f}, {window['position'][1]:.2f})")
    print(f"     → Wall: {window['wall_id']}")
    print(f"     → Position on wall: {window['position_on_wall']:.2f}")

print("\n✅ Opening assignment test complete!")
```

---

## ⏱️ **TIMELINE FOR OPTION 1**

```
Hour 1: Opening-to-Wall Assignment
├── Add OpeningWallAssigner to extraction_engine.py (30 min)
├── Create test_opening_assignment.py (15 min)
└── Test assignment logic (15 min)

Hour 2: Blender Export
├── Create export_phase2_to_blender.py (45 min)
└── Run export and verify in Blender (15 min)

RESULT: TB-LKTN house in Blender with embedded openings! ✅
```

---

## 🎬 **WHAT YOU'LL SEE IN BLENDER**

After 2 hours:
- ✅ 4 outer walls (perimeter)
- ✅ 10 internal walls (room dividers)
- ✅ 7 doors embedded in walls (Boolean subtraction)
- ✅ 10 windows embedded in walls
- ✅ 1 floor slab (27.7m × 19.7m)
- ⚠️ All at correct XY, but Z heights uniform (doors/windows at floor level)
- ⚠️ No roof

**Good enough for:**
- ✅ Spatial validation (is layout correct?)
- ✅ Client presentation (here's your house in 3D!)
- ✅ Design review (do room sizes make sense?)

**Not yet good for:**
- ❌ Rendering (need materials, lighting)
- ❌ Construction documentation (need accurate heights)
- ❌ IFC export (need room boundaries, element relationships)

---

**What do you want to do?**
1. **Option 1** - Quick Blender export (2 hours) ⭐
2. **Option 2** - Hardening (4-6 hours)
3. **Option 3** - Phase 1D with regex patterns (1 week)
