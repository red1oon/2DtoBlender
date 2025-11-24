#!/usr/bin/env python3
"""
Complete Blender Export with Parametric Objects
Exports validated JSON template to Blender .blend file
"""

import json
import struct
import sqlite3
import numpy as np
import sys
import os

# Add Blender Python path
sys.path.append('/home/red1/blender-4.2.14/4.2/python/lib/python3.11/site-packages')

import bpy
import bmesh
from mathutils import Vector, Euler, Matrix


def load_json_template(json_path):
    """Load validated JSON template"""
    with open(json_path, 'r') as f:
        return json.load(f)


def connect_library_db(db_path):
    """Connect to library database"""
    return sqlite3.connect(db_path)


def fetch_library_geometry(cursor, object_type):
    """Fetch geometry from library by object_type ID"""
    # Query object_catalog to get geometry_hash
    cursor.execute("""
        SELECT geometry_hash
        FROM object_catalog
        WHERE object_type = ?
    """, (object_type,))

    catalog_row = cursor.fetchone()
    if not catalog_row:
        print(f"  ⚠️  Object not found in catalog: {object_type}")
        return None, None, None

    geometry_hash = catalog_row[0]

    # Query base_geometries to get actual geometry
    cursor.execute("""
        SELECT vertices, faces, normals
        FROM base_geometries
        WHERE geometry_hash = ?
    """, (geometry_hash,))

    row = cursor.fetchone()
    if not row:
        print(f"  ⚠️  Geometry not found: {geometry_hash}")
        return None, None, None

    vertices_blob, faces_blob, normals_blob = row

    # Unpack vertices
    vertices = struct.unpack(f'<{len(vertices_blob)//4}f', vertices_blob)
    vertices = [vertices[i:i+3] for i in range(0, len(vertices), 3)]

    # Unpack faces
    faces = struct.unpack(f'<{len(faces_blob)//4}I', faces_blob)
    faces = [faces[i:i+3] for i in range(0, len(faces), 3)]

    # Unpack normals
    normals = struct.unpack(f'<{len(normals_blob)//4}f', normals_blob)
    normals = [normals[i:i+3] for i in range(0, len(normals), 3)]

    return vertices, faces, normals


def create_parametric_roof(obj_data):
    """Create gable roof geometry from parameters"""
    dims = obj_data["dimensions"]
    width = dims["width"]
    length = dims["length"]
    ridge_height = dims["height"]

    # Gable roof vertices
    # Bottom rectangle
    vertices = [
        (-width/2, -length/2, 0),
        (width/2, -length/2, 0),
        (width/2, length/2, 0),
        (-width/2, length/2, 0),
        # Ridge line (top)
        (-width/2, 0, ridge_height),
        (width/2, 0, ridge_height)
    ]

    # Faces (two triangular sides + two trapezoidal sides)
    faces = [
        (0, 1, 5, 4),  # South slope
        (2, 3, 4, 5),  # North slope
        (0, 4, 3),     # West gable
        (1, 2, 5)      # East gable
    ]

    return vertices, faces


def create_parametric_slab(obj_data):
    """Create floor slab geometry from parameters"""
    dims = obj_data["dimensions"]
    width = dims["width"]
    length = dims["length"]
    thickness = dims["thickness"]

    # Box geometry for slab
    vertices = [
        # Bottom face
        (-width/2, -length/2, -thickness/2),
        (width/2, -length/2, -thickness/2),
        (width/2, length/2, -thickness/2),
        (-width/2, length/2, -thickness/2),
        # Top face
        (-width/2, -length/2, thickness/2),
        (width/2, -length/2, thickness/2),
        (width/2, length/2, thickness/2),
        (-width/2, length/2, thickness/2)
    ]

    faces = [
        (0, 1, 2, 3),  # Bottom
        (4, 5, 6, 7),  # Top
        (0, 1, 5, 4),  # South
        (1, 2, 6, 5),  # East
        (2, 3, 7, 6),  # North
        (3, 0, 4, 7)   # West
    ]

    return vertices, faces


def create_parametric_gutter(obj_data):
    """Create gutter geometry from path"""
    path_points = obj_data["geometry"]["path_points"]

    # Simple box profile along path
    vertices = []
    faces = []

    width = 0.15  # 150mm
    height = 0.1  # 100mm

    for i, point in enumerate(path_points):
        x, y = point
        # Rectangle profile
        vertices.extend([
            (x, y - width/2, 0),
            (x, y + width/2, 0),
            (x, y + width/2, height),
            (x, y - width/2, height)
        ])

        # Create faces between segments
        if i > 0:
            base = (i-1) * 4
            faces.extend([
                (base, base+1, base+5, base+4),  # Bottom
                (base+1, base+2, base+6, base+5),  # Side
                (base+2, base+3, base+7, base+6),  # Top
                (base+3, base, base+4, base+7)   # Side
            ])

    return vertices, faces


