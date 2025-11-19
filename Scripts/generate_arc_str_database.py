#!/usr/bin/env python3
"""
ARC/STR Database Generator with World-Positioned Geometry
==========================================================

Generates a federation-compatible database from filtered 2D DXF files.

╔══════════════════════════════════════════════════════════════════════╗
║  CRITICAL: VERTICES MUST BE AT WORLD POSITIONS                       ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  The Bonsai blend_cache.py bake code does NOT apply transforms.      ║
║  It uses vertices directly from element_geometry table.              ║
║                                                                      ║
║  WRONG: Store centered templates + separate transforms               ║
║         → All objects render at origin (0,0,0)                       ║
║                                                                      ║
║  CORRECT: Store vertices at final world positions                    ║
║           → Objects render at correct locations                      ║
║                                                                      ║
║  See: generate_box_at_position() - offsets vertices by (cx, cy, cz)  ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝

This creates the same database structure as 8_IFC/enhanced_federation.db
for compatibility with Bonsai BBox Preview and Blend bake.

Usage:
    python3 generate_arc_str_database.py

Output:
    DatabaseFiles/Terminal1_ARC_STR.db
"""

import sys
import sqlite3
import struct
import hashlib
import math
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Optional

# Add ezdxf support
try:
    import ezdxf
except ImportError:
    print("ERROR: ezdxf not installed. Run: pip install ezdxf")
    sys.exit(1)

# Import geometry generators
from geometry_generators import (
    generate_element_geometry,
    GeometryResult,
    BoxGenerator,
    OrientedBoxGenerator,
    CylinderGenerator,
    ExtrudedPolylineGenerator,
    SlabGenerator,
    DomeGenerator,
    compute_face_normal
)

# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
TEMPLATES_FILE = BASE_DIR / "arc_str_element_templates.json"
CHEATSHEET_FILE = BASE_DIR / "terminal1_cheatsheet.json"
EXTRACTED_DIR = BASE_DIR / "SourceFiles" / "Terminal1_Extracted"
OUTPUT_DIR = BASE_DIR / "DatabaseFiles"
OUTPUT_DB = OUTPUT_DIR / "Terminal1_ARC_STR.db"

# Also check for any .blend files to delete
BLEND_OUTPUT = OUTPUT_DIR / "Terminal1_ARC_STR.blend"
BLEND_FULL_OUTPUT = OUTPUT_DIR / "Terminal1_ARC_STR_full.blend"

# ============================================================================
# GEOMETRY UTILITIES
# ============================================================================

def pack_vertices(vertices: List[Tuple[float, float, float]]) -> bytes:
    """Pack list of (x,y,z) tuples into binary BLOB."""
    return struct.pack(f'<{len(vertices)*3}f', *[coord for v in vertices for coord in v])

def pack_faces(faces: List[Tuple[int, int, int]]) -> bytes:
    """Pack list of (i1,i2,i3) tuples into binary BLOB."""
    return struct.pack(f'<{len(faces)*3}I', *[idx for face in faces for idx in face])

def pack_normals(normals: List[Tuple[float, float, float]]) -> bytes:
    """Pack list of normal vectors into binary BLOB."""
    return struct.pack(f'<{len(normals)*3}f', *[coord for n in normals for coord in n])

def compute_hash(vertices_blob: bytes, faces_blob: bytes) -> str:
    """Compute SHA256 hash of geometry for deduplication."""
    hasher = hashlib.sha256()
    hasher.update(vertices_blob)
    hasher.update(faces_blob)
    return hasher.hexdigest()

def compute_face_normal(v0, v1, v2) -> Tuple[float, float, float]:
    """Compute face normal using cross product."""
    e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
    e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
    nx = e1[1] * e2[2] - e1[2] * e2[1]
    ny = e1[2] * e2[0] - e1[0] * e2[2]
    nz = e1[0] * e2[1] - e1[1] * e2[0]
    length = math.sqrt(nx*nx + ny*ny + nz*nz)
    if length > 0:
        return (nx/length, ny/length, nz/length)
    return (0, 0, 1)

def generate_box_geometry(width: float, depth: float, height: float) -> Tuple[List, List, List]:
    """Generate box geometry centered at origin."""
    hx, hy, hz = width/2, depth/2, height/2
    vertices = [
        (-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0),
        (-hx, -hy, height), (hx, -hy, height), (hx, hy, height), (-hx, hy, height),
    ]
    faces = [
        (0, 1, 2), (0, 2, 3),  # Bottom
        (4, 7, 6), (4, 6, 5),  # Top
        (0, 4, 5), (0, 5, 1),  # Front
        (2, 6, 7), (2, 7, 3),  # Back
        (0, 3, 7), (0, 7, 4),  # Left
        (1, 5, 6), (1, 6, 2),  # Right
    ]
    normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
    return vertices, faces, normals

def generate_box_at_position(width: float, depth: float, height: float,
                              cx: float, cy: float, cz: float) -> Tuple[List, List, List]:
    """Generate box geometry at world position (cx, cy, cz)."""
    hx, hy = width/2, depth/2
    vertices = [
        (cx-hx, cy-hy, cz), (cx+hx, cy-hy, cz), (cx+hx, cy+hy, cz), (cx-hx, cy+hy, cz),
        (cx-hx, cy-hy, cz+height), (cx+hx, cy-hy, cz+height), (cx+hx, cy+hy, cz+height), (cx-hx, cy+hy, cz+height),
    ]
    faces = [
        (0, 1, 2), (0, 2, 3),  # Bottom
        (4, 7, 6), (4, 6, 5),  # Top
        (0, 4, 5), (0, 5, 1),  # Front
        (2, 6, 7), (2, 7, 3),  # Back
        (0, 3, 7), (0, 7, 4),  # Left
        (1, 5, 6), (1, 6, 2),  # Right
    ]
    normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
    return vertices, faces, normals

