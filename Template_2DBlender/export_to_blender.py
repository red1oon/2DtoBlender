#!/usr/bin/env python3
"""
Export Coordinated Elements to Blender (Rule 0 Compliant)
==========================================================
Reads coordinated_elements.db and generates Blender .blend file.
Uses LOD300 geometry from Ifc_Object_Library.db via library_query.
Pure deterministic geometry generation - no AI/ML.
"""

import sqlite3
import json
import sys
from pathlib import Path

# Add core directory to path
sys.path.insert(0, str(Path(__file__).parent / 'core'))
from library_query import LibraryQuery


def generate_blender_script(db_path: str, gridtruth_path: str, library_path: str = "Ifc_Object_Library.db") -> str:
    """Generate Blender Python script from coordinated elements using LOD300 geometry"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Load GridTruth
    with open(gridtruth_path) as f:
        gridtruth = json.load(f)

    # Initialize library query for LOD300 geometry
    try:
        lib = LibraryQuery(library_path)
        print(f"✓ Connected to geometry library: {library_path}")
    except FileNotFoundError:
        print(f"⚠️  Library not found: {library_path} - using fallback geometry")
        lib = None

    script = """import bpy
import bmesh
import math
from mathutils import Vector, Euler

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create collection
collection = bpy.data.collections.new("TB-LKTN_HOUSE")
bpy.context.scene.collection.children.link(collection)

def create_lod300_mesh(name, vertices, faces, x, y, z, rotation_z=0):
    \"\"\"Create mesh from LOD300 geometry with position and rotation\"\"\"
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    # Create mesh from vertices and faces
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    # Set position
    obj.location = (x, y, z)

    # Set rotation
    if rotation_z != 0:
        obj.rotation_euler = Euler((0, 0, math.radians(rotation_z)), 'XYZ')

    return obj

def create_wall(name, start, end, height):
    \"\"\"Create wall as extruded rectangle\"\"\"
    thickness = 0.15  # 150mm

    # Create mesh
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    bm = bmesh.new()

    # Wall vertices (rectangle)
    x0, y0 = start
    x1, y1 = end

    # Calculate perpendicular offset for thickness
    dx = x1 - x0
    dy = y1 - y0
    length = (dx**2 + dy**2)**0.5

    if length > 0.001:
        nx = -dy / length * thickness / 2
        ny = dx / length * thickness / 2

        # Bottom face
        v1 = bm.verts.new((x0 + nx, y0 + ny, 0))
        v2 = bm.verts.new((x1 + nx, y1 + ny, 0))
        v3 = bm.verts.new((x1 - nx, y1 - ny, 0))
        v4 = bm.verts.new((x0 - nx, y0 - ny, 0))

        # Top face
        v5 = bm.verts.new((x0 + nx, y0 + ny, height))
        v6 = bm.verts.new((x1 + nx, y1 + ny, height))
        v7 = bm.verts.new((x1 - nx, y1 - ny, height))
        v8 = bm.verts.new((x0 - nx, y0 - ny, height))

        # Create faces
        bm.faces.new([v1, v2, v3, v4])  # Bottom
        bm.faces.new([v5, v6, v7, v8])  # Top
        bm.faces.new([v1, v2, v6, v5])  # Side 1
        bm.faces.new([v2, v3, v7, v6])  # Side 2
        bm.faces.new([v3, v4, v8, v7])  # Side 3
        bm.faces.new([v4, v1, v5, v8])  # Side 4

    bm.to_mesh(mesh)
    bm.free()

    return obj

# Building envelope from GridTruth
"""

    # Add building envelope
    envelope = gridtruth["building_envelope"]
    setback = gridtruth["building_parameters"]["wall_setback_from_grid"]
    max_x = gridtruth["grid_horizontal"]["E"]
    max_y = gridtruth["grid_vertical"]["5"]
    height = gridtruth["elevations"]["ceiling"]

    script += f"""
# Exterior walls
wall_south = create_wall("WALL_SOUTH", [{setback}, {setback}], [{max_x - setback}, {setback}], {height})
wall_east = create_wall("WALL_EAST", [{max_x - setback}, {setback}], [{max_x - setback}, {max_y - setback}], {height})
wall_north = create_wall("WALL_NORTH", [{max_x - setback}, {max_y - setback}], [{setback}, {max_y - setback}], {height})
wall_west = create_wall("WALL_WEST", [{setback}, {max_y - setback}], [{setback}, {setback}], {height})

# Set wall material
for wall in [wall_south, wall_east, wall_north, wall_west]:
    wall.display_type = 'SOLID'
    wall.color = (0.8, 0.8, 0.8, 1.0)

