"""
Library Query Module
====================
Query Ifc_Object_Library.db for LOD300 geometry.
Replace runtime geometry creation with library objects.
"""

import sqlite3
import struct
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np


class LibraryQuery:
    """Query IFC object library for LOD300 geometry"""

    def __init__(self, library_path: str = "Ifc_Object_Library.db"):
        self.library_path = Path(library_path)
        if not self.library_path.exists():
            raise FileNotFoundError(f"Library not found: {library_path}")

        self.conn = sqlite3.connect(self.library_path)
        self.cursor = self.conn.cursor()

    def get_object_by_type(self, object_type: str) -> Optional[Dict]:
        """
        Get object geometry by object_type.

        Args:
            object_type: e.g., "door_single_900x2100_lod300"

        Returns:
            Dict with vertices, faces, normals, dimensions
        """
        self.cursor.execute("""
            SELECT
                bg.vertices, bg.faces, bg.normals,
                bg.vertex_count, bg.face_count,
                oc.width_mm, oc.depth_mm, oc.height_mm,
                oc.ifc_class, oc.object_name
            FROM object_catalog oc
            JOIN base_geometries bg ON oc.geometry_hash = bg.geometry_hash
            WHERE oc.object_type = ?
            LIMIT 1
        """, (object_type,))

        row = self.cursor.fetchone()
        if not row:
            return None

        vertices_blob, faces_blob, normals_blob, v_count, f_count, width, depth, height, ifc_class, name = row

        # Decode binary blobs
        vertices = self._decode_vertices(vertices_blob, v_count)
        faces = self._decode_faces(faces_blob, f_count)
        normals = self._decode_normals(normals_blob, f_count) if normals_blob else None

        return {
            'vertices': vertices,
            'faces': faces,
            'normals': normals,
            'dimensions': {
                'width': width / 1000.0,  # mm to meters
                'depth': depth / 1000.0,
                'height': height / 1000.0
            },
            'ifc_class': ifc_class,
            'object_name': name,
            'object_type': object_type
        }

    def get_door_geometry(self, width_mm: int, height_mm: int) -> Optional[Dict]:
        """
        Get door geometry by dimensions.

        Args:
            width_mm: Door width in millimeters (e.g., 900, 750)
            height_mm: Door height in millimeters (e.g., 2100)

        Returns:
            Dict with geometry or None if not found
        """
        # Try exact match first
        self.cursor.execute("""
            SELECT object_type
            FROM object_catalog
            WHERE ifc_class = 'IfcDoor'
              AND width_mm = ?
              AND height_mm = ?
              AND object_type LIKE '%lod300%'
            LIMIT 1
        """, (width_mm, height_mm))

        row = self.cursor.fetchone()
        if row:
            return self.get_object_by_type(row[0])

        # Fallback: find closest match
        self.cursor.execute("""
            SELECT object_type,
                   ABS(width_mm - ?) + ABS(height_mm - ?) as diff
            FROM object_catalog
            WHERE ifc_class = 'IfcDoor'
              AND object_type LIKE '%lod300%'
            ORDER BY diff
            LIMIT 1
        """, (width_mm, height_mm))

        row = self.cursor.fetchone()
        if row:
            print(f"⚠️  Door {width_mm}x{height_mm} not found, using closest: {row[0]}")
            return self.get_object_by_type(row[0])

        return None

    def get_window_geometry(self, width_mm: int, height_mm: int) -> Optional[Dict]:
        """Get window geometry by dimensions"""
        self.cursor.execute("""
            SELECT object_type
            FROM object_catalog
            WHERE ifc_class = 'IfcWindow'
              AND width_mm = ?
              AND height_mm = ?
              AND object_type LIKE '%lod300%'
            LIMIT 1
        """, (width_mm, height_mm))

        row = self.cursor.fetchone()
        if row:
            return self.get_object_by_type(row[0])

        # Fallback
        self.cursor.execute("""
            SELECT object_type,
                   ABS(width_mm - ?) + ABS(height_mm - ?) as diff
            FROM object_catalog
            WHERE ifc_class = 'IfcWindow'
              AND object_type LIKE '%lod300%'
            ORDER BY diff
            LIMIT 1
        """, (width_mm, height_mm))

        row = self.cursor.fetchone()
        if row:
            print(f"⚠️  Window {width_mm}x{height_mm} not found, using closest: {row[0]}")
            return self.get_object_by_type(row[0])

        return None

    def get_wall_geometry(self) -> Optional[Dict]:
        """Get standard wall geometry"""
        # Standard wall section (will be extruded)
        self.cursor.execute("""
            SELECT object_type
            FROM object_catalog
            WHERE ifc_class = 'IfcWall'
              AND object_type LIKE '%lod300%'
            LIMIT 1
        """)

        row = self.cursor.fetchone()
        if row:
            return self.get_object_by_type(row[0])

        return None

    def list_available_objects(self, ifc_class: Optional[str] = None) -> list:
        """List available objects in library"""
        if ifc_class:
            self.cursor.execute("""
                SELECT object_type, ifc_class, width_mm, height_mm, depth_mm, object_name
                FROM object_catalog
                WHERE ifc_class = ?
                ORDER BY object_type
            """, (ifc_class,))
        else:
            self.cursor.execute("""
                SELECT object_type, ifc_class, width_mm, height_mm, depth_mm, object_name
                FROM object_catalog
                ORDER BY ifc_class, object_type
            """)

        return self.cursor.fetchall()

    def _decode_vertices(self, blob: bytes, count: int) -> np.ndarray:
        """Decode vertices from binary blob"""
        # Format: float32 triplets (x, y, z)
        num_floats = count * 3
        vertices = struct.unpack(f'<{num_floats}f', blob)
        return np.array(vertices).reshape(count, 3)

    def _decode_faces(self, blob: bytes, count: int) -> np.ndarray:
        """Decode faces from binary blob"""
        # Format: uint32 triplets (v1, v2, v3)
        num_ints = count * 3
        faces = struct.unpack(f'<{num_ints}I', blob)
        return np.array(faces).reshape(count, 3)

    def _decode_normals(self, blob: bytes, count: int) -> np.ndarray:
        """Decode normals from binary blob"""
        # Format: float32 triplets (nx, ny, nz)
        num_floats = count * 3
        normals = struct.unpack(f'<{num_floats}f', blob)
        return np.array(normals).reshape(count, 3)

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test library query"""
    print("=" * 70)
    print("LIBRARY QUERY TEST")
    print("=" * 70)

    lib = LibraryQuery()

    # Test door queries
    print("\nDoor 900x2100:")
    door = lib.get_door_geometry(900, 2100)
    if door:
        print(f"  ✓ Found: {door['object_type']}")
        print(f"    Vertices: {len(door['vertices'])}")
        print(f"    Faces: {len(door['faces'])}")
    else:
        print("  ✗ Not found")

    print("\nDoor 750x2100:")
    door = lib.get_door_geometry(750, 2100)
    if door:
        print(f"  ✓ Found: {door['object_type']}")
        print(f"    Vertices: {len(door['vertices'])}")
        print(f"    Faces: {len(door['faces'])}")
    else:
        print("  ✗ Not found")

    # List available doors
    print("\nAvailable doors:")
    doors = lib.list_available_objects('IfcDoor')
    for obj_type, ifc, w, h, d, name in doors[:5]:
        print(f"  {obj_type}: {w}x{h}mm")

    lib.close()


if __name__ == "__main__":
    main()
