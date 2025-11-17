#!/usr/bin/env python3
"""Add geometry to existing devices in database (sprinklers, lights)"""
import sqlite3
import struct
import hashlib

def pack_vertices(vertices):
    return struct.pack(f'<{len(vertices)*3}f', *[coord for v in vertices for coord in v])

def pack_faces(faces):
    return struct.pack(f'<{len(faces)*3}I', *[idx for f in faces for idx in f])

def pack_normals(normals):
    return struct.pack(f'<{len(normals)*3}f', *[coord for n in normals for coord in n])

def compute_hash(v_blob, f_blob):
    h = hashlib.sha256()
    h.update(v_blob)
    h.update(f_blob)
    return h.hexdigest()[:32]

def add_device_geometries(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all devices without geometry
    cursor.execute("""
        SELECT e.guid, t.center_x, t.center_y, t.center_z
        FROM elements_meta e
        JOIN element_transforms t ON e.guid = t.guid
        LEFT JOIN base_geometries g ON e.guid = g.guid
        WHERE e.element_name LIKE 'Generated_%'
          AND g.guid IS NULL
    """)
    
    devices = cursor.fetchall()
    print(f"Found {len(devices)} devices without geometry")
    
    if not devices:
        print("✅ All devices already have geometry")
        conn.close()
        return
    
    # Generate box geometry for each device
    size = 0.2  # 20cm cube
    half = size / 2
    
    added = 0
    for guid, x, y, z in devices:
        vertices = [
            (x - half, y - half, z - half),
            (x + half, y - half, z - half),
            (x + half, y + half, z - half),
            (x - half, y + half, z - half),
            (x - half, y - half, z + half),
            (x + half, y - half, z + half),
            (x + half, y + half, z + half),
            (x - half, y + half, z + half),
        ]
        faces = [(0,1,2), (0,2,3), (4,5,6), (4,6,7), (0,1,5), (0,5,4), (2,3,7), (2,7,6), (0,3,7), (0,7,4), (1,2,6), (1,6,5)]
        normals = [(0,0,-1), (0,0,-1), (0,0,1), (0,0,1), (0,-1,0), (0,-1,0), (0,1,0), (0,1,0), (-1,0,0), (-1,0,0), (1,0,0), (1,0,0)]
        
        v_blob = pack_vertices(vertices)
        f_blob = pack_faces(faces)
        n_blob = pack_normals(normals)
        geom_hash = compute_hash(v_blob, f_blob)
        
        cursor.execute("""
            INSERT OR REPLACE INTO base_geometries (guid, geometry_hash, vertices, faces, normals)
            VALUES (?, ?, ?, ?, ?)
        """, (guid, geom_hash, v_blob, f_blob, n_blob))
        
        added += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ Added geometry to {added} devices")

if __name__ == "__main__":
    add_device_geometries("Terminal1_MainBuilding_FILTERED.db")
