# 🎨 Blender Import Guide - View Your Generated BIM!

**Database:** `Generated_Terminal1_SAMPLE.db`
**Elements:** 15,257 IFC elements with 3D geometries
**Ready:** ✅ YES! Open in Blender now!

---

## 🚀 Method 1: Quick Import (Python Console)

**Step 1: Launch Blender with Bonsai**
```bash
~/blender-4.2.14/blender
```

**Step 2: Open Python Console**
- Window → Toggle System Console (to see progress)
- Scripting workspace → Python Console

**Step 3: Run Import Script**
```python
import sys
sys.path.insert(0, '/home/red1/Documents/bonsai/2Dto3D/Scripts')

import import_to_blender
import_to_blender.import_database('/home/red1/Documents/bonsai/2Dto3D/Generated_Terminal1_SAMPLE.db')
```

**Step 4: View Results**
- Press `Home` key to frame all elements
- Check **Outliner** → Collections by discipline
- Select objects to see metadata

---

## 🎬 Method 2: Command Line (Automated)

```bash
~/blender-4.2.14/blender --python /home/red1/Documents/bonsai/2Dto3D/Scripts/import_to_blender.py -- /home/red1/Documents/bonsai/2Dto3D/Generated_Terminal1_SAMPLE.db
```

**To limit import (testing):**
```bash
# Import only first 1000 elements
~/blender-4.2.14/blender --python /home/red1/Documents/bonsai/2Dto3D/Scripts/import_to_blender.py -- /home/red1/Documents/bonsai/2Dto3D/Generated_Terminal1_SAMPLE.db 1000
```

---

## 📊 What You'll See

### Outliner Structure

```
Scene Collection
├── 🏛️ Seating (11,604 elements)
│   ├── IfcBuildingElementProxy_0001
│   ├── IfcBuildingElementProxy_0002
│   ├── ...
│   ├── IfcWall_001
│   └── IfcWindow_001
│
├── 🔥 Fire_Protection (2,063 elements)
│   ├── IfcBuildingElementProxy_...
│   └── IfcPipeSegment_...
│
├── 🏗️ Structure (634 elements)
│   └── IfcColumn_...
│
├── ❄️ ACMV (544 elements)
│   └── IfcBuildingElementProxy_...
│
├── ⚡ Electrical (338 elements)
│   └── IfcBuildingElementProxy_...
│
├── 🚰 Plumbing (54 elements)
│   └── IfcPipeSegment_...
│
└── 🔥 LPG (20 elements)
    └── IfcPipeSegment_...
```

### Color Coding

- **Tan** - Architecture/Seating
- **Red** - Fire Protection
- **Gray** - Structure
- **Light Blue** - ACMV
- **Yellow** - Electrical
- **Blue** - Plumbing
- **Cyan** - Chilled Water
- **Orange** - LPG

### Element Properties

Select any object → Object Properties panel:
- **guid:** Unique identifier
- **discipline:** Fire_Protection, Seating, etc.
- **ifc_class:** IfcWall, IfcColumn, etc.

---

## 🎯 Useful Blender Operations

### Navigation
```
Home          - Frame all elements
Numpad 7      - Top view
Numpad 1      - Front view
Numpad 3      - Side view
Middle Mouse  - Rotate view
Shift+Middle  - Pan view
Scroll        - Zoom
```

### Selection
```
A             - Select all
Alt+A         - Deselect all
B             - Box select
C             - Circle select
```

### Collections
```
Click eye icon       - Hide/show collection
Click checkbox       - Enable/disable in viewport
M                    - Move selected to collection
```

### Filtering by Discipline

**Hide all except Fire Protection:**
1. Click eye icon on all other collections
2. Only Fire_Protection visible
3. Press `Home` to frame

**Show only Structure:**
1. Hide all collections
2. Show Structure collection
3. Analyze column placement

---

## 📈 Performance Tips

### If Blender is Slow (15K+ elements)

**Option 1: Import Subset**
```python
# Import only 1000 elements for quick testing
import_to_blender.import_database(
    '/home/red1/Documents/bonsai/2Dto3D/Generated_Terminal1_SAMPLE.db',
    limit=1000
)
```

**Option 2: Display as Bounds**
1. Select all objects (A)
2. Object Properties → Viewport Display
3. Display As: Bounds
4. Much faster navigation

**Option 3: Level of Detail**
1. Edit → Preferences → Viewport
2. Reduce subdivision levels
3. Lower anti-aliasing

