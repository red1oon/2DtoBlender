# Mini Bonsai Tree GUI Integration Guide
**2D-to-3D Conversion Pipeline - GUI Interface Specification**

Last Updated: November 17, 2025

---

## ✅ Current Code Alignment Status

Our codebase is **READY for GUI integration** with the following modular structure:

### 1. **Shape Library** (`Scripts/shape_library.py`)
**Status:** ✅ Fully GUI-ready

**Design Principles:**
- ✅ Individual callable functions (not monolithic)
- ✅ Consistent return signature: `(vertices, faces, normals)`
- ✅ Parametric inputs (style, size, type options)
- ✅ All shapes centered at origin (GUI handles positioning)
- ✅ Well-documented with docstrings

**Available Shape Generators:**

```python
# Furniture (2 functions, 3+ variants each)
generate_chair(style='office|dining|stool', seat_height=0.45)
generate_table(seats=2-8, shape='rectangular|circular|square')

# Lighting (1 function, 5 types)
generate_light_fixture(type='pendant|recessed|track|wall_sconce|floor_lamp')

# Fire Protection (2 functions, 4 types)
generate_sprinkler(type='head|pipe|standpipe')
generate_fire_extinguisher()

# Plumbing (2 functions, 4 types)
generate_toilet()
generate_sink(type='wall|pedestal|counter')

# Equipment (2 functions, 7 types)
generate_hvac_unit(type='diffuser|ahu|fcu|exhaust_fan')
generate_electrical_panel(type='distribution|switchgear|transformer')
```

**Total:** 9 main functions, 20+ object variants

**GUI Usage Example:**
```python
from Scripts.shape_library import generate_chair, generate_sprinkler

# User selects "Office Chair" from GUI dropdown
vertices, faces, normals = generate_chair(style='office', seat_height=0.45)

# User adjusts seat height slider → regenerate
vertices, faces, normals = generate_chair(style='office', seat_height=0.50)
```

---

## 2. **Database Schema** (SQLite)
**Status:** ✅ GUI-accessible with clear interfaces

### **Key Tables for GUI:**

#### `elements_meta` - Element Metadata
```sql
SELECT guid, discipline, ifc_class, element_name, dimensions
FROM elements_meta
WHERE discipline = 'FP'  -- Filter by discipline
  AND ifc_class = 'IfcBuildingElementProxy';
```

**GUI Use Cases:**
- **Object Browser:** List all elements by discipline/class
- **Selection:** Filter by IFC class (walls, doors, equipment, etc.)
- **Properties Panel:** Display element_name, dimensions, discipline

#### `base_geometries` - 3D Mesh Data
```sql
SELECT vertices, faces, normals
FROM base_geometries
WHERE guid = '00dd0c1e-0f0a-4b62-8a0b-1234567890ab';
```

**GUI Use Cases:**
- **Viewport Display:** Load mesh for selected element
- **Shape Replacement:** Swap vertices/faces/normals with shape_library output

#### `element_transforms` - Position/Rotation
```sql
SELECT center_x, center_y, center_z, rotation_z
FROM element_transforms
WHERE guid = '...';
```

**GUI Use Cases:**
- **3D Viewport:** Position and rotate objects
- **Spatial Queries:** Find nearby elements

#### `material_assignments` - Viewport Colors (FUTURE)
```sql
SELECT material_name, color_rgba
FROM material_assignments
WHERE guid = '...';
```

**GUI Use Cases:**
- **Material Editor:** Assign colors by discipline
- **Viewport Preview:** Display color-coded elements

**Note:** Material mode currently uses `elements_meta.material_rgba` (empty). GUI should populate this column for Bonsai Material mode compatibility.

---

## 3. **Modular Generation Scripts**
**Status:** ✅ Can be imported and called from GUI

### **Geometry Generation** (`Scripts/generate_3d_geometry.py`)

**GUI-Callable Functions:**
```python
from Scripts.generate_3d_geometry import (
    generate_element_geometry,   # Main function
    add_dimension_variety,        # Dimension randomizer
    pack_vertices,                # Binary packing
    pack_faces,
    pack_normals
)

# Generate geometry for a specific element
vertices, faces, normals = generate_element_geometry(
    ifc_class='IfcDoor',
    center_x=0, center_y=0, center_z=0,
    dimensions={'width': 0.9, 'height': 2.1},
    guid='element-guid-12345'
)

# Pack for database storage
vertices_blob = pack_vertices(vertices)
faces_blob = pack_faces(faces)
normals_blob = pack_normals(normals)
```

