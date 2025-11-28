#!/usr/bin/env python3
"""
GridTruth Fallback Generator

Generates structural elements from GridTruth.json when PDF extraction fails.
Used by extraction_engine.py as fallback for mandatory template items.

Functions:
- generate_walls(grid_truth_path) -> list
- generate_roof(grid_truth_path) -> dict
- generate_drains(grid_truth_path) -> list
- generate_item(item, grid_truth_path) -> list
"""

import json
from pathlib import Path


def generate_walls(grid_truth_path):
    """
    Generate wall segments from GridTruth room_bounds

    Args:
        grid_truth_path: Path to GridTruth.json

    Returns:
        list: Wall objects with position, end_point, thickness
    """
    try:
        with open(grid_truth_path) as f:
            grid_truth = json.load(f)
    except FileNotFoundError:
        print(f"⚠️  GridTruth not found: {grid_truth_path}")
        return []

    room_bounds = grid_truth.get('room_bounds', {})
    if not room_bounds:
        print("⚠️  No room_bounds in GridTruth")
        return []

    # Track all wall segments to avoid duplicates
    wall_segments = set()

    for room_name, bounds in room_bounds.items():
        if room_name.startswith('_'):  # Skip metadata like _note
            continue

        x_min, x_max = bounds['x_min'], bounds['x_max']
        y_min, y_max = bounds['y_min'], bounds['y_max']

        # Create 4 wall segments for this room (as tuples for deduplication)
        segments = [
            # South wall: (x_min, y_min) → (x_max, y_min)
            ((x_min, y_min, 0.0), (x_max, y_min, 0.0)),
            # North wall: (x_min, y_max) → (x_max, y_max)
            ((x_min, y_max, 0.0), (x_max, y_max, 0.0)),
            # West wall: (x_min, y_min) → (x_min, y_max)
            ((x_min, y_min, 0.0), (x_min, y_max, 0.0)),
            # East wall: (x_max, y_min) → (x_max, y_max)
            ((x_max, y_min, 0.0), (x_max, y_max, 0.0)),
        ]

        for seg in segments:
            # Add both directions (normalize to avoid duplicates)
            normalized = tuple(sorted([seg[0], seg[1]]))
            wall_segments.add(normalized)

    # Convert to wall objects
    walls = []
    for i, (start, end) in enumerate(wall_segments):
        # Determine if interior or exterior wall
        # (simplified: exterior if on building perimeter)
        is_exterior = (start[0] == 0.0 or start[1] == 0.0 or
                       end[0] == 0.0 or end[1] == 0.0 or
                       start[0] >= 11.0 or start[1] >= 8.0 or
                       end[0] >= 11.0 or end[1] >= 8.0)

        wall_type = "wall_brick_3m_lod300" if is_exterior else "wall_lightweight_100_lod300"
        wall_category = "exterior" if is_exterior else "interior"

        wall = {
            "name": f"wall_{wall_category}_{i+1}",
            "object_type": wall_type,
            "position": list(start),
            "end_point": list(end),
            "height": 3.0,
            "thickness": 0.15 if is_exterior else 0.10,
            "placed": False,
            "room": "structure",
            "phase": "1C_walls"
        }
        walls.append(wall)

    print(f"    ✅ Generated {len(walls)} wall segments from GridTruth")
    return walls


def generate_roof(grid_truth_path):
    """
    Generate roof slab from GridTruth building_envelope

    Args:
        grid_truth_path: Path to GridTruth.json

    Returns:
        dict: Roof object or None if envelope missing
    """
    try:
        with open(grid_truth_path) as f:
            grid_truth = json.load(f)
    except FileNotFoundError:
        return None

    envelope = grid_truth.get('building_envelope', {})
    if not envelope:
        return None

    x_min = envelope.get('x_min', 0.0)
    x_max = envelope.get('x_max', 11.2)
    y_min = envelope.get('y_min', 0.0)
    y_max = envelope.get('y_max', 8.5)
    height = envelope.get('height', 3.0)

    roof = {
        "name": "roof_main",
        "object_type": "roof_slab_flat_lod300",
        "position": [x_min, y_min, height],
        "dimensions": {
            "length": x_max - x_min,
            "width": y_max - y_min,
            "thickness": 0.15
        },
        "placed": False,
        "room": "structure",
        "phase": "1C_structure"
    }

    print(f"    ✅ Generated roof from GridTruth")
    return roof


