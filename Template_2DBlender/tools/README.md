# Library Management Tools

**Location:** `/home/red1/Documents/bonsai/2DtoBlender/Template_2DBlender/tools/`

## Key Resources

### Database Location
```
DatabaseFiles/Ifc_Object_Library.db
(128MB, 7,235 LOD300 prefab objects)
```

### Tools

#### 1. Geometry Generators
**File:** `geometry_generators.py`
- Core geometry generation utilities
- Provides: `compute_face_normal()`, `GeometryResult`
- Used by: All library generation scripts

#### 2. Complete Library Generator
**File:** `generate_complete_library_lod300.py`
- Generates all LOD300 library objects
- Phases 2, 3, 4 generators (70 objects)
- Usage:
  ```bash
  python3 generate_complete_library_lod300.py --output ../DatabaseFiles/Ifc_Object_Library.db --phase 2
  ```

#### 3. Gutter Corner Connector
**File:** `add_gutter_corner.py`
- Adds 90-degree gutter corner elbow
- Object type: `roof_gutter_corner_90_lod300`
- IFC Class: `IfcPipeFitting`
- Usage:
  ```bash
  python3 add_gutter_corner.py ../DatabaseFiles/Ifc_Object_Library.db
  ```

## Adding New Library Objects

### Step 1: Create Geometry Generator
Use `geometry_generators.py` as reference:
```python
def generate_my_object():
    vertices = [...]  # List of (x, y, z) tuples
    faces = [...]     # List of (v0, v1, v2) index triplets
    normals = [compute_face_normal(v0, v1, v2) for each face]
    return GeometryResult(vertices, faces, normals)
```

### Step 2: Add to Database
```python
import sqlite3
import struct

# Generate geometry
vertices, faces, normals = generate_my_object()

# Pack binary blobs
vertices_blob = struct.pack(f'<{len(vertices)*3}f', *[c for v in vertices for c in v])
faces_blob = struct.pack(f'<{len(faces)*3}I', *[idx for f in faces for idx in f])
normals_blob = struct.pack(f'<{len(normals)*3}f', *[c for n in normals for c in n])

# Insert into database
conn = sqlite3.connect('DatabaseFiles/Ifc_Object_Library.db')
cursor = conn.cursor()

cursor.execute("""
    INSERT INTO base_geometries (geometry_hash, vertices, faces, normals)
    VALUES (?, ?, ?, ?)
""", (geometry_hash, vertices_blob, faces_blob, normals_blob))

cursor.execute("""
    INSERT INTO object_catalog (
        object_type, object_name, ifc_class, category, sub_category,
        width_mm, depth_mm, height_mm, description,
        geometry_hash, construction_type, standard_compliance
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (...))

conn.commit()
```

### Step 3: Validate
```bash
sqlite3 DatabaseFiles/Ifc_Object_Library.db "SELECT object_type FROM object_catalog WHERE object_type = 'my_object_lod300';"
```

## Database Schema

### Tables
- `base_geometries` - Geometry blobs (vertices, faces, normals)
- `object_catalog` - Object metadata (type, IFC class, dimensions)
- `placement_rules` - Placement constraints
- `connection_requirements` - Connection rules
- `malaysian_standards` - Standards compliance
- `validation_rules` - Validation criteria

### Key Columns
- `object_type` - Unique identifier (e.g., `door_single_900_lod300`)
- `ifc_class` - IFC entity type (e.g., `IfcDoor`, `IfcWindow`)
- `geometry_hash` - Links to base_geometries table
- `width_mm`, `depth_mm`, `height_mm` - Bounding box dimensions

## Current Status

**Library Objects:** 7,235 LOD300 objects
**Master Template References:** 26 object_types validated

**Recent Addition:**
- ✅ `roof_gutter_corner_90_lod300` - Gutter corner elbow for perimeter drainage