**GUI Workflow:**
1. User selects element in GUI
2. User chooses new shape from shape_library
3. GUI calls `generate_*()` function
4. GUI updates `base_geometries` table with new blobs
5. Viewport refreshes with new geometry

---

## 4. **GUI Integration Points**

### **Point 1: Object Browser / Element Selection**

**Database Query:**
```python
import sqlite3

conn = sqlite3.connect('Terminal1_MainBuilding_FILTERED.db')
cursor = conn.cursor()

# Get all elements grouped by discipline
cursor.execute("""
    SELECT discipline, ifc_class, COUNT(*) as count
    FROM elements_meta
    GROUP BY discipline, ifc_class
    ORDER BY discipline, count DESC
""")

# Build GUI tree:
# - ARC (911)
#   - IfcWall (347)
#   - IfcDoor (265)
# - FP (219)
#   - IfcBuildingElementProxy (219)
```

### **Point 2: Shape Replacement Workflow**

**User Action:** Right-click element → "Replace with..." → Select shape type

**GUI Code:**
```python
from Scripts.shape_library import generate_sprinkler
import sqlite3

# 1. User selects FP equipment element
selected_guid = '00dd0c1e-0f0a-4b62...'

# 2. User chooses "Sprinkler Head" from dropdown
vertices, faces, normals = generate_sprinkler(type='head', ceiling_height=3.0)

# 3. Pack for database
from Scripts.generate_3d_geometry import pack_vertices, pack_faces, pack_normals
vertices_blob = pack_vertices(vertices)
faces_blob = pack_faces(faces)
normals_blob = pack_normals(normals)

# 4. Update database
conn = sqlite3.connect('Terminal1_MainBuilding_FILTERED.db')
cursor = conn.cursor()
cursor.execute("""
    UPDATE base_geometries
    SET vertices = ?, faces = ?, normals = ?
    WHERE guid = ?
""", (vertices_blob, faces_blob, normals_blob, selected_guid))
conn.commit()

# 5. Update R-tree bbox
# Run Scripts/fix_rtree_bboxes.py or update manually

# 6. Refresh viewport
```

### **Point 3: Batch Operations**

**User Action:** Select all FP equipment → Replace all with sprinklers

**GUI Code:**
```python
# Get all FP equipment
cursor.execute("""
    SELECT guid FROM elements_meta
    WHERE discipline = 'FP' AND ifc_class = 'IfcBuildingElementProxy'
""")
guids = [row[0] for row in cursor.fetchall()]

# Generate sprinkler geometry once (all identical)
vertices, faces, normals = generate_sprinkler(type='head')
vertices_blob = pack_vertices(vertices)
faces_blob = pack_faces(faces)
normals_blob = pack_normals(normals)

# Update all in batch
cursor.executemany("""
    UPDATE base_geometries
    SET vertices = ?, faces = ?, normals = ?
    WHERE guid = ?
""", [(vertices_blob, faces_blob, normals_blob, guid) for guid in guids])
conn.commit()
```

### **Point 4: Material/Color Assignment (FUTURE)**