def generate_floor_slab(grid_truth_path):
    """Generate floor slab from GridTruth building_envelope"""
    try:
        with open(grid_truth_path) as f:
            grid_truth = json.load(f)
    except FileNotFoundError:
        return None

    envelope = grid_truth.get('building_envelope', {})
    if not envelope:
        return None

    x_min = envelope.get('x_min', 0.0)
    x_max = envelope.get('x_max', 11.2)
    y_min = envelope.get('y_min', 0.0)
    y_max = envelope.get('y_max', 8.5)

    floor = {
        "name": "floor_slab_main",
        "object_type": "slab_6x4_150_lod300",
        "position": [x_min, y_min, 0.0],
        "dimensions": {
            "length": x_max - x_min,
            "width": y_max - y_min,
            "thickness": 0.15
        },
        "placed": False,
        "room": "structure",
        "phase": "1C_structure"
    }

    print(f"    ✅ Generated floor slab from GridTruth")
    return floor


def generate_ceiling(grid_truth_path):
    """Generate ceiling plane from GridTruth building_envelope"""
    try:
        with open(grid_truth_path) as f:
            grid_truth = json.load(f)
    except FileNotFoundError:
        return None

    envelope = grid_truth.get('building_envelope', {})
    if not envelope:
        return None

    x_min = envelope.get('x_min', 0.0)
    x_max = envelope.get('x_max', 11.2)
    y_min = envelope.get('y_min', 0.0)
    y_max = envelope.get('y_max', 8.5)
    height = envelope.get('height', 3.0)

    ceiling = {
        "name": "ceiling_main",
        "object_type": "ceiling_gypsum_lod300",
        "position": [x_min, y_min, height - 0.1],  # Just below roof
        "dimensions": {
            "length": x_max - x_min,
            "width": y_max - y_min,
            "thickness": 0.01
        },
        "placed": False,
        "room": "structure",
        "phase": "1C_structure"
    }

    print(f"    ✅ Generated ceiling from GridTruth")
    return ceiling


def generate_drains(grid_truth_path):
    """
    Generate discharge perimeter gutters from GridTruth building_envelope

    Args:
        grid_truth_path: Path to GridTruth.json

    Returns:
        list: Drain/gutter objects (4 perimeter segments)
    """
    try:
        with open(grid_truth_path) as f:
            grid_truth = json.load(f)
    except FileNotFoundError:
        return []

    envelope = grid_truth.get('building_envelope', {})
    if not envelope:
        return []

    x_min = envelope.get('x_min', 0.0)
    x_max = envelope.get('x_max', 11.2)
    y_min = envelope.get('y_min', 0.0)
    y_max = envelope.get('y_max', 8.5)
    height = envelope.get('height', 3.0)

    # Generate discharge perimeter (gutter around roof)
    perimeter_points = [
        # South edge
        ([x_min, y_min, height], [x_max, y_min, height]),
        # East edge
        ([x_max, y_min, height], [x_max, y_max, height]),
        # North edge
        ([x_max, y_max, height], [x_min, y_max, height]),
        # West edge
        ([x_min, y_max, height], [x_min, y_min, height])
    ]

    drains = []
    for i, (start, end) in enumerate(perimeter_points):
        drain = {
            "name": f"discharge_perimeter_{i+1}",
            "object_type": "roof_gutter_100_lod300",
            "position": start,
            "end_point": end,
            "placed": False,
            "room": "structure",
            "phase": "1B_calibration"
        }
        drains.append(drain)

    print(f"    ✅ Generated {len(drains)} discharge drains from GridTruth")
    return drains


