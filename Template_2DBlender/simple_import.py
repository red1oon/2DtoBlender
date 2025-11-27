#!/usr/bin/env python3
"""Simple Blender Import - No Collection Management"""

import bpy
import json
import sys
import math
from mathutils import Euler


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def create_box(name, position, dimensions, rotation_z=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (
        dimensions.get('width', 0.1) / 2,
        dimensions.get('length', 0.1) / 2,
        dimensions.get('height', 0.1) / 2
    )
    if rotation_z != 0:
        obj.rotation_euler = Euler((0, 0, math.radians(rotation_z)), 'XYZ')
    return obj


def create_wall(name, position, end_point, thickness, height):
    from mathutils import Vector
    start = Vector(position)
    end = Vector(end_point)
    direction = end - start
    length = direction.length
    mid_point = (start + end) / 2

    bpy.ops.mesh.primitive_cube_add(size=1, location=(mid_point[0], mid_point[1], height/2))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (length / 2, thickness / 2, height / 2)
    angle = math.atan2(direction[1], direction[0])
    obj.rotation_euler = Euler((0, 0, angle), 'XYZ')
    return obj


def import_objects(json_file):
    with open(json_file) as f:
        data = json.load(f)

    objects = data.get('objects_complete', [])
    print(f"Importing {len(objects)} objects...")

    clear_scene()
    counts = {'wall': 0, 'door': 0, 'window': 0, 'fixture': 0, 'structural': 0}

    for obj_data in objects:
        try:
            obj_type = obj_data.get('type', 'fixture')
            obj_name = obj_data.get('object_id') or obj_data.get('name', 'unnamed')
            position = obj_data.get('position', [0, 0, 0])
            dimensions = obj_data.get('dimensions', {})
            rotation_z = obj_data.get('orientation', {}).get('rotation_z', 0)

            if obj_type == 'wall' and 'end_point' in obj_data:
                end_point = obj_data['end_point']
                thickness = dimensions.get('thickness', 0.1)
                height = dimensions.get('height', 3.0)
                create_wall(obj_name, position, end_point, thickness, height)
            else:
                create_box(obj_name, position, dimensions, rotation_z)

            counts[obj_type] = counts.get(obj_type, 0) + 1

        except Exception as e:
            print(f"Error importing {obj_name}: {e}")

    print(f"✅ Imported: Structural:{counts.get('structural',0)}, Walls:{counts['wall']}, Doors:{counts['door']}, Windows:{counts['window']}, Fixtures:{counts['fixture']}")
    return counts


# Main
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]

if len(argv) >= 1:
    json_file = argv[0]
    output_file = argv[1] if len(argv) > 1 else 'model.blend'

    import_objects(json_file)
    bpy.ops.wm.save_as_mainfile(filepath=output_file)
    print(f"✅ Saved: {output_file}")