def generate_oriented_box(length: float, width: float, height: float,
                          cx: float, cy: float, cz: float, rotation: float) -> Tuple[List, List, List]:
    """Generate box geometry oriented along rotation angle at world position."""
    # Half dimensions
    hl, hw = length/2, width/2

    # Rotation matrix components
    cos_r = math.cos(rotation)
    sin_r = math.sin(rotation)

    # Local corners (length along X, width along Y)
    local_corners = [
        (-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw)
    ]

    # Transform to world coordinates
    vertices = []
    for lx, ly in local_corners:
        wx = cx + lx * cos_r - ly * sin_r
        wy = cy + lx * sin_r + ly * cos_r
        vertices.append((wx, wy, cz))
    for lx, ly in local_corners:
        wx = cx + lx * cos_r - ly * sin_r
        wy = cy + lx * sin_r + ly * cos_r
        vertices.append((wx, wy, cz + height))

    faces = [
        (0, 1, 2), (0, 2, 3),  # Bottom
        (4, 7, 6), (4, 6, 5),  # Top
        (0, 4, 5), (0, 5, 1),  # Front
        (2, 6, 7), (2, 7, 3),  # Back
        (0, 3, 7), (0, 7, 4),  # Left
        (1, 5, 6), (1, 6, 2),  # Right
    ]
    normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
    return vertices, faces, normals

def generate_cylinder_at_position(radius: float, height: float,
                                   cx: float, cy: float, cz: float,
                                   segments: int = 12) -> Tuple[List, List, List]:
    """Generate cylinder geometry at world position."""
    vertices = [(cx, cy, cz)]  # Bottom center
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        vertices.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle), cz))

    vertices.append((cx, cy, cz + height))  # Top center
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        vertices.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle), cz + height))

    faces = []
    # Bottom cap
    for i in range(segments):
        faces.append((0, 1 + (i + 1) % segments, 1 + i))
    # Top cap
    top_center = segments + 1
    for i in range(segments):
        faces.append((top_center, top_center + 1 + i, top_center + 1 + (i + 1) % segments))
    # Side faces
    for i in range(segments):
        b1 = 1 + i
        b2 = 1 + (i + 1) % segments
        t1 = top_center + 1 + i
        t2 = top_center + 1 + (i + 1) % segments
        faces.append((b1, b2, t2))
        faces.append((b1, t2, t1))

    normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
    return vertices, faces, normals

def generate_extruded_polyline(points: List[Tuple[float, float]], thickness: float, height: float,
                                cz: float) -> Tuple[List, List, List]:
    """
    Generate extruded wall geometry from polyline points.
    Creates a 3D wall by offsetting polyline inward/outward by thickness/2.
    """
    if len(points) < 2:
        # Fallback to box
        return generate_box_at_position(1.0, thickness, height, points[0][0], points[0][1], cz)

    # Calculate offset polyline (simplified - perpendicular offset)
    vertices = []
    n = len(points)

    # For each point, calculate perpendicular direction
    for i in range(n):
        p0 = points[i]

        # Get direction vectors
        if i == 0:
            dx = points[1][0] - points[0][0]
            dy = points[1][1] - points[0][1]
        elif i == n - 1:
            dx = points[n-1][0] - points[n-2][0]
            dy = points[n-1][1] - points[n-2][1]
        else:
            dx = points[i+1][0] - points[i-1][0]
            dy = points[i+1][1] - points[i-1][1]

        # Normalize and get perpendicular
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0.001:
            nx, ny = -dy/length, dx/length
        else:
            nx, ny = 0, 1

        # Offset points
        ht = thickness / 2
        vertices.append((p0[0] + nx*ht, p0[1] + ny*ht, cz))
        vertices.append((p0[0] - nx*ht, p0[1] - ny*ht, cz))

    # Add top vertices
    bottom_count = len(vertices)
    for v in vertices[:bottom_count]:
        vertices.append((v[0], v[1], cz + height))

    faces = []
    # Bottom and top caps (triangulate)
    for i in range(n - 1):
        # Bottom quad (two triangles)
        b0, b1 = i*2, i*2 + 1
        b2, b3 = (i+1)*2, (i+1)*2 + 1
        faces.append((b0, b2, b1))
        faces.append((b1, b2, b3))

        # Top quad
        t0, t1 = bottom_count + b0, bottom_count + b1
        t2, t3 = bottom_count + b2, bottom_count + b3
        faces.append((t0, t1, t2))
        faces.append((t1, t3, t2))

    # Side faces
    for i in range(n - 1):
        # Outer side
        b0, b2 = i*2, (i+1)*2
        t0, t2 = bottom_count + b0, bottom_count + b2
        faces.append((b0, t0, t2))
        faces.append((b0, t2, b2))

        # Inner side
        b1, b3 = i*2 + 1, (i+1)*2 + 1
        t1, t3 = bottom_count + b1, bottom_count + b3
        faces.append((b1, b3, t3))
        faces.append((b1, t3, t1))

    # End caps
    # Start cap
    faces.append((0, 1, bottom_count + 1))
    faces.append((0, bottom_count + 1, bottom_count))
    # End cap
    e0, e1 = (n-1)*2, (n-1)*2 + 1
    faces.append((e0, bottom_count + e0, bottom_count + e1))
    faces.append((e0, bottom_count + e1, e1))

    normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
    return vertices, faces, normals

