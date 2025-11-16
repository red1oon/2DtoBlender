#!/usr/bin/env python3
"""
Add Geometries to Database (Schema v2 - Matches Working IFC Database)

Populates:
- base_geometries (geometry_hash as PRIMARY KEY, stores unique geometry blobs)
- element_instances (links guid → geometry_hash)
- elements_rtree (spatial index using elements_meta.id)

Usage:
    python3 add_geometries_v2.py <database_path>
"""

import sys
import sqlite3
import struct
import hashlib
from pathlib import Path


def create_box_mesh(x, y, z, width=1.0, height=1.0, depth=1.0):
    """
    Create a simple box mesh as a binary blob.

    Returns tessellated mesh data in a simple format:
    - 4 bytes: vertex count
    - 4 bytes: face count
    - Vertices: count * (3 floats for x,y,z)
    - Faces: count * (3 ints for triangle indices)
    """
    # Box vertices (8 corners)
    hw, hh, hd = width/2, height/2, depth/2
    vertices = [
        (x-hw, y-hd, z-hh),  # 0: front-bottom-left
        (x+hw, y-hd, z-hh),  # 1: front-bottom-right
        (x+hw, y+hd, z-hh),  # 2: back-bottom-right
        (x-hw, y+hd, z-hh),  # 3: back-bottom-left
        (x-hw, y-hd, z+hh),  # 4: front-top-left
        (x+hw, y-hd, z+hh),  # 5: front-top-right
        (x+hw, y+hd, z+hh),  # 6: back-top-right
        (x-hw, y+hd, z+hh),  # 7: back-top-left
    ]

    # Box faces (12 triangles, 2 per face)
    faces = [
        # Bottom
        (0, 1, 2), (0, 2, 3),
        # Top
        (4, 6, 5), (4, 7, 6),
        # Front
        (0, 5, 1), (0, 4, 5),
        # Back
        (3, 2, 6), (3, 6, 7),
        # Left
        (0, 3, 7), (0, 7, 4),
        # Right
        (1, 5, 6), (1, 6, 2),
    ]

    # Pack into binary format
    data = bytearray()

    # Header: vertex count, face count
    data.extend(struct.pack('I', len(vertices)))
    data.extend(struct.pack('I', len(faces)))

    # Vertices (x, y, z as floats)
    for vx, vy, vz in vertices:
        data.extend(struct.pack('fff', vx, vy, vz))

    # Faces (indices as ints)
    for f0, f1, f2 in faces:
        data.extend(struct.pack('III', f0, f1, f2))

    return bytes(data)


def calculate_geometry_hash(geometry_blob):
    """Calculate SHA256 hash of geometry for deduplication"""
    return hashlib.sha256(geometry_blob).hexdigest()


def get_element_size(ifc_class):
    """Get scaled element size for 5.4km DXF building"""
    SCALE = 77.0  # DXF building is 77× larger than typical IFC

    sizes = {
        'IfcWall': (0.2 * SCALE, 3.0 * SCALE, 0.15 * SCALE),
        'IfcWindow': (1.2 * SCALE, 1.5 * SCALE, 0.1 * SCALE),
        'IfcDoor': (1.0 * SCALE, 2.1 * SCALE, 0.05 * SCALE),
        'IfcColumn': (0.4 * SCALE, 3.0 * SCALE, 0.4 * SCALE),
        'IfcBeam': (0.3 * SCALE, 0.5 * SCALE, 2.0 * SCALE),
        'IfcSlab': (3.0 * SCALE, 3.0 * SCALE, 0.2 * SCALE),
        'IfcFurniture': (0.6 * SCALE, 0.6 * SCALE, 0.8 * SCALE),
        'IfcPipeSegment': (0.1 * SCALE, 0.1 * SCALE, 1.0 * SCALE),
        'IfcDuctSegment': (0.4 * SCALE, 0.3 * SCALE, 1.0 * SCALE),
        'IfcLightFixture': (0.3 * SCALE, 0.3 * SCALE, 0.1 * SCALE),
        'IfcFireSuppressionTerminal': (0.1 * SCALE, 0.1 * SCALE, 0.1 * SCALE),
        'IfcAirTerminal': (0.4 * SCALE, 0.4 * SCALE, 0.2 * SCALE),
        'IfcBuildingElementProxy': (0.5 * SCALE, 0.5 * SCALE, 0.5 * SCALE),
    }

    return sizes.get(ifc_class, (0.5 * SCALE, 0.5 * SCALE, 0.5 * SCALE))


