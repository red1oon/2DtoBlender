#!/usr/bin/env python3
"""
Database Geometry Fetcher - LOD300 Geometry from Ifc_Object_Library.db

Fetches actual LOD300 geometry blobs from database for Blender import
Eliminates placeholder boxes - uses real prefab geometry

Database Schema:
- object_catalog: object_type, geometry_hash, dimensions
- base_geometries: vertices BLOB, faces BLOB, normals BLOB

Binary Blob Format:
- vertices: float32 array [x1,y1,z1, x2,y2,z2, ...]
- faces: uint32 array [v1,v2,v3, v4,v5,v6, ...] (triangles)
- normals: float32 array [nx1,ny1,nz1, nx2,ny2,nz2, ...]

No AI - pure binary blob parsing and mesh construction
"""

import sqlite3
import struct
import numpy as np


class DatabaseGeometryFetcher:
    """Fetch LOD300 geometry from Ifc_Object_Library.db"""

    def __init__(self, database_path):
        """
        Initialize geometry fetcher

        Args:
            database_path: Path to Ifc_Object_Library.db
        """
        self.db_path = database_path
        self.connection = sqlite3.connect(database_path)
        self.cursor = self.connection.cursor()
        print(f"✅ Connected to geometry database: {database_path}")

    def fetch_geometry(self, object_type):
        """
        Fetch LOD300 geometry for object_type

        Args:
            object_type: Library ID (e.g., 'door_single_900_lod300')

        Returns:
            {
                'vertices': np.array([[x,y,z], ...]),  # Nx3 array
                'faces': np.array([[v1,v2,v3], ...]),  # Mx3 array (triangle indices)
                'normals': np.array([[nx,ny,nz], ...]), # Mx3 array
                'dimensions': {'width': float, 'depth': float, 'height': float},
                'metadata': {...}
            }
            or None if not found
        """
        # Query object_catalog for geometry_hash + base_rotation (if columns exist)
        # Gracefully handle databases without base_rotation columns
        try:
            self.cursor.execute("""
                SELECT oc.geometry_hash, oc.width_mm, oc.depth_mm, oc.height_mm,
                       oc.object_name, oc.ifc_class, oc.category,
                       oc.base_rotation_x, oc.base_rotation_y, oc.base_rotation_z
                FROM object_catalog oc
                WHERE oc.object_type = ?
                LIMIT 1
            """, (object_type,))

            row = self.cursor.fetchone()
            if not row:
                print(f"❌ Object type not found in database: {object_type}")
                return None

            geometry_hash, width_mm, depth_mm, height_mm, object_name, ifc_class, category, base_rot_x, base_rot_y, base_rot_z = row

        except Exception as e:
            # Fallback: base_rotation columns don't exist yet
            if "no such column: base_rotation" in str(e):
                print(f"⚠️  Database missing base_rotation columns - using fallback (0,0,0)")
            else:
                print(f"⚠️  Error reading base_rotation for {object_type}: {e} - using fallback")

            self.cursor.execute("""
                SELECT oc.geometry_hash, oc.width_mm, oc.depth_mm, oc.height_mm,
                       oc.object_name, oc.ifc_class, oc.category
                FROM object_catalog oc
                WHERE oc.object_type = ?
                LIMIT 1
            """, (object_type,))

            row = self.cursor.fetchone()
            if not row:
                print(f"❌ Object type not found in database: {object_type}")
                return None

            geometry_hash, width_mm, depth_mm, height_mm, object_name, ifc_class, category = row
            base_rot_x, base_rot_y, base_rot_z = 0.0, 0.0, 0.0  # Default: no rotation

        # Query base_geometries for binary blobs
        self.cursor.execute("""
            SELECT vertices, faces, normals, vertex_count, face_count
            FROM base_geometries
            WHERE geometry_hash = ?
        """, (geometry_hash,))

        geo_row = self.cursor.fetchone()
        if not geo_row:
            print(f"❌ Geometry not found for hash: {geometry_hash}")
            return None

        vertices_blob, faces_blob, normals_blob, vertex_count, face_count = geo_row

        # Parse binary blobs
        vertices = self._parse_vertices_blob(vertices_blob, vertex_count)
        faces = self._parse_faces_blob(faces_blob, face_count)
        normals = self._parse_normals_blob(normals_blob, face_count) if normals_blob else None

        # Dimensions in meters
        dimensions = {
            'width': width_mm / 1000.0 if width_mm else 0.1,
            'depth': depth_mm / 1000.0 if depth_mm else 0.1,
            'height': height_mm / 1000.0 if height_mm else 0.1
        }

        metadata = {
            'object_type': object_type,
            'object_name': object_name,
            'ifc_class': ifc_class,
            'category': category,
            'geometry_hash': geometry_hash,
            'vertex_count': vertex_count,
            'face_count': face_count
        }

        print(f"✅ Fetched geometry: {object_name}")
        print(f"   Vertices: {vertex_count}, Faces: {face_count}")
        print(f"   Dimensions: {dimensions['width']:.2f} x {dimensions['depth']:.2f} x {dimensions['height']:.2f}m")
        if base_rot_x != 0.0 or base_rot_y != 0.0 or base_rot_z != 0.0:
            print(f"   Base rotation: ({base_rot_x:.2f}, {base_rot_y:.2f}, {base_rot_z:.2f}) rad")

        return {
            'vertices': vertices,
            'faces': faces,
            'normals': normals,
            'dimensions': dimensions,
            'metadata': metadata,
            'base_rotation': (base_rot_x, base_rot_y, base_rot_z)  # Add base rotation
        }

    def _parse_vertices_blob(self, blob, vertex_count):
        """
        Parse vertices BLOB to numpy array

        Args:
            blob: Binary blob of float32 values
            vertex_count: Number of vertices

        Returns:
            np.array shape (vertex_count, 3) - [[x,y,z], ...]
        """
        if not blob:
            return np.array([])

        # Each vertex = 3 floats (x, y, z) = 12 bytes
        expected_size = vertex_count * 3 * 4  # 4 bytes per float32
        if len(blob) != expected_size:
            print(f"⚠️  Vertex blob size mismatch: expected {expected_size}, got {len(blob)}")

        # Unpack as float32 array
        float_count = len(blob) // 4
        floats = struct.unpack(f'<{float_count}f', blob)  # Little-endian float32

        # Reshape to (N, 3)
        vertices = np.array(floats).reshape(-1, 3)
        return vertices

    def _parse_faces_blob(self, blob, face_count):
        """
        Parse faces BLOB to numpy array

        Args:
            blob: Binary blob of uint32 values
            face_count: Number of faces (triangles)

        Returns:
            np.array shape (face_count, 3) - [[v1,v2,v3], ...]
        """
        if not blob:
            return np.array([])

        # Each face = 3 vertex indices (uint32) = 12 bytes
        expected_size = face_count * 3 * 4  # 4 bytes per uint32
        if len(blob) != expected_size:
            print(f"⚠️  Face blob size mismatch: expected {expected_size}, got {len(blob)}")

        # Unpack as uint32 array
        uint_count = len(blob) // 4
        indices = struct.unpack(f'<{uint_count}I', blob)  # Little-endian uint32

        # Reshape to (N, 3)
        faces = np.array(indices).reshape(-1, 3)
        return faces

    def _parse_normals_blob(self, blob, face_count):
        """
        Parse normals BLOB to numpy array

        Args:
            blob: Binary blob of float32 values
            face_count: Number of faces

        Returns:
            np.array shape (face_count, 3) - [[nx,ny,nz], ...]
        """
        if not blob:
            return None

        # Each normal = 3 floats (nx, ny, nz) = 12 bytes
        expected_size = face_count * 3 * 4
        if len(blob) != expected_size:
            print(f"⚠️  Normal blob size mismatch: expected {expected_size}, got {len(blob)}")

        # Unpack as float32 array
        float_count = len(blob) // 4
        floats = struct.unpack(f'<{float_count}f', blob)

        # Reshape to (N, 3)
        normals = np.array(floats).reshape(-1, 3)
        return normals

    def fetch_all_geometries(self, object_types):
        """
        Fetch geometries for multiple object types

        Args:
            object_types: List of object_type strings

        Returns:
            dict: {object_type: geometry_data, ...}

        Raises:
            RuntimeError: If any object_type fails to load (HARD STOP - no placeholders)
        """
        geometries = {}
        failed_types = []
        print(f"\n📦 Fetching {len(object_types)} unique geometries from database...")
        print(f"🔍 DEBUG: Requested types: {object_types}")

        for obj_type in object_types:
            geometry = self.fetch_geometry(obj_type)
            if geometry:
                geometries[obj_type] = geometry
            else:
                failed_types.append(obj_type)
                print(f"❌ FAILED: {obj_type}")

        print(f"🔍 DEBUG: Returned types: {list(geometries.keys())}")
        print(f"🔍 DEBUG: Missing types: {failed_types}")

        if failed_types:
            error_msg = f"""
            ❌ HARD STOP: Failed to load {len(failed_types)} object type(s) from library

            Missing object types:
            {chr(10).join(f"  - {t}" for t in failed_types)}

            This is a HUMAN/AI checkpoint failure.

            Required action:
            1. Verify object_types exist in Ifc_Object_Library.db object_catalog table
            2. Verify object_types have geometry_hash in base_geometries table
            3. Verify base_geometries has vertices, faces, AND normals BLOBs
            4. Update MANUAL_LIBRARY_MAPPING in convert_master_to_blender.py if needed
            5. Re-run Blender import

            DO NOT proceed with placeholder boxes - manual verification required.
            """
            print(error_msg)
            raise RuntimeError(error_msg)

        print(f"\n✅ Fetched {len(geometries)}/{len(object_types)} geometries")
        return geometries

    def _create_placeholder_geometry(self, object_type):
        """
        Create placeholder box geometry if database lookup fails

        Returns simple cube vertices/faces for fallback
        """
        # Simple cube: 8 vertices, 12 triangular faces
        vertices = np.array([
            [-0.5, -0.5, -0.5], [0.5, -0.5, -0.5], [0.5, 0.5, -0.5], [-0.5, 0.5, -0.5],
            [-0.5, -0.5,  0.5], [0.5, -0.5,  0.5], [0.5, 0.5,  0.5], [-0.5, 0.5,  0.5]
        ])

        faces = np.array([
            [0,1,2], [0,2,3],  # Bottom
            [4,5,6], [4,6,7],  # Top
            [0,1,5], [0,5,4],  # Front
            [2,3,7], [2,7,6],  # Back
            [0,3,7], [0,7,4],  # Left
            [1,2,6], [1,6,5]   # Right
        ])

        return {
            'vertices': vertices,
            'faces': faces,
            'normals': None,
            'dimensions': {'width': 1.0, 'depth': 1.0, 'height': 1.0},
            'metadata': {
                'object_type': object_type,
                'is_placeholder': True
            }
        }

    def close(self):
        """Close database connection"""
        self.connection.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python3 database_geometry_fetcher.py <database_path> <object_type>")
        print("Example: python3 database_geometry_fetcher.py DatabaseFiles/Ifc_Object_Library.db door_single_900_lod300")
        sys.exit(1)

    db_path = sys.argv[1]
    object_type = sys.argv[2]

    # Fetch geometry
    fetcher = DatabaseGeometryFetcher(db_path)
    geometry = fetcher.fetch_geometry(object_type)

    if geometry:
        print(f"\nGeometry details:")
        print(f"  Vertices shape: {geometry['vertices'].shape}")
        print(f"  Faces shape: {geometry['faces'].shape}")
        if geometry['normals'] is not None:
            print(f"  Normals shape: {geometry['normals'].shape}")
        print(f"  Dimensions: {geometry['dimensions']}")

        # Sample vertices
        print(f"\nFirst 3 vertices:")
        print(geometry['vertices'][:3])
        print(f"\nFirst 3 faces:")
        print(geometry['faces'][:3])

    fetcher.close()