def generate_cylinder_geometry(radius: float, height: float, segments: int = 12) -> Tuple[List, List, List]:
    """Generate cylinder geometry centered at origin."""
    vertices = [(0, 0, 0)]  # Bottom center
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        vertices.append((radius * math.cos(angle), radius * math.sin(angle), 0))
    vertices.append((0, 0, height))  # Top center
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        vertices.append((radius * math.cos(angle), radius * math.sin(angle), height))

    faces = []
    # Bottom cap
    for i in range(segments):
        faces.append((0, i + 1, (i + 1) % segments + 1))
    # Sides
    for i in range(segments):
        b1, b2 = i + 1, (i + 1) % segments + 1
        t1, t2 = segments + 2 + i, segments + 2 + (i + 1) % segments
        faces.extend([(b1, t1, t2), (b1, t2, b2)])
    # Top cap
    for i in range(segments):
        faces.append((segments + 1, segments + 2 + (i + 1) % segments, segments + 2 + i))

    normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
    return vertices, faces, normals

# ============================================================================
# DATABASE SCHEMA
# ============================================================================

def create_database_schema(conn: sqlite3.Connection):
    """Create federation-compatible database schema."""
    cursor = conn.cursor()

    # Core tables matching 8_IFC structure
    cursor.executescript("""
        -- Base geometries (template shapes, stored once)
        CREATE TABLE IF NOT EXISTS base_geometries (
            geometry_hash TEXT PRIMARY KEY,
            vertices BLOB NOT NULL,
            faces BLOB NOT NULL,
            normals BLOB,
            vertex_count INTEGER NOT NULL,
            face_count INTEGER NOT NULL
        );

        -- Element instances (point to base geometry)
        CREATE TABLE IF NOT EXISTS element_instances (
            guid TEXT PRIMARY KEY,
            geometry_hash TEXT NOT NULL,
            FOREIGN KEY (geometry_hash) REFERENCES base_geometries(geometry_hash)
        );

        -- Element metadata
        CREATE TABLE IF NOT EXISTS elements_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guid TEXT UNIQUE NOT NULL,
            discipline TEXT NOT NULL,
            ifc_class TEXT NOT NULL,
            filepath TEXT,
            element_name TEXT,
            element_type TEXT,
            element_description TEXT,
            storey TEXT,
            material_name TEXT,
            material_rgba TEXT
        );

        -- Element transforms (position in world)
        CREATE TABLE IF NOT EXISTS element_transforms (
            guid TEXT PRIMARY KEY,
            center_x REAL NOT NULL,
            center_y REAL NOT NULL,
            center_z REAL NOT NULL,
            rotation_z REAL DEFAULT 0.0,
            length REAL,
            transform_source TEXT DEFAULT 'dxf_extraction',
            FOREIGN KEY (guid) REFERENCES elements_meta(guid)
        );

        -- Spatial structure
        CREATE TABLE IF NOT EXISTS spatial_structure (
            guid TEXT PRIMARY KEY,
            building TEXT,
            storey TEXT,
            space TEXT,
            FOREIGN KEY (guid) REFERENCES elements_meta(guid)
        );

        -- Global offset for coordinate alignment
        CREATE TABLE IF NOT EXISTS global_offset (
            offset_x REAL NOT NULL,
            offset_y REAL NOT NULL,
            offset_z REAL NOT NULL,
            extent_x REAL,
            extent_y REAL,
            extent_z REAL
        );

        -- Extraction metadata
        CREATE TABLE IF NOT EXISTS extraction_metadata (
            extraction_date TEXT NOT NULL,
            extraction_mode TEXT NOT NULL,
            total_elements INTEGER,
            unique_geometries INTEGER,
            source_files TEXT,
            config_json TEXT
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_elements_discipline ON elements_meta(discipline);
        CREATE INDEX IF NOT EXISTS idx_elements_ifc_class ON elements_meta(ifc_class);
        CREATE INDEX IF NOT EXISTS idx_elements_storey ON elements_meta(storey);
        CREATE INDEX IF NOT EXISTS idx_instances_hash ON element_instances(geometry_hash);

        -- R-tree spatial index for 3D bounding box queries
        CREATE VIRTUAL TABLE IF NOT EXISTS elements_rtree USING rtree(
            id,
            minX, maxX,
            minY, maxY,
            minZ, maxZ
        );

        -- Element geometry view (for Bonsai bake compatibility)
        CREATE VIEW IF NOT EXISTS element_geometry AS
        SELECT
            ei.guid,
            ei.geometry_hash,
            bg.vertices,
            bg.faces,
            bg.vertex_count,
            bg.face_count,
            bg.normals
        FROM element_instances ei
        JOIN base_geometries bg ON ei.geometry_hash = bg.geometry_hash;
    """)

    conn.commit()
    print("Database schema created")

# ============================================================================
# TEMPLATE GEOMETRY GENERATION
# ============================================================================

