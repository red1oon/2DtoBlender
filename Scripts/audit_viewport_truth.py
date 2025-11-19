#!/usr/bin/env python3
"""
Viewport Snapshot - Render database geometry to PNG without Blender

Uses trimesh to reconstruct meshes from database and render to image.
Camera can be controlled via command line arguments.

Usage:
    python viewport_snapshot.py <database.db> [options]

Options:
    --output, -o    Output PNG path (default: Screenshots/<db_name>_<timestamp>.png)
    --angle         Camera angle preset: iso, top, front, side (default: iso)
    --distance      Camera distance multiplier (default: 2.0)
    --resolution    Image resolution WxH (default: 1920x1080)
    --show-axes     Show XYZ axes in render
"""

import sys
import sqlite3
import argparse
import json
from pathlib import Path
from datetime import datetime
import numpy as np

try:
    import trimesh
    from PIL import Image
except ImportError:
    print("ERROR: Required packages not installed.")
    print("Run: ./venv/bin/pip install trimesh pillow numpy")
    sys.exit(1)


def load_meshes_from_db(db_path: str) -> trimesh.Scene:
    """Load all element geometries from database into trimesh scene."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    scene = trimesh.Scene()

    # Get all elements with geometry (instanced pattern)
    cursor.execute("""
        SELECT em.guid, em.ifc_class, em.discipline,
               bg.vertices, bg.faces
        FROM elements_meta em
        JOIN element_geometry eg ON em.guid = eg.guid
        JOIN base_geometries bg ON eg.geometry_hash = bg.geometry_hash
    """)

    # Color mapping by IFC class
    colors = {
        'IfcWall': [0.85, 0.85, 0.85, 1.0],
        'IfcSlab': [0.7, 0.7, 0.7, 1.0],
        'IfcColumn': [0.6, 0.6, 0.6, 1.0],
        'IfcBeam': [0.65, 0.65, 0.65, 1.0],
        'IfcPlate': [0.6, 0.65, 0.7, 1.0],
        'IfcRoof': [0.5, 0.7, 0.9, 0.8],
        'IfcWindow': [0.6, 0.8, 1.0, 0.5],
        'IfcDoor': [0.55, 0.35, 0.20, 1.0],
    }
    default_color = [0.7, 0.7, 0.7, 1.0]

    mesh_count = 0
    for row in cursor.fetchall():
        guid, ifc_class, discipline, vertices_blob, faces_blob = row

        try:
            # Decode BLOB data (stored as JSON strings in BLOB)
            vertices = json.loads(vertices_blob)
            faces = json.loads(faces_blob)

            if not vertices or not faces:
                continue

            # Create mesh
            mesh = trimesh.Trimesh(
                vertices=np.array(vertices),
                faces=np.array(faces)
            )

            # Apply color
            color = colors.get(ifc_class, default_color)
            mesh.visual.face_colors = [int(c * 255) for c in color]

            scene.add_geometry(mesh, node_name=guid)
            mesh_count += 1

        except Exception as e:
            print(f"Warning: Failed to load {guid}: {e}")
            continue

    conn.close()
    print(f"Loaded {mesh_count} meshes from database")

    return scene


def get_camera_transform(scene: trimesh.Scene, angle: str, distance: float):
    """Get camera transformation matrix for given angle preset."""

    # Get scene bounds
    bounds = scene.bounds
    center = (bounds[0] + bounds[1]) / 2
    size = np.linalg.norm(bounds[1] - bounds[0])

    # Camera distance from center
    cam_dist = size * distance

    if angle == 'iso':
        # Isometric view (like Blender's default)
        cam_pos = center + np.array([cam_dist * 0.7, -cam_dist * 0.7, cam_dist * 0.5])
    elif angle == 'top':
        # Top-down view
        cam_pos = center + np.array([0, 0, cam_dist])
    elif angle == 'front':
        # Front view (looking at -Y)
        cam_pos = center + np.array([0, -cam_dist, 0])
    elif angle == 'side':
        # Side view (looking at -X)
        cam_pos = center + np.array([-cam_dist, 0, 0])
    elif angle == 'se':
        # Southeast isometric
        cam_pos = center + np.array([cam_dist * 0.7, cam_dist * 0.7, cam_dist * 0.5])
    else:
        # Default to isometric
        cam_pos = center + np.array([cam_dist * 0.7, -cam_dist * 0.7, cam_dist * 0.5])

    # Create look-at transform
    transform = trimesh.transformations.look_at(cam_pos, center, [0, 0, 1])

    return transform


def render_snapshot(scene: trimesh.Scene, output_path: str,
                   angle: str = 'iso', distance: float = 2.0,
                   resolution: tuple = (1920, 1080)):
    """Render scene to PNG file."""

    # Set camera
    camera_transform = get_camera_transform(scene, angle, distance)

    # Try to render
    try:
        # trimesh's save_image needs pyglet or other backend
        png_data = scene.save_image(resolution=resolution, visible=True)

        with open(output_path, 'wb') as f:
            f.write(png_data)

        print(f"Snapshot saved: {output_path}")
        return True

    except Exception as e:
        print(f"Render failed: {e}")
        print("Trying alternative method...")

        # Fallback: create simple orthographic projection
        try:
            from PIL import Image, ImageDraw

            # Get 2D projection of all vertices
            bounds = scene.bounds
            width, height = resolution

            # Create image
            img = Image.new('RGB', (width, height), color=(40, 40, 40))
            draw = ImageDraw.Draw(img)

            # Project and draw each mesh
            for name, geom in scene.geometry.items():
                if hasattr(geom, 'vertices'):
                    verts = geom.vertices

                    # Simple orthographic projection based on angle
                    if angle == 'top':
                        proj_x = verts[:, 0]
                        proj_y = verts[:, 1]
                    elif angle == 'front':
                        proj_x = verts[:, 0]
                        proj_y = verts[:, 2]
                    else:  # iso
                        proj_x = verts[:, 0] - verts[:, 1] * 0.5
                        proj_y = verts[:, 2] + verts[:, 1] * 0.3

                    # Scale to image
                    x_range = bounds[1][0] - bounds[0][0]
                    y_range = bounds[1][2] - bounds[0][2] + bounds[1][1] * 0.3

                    scale = min(width / x_range, height / y_range) * 0.8

                    px = ((proj_x - proj_x.min()) * scale + width * 0.1).astype(int)
                    py = (height - (proj_y - proj_y.min()) * scale - height * 0.1).astype(int)

                    # Draw edges from faces
                    if hasattr(geom, 'faces'):
                        for face in geom.faces:
                            points = [(px[i], py[i]) for i in face]
                            if len(points) >= 3:
                                draw.polygon(points, outline=(180, 180, 180), fill=(100, 100, 100))

            img.save(output_path)
            print(f"Fallback snapshot saved: {output_path}")
            return True

        except Exception as e2:
            print(f"Fallback render also failed: {e2}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Render database geometry to PNG without Blender',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('database', help='Path to federation database (.db)')
    parser.add_argument('--output', '-o', help='Output PNG path')
    parser.add_argument('--angle', '-a', default='iso',
                       choices=['iso', 'top', 'front', 'side', 'se'],
                       help='Camera angle preset')
    parser.add_argument('--distance', '-d', type=float, default=2.0,
                       help='Camera distance multiplier')
    parser.add_argument('--resolution', '-r', default='1920x1080',
                       help='Image resolution WxH')

    args = parser.parse_args()

    db_path = Path(args.database)
    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}")
        sys.exit(1)

    # Parse resolution
    try:
        res_w, res_h = map(int, args.resolution.split('x'))
        resolution = (res_w, res_h)
    except:
        print(f"ERROR: Invalid resolution format: {args.resolution}")
        sys.exit(1)

    # Default output path
    if args.output:
        output_path = args.output
    else:
        screenshots_dir = Path(__file__).parent.parent / "Screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = screenshots_dir / f"{db_path.stem}_{timestamp}.png"

    # Load and render
    print(f"\nLoading database: {db_path}")
    scene = load_meshes_from_db(str(db_path))

    print(f"Rendering with angle={args.angle}, distance={args.distance}")
    success = render_snapshot(scene, str(output_path),
                             args.angle, args.distance, resolution)

    if success:
        print(f"\nSnapshot complete: {output_path}")
    else:
        print("\nSnapshot failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
