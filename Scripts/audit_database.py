#!/usr/bin/env python3
"""
Database Audit Engine
======================

Audits federation database and outputs human-readable text report
describing geometry, semantics, and metrics - without requiring Blender.

This tool replicates how blend_cache.py interprets the database,
ensuring WYSIWYG accuracy between audit report and Blender viewport.

Usage:
    python3 audit_database.py <database_path>
    python3 audit_database.py --help

Output Layers:
    1. Geometry - What Blender sees (dimensions, positions)
    2. Semantics - What objects mean (IFC class, discipline)
    3. Analytics - Space characteristics (patterns, relationships)
    4. Summary - Aggregate metrics (totals, areas, volumes)
    5. Shape Classification - Complexity (% box-like, cylindrical)
"""

import sys
import sqlite3
import struct
import math
import argparse
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from collections import Counter, defaultdict

# =============================================================================
# DECODE LAYER - Mirrors blend_cache.py exactly
# =============================================================================

def unpack_vertices(blob: bytes) -> List[Tuple[float, float, float]]:
    """
    Unpack vertices from database BLOB.
    Mirrors blend_cache.py unpack_vertices() exactly.
    """
    if not blob:
        return []
    count = len(blob) // 12  # 3 floats (xyz) = 12 bytes
    vertices = []
    for i in range(count):
        offset = i * 12
        x, y, z = struct.unpack('fff', blob[offset:offset+12])
        vertices.append((x, y, z))
    return vertices


def unpack_faces(blob: bytes) -> List[Tuple[int, int, int]]:
    """
    Unpack faces from database BLOB.
    Mirrors blend_cache.py unpack_faces() exactly.
    """
    if not blob:
        return []
    count = len(blob) // 12  # 3 ints (triangle) = 12 bytes
    faces = []
    for i in range(count):
        offset = i * 12
        v1, v2, v3 = struct.unpack('iii', blob[offset:offset+12])
        faces.append((v1, v2, v3))
    return faces


# =============================================================================
# GEOMETRY ANALYSIS
# =============================================================================

def compute_bbox(vertices: List[Tuple[float, float, float]]) -> Dict:
    """Compute bounding box from vertices."""
    if not vertices:
        return {'min': (0, 0, 0), 'max': (0, 0, 0), 'size': (0, 0, 0)}

    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]

    min_pt = (min(xs), min(ys), min(zs))
    max_pt = (max(xs), max(ys), max(zs))
    size = (max_pt[0] - min_pt[0], max_pt[1] - min_pt[1], max_pt[2] - min_pt[2])

    return {'min': min_pt, 'max': max_pt, 'size': size}


def classify_orientation(bbox: Dict) -> str:
    """Classify element orientation based on bounding box."""
    sx, sy, sz = bbox['size']

    if sz > sx and sz > sy:
        return 'vertical'
    elif sx > sy * 2:
        return 'E-W'
    elif sy > sx * 2:
        return 'N-S'
    else:
        return 'square'


def classify_shape(vertex_count: int, face_count: int) -> str:
    """Classify element shape based on mesh complexity."""
    if vertex_count == 8 and face_count == 12:
        return 'box'
    elif vertex_count == 26 and face_count >= 44:
        return 'cylinder'
    elif vertex_count <= 8:
        return 'simple'
    elif vertex_count <= 24:
        return 'extruded'
    else:
        return 'complex'


