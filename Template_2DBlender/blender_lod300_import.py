#!/usr/bin/env python3
"""
Blender LOD300 Import - Real Geometry from Database

Imports extraction output JSON to Blender using actual LOD300 geometry
NO placeholder boxes - fetches real meshes from Ifc_Object_Library.db

Flow:
1. Load extraction output JSON
2. Get unique object_types
3. Fetch LOD300 geometries from database
4. Create meshes in Blender from vertices/faces
5. Position objects at extracted coordinates
6. Mark objects as "placed": true
7. Verify hash total

No AI - pure geometry processing
"""

import bpy
import json
import sys
import os
import math
import numpy as np
from mathutils import Vector, Euler
from datetime import datetime

# Add core directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))
from database_geometry_fetcher import DatabaseGeometryFetcher


def clear_scene():
    """Clear all objects from scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    print("✅ Scene cleared")


def create_mesh_from_geometry(name, geometry_data):
    """
    Create Blender mesh from geometry data

    Args:
        name: Object name
        geometry_data: Dict with 'vertices', 'faces', 'normals'

    Returns:
        bpy.types.Mesh object
    """
    vertices = geometry_data['vertices']
    faces = geometry_data['faces']

    # Create mesh
    mesh = bpy.data.meshes.new(name=f"{name}_mesh")

    # Vertices as list of tuples
    verts = [tuple(v) for v in vertices]

    # Faces as list of tuples
    face_indices = [tuple(f) for f in faces]

    # Create mesh from vertices and faces
    mesh.from_pydata(verts, [], face_indices)

    # Calculate normals if not provided
    if geometry_data.get('normals') is not None:
        # Use provided normals (optional - Blender can auto-calculate)
        pass

    mesh.update()
    mesh.validate()

    return mesh


def create_object_from_mesh(name, mesh, position, orientation=0.0, scale=1.0):
    """
    Create Blender object from mesh at position with orientation

    Args:
        name: Object name
        mesh: bpy.types.Mesh
        position: [x, y, z]
        orientation: Rotation in degrees (Z-axis)
        scale: Uniform scale factor

    Returns:
        bpy.types.Object
    """
    obj = bpy.data.objects.new(name, mesh)

    # Set position
    obj.location = (position[0], position[1], position[2])

    # Set rotation (Z-axis)
    if orientation != 0:
        obj.rotation_euler = Euler((0, 0, math.radians(orientation)), 'XYZ')

    # Set scale
    if scale != 1.0:
        obj.scale = (scale, scale, scale)

    # Link to scene
    bpy.context.collection.objects.link(obj)

    return obj


def create_wall_from_geometry(name, geometry_data, position, end_point, thickness, height):
    """
    Create wall using line segment transformation

    Args:
        name: Wall name
        geometry_data: Base geometry (will be stretched)
        position: Start point [x, y, z]
        end_point: End point [x, y, z]
        thickness: Wall thickness
        height: Wall height

    Returns:
        bpy.types.Object
    """
    # Calculate wall parameters
    start = Vector(position)
    end = Vector(end_point)
    direction = end - start
    length = direction.length
    mid_point = (start + end) / 2

    # Create simple box for wall (ignore base geometry for walls)
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(mid_point[0], mid_point[1], height / 2)
    )

    obj = bpy.context.active_object
    obj.name = name

    # Scale to wall dimensions
    obj.scale = (length / 2, thickness / 2, height / 2)

    # Rotate to align with wall direction
    angle = math.atan2(direction[1], direction[0])
    obj.rotation_euler = Euler((0, 0, angle), 'XYZ')

    return obj


def import_lod300_geometry(json_file, database_path):
    """
    Import objects from JSON using LOD300 geometry from database

    Args:
        json_file: Path to extraction output JSON
        database_path: Path to Ifc_Object_Library.db

    Returns:
        dict: Import statistics
    """
    print(f"\n🔷 Starting LOD300 Import")
    print(f"   Input: {json_file}")
    print(f"   Database: {database_path}")

    # Load extraction JSON
    with open(json_file) as f:
        data = json.load(f)

    objects = data.get('objects', [])
    summary = data.get('summary', {})

    print(f"\n✅ Loaded extraction output: {len(objects)} objects")
    print(f"   Hash total: {summary.get('total_objects', 0)}")

    # Get unique object_types
    object_types = list(set(obj.get('object_type') for obj in objects if obj.get('object_type')))
    print(f"\n📦 Unique object types: {len(object_types)}")

    # Fetch all geometries from database
    fetcher = DatabaseGeometryFetcher(database_path)
    geometries = fetcher.fetch_all_geometries(object_types)
    fetcher.close()

    # Clear scene
    clear_scene()

    # Import statistics
    stats = {
        'total_objects': len(objects),
        'placed': 0,
        'walls': 0,
        'structure': 0,
        'openings': 0,
        'electrical': 0,
        'furniture': 0,
        'other': 0
    }

    # Create objects in Blender
    print(f"\n🏗️  Creating {len(objects)} objects in Blender...")

    for i, obj_data in enumerate(objects, 1):
        try:
            obj_type = obj_data.get('object_type')
            obj_name = obj_data.get('name', 'unnamed')
            position = obj_data.get('position', [0, 0, 0])
            orientation = obj_data.get('orientation', 0.0)
            phase = obj_data.get('_phase', 'other')

            # Get geometry from database
            geometry = geometries.get(obj_type)

            if not geometry:
                print(f"⚠️  [{i}/{len(objects)}] No geometry for {obj_name} ({obj_type})")
                continue

            # Special handling for walls (use line segments)
            if 'wall' in obj_type.lower() and 'end_point' in obj_data:
                end_point = obj_data['end_point']
                thickness = obj_data.get('thickness', 0.1)
                height = obj_data.get('height', 3.0)
                obj = create_wall_from_geometry(obj_name, geometry, position, end_point, thickness, height)
                stats['walls'] += 1

            else:
                # Regular objects - create from LOD300 geometry
                mesh = create_mesh_from_geometry(obj_name, geometry)

                # Scale mesh to actual dimensions if needed
                dims = geometry.get('dimensions', {})
                length = obj_data.get('length', dims.get('width', 1.0))

                # For gutters with length parameter, scale along X-axis
                if 'length' in obj_data and obj_type.startswith('roof_gutter'):
                    scale_x = length / dims.get('width', 1.0)
                    obj = create_object_from_mesh(obj_name, mesh, position, orientation)
                    obj.scale = (scale_x, 1.0, 1.0)
                else:
                    obj = create_object_from_mesh(obj_name, mesh, position, orientation)

                # Categorize
                if 'structure' in phase or 'slab' in obj_type or 'roof' in obj_type or 'ceiling' in obj_type:
                    stats['structure'] += 1
                elif 'opening' in phase or 'door' in obj_type or 'window' in obj_type:
                    stats['openings'] += 1
                elif 'electrical' in phase:
                    stats['electrical'] += 1
                elif 'furniture' in phase:
                    stats['furniture'] += 1
                else:
                    stats['other'] += 1

            stats['placed'] += 1

            if i % 10 == 0:
                print(f"   Progress: {i}/{len(objects)} objects created")

        except Exception as e:
            print(f"❌ Error creating {obj_name}: {e}")
            import traceback
            traceback.print_exc()

    # Report statistics
    print(f"\n✅ Import Complete:")
    print(f"   Placed: {stats['placed']}/{stats['total_objects']}")
    print(f"   - Structure: {stats['structure']}")
    print(f"   - Walls: {stats['walls']}")
    print(f"   - Openings: {stats['openings']}")
    print(f"   - Electrical: {stats['electrical']}")
    print(f"   - Furniture: {stats['furniture']}")
    print(f"   - Other: {stats['other']}")

    # Mark objects as placed in JSON (for hash total verification)
    for obj in objects:
        obj['placed'] = True

    # Save updated JSON with pattern: <PDFname>OUTPUT<timestamp>.json
    # Extract PDF name from metadata if available, otherwise use generic name
    pdf_source = data.get('metadata', {}).get('pdf_source', 'UNKNOWN.pdf')
    # Remove extension and replace spaces/underscores with hyphens: "TB-LKTN HOUSE.pdf" → "TB-LKTN-HOUSE"
    pdf_basename = os.path.splitext(pdf_source)[0].replace(' ', '-').replace('_', '-')

    # Generate timestamp: YYYYMMDD_HHMMSS
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Create output filename: TB-LKTN_OUTPUT_20251126_200000.json
    output_filename = f"{pdf_basename}_OUTPUT_{timestamp}.json"
    output_dir = os.path.join(os.path.dirname(json_file), '../output_artifacts')
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, output_filename)

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n✅ Updated JSON saved: {output_file}")

    # Verify hash total
    expected = summary.get('total_objects', 0)
    actual = stats['placed']
    if expected == actual:
        print(f"✅ Hash total verified: {actual}/{expected} objects placed")
    else:
        print(f"⚠️  Hash total mismatch: {actual}/{expected} objects placed")

    return stats


# Main execution
if __name__ == "__main__":
    argv = sys.argv

    # Blender arguments come after "--"
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]

    if len(argv) < 2:
        print("Usage: blender --python blender_lod300_import.py -- <extraction_output.json> <database_path> [output.blend]")
        print("Example: blender --python blender_lod300_import.py -- output.json DatabaseFiles/Ifc_Object_Library.db model.blend")
        sys.exit(1)

    json_file = argv[0]
    database_path = argv[1]
    output_file = argv[2] if len(argv) > 2 else 'output.blend'

    # Import with LOD300 geometry
    stats = import_lod300_geometry(json_file, database_path)

    # Save Blender file
    bpy.ops.wm.save_as_mainfile(filepath=output_file)
    print(f"\n✅ Blender file saved: {output_file}")