def create_blender_mesh(name, vertices, faces, position, orientation):
    """Create Blender mesh object with transformations"""
    # Create mesh and object
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)

    # Link to scene
    bpy.context.collection.objects.link(obj)

    # Create mesh from vertices and faces
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    # Apply position
    obj.location = Vector(position)

    # Apply rotation (convert degrees to radians)
    if orientation:
        rotation_x = np.radians(orientation.get("rotation_x", 0.0))
        rotation_y = np.radians(orientation.get("rotation_y", 0.0))
        rotation_z = np.radians(orientation.get("rotation_z", 0.0))
        obj.rotation_euler = Euler((rotation_x, rotation_y, rotation_z), 'XYZ')

    # Recalculate normals
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    return obj


def export_to_blender(json_path, library_db_path, output_blend_path):
    """
    Complete export pipeline:
    1. Load JSON
    2. Fetch/generate geometry
    3. Apply transformations
    4. Export to .blend
    """
    print("=" * 60)
    print("COMPLETE BLENDER EXPORT WITH PARAMETRIC OBJECTS")
    print("=" * 60)

    # Clear existing scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Load template
    print(f"\n✅ Loading template: {json_path}")
    template = load_json_template(json_path)

    # Connect to library
    print(f"✅ Connecting to library: {library_db_path}")
    conn = connect_library_db(library_db_path)
    cursor = conn.cursor()

    # Process each object
    objects_list = template["objects"]
    total_objects = len([obj for obj in objects_list if "object_type" in obj])

    print(f"\n✅ Processing {total_objects} objects...\n")

    created_count = 0
    parametric_count = 0
    library_count = 0

    for obj_data in objects_list:
        # Skip comment entries
        if "_comment" in obj_data:
            continue

        object_type = obj_data["object_type"]
        name = obj_data["name"]
        position = obj_data["position"]
        orientation = obj_data.get("orientation", None)

        print(f"  📦 {name} ({object_type})")

        # Check if parametric
        is_parametric = obj_data.get("parametric", False)

        if is_parametric:
            # Generate parametric geometry
            print(f"     🔧 Generating parametric geometry...")

            if "roof" in object_type:
                vertices, faces = create_parametric_roof(obj_data)
            elif "slab" in object_type:
                vertices, faces = create_parametric_slab(obj_data)
            elif "gutter" in object_type:
                vertices, faces = create_parametric_gutter(obj_data)
            else:
                print(f"     ⚠️  Unknown parametric type, skipping")
                continue

            parametric_count += 1
        else:
            # Fetch from library
            print(f"     📚 Fetching from library...")
            vertices, faces, normals = fetch_library_geometry(cursor, object_type)

            if not vertices:
                print(f"     ⚠️  Not found in library, creating placeholder...")
                # Create 8-vertex box as placeholder
                vertices = [
                    (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5),
                    (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
                    (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5),
                    (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)
                ]
                faces = [
                    (0,1,2,3), (4,5,6,7), (0,1,5,4),
                    (1,2,6,5), (2,3,7,6), (3,0,4,7)
                ]
            else:
                library_count += 1

        # Create Blender mesh
        obj = create_blender_mesh(name, vertices, faces, position, orientation)

        # Add custom properties
        obj["object_type"] = object_type
        obj["room"] = obj_data.get("room", "unknown")
        obj["parametric"] = is_parametric

        if "validation" in obj_data:
            obj["validated"] = obj_data["validation"].get("no_clashes", False)

        created_count += 1
        print(f"     ✅ Created in Blender")

    # Close database
    conn.close()

    # Save .blend file
    print(f"\n✅ Exporting to: {output_blend_path}")
    bpy.ops.wm.save_as_mainfile(filepath=output_blend_path)

    # Summary
    print("\n" + "=" * 60)
    print("EXPORT SUMMARY")
    print("=" * 60)
    print(f"✅ Total objects created: {created_count}")
    print(f"🔧 Parametric objects: {parametric_count}")
    print(f"📚 Library objects: {library_count}")
    print(f"📁 Output file: {output_blend_path}")
    print("=" * 60)
    print("✅ EXPORT COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    # Paths
    json_path = "/home/red1/Documents/bonsai/2DtoBlender/Template_2DBlender/output_artifacts/TB_LKTN_COMPLETE_VALIDATED.json"
    library_db_path = "/home/red1/Documents/bonsai/2DtoBlender/Template_2DBlender/Ifc_Object_Library.db"
    output_blend_path = "/home/red1/Documents/bonsai/2DtoBlender/Template_2DBlender/output_artifacts/TB_LKTN_COMPLETE.blend"

    # Export
    export_to_blender(json_path, library_db_path, output_blend_path)