def add_geometries_to_database(db_path):
    """Add geometries following working IFC database schema"""
    db_path = Path(db_path)

    if not db_path.exists():
        print(f"❌ Error: Database not found: {db_path}")
        return False

    print(f"📂 Opening database: {db_path.name}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Clear existing data
    print("⚠️  Clearing existing geometries...")
    cursor.execute("DELETE FROM element_instances")
    cursor.execute("DELETE FROM base_geometries")
    cursor.execute("DELETE FROM elements_rtree")

    # Get all elements with positions
    print("🎯 Fetching element data...")
    cursor.execute("""
        SELECT
            m.id,
            m.guid,
            m.ifc_class,
            t.center_x,
            t.center_y,
            t.center_z
        FROM elements_meta m
        JOIN element_transforms t ON m.guid = t.guid
    """)

    elements = cursor.fetchall()
    print(f"✅ Found {len(elements)} elements")

    # Track unique geometries
    geometry_cache = {}  # geometry_hash -> (vertices_blob, faces_blob, vertex_count, face_count)

    print("🔨 Generating geometries...")
    inserted_geom = 0
    inserted_inst = 0

    for elem_id, guid, ifc_class, x, y, z in elements:
        # Get element size
        width, height, depth = get_element_size(ifc_class)

        # Create geometry
        geometry_blob = create_box_mesh(x, y, z, width, height, depth)
        geometry_hash = calculate_geometry_hash(geometry_blob)

        # Store unique geometry if not seen before
        if geometry_hash not in geometry_cache:
            # Split blob into vertices and faces
            # Format: [vertex_count][face_count][vertices...][faces...]
            vertex_count = struct.unpack('I', geometry_blob[0:4])[0]
            face_count = struct.unpack('I', geometry_blob[4:8])[0]

            # Vertices start at byte 8, each vertex is 3 floats (12 bytes)
            vertex_size = vertex_count * 3 * 4
            vertices_blob = geometry_blob[8:8+vertex_size]

            # Faces start after vertices, each face is 3 ints (12 bytes)
            faces_blob = geometry_blob[8+vertex_size:]

            # Insert into base_geometries
            cursor.execute("""
                INSERT INTO base_geometries
                (geometry_hash, vertices, faces, normals, vertex_count, face_count)
                VALUES (?, ?, ?, NULL, ?, ?)
            """, (geometry_hash, vertices_blob, faces_blob, vertex_count, face_count))

            geometry_cache[geometry_hash] = True
            inserted_geom += 1

        # Link element to geometry via element_instances
        cursor.execute("""
            INSERT INTO element_instances (guid, geometry_hash)
            VALUES (?, ?)
        """, (guid, geometry_hash))

        inserted_inst += 1

        # Update R-tree with actual bbox
        hw, hh, hd = width/2, height/2, depth/2
        bbox_min_x, bbox_min_y, bbox_min_z = x-hw, y-hd, z-hh
        bbox_max_x, bbox_max_y, bbox_max_z = x+hw, y+hd, z+hh

        cursor.execute("""
            INSERT INTO elements_rtree (id, minX, maxX, minY, maxY, minZ, maxZ)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (elem_id, bbox_min_x, bbox_max_x, bbox_min_y, bbox_max_y, bbox_min_z, bbox_max_z))

        if inserted_inst % 1000 == 0:
            print(f"  Progress: {inserted_inst}/{len(elements)} ({inserted_inst/len(elements)*100:.1f}%)")

    conn.commit()
    conn.close()

    print(f"\n✅ Successfully populated geometry tables")
    print(f"📊 Statistics:")
    print(f"   - Elements: {len(elements):,}")
    print(f"   - Unique geometries: {inserted_geom:,}")
    print(f"   - Element instances: {inserted_inst:,}")
    print(f"   - Spatial index entries: {inserted_inst:,}")

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 add_geometries_v2.py <database_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    success = add_geometries_to_database(db_path)

    if success:
        print("\n🎉 Database ready for Bonsai Federation Preview!")
    else:
        print("\n❌ Failed to add geometries")
        sys.exit(1)


if __name__ == '__main__':
    main()
