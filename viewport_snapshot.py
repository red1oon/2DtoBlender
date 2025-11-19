#!/usr/bin/env python3
"""
Viewport Snapshot Tool - Pure Software Renderer

Renders federation database geometry to PNG without launching Blender.
Uses only numpy + PIL for software rasterization.

This enables autonomous audit cycles where Claude can "see" the model
by reading the output PNG file.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image


class SoftwareRenderer:
    """Pure software 3D renderer using numpy + PIL."""

    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height
        # Color buffer (RGBA)
        self.color_buffer = np.zeros((height, width, 4), dtype=np.uint8)
        # Depth buffer (z-buffer)
        self.depth_buffer = np.full((height, width), np.inf, dtype=np.float32)
        # Background color
        self.clear_color = np.array([40, 40, 40, 255], dtype=np.uint8)

    def clear(self):
        """Clear buffers."""
        self.color_buffer[:] = self.clear_color
        self.depth_buffer[:] = np.inf

    def set_camera(self, angle: str = 'iso', distance: float = 1.0, center=None, size=None):
        """
        Set up camera transformation matrix.

        Args:
            angle: Camera angle preset ('iso', 'top', 'front', 'side', 'se')
            distance: Distance multiplier (zoom)
            center: Scene center point
            size: Scene bounding box size
        """
        if center is None:
            center = np.array([0, 0, 0])
        if size is None:
            size = 100.0

        # Camera direction vectors for each preset
        presets = {
            'iso': np.array([1, 1, 1]),      # Isometric
            'top': np.array([0, 0, 1]),      # Top-down
            'front': np.array([0, -1, 0]),   # Front view
            'side': np.array([1, 0, 0]),     # Side view
            'se': np.array([1, -1, 1]),      # South-east isometric
        }

        direction = presets.get(angle, presets['iso'])
        direction = direction / np.linalg.norm(direction)

        # Camera position
        cam_distance = size * distance * 2
        self.cam_pos = center + direction * cam_distance
        self.cam_target = center

        # Build view matrix (look-at)
        forward = direction
        right = np.cross(np.array([0, 0, 1]), forward)
        if np.linalg.norm(right) < 0.001:
            right = np.array([1, 0, 0])
        right = right / np.linalg.norm(right)
        up = np.cross(forward, right)

        self.view_matrix = np.array([
            [right[0], right[1], right[2], -np.dot(right, self.cam_pos)],
            [up[0], up[1], up[2], -np.dot(up, self.cam_pos)],
            [forward[0], forward[1], forward[2], -np.dot(forward, self.cam_pos)],
            [0, 0, 0, 1]
        ])

        # Orthographic projection scale
        self.ortho_scale = size * distance

    def project_vertex(self, vertex):
        """
        Project a 3D vertex to 2D screen coordinates.

        Args:
            vertex: 3D point (x, y, z)

        Returns:
            (screen_x, screen_y, depth) or None if behind camera
        """
        # Apply view transformation
        v = np.array([vertex[0], vertex[1], vertex[2], 1.0])
        v_view = self.view_matrix @ v

        # Orthographic projection
        x = v_view[0] / self.ortho_scale
        y = v_view[1] / self.ortho_scale
        z = v_view[2]

        # Convert to screen coordinates
        screen_x = int((x + 1) * 0.5 * self.width)
        screen_y = int((1 - y) * 0.5 * self.height)  # Flip Y

        return (screen_x, screen_y, z)

    def barycentric(self, p, v0, v1, v2):
        """
        Compute barycentric coordinates of point p in triangle v0-v1-v2.

        Returns:
            (u, v, w) barycentric coordinates, or None if degenerate
        """
        v0v1 = np.array([v1[0] - v0[0], v1[1] - v0[1]])
        v0v2 = np.array([v2[0] - v0[0], v2[1] - v0[1]])
        v0p = np.array([p[0] - v0[0], p[1] - v0[1]])

        dot00 = np.dot(v0v1, v0v1)
        dot01 = np.dot(v0v1, v0v2)
        dot02 = np.dot(v0v1, v0p)
        dot11 = np.dot(v0v2, v0v2)
        dot12 = np.dot(v0v2, v0p)

        denom = dot00 * dot11 - dot01 * dot01
        if abs(denom) < 1e-10:
            return None

        inv_denom = 1.0 / denom
        u = (dot11 * dot02 - dot01 * dot12) * inv_denom
        v = (dot00 * dot12 - dot01 * dot02) * inv_denom

        return (u, v, 1 - u - v)

    def draw_triangle(self, v0, v1, v2, color, cull_backface=True):
        """
        Rasterize a single triangle with z-buffering (vectorized).

        Args:
            v0, v1, v2: Projected vertices (screen_x, screen_y, depth)
            color: RGBA color tuple
            cull_backface: Skip triangles facing away from camera
        """
        # Backface culling - check winding order in screen space
        if cull_backface:
            edge1 = (v1[0] - v0[0], v1[1] - v0[1])
            edge2 = (v2[0] - v0[0], v2[1] - v0[1])
            cross = edge1[0] * edge2[1] - edge1[1] * edge2[0]
            if cross <= 0:  # Clockwise = back-facing
                return

        # Bounding box
        min_x = max(0, int(min(v0[0], v1[0], v2[0])))
        max_x = min(self.width - 1, int(max(v0[0], v1[0], v2[0])))
        min_y = max(0, int(min(v0[1], v1[1], v2[1])))
        max_y = min(self.height - 1, int(max(v0[1], v1[1], v2[1])))

        if min_x > max_x or min_y > max_y:
            return

        # Vectorized rasterization
        # Create coordinate grid for bounding box
        xs = np.arange(min_x, max_x + 1)
        ys = np.arange(min_y, max_y + 1)
        xx, yy = np.meshgrid(xs, ys)

        # Compute barycentric coordinates for all pixels at once
        v0v1 = np.array([v1[0] - v0[0], v1[1] - v0[1]])
        v0v2 = np.array([v2[0] - v0[0], v2[1] - v0[1]])
        v0p_x = xx - v0[0]
        v0p_y = yy - v0[1]

        dot00 = np.dot(v0v1, v0v1)
        dot01 = np.dot(v0v1, v0v2)
        dot11 = np.dot(v0v2, v0v2)

        dot02 = v0v1[0] * v0p_x + v0v1[1] * v0p_y
        dot12 = v0v2[0] * v0p_x + v0v2[1] * v0p_y

        denom = dot00 * dot11 - dot01 * dot01
        if abs(denom) < 1e-10:
            return

        inv_denom = 1.0 / denom
        u = (dot11 * dot02 - dot01 * dot12) * inv_denom
        v = (dot00 * dot12 - dot01 * dot02) * inv_denom
        w = 1 - u - v

        # Mask for pixels inside triangle
        inside = (u >= 0) & (v >= 0) & (w >= 0)

        if not np.any(inside):
            return

        # Interpolate depth for all inside pixels
        z = u * v0[2] + v * v1[2] + w * v2[2]

        # Get pixel coordinates that are inside
        inside_y, inside_x = np.where(inside)
        inside_y = inside_y + min_y
        inside_x = inside_x + min_x
        inside_z = z[inside]

        # Z-buffer test and update (vectorized where possible)
        for i in range(len(inside_x)):
            px, py, pz = inside_x[i], inside_y[i], inside_z[i]
            if pz < self.depth_buffer[py, px]:
                self.depth_buffer[py, px] = pz
                self.color_buffer[py, px] = color

    def render_mesh(self, vertices, faces, color):
        """
        Render a mesh.

        Args:
            vertices: List of (x, y, z) vertices
            faces: List of face indices (triangles)
            color: RGBA color tuple
        """
        # Project all vertices
        projected = []
        for v in vertices:
            proj = self.project_vertex(v)
            projected.append(proj)

        # Draw each triangle
        for face in faces:
            if len(face) >= 3:
                v0 = projected[face[0]]
                v1 = projected[face[1]]
                v2 = projected[face[2]]

                # Simple backface culling (optional)
                # For now, draw all faces
                self.draw_triangle(v0, v1, v2, color)

                # Handle quads by splitting into two triangles
                if len(face) == 4:
                    v3 = projected[face[3]]
                    self.draw_triangle(v0, v2, v3, color)

    def get_image(self):
        """Get the rendered image as PIL Image."""
        return Image.fromarray(self.color_buffer, 'RGBA')


class DatabaseGeometryLoader:
    """Load geometry from federation database."""

    # IFC class colors (matching Blender materials)
    IFC_COLORS = {
        'IfcWall': (200, 200, 200, 255),
        'IfcSlab': (180, 180, 180, 255),
        'IfcColumn': (160, 160, 160, 255),
        'IfcBeam': (140, 140, 140, 255),
        'IfcWindow': (100, 150, 200, 180),
        'IfcDoor': (139, 90, 43, 255),
        'IfcRoof': (150, 100, 80, 255),
        'IfcStair': (170, 170, 170, 255),
        'IfcRailing': (120, 120, 120, 255),
        'IfcCurtainWall': (80, 120, 180, 150),
        'IfcPlate': (190, 190, 190, 255),
        'IfcMember': (130, 130, 130, 255),
        'IfcFooting': (100, 100, 100, 255),
        'IfcPile': (90, 90, 90, 255),
        'IfcBuildingElementProxy': (200, 150, 100, 255),
    }
    DEFAULT_COLOR = (180, 180, 180, 255)

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    def decode_blob(self, blob, blob_type='vertices'):
        """
        Decode BLOB data - supports multiple formats.

        Args:
            blob: Raw BLOB data
            blob_type: 'vertices' or 'faces'

        Returns:
            Decoded data as list
        """
        if not isinstance(blob, bytes):
            # Already decoded (string)
            return json.loads(blob)

        # Try JSON UTF-8 first
        try:
            return json.loads(blob.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass

        # Try raw binary numpy format
        if blob_type == 'vertices':
            # Vertices: float32 array, reshape to Nx3
            arr = np.frombuffer(blob, dtype=np.float32)
            return arr.reshape(-1, 3).tolist()
        else:
            # Faces: int32 array, reshape to Nx3 (triangles) or Nx4 (quads)
            arr = np.frombuffer(blob, dtype=np.int32)
            # Assume triangles
            if len(arr) % 3 == 0:
                return arr.reshape(-1, 3).tolist()
            elif len(arr) % 4 == 0:
                return arr.reshape(-1, 4).tolist()
            else:
                # Return flat list, let mesh handling deal with it
                return arr.tolist()

    def get_color_for_class(self, ifc_class: str):
        """Get color for an IFC class."""
        # Check exact match first
        if ifc_class in self.IFC_COLORS:
            return self.IFC_COLORS[ifc_class]
        # Check prefix match
        for key, color in self.IFC_COLORS.items():
            if ifc_class.startswith(key):
                return color
        return self.DEFAULT_COLOR

    def load_meshes(self, surface_only=False, disciplines=None, exclude=None):
        """
        Load all meshes from database.

        Args:
            surface_only: If True, only load surface elements (walls, slabs, roofs)
            disciplines: List of disciplines to include (e.g., ['ARC', 'STR']), None for all
            exclude: List of disciplines to exclude (e.g., ['ARC', 'STR'])

        Returns:
            List of (vertices, faces, color) tuples
        """
        meshes = []
        cursor = self.conn.cursor()

        # Surface element classes
        surface_classes = [
            'IfcWall', 'IfcSlab', 'IfcRoof', 'IfcCurtainWall',
            'IfcCovering', 'IfcPlate', 'IfcWindow', 'IfcDoor'
        ]

        # Try schema with element_instances (POC style)
        query = """
        SELECT
            em.guid,
            em.ifc_class,
            em.discipline,
            et.center_x,
            et.center_y,
            et.center_z,
            et.rotation_z,
            bg.vertices,
            bg.faces
        FROM elements_meta em
        JOIN element_instances ei ON em.guid = ei.guid
        JOIN base_geometries bg ON ei.geometry_hash = bg.geometry_hash
        LEFT JOIN element_transforms et ON em.guid = et.guid
        """

        try:
            cursor.execute(query)
            rows = cursor.fetchall()
        except sqlite3.OperationalError as e:
            # Fallback to alternate schema
            print(f"Trying alternate schema... ({e})")
            query = """
            SELECT
                em.guid,
                em.ifc_class,
                em.discipline,
                NULL as center_x,
                NULL as center_y,
                NULL as center_z,
                NULL as rotation_z,
                bg.vertices,
                bg.faces
            FROM elements_meta em
            JOIN element_geometry eg ON em.guid = eg.guid
            JOIN base_geometries bg ON eg.geometry_hash = bg.geometry_hash
            """
            try:
                cursor.execute(query)
                rows = cursor.fetchall()
            except sqlite3.OperationalError as e2:
                print(f"Database query error: {e2}")
                return meshes

        for row in rows:
            try:
                # Decode BLOB data
                vertices_blob = row['vertices']
                faces_blob = row['faces']

                # Try multiple decoding strategies
                vertices = self.decode_blob(vertices_blob, 'vertices')
                faces = self.decode_blob(faces_blob, 'faces')

                # Apply transform if present (center + rotation)
                center_x = row['center_x']
                if center_x is not None:
                    center = [row['center_x'], row['center_y'], row['center_z']]
                    rotation_z = row['rotation_z'] or 0.0
                    vertices = self.apply_center_transform(vertices, center, rotation_z)

                # Get color based on IFC class
                ifc_class = row['ifc_class'] or 'Unknown'
                discipline = row['discipline'] if 'discipline' in row.keys() else None

                # Filter by discipline
                if disciplines and discipline:
                    if discipline.upper() not in [d.upper() for d in disciplines]:
                        continue

                # Exclude disciplines
                if exclude and discipline:
                    if discipline.upper() in exclude:
                        continue

                # Filter for surface elements only
                if surface_only:
                    is_surface = any(ifc_class.startswith(sc) for sc in surface_classes)
                    if not is_surface:
                        continue

                color = self.get_color_for_class(ifc_class)

                meshes.append((vertices, faces, color))

            except Exception as e:
                guid = row['guid'] if row['guid'] else 'unknown'
                print(f"Warning: Failed to load mesh {guid}: {e}")
                continue

        return meshes

    def apply_center_transform(self, vertices, center, rotation_z):
        """Apply center translation and Z rotation to vertices."""
        transformed = []
        cos_r = np.cos(rotation_z)
        sin_r = np.sin(rotation_z)

        for v in vertices:
            # Rotate around Z axis
            x = v[0] * cos_r - v[1] * sin_r
            y = v[0] * sin_r + v[1] * cos_r
            z = v[2]
            # Translate to center
            transformed.append([x + center[0], y + center[1], z + center[2]])

        return transformed

    def get_scene_bounds(self, meshes):
        """Calculate scene bounding box."""
        if not meshes:
            return np.array([0, 0, 0]), 100.0

        all_verts = []
        for vertices, faces, color in meshes:
            all_verts.extend(vertices)

        if not all_verts:
            return np.array([0, 0, 0]), 100.0

        verts = np.array(all_verts)
        min_bounds = verts.min(axis=0)
        max_bounds = verts.max(axis=0)

        center = (min_bounds + max_bounds) / 2
        size = np.linalg.norm(max_bounds - min_bounds)

        return center, max(size, 1.0)


def render_database(db_path: str, output_path: str = None,
                    angle: str = 'iso', distance: float = 1.5,
                    resolution: tuple = (1920, 1080),
                    surface_only: bool = False,
                    disciplines: list = None,
                    exclude: list = None):
    """
    Render database geometry to PNG.

    Args:
        db_path: Path to SQLite database
        output_path: Output PNG path (auto-generated if None)
        angle: Camera angle preset
        distance: Camera distance multiplier
        resolution: Image resolution (width, height)
        surface_only: Only render surface elements
        disciplines: List of disciplines to include (e.g., ['ARC', 'STR'])
        exclude: List of disciplines to exclude (e.g., ['ARC', 'STR'])

    Returns:
        Path to saved PNG file
    """
    print(f"Loading database: {db_path}")
    if disciplines:
        print(f"Disciplines: {', '.join(disciplines)}")
    if exclude:
        print(f"Excluding: {', '.join(exclude)}")
    if surface_only:
        print("Filtering: surface elements only")

    # Load geometry
    loader = DatabaseGeometryLoader(db_path)
    meshes = loader.load_meshes(surface_only=surface_only, disciplines=disciplines, exclude=exclude)

    if not meshes:
        print("Error: No meshes loaded from database")
        loader.close()
        return None

    print(f"Loaded {len(meshes)} meshes from database")

    # Get scene bounds
    center, size = loader.get_scene_bounds(meshes)
    loader.close()

    print(f"Scene center: {center}, size: {size:.1f}")

    # Create renderer
    renderer = SoftwareRenderer(resolution[0], resolution[1])
    renderer.clear()
    renderer.set_camera(angle=angle, distance=distance, center=center, size=size)

    print(f"Rendering with angle={angle}, distance={distance}")

    # Render all meshes
    for i, (vertices, faces, color) in enumerate(meshes):
        renderer.render_mesh(vertices, faces, color)
        if (i + 1) % 100 == 0:
            print(f"  Rendered {i + 1}/{len(meshes)} meshes...")

    # Generate output path if not specified
    if output_path is None:
        db_name = Path(db_path).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent / "Screenshots"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{db_name}_{timestamp}.png"

    # Save image
    image = renderer.get_image()
    image.save(output_path)

    print(f"\nSnapshot saved: {output_path}")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Render federation database geometry to PNG without Blender"
    )
    parser.add_argument(
        "database",
        help="Path to SQLite database with geometry"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output PNG path (auto-generated if not specified)"
    )
    parser.add_argument(
        "--angle", "-a",
        choices=['iso', 'top', 'front', 'side', 'se'],
        default='iso',
        help="Camera angle preset (default: iso)"
    )
    parser.add_argument(
        "--distance", "-d",
        type=float,
        default=1.5,
        help="Camera distance multiplier (default: 1.5)"
    )
    parser.add_argument(
        "--resolution", "-r",
        default="1920x1080",
        help="Image resolution WxH (default: 1920x1080)"
    )
    parser.add_argument(
        "--surface-only", "-s",
        action="store_true",
        help="Only render surface elements (walls, slabs, roofs, windows, doors)"
    )
    parser.add_argument(
        "--discipline", "-D",
        help="Comma-separated list of disciplines to show (e.g., ARC,STR,MEP)"
    )
    parser.add_argument(
        "--exclude", "-X",
        help="Comma-separated list of disciplines to exclude (e.g., ARC,STR)"
    )

    args = parser.parse_args()

    # Parse disciplines
    disciplines = None
    if args.discipline:
        disciplines = [d.strip() for d in args.discipline.split(',')]

    # Parse exclusions
    exclude = None
    if args.exclude:
        exclude = [d.strip().upper() for d in args.exclude.split(',')]

    # Parse resolution
    try:
        width, height = map(int, args.resolution.split('x'))
        resolution = (width, height)
    except ValueError:
        print(f"Invalid resolution format: {args.resolution}")
        sys.exit(1)

    # Render
    output = render_database(
        args.database,
        args.output,
        args.angle,
        args.distance,
        resolution,
        args.surface_only,
        disciplines,
        exclude
    )

    if output:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
