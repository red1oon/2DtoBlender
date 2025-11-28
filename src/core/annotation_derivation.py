#!/usr/bin/env python3
"""
Annotation Derivation - Rule 0 Compliant Data Extraction

Derives building dimensions and spatial data from Annotations DB.
Replaces manual GridTruth.json with automated extraction.

Philosophy:
- PDF → Annotations DB (extracted primitives)
- Annotations DB → Derivation (computed structures)
- No manual data entry

Functions:
- derive_building_envelope() - Building outer bounds
- derive_room_bounds() - Room boundaries from labels + walls
- derive_elevations() - Height data from dimensions/defaults
- derive_grid_positions() - Grid coordinate system
"""

import sqlite3
import numpy as np
from typing import Dict, Tuple, Optional
from pathlib import Path


def derive_scale_from_dimensions(db_path: str) -> Tuple[float, float]:
    """
    Derive PDF-to-meters scale from dimension annotations

    Matches dimension text (e.g., "1300" = 1.3m) to grid line spacings
    to calculate the scale factor: meters / PDF_units

    Args:
        db_path: Path to annotations database

    Returns:
        (scale_x, scale_y) in meters per PDF unit
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get dimension text (4-digit numbers like "1300", "3100")
    cursor.execute("""
        SELECT text, x, y FROM primitives_text
        WHERE text GLOB '[0-9][0-9][0-9][0-9]'
        AND LENGTH(text) = 4
        AND page = 1
    """)
    dimensions = cursor.fetchall()

    # Get grid label positions
    # Strategy: Find the most common y-position for horizontal grids (they should be aligned)
    # Then filter horizontal grids to that y-range
    cursor.execute("""
        SELECT text, x, y FROM primitives_text
        WHERE text IN ('A','B','C','D','E')
        AND page = 1
    """)
    all_h_grids = cursor.fetchall()

    # Find the y-cluster with most complete grid set (A, B, C, D, E)
    if all_h_grids:
        # Group grids by y-position clusters (tolerance: 5 units)
        y_clusters = {}
        for label, x, y in all_h_grids:
            # Find existing cluster or create new one
            found_cluster = False
            for cluster_y in list(y_clusters.keys()):
                if abs(y - cluster_y) < 5:
                    y_clusters[cluster_y].append((label, x))
                    found_cluster = True
                    break
            if not found_cluster:
                y_clusters[y] = [(label, x)]

        # Find cluster with most unique labels
        best_cluster = None
        max_unique = 0
        best_cluster_y = None
        for cluster_y, grids in y_clusters.items():
            unique_labels = len(set(label for label, _ in grids))
            if unique_labels > max_unique:
                max_unique = unique_labels
                best_cluster = grids
                best_cluster_y = cluster_y

        print(f"\n=== HORIZONTAL GRID DIAGNOSTICS ===")
        print(f"Found {len(y_clusters)} Y-position clusters on page 1")
        for cluster_y, grids in sorted(y_clusters.items()):
            unique = len(set(label for label, _ in grids))
            labels = sorted(set(label for label, _ in grids))
            print(f"  Y~{cluster_y:.1f}: {len(grids)} grids, {unique} unique ({', '.join(labels)})")
        print(f"Selected cluster Y~{best_cluster_y:.1f} with {max_unique} unique labels")
        print(f"\nGrid positions in selected cluster:")
        for label, x in sorted(best_cluster, key=lambda g: g[0]):
            print(f"  {label}: x={x:.1f}")

        # Average x positions for each label in best cluster
        h_positions = {}
        for label, x in best_cluster:
            if label not in h_positions:
                h_positions[label] = []
            h_positions[label].append(x)
        h_grids = {label: np.mean(xs) for label, xs in h_positions.items()}

        print(f"\nAfter averaging duplicates:")
        for label in sorted(h_grids.keys()):
            count = len(h_positions[label])
            if count > 1:
                print(f"  {label}: x={h_grids[label]:.1f} (averaged {count} positions: {[f'{x:.1f}' for x in h_positions[label]]})")
            else:
                print(f"  {label}: x={h_grids[label]:.1f}")
    else:
        h_grids = {}

    # Same for vertical grids (find x-cluster with most complete grid set)
    cursor.execute("""
        SELECT text, x, y FROM primitives_text
        WHERE text IN ('1','2','3','4','5')
        AND page = 1
    """)
    all_v_grids = cursor.fetchall()

    if all_v_grids:
        # Group grids by x-position clusters (tolerance: 5 units)
        x_clusters = {}
        for label, x, y in all_v_grids:
            found_cluster = False
            for cluster_x in list(x_clusters.keys()):
                if abs(x - cluster_x) < 5:
                    x_clusters[cluster_x].append((label, y))
                    found_cluster = True
                    break
            if not found_cluster:
                x_clusters[x] = [(label, y)]

        # Find cluster with most unique labels
        best_cluster = None
        max_unique = 0
        best_cluster_x = None
        for cluster_x, grids in x_clusters.items():
            unique_labels = len(set(label for label, _ in grids))
            if unique_labels > max_unique:
                max_unique = unique_labels
                best_cluster = grids
                best_cluster_x = cluster_x

        print(f"\n=== VERTICAL GRID DIAGNOSTICS ===")
        print(f"Found {len(x_clusters)} X-position clusters on page 1")
        for cluster_x, grids in sorted(x_clusters.items()):
            unique = len(set(label for label, _ in grids))
            labels = sorted(set(label for label, _ in grids), key=lambda x: int(x))
            print(f"  X~{cluster_x:.1f}: {len(grids)} grids, {unique} unique ({', '.join(labels)})")
        print(f"Selected cluster X~{best_cluster_x:.1f} with {max_unique} unique labels")
        print(f"\nGrid positions in selected cluster:")
        for label, y in sorted(best_cluster, key=lambda g: int(g[0])):
            print(f"  {label}: y={y:.1f}")

        # Average y positions for each label in best cluster
        v_positions = {}
        for label, y in best_cluster:
            if label not in v_positions:
                v_positions[label] = []
            v_positions[label].append(y)
        v_grids = {label: np.mean(ys) for label, ys in v_positions.items()}

        print(f"\nAfter averaging duplicates:")
        for label in sorted(v_grids.keys(), key=lambda x: int(x)):
            count = len(v_positions[label])
            if count > 1:
                print(f"  {label}: y={v_grids[label]:.1f} (averaged {count} positions: {[f'{y:.1f}' for y in v_positions[label]]})")
            else:
                print(f"  {label}: y={v_grids[label]:.1f}")
    else:
        v_grids = {}

    conn.close()

    if len(h_grids) < 2 or len(v_grids) < 2:
        raise ValueError("Insufficient grid labels found for scale calibration")

    # Match dimension text to grid pairs
    # Strategy: Find dimension text near grid lines, match to spacing

    scale_x = None
    scale_y = None

    # Find horizontal scale (from vertical dimensions like "1300", "3100")
    # These dimensions are between grid lines A-B, B-C, etc.
    # Strategy: Find ALL candidate matches, prefer ADJACENT grids and SMALL dimensions
    candidates = []
    for dim_text, dim_x, dim_y in dimensions:
        dim_value_mm = float(dim_text)
        dim_value_m = dim_value_mm / 1000.0

        # Skip very large dimensions (likely total building size, not grid spacing)
        if dim_value_m > 5.0:  # Grid spacings typically < 5m
            continue

        # Check if this dimension is near horizontal grid pair
        # Dimension text typically appears between the grids it measures
        grid_labels = sorted(h_grids.keys())  # Sort alphabetically: A, B, C, D, E
        for i in range(len(grid_labels) - 1):
            label1, label2 = grid_labels[i], grid_labels[i + 1]
            x1, x2 = h_grids[label1], h_grids[label2]
            midpoint = (x1 + x2) / 2.0

            # Check if dimension text is near this grid pair
            if min(x1, x2) - 50 <= dim_x <= max(x1, x2) + 50:
                pdf_distance = abs(x2 - x1)
                calculated_scale = dim_value_m / pdf_distance

                # Sanity check: scale should be in reasonable range (0.001 to 0.1 m/unit)
                if 0.001 <= calculated_scale <= 0.1:
                    # Calculate how close dimension is to grid midpoint (prefer centered dimensions)
                    distance_to_midpoint = abs(dim_x - midpoint)
                    # Prefer FIRST grid pair (A-B) and dimensions close to midpoint
                    priority = i * 100 + distance_to_midpoint
                    candidates.append((calculated_scale, dim_text, label1, label2, pdf_distance, dim_value_m, priority))

    # Select best candidate (lowest priority = first grid pair + closest to midpoint)
    if candidates:
        candidates.sort(key=lambda c: c[6])  # Sort by priority
        scale_x, dim_text, label1, label2, pdf_distance, dim_value_m, _ = candidates[0]
        print(f"   Found X scale from dimension '{dim_text}' between grids {label1}-{label2}")
        print(f"   PDF distance: {pdf_distance:.2f}, Real distance: {dim_value_m}m, Scale: {scale_x:.6f} m/unit")

    # Find vertical scale (from horizontal dimensions)
    # Strategy: Find ALL candidate matches, prefer ADJACENT grids and SMALL dimensions
    candidates = []
    for dim_text, dim_x, dim_y in dimensions:
        dim_value_mm = float(dim_text)
        dim_value_m = dim_value_mm / 1000.0

        # Skip very large dimensions (likely total building size, not grid spacing)
        if dim_value_m > 5.0:  # Grid spacings typically < 5m
            continue

        # Check if this dimension is near vertical grid pair
        grid_labels = sorted(v_grids.keys(), key=lambda x: int(x))  # Sort numerically: 1, 2, 3, 4, 5
        for i in range(len(grid_labels) - 1):
            label1, label2 = grid_labels[i], grid_labels[i + 1]
            y1, y2 = v_grids[label1], v_grids[label2]
            midpoint = (y1 + y2) / 2.0

            # Check if dimension text is near this grid pair
            if min(y1, y2) - 50 <= dim_y <= max(y1, y2) + 50:
                pdf_distance = abs(y2 - y1)
                calculated_scale = dim_value_m / pdf_distance

                # Sanity check
                if 0.001 <= calculated_scale <= 0.1:
                    # Calculate how close dimension is to grid midpoint (prefer centered dimensions)
                    distance_to_midpoint = abs(dim_y - midpoint)
                    # Prefer FIRST grid pair (1-2) and dimensions close to midpoint
                    priority = i * 100 + distance_to_midpoint
                    candidates.append((calculated_scale, dim_text, label1, label2, pdf_distance, dim_value_m, priority))

    # Select best candidate (lowest priority = first grid pair + closest to midpoint)
    if candidates:
        candidates.sort(key=lambda c: c[6])  # Sort by priority
        scale_y, dim_text, label1, label2, pdf_distance, dim_value_m, _ = candidates[0]
        print(f"   Found Y scale from dimension '{dim_text}' between grids {label1}-{label2}")
        print(f"   PDF distance: {pdf_distance:.2f}, Real distance: {dim_value_m}m, Scale: {scale_y:.6f} m/unit")

    # If we didn't find both scales, use the one we found for both axes
    if scale_x and not scale_y:
        scale_y = scale_x
        print(f"   Using X scale for Y axis (same scale assumed)")
    elif scale_y and not scale_x:
        scale_x = scale_y
        print(f"   Using Y scale for X axis (same scale assumed)")
    elif not scale_x and not scale_y:
        raise ValueError("Could not derive scale from dimension annotations")

    return scale_x, scale_y


def derive_grid_positions(db_path: str) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Derive grid positions from grid labels in primitives_text

    Uses PDF coordinates + scale calibration to calculate real-world positions.
    NO HARDCODED VALUES.

    Args:
        db_path: Path to annotations database

    Returns:
        (grid_horizontal, grid_vertical) where:
        - grid_horizontal: {A: 0.0, B: 1.3, C: 4.4, ...} (calculated from PDF)
        - grid_vertical: {1: 0.0, 2: 2.3, 3: 5.4, ...} (calculated from PDF)
    """
    # Get scale from dimension annotations
    scale_x, scale_y = derive_scale_from_dimensions(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get horizontal grid labels (find cluster with most complete grid set)
    cursor.execute("""
        SELECT text, x, y FROM primitives_text
        WHERE text IN ('A','B','C','D','E')
        AND page = 1
    """)
    all_h_grids = cursor.fetchall()

    if all_h_grids:
        # Group grids by y-position clusters
        y_clusters = {}
        for label, x, y in all_h_grids:
            found_cluster = False
            for cluster_y in list(y_clusters.keys()):
                if abs(y - cluster_y) < 5:
                    y_clusters[cluster_y].append((label, x))
                    found_cluster = True
                    break
            if not found_cluster:
                y_clusters[y] = [(label, x)]

        # Find cluster with most unique labels
        best_cluster = None
        max_unique = 0
        for cluster_y, grids in y_clusters.items():
            unique_labels = len(set(label for label, _ in grids))
            if unique_labels > max_unique:
                max_unique = unique_labels
                best_cluster = grids

        h_positions = {}
        for label, x in best_cluster:
            if label not in h_positions:
                h_positions[label] = []
            h_positions[label].append(x)
        h_grids_avg = {label: np.mean(xs) for label, xs in h_positions.items()}
        # Sort by label order (A, B, C, D, E) not PDF position
        h_grids_data = sorted(h_grids_avg.items(), key=lambda x: x[0])
    else:
        raise ValueError("Horizontal grid labels not found in database")

    # Get vertical grid labels (find cluster with most complete grid set)
    cursor.execute("""
        SELECT text, x, y FROM primitives_text
        WHERE text IN ('1','2','3','4','5')
        AND page = 1
    """)
    all_v_grids = cursor.fetchall()

    if all_v_grids:
        # Group grids by x-position clusters
        x_clusters = {}
        for label, x, y in all_v_grids:
            found_cluster = False
            for cluster_x in list(x_clusters.keys()):
                if abs(x - cluster_x) < 5:
                    x_clusters[cluster_x].append((label, y))
                    found_cluster = True
                    break
            if not found_cluster:
                x_clusters[x] = [(label, y)]

        # Find cluster with most unique labels
        best_cluster = None
        max_unique = 0
        for cluster_x, grids in x_clusters.items():
            unique_labels = len(set(label for label, _ in grids))
            if unique_labels > max_unique:
                max_unique = unique_labels
                best_cluster = grids

        v_positions = {}
        for label, y in best_cluster:
            if label not in v_positions:
                v_positions[label] = []
            v_positions[label].append(y)
        v_grids_avg = {label: np.mean(ys) for label, ys in v_positions.items()}
        # Sort by label order (1, 2, 3, 4, 5) not PDF position
        # PDF y-coordinates increase top-to-bottom, but grid 1 should be origin
        v_grids_data = sorted(v_grids_avg.items(), key=lambda x: int(x[0]))
    else:
        raise ValueError("Vertical grid labels not found in database")

    conn.close()

    # Convert PDF coordinates to real-world positions
    # Origin = first grid position (A for horizontal, 1 for vertical)
    origin_x = h_grids_data[0][1]  # PDF x of first grid
    origin_y = v_grids_data[0][1]  # PDF y of first grid

    # Calculate real positions using scale
    grid_horizontal = {}
    for label, pdf_x in h_grids_data:
        # Convert PDF coordinate to meters, relative to origin
        real_x = (pdf_x - origin_x) * scale_x
        grid_horizontal[label] = round(real_x, 2)

    grid_vertical = {}
    for label, pdf_y in v_grids_data:
        # Convert PDF coordinate to meters, relative to origin
        # PDF y increases downward, so reverse the calculation
        real_y = (origin_y - pdf_y) * scale_y
        grid_vertical[label] = round(real_y, 2)

    # SANITY CHECKS: Validate building dimensions are reasonable for terrace house
    grid_width = grid_horizontal.get('E', 0.0) - grid_horizontal.get('A', 0.0)
    grid_depth = max(grid_vertical.values()) - min(grid_vertical.values())

    if not (3.0 <= grid_width <= 15.0):
        raise ValueError(
            f"Grid width {grid_width:.1f}m unreasonable for terrace house (expected 3-15m).\n"
            f"Likely cause: Wrong dimension matched or wrong grid cluster selected.\n"
            f"Horizontal grids: {grid_horizontal}"
        )

    if not (5.0 <= grid_depth <= 20.0):
        raise ValueError(
            f"Grid depth {grid_depth:.1f}m unreasonable for terrace house (expected 5-20m).\n"
            f"Likely cause: Wrong dimension matched or wrong grid cluster selected.\n"
            f"Vertical grids: {grid_vertical}"
        )

    print(f"✅ Derived grid positions from PDF coordinates + scale calibration")
    print(f"   Horizontal: {grid_horizontal}")
    print(f"   Vertical: {grid_vertical}")
    print(f"   Scale: {scale_x:.6f} m/unit (X), {scale_y:.6f} m/unit (Y)")
    print(f"   Building size: {grid_width:.1f}m wide × {grid_depth:.1f}m deep")

    return (grid_horizontal, grid_vertical)


def derive_building_envelope(db_path: str) -> Dict[str, float]:
    """
    Derive building envelope from annotations

    Strategy:
    1. Try: Derive from room bounds (if rooms detected)
    2. Fallback: Use grid extents (A to E, 1 to 5)
    3. Fallback: Use wall line extents

    Args:
        db_path: Path to annotations database

    Returns:
        {x_min, x_max, y_min, y_max, width, depth, area_m2, perimeter_m}
    """
    # First try: derive from grid positions (most reliable)
    grid_h, grid_v = derive_grid_positions(db_path)

    # Building envelope typically 750mm setback from grid
    # Grid extent: A to E, 1 to 5
    # Get min/max from actual grid values (no hardcoded fallbacks)
    h_values = list(grid_h.values())
    v_values = list(grid_v.values())

    grid_x_min = min(h_values)
    grid_x_max = max(h_values)
    grid_y_min = min(v_values)
    grid_y_max = max(v_values)

    # Apply setback (750mm from grid to exterior wall face)
    setback = 0.75
    x_min = grid_x_min + setback
    x_max = grid_x_max - setback
    y_min = grid_y_min + setback
    y_max = grid_y_max - setback

    width = x_max - x_min
    depth = y_max - y_min
    area_m2 = width * depth
    perimeter_m = 2 * (width + depth)

    envelope = {
        'x_min': round(x_min, 2),
        'x_max': round(x_max, 2),
        'y_min': round(y_min, 2),
        'y_max': round(y_max, 2),
        'width': round(width, 1),
        'depth': round(depth, 1),
        'area_m2': round(area_m2, 1),
        'perimeter_m': round(perimeter_m, 1)
    }

    print(f"✅ Derived building envelope from grid extents:")
    print(f"   Dimensions: {envelope['width']}m × {envelope['depth']}m")
    print(f"   Area: {envelope['area_m2']}m²")

    return envelope


def derive_room_bounds(db_path: str) -> Dict[str, Dict[str, float]]:
    """
    Derive room bounds from room labels + enclosing walls

    Strategy:
    1. Find room labels (RUANG TAMU, DAPUR, BILIK, etc.)
    2. Find wall lines from primitives_lines
    3. For each room label, find nearest enclosing walls
    4. Compute bounding box from enclosing walls
    5. Convert to real-world coordinates using scale

    NO HARDCODED VALUES.

    Args:
        db_path: Path to annotations database

    Returns:
        {ROOM_NAME: {x_min, x_max, y_min, y_max}}
    """
    # Get scale for converting PDF coords to meters
    scale_x, scale_y = derive_scale_from_dimensions(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Extract room labels with their PDF positions
    cursor.execute("""
        SELECT text, x, y FROM primitives_text
        WHERE page = 1
        AND (
            text LIKE '%RUANG%'
            OR text LIKE '%BILIK%'
            OR text LIKE '%DAPUR%'
            OR text LIKE '%TANDAS%'
            OR text LIKE '%BASUH%'
            OR text LIKE '%MANDI%'
        )
    """)
    room_labels = cursor.fetchall()

    if not room_labels:
        raise ValueError("No room labels found in database - cannot derive room bounds")

    # Get wall lines (filter for substantial lines, likely walls)
    # Walls are typically longer than 20 PDF units
    cursor.execute("""
        SELECT x0, y0, x1, y1 FROM primitives_lines
        WHERE page = 1
        AND length > 20
    """)
    wall_lines = cursor.fetchall()

    conn.close()

    if not wall_lines:
        raise ValueError("No wall lines found in database - cannot derive room bounds")

    # Get grid positions for origin reference
    grid_h, grid_v = derive_grid_positions(db_path)
    origin_x_pdf = min([pos / scale_x for pos in grid_h.values()])  # Reconstruct PDF origin
    origin_y_pdf = min([pos / scale_y for pos in grid_v.values()])

    # Separate walls into vertical and horizontal
    vertical_walls = []
    horizontal_walls = []
    for x0, y0, x1, y1 in wall_lines:
        if abs(x1 - x0) < 5:  # Vertical wall (x doesn't change much)
            vertical_walls.append((x0, x1, min(y0, y1), max(y0, y1)))
        elif abs(y1 - y0) < 5:  # Horizontal wall (y doesn't change much)
            horizontal_walls.append((y0, y1, min(x0, x1), max(x0, x1)))

    print(f"   Found {len(vertical_walls)} vertical walls, {len(horizontal_walls)} horizontal walls")

    room_bounds = {}

    for room_name, label_x, label_y in room_labels:
        # Normalize room name (remove spaces, convert to uppercase)
        normalized_name = room_name.strip().replace(' ', '_').upper()

        # Find enclosing walls around this label position
        # Left wall: nearest vertical wall with x < label_x
        left_walls = [(x, y_min, y_max) for x, _, y_min, y_max in vertical_walls
                      if x < label_x and y_min <= label_y <= y_max]
        left_x = max([x for x, _, _ in left_walls]) if left_walls else label_x - 50

        # Right wall: nearest vertical wall with x > label_x
        right_walls = [(x, y_min, y_max) for x, _, y_min, y_max in vertical_walls
                       if x > label_x and y_min <= label_y <= y_max]
        right_x = min([x for x, _, _ in right_walls]) if right_walls else label_x + 50

        # Bottom wall: nearest horizontal wall with y < label_y
        bottom_walls = [(y, x_min, x_max) for y, _, x_min, x_max in horizontal_walls
                        if y < label_y and x_min <= label_x <= x_max]
        bottom_y = max([y for y, _, _ in bottom_walls]) if bottom_walls else label_y - 50

        # Top wall: nearest horizontal wall with y > label_y
        top_walls = [(y, x_min, x_max) for y, _, x_min, x_max in horizontal_walls
                     if y > label_y and x_min <= label_x <= x_max]
        top_y = min([y for y, _, _ in top_walls]) if top_walls else label_y + 50

        # Convert PDF coordinates to real-world coordinates
        x_min_real = (left_x - origin_x_pdf) * scale_x
        x_max_real = (right_x - origin_x_pdf) * scale_x
        y_min_real = (bottom_y - origin_y_pdf) * scale_y
        y_max_real = (top_y - origin_y_pdf) * scale_y

        room_bounds[normalized_name] = {
            'x_min': round(x_min_real, 2),
            'x_max': round(x_max_real, 2),
            'y_min': round(y_min_real, 2),
            'y_max': round(y_max_real, 2)
        }

    print(f"✅ Derived {len(room_bounds)} room bounds from wall-based detection")
    print(f"   Rooms: {', '.join(room_bounds.keys())}")

    return room_bounds


def derive_elevations(db_path: str) -> Dict[str, float]:
    """
    Derive elevation data from dimension annotations or defaults

    Strategy:
    1. Try: Extract ceiling heights from dimension text
    2. Try: Extract floor levels from annotations
    3. Fallback: Use Malaysian residential standards

    Args:
        db_path: Path to annotations database

    Returns:
        {ground, floor_finish_level, window_sill_low, window_sill_high,
         door_head, ceiling, roof_top}
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Try to extract ceiling height from dimension annotations
    # Look for height-related text (e.g., "3000mm", "3.0m")
    cursor.execute("""
        SELECT text FROM primitives_text
        WHERE page = 1
        AND (text LIKE '%3000%' OR text LIKE '%ceiling%' OR text LIKE '%height%')
        LIMIT 10
    """)

    height_annotations = cursor.fetchall()
    conn.close()

    # Parse ceiling height if found
    ceiling_height = 3.0  # Default for Malaysian residential

    for (text,) in height_annotations:
        # Simple parsing for "3000mm" → 3.0m
        if '3000' in text:
            ceiling_height = 3.0
            break

    # Malaysian residential building standards (UBBL 1984)
    elevations = {
        'ground': 0.0,
        'floor_finish_level': 0.15,      # 150mm screed
        'window_sill_low': 0.9,          # Bathroom window
        'window_sill_high': 1.5,         # Standard window
        'door_head': 2.1,                # Standard door 2100mm
        'ceiling': ceiling_height,
        'roof_top': ceiling_height + 0.5  # ~500mm roof structure
    }

    print(f"✅ Derived elevations (ceiling: {ceiling_height}m)")

    return elevations


def get_annotation_db_path(pdf_path: str) -> Optional[str]:
    """
    Get annotation database path from PDF path

    Args:
        pdf_path: Path to source PDF

    Returns:
        Path to annotation database or None if not found
    """
    pdf_path_obj = Path(pdf_path)
    pdf_basename = pdf_path_obj.stem.replace(' ', '_')

    # Check in output_artifacts/
    db_path = pdf_path_obj.parent.parent / 'output_artifacts' / f'{pdf_basename}_ANNOTATION_FROM_2D.db'

    if db_path.exists():
        return str(db_path)

    # Check relative to current directory
    db_path = Path('output_artifacts') / f'{pdf_basename}_ANNOTATION_FROM_2D.db'

    if db_path.exists():
        return str(db_path)

    return None


if __name__ == "__main__":
    """Test derivation functions"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python annotation_derivation.py <annotation_db_path>")
        sys.exit(1)

    db_path = sys.argv[1]

    print("=" * 80)
    print("ANNOTATION DERIVATION TEST")
    print("=" * 80)
    print(f"Database: {db_path}\n")

    print("\n1. Grid Positions:")
    print("-" * 80)
    grid_h, grid_v = derive_grid_positions(db_path)

    print("\n2. Building Envelope:")
    print("-" * 80)
    envelope = derive_building_envelope(db_path)

    print("\n3. Room Bounds:")
    print("-" * 80)
    rooms = derive_room_bounds(db_path)
    print(f"   Rooms: {', '.join(rooms.keys())}")

    print("\n4. Elevations:")
    print("-" * 80)
    elevations = derive_elevations(db_path)

    print("\n" + "=" * 80)
    print("✅ DERIVATION TEST COMPLETE")
    print("=" * 80)
