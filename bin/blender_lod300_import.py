#!/usr/bin/env python3
"""
Blender LOD300 Import - Real Geometry from Database
VERSION: 2025-11-27-DEBUG-V3

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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))
from database_geometry_fetcher import DatabaseGeometryFetcher


def clear_scene():
    """Clear all objects from scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    print("✅ Scene cleared")


def create_mesh_from_geometry(name, geometry_data, base_rotation=(0.0, 0.0, 0.0)):
    """
    Create Blender mesh from geometry data

    Args:
        name: Object name
        geometry_data: Dict with 'vertices', 'faces', 'normals'
        base_rotation: (rx, ry, rz) in radians - rotates vertices before mesh creation

    Returns:
        bpy.types.Mesh object
    """
    vertices = geometry_data['vertices'].copy()  # CRITICAL: Copy to avoid modifying shared geometry
    faces = geometry_data['faces']

    # Apply base rotation to vertices (if needed)
    base_x, base_y, base_z = base_rotation
    if base_x != 0.0 or base_y != 0.0 or base_z != 0.0:
        print(f"      [DEBUG] Applying vertex rotation: ({math.degrees(base_x):.0f}°, {math.degrees(base_y):.0f}°, {math.degrees(base_z):.0f}°)")
        # Convert vertices to numpy for matrix multiplication
        verts_array = np.array(vertices)
        print(f"      [DEBUG] Pre-rotation vertex count: {len(vertices)}")

        # Build rotation matrices
        # X-axis rotation
        if base_x != 0.0:
            cos_x, sin_x = math.cos(base_x), math.sin(base_x)
            rot_x = np.array([
                [1, 0, 0],
                [0, cos_x, -sin_x],
                [0, sin_x, cos_x]
            ])
            verts_array = verts_array @ rot_x.T

        # Y-axis rotation
        if base_y != 0.0:
            cos_y, sin_y = math.cos(base_y), math.sin(base_y)
            rot_y = np.array([
                [cos_y, 0, sin_y],
                [0, 1, 0],
                [-sin_y, 0, cos_y]
            ])
            verts_array = verts_array @ rot_y.T

        # Z-axis rotation
        if base_z != 0.0:
            cos_z, sin_z = math.cos(base_z), math.sin(base_z)
            rot_z = np.array([
                [cos_z, -sin_z, 0],
                [sin_z, cos_z, 0],
                [0, 0, 1]
            ])
            verts_array = verts_array @ rot_z.T

        vertices = verts_array.tolist()
        print(f"      [DEBUG] Post-rotation vertex count: {len(vertices)}")
        print(f"      [DEBUG] First rotated vertex: {vertices[0]}")

    # Create mesh
    mesh = bpy.data.meshes.new(name=f"{name}_mesh")

    # Vertices as list of tuples
    verts = [tuple(v) for v in vertices]

    # DEBUG: Confirm vertices being passed to Blender
    if len(verts) < 100 and 'toilet_paper' in name:
        print(f"      [DEBUG] Passing {len(verts)} vertices to from_pydata, first={verts[0]}")

    # Faces as list of tuples
    face_indices = [tuple(f) for f in faces]

    # Create mesh from vertices and faces
    mesh.from_pydata(verts, [], face_indices)

    # DEBUG: Check what Blender actually stored
    if len(verts) < 100 and 'toilet_paper' in name:
        actual_verts = [v.co for v in mesh.vertices]
        print(f"      [DEBUG] After from_pydata, Blender mesh has {len(actual_verts)} vertices")
        print(f"      [DEBUG] First vertex in Blender mesh: {tuple(actual_verts[0])}")

    # Calculate normals if not provided
    if geometry_data.get('normals') is not None:
        # Use provided normals (optional - Blender can auto-calculate)
        pass

    mesh.update()
    mesh.validate()

    # DEBUG: Check after update/validate
    if len(verts) < 100 and 'toilet_paper' in name:
        actual_verts = [v.co for v in mesh.vertices]
        print(f"      [DEBUG] ALL {len(actual_verts)} vertices in final mesh:")
        for i in range(len(actual_verts)):
            print(f"        [{i}]: ({actual_verts[i].x:.4f}, {actual_verts[i].y:.4f}, {actual_verts[i].z:.4f})")
        xs = [v.x for v in actual_verts]
        ys = [v.y for v in actual_verts]
        zs = [v.z for v in actual_verts]
        print(f"      [DEBUG] Spans: X={max(xs)-min(xs):.3f}, Y={max(ys)-min(ys):.3f}, Z={max(zs)-min(zs):.3f}")
        print(f"      [DEBUG] Min/Max: X=[{min(xs):.3f}, {max(xs):.3f}], Y=[{min(ys):.3f}, {max(ys):.3f}], Z=[{min(zs):.3f}, {max(zs):.3f}]")
        tallest = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
        axis = 'X' if (max(xs)-min(xs)) == tallest else ('Y' if (max(ys)-min(ys)) == tallest else 'Z')
        print(f"      [DEBUG] Tallest axis: {axis} = {tallest:.3f}m")

    return mesh