**Current Issue:** `elements_meta.material_rgba` is empty (Material mode won't work)

**GUI Should Populate:**
```python
# Populate material_rgba from material_assignments table
cursor.execute("""
    UPDATE elements_meta
    SET material_rgba = (
        SELECT color_rgba FROM material_assignments
        WHERE material_assignments.guid = elements_meta.guid
        LIMIT 1
    )
""")
conn.commit()
```

**Or GUI Material Editor:**
```python
# User assigns red color to all FP elements
cursor.execute("""
    UPDATE elements_meta
    SET material_rgba = '1.0,0.2,0.2,1.0'
    WHERE discipline = 'FP'
""")
```

---

## 5. **Database Access Patterns for GUI**

### **Pattern 1: Element Properties Panel**
```python
def get_element_properties(guid):
    """Get all properties for selected element."""
    cursor.execute("""
        SELECT
            m.guid,
            m.discipline,
            m.ifc_class,
            m.element_name,
            m.dimensions,
            t.center_x, t.center_y, t.center_z,
            t.rotation_z,
            ma.material_name,
            ma.color_rgba
        FROM elements_meta m
        LEFT JOIN element_transforms t ON m.guid = t.guid
        LEFT JOIN material_assignments ma ON m.guid = ma.guid
        WHERE m.guid = ?
    """, (guid,))
    return cursor.fetchone()
```

### **Pattern 2: Spatial Query (Find Nearby)**
```python
def find_nearby_elements(x, y, z, radius=5.0):
    """Find elements within radius of point (for GUI selection)."""
    cursor.execute("""
        SELECT m.guid, m.ifc_class, t.center_x, t.center_y, t.center_z
        FROM elements_meta m
        JOIN element_transforms t ON m.guid = t.guid
        WHERE
            (t.center_x - ?)*(t.center_x - ?) +
            (t.center_y - ?)*(t.center_y - ?) +
            (t.center_z - ?)*(t.center_z - ?) < ?*?
    """, (x, x, y, y, z, z, radius, radius))
    return cursor.fetchall()
```

### **Pattern 3: Filter by Discipline**
```python
def get_elements_by_discipline(discipline_code):
    """Get all elements for a discipline (for GUI filtering)."""
    cursor.execute("""
        SELECT guid, ifc_class, element_name
        FROM elements_meta
        WHERE discipline = ?
        ORDER BY ifc_class, element_name
    """, (discipline_code,))  # 'ARC', 'FP', 'STR', 'ELEC'
    return cursor.fetchall()
```

---

## 6. **GUI Development Checklist**

### **Phase 1: Basic Viewer** ✅ (Data Ready)
- [ ] Connect to database
- [ ] Display element tree (discipline → ifc_class → elements)
- [ ] Show element properties panel
- [ ] Load geometry from base_geometries table
- [ ] Render in 3D viewport with colors from material_assignments

### **Phase 2: Shape Library Integration** ✅ (Code Ready)
- [ ] Import shape_library.py
- [ ] Create shape selector dropdown/palette
- [ ] Implement "Replace Shape" function
- [ ] Update base_geometries table
- [ ] Refresh viewport after replacement

### **Phase 3: Batch Operations** ✅ (Code Ready)
- [ ] Multi-select elements
- [ ] "Replace All" functionality
- [ ] Progress bar for batch updates
- [ ] Undo/redo system (save geometry_hash before changes)

### **Phase 4: Material Editor** ⚠️ (Needs Implementation)
- [ ] Populate elements_meta.material_rgba from material_assignments
- [ ] Color picker for disciplines/elements
- [ ] Preview in viewport
- [ ] Save to database

### **Phase 5: Custom Shapes** (Future)
- [ ] Import custom OBJ/STL files
- [ ] Convert to vertices/faces/normals format
- [ ] Add to shape library dynamically
- [ ] Save custom shapes to library database

---

## 7. **API Summary for GUI Developers**

### **Shape Library API:**
```python
# Import available generators
from Scripts.shape_library import (
    generate_chair,
    generate_table,
    generate_light_fixture,
    generate_sprinkler,
    generate_fire_extinguisher,
    generate_toilet,
    generate_sink,
    generate_hvac_unit,
    generate_electrical_panel
)

# All functions return: (vertices, faces, normals)
# - vertices: List[(float, float, float)]
# - faces: List[(int, int, int)]
# - normals: List[(float, float, float)]
```

### **Geometry Packing API:**
```python
from Scripts.generate_3d_geometry import (
    pack_vertices,   # List[Tuple] → bytes (binary BLOB)
    pack_faces,      # List[Tuple] → bytes
    pack_normals     # List[Tuple] → bytes
)
```

### **Database Tables:**
```
elements_meta        → Element metadata (guid, discipline, ifc_class, dimensions)
base_geometries      → 3D mesh data (vertices, faces, normals BLOBs)
element_transforms   → Position/rotation (center_x/y/z, rotation_z)
material_assignments → Colors (discipline-based RGBA)
elements_rtree       → Spatial index for Preview mode bboxes
```

---

## 8. **Known Limitations for GUI**

### **Material Mode:**
- ❌ `elements_meta.material_rgba` is empty (0/1185 populated)
- ✅ `material_assignments` table is populated (1185/1185)
- **Solution:** GUI should copy data from material_assignments → elements_meta.material_rgba

### **Dimension Variety:**
- ✅ Actual geometry has varied dimensions (850 unique bbox sizes)
- ⚠️ `element_transforms.length` only stores wall lengths
- **Note:** Validators checking element_transforms will miss bbox diversity

### **Shape Type Detection:**
- ✅ Can detect shape type by vertex count:
  - 8 vertices = Box
  - 16 vertices = Frame (doors/windows)
  - 26 vertices = Cylinder (columns)
- **GUI Can:** Display shape type in properties panel

---

## 9. **Recommended GUI Architecture**

```
┌─────────────────────────────────────────────┐
│ Mini Bonsai Tree GUI (Blender Addon)       │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐  ┌──────────────────┐   │
│  │ Element Tree │  │ Shape Palette    │   │
│  │              │  │                  │   │
│  │ - ARC (911)  │  │ [Chair]  [Table] │   │
│  │   - Walls    │  │ [Light]  [Sprink]│   │
│  │   - Doors    │  │ [Toilet] [Sink]  │   │
│  │ - FP (219)   │  │ [HVAC]   [Panel] │   │
│  │ - STR (29)   │  │                  │   │
│  └──────────────┘  └──────────────────┘   │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │ 3D Viewport (Blender)                │  │
│  │ - Load from base_geometries          │  │
│  │ - Position from element_transforms   │  │
│  │ - Colors from material_assignments   │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │ Properties Panel                     │  │
│  │ - GUID: 00dd0c1e...                  │  │
│  │ - Class: IfcBuildingElementProxy     │  │
│  │ - Discipline: FP                     │  │
│  │ - Dimensions: 1.27 × 1.59 × 1.47m    │  │
│  │ - Position: (16.72, 7.26, 2.5)       │  │
│  │ - [Replace Shape ▼] [Apply Color]    │  │
│  └──────────────────────────────────────┘  │
│                                             │
└─────────────────────────────────────────────┘
              ↕
┌─────────────────────────────────────────────┐
│ Database Layer (SQLite)                     │
├─────────────────────────────────────────────┤
│ - elements_meta                             │
│ - base_geometries (BLOB storage)            │
│ - element_transforms                        │
│ - material_assignments                      │
└─────────────────────────────────────────────┘
              ↕
┌─────────────────────────────────────────────┐
│ Python Backend (Our Code)                   │
├─────────────────────────────────────────────┤
│ - Scripts/shape_library.py ✅               │
│ - Scripts/generate_3d_geometry.py ✅         │
│ - Scripts/fix_rtree_bboxes.py ✅             │
└─────────────────────────────────────────────┘
```

---

## 10. **Testing GUI Integration**

### **Test 1: Load Shape Library**
```python
# In Blender Python console
import sys
sys.path.append('/home/red1/Documents/bonsai/2Dto3D')

from Scripts.shape_library import generate_chair
vertices, faces, normals = generate_chair(style='office')
print(f"Generated chair: {len(vertices)} vertices, {len(faces)} faces")
# Expected: 32 vertices, 48 faces
```

### **Test 2: Query Database**
```python
import sqlite3
conn = sqlite3.connect('/home/red1/Documents/bonsai/2Dto3D/Terminal1_MainBuilding_FILTERED.db')
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM elements_meta WHERE discipline = 'FP'")
print(f"FP elements: {cursor.fetchone()[0]}")
# Expected: 219
```

### **Test 3: Replace Geometry**
```python
# Replace one element's geometry
from Scripts.shape_library import generate_sprinkler
from Scripts.generate_3d_geometry import pack_vertices, pack_faces, pack_normals

vertices, faces, normals = generate_sprinkler(type='head')
vertices_blob = pack_vertices(vertices)
faces_blob = pack_faces(faces)
normals_blob = pack_normals(normals)

cursor.execute("""
    UPDATE base_geometries
    SET vertices = ?, faces = ?, normals = ?
    WHERE guid = (SELECT guid FROM elements_meta WHERE discipline = 'FP' LIMIT 1)
""", (vertices_blob, faces_blob, normals_blob))
conn.commit()
print("✅ Geometry replaced")
```

---

## ✅ **Summary: Code Alignment Status**

| Component | GUI-Ready? | Notes |
|-----------|------------|-------|
| **Shape Library** | ✅ YES | 9 functions, parametric, well-documented |
| **Database Schema** | ✅ YES | Clear tables with indexed queries |
| **Geometry Generation** | ✅ YES | Modular, importable functions |
| **Binary Packing** | ✅ YES | pack_vertices/faces/normals available |
| **Material System** | ⚠️ PARTIAL | Need to populate material_rgba column |
| **Documentation** | ✅ YES | This guide + docstrings |
| **Test Data** | ✅ YES | 1,185 elements with varied geometry |

**Overall Readiness:** **90% GUI-Ready** ✅

**Remaining Task for GUI:**
- Populate `elements_meta.material_rgba` from `material_assignments` table for Material mode support

---

## Contact / Support

For GUI integration questions or issues:
- Shape library: See `Scripts/shape_library.py` docstrings
- Database queries: See section 5 (Database Access Patterns)
- Geometry format: See section 7 (API Summary)

**Last Updated:** November 17, 2025
**Pipeline Status:** Production Ready
**Database:** Terminal1_MainBuilding_FILTERED.db (1.9 MB)