def create_template_geometries(conn: sqlite3.Connection, templates: Dict) -> Dict[str, str]:
    """
    Create template geometries in base_geometries table.
    Returns mapping of template_key -> geometry_hash.
    """
    cursor = conn.cursor()
    template_hashes = {}

    # ARC elements
    for ifc_class, template in templates.get('arc_elements', {}).items():
        params = template.get('parameters', {})
        geom_type = template.get('geometry_type', 'box')

        if geom_type == 'box' or geom_type == 'extrusion':
            width = params.get('width_m', params.get('thickness_m', 0.2))
            depth = params.get('depth_m', width)
            height = params.get('height_m', 3.0)
            vertices, faces, normals = generate_box_geometry(width, depth, height)
        elif geom_type == 'cylinder':
            radius = params.get('width_m', 0.4) / 2
            height = params.get('height_m', 4.0)
            vertices, faces, normals = generate_cylinder_geometry(radius, height)
        else:
            # Default box
            vertices, faces, normals = generate_box_geometry(1.0, 1.0, 1.0)

        # Pack and hash
        v_blob = pack_vertices(vertices)
        f_blob = pack_faces(faces)
        n_blob = pack_normals(normals)
        geom_hash = compute_hash(v_blob, f_blob)

        # Store
        cursor.execute("""
            INSERT OR REPLACE INTO base_geometries
            (geometry_hash, vertices, faces, normals, vertex_count, face_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (geom_hash, v_blob, f_blob, n_blob, len(vertices), len(faces)))

        template_hashes[f"ARC_{ifc_class}"] = geom_hash

    # STR elements
    for ifc_class, template in templates.get('str_elements', {}).items():
        params = template.get('parameters', {})
        geom_type = template.get('geometry_type', 'box')

        if ifc_class == 'IfcColumn':
            # Square columns for STR
            size = params.get('width_m', 0.75)
            height = params.get('height_m', 4.0)
            vertices, faces, normals = generate_box_geometry(size, size, height)
        elif ifc_class == 'IfcBeam':
            width = params.get('width_m', 0.3)
            depth = params.get('depth_m', 0.7)
            # Length will be per-instance
            vertices, faces, normals = generate_box_geometry(1.0, width, depth)  # Unit length
        else:
            width = params.get('width_m', params.get('thickness_m', 0.3))
            depth = params.get('depth_m', width)
            height = params.get('height_m', 0.3)
            vertices, faces, normals = generate_box_geometry(width, depth, height)

        v_blob = pack_vertices(vertices)
        f_blob = pack_faces(faces)
        n_blob = pack_normals(normals)
        geom_hash = compute_hash(v_blob, f_blob)

        cursor.execute("""
            INSERT OR REPLACE INTO base_geometries
            (geometry_hash, vertices, faces, normals, vertex_count, face_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (geom_hash, v_blob, f_blob, n_blob, len(vertices), len(faces)))

        template_hashes[f"STR_{ifc_class}"] = geom_hash

    conn.commit()
    print(f"Created {len(template_hashes)} template geometries")
    return template_hashes

# ============================================================================
# WALL SEGMENT MERGING
# ============================================================================

def merge_wall_segments(segments: List[Tuple[Tuple[float, float], Tuple[float, float]]],
                        tolerance: float = 100.0) -> List[List[Tuple[float, float]]]:
    """
    Merge connected LINE/POLYLINE segments into continuous wall chains.

    Args:
        segments: List of (start, end) coordinate tuples in mm
        tolerance: Snapping tolerance in mm (default 100mm = 10cm)

    Returns:
        List of polyline chains, each a list of (x, y) points
    """
    from collections import defaultdict

    def round_to_tolerance(x, y):
        return (round(x / tolerance) * tolerance, round(y / tolerance) * tolerance)

    # Build adjacency graph with snapped coordinates
    graph = defaultdict(set)
    point_to_original = {}  # Map snapped -> original coordinates

    for start, end in segments:
        start_snap = round_to_tolerance(*start)
        end_snap = round_to_tolerance(*end)

        if start_snap == end_snap:
            continue  # Skip zero-length segments

        graph[start_snap].add(end_snap)
        graph[end_snap].add(start_snap)

        # Keep best original coordinates (average if multiple)
        if start_snap not in point_to_original:
            point_to_original[start_snap] = start
        if end_snap not in point_to_original:
            point_to_original[end_snap] = end

    # Find chains using DFS
    visited = set()
    chains = []

    def build_chain(start_node):
        """Build a chain following connected segments."""
        chain = [start_node]
        visited.add(start_node)

        # Extend in one direction
        current = start_node
        while True:
            neighbors = graph[current] - visited
            if not neighbors:
                break
            next_node = min(neighbors)  # Deterministic choice
            chain.append(next_node)
            visited.add(next_node)
            current = next_node

        # Try extending from start in other direction
        current = start_node
        while True:
            neighbors = graph[current] - visited
            if not neighbors:
                break
            next_node = min(neighbors)
            chain.insert(0, next_node)
            visited.add(next_node)
            current = next_node

        return chain

    # Build all chains
    for node in graph:
        if node not in visited:
            chain = build_chain(node)
            if len(chain) >= 2:
                # Convert back to original coordinates
                original_chain = [point_to_original.get(p, p) for p in chain]
                chains.append(original_chain)

    return chains


# ============================================================================
# DXF EXTRACTION
# ============================================================================

def apply_rotation_transform(x: float, y: float) -> Tuple[float, float]:
    """Apply 90° CCW rotation: (x, y) → (-y, x)"""
    return (-y, x)

def extract_dxf_entities(dxf_path: Path, discipline: str, floor: str,
                        templates: Dict, layer_mapping: Dict) -> List[Dict]:
    """
    Extract entities from DXF file and classify by layer.
    Merges wall LINE segments into continuous polylines for proper extrusion.
    Returns list of element dicts ready for database insertion.
    """
    elements = []

    try:
        doc = ezdxf.readfile(str(dxf_path))
    except Exception as e:
        print(f"  ERROR reading {dxf_path.name}: {e}")
        return elements

    msp = doc.modelspace()

    # Determine coordinate offset based on discipline
    if discipline == 'ARC':
        offset_x, offset_y = -68.9, 1598.6
    else:  # STR
        offset_x, offset_y = -35.7, -44.5

    # ========================================================================
    # PHASE 1: Collect and merge wall segments
    # ========================================================================
    wall_segments = []  # List of (start, end) in mm

    for entity in msp:
        if not hasattr(entity.dxf, 'layer'):
            continue

        layer_raw = entity.dxf.layer
        layer_upper = layer_raw.upper()
        mapping = layer_mapping.get(layer_raw) or layer_mapping.get(layer_upper)

        if not mapping or mapping.get('ifc_class') != 'IfcWall':
            continue

        # Collect wall segments
        if entity.dxftype() == 'LINE':
            start = (entity.dxf.start.x, entity.dxf.start.y)
            end = (entity.dxf.end.x, entity.dxf.end.y)
            wall_segments.append((start, end))

        elif entity.dxftype() == 'LWPOLYLINE':
            points = list(entity.get_points('xy'))
            for i in range(len(points) - 1):
                start = (points[i][0], points[i][1])
                end = (points[i+1][0], points[i+1][1])
                wall_segments.append((start, end))

    # Create individual wall elements from each segment (no merging for better accuracy)
    if wall_segments:
        print(f"    Walls: {len(wall_segments)} segments (keeping individual)")

        for start, end in wall_segments:
            # Calculate segment length
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = math.sqrt(dx*dx + dy*dy)

            # Skip very short walls (likely artifacts)
            if length < 500:  # 500mm = 0.5m (filter small segments that are DXF artifacts)
                continue

            # Calculate center and rotation
            cx = (start[0] + end[0]) / 2
            cy = (start[1] + end[1]) / 2
            rotation = math.atan2(dy, dx)

            # Transform to world coordinates
            cx_m, cy_m = cx / 1000.0, cy / 1000.0
            cx_rot, cy_rot = apply_rotation_transform(cx_m, cy_m)
            cx_final = cx_rot + offset_x
            cy_final = cy_rot + offset_y

            # Transform endpoints for polyline
            start_m = (start[0] / 1000.0, start[1] / 1000.0)
            end_m = (end[0] / 1000.0, end[1] / 1000.0)
            start_rot = apply_rotation_transform(*start_m)
            end_rot = apply_rotation_transform(*end_m)
            transformed_chain = [
                (start_rot[0] + offset_x, start_rot[1] + offset_y),
                (end_rot[0] + offset_x, end_rot[1] + offset_y)
            ]

            guid = str(uuid.uuid4()).replace('-', '')[:22]
            elements.append({
                'guid': guid,
                'discipline': discipline,
                'ifc_class': 'IfcWall',
                'floor': floor,
                'center_x': cx_final,
                'center_y': cy_final,
                'center_z': 0,
                'rotation_z': rotation,
                'length': length / 1000.0,
                'layer': 'WALL',
                'source_file': dxf_path.name,
                'polyline_points': transformed_chain
            })

    # ========================================================================
    # PHASE 2: Extract non-wall entities normally
    # ========================================================================
    for entity in msp:
        if entity.dxftype() not in ['LINE', 'LWPOLYLINE', 'CIRCLE', 'ARC', 'INSERT']:
            continue

        layer_raw = entity.dxf.layer if hasattr(entity.dxf, 'layer') else ''
        layer_upper = layer_raw.upper()
        mapping = layer_mapping.get(layer_raw) or layer_mapping.get(layer_upper)

        if not mapping:
            continue

        ifc_class = mapping.get('ifc_class', 'IfcBuildingElementProxy')
        elem_discipline = mapping.get('discipline', discipline)

        # Skip walls - already processed above
        if ifc_class == 'IfcWall':
            continue

        # Extract position based on entity type
        x, y, z = 0, 0, 0
        length = 0
        rotation = 0
        polyline_points_raw = None

        if entity.dxftype() == 'CIRCLE':
            x, y = entity.dxf.center.x, entity.dxf.center.y
            z = entity.dxf.center.z if hasattr(entity.dxf.center, 'z') else 0
            length = entity.dxf.radius * 2

        elif entity.dxftype() == 'LINE':
            start = entity.dxf.start
            end = entity.dxf.end
            x = (start.x + end.x) / 2
            y = (start.y + end.y) / 2
            z = (start.z + end.z) / 2 if hasattr(start, 'z') else 0
            length = math.sqrt((end.x - start.x)**2 + (end.y - start.y)**2)
            if length > 0.001:
                rotation = math.atan2(end.y - start.y, end.x - start.x)

        elif entity.dxftype() == 'LWPOLYLINE':
            points = list(entity.get_points('xy'))
            if points:
                x = sum(p[0] for p in points) / len(points)
                y = sum(p[1] for p in points) / len(points)
                for i in range(len(points) - 1):
                    length += math.sqrt((points[i+1][0] - points[i][0])**2 +
                                       (points[i+1][1] - points[i][1])**2)
                polyline_points_raw = points

        elif entity.dxftype() == 'INSERT':
            x, y = entity.dxf.insert.x, entity.dxf.insert.y
            z = entity.dxf.insert.z if hasattr(entity.dxf.insert, 'z') else 0
            rotation = math.radians(entity.dxf.rotation) if hasattr(entity.dxf, 'rotation') else 0

        elif entity.dxftype() == 'ARC':
            x, y = entity.dxf.center.x, entity.dxf.center.y
            z = entity.dxf.center.z if hasattr(entity.dxf.center, 'z') else 0
            length = entity.dxf.radius

        # Convert to meters and apply transforms
        x_m, y_m, z_m = x / 1000.0, y / 1000.0, z / 1000.0
        length_m = length / 1000.0

        x_rot, y_rot = apply_rotation_transform(x_m, y_m)
        x_final = x_rot + offset_x
        y_final = y_rot + offset_y

        # Also rotate the angle by 90° CCW to match coordinate rotation
        rotation_transformed = rotation + math.pi / 2

        # Transform polyline points if present
        polyline_points_transformed = None
        if polyline_points_raw:
            polyline_points_transformed = []
            for px, py in polyline_points_raw:
                px_m, py_m = px / 1000.0, py / 1000.0
                px_rot, py_rot = apply_rotation_transform(px_m, py_m)
                polyline_points_transformed.append((px_rot + offset_x, py_rot + offset_y))

        guid = str(uuid.uuid4()).replace('-', '')[:22]
        elements.append({
            'guid': guid,
            'discipline': elem_discipline,
            'ifc_class': ifc_class,
            'floor': floor,
            'center_x': x_final,
            'center_y': y_final,
            'center_z': z_m,
            'rotation_z': rotation_transformed,
            'length': length_m,
            'layer': layer_raw,
            'source_file': dxf_path.name,
            'polyline_points': polyline_points_transformed
        })

    return elements

# ============================================================================
# MAIN GENERATION
# ============================================================================

def main():
    print("="*70)
    print("ARC/STR DATABASE GENERATOR - Instanced Geometry Pattern")
    print("="*70)

    # Clean up existing files
    if BLEND_OUTPUT.exists():
        BLEND_OUTPUT.unlink()
        print(f"Deleted existing: {BLEND_OUTPUT.name}")

    if BLEND_FULL_OUTPUT.exists():
        BLEND_FULL_OUTPUT.unlink()
        print(f"Deleted existing: {BLEND_FULL_OUTPUT.name}")

    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()
        print(f"Deleted existing: {OUTPUT_DB.name}")

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load templates
    if not TEMPLATES_FILE.exists():
        print(f"ERROR: Templates file not found: {TEMPLATES_FILE}")
        sys.exit(1)

    with open(TEMPLATES_FILE) as f:
        templates = json.load(f)
    print(f"Loaded templates from: {TEMPLATES_FILE.name}")

    # Load cheatsheet for alignment info
    if CHEATSHEET_FILE.exists():
        with open(CHEATSHEET_FILE) as f:
            cheatsheet = json.load(f)
        print(f"Loaded cheatsheet from: {CHEATSHEET_FILE.name}")
    else:
        cheatsheet = {}

    # Get layer mapping
    layer_mapping = templates.get('dxf_layer_to_ifc_mapping', {})

    # Create database
    conn = sqlite3.connect(str(OUTPUT_DB))
    create_database_schema(conn)

    # Create template geometries
    template_hashes = create_template_geometries(conn, templates)

    # Define source files
    dxf_sources = [
        ('ARC', '1F', EXTRACTED_DIR / "Terminal1_ARC.dxf"),
        ('STR', '1F', EXTRACTED_DIR / "Terminal1_STR_1F.dxf"),
        ('STR', '3F', EXTRACTED_DIR / "Terminal1_STR_3F.dxf"),
        ('STR', '4F-6F', EXTRACTED_DIR / "Terminal1_STR_4F-6F.dxf"),
    ]

    # Get floor elevations
    floor_elevations = templates.get('floor_elevations_m', {
        '1F': 0.0, '3F': 8.0, '4F-6F': 12.0
    })

    # Extract all entities
    all_elements = []
    cursor = conn.cursor()

    print("\nExtracting DXF entities...")
    for discipline, floor, dxf_path in dxf_sources:
        if not dxf_path.exists():
            print(f"  SKIP: {dxf_path.name} not found")
            continue

        elements = extract_dxf_entities(dxf_path, discipline, floor, templates, layer_mapping)

        # Set Z elevation based on floor
        base_z = floor_elevations.get(floor, 0.0)
        for elem in elements:
            elem['center_z'] = base_z

        all_elements.extend(elements)
        print(f"  {dxf_path.name}: {len(elements)} elements")

    print(f"\nTotal elements extracted from DXF: {len(all_elements)}")

    # ========================================================================
    # ADD DOME FROM BUILDING CONFIG
    # ========================================================================
    building_config_path = BASE_DIR / "building_config.json"
    if building_config_path.exists():
        with open(building_config_path) as f:
            building_config = json.load(f)

        dome_config = building_config.get('dome', {})
        if dome_config.get('enabled', False):
            print("\nGenerating dome element...")
            dome_guid = str(uuid.uuid4()).replace('-', '')[:22]
            dome_element = {
                'guid': dome_guid,
                'discipline': 'ARC',
                'ifc_class': 'IfcRoof',
                'floor': 'ROOF',
                'center_x': dome_config.get('center_x_m', 0.0),
                'center_y': dome_config.get('center_y_m', 10.0),
                'center_z': dome_config.get('base_elevation_m', 12.5),
                'rotation_z': 0,
                'length': dome_config.get('radius_m', 12.5) * 2,
                'layer': 'DOME',
                'source_file': 'building_config.json',
                'polyline_points': None,
                'dome_config': dome_config  # Pass config for geometry generation
            }
            all_elements.append(dome_element)
            print(f"  Dome: radius={dome_config.get('radius_m')}m, height={dome_config.get('height_m')}m")

        # Generate floor slabs from building_config
        gen_options = building_config.get('generation_options', {})
        if gen_options.get('generate_floor_slabs', True):
            print("\nGenerating floor slabs...")
            floors_config = building_config.get('floors', {})

            # Calculate building footprint from existing elements
            if all_elements:
                min_x = min(e['center_x'] for e in all_elements) - 5
                max_x = max(e['center_x'] for e in all_elements) + 5
                min_y = min(e['center_y'] for e in all_elements) - 5
                max_y = max(e['center_y'] for e in all_elements) + 5

                slab_width = max_x - min_x
                slab_depth = max_y - min_y
                slab_cx = (min_x + max_x) / 2
                slab_cy = (min_y + max_y) / 2

                floor_count = 0
                for floor_id, floor_data in floors_config.items():
                    if floor_id == 'ROOF':
                        continue  # Skip roof level

                    elevation = floor_data.get('elevation_m', 0.0)
                    thickness = floor_data.get('slab_thickness_m', 0.3)

                    slab_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    slab_element = {
                        'guid': slab_guid,
                        'discipline': 'STR',
                        'ifc_class': 'IfcSlab',
                        'floor': floor_id,
                        'center_x': slab_cx,
                        'center_y': slab_cy,
                        'center_z': elevation,
                        'rotation_z': 0,
                        'length': slab_width,  # Will use as both width and depth
                        'layer': 'FLOOR_SLAB',
                        'source_file': 'building_config.json',
                        'polyline_points': None,
                        'floor_slab_config': {
                            'width': slab_width,
                            'depth': slab_depth,
                            'thickness': thickness
                        }
                    }
                    all_elements.append(slab_element)
                    floor_count += 1

                print(f"  Generated {floor_count} floor slabs ({slab_width:.1f}m x {slab_depth:.1f}m)")

        # Generate perimeter walls (default enclosure)
        if gen_options.get('generate_perimeter_walls', True) and all_elements:
            print("\nGenerating perimeter walls...")

            wall_height = 3.5  # Default wall height
            wall_thickness = 0.2

            # Create 4 perimeter walls (N, E, S, W)
            perimeter_walls = [
                # North wall (top edge, runs E-W)
                {'start': (min_x, max_y), 'end': (max_x, max_y), 'name': 'North'},
                # East wall (right edge, runs N-S)
                {'start': (max_x, min_y), 'end': (max_x, max_y), 'name': 'East'},
                # South wall (bottom edge, runs E-W)
                {'start': (min_x, min_y), 'end': (max_x, min_y), 'name': 'South'},
                # West wall (left edge, runs N-S)
                {'start': (min_x, min_y), 'end': (min_x, max_y), 'name': 'West'},
            ]

            for wall in perimeter_walls:
                start = wall['start']
                end = wall['end']

                # Calculate wall properties
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                length = math.sqrt(dx*dx + dy*dy)
                cx = (start[0] + end[0]) / 2
                cy = (start[1] + end[1]) / 2
                rotation = math.atan2(dy, dx)

                wall_guid = str(uuid.uuid4()).replace('-', '')[:22]
                wall_element = {
                    'guid': wall_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcWall',
                    'floor': '1F',
                    'center_x': cx,
                    'center_y': cy,
                    'center_z': 0.0,
                    'rotation_z': rotation,
                    'length': length,
                    'layer': f'PERIMETER_{wall["name"].upper()}',
                    'source_file': 'building_config.json',
                    'polyline_points': [start, end]
                }
                all_elements.append(wall_element)

            print(f"  Generated 4 perimeter walls ({slab_width:.1f}m x {slab_depth:.1f}m enclosure)")

        # Generate default entrance doors (POC template)
        if gen_options.get('generate_entrance_doors', True) and all_elements:
            print("\nGenerating entrance doors...")

            door_width = 2.0
            door_height = 2.5
            door_depth = 0.2

            # Entrance doors on each side (centered)
            entrance_doors = [
                {'pos': (slab_cx, max_y), 'name': 'North_Entrance'},
                {'pos': (max_x, slab_cy), 'name': 'East_Entrance'},
                {'pos': (slab_cx, min_y), 'name': 'South_Entrance'},
                {'pos': (min_x, slab_cy), 'name': 'West_Entrance'},
            ]

            for door in entrance_doors:
                door_guid = str(uuid.uuid4()).replace('-', '')[:22]
                door_element = {
                    'guid': door_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcDoor',
                    'floor': '1F',
                    'center_x': door['pos'][0],
                    'center_y': door['pos'][1],
                    'center_z': 0.0,
                    'rotation_z': 0,
                    'length': door_width,
                    'layer': f'DOOR_{door["name"].upper()}',
                    'source_file': 'building_config.json',
                    'polyline_points': None
                }
                all_elements.append(door_element)

            print(f"  Generated 4 entrance doors")

        # Generate default stairs (POC template - vertical circulation)
        if gen_options.get('generate_stairs', True) and all_elements:
            print("\nGenerating stairs...")

            stair_width = 1.5
            stair_run = 3.0
            stair_rise = 4.0  # One floor height

            # Stairs at corners for vertical circulation
            stairs = [
                {'pos': (min_x + 5, min_y + 5), 'name': 'SW_Stair'},
                {'pos': (max_x - 5, min_y + 5), 'name': 'SE_Stair'},
                {'pos': (min_x + 5, max_y - 5), 'name': 'NW_Stair'},
                {'pos': (max_x - 5, max_y - 5), 'name': 'NE_Stair'},
            ]

            for stair in stairs:
                stair_guid = str(uuid.uuid4()).replace('-', '')[:22]
                stair_element = {
                    'guid': stair_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcStairFlight',
                    'floor': '1F',
                    'center_x': stair['pos'][0],
                    'center_y': stair['pos'][1],
                    'center_z': 0.0,
                    'rotation_z': 0,
                    'length': stair_run,
                    'layer': f'STAIR_{stair["name"].upper()}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'stair_config': {
                        'width': stair_width,
                        'run': stair_run,
                        'rise': stair_rise,
                        'treads': 12,
                        'riser_height': stair_rise / 12
                    }
                }
                all_elements.append(stair_element)

            print(f"  Generated 4 stairs (vertical circulation)")

        # Generate conduits for MEP routing (placeholder for future disciplines)
        if gen_options.get('generate_conduits', False):
            print("\nGenerating MEP conduits (placeholder)...")
            # Future: Add vertical and horizontal conduit runs for MEP routing
            # - Vertical risers at core locations
            # - Horizontal runs along corridors
            # - Connection points at floor levels

    print(f"\nTotal elements (with dome, slabs, perimeter, doors): {len(all_elements)}")

    # Insert elements into database
    print("\nPopulating database...")
    stats = {'by_class': {}, 'by_discipline': {}}

    for elem in all_elements:
        guid = elem['guid']

        # Get element dimensions from template
        template_key_lookup = elem['ifc_class']
        if elem['discipline'] == 'ARC':
            params = templates.get('arc_elements', {}).get(template_key_lookup, {}).get('parameters', {})
            material_info = templates.get('arc_elements', {}).get(template_key_lookup, {}).get('material', {})
        else:
            params = templates.get('str_elements', {}).get(template_key_lookup, {}).get('parameters', {})
            material_info = templates.get('str_elements', {}).get(template_key_lookup, {}).get('material', {})

        material_name = material_info.get('name', 'Default')
        material_rgba = json.dumps(material_info.get('rgba', [0.7, 0.7, 0.7, 1.0]))

        # Generate geometry using factory function (handles all element types)
        geom_result = generate_element_geometry(elem, templates)
        vertices, faces, normals = geom_result.vertices, geom_result.faces, geom_result.normals

        # Pack and hash
        v_blob = pack_vertices(vertices)
        f_blob = pack_faces(faces)
        n_blob = pack_normals(normals)
        geom_hash = compute_hash(v_blob, f_blob)

        # Store geometry (each element has unique world-positioned geometry)
        cursor.execute("""
            INSERT OR IGNORE INTO base_geometries
            (geometry_hash, vertices, faces, normals, vertex_count, face_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (geom_hash, v_blob, f_blob, n_blob, len(vertices), len(faces)))

        # Insert element metadata
        cursor.execute("""
            INSERT INTO elements_meta
            (guid, discipline, ifc_class, filepath, element_name, storey, material_name, material_rgba)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (guid, elem['discipline'], elem['ifc_class'], elem['source_file'],
              f"{elem['ifc_class']}_{guid[:8]}", elem['floor'], material_name, material_rgba))

        # Insert element instance (points to template geometry)
        cursor.execute("""
            INSERT INTO element_instances (guid, geometry_hash)
            VALUES (?, ?)
        """, (guid, geom_hash))

        # Insert transform
        cursor.execute("""
            INSERT INTO element_transforms
            (guid, center_x, center_y, center_z, rotation_z, length)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (guid, elem['center_x'], elem['center_y'], elem['center_z'],
              elem['rotation_z'], elem['length']))

        # Insert spatial structure
        cursor.execute("""
            INSERT INTO spatial_structure (guid, building, storey)
            VALUES (?, ?, ?)
        """, (guid, 'Terminal 1', elem['floor']))

        # Calculate bounding box from actual vertices
        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        zs = [v[2] for v in vertices]
        minX, maxX = min(xs), max(xs)
        minY, maxY = min(ys), max(ys)
        minZ, maxZ = min(zs), max(zs)

        # Get row id from elements_meta for rtree
        cursor.execute("SELECT id FROM elements_meta WHERE guid = ?", (guid,))
        row_id = cursor.fetchone()[0]

        # Insert into R-tree spatial index
        cursor.execute("""
            INSERT INTO elements_rtree (id, minX, maxX, minY, maxY, minZ, maxZ)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (row_id, minX, maxX, minY, maxY, minZ, maxZ))

        # Track stats
        ifc_class = elem['ifc_class']
        discipline = elem['discipline']
        stats['by_class'][ifc_class] = stats['by_class'].get(ifc_class, 0) + 1
        stats['by_discipline'][discipline] = stats['by_discipline'].get(discipline, 0) + 1

    # Insert extraction metadata
    cursor.execute("""
        INSERT INTO extraction_metadata
        (extraction_date, extraction_mode, total_elements, unique_geometries, source_files, config_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), 'instanced_geometry', len(all_elements),
          len(template_hashes), json.dumps([str(s[2].name) for s in dxf_sources]),
          json.dumps({'templates': TEMPLATES_FILE.name})))

    # Insert global offset (for coordinate alignment)
    cursor.execute("""
        INSERT INTO global_offset (offset_x, offset_y, offset_z)
        VALUES (0, 0, 0)
    """)

    conn.commit()
    conn.close()

    # Print summary
    print("\n" + "="*70)
    print("DATABASE GENERATION COMPLETE")
    print("="*70)
    print(f"Output: {OUTPUT_DB}")
    print(f"Total elements: {len(all_elements)}")
    print(f"Unique geometries: {len(template_hashes)}")
    print(f"Storage optimization: {len(all_elements)/len(template_hashes):.1f}x instances per geometry")

    print("\nBy Discipline:")
    for disc, count in sorted(stats['by_discipline'].items()):
        print(f"  {disc}: {count}")

    print("\nBy IFC Class:")
    for ifc_class, count in sorted(stats['by_class'].items(), key=lambda x: -x[1]):
        print(f"  {ifc_class}: {count}")

    print("\n" + "="*70)
    print("Next: Load in Bonsai BBox Preview or run blend bake")
    print("="*70)

    # Auto-run audit if --audit flag is passed
    if '--audit' in sys.argv:
        print("\n")
        from audit_database import generate_report
        report = generate_report(str(OUTPUT_DB))
        print(report)


if __name__ == "__main__":
    main()
