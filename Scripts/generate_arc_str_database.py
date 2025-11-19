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

# Import MEP generator classes
from mep_generator import MEPGeneratorOrchestrator

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

        # Skip oversized beams (likely DXF artifacts or reference lines)
        # Typical structural beam span is 6-12m, max 15m
        if ifc_class == 'IfcBeam' and length_m > 15.0:
            continue

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

            # Calculate building footprint from structural elements only (walls, columns)
            # This avoids scattered plates/windows skewing the footprint
            structural_elements = [e for e in all_elements
                                   if e['ifc_class'] in ['IfcWall', 'IfcColumn', 'IfcBeam']]

            if structural_elements:
                min_x = min(e['center_x'] for e in structural_elements)
                max_x = max(e['center_x'] for e in structural_elements)
                min_y = min(e['center_y'] for e in structural_elements)
                max_y = max(e['center_y'] for e in structural_elements)

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

        # Generate perimeter walls (default enclosure) - use structural footprint
        if gen_options.get('generate_perimeter_walls', True) and structural_elements:
            print("\nGenerating perimeter walls...")

            wall_height = 3.5  # Default wall height
            wall_thickness = 0.2

            # Use the structural-based bounds (not scattered plates)
            # Note: min_x, max_x, min_y, max_y already calculated above from structural_elements

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

        # Generate covered walkway/canopy to jetty (north side)
        if gen_options.get('generate_entrance_doors', True) and structural_elements:
            print("\nGenerating jetty canopy...")

            canopy_width = 8.0
            canopy_length = 20.0  # Extends from building to jetty
            canopy_height = 4.0
            canopy_thickness = 0.3

            # Canopy structure extending north from building
            canopy_guid = str(uuid.uuid4()).replace('-', '')[:22]
            all_elements.append({
                'guid': canopy_guid,
                'discipline': 'ARC',
                'ifc_class': 'IfcSlab',  # Canopy roof
                'floor': 'GF',
                'center_x': slab_cx,
                'center_y': max_y + canopy_length/2,
                'center_z': canopy_height,
                'rotation_z': 0,
                'length': canopy_length,
                'layer': 'CANOPY_JETTY',
                'source_file': 'building_config.json',
                'polyline_points': None,
                'slab_config': {
                    'width': canopy_width,
                    'depth': canopy_length,
                    'thickness': canopy_thickness
                }
            })

            # Support columns for canopy
            canopy_columns = [
                {'pos': (slab_cx - 3, max_y + 5), 'name': 'CanopyCol_1'},
                {'pos': (slab_cx + 3, max_y + 5), 'name': 'CanopyCol_2'},
                {'pos': (slab_cx - 3, max_y + 15), 'name': 'CanopyCol_3'},
                {'pos': (slab_cx + 3, max_y + 15), 'name': 'CanopyCol_4'},
            ]

            for col in canopy_columns:
                col_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': col_guid,
                    'discipline': 'STR',
                    'ifc_class': 'IfcColumn',
                    'floor': 'GF',
                    'center_x': col['pos'][0],
                    'center_y': col['pos'][1],
                    'center_z': 0.0,
                    'rotation_z': 0,
                    'length': 0.3,  # Column diameter
                    'layer': f'STRUCT_{col["name"]}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'column_config': {
                        'diameter': 0.3,
                        'height': canopy_height
                    }
                })

            print(f"  Generated jetty canopy with 4 columns")

        # Generate external signage pylon
        if gen_options.get('generate_entrance_doors', True) and structural_elements:
            print("\nGenerating signage pylons...")

            pylon_width = 2.0
            pylon_depth = 0.5
            pylon_height = 8.0

            # Pylons at main entrances
            pylon_positions = [
                {'pos': (slab_cx, min_y - 5), 'name': 'Pylon_South'},  # Main entrance
                {'pos': (min_x - 5, slab_cy), 'name': 'Pylon_West'},
            ]

            for pylon in pylon_positions:
                pylon_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': pylon_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcFurniture',
                    'floor': 'GF',
                    'center_x': pylon['pos'][0],
                    'center_y': pylon['pos'][1],
                    'center_z': 0.0,
                    'rotation_z': 0,
                    'length': pylon_width,
                    'layer': f'SIGNAGE_{pylon["name"]}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'furniture_config': {
                        'width': pylon_width,
                        'depth': pylon_depth,
                        'height': pylon_height
                    }
                })

            print(f"  Generated {len(pylon_positions)} signage pylons")

        # Generate vehicle drop-off zone (south entrance)
        if gen_options.get('generate_entrance_doors', True) and structural_elements:
            print("\nGenerating drop-off zone...")

            # Drop-off canopy/shelter
            dropoff_canopy_guid = str(uuid.uuid4()).replace('-', '')[:22]
            all_elements.append({
                'guid': dropoff_canopy_guid,
                'discipline': 'ARC',
                'ifc_class': 'IfcSlab',
                'floor': 'GF',
                'center_x': slab_cx,
                'center_y': min_y - 10,
                'center_z': 5.0,  # Higher for vehicles
                'rotation_z': 0,
                'length': 15.0,
                'layer': 'CANOPY_DROPOFF',
                'source_file': 'building_config.json',
                'polyline_points': None,
                'slab_config': {
                    'width': 15.0,
                    'depth': 8.0,
                    'thickness': 0.3
                }
            })

            # Bollards for traffic control
            bollard_spacing = 3.0
            num_bollards = 6
            start_x = slab_cx - (num_bollards - 1) * bollard_spacing / 2

            for i in range(num_bollards):
                bollard_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': bollard_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcFurniture',
                    'floor': 'GF',
                    'center_x': start_x + i * bollard_spacing,
                    'center_y': min_y - 6,
                    'center_z': 0.0,
                    'rotation_z': 0,
                    'length': 0.3,
                    'layer': f'BOLLARD_{i+1}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'furniture_config': {
                        'width': 0.3,
                        'depth': 0.3,
                        'height': 1.0
                    }
                })

            print(f"  Generated drop-off canopy with {num_bollards} bollards")

        # Generate security checkpoints (GF - near entrances)
        if gen_options.get('generate_counters', True) and structural_elements:
            print("\nGenerating security checkpoints...")

            # Security screening lanes
            lane_width = 1.2
            lane_depth = 3.0
            lane_height = 2.0

            # Checkpoint near south entrance (main departure)
            num_lanes = 4
            lane_spacing = 2.0
            start_x = slab_cx - (num_lanes - 1) * lane_spacing / 2

            for i in range(num_lanes):
                security_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': security_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcFurniture',
                    'floor': 'GF',
                    'center_x': start_x + i * lane_spacing,
                    'center_y': min_y + 25,  # After ticketing area
                    'center_z': 0.0,
                    'rotation_z': 0,
                    'length': lane_depth,
                    'layer': f'SECURITY_LANE_{i+1}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'furniture_config': {
                        'width': lane_width,
                        'depth': lane_depth,
                        'height': lane_height
                    }
                })

            print(f"  Generated {num_lanes} security screening lanes")

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

        # ====================================================================
        # TRANSPORT HUB ELEMENTS - Glass facades, elevators, escalators
        # ====================================================================

        # Generate rooftop mechanical equipment (ROOF level)
        if gen_options.get('generate_curtain_walls', True) and structural_elements:
            print("\nGenerating rooftop equipment...")

            roof_z = 16.0  # Top of 4F-6F
            equip_count = 0

            # HVAC Chillers (large units)
            chiller_positions = [
                {'pos': (slab_cx - 12, slab_cy + 15), 'name': 'Chiller_1', 'size': (4.0, 2.5, 2.0)},
                {'pos': (slab_cx + 12, slab_cy + 15), 'name': 'Chiller_2', 'size': (4.0, 2.5, 2.0)},
            ]

            for chiller in chiller_positions:
                ch_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': ch_guid,
                    'discipline': 'ACMV',
                    'ifc_class': 'IfcFurniture',  # Mechanical equipment
                    'floor': 'ROOF',
                    'center_x': chiller['pos'][0],
                    'center_y': chiller['pos'][1],
                    'center_z': roof_z,
                    'rotation_z': 0,
                    'length': chiller['size'][0],
                    'layer': f'MECH_{chiller["name"]}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'furniture_config': {
                        'width': chiller['size'][0],
                        'depth': chiller['size'][1],
                        'height': chiller['size'][2]
                    }
                })
                equip_count += 1

            # Lift machine rooms (above elevator shafts)
            lift_rooms = [
                {'pos': (slab_cx - 3, slab_cy), 'name': 'LiftRoom_W', 'size': (3.0, 3.0, 2.5)},
                {'pos': (slab_cx + 3, slab_cy), 'name': 'LiftRoom_E', 'size': (3.0, 3.0, 2.5)},
            ]

            for lift in lift_rooms:
                lift_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': lift_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcSpace',
                    'floor': 'ROOF',
                    'center_x': lift['pos'][0],
                    'center_y': lift['pos'][1],
                    'center_z': roof_z,
                    'rotation_z': 0,
                    'length': lift['size'][0],
                    'layer': f'PLANT_{lift["name"]}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'space_config': {
                        'width': lift['size'][0],
                        'depth': lift['size'][1],
                        'height': lift['size'][2],
                        'space_type': 'Lift Machine Room'
                    }
                })
                equip_count += 1

            # AHU units (air handling)
            ahu_positions = [
                {'pos': (slab_cx - 15, slab_cy - 10), 'name': 'AHU_1'},
                {'pos': (slab_cx + 15, slab_cy - 10), 'name': 'AHU_2'},
                {'pos': (slab_cx, slab_cy + 20), 'name': 'AHU_3'},
            ]

            for ahu in ahu_positions:
                ahu_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': ahu_guid,
                    'discipline': 'ACMV',
                    'ifc_class': 'IfcFurniture',
                    'floor': 'ROOF',
                    'center_x': ahu['pos'][0],
                    'center_y': ahu['pos'][1],
                    'center_z': roof_z,
                    'rotation_z': 0,
                    'length': 3.0,
                    'layer': f'MECH_{ahu["name"]}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'furniture_config': {
                        'width': 3.0,
                        'depth': 2.0,
                        'height': 1.8
                    }
                })
                equip_count += 1

            print(f"  Generated {equip_count} rooftop mechanical equipment")

        # Generate glass curtain walls on all facades (multi-floor)
        if gen_options.get('generate_curtain_walls', True) and structural_elements:
            print("\nGenerating glass curtain walls...")

            glass_height = 3.0  # Height per floor
            glass_depth = 0.1   # Glass thickness
            panel_width = 3.0   # Width of each glass panel

            floors_config = building_config.get('floors', {})
            curtain_count = 0

            for floor_id, floor_data in floors_config.items():
                if floor_id == 'ROOF':
                    continue

                elevation = floor_data.get('elevation_m', 0.0)

                # North facade panels
                num_panels_ew = int(slab_width / panel_width)
                for i in range(num_panels_ew):
                    panel_x = min_x + panel_width/2 + i * panel_width
                    if panel_x > max_x - panel_width/2:
                        break

                    cw_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    all_elements.append({
                        'guid': cw_guid,
                        'discipline': 'ARC',
                        'ifc_class': 'IfcCurtainWall',
                        'floor': floor_id,
                        'center_x': panel_x,
                        'center_y': max_y,
                        'center_z': elevation,
                        'rotation_z': 0,
                        'length': panel_width,
                        'layer': f'CURTAIN_WALL_N_{floor_id}',
                        'source_file': 'building_config.json',
                        'polyline_points': None
                    })
                    curtain_count += 1

                # South facade panels
                for i in range(num_panels_ew):
                    panel_x = min_x + panel_width/2 + i * panel_width
                    if panel_x > max_x - panel_width/2:
                        break

                    cw_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    all_elements.append({
                        'guid': cw_guid,
                        'discipline': 'ARC',
                        'ifc_class': 'IfcCurtainWall',
                        'floor': floor_id,
                        'center_x': panel_x,
                        'center_y': min_y,
                        'center_z': elevation,
                        'rotation_z': 0,
                        'length': panel_width,
                        'layer': f'CURTAIN_WALL_S_{floor_id}',
                        'source_file': 'building_config.json',
                        'polyline_points': None
                    })
                    curtain_count += 1

                # East facade panels
                num_panels_ns = int(slab_depth / panel_width)
                for i in range(num_panels_ns):
                    panel_y = min_y + panel_width/2 + i * panel_width
                    if panel_y > max_y - panel_width/2:
                        break

                    cw_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    all_elements.append({
                        'guid': cw_guid,
                        'discipline': 'ARC',
                        'ifc_class': 'IfcCurtainWall',
                        'floor': floor_id,
                        'center_x': max_x,
                        'center_y': panel_y,
                        'center_z': elevation,
                        'rotation_z': math.pi/2,
                        'length': panel_width,
                        'layer': f'CURTAIN_WALL_E_{floor_id}',
                        'source_file': 'building_config.json',
                        'polyline_points': None
                    })
                    curtain_count += 1

                # West facade panels
                for i in range(num_panels_ns):
                    panel_y = min_y + panel_width/2 + i * panel_width
                    if panel_y > max_y - panel_width/2:
                        break

                    cw_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    all_elements.append({
                        'guid': cw_guid,
                        'discipline': 'ARC',
                        'ifc_class': 'IfcCurtainWall',
                        'floor': floor_id,
                        'center_x': min_x,
                        'center_y': panel_y,
                        'center_z': elevation,
                        'rotation_z': math.pi/2,
                        'length': panel_width,
                        'layer': f'CURTAIN_WALL_W_{floor_id}',
                        'source_file': 'building_config.json',
                        'polyline_points': None
                    })
                    curtain_count += 1

            print(f"  Generated {curtain_count} glass curtain wall panels")

        # Generate elevator shafts at building core
        if gen_options.get('generate_elevators', True) and structural_elements:
            print("\nGenerating elevator shafts...")

            elevator_width = 2.5
            elevator_depth = 2.5
            shaft_height = 16.5  # Full building height

            # 2 elevator shafts at core (center of building)
            elevator_positions = [
                {'pos': (slab_cx - 3, slab_cy), 'name': 'Elevator_1'},
                {'pos': (slab_cx + 3, slab_cy), 'name': 'Elevator_2'},
            ]

            for elev in elevator_positions:
                elev_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': elev_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcTransportElement',
                    'floor': '1F',
                    'center_x': elev['pos'][0],
                    'center_y': elev['pos'][1],
                    'center_z': 0.0,
                    'rotation_z': 0,
                    'length': elevator_width,
                    'layer': f'ELEVATOR_{elev["name"].upper()}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'elevator_config': {
                        'width': elevator_width,
                        'depth': elevator_depth,
                        'height': shaft_height
                    }
                })

            print(f"  Generated 2 elevator shafts at building core")

        # Generate escalators near main entrances
        if gen_options.get('generate_escalators', True) and structural_elements:
            print("\nGenerating escalators...")

            escalator_width = 1.2
            escalator_run = 8.0
            escalator_rise = 4.0  # One floor height

            # Escalators near N and S entrances (main passenger flow)
            escalator_positions = [
                {'pos': (slab_cx - 5, max_y - 10), 'name': 'North_Up', 'rotation': 0},
                {'pos': (slab_cx + 5, max_y - 10), 'name': 'North_Down', 'rotation': math.pi},
                {'pos': (slab_cx - 5, min_y + 10), 'name': 'South_Up', 'rotation': math.pi},
                {'pos': (slab_cx + 5, min_y + 10), 'name': 'South_Down', 'rotation': 0},
            ]

            for esc in escalator_positions:
                esc_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': esc_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcTransportElement',
                    'floor': '1F',
                    'center_x': esc['pos'][0],
                    'center_y': esc['pos'][1],
                    'center_z': 0.0,
                    'rotation_z': esc['rotation'],
                    'length': escalator_run,
                    'layer': f'ESCALATOR_{esc["name"].upper()}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'escalator_config': {
                        'width': escalator_width,
                        'run': escalator_run,
                        'rise': escalator_rise
                    }
                })

            print(f"  Generated 4 escalators (passenger circulation)")

        # ====================================================================
        # INTERIOR ELEMENTS - Restrooms, counters, seating, retail
        # ====================================================================

        # Generate restroom blocks with accessible facilities (MS 1184 / ADA compliance)
        if gen_options.get('generate_restrooms', True) and structural_elements:
            print("\nGenerating restroom blocks...")

            # Standard restroom dimensions (MS 1184 compliant)
            restroom_width = 8.0   # Wider for accessible stalls
            restroom_depth = 5.0   # Deeper for circulation
            restroom_height = 3.0

            floors_config = building_config.get('floors', {})
            restroom_count = 0

            for floor_id, floor_data in floors_config.items():
                if floor_id == 'ROOF':
                    continue

                elevation = floor_data.get('elevation_m', 0.0)

                # 4 restroom blocks per floor (corners, inset from perimeter)
                # Paired Male/Female with accessible facilities
                restroom_positions = [
                    {'pos': (min_x + 10, max_y - 10), 'name': f'WC_M_NW_{floor_id}', 'type': 'Male'},
                    {'pos': (max_x - 10, max_y - 10), 'name': f'WC_F_NE_{floor_id}', 'type': 'Female'},
                    {'pos': (min_x + 10, min_y + 10), 'name': f'WC_F_SW_{floor_id}', 'type': 'Female'},
                    {'pos': (max_x - 10, min_y + 10), 'name': f'WC_M_SE_{floor_id}', 'type': 'Male'},
                ]

                for rr in restroom_positions:
                    rr_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    all_elements.append({
                        'guid': rr_guid,
                        'discipline': 'ARC',
                        'ifc_class': 'IfcSpace',
                        'floor': floor_id,
                        'center_x': rr['pos'][0],
                        'center_y': rr['pos'][1],
                        'center_z': elevation,
                        'rotation_z': 0,
                        'length': restroom_width,
                        'layer': f'RESTROOM_{rr["name"]}',
                        'source_file': 'building_config.json',
                        'polyline_points': None,
                        'space_config': {
                            'width': restroom_width,
                            'depth': restroom_depth,
                            'height': restroom_height,
                            'space_type': rr['type'],
                            'accessible': True  # All include accessible stalls
                        }
                    })
                    restroom_count += 1

            print(f"  Generated {restroom_count} restroom blocks (MS 1184 compliant)")

        # Generate check-in/ticketing counters (ground floor only)
        if gen_options.get('generate_counters', True) and structural_elements:
            print("\nGenerating check-in counters...")

            # Realistic counter dimensions (ferry terminal ticketing)
            counter_width = 2.0   # Per station width
            counter_depth = 0.8   # Standard service counter depth
            counter_height = 1.1  # ADA compliant height

            # Row of counters near south entrance (departure area)
            num_counters = 8
            counter_spacing = 2.5  # 2.5m between stations
            start_x = slab_cx - (num_counters - 1) * counter_spacing / 2

            for i in range(num_counters):
                counter_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': counter_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcFurniture',
                    'floor': 'GF',
                    'center_x': start_x + i * counter_spacing,
                    'center_y': min_y + 15,
                    'center_z': 0.0,
                    'rotation_z': 0,
                    'length': counter_width,
                    'layer': f'TICKET_COUNTER_{i+1}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'furniture_config': {
                        'width': counter_width,
                        'depth': counter_depth,
                        'height': counter_height
                    }
                })

            print(f"  Generated {num_counters} ticketing counters")

        # Generate drinking fountains (transit amenity - near restrooms)
        if gen_options.get('generate_restrooms', True) and structural_elements:
            print("\nGenerating drinking fountains...")

            fountain_width = 0.8   # Scaled up for visibility
            fountain_depth = 0.6
            fountain_height = 1.0  # Accessible height

            floors_config = building_config.get('floors', {})
            fountain_count = 0

            for floor_id, floor_data in floors_config.items():
                if floor_id == 'ROOF':
                    continue

                elevation = floor_data.get('elevation_m', 0.0)

                # One fountain pair per floor (near NW and SE restrooms)
                fountain_positions = [
                    {'pos': (min_x + 10, max_y - 15), 'name': f'Fountain_NW_{floor_id}'},
                    {'pos': (max_x - 10, min_y + 15), 'name': f'Fountain_SE_{floor_id}'},
                ]

                for ftn in fountain_positions:
                    ftn_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    all_elements.append({
                        'guid': ftn_guid,
                        'discipline': 'ARC',
                        'ifc_class': 'IfcFurniture',
                        'floor': floor_id,
                        'center_x': ftn['pos'][0],
                        'center_y': ftn['pos'][1],
                        'center_z': elevation,
                        'rotation_z': 0,
                        'length': fountain_width,
                        'layer': f'FOUNTAIN_{ftn["name"]}',
                        'source_file': 'building_config.json',
                        'polyline_points': None,
                        'furniture_config': {
                            'width': fountain_width,
                            'depth': fountain_depth,
                            'height': fountain_height
                        }
                    })
                    fountain_count += 1

            print(f"  Generated {fountain_count} drinking fountains")

        # Generate trash/recycling bins (near seating and food areas)
        if gen_options.get('generate_restrooms', True) and structural_elements:
            print("\nGenerating waste bins...")

            bin_width = 0.8   # Scaled up for visibility
            bin_depth = 0.8
            bin_height = 1.2

            floors_config = building_config.get('floors', {})
            bin_count = 0

            for floor_id, floor_data in floors_config.items():
                if floor_id == 'ROOF':
                    continue

                elevation = floor_data.get('elevation_m', 0.0)

                # Bins at strategic locations (4 per floor)
                bin_positions = [
                    {'pos': (slab_cx - 15, slab_cy + 5), 'name': f'Bin_NW_{floor_id}'},
                    {'pos': (slab_cx + 15, slab_cy + 5), 'name': f'Bin_NE_{floor_id}'},
                    {'pos': (slab_cx - 15, slab_cy - 5), 'name': f'Bin_SW_{floor_id}'},
                    {'pos': (slab_cx + 15, slab_cy - 5), 'name': f'Bin_SE_{floor_id}'},
                ]

                for bin_loc in bin_positions:
                    bin_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    all_elements.append({
                        'guid': bin_guid,
                        'discipline': 'ARC',
                        'ifc_class': 'IfcFurniture',
                        'floor': floor_id,
                        'center_x': bin_loc['pos'][0],
                        'center_y': bin_loc['pos'][1],
                        'center_z': elevation,
                        'rotation_z': 0,
                        'length': bin_width,
                        'layer': f'WASTE_{bin_loc["name"]}',
                        'source_file': 'building_config.json',
                        'polyline_points': None,
                        'furniture_config': {
                            'width': bin_width,
                            'depth': bin_depth,
                            'height': bin_height
                        }
                    })
                    bin_count += 1

            print(f"  Generated {bin_count} waste bins")

        # Generate seating areas (waiting lounges)
        if gen_options.get('generate_seating', True) and structural_elements:
            print("\nGenerating seating areas...")

            seat_row_width = 10.0
            seat_row_depth = 1.0
            seat_height = 0.5

            floors_config = building_config.get('floors', {})
            seating_count = 0

            for floor_id, floor_data in floors_config.items():
                if floor_id in ['ROOF', '4F-6F']:  # Skip roof and upper mechanical floors
                    continue

                elevation = floor_data.get('elevation_m', 0.0)

                # 2 seating rows per floor (east and west sides of central area)
                seating_positions = [
                    {'pos': (slab_cx - 12, slab_cy), 'name': f'Seating_W_{floor_id}'},
                    {'pos': (slab_cx + 12, slab_cy), 'name': f'Seating_E_{floor_id}'},
                ]

                for seat in seating_positions:
                    # Multiple rows of seats
                    for row in range(3):
                        seat_guid = str(uuid.uuid4()).replace('-', '')[:22]
                        all_elements.append({
                            'guid': seat_guid,
                            'discipline': 'ARC',
                            'ifc_class': 'IfcFurniture',
                            'floor': floor_id,
                            'center_x': seat['pos'][0],
                            'center_y': seat['pos'][1] + row * 2,
                            'center_z': elevation,
                            'rotation_z': 0,
                            'length': seat_row_width,
                            'layer': f'SEATING_{seat["name"]}_R{row}',
                            'source_file': 'building_config.json',
                            'polyline_points': None,
                            'furniture_config': {
                                'width': seat_row_width,
                                'depth': seat_row_depth,
                                'height': seat_height
                            }
                        })
                        seating_count += 1

            print(f"  Generated {seating_count} seating rows")

        # Generate retail/F&B spaces (kiosks)
        if gen_options.get('generate_retail', True) and structural_elements:
            print("\nGenerating retail kiosks...")

            kiosk_width = 4.0
            kiosk_depth = 3.0
            kiosk_height = 3.0

            # Kiosks along main circulation corridor (1F only for now)
            kiosk_positions = [
                {'pos': (slab_cx - 15, slab_cy + 10), 'name': 'Retail_1'},
                {'pos': (slab_cx + 15, slab_cy + 10), 'name': 'Retail_2'},
                {'pos': (slab_cx - 15, slab_cy - 10), 'name': 'FnB_1'},
                {'pos': (slab_cx + 15, slab_cy - 10), 'name': 'FnB_2'},
            ]

            for kiosk in kiosk_positions:
                kiosk_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': kiosk_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcSpace',
                    'floor': '1F',
                    'center_x': kiosk['pos'][0],
                    'center_y': kiosk['pos'][1],
                    'center_z': 0.0,
                    'rotation_z': 0,
                    'length': kiosk_width,
                    'layer': f'KIOSK_{kiosk["name"]}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'space_config': {
                        'width': kiosk_width,
                        'depth': kiosk_depth,
                        'height': kiosk_height
                    }
                })

            print(f"  Generated {len(kiosk_positions)} retail/F&B kiosks")

        # Generate luggage cart corrals (GF only - transit hub amenity)
        if gen_options.get('generate_retail', True) and structural_elements:
            print("\nGenerating luggage cart areas...")

            cart_area_width = 3.0
            cart_area_depth = 2.0
            cart_area_height = 1.2  # Low rail enclosure

            # Cart corrals near entrances
            cart_positions = [
                {'pos': (min_x + 8, slab_cy - 5), 'name': 'CartCorral_W'},
                {'pos': (max_x - 8, slab_cy - 5), 'name': 'CartCorral_E'},
            ]

            for cart in cart_positions:
                cart_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': cart_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcFurniture',
                    'floor': 'GF',
                    'center_x': cart['pos'][0],
                    'center_y': cart['pos'][1],
                    'center_z': 0.0,
                    'rotation_z': 0,
                    'length': cart_area_width,
                    'layer': f'CART_{cart["name"]}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'furniture_config': {
                        'width': cart_area_width,
                        'depth': cart_area_depth,
                        'height': cart_area_height
                    }
                })

            print(f"  Generated {len(cart_positions)} luggage cart areas")

        # Generate information kiosks and departure boards (wayfinding)
        if gen_options.get('generate_retail', True) and structural_elements:
            print("\nGenerating information displays...")

            # Information kiosks - freestanding touch screens
            info_kiosk_width = 1.2   # Scaled up for visibility
            info_kiosk_depth = 0.8
            info_kiosk_height = 2.0

            # Departure boards - wall-mounted displays
            board_width = 3.0
            board_depth = 0.15
            board_height = 1.5

            floors_config = building_config.get('floors', {})
            info_count = 0

            for floor_id, floor_data in floors_config.items():
                if floor_id == 'ROOF':
                    continue

                elevation = floor_data.get('elevation_m', 0.0)

                # Information kiosks at main circulation points
                info_positions = [
                    {'pos': (slab_cx, slab_cy), 'name': f'InfoKiosk_Central_{floor_id}'},
                    {'pos': (slab_cx - 12, slab_cy), 'name': f'InfoKiosk_W_{floor_id}'},
                    {'pos': (slab_cx + 12, slab_cy), 'name': f'InfoKiosk_E_{floor_id}'},
                ]

                for info in info_positions:
                    info_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    all_elements.append({
                        'guid': info_guid,
                        'discipline': 'ARC',
                        'ifc_class': 'IfcFurniture',
                        'floor': floor_id,
                        'center_x': info['pos'][0],
                        'center_y': info['pos'][1],
                        'center_z': elevation,
                        'rotation_z': 0,
                        'length': info_kiosk_width,
                        'layer': f'INFO_{info["name"]}',
                        'source_file': 'building_config.json',
                        'polyline_points': None,
                        'furniture_config': {
                            'width': info_kiosk_width,
                            'depth': info_kiosk_depth,
                            'height': info_kiosk_height
                        }
                    })
                    info_count += 1

            # Departure boards (GF near ticketing area)
            board_positions = [
                {'pos': (slab_cx - 8, min_y + 20), 'name': 'Departures_W'},
                {'pos': (slab_cx + 8, min_y + 20), 'name': 'Departures_E'},
            ]

            for board in board_positions:
                board_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': board_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcFurniture',
                    'floor': 'GF',
                    'center_x': board['pos'][0],
                    'center_y': board['pos'][1],
                    'center_z': 2.5,  # Wall-mounted height
                    'rotation_z': 0,
                    'length': board_width,
                    'layer': f'DISPLAY_{board["name"]}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'furniture_config': {
                        'width': board_width,
                        'depth': board_depth,
                        'height': board_height
                    }
                })
                info_count += 1

            print(f"  Generated {info_count} information displays")

        # Generate ATM/service kiosks (GF only)
        if gen_options.get('generate_retail', True) and structural_elements:
            print("\nGenerating ATM kiosks...")

            atm_width = 1.0   # Scaled up for visibility
            atm_depth = 1.0
            atm_height = 2.0

            # ATMs along west wall near entrance
            atm_positions = [
                {'pos': (min_x + 3, slab_cy - 5), 'name': 'ATM_1'},
                {'pos': (min_x + 3, slab_cy), 'name': 'ATM_2'},
                {'pos': (min_x + 3, slab_cy + 5), 'name': 'ATM_3'},
            ]

            for atm in atm_positions:
                atm_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': atm_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcFurniture',
                    'floor': 'GF',
                    'center_x': atm['pos'][0],
                    'center_y': atm['pos'][1],
                    'center_z': 0.0,
                    'rotation_z': math.pi / 2,  # Facing into building
                    'length': atm_depth,
                    'layer': f'ATM_{atm["name"]}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'furniture_config': {
                        'width': atm_width,
                        'depth': atm_depth,
                        'height': atm_height
                    }
                })

            print(f"  Generated {len(atm_positions)} ATM kiosks")

        # Generate planters (interior landscaping)
        if gen_options.get('generate_seating', True) and structural_elements:
            print("\nGenerating planters...")

            planter_size = 1.2
            planter_height = 0.8

            floors_config = building_config.get('floors', {})
            planter_count = 0

            for floor_id, floor_data in floors_config.items():
                if floor_id in ['ROOF', '4F-6F']:
                    continue

                elevation = floor_data.get('elevation_m', 0.0)

                # Planters along main circulation
                planter_positions = [
                    {'pos': (slab_cx - 8, slab_cy + 8), 'name': f'Planter_NW_{floor_id}'},
                    {'pos': (slab_cx + 8, slab_cy + 8), 'name': f'Planter_NE_{floor_id}'},
                ]

                for pl in planter_positions:
                    pl_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    all_elements.append({
                        'guid': pl_guid,
                        'discipline': 'ARC',
                        'ifc_class': 'IfcFurniture',
                        'floor': floor_id,
                        'center_x': pl['pos'][0],
                        'center_y': pl['pos'][1],
                        'center_z': elevation,
                        'rotation_z': 0,
                        'length': planter_size,
                        'layer': f'PLANTER_{pl["name"]}',
                        'source_file': 'building_config.json',
                        'polyline_points': None,
                        'furniture_config': {
                            'width': planter_size,
                            'depth': planter_size,
                            'height': planter_height
                        }
                    })
                    planter_count += 1

            print(f"  Generated {planter_count} planters")

        # Generate first aid station (GF - safety requirement)
        if gen_options.get('generate_restrooms', True) and structural_elements:
            print("\nGenerating first aid station...")

            aid_width = 3.0
            aid_depth = 2.5
            aid_height = 3.0

            # Near central restrooms for accessibility
            aid_guid = str(uuid.uuid4()).replace('-', '')[:22]
            all_elements.append({
                'guid': aid_guid,
                'discipline': 'ARC',
                'ifc_class': 'IfcSpace',
                'floor': 'GF',
                'center_x': max_x - 10,
                'center_y': slab_cy,
                'center_z': 0.0,
                'rotation_z': 0,
                'length': aid_width,
                'layer': 'FIRST_AID_STATION',
                'source_file': 'building_config.json',
                'polyline_points': None,
                'space_config': {
                    'width': aid_width,
                    'depth': aid_depth,
                    'height': aid_height,
                    'space_type': 'First Aid'
                }
            })

            print(f"  Generated 1 first aid station")

        # Generate baggage claim carousel (GF - arrival facility)
        if gen_options.get('generate_counters', True) and structural_elements:
            print("\nGenerating baggage claim area...")

            # Carousel dimensions (oval conveyor belt)
            carousel_width = 12.0
            carousel_depth = 4.0
            carousel_height = 0.8

            # Two carousels for arrival hall
            carousel_positions = [
                {'pos': (slab_cx - 8, max_y - 15), 'name': 'Carousel_1'},
                {'pos': (slab_cx + 8, max_y - 15), 'name': 'Carousel_2'},
            ]

            for carousel in carousel_positions:
                carousel_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': carousel_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcFurniture',
                    'floor': 'GF',
                    'center_x': carousel['pos'][0],
                    'center_y': carousel['pos'][1],
                    'center_z': 0.0,
                    'rotation_z': 0,
                    'length': carousel_width,
                    'layer': f'BAGGAGE_{carousel["name"]}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'furniture_config': {
                        'width': carousel_width,
                        'depth': carousel_depth,
                        'height': carousel_height
                    }
                })

            print(f"  Generated {len(carousel_positions)} baggage carousels")

        # Generate boarding gates (GF - departure points)
        if gen_options.get('generate_counters', True) and structural_elements:
            print("\nGenerating boarding gates...")

            # Gate counter/desk
            gate_width = 3.0
            gate_depth = 1.5
            gate_height = 1.1

            # Gates along north wall (jetty side)
            num_gates = 4
            gate_spacing = 8.0
            start_x = slab_cx - (num_gates - 1) * gate_spacing / 2

            for i in range(num_gates):
                gate_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': gate_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcFurniture',
                    'floor': 'GF',
                    'center_x': start_x + i * gate_spacing,
                    'center_y': max_y - 8,  # Near north exit to jetty
                    'center_z': 0.0,
                    'rotation_z': 0,
                    'length': gate_width,
                    'layer': f'GATE_{i+1}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'furniture_config': {
                        'width': gate_width,
                        'depth': gate_depth,
                        'height': gate_height
                    }
                })

            print(f"  Generated {num_gates} boarding gates")

        # Generate customs/immigration checkpoint (GF - international terminal)
        if gen_options.get('generate_counters', True) and structural_elements:
            print("\nGenerating customs checkpoint...")

            # Immigration booth
            booth_width = 2.0
            booth_depth = 2.0
            booth_height = 2.5

            # Booths in row for passport control
            num_booths = 6
            booth_spacing = 3.0
            start_x = slab_cx - (num_booths - 1) * booth_spacing / 2

            for i in range(num_booths):
                booth_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': booth_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcSpace',
                    'floor': 'GF',
                    'center_x': start_x + i * booth_spacing,
                    'center_y': max_y - 20,  # After security, before gates
                    'center_z': 0.0,
                    'rotation_z': 0,
                    'length': booth_width,
                    'layer': f'IMMIGRATION_BOOTH_{i+1}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'space_config': {
                        'width': booth_width,
                        'depth': booth_depth,
                        'height': booth_height,
                        'space_type': 'Immigration'
                    }
                })

            print(f"  Generated {num_booths} immigration booths")

        # Generate glass partition walls in public areas
        if gen_options.get('generate_glass_partitions', True) and structural_elements:
            print("\nGenerating glass partition walls...")

            glass_thickness = 0.012  # 12mm tempered glass
            glass_height = 2.4  # Partial height partitions
            glass_panel_width = 1.5  # Standard glass panel width

            # Glass material with transparency
            glass_rgba = [0.3, 0.5, 0.8, 0.3]  # Semi-transparent blue-tinted

            floors_config = building_config.get('floors', {})
            partition_count = 0

            for floor_id, floor_data in floors_config.items():
                if floor_id == 'ROOF':
                    continue

                elevation = floor_data.get('elevation_m', 0.0)

                # ================================================================
                # 1. Waiting lounge enclosures (around seating areas)
                # ================================================================
                # East and West waiting lounges - create L-shaped partitions
                lounge_positions = [
                    # West lounge - L-shape facing center
                    {
                        'walls': [
                            {'start': (slab_cx - 18, slab_cy - 4), 'end': (slab_cx - 18, slab_cy + 4)},  # West edge
                            {'start': (slab_cx - 18, slab_cy + 4), 'end': (slab_cx - 7, slab_cy + 4)},   # North edge
                        ],
                        'name': f'Lounge_W_{floor_id}'
                    },
                    # East lounge - L-shape facing center
                    {
                        'walls': [
                            {'start': (slab_cx + 18, slab_cy - 4), 'end': (slab_cx + 18, slab_cy + 4)},  # East edge
                            {'start': (slab_cx + 7, slab_cy + 4), 'end': (slab_cx + 18, slab_cy + 4)},   # North edge
                        ],
                        'name': f'Lounge_E_{floor_id}'
                    },
                ]

                for lounge in lounge_positions:
                    for i, wall in enumerate(lounge['walls']):
                        start = wall['start']
                        end = wall['end']

                        # Calculate wall properties
                        dx = end[0] - start[0]
                        dy = end[1] - start[1]
                        length = math.sqrt(dx*dx + dy*dy)
                        cx = (start[0] + end[0]) / 2
                        cy = (start[1] + end[1]) / 2
                        rotation = math.atan2(dy, dx)

                        # Generate individual glass panels along the wall
                        num_panels = max(1, int(length / glass_panel_width))
                        panel_length = length / num_panels

                        for p in range(num_panels):
                            # Calculate panel center position along wall
                            t = (p + 0.5) / num_panels
                            panel_cx = start[0] + dx * t
                            panel_cy = start[1] + dy * t

                            partition_guid = str(uuid.uuid4()).replace('-', '')[:22]
                            all_elements.append({
                                'guid': partition_guid,
                                'discipline': 'ARC',
                                'ifc_class': 'IfcWall',
                                'floor': floor_id,
                                'center_x': panel_cx,
                                'center_y': panel_cy,
                                'center_z': elevation,
                                'rotation_z': rotation,
                                'length': panel_length,
                                'layer': f'GLASS_PARTITION_{lounge["name"]}_{i}',
                                'source_file': 'building_config.json',
                                'polyline_points': None,
                                'glass_partition_config': {
                                    'thickness': glass_thickness,
                                    'height': glass_height,
                                    'length': panel_length,
                                    'material_rgba': glass_rgba
                                }
                            })
                            partition_count += 1

                # ================================================================
                # 2. Check-in counter area dividers (GF only)
                # ================================================================
                if floor_id == 'GF':
                    # Glass queue barriers between counter stations
                    num_dividers = 5  # Between 6 counters
                    counter_spacing = 3.0
                    start_x = slab_cx - (num_dividers) * counter_spacing / 2
                    divider_length = 4.0
                    divider_y = min_y + 15

                    for i in range(num_dividers):
                        divider_x = start_x + i * counter_spacing + counter_spacing / 2

                        partition_guid = str(uuid.uuid4()).replace('-', '')[:22]
                        all_elements.append({
                            'guid': partition_guid,
                            'discipline': 'ARC',
                            'ifc_class': 'IfcWall',
                            'floor': floor_id,
                            'center_x': divider_x,
                            'center_y': divider_y - divider_length / 2,
                            'center_z': elevation,
                            'rotation_z': math.pi / 2,  # Perpendicular to counters
                            'length': divider_length,
                            'layer': f'GLASS_QUEUE_DIVIDER_{i}',
                            'source_file': 'building_config.json',
                            'polyline_points': None,
                            'glass_partition_config': {
                                'thickness': glass_thickness,
                                'height': 1.2,  # Lower height for queue barriers
                                'length': divider_length,
                                'material_rgba': glass_rgba
                            }
                        })
                        partition_count += 1

                # ================================================================
                # 3. Retail zone enclosures (around kiosks)
                # ================================================================
                if floor_id == '1F':
                    # Glass fronts for retail kiosks
                    kiosk_centers = [
                        (slab_cx - 15, slab_cy + 10),  # Retail_1
                        (slab_cx + 15, slab_cy + 10),  # Retail_2
                        (slab_cx - 15, slab_cy - 10),  # FnB_1
                        (slab_cx + 15, slab_cy - 10),  # FnB_2
                    ]

                    kiosk_width = 4.0
                    kiosk_depth = 3.0

                    for idx, (kx, ky) in enumerate(kiosk_centers):
                        # Front glass wall for each kiosk (facing center)
                        if ky > slab_cy:
                            # North kiosks - front faces south
                            front_y = ky - kiosk_depth / 2
                            rotation = 0
                        else:
                            # South kiosks - front faces north
                            front_y = ky + kiosk_depth / 2
                            rotation = math.pi

                        partition_guid = str(uuid.uuid4()).replace('-', '')[:22]
                        all_elements.append({
                            'guid': partition_guid,
                            'discipline': 'ARC',
                            'ifc_class': 'IfcWall',
                            'floor': floor_id,
                            'center_x': kx,
                            'center_y': front_y,
                            'center_z': elevation,
                            'rotation_z': rotation,
                            'length': kiosk_width,
                            'layer': f'GLASS_KIOSK_FRONT_{idx}',
                            'source_file': 'building_config.json',
                            'polyline_points': None,
                            'glass_partition_config': {
                                'thickness': glass_thickness,
                                'height': glass_height,
                                'length': kiosk_width,
                                'material_rgba': glass_rgba
                            }
                        })
                        partition_count += 1

            print(f"  Generated {partition_count} glass partition wall panels")

        # Generate automated entrance doors (sliding/revolving)
        if gen_options.get('generate_entrance_doors', True) and structural_elements:
            print("\nGenerating automated entrance doors...")

            auto_door_count = 0

            # Main entrances get automatic sliding doors
            auto_door_positions = [
                {'pos': (slab_cx, min_y + 0.5), 'name': 'South_AutoDoor', 'type': 'sliding', 'rotation': 0},
                {'pos': (slab_cx, max_y - 0.5), 'name': 'North_AutoDoor', 'type': 'sliding', 'rotation': 0},
                {'pos': (min_x + 0.5, slab_cy), 'name': 'West_AutoDoor', 'type': 'revolving', 'rotation': math.pi/2},
                {'pos': (max_x - 0.5, slab_cy), 'name': 'East_AutoDoor', 'type': 'revolving', 'rotation': math.pi/2},
            ]

            for auto_door in auto_door_positions:
                # Door frame/housing
                door_guid = str(uuid.uuid4()).replace('-', '')[:22]

                # Sliding doors are wider, revolving are square
                if auto_door['type'] == 'sliding':
                    door_width = 4.0  # Wide sliding glass doors
                    door_depth = 0.3
                else:  # revolving
                    door_width = 2.5  # Revolving door diameter
                    door_depth = 2.5

                all_elements.append({
                    'guid': door_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcDoor',
                    'floor': 'GF',
                    'center_x': auto_door['pos'][0],
                    'center_y': auto_door['pos'][1],
                    'center_z': 0.0,
                    'rotation_z': auto_door['rotation'],
                    'length': door_width,
                    'layer': f'AUTO_DOOR_{auto_door["name"]}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'door_config': {
                        'width': door_width,
                        'depth': door_depth,
                        'height': 2.8,
                        'door_type': auto_door['type']
                    }
                })
                auto_door_count += 1

            print(f"  Generated {auto_door_count} automated entrance doors")

        # Generate ceiling fans for waiting areas
        if gen_options.get('generate_counters', True) and structural_elements:
            print("\nGenerating ceiling fans...")

            fan_count = 0
            fan_diameter = 1.2
            fan_height = 0.3

            floors_config = building_config.get('floors', {})

            for floor_id, floor_data in floors_config.items():
                if floor_id == 'ROOF':
                    continue

                elevation = floor_data.get('elevation_m', 0.0)
                ceiling_z = floor_data.get('ceiling_m', elevation + 4.0)

                # Fans in waiting areas (east and west lounges)
                fan_positions = [
                    # West waiting lounge (3 fans in row)
                    (slab_cx - 15, slab_cy - 3),
                    (slab_cx - 15, slab_cy),
                    (slab_cx - 15, slab_cy + 3),
                    # East waiting lounge (3 fans in row)
                    (slab_cx + 15, slab_cy - 3),
                    (slab_cx + 15, slab_cy),
                    (slab_cx + 15, slab_cy + 3),
                ]

                for i, pos in enumerate(fan_positions):
                    fan_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    all_elements.append({
                        'guid': fan_guid,
                        'discipline': 'ELEC',
                        'ifc_class': 'IfcFurniture',
                        'floor': floor_id,
                        'center_x': pos[0],
                        'center_y': pos[1],
                        'center_z': ceiling_z - fan_height,  # Hang from ceiling
                        'rotation_z': 0,
                        'length': fan_diameter,
                        'layer': f'CEILING_FAN_{floor_id}_{i+1}',
                        'source_file': 'building_config.json',
                        'polyline_points': None,
                        'furniture_config': {
                            'width': fan_diameter,
                            'depth': fan_diameter,
                            'height': fan_height
                        }
                    })
                    fan_count += 1

            print(f"  Generated {fan_count} ceiling fans")

        # Generate canteen/F&B space with seating (1F)
        if gen_options.get('generate_kiosks', True) and structural_elements:
            print("\nGenerating canteen area...")

            # Canteen location on 1F (northeast corner)
            canteen_cx = slab_cx + 12
            canteen_cy = max_y - 18
            canteen_z = 4.0  # 1F elevation

            canteen_count = 0

            # Canteen space enclosure
            canteen_guid = str(uuid.uuid4()).replace('-', '')[:22]
            all_elements.append({
                'guid': canteen_guid,
                'discipline': 'ARC',
                'ifc_class': 'IfcSpace',
                'floor': '1F',
                'center_x': canteen_cx,
                'center_y': canteen_cy,
                'center_z': canteen_z,
                'rotation_z': 0,
                'length': 10.0,
                'layer': 'CANTEEN_SPACE',
                'source_file': 'building_config.json',
                'polyline_points': None,
                'space_config': {
                    'width': 10.0,
                    'depth': 8.0,
                    'height': 3.5,
                    'space_type': 'Canteen'
                }
            })
            canteen_count += 1

            # Food service counter
            counter_guid = str(uuid.uuid4()).replace('-', '')[:22]
            all_elements.append({
                'guid': counter_guid,
                'discipline': 'ARC',
                'ifc_class': 'IfcFurniture',
                'floor': '1F',
                'center_x': canteen_cx,
                'center_y': canteen_cy + 2,  # North side for service
                'center_z': canteen_z,
                'rotation_z': 0,
                'length': 6.0,
                'layer': 'CANTEEN_COUNTER',
                'source_file': 'building_config.json',
                'polyline_points': None,
                'furniture_config': {
                    'width': 6.0,
                    'depth': 0.8,
                    'height': 1.1
                }
            })
            canteen_count += 1

            # Dining tables with seating (4 tables)
            table_positions = [
                (canteen_cx - 3, canteen_cy - 2),
                (canteen_cx + 3, canteen_cy - 2),
                (canteen_cx - 3, canteen_cy),
                (canteen_cx + 3, canteen_cy),
            ]

            for i, pos in enumerate(table_positions):
                # Table
                table_guid = str(uuid.uuid4()).replace('-', '')[:22]
                all_elements.append({
                    'guid': table_guid,
                    'discipline': 'ARC',
                    'ifc_class': 'IfcFurniture',
                    'floor': '1F',
                    'center_x': pos[0],
                    'center_y': pos[1],
                    'center_z': canteen_z,
                    'rotation_z': 0,
                    'length': 1.2,
                    'layer': f'CANTEEN_TABLE_{i+1}',
                    'source_file': 'building_config.json',
                    'polyline_points': None,
                    'furniture_config': {
                        'width': 1.2,
                        'depth': 0.8,
                        'height': 0.75
                    }
                })
                canteen_count += 1

                # Chairs around table (4 per table)
                chair_offsets = [
                    (-0.6, 0), (0.6, 0),  # Left and right
                    (0, -0.5), (0, 0.5),  # Front and back
                ]
                for j, offset in enumerate(chair_offsets):
                    chair_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    all_elements.append({
                        'guid': chair_guid,
                        'discipline': 'ARC',
                        'ifc_class': 'IfcFurniture',
                        'floor': '1F',
                        'center_x': pos[0] + offset[0],
                        'center_y': pos[1] + offset[1],
                        'center_z': canteen_z,
                        'rotation_z': 0,
                        'length': 0.45,
                        'layer': f'CANTEEN_CHAIR_{i+1}_{j+1}',
                        'source_file': 'building_config.json',
                        'polyline_points': None,
                        'furniture_config': {
                            'width': 0.45,
                            'depth': 0.45,
                            'height': 0.85
                        }
                    })
                    canteen_count += 1

            print(f"  Generated canteen area with {canteen_count} elements")

        # Generate conduits for MEP routing (placeholder for future disciplines)
        if gen_options.get('generate_conduits', False):
            print("\nGenerating MEP conduits (placeholder)...")
            # Future: Add vertical and horizontal conduit runs for MEP routing
            # - Vertical risers at core locations
            # - Horizontal runs along corridors
            # - Connection points at floor levels

        # ====================================================================
        # MEP GENERATION (FP, ELEC, ACMV) - Using modular generator classes
        # ====================================================================
        generate_mep = (gen_options.get('generate_fire_protection', False) or
                       gen_options.get('generate_electrical', False))

        if generate_mep and structural_elements:
            print("\nGenerating MEP elements (FP, ELEC)...")

            # Check if zones_config exists, create default if not
            script_dir = Path(__file__).parent
            zones_config_path = script_dir / 'zones_config.json'
            if not zones_config_path.exists():
                # Create minimal zones config
                default_zones = {
                    "_comment": "Zone configuration for Mini Bonsai GUI",
                    "_gui_editable": True,
                    "vertical_stratification": {
                        "FP_sprinkler": -0.3,
                        "FP_pipe_main": -0.5,
                        "FP_pipe_branch": -0.45,
                        "ELEC_light": -0.55,
                        "ELEC_conduit_main": -0.7,
                        "ELEC_conduit_branch": -0.65
                    },
                    "discipline_clearances": {
                        "FP_to_ELEC": 0.3,
                        "FP_to_ACMV": 0.5,
                        "ELEC_to_ACMV": 0.3
                    },
                    "toilet_zones": [],
                    "ac_equipment": [],
                    "fire_equipment": []
                }
                with open(zones_config_path, 'w') as f:
                    json.dump(default_zones, f, indent=2)

            # Use MEP generator orchestrator
            mep_orchestrator = MEPGeneratorOrchestrator(
                str(zones_config_path),
                str(script_dir.parent / 'building_config.json')
            )

            mep_elements = mep_orchestrator.generate_all(structural_elements)
            all_elements.extend(mep_elements)

            print(f"  Total MEP elements: {len(mep_elements)}")

        # Legacy inline generation (kept for reference, disabled)
        if False and gen_options.get('generate_fire_protection', False) and structural_elements:
            print("\nGenerating Fire Protection elements...")

            mep_config = building_config.get('mep_config', {})
            fp_config = mep_config.get('fire_protection', {})
            sprinkler_config = fp_config.get('sprinkler', {})
            pipe_config = fp_config.get('pipe', {})

            spacing = sprinkler_config.get('spacing_m', 3.5)
            z_offset = sprinkler_config.get('z_offset_from_ceiling_m', -0.3)

            floors_config = building_config.get('floors', {})
            sprinkler_count = 0
            pipe_count = 0

            # Calculate usable area (avoiding restroom corners)
            margin = 10.0  # Stay away from corners where restrooms are

            for floor_id, floor_data in floors_config.items():
                if floor_id == 'ROOF':
                    continue

                elevation = floor_data.get('elevation_m', 0.0)
                floor_height = floor_data.get('floor_to_floor_m', 4.0)
                ceiling_z = elevation + floor_height + z_offset

                # Grid of sprinklers with margin from edges
                usable_min_x = min_x + margin
                usable_max_x = max_x - margin
                usable_min_y = min_y + margin
                usable_max_y = max_y - margin

                # Generate sprinkler grid
                y = usable_min_y
                row_heads = []
                while y <= usable_max_y:
                    x = usable_min_x
                    row = []
                    while x <= usable_max_x:
                        sprinkler_guid = str(uuid.uuid4()).replace('-', '')[:22]
                        all_elements.append({
                            'guid': sprinkler_guid,
                            'discipline': 'FP',
                            'ifc_class': 'IfcFireSuppressionTerminal',
                            'floor': floor_id,
                            'center_x': x,
                            'center_y': y,
                            'center_z': ceiling_z,
                            'rotation_z': 0,
                            'length': 0.05,
                            'layer': f'SPRINKLER_{floor_id}',
                            'source_file': 'building_config.json',
                            'polyline_points': None,
                            'sprinkler_config': {
                                'head_radius': sprinkler_config.get('head_radius_m', 0.025),
                                'head_length': sprinkler_config.get('head_length_m', 0.08)
                            }
                        })
                        row.append((x, y))
                        sprinkler_count += 1
                        x += spacing
                    row_heads.append(row)
                    y += spacing

                # Generate pipe network connecting sprinklers
                pipe_z = elevation + floor_height + pipe_config.get('z_offset_from_ceiling_m', -0.5)

                # Main pipe runs along Y axis (center of building)
                main_x = slab_cx
                if row_heads:
                    # Main vertical run
                    main_length = usable_max_y - usable_min_y
                    main_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    all_elements.append({
                        'guid': main_guid,
                        'discipline': 'FP',
                        'ifc_class': 'IfcPipeSegment',
                        'floor': floor_id,
                        'center_x': main_x,
                        'center_y': slab_cy,
                        'center_z': pipe_z,
                        'rotation_z': math.pi/2,  # Along Y axis
                        'length': main_length,
                        'layer': f'FP_MAIN_{floor_id}',
                        'source_file': 'building_config.json',
                        'polyline_points': None,
                        'pipe_config': {
                            'radius': pipe_config.get('main_radius_m', 0.05),
                            'length': main_length
                        }
                    })
                    pipe_count += 1

                    # Branch pipes for each row
                    for row in row_heads:
                        if len(row) > 0:
                            row_y = row[0][1]
                            branch_length = (usable_max_x - usable_min_x)
                            branch_guid = str(uuid.uuid4()).replace('-', '')[:22]
                            all_elements.append({
                                'guid': branch_guid,
                                'discipline': 'FP',
                                'ifc_class': 'IfcPipeSegment',
                                'floor': floor_id,
                                'center_x': slab_cx,
                                'center_y': row_y,
                                'center_z': pipe_z,
                                'rotation_z': 0,  # Along X axis
                                'length': branch_length,
                                'layer': f'FP_BRANCH_{floor_id}',
                                'source_file': 'building_config.json',
                                'polyline_points': None,
                                'pipe_config': {
                                    'radius': pipe_config.get('branch_radius_m', 0.025),
                                    'length': branch_length
                                }
                            })
                            pipe_count += 1

            print(f"  Generated {sprinkler_count} sprinklers + {pipe_count} pipe segments")

        # ====================================================================
        # ELECTRICAL (ELEC) - Light fixtures and conduits (LEGACY - disabled)
        # ====================================================================
        if False and gen_options.get('generate_electrical', False) and structural_elements:
            print("\nGenerating Electrical elements...")

            mep_config = building_config.get('mep_config', {})
            elec_config = mep_config.get('electrical', {})
            light_config = elec_config.get('light_fixture', {})
            conduit_config = elec_config.get('conduit', {})

            spacing = light_config.get('spacing_m', 4.0)
            z_offset = light_config.get('z_offset_from_ceiling_m', -0.5)

            floors_config = building_config.get('floors', {})
            light_count = 0
            conduit_count = 0

            # Calculate usable area (avoiding restroom corners)
            margin = 10.0

            for floor_id, floor_data in floors_config.items():
                if floor_id == 'ROOF':
                    continue

                elevation = floor_data.get('elevation_m', 0.0)
                floor_height = floor_data.get('floor_to_floor_m', 4.0)
                ceiling_z = elevation + floor_height + z_offset

                # Grid of light fixtures with margin from edges
                usable_min_x = min_x + margin
                usable_max_x = max_x - margin
                usable_min_y = min_y + margin
                usable_max_y = max_y - margin

                # Generate light fixture grid (offset from sprinklers to avoid clash)
                offset = spacing / 2  # Offset lights from sprinkler grid
                y = usable_min_y + offset
                row_lights = []
                while y <= usable_max_y:
                    x = usable_min_x + offset
                    row = []
                    while x <= usable_max_x:
                        light_guid = str(uuid.uuid4()).replace('-', '')[:22]
                        all_elements.append({
                            'guid': light_guid,
                            'discipline': 'ELEC',
                            'ifc_class': 'IfcLightFixture',
                            'floor': floor_id,
                            'center_x': x,
                            'center_y': y,
                            'center_z': ceiling_z,
                            'rotation_z': 0,
                            'length': light_config.get('width_m', 0.6),
                            'layer': f'LIGHT_{floor_id}',
                            'source_file': 'building_config.json',
                            'polyline_points': None,
                            'light_config': {
                                'width': light_config.get('width_m', 0.6),
                                'depth': light_config.get('depth_m', 0.6),
                                'thickness': light_config.get('thickness_m', 0.05)
                            }
                        })
                        row.append((x, y))
                        light_count += 1
                        x += spacing
                    row_lights.append(row)
                    y += spacing

                # Generate conduit network
                conduit_z = elevation + floor_height + conduit_config.get('z_offset_from_ceiling_m', -0.7)

                if row_lights:
                    # Main conduit run along Y axis
                    main_length = usable_max_y - usable_min_y
                    main_guid = str(uuid.uuid4()).replace('-', '')[:22]
                    all_elements.append({
                        'guid': main_guid,
                        'discipline': 'ELEC',
                        'ifc_class': 'IfcCableCarrierSegment',
                        'floor': floor_id,
                        'center_x': slab_cx + 2,  # Offset from FP main
                        'center_y': slab_cy,
                        'center_z': conduit_z,
                        'rotation_z': math.pi/2,  # Along Y axis
                        'length': main_length,
                        'layer': f'ELEC_MAIN_{floor_id}',
                        'source_file': 'building_config.json',
                        'polyline_points': None,
                        'conduit_config': {
                            'length': main_length,
                            'width': conduit_config.get('main_width_m', 0.15),
                            'height': conduit_config.get('main_height_m', 0.08)
                        }
                    })
                    conduit_count += 1

                    # Branch conduits for each row
                    for row in row_lights:
                        if len(row) > 0:
                            row_y = row[0][1]
                            branch_length = (usable_max_x - usable_min_x)
                            branch_guid = str(uuid.uuid4()).replace('-', '')[:22]
                            all_elements.append({
                                'guid': branch_guid,
                                'discipline': 'ELEC',
                                'ifc_class': 'IfcCableCarrierSegment',
                                'floor': floor_id,
                                'center_x': slab_cx,
                                'center_y': row_y,
                                'center_z': conduit_z,
                                'rotation_z': 0,  # Along X axis
                                'length': branch_length,
                                'layer': f'ELEC_BRANCH_{floor_id}',
                                'source_file': 'building_config.json',
                                'polyline_points': None,
                                'conduit_config': {
                                    'length': branch_length,
                                    'width': conduit_config.get('branch_width_m', 0.1),
                                    'height': conduit_config.get('branch_height_m', 0.05)
                                }
                            })
                            conduit_count += 1

            print(f"  Generated {light_count} light fixtures + {conduit_count} conduit segments")

    print(f"\nTotal elements (with interior fit-out): {len(all_elements)}")

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