def detect_grid_pattern(positions: List[Tuple[float, float]]) -> Optional[Dict]:
    """Detect regular grid pattern in XY positions."""
    if len(positions) < 4:
        return None

    # Get unique X and Y coordinates
    xs = sorted(set(round(p[0], 1) for p in positions))
    ys = sorted(set(round(p[1], 1) for p in positions))

    if len(xs) < 2 or len(ys) < 2:
        return None

    # Calculate spacing
    x_spacing = [xs[i+1] - xs[i] for i in range(len(xs)-1)]
    y_spacing = [ys[i+1] - ys[i] for i in range(len(ys)-1)]

    # Check for regularity
    avg_x = sum(x_spacing) / len(x_spacing)
    avg_y = sum(y_spacing) / len(y_spacing)

    x_regular = all(abs(s - avg_x) < 0.5 for s in x_spacing)
    y_regular = all(abs(s - avg_y) < 0.5 for s in y_spacing)

    if x_regular and y_regular:
        return {
            'cols': len(xs),
            'rows': len(ys),
            'spacing_x': avg_x,
            'spacing_y': avg_y,
            'regular': True
        }

    return {'cols': len(xs), 'rows': len(ys), 'regular': False}


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(db_path: str) -> str:
    """Generate full audit report for database."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    report = []

    # Header
    report.append("=" * 70)
    report.append(f"DATABASE AUDIT REPORT")
    report.append(f"Source: {Path(db_path).name}")
    from datetime import datetime
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 70)
    report.append("")

    # Get all elements with geometry
    # Handle different schema versions

    # First check what columns exist in element_transforms
    cursor.execute("PRAGMA table_info(element_transforms)")
    et_columns = {row[1] for row in cursor.fetchall()}
    has_length = 'length' in et_columns

    # Check if element_geometry has vertex_count
    cursor.execute("PRAGMA table_info(element_geometry)")
    eg_info = cursor.fetchall()
    # element_geometry might be a view, check base_geometries
    cursor.execute("PRAGMA table_info(base_geometries)")
    bg_columns = {row[1] for row in cursor.fetchall()}
    has_vertex_count = 'vertex_count' in bg_columns

    # Build query based on available columns
    if has_vertex_count and has_length:
        cursor.execute("""
            SELECT em.guid, em.ifc_class, em.discipline, em.storey,
                   eg.vertices, bg.vertex_count, bg.face_count,
                   et.center_x, et.center_y, et.center_z, et.length
            FROM elements_meta em
            JOIN element_geometry eg ON em.guid = eg.guid
            JOIN base_geometries bg ON eg.geometry_hash = bg.geometry_hash
            JOIN element_transforms et ON em.guid = et.guid
        """)
        elements = cursor.fetchall()
    elif has_vertex_count:
        cursor.execute("""
            SELECT em.guid, em.ifc_class, em.discipline, em.storey,
                   eg.vertices, bg.vertex_count, bg.face_count,
                   et.center_x, et.center_y, et.center_z
            FROM elements_meta em
            JOIN element_geometry eg ON em.guid = eg.guid
            JOIN base_geometries bg ON eg.geometry_hash = bg.geometry_hash
            JOIN element_transforms et ON em.guid = et.guid
        """)
        raw = cursor.fetchall()
        elements = [(*row, 0) for row in raw]  # Add length=0
    else:
        # Minimal schema - compute counts from blobs
        cursor.execute("""
            SELECT em.guid, em.ifc_class, em.discipline, em.storey,
                   eg.vertices, eg.faces,
                   et.center_x, et.center_y, et.center_z
            FROM elements_meta em
            JOIN element_geometry eg ON em.guid = eg.guid
            JOIN element_transforms et ON em.guid = et.guid
        """)
        raw_elements = cursor.fetchall()
        elements = []
        for row in raw_elements:
            guid, ifc_class, discipline, storey, verts_blob, faces_blob, cx, cy, cz = row
            vert_count = len(verts_blob) // 12 if verts_blob else 0
            face_count = len(faces_blob) // 12 if faces_blob else 0
            elements.append((guid, ifc_class, discipline, storey, verts_blob, vert_count, face_count, cx, cy, cz, 0))

    if not elements:
        report.append("  No elements found!")
        conn.close()
        return "\n".join(report)

    # Compute overall bounding box
    all_vertices = []
    element_data = []

    for row in elements:
        guid, ifc_class, discipline, storey, verts_blob, vert_count, face_count, cx, cy, cz, length = row
        vertices = unpack_vertices(verts_blob)
        all_vertices.extend(vertices)

        bbox = compute_bbox(vertices)
        orientation = classify_orientation(bbox)
        shape = classify_shape(vert_count, face_count)

        element_data.append({
            'guid': guid,
            'ifc_class': ifc_class,
            'discipline': discipline,
            'storey': storey,
            'vertices': vertices,
            'vertex_count': vert_count,
            'face_count': face_count,
            'center': (cx, cy, cz),
            'length': length or 0,
            'bbox': bbox,
            'orientation': orientation,
            'shape': shape
        })

    # Building envelope
    building_bbox = compute_bbox(all_vertices)

    # ==========================================================================
    # LAYER 0: SPATIAL LAYOUT
    # ==========================================================================
    report.append("LAYER 0: SPATIAL LAYOUT (Orientation & Position)")
    report.append("=" * 70)
    report.append("")

    # Building position
    center_x = (building_bbox['min'][0] + building_bbox['max'][0]) / 2
    center_y = (building_bbox['min'][1] + building_bbox['max'][1]) / 2

    report.append("BUILDING POSITION")
    report.append("-" * 70)

    # Determine which side of origin
    pos_desc = []
    if center_x > 1:
        pos_desc.append("E of origin")
    elif center_x < -1:
        pos_desc.append("W of origin")
    if center_y > 1:
        pos_desc.append("N of origin")
    elif center_y < -1:
        pos_desc.append("S of origin")
    pos_str = ", ".join(pos_desc) if pos_desc else "at origin"

    report.append(f"  Center: ({center_x:.1f}, {center_y:.1f}) - {pos_str}")
    report.append(f"  Extent: X[{building_bbox['min'][0]:.1f}, {building_bbox['max'][0]:.1f}] Y[{building_bbox['min'][1]:.1f}, {building_bbox['max'][1]:.1f}] Z[{building_bbox['min'][2]:.1f}, {building_bbox['max'][2]:.1f}]")

    # Long axis orientation
    if building_bbox['size'][0] > building_bbox['size'][1] * 1.2:
        axis_orient = "Long axis runs E-W"
    elif building_bbox['size'][1] > building_bbox['size'][0] * 1.2:
        axis_orient = "Long axis runs N-S"
    else:
        axis_orient = "Roughly square footprint"
    report.append(f"  Orientation: {axis_orient}")
    report.append("")

    # Quadrant analysis
    report.append("QUADRANT ANALYSIS (from origin)")
    report.append("-" * 70)

    ne_count = sum(1 for e in element_data if e['center'][0] >= 0 and e['center'][1] >= 0)
    nw_count = sum(1 for e in element_data if e['center'][0] < 0 and e['center'][1] >= 0)
    se_count = sum(1 for e in element_data if e['center'][0] >= 0 and e['center'][1] < 0)
    sw_count = sum(1 for e in element_data if e['center'][0] < 0 and e['center'][1] < 0)
    total = len(element_data)

    def quadrant_status(count, total):
        pct = (count / total * 100) if total > 0 else 0
        if pct < 10:
            return f"{count} ({pct:.0f}%) ⚠️ Sparse"
        return f"{count} ({pct:.0f}%)"

    report.append(f"  NE (+X, +Y): {quadrant_status(ne_count, total)}")
    report.append(f"  NW (-X, +Y): {quadrant_status(nw_count, total)}")
    report.append(f"  SE (+X, -Y): {quadrant_status(se_count, total)}")
    report.append(f"  SW (-X, -Y): {quadrant_status(sw_count, total)}")
    report.append("")

    # Perimeter walls analysis
    walls = [e for e in element_data if e['ifc_class'] == 'IfcWall']
    if walls and len(walls) >= 4:
        report.append("PERIMETER WALLS (clockwise from North)")
        report.append("-" * 70)

        # Find walls at extremes
        ew_walls = [w for w in walls if w['orientation'] == 'E-W']
        ns_walls = [w for w in walls if w['orientation'] == 'N-S']

        # North wall (highest Y, E-W orientation)
        if ew_walls:
            north_candidates = sorted(ew_walls, key=lambda w: (w['bbox']['max'][1] + w['bbox']['min'][1])/2, reverse=True)
            if north_candidates:
                w = north_candidates[0]
                y_pos = (w['bbox']['min'][1] + w['bbox']['max'][1]) / 2
                x_min, x_max = w['bbox']['min'][0], w['bbox']['max'][0]
                report.append(f"  North: {w['length']:.1f}m at Y={y_pos:.1f}, from X={x_min:.0f} to X={x_max:.0f}")

        # East wall (highest X, N-S orientation)
        if ns_walls:
            east_candidates = sorted(ns_walls, key=lambda w: (w['bbox']['max'][0] + w['bbox']['min'][0])/2, reverse=True)
            if east_candidates:
                w = east_candidates[0]
                x_pos = (w['bbox']['min'][0] + w['bbox']['max'][0]) / 2
                y_min, y_max = w['bbox']['min'][1], w['bbox']['max'][1]
                report.append(f"  East:  {w['length']:.1f}m at X={x_pos:.1f}, from Y={y_min:.0f} to Y={y_max:.0f}")

        # South wall (lowest Y, E-W orientation)
        if ew_walls:
            south_candidates = sorted(ew_walls, key=lambda w: (w['bbox']['max'][1] + w['bbox']['min'][1])/2)
            if south_candidates:
                w = south_candidates[0]
                y_pos = (w['bbox']['min'][1] + w['bbox']['max'][1]) / 2
                x_min, x_max = w['bbox']['min'][0], w['bbox']['max'][0]
                report.append(f"  South: {w['length']:.1f}m at Y={y_pos:.1f}, from X={x_min:.0f} to X={x_max:.0f}")

        # West wall (lowest X, N-S orientation)
        if ns_walls:
            west_candidates = sorted(ns_walls, key=lambda w: (w['bbox']['max'][0] + w['bbox']['min'][0])/2)
            if west_candidates:
                w = west_candidates[0]
                x_pos = (w['bbox']['min'][0] + w['bbox']['max'][0]) / 2
                y_min, y_max = w['bbox']['min'][1], w['bbox']['max'][1]
                report.append(f"  West:  {w['length']:.1f}m at X={x_pos:.1f}, from Y={y_min:.0f} to Y={y_max:.0f}")

        report.append("")

    # Column grid with position
    columns = [e for e in element_data if e['ifc_class'] == 'IfcColumn']
    if columns:
        report.append("COLUMN GRID")
        report.append("-" * 70)

        col_positions = [(c['center'][0], c['center'][1]) for c in columns]

        # Find grid origin (minimum X, Y)
        min_col_x = min(p[0] for p in col_positions)
        min_col_y = min(p[1] for p in col_positions)
        report.append(f"  Grid origin: ({min_col_x:.1f}, {min_col_y:.1f})")

        grid = detect_grid_pattern(col_positions)
        if grid and grid.get('regular'):
            report.append(f"  Spacing: {grid['spacing_x']:.1f}m (X) × {grid['spacing_y']:.1f}m (Y)")
            expected = grid['cols'] * grid['rows']
            report.append(f"  Pattern: {grid['cols']} × {grid['rows']} = {expected} expected, {len(columns)} actual")
        else:
            report.append(f"  Pattern: Irregular distribution")
        report.append("")

    # ==========================================================================
    # LAYER 1: GEOMETRY
    # ==========================================================================
    report.append("")
    report.append("LAYER 1: GEOMETRY (What Blender Sees)")
    report.append("=" * 70)
    report.append("")

    report.append("BUILDING ENVELOPE")
    report.append("-" * 70)
    report.append(f"  Bounding box:")
    report.append(f"    X: [{building_bbox['min'][0]:.1f}, {building_bbox['max'][0]:.1f}] ({building_bbox['size'][0]:.1f}m)")
    report.append(f"    Y: [{building_bbox['min'][1]:.1f}, {building_bbox['max'][1]:.1f}] ({building_bbox['size'][1]:.1f}m)")
    report.append(f"    Z: [{building_bbox['min'][2]:.1f}, {building_bbox['max'][2]:.1f}] ({building_bbox['size'][2]:.1f}m)")
    report.append(f"  Overall dimensions: {building_bbox['size'][0]:.1f}m x {building_bbox['size'][1]:.1f}m x {building_bbox['size'][2]:.1f}m")
    report.append("")

    # Walls analysis
    walls = [e for e in element_data if e['ifc_class'] == 'IfcWall']
    if walls:
        report.append(f"WALLS ({len(walls)} elements)")
        report.append("-" * 70)

        # Sort by length
        walls_sorted = sorted(walls, key=lambda w: w['length'], reverse=True)

        report.append("  Top walls by length:")
        for i, wall in enumerate(walls_sorted[:5]):
            sx, sy, sz = wall['bbox']['size']
            pos_y = (wall['bbox']['min'][1] + wall['bbox']['max'][1]) / 2
            pos_x = (wall['bbox']['min'][0] + wall['bbox']['max'][0]) / 2

            if wall['orientation'] == 'E-W':
                report.append(f"    {i+1}. {wall['length']:.1f}m E-W at Y={pos_y:.1f}")
            elif wall['orientation'] == 'N-S':
                report.append(f"    {i+1}. {wall['length']:.1f}m N-S at X={pos_x:.1f}")
            else:
                report.append(f"    {i+1}. {wall['length']:.1f}m {wall['orientation']}")
        report.append("")

    # Columns analysis
    columns = [e for e in element_data if e['ifc_class'] == 'IfcColumn']
    if columns:
        report.append(f"COLUMNS ({len(columns)} elements)")
        report.append("-" * 70)

        # Get positions for grid detection
        col_positions = [(c['center'][0], c['center'][1]) for c in columns]
        grid = detect_grid_pattern(col_positions)

        if grid and grid.get('regular'):
            report.append(f"  Grid pattern: {grid['cols']} x {grid['rows']} detected")
            report.append(f"  Spacing: {grid['spacing_x']:.1f}m (X) x {grid['spacing_y']:.1f}m (Y)")
        else:
            report.append(f"  Pattern: Irregular or insufficient for grid detection")

        # Sample dimensions
        if columns:
            sample = columns[0]
            report.append(f"  Sample size: {sample['bbox']['size'][0]:.2f}m x {sample['bbox']['size'][1]:.2f}m x {sample['bbox']['size'][2]:.1f}m")
        report.append("")

    # Beams analysis
    beams = [e for e in element_data if e['ifc_class'] == 'IfcBeam']
    if beams:
        report.append(f"BEAMS ({len(beams)} elements)")
        report.append("-" * 70)

        lengths = [b['length'] for b in beams if b['length'] > 0]
        if lengths:
            report.append(f"  Length range: {min(lengths):.1f}m - {max(lengths):.1f}m")
            report.append(f"  Average length: {sum(lengths)/len(lengths):.1f}m")

        ew_count = sum(1 for b in beams if b['orientation'] == 'E-W')
        ns_count = sum(1 for b in beams if b['orientation'] == 'N-S')
        report.append(f"  Orientation: {ew_count} E-W, {ns_count} N-S")
        report.append("")

    # ==========================================================================
    # LAYER 2: SEMANTICS
    # ==========================================================================
    report.append("")
    report.append("LAYER 2: SEMANTICS (What Objects Mean)")
    report.append("=" * 70)
    report.append("")

    # By IFC class
    class_counts = Counter(e['ifc_class'] for e in element_data)
    report.append("BY IFC CLASS")
    report.append("-" * 70)
    for ifc_class, count in class_counts.most_common():
        disciplines = set(e['discipline'] for e in element_data if e['ifc_class'] == ifc_class)
        disc_str = ', '.join(disciplines)
        report.append(f"  {ifc_class}: {count} ({disc_str})")
    report.append("")

    # By discipline
    disc_counts = Counter(e['discipline'] for e in element_data)
    report.append("BY DISCIPLINE")
    report.append("-" * 70)
    for discipline, count in disc_counts.most_common():
        report.append(f"  {discipline}: {count}")

    # Check for missing disciplines
    expected = {'ARC', 'STR', 'MEP'}
    missing = expected - set(disc_counts.keys())
    if missing:
        for m in missing:
            report.append(f"  {m}: 0 (not present)")
    report.append("")

    # By floor
    storey_counts = Counter(e['storey'] for e in element_data if e['storey'])
    if storey_counts:
        report.append("BY FLOOR")
        report.append("-" * 70)
        for storey, count in sorted(storey_counts.items()):
            report.append(f"  {storey}: {count}")
        report.append("")

    # ==========================================================================
    # LAYER 3: ANALYTICS
    # ==========================================================================
    report.append("")
    report.append("LAYER 3: ANALYTICS (Space Characteristics)")
    report.append("=" * 70)
    report.append("")

    # Perimeter analysis (for walls)
    if walls and len(walls) >= 4:
        report.append("PERIMETER ANALYSIS")
        report.append("-" * 70)

        # Get longest walls in each direction
        ew_walls = sorted([w for w in walls if w['orientation'] == 'E-W'],
                         key=lambda w: w['length'], reverse=True)
        ns_walls = sorted([w for w in walls if w['orientation'] == 'N-S'],
                         key=lambda w: w['length'], reverse=True)

        if len(ew_walls) >= 2 and len(ns_walls) >= 2:
            # Check for closure
            north_wall = ew_walls[0]
            south_wall = ew_walls[1] if len(ew_walls) > 1 else None

            report.append(f"  Longest E-W walls:")
            for i, w in enumerate(ew_walls[:2]):
                pos_y = (w['bbox']['min'][1] + w['bbox']['max'][1]) / 2
                edge = "North" if pos_y > 0 else "South"
                report.append(f"    {i+1}. {w['length']:.1f}m at Y={pos_y:.1f} ({edge})")

            report.append(f"  Longest N-S walls:")
            for i, w in enumerate(ns_walls[:2]):
                pos_x = (w['bbox']['min'][0] + w['bbox']['max'][0]) / 2
                edge = "East" if pos_x > 0 else "West"
                report.append(f"    {i+1}. {w['length']:.1f}m at X={pos_x:.1f} ({edge})")
        report.append("")

    # Openings
    windows = [e for e in element_data if e['ifc_class'] == 'IfcWindow']
    doors = [e for e in element_data if e['ifc_class'] == 'IfcDoor']

    report.append("OPENINGS")
    report.append("-" * 70)
    report.append(f"  Windows: {len(windows)}")
    report.append(f"  Doors: {len(doors)}")
    if len(doors) == 0:
        report.append(f"    (No doors detected)")
    report.append("")

    # ==========================================================================
    # LAYER 4: SUMMARY
    # ==========================================================================
    report.append("")
    report.append("LAYER 4: SUMMARY (Aggregate Metrics)")
    report.append("=" * 70)
    report.append("")

    report.append("ELEMENT COUNTS")
    report.append("-" * 70)
    report.append(f"  Total elements: {len(element_data)}")
    for ifc_class, count in class_counts.most_common():
        report.append(f"    {ifc_class}: {count}")
    report.append("")

    # Wall metrics
    if walls:
        total_wall_length = sum(w['length'] for w in walls)
        report.append("WALL METRICS")
        report.append("-" * 70)
        report.append(f"  Total wall length: {total_wall_length:.1f}m")
        report.append(f"  Average wall length: {total_wall_length/len(walls):.1f}m")
        report.append("")

    # Geometry stats
    total_verts = sum(e['vertex_count'] for e in element_data)
    total_faces = sum(e['face_count'] for e in element_data)

    report.append("GEOMETRY STATISTICS")
    report.append("-" * 70)
    report.append(f"  Total vertices: {total_verts:,}")
    report.append(f"  Total faces: {total_faces:,}")
    report.append(f"  Average vertices/element: {total_verts/len(element_data):.0f}")
    report.append(f"  Average faces/element: {total_faces/len(element_data):.0f}")
    report.append("")

    # Volume estimate
    vol = building_bbox['size'][0] * building_bbox['size'][1] * building_bbox['size'][2]
    report.append("VOLUME ESTIMATE")
    report.append("-" * 70)
    report.append(f"  Bounding box volume: {vol:,.0f} m³")
    report.append("")

    # ==========================================================================
    # LAYER 5: SHAPE CLASSIFICATION
    # ==========================================================================
    report.append("")
    report.append("LAYER 5: SHAPE CLASSIFICATION (Complexity)")
    report.append("=" * 70)
    report.append("")

    shape_counts = Counter(e['shape'] for e in element_data)
    total = len(element_data)

    report.append("BY PRIMITIVE TYPE")
    report.append("-" * 70)
    for shape, count in shape_counts.most_common():
        pct = (count / total) * 100
        report.append(f"  {shape.capitalize()}: {count} ({pct:.0f}%)")
    report.append("")

    # Mesh complexity
    vert_counts = [e['vertex_count'] for e in element_data]
    report.append("MESH COMPLEXITY")
    report.append("-" * 70)
    report.append(f"  Simplest: {min(vert_counts)} vertices")
    report.append(f"  Most complex: {max(vert_counts)} vertices")
    report.append(f"  Average: {sum(vert_counts)/len(vert_counts):.0f} vertices")

    # Performance assessment
    simple_pct = sum(1 for v in vert_counts if v <= 26) / len(vert_counts) * 100
    if simple_pct > 80:
        report.append(f"  Render performance: Good (mostly simple geometry)")
    else:
        report.append(f"  Render performance: May be slow ({100-simple_pct:.0f}% complex)")
    report.append("")

    # Footer
    report.append("=" * 70)
    report.append("END OF AUDIT REPORT")
    report.append("=" * 70)

    conn.close()
    return "\n".join(report)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Audit federation database and generate text report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('database', help='Path to federation database (.db)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--save', '-s', action='store_true',
                       help='Save timestamped report to AuditReports directory')

    args = parser.parse_args()

    db_path = Path(args.database)
    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    report = generate_report(str(db_path))

    # Save timestamped report if requested
    if args.save:
        from datetime import datetime
        reports_dir = Path(__file__).parent.parent / "AuditReports"
        reports_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_name = db_path.stem
        report_path = reports_dir / f"{db_name}_{timestamp}.txt"

        with open(report_path, 'w') as f:
            f.write(report)
        print(f"Report saved to: {report_path}")

    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report saved to: {args.output}")
    elif not args.save:
        print(report)
    else:
        # If --save was used, still print to stdout
        print(report)


if __name__ == "__main__":
    main()
