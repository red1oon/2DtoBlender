#!/usr/bin/env python3
"""
Import JSON to Blender with Orientations

Imports complete JSON dataset into Blender with:
- Positioned objects (walls, doors, windows, fixtures, structural)
- Proper rotations for doors/windows
- Color coding by type
- Collections for organization
"""

import bpy
import json
import sys
import math
from mathutils import Vector, Euler


def clear_scene():
    """Clear default scene objects"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def create_collections():
    """Create organized collections"""
    collections = {
        'Structural': bpy.data.collections.new('Structural'),
        'Walls': bpy.data.collections.new('Walls'),
        'Doors': bpy.data.collections.new('Doors'),
        'Windows': bpy.data.collections.new('Windows'),
        'Fixtures': bpy.data.collections.new('Fixtures')
    }

    for col in collections.values():
        bpy.context.scene.collection.children.link(col)

    return collections


def create_material(name, color):
    """Create colored material"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = color
    return mat


def create_box(name, position, dimensions, rotation_z=0):
    """Create a box mesh at position with rotation"""
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(position[0], position[1], position[2])
    )

    obj = bpy.context.active_object
    obj.name = name

    # Scale to dimensions
    obj.scale = (
        dimensions.get('width', 0.1) / 2,
        dimensions.get('length', 0.1) / 2,
        dimensions.get('height', 0.1) / 2
    )

    # Apply rotation (Z-axis)
    if rotation_z != 0:
        obj.rotation_euler = Euler((0, 0, math.radians(rotation_z)), 'XYZ')

    return obj


def create_wall(name, position, end_point, thickness, height):
    """Create wall as line extruded to thickness and height"""
    # Calculate wall vector
    start = Vector(position)
    end = Vector(end_point)

    direction = end - start
    length = direction.length
    mid_point = (start + end) / 2

    # Create box for wall
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(mid_point[0], mid_point[1], height/2)
    )

    obj = bpy.context.active_object
    obj.name = name

    # Scale
    obj.scale = (length / 2, thickness / 2, height / 2)

    # Rotate to align with wall direction
    angle = math.atan2(direction[1], direction[0])
    obj.rotation_euler = Euler((0, 0, angle), 'XYZ')

    return obj


def import_objects(json_file):
    """Import all objects from JSON"""

    print("="*80)
    print("IMPORTING TO BLENDER")
    print("="*80)
    print()

    with open(json_file) as f:
        data = json.load(f)

    objects = data.get('objects_complete', [])

    print(f"Found {len(objects)} objects to import")
    print()

    # Clear scene
    clear_scene()

    # Create collections
    collections = create_collections()

    # Create materials
    materials = {
        'wall': create_material('Wall_Material', (0.8, 0.8, 0.8, 1.0)),
        'door': create_material('Door_Material', (0.6, 0.3, 0.1, 1.0)),
        'window': create_material('Window_Material', (0.5, 0.7, 1.0, 0.7)),
        'fixture': create_material('Fixture_Material', (1.0, 0.9, 0.7, 1.0)),
        'structural': create_material('Structural_Material', (0.5, 0.5, 0.5, 1.0))
    }

    # Import by type
    counts = {'wall': 0, 'door': 0, 'window': 0, 'fixture': 0, 'structural': 0}

    for obj_data in objects:
        obj_type = obj_data.get('type', 'fixture')
        obj_name = obj_data.get('object_id') or obj_data.get('name', 'unnamed')
        position = obj_data.get('position', [0, 0, 0])
        dimensions = obj_data.get('dimensions', {})

        # Get rotation for doors/windows
        rotation_z = 0
        if 'orientation' in obj_data:
            rotation_z = obj_data['orientation'].get('rotation_z', 0)

        # Create object based on type
        if obj_type == 'wall' and 'end_point' in obj_data:
            # Wall (line segment)
            end_point = obj_data['end_point']
            thickness = dimensions.get('thickness', 0.1)
            height = dimensions.get('height', 3.0)

            obj = create_wall(obj_name, position, end_point, thickness, height)
            obj.data.materials.append(materials['wall'])
            collections['Walls'].objects.link(obj)
            if obj.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(obj)
            counts['wall'] += 1

        elif obj_type in ['door', 'window']:
            # Door/Window with rotation
            obj = create_box(obj_name, position, dimensions, rotation_z)
            obj.data.materials.append(materials[obj_type])

            if obj_type == 'door':
                collections['Doors'].objects.link(obj)
            else:
                collections['Windows'].objects.link(obj)

            if obj.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(obj)
            counts[obj_type] += 1

        elif obj_type == 'structural':
            # Structural elements (floor, roof, etc.)
            obj = create_box(obj_name, position, dimensions)
            obj.data.materials.append(materials['structural'])
            collections['Structural'].objects.link(obj)
            if obj.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(obj)
            counts['structural'] += 1

        elif obj_type == 'fixture':
            # Fixtures (sanitary, equipment, etc.)
            obj = create_box(obj_name, position, dimensions)
            obj.data.materials.append(materials['fixture'])
            collections['Fixtures'].objects.link(obj)
            if obj.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(obj)
            counts['fixture'] += 1

    print()
    print("Import Summary:")
    print(f"  Structural: {counts['structural']}")
    print(f"  Walls:      {counts['wall']}")
    print(f"  Doors:      {counts['door']} (with rotation)")
    print(f"  Windows:    {counts['window']} (with rotation)")
    print(f"  Fixtures:   {counts['fixture']}")
    print(f"  TOTAL:      {sum(counts.values())}")
    print()

    # Set viewport shading
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'SOLID'
                    space.shading.show_xray = True
                    space.shading.xray_alpha = 0.5

    # Frame all objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.view3d.view_all()

    print("✅ Import complete!")
    print()
    print("Viewport Settings:")
    print("  - Shading: Solid with X-ray")
    print("  - Collections: Organized by type")
    print("  - Colors: Wall(gray), Door(brown), Window(blue), Fixture(cream), Structural(dark gray)")
    print()


def main():
    # Remove Blender's script arguments
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    if len(argv) < 1:
        print("Usage: blender --background --python import_to_blender.py -- <input.json> [output.blend]")
        return

    json_file = argv[0]
    output_file = argv[1] if len(argv) > 1 else 'model_with_orientation.blend'

    # Import objects
    import_objects(json_file)

    # Save blend file
    bpy.ops.wm.save_as_mainfile(filepath=output_file)
    print(f"✅ Saved to: {output_file}")


if __name__ == "__main__":
    main()