---

## 🔍 Analyzing the Import

### Check Element Counts

```python
import bpy

# Count by collection
for coll in bpy.data.collections:
    count = len(coll.objects)
    print(f"{coll.name}: {count} objects")
```

### Find Elements by Type

```python
import bpy

# Find all columns
columns = [obj for obj in bpy.data.objects if obj.get('ifc_class') == 'IfcColumn']
print(f"Found {len(columns)} columns")

# Select all columns
for obj in columns:
    obj.select_set(True)
```

### Query Metadata

```python
import bpy

# Get selected object metadata
obj = bpy.context.active_object
if obj:
    print(f"GUID: {obj.get('guid')}")
    print(f"Discipline: {obj.get('discipline')}")
    print(f"IFC Class: {obj.get('ifc_class')}")
```

---

## 🐛 Troubleshooting

### "Module not found" Error

```python
# Make sure path is correct
import sys
print(sys.path)

# Add path explicitly
sys.path.insert(0, '/home/red1/Documents/bonsai/2Dto3D/Scripts')
```

### "Database not found" Error

```python
# Check database exists
from pathlib import Path
db = Path('/home/red1/Documents/bonsai/2Dto3D/Generated_Terminal1_SAMPLE.db')
print(f"Exists: {db.exists()}")
print(f"Size: {db.stat().st_size / 1024 / 1024:.1f} MB")
```

### Import Appears Empty

1. Check System Console for errors
2. Try limiting to 10 elements first
3. Check if collections are hidden in Outliner

### Blender Crashes

- Reduce import limit to 1000 elements
- Close other applications
- Try in a new Blender file

---

## 🎨 Advanced: Custom Materials

**Add better materials by IFC class:**

```python
import bpy

def assign_materials_by_type():
    for obj in bpy.data.objects:
        ifc_class = obj.get('ifc_class', '')

        if 'Wall' in ifc_class:
            # Walls = white/gray
            mat = create_material("Wall_Material", (0.9, 0.9, 0.9, 1.0))
        elif 'Column' in ifc_class:
            # Columns = dark gray
            mat = create_material("Column_Material", (0.3, 0.3, 0.3, 1.0))
        elif 'Window' in ifc_class:
            # Windows = glass blue
            mat = create_material("Window_Material", (0.5, 0.7, 1.0, 0.5))
        else:
            continue

        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

def create_material(name, color):
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True

    # Set base color in nodes
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        if color[3] < 1.0:  # If transparent
            bsdf.inputs['Alpha'].default_value = color[3]
            mat.blend_method = 'BLEND'

    return mat

# Run
assign_materials_by_type()
```

---

## 📸 Render Setup

**Quick render setup:**

```python
import bpy

# Set render engine
bpy.context.scene.render.engine = 'CYCLES'

# Add sun light
bpy.ops.object.light_add(type='SUN', location=(0, 0, 50))
sun = bpy.context.active_object
sun.data.energy = 5.0

# Add camera
bpy.ops.object.camera_add(location=(50, -50, 30))
camera = bpy.context.active_object
camera.rotation_euler = (1.1, 0, 0.785)

# Set as active camera
bpy.context.scene.camera = camera

# Frame all in camera view
bpy.ops.view3d.camera_to_view_selected()
```

---

## 🎯 Next Steps After Viewing

**Once you verify the import works:**

1. **Analyze Coverage**
   - Which disciplines are well-represented?
   - Which need more work?
   - Are positions correct?

2. **Improve Geometries**
   - Replace boxes with actual IFC geometries
   - Add proper dimensions from DWG
   - Import actual shapes

3. **Add Properties**
   - Material assignments
   - Property sets
   - Relationships

4. **Export to IFC**
   - Bonsai → Export → IFC
   - Validate in IFC viewer
   - Share with stakeholders

---

## ✅ Success Checklist

- [ ] Blender opens without errors
- [ ] Import script runs successfully
- [ ] Collections appear in Outliner
- [ ] Elements visible in 3D viewport (press Home)
- [ ] Colors match disciplines
- [ ] Can select objects and see metadata
- [ ] Count matches expected (15,257 total)
- [ ] All 7 disciplines present

**If all checked → 🎉 SUCCESS! Your 2D→3D conversion is visualized!**

---

**Created:** November 15, 2025
**Database:** Generated_Terminal1_SAMPLE.db (5.0 MB)
**Elements:** 15,257 with placeholder geometries
**Status:** ✅ Ready to import and view!