def generate_doors(grid_truth_path, door_schedule=None):
    """
    Generate doors from GridTruth room_bounds following UBBL regulations

    UBBL Requirements:
    - Minimum door width: 750mm (main entrance 900mm preferred)
    - Door height: 2100mm (standard)
    - Placement: At room boundaries, prefer entry from corridor/circulation
    - Swing: Into room (away from corridor)

    Args:
        grid_truth_path: Path to GridTruth.json
        door_schedule: Optional door schedule data from PDF extraction

    Returns:
        list: Door objects with positions inferred from room boundaries
    """
    try:
        with open(grid_truth_path) as f:
            grid_truth = json.load(f)
    except FileNotFoundError:
        print(f"⚠️  GridTruth not found: {grid_truth_path}")
        return []

    room_bounds = grid_truth.get('room_bounds', {})
    if not room_bounds:
        print("⚠️  No room_bounds in GridTruth")
        return []

    doors = []
    door_counter = 1

    # Define door placement rules per room type (UBBL + Malaysian typology)
    room_door_rules = {
        'RUANG_TAMU': {'wall': 'south', 'offset': 0.5, 'type': 'D1', 'width': 0.9},  # Main entrance
        'DAPUR': {'wall': 'west', 'offset': 0.5, 'type': 'D2', 'width': 0.75},      # Kitchen from living
        'BILIK_UTAMA': {'wall': 'south', 'offset': 0.5, 'type': 'D2', 'width': 0.75},  # Master bedroom
        'BILIK_2': {'wall': 'south', 'offset': 0.5, 'type': 'D2', 'width': 0.75},   # Bedroom 2
        'BILIK_MANDI': {'wall': 'east', 'offset': 0.3, 'type': 'D3', 'width': 0.75},  # Bathroom 1
        'TANDAS': {'wall': 'east', 'offset': 0.3, 'type': 'D3', 'width': 0.75},     # Bathroom 2
        'RUANG_BASUH': {'wall': 'west', 'offset': 0.3, 'type': 'D3', 'width': 0.75},  # Utility
        'CORRIDOR': None  # Corridor has no door (circulation space)
    }

    for room_name, bounds in room_bounds.items():
        if room_name.startswith('_'):  # Skip metadata
            continue

        rule = room_door_rules.get(room_name)
        if not rule:  # No door for this room type
            continue

        x_min, x_max = bounds['x_min'], bounds['x_max']
        y_min, y_max = bounds['y_min'], bounds['y_max']

        # Calculate door position based on wall placement
        wall = rule['wall']
        offset = rule['offset']
        width = rule['width']

        if wall == 'south':  # Door on south wall (y_min)
            door_x = x_min + offset
            door_y = y_min
            orientation = 0.0  # Facing north (into room)
        elif wall == 'north':  # Door on north wall (y_max)
            door_x = x_min + offset
            door_y = y_max
            orientation = 180.0  # Facing south
        elif wall == 'west':  # Door on west wall (x_min)
            door_x = x_min
            door_y = y_min + offset
            orientation = 90.0  # Facing east
        elif wall == 'east':  # Door on east wall (x_max)
            door_x = x_max
            door_y = y_min + offset
            orientation = 270.0  # Facing west
        else:
            continue

        # Determine object_type from width (UBBL compliant)
        if width >= 0.9:
            object_type = "door_single_900_lod300"
        else:
            object_type = "door_single_750x2100_lod300"

        # Override from door_schedule if available
        door_label = rule['type']
        if door_schedule and isinstance(door_schedule, list):
            for sched_item in door_schedule:
                # Handle both string and dict formats
                if isinstance(sched_item, dict):
                    if sched_item.get('type') == door_label:
                        # Get dimensions from schedule
                        sched_width = sched_item.get('width', width)
                        if sched_width >= 0.9:
                            object_type = "door_single_900_lod300"
                        else:
                            object_type = "door_single_750x2100_lod300"
                        break
                # If sched_item is string, skip (can't extract dimensions)

        door = {
            "name": f"door_{room_name.lower()}",
            "object_type": object_type,
            "position": [door_x, door_y, 0.0],
            "orientation": orientation,
            "height": 2.1,  # UBBL standard door height
            "width": width,
            "placed": False,
            "room": room_name.lower(),
            "phase": "2_openings",
            "_generation_method": "gridtruth_inference",
            "_ubbl_compliant": True,
            "_label": door_label
        }
        doors.append(door)
        door_counter += 1

    print(f"    ✅ Generated {len(doors)} doors from GridTruth (UBBL compliant)")
    return doors


def generate_item(item, grid_truth_path, context=None):
    """
    Dispatcher - route to appropriate generator based on item type

    Args:
        item: Template item dict with object_type
        grid_truth_path: Path to GridTruth.json
        context: Optional extraction context (for door_schedule, etc.)

    Returns:
        list: Generated objects (empty if not supported)
    """
    object_type = item.get('object_type', '') or ''
    object_type_lower = object_type.lower()

    # Check detection_id for doors (object_type may be null)
    detection_id = item.get('detection_id', '')
    item_name = item.get('item', '').lower()

    if 'wall' in object_type_lower:
        return generate_walls(grid_truth_path)
    elif 'gutter' in object_type_lower or 'drain' in object_type_lower:
        # Check gutter/drain BEFORE roof (roof_gutter_100_lod300 contains 'roof')
        return generate_drains(grid_truth_path)
    elif 'slab' in object_type_lower or 'floor' in item_name:
        floor = generate_floor_slab(grid_truth_path)
        return [floor] if floor else []
    elif 'ceiling' in object_type_lower or 'ceiling' in item_name:
        ceiling = generate_ceiling(grid_truth_path)
        return [ceiling] if ceiling else []
    elif 'roof' in object_type_lower:
        roof = generate_roof(grid_truth_path)
        return [roof] if roof else []
    elif 'door' in item_name or detection_id == 'TEXT_LABEL_SEARCH':
        # Handle doors - use door_schedule from context if available
        door_schedule = None
        if context and isinstance(context, dict):
            door_schedule = context.get('door_schedule')
        return generate_doors(grid_truth_path, door_schedule)
    else:
        # Not a structural item we can generate from GridTruth
        return []