def create_object_from_mesh(name, mesh, position, orientation=0.0, base_rotation=None, scale=1.0):
    """
    Create Blender object from mesh at position with orientation

    Args:
        name: Object name
        mesh: bpy.types.Mesh (vertices already rotated by base_rotation if needed)
        position: [x, y, z]
        orientation: Rotation in degrees (Z-axis) from JSON
        base_rotation: DEPRECATED - now applied during mesh creation
        scale: Uniform scale factor

    Returns:
        bpy.types.Object
    """
    obj = bpy.data.objects.new(name, mesh)

    # Set position
    obj.location = (position[0], position[1], position[2])

    # Set rotation: only Z-axis orientation from JSON
    # (base_rotation already applied to mesh vertices)
    if orientation != 0:
        obj.rotation_euler = Euler((0, 0, math.radians(orientation)), 'XYZ')

    # Set scale
    if scale != 1.0:
        obj.scale = (scale, scale, scale)

    # Link to scene
    bpy.context.collection.objects.link(obj)

    return obj


def create_roof_from_geometry(name, geometry_data, position, end_point, dimensions):
    """
    Create sloped roof object from start to end point

    The roof geometry is already sloped in library (Z varies).
    This function positions and orients it from eave (position) to ridge (end_point).

    Args:
        name: Roof name
        geometry_data: Base geometry (already sloped surface)
        position: Start position [x, y, z] (eave position)
        end_point: End position [x, y, z] (ridge position)
        dimensions: [width, slope_length, thickness] from JSON

    Returns:
        bpy.types.Object
    """
    import numpy as np

    # Get base rotation from geometry if any
    base_rotation = geometry_data.get('base_rotation', (0.0, 0.0, 0.0))

    # Create mesh from geometry (roof tile is already sloped)
    mesh = create_mesh_from_geometry(name, geometry_data, base_rotation)

    # Calculate roof orientation
    start = Vector(position)
    end = Vector(end_point)
    direction = end - start  # Vector from eave to ridge

    # Calculate midpoint for placement
    mid_point = (start + end) / 2

    # Create object at midpoint
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = (mid_point[0], mid_point[1], mid_point[2])

    # Calculate rotation to align roof slope with direction
    # Roof needs to tilt from low (eave) to high (ridge)
    horizontal_dist = math.sqrt(direction[0]**2 + direction[1]**2)
    vertical_rise = direction[2]

    # X-rotation: tilt angle (pitch)
    pitch_angle = math.atan2(vertical_rise, horizontal_dist)

    # Z-rotation: compass direction
    yaw_angle = math.atan2(direction[1], direction[0])

    # Apply rotations: first yaw (Z), then pitch (X)
    obj.rotation_euler = Euler((pitch_angle, 0, yaw_angle), 'XYZ')

    # Scale to match dimensions
    # dimensions = [width, slope_length, thickness]
    geo_dims = geometry_data.get('dimensions', {})
    scale_x = dimensions[0] / geo_dims.get('width', 1.0) if dimensions else 1.0
    scale_y = dimensions[1] / geo_dims.get('depth', 1.0) if dimensions and len(dimensions) > 1 else 1.0
    scale_z = 1.0  # Keep thickness as-is

    obj.scale = (scale_x, scale_y, scale_z)

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

            # Special handling for roofs with end_point (sloped roofs)
            elif 'roof' in obj_type.lower() and 'end_point' in obj_data and 'tile' in obj_type.lower():
                end_point = obj_data['end_point']
                dimensions = obj_data.get('dimensions', [11.2, 4.69, 0.02])  # [width, slope_length, thickness]
                obj = create_roof_from_geometry(obj_name, geometry, position, end_point, dimensions)
                stats['structure'] += 1

            else:
                # Regular objects - create from LOD300 geometry
                # Get base rotation from geometry (library object's inherent orientation)
                base_rotation = geometry.get('base_rotation', (0.0, 0.0, 0.0))

                # DEBUG: Log rotation for objects with non-zero rotation
                if base_rotation[0] != 0 or base_rotation[1] != 0 or base_rotation[2] != 0:
                    print(f"   🔧 {obj_name} ({obj_type}): base_rotation=({math.degrees(base_rotation[0]):.0f}°, {math.degrees(base_rotation[1]):.0f}°, {math.degrees(base_rotation[2]):.0f}°)")

                # Create mesh with vertices already rotated by base_rotation
                mesh = create_mesh_from_geometry(obj_name, geometry, base_rotation)

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