"""

    # Add doors with LOD300 geometry
    cursor.execute("""
        SELECT element_id, x, y, z, width_m, height_m, rotation_z
        FROM coordinated_elements
        WHERE ifc_class = 'IfcDoor'
        ORDER BY element_id
    """)

    script += "\n# Doors (LOD300 geometry)\n"
    doors = cursor.fetchall()
    for elem_id, x, y, z, w, h, rot in doors:
        rot = rot if rot is not None else 0
        width_mm = int(w * 1000)
        height_mm = int(h * 1000)

        # Fetch LOD300 geometry
        if lib:
            door_geom = lib.get_door_geometry(width_mm, height_mm)
            if door_geom:
                vertices = [list(v) for v in door_geom['vertices']]
                faces = [list(f) for f in door_geom['faces']]
                script += f"# Door {elem_id}: {width_mm}x{height_mm}mm - {door_geom['object_type']}\n"
                script += f"door_{elem_id}_verts = {vertices}\n"
                script += f"door_{elem_id}_faces = {faces}\n"
                script += f"door_{elem_id} = create_lod300_mesh('{elem_id}', door_{elem_id}_verts, door_{elem_id}_faces, {x}, {y}, {z}, {rot})\n"
                script += f"door_{elem_id}.color = (0.6, 0.3, 0.1, 1.0)\n"
            else:
                print(f"⚠️  No LOD300 geometry for door {width_mm}x{height_mm}mm, skipping")
        else:
            print(f"⚠️  Library not available for door {elem_id}")

    # Add windows with LOD300 geometry
    cursor.execute("""
        SELECT element_id, x, y, z, width_m, height_m, rotation_z
        FROM coordinated_elements
        WHERE ifc_class = 'IfcWindow'
        ORDER BY element_id
    """)

    script += "\n# Windows (LOD300 geometry)\n"
    windows = cursor.fetchall()
    for elem_id, x, y, z, w, h, rot in windows:
        rot = rot if rot is not None else 0
        width_mm = int(w * 1000)
        height_mm = int(h * 1000)

        # Fetch LOD300 geometry
        if lib:
            window_geom = lib.get_window_geometry(width_mm, height_mm)
            if window_geom:
                vertices = [list(v) for v in window_geom['vertices']]
                faces = [list(f) for f in window_geom['faces']]
                script += f"# Window {elem_id}: {width_mm}x{height_mm}mm - {window_geom['object_type']}\n"
                script += f"window_{elem_id}_verts = {vertices}\n"
                script += f"window_{elem_id}_faces = {faces}\n"
                script += f"window_{elem_id} = create_lod300_mesh('{elem_id}', window_{elem_id}_verts, window_{elem_id}_faces, {x}, {y}, {z}, {rot})\n"
                script += f"window_{elem_id}.color = (0.4, 0.6, 0.9, 1.0)\n"
            else:
                print(f"⚠️  No LOD300 geometry for window {width_mm}x{height_mm}mm, skipping")
        else:
            print(f"⚠️  Library not available for window {elem_id}")

    script += """
# Select all for verification
bpy.ops.object.select_all(action='SELECT')

print("✓ Building created with LOD300 geometry")
print(f"  Objects: {len(bpy.data.objects)}")
print(f"  Meshes: {len([o for o in bpy.data.objects if o.type == 'MESH'])}")
"""

    conn.close()
    if lib:
        lib.close()

    return script


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 export_to_blender.py <coordinated_db> [library_db]")
        sys.exit(1)

    db_path = sys.argv[1]
    library_path = sys.argv[2] if len(sys.argv) > 2 else "Ifc_Object_Library.db"
    gridtruth_path = "GridTruth_TB-LKTN.json"
    script_path = "output_artifacts/blender_script.py"
    blend_path = "output_artifacts/TB-LKTN_HOUSE.blend"

    print("=" * 70)
    print("EXPORT TO BLENDER (LOD300)")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Library: {library_path}")
    print(f"GridTruth: {gridtruth_path}")
    print()

    # Generate script with LOD300 geometry
    print("Generating Blender script with LOD300 geometry...")
    script = generate_blender_script(db_path, gridtruth_path, library_path)

    # Add save command to script
    script += f"\n# Save file\nbpy.ops.wm.save_as_mainfile(filepath='{Path(blend_path).absolute()}')\nprint('✓ Saved to {blend_path}')\n"

    with open(script_path, 'w') as f:
        f.write(script)
    print(f"  ✓ Saved to {script_path}")

    # Execute in Blender
    print("\nRunning Blender...")
    import subprocess

    blender_path = "/home/red1/blender-4.2.14/blender"
    cmd = [
        blender_path,
        "--background",
        "--python", str(Path(script_path).absolute())
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if "Saved to" in result.stdout or Path(blend_path).exists():
        print(f"\n✓ Saved to {blend_path}")
        print("=" * 70)
    else:
        print(f"\n✗ Blender error:")
        print(result.stderr[-500:])

    print("\nTo view: blender", blend_path)


if __name__ == "__main__":
    main()
