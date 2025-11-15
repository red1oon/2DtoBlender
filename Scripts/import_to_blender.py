"""
Import Generated Database into Blender

Usage in Blender Python Console:
    import sys
    sys.path.insert(0, '/home/red1/Documents/bonsai/2Dto3D/Scripts')

    import import_to_blender
    import_to_blender.import_database('/home/red1/Documents/bonsai/2Dto3D/Generated_Terminal1_SAMPLE.db')

Or run as script:
    ~/blender-4.2.14/blender --python import_to_blender.py -- /path/to/database.db
"""

import bpy
import bmesh
import sqlite3
import struct
from pathlib import Path
from collections import defaultdict


def parse_box_geometry(blob):
    """Parse binary box geometry blob into vertices and faces."""
    # Read header
    vertex_count = struct.unpack('I', blob[0:4])[0]
    face_count = struct.unpack('I', blob[4:8])[0]

    offset = 8

    # Read vertices
    vertices = []
    for i in range(vertex_count):
        x, y, z = struct.unpack('fff', blob[offset:offset+12])
        vertices.append((x, y, z))
        offset += 12

    # Read faces
    faces = []
    for i in range(face_count):
        f0, f1, f2 = struct.unpack('III', blob[offset:offset+12])
        faces.append((f0, f1, f2))
        offset += 12

    return vertices, faces


def create_mesh_object(name, guid, vertices, faces):
    """Create a Blender mesh object from vertices and faces."""
    # Create mesh
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)

    # Link to scene
    bpy.context.collection.objects.link(obj)

    # Build mesh from vertices and faces
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    # Store GUID as custom property
    obj['guid'] = guid

    return obj


def get_discipline_color(discipline):
    """Get color for discipline grouping."""
    colors = {
        'Seating': (0.8, 0.6, 0.4, 1.0),          # Tan (Architecture)
        'Fire_Protection': (1.0, 0.2, 0.2, 1.0),  # Red
        'Structure': (0.5, 0.5, 0.5, 1.0),        # Gray
        'ACMV': (0.2, 0.6, 1.0, 1.0),            # Light Blue
        'Electrical': (1.0, 1.0, 0.2, 1.0),      # Yellow
        'Plumbing': (0.2, 0.2, 1.0, 1.0),        # Blue
        'Chilled_Water': (0.2, 0.8, 0.8, 1.0),   # Cyan
        'LPG': (1.0, 0.5, 0.0, 1.0),             # Orange
    }
    return colors.get(discipline, (0.7, 0.7, 0.7, 1.0))


def import_database(db_path, limit=None):
    """
    Import elements from database into Blender.

    Args:
        db_path: Path to SQLite database
        limit: Optional limit on number of elements to import (for testing)
    """
    db_path = Path(db_path)

    if not db_path.exists():
        print(f"❌ Error: Database not found: {db_path}")
        return

    print(f"\n{'='*70}")
    print(f"Importing Database: {db_path.name}")
    print(f"{'='*70}\n")

    # Connect to database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    required_tables = ['elements_meta', 'element_transforms', 'base_geometries']
    missing = [t for t in required_tables if t not in tables]

    if missing:
        print(f"❌ Error: Missing required tables: {missing}")
        conn.close()
        return

    # Get element count
    cursor.execute("SELECT COUNT(*) FROM elements_meta")
    total_elements = cursor.fetchone()[0]

    print(f"📊 Total elements in database: {total_elements}")
    if limit:
        print(f"   Importing first {limit} elements (testing)")

    # Get elements with geometries
    query = """
        SELECT
            m.guid,
            m.discipline,
            m.ifc_class,
            m.element_name,
            g.geometry_blob
        FROM elements_meta m
        JOIN base_geometries g ON m.guid = g.guid
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    elements = cursor.fetchall()

    print(f"✅ Loading {len(elements)} elements with geometries\n")

    # Create collections for each discipline
    collections = {}
    discipline_counts = defaultdict(int)

    # Clear existing objects (optional - comment out if you want to keep existing)
    # bpy.ops.object.select_all(action='SELECT')
    # bpy.ops.object.delete()

    # Import elements
    imported = 0
    errors = 0

    for guid, discipline, ifc_class, element_name, geometry_blob in elements:
        try:
            # Parse geometry
            vertices, faces = parse_box_geometry(geometry_blob)

            # Create collection for discipline if not exists
            if discipline not in collections:
                coll = bpy.data.collections.new(f"{discipline}")
                bpy.context.scene.collection.children.link(coll)
                collections[discipline] = coll

            # Create mesh object
            name = element_name or f"{ifc_class}_{imported}"
            obj = create_mesh_object(name, guid, vertices, faces)

            # Link to discipline collection
            bpy.context.collection.objects.unlink(obj)
            collections[discipline].objects.link(obj)

            # Store metadata
            obj['discipline'] = discipline
            obj['ifc_class'] = ifc_class

            # Set material/color by discipline
            mat_name = f"Material_{discipline}"
            if mat_name not in bpy.data.materials:
                mat = bpy.data.materials.new(mat_name)
                mat.diffuse_color = get_discipline_color(discipline)
                mat.use_nodes = False
            else:
                mat = bpy.data.materials[mat_name]

            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)

            imported += 1
            discipline_counts[discipline] += 1

            if imported % 500 == 0:
                print(f"  Progress: {imported}/{len(elements)} ({imported/len(elements)*100:.1f}%)")

        except Exception as e:
            errors += 1
            if errors <= 5:  # Show first 5 errors
                print(f"  ⚠️  Error importing {guid}: {e}")

    conn.close()

    # Summary
    print(f"\n{'='*70}")
    print(f"Import Complete!")
    print(f"{'='*70}\n")
    print(f"✅ Imported: {imported} elements")
    if errors:
        print(f"⚠️  Errors: {errors} elements failed")

    print(f"\n📊 Elements by Discipline:")
    for discipline, count in sorted(discipline_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {discipline}: {count} elements")

    print(f"\n📁 Collections created: {len(collections)}")
    print(f"   (Check Outliner → expand collections to see elements)")

    print(f"\n💡 Next steps:")
    print(f"   1. View → Frame All (Home key) to see all elements")
    print(f"   2. Toggle collections in Outliner to view by discipline")
    print(f"   3. Select objects to see metadata in Object Properties")

    return imported


def main():
    """Entry point when run as Blender script."""
    import sys

    # Get database path from command line args
    if '--' in sys.argv:
        args = sys.argv[sys.argv.index('--') + 1:]
        if args:
            db_path = args[0]
            limit = int(args[1]) if len(args) > 1 else None
            import_database(db_path, limit)
            return

    print("Usage:")
    print("  In Blender Python console:")
    print("    import import_to_blender")
    print("    import_to_blender.import_database('/path/to/database.db')")
    print("\n  Or run as script:")
    print("    blender --python import_to_blender.py -- /path/to/database.db [limit]")


if __name__ == '__main__':
    main()
