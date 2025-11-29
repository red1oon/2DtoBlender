#!/usr/bin/env python3
"""
GridTruth Fallback Generator

Generates structural elements from GridTruth.json when PDF extraction fails.
Used by extraction_engine.py as fallback for mandatory template items.

Architecture:
- GridTruthGenerator: Abstract generator (config-driven, no hardcoded types)
- Legacy functions: Hardcoded generators (generate_walls, etc.) - kept for compatibility

The abstract generator interprets placement rules from template:
- placement_zone: where (envelope, envelope_front, room:NAME, etc.)
- height_rule: Z position (ground, ffl, ceiling, door_head, etc.)
- extent_rule: size (full_envelope, parametric, room_bounds)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union


class GridTruthGenerator:
    """
    Abstract generator - creates any element from template + GridTruth.
    No hardcoded item types - purely config-driven.

    Usage:
        generator = GridTruthGenerator(grid_truth_path)
        result = generator.generate(template_item)
    """

    def __init__(self, grid_truth_path: str = None, annotation_db_path: str = None):
        """
        Initialize generator with spatial data

        Args:
            grid_truth_path: Path to GridTruth.json (DEPRECATED - for compatibility)
            annotation_db_path: Path to annotations DB (preferred)
        """
        if annotation_db_path:
            # Rule 0 compliant: derive from extracted annotations
            from src.core.annotation_derivation import (
                derive_building_envelope,
                derive_elevations,
                derive_room_bounds
            )
            self.envelope = derive_building_envelope(annotation_db_path)
            self.elevations = derive_elevations(annotation_db_path)
            self.rooms = derive_room_bounds(annotation_db_path)

        elif grid_truth_path:
            # Legacy: load from manual GridTruth.json
            with open(grid_truth_path) as f:
                self.gt = json.load(f)
            self.envelope = self.gt.get('building_envelope', {})
            self.elevations = self.gt.get('elevations', {})
            self.rooms = self.gt.get('room_bounds', {})

        else:
            raise ValueError("Must provide either annotation_db_path or grid_truth_path")

    def generate(self, item: dict) -> Optional[Union[dict, List[dict]]]:
        """
        Generate element based on template item definition

        Args:
            item: Template item with placement_zone, height_rule, extent_rule

        Returns:
            Generated object(s) or None if cannot generate
        """
        placement = item.get('placement_zone', 'envelope')
        height_rule = item.get('height_rule', 'ground')
        extent_rule = item.get('extent_rule', 'parametric')

        # Handle perimeter elements (return list of 4 segments)
        if placement == 'envelope_perimeter':
            return self._generate_perimeter(item, height_rule)

        # Single element (roof, floor, porch, etc.)
        bounds = self._get_bounds(placement, item)
        if not bounds:
            return None

        z = self._get_height(height_rule)
        return self._create_element(item, bounds, z, extent_rule)

    def _get_bounds(self, placement: str, item: dict) -> Optional[dict]:
        """
        Resolve placement zone to actual bounds

        Args:
            placement: Placement zone name (envelope, envelope_front, room:NAME)
            item: Template item (for parametric overrides)

        Returns:
            dict with x_min, x_max, y_min, y_max or None
        """
        if placement == 'envelope':
            return self.envelope

        elif placement == 'envelope_front':
            # Front edge (south) - reduced depth for porch canopy
            depth = item.get('parametric_defaults', {}).get('depth', 1.2)
            return {
                'x_min': self.envelope['x_min'],
                'x_max': self.envelope['x_max'],
                'y_min': self.envelope['y_min'],
                'y_max': self.envelope['y_min'] + depth
            }

        elif placement.startswith('room:'):
            room_name = placement.split(':', 1)[1]
            return self.rooms.get(room_name)

        else:
            return self.envelope

    def _get_height(self, rule: str) -> float:
        """
        Resolve height rule to Z coordinate

        Args:
            rule: Height rule name (ground, ffl, ceiling, door_head, etc.)

        Returns:
            Z coordinate in meters
        """
        heights = {
            'ground': 0.0,
            'ffl': self.elevations.get('floor_finish_level', 0.15),
            'ceiling': self.elevations.get('ceiling', 3.0),
            'door_head': self.elevations.get('door_head', 2.1),
            'roof_top': self.elevations.get('ceiling', 3.0) + 0.5,
        }
        return heights.get(rule, 0.0)

    def _generate_perimeter(self, item: dict, height_rule: str) -> List[dict]:
        """
        Generate 4 perimeter segments (for gutters, drains, etc.)

        Args:
            item: Template item
            height_rule: Height rule for Z position

        Returns:
            List of 4 segment objects
        """
        z = self._get_height(height_rule)
        x_min = self.envelope['x_min']
        x_max = self.envelope['x_max']
        y_min = self.envelope['y_min']
        y_max = self.envelope['y_max']

        segments = [
            # South edge
            {'start': [x_min, y_min, z], 'end': [x_max, y_min, z], 'edge': 'south'},
            # East edge
            {'start': [x_max, y_min, z], 'end': [x_max, y_max, z], 'edge': 'east'},
            # North edge
            {'start': [x_max, y_max, z], 'end': [x_min, y_max, z], 'edge': 'north'},
            # West edge
            {'start': [x_min, y_max, z], 'end': [x_min, y_min, z], 'edge': 'west'}
        ]

        objects = []
        for i, seg in enumerate(segments):
            obj = {
                'name': f"{item.get('item', 'perimeter').lower().replace(' ', '_')}_{i+1}",
                'object_type': item.get('object_type'),
                'position': seg['start'],
                'end_point': seg['end'],
                'placed': False,
                'room': 'structure',
                'phase': item.get('_phase', 'unknown'),
                'generated_from': 'gridtruth_abstract'
            }
            objects.append(obj)

        return objects

    def _create_element(self, item: dict, bounds: dict, z: float, extent_rule: str) -> dict:
        """
        Create element dict from resolved parameters

        Args:
            item: Template item
            bounds: Resolved bounds (x_min, x_max, y_min, y_max)
            z: Z coordinate
            extent_rule: Extent rule (full_envelope, parametric, etc.)

        Returns:
            Generated object dict
        """
        x_min = bounds['x_min']
        x_max = bounds['x_max']
        y_min = bounds['y_min']
        y_max = bounds['y_max']

        # Calculate dimensions based on extent rule
        if extent_rule == 'full_envelope':
            width = x_max - x_min
            depth = y_max - y_min
        elif extent_rule == 'parametric':
            defaults = item.get('parametric_defaults', {})
            width = defaults.get('width', x_max - x_min)
            depth = defaults.get('depth', y_max - y_min)
        else:
            width = x_max - x_min
            depth = y_max - y_min

        # For centered elements (like porch canopy), calculate center position
        if item.get('centered', False):
            center_x = (x_min + x_max) / 2
            center_y = (y_min + y_max) / 2
            position = [center_x - width/2, center_y - depth/2, z]
        else:
            position = [x_min, y_min, z]

        return {
            'name': item.get('item', 'generated_element').lower().replace(' ', '_'),
            'object_type': item.get('object_type'),
            'position': position,
            'dimensions': {
                'width': width,
                'depth': depth,
                'thickness': item.get('parametric_defaults', {}).get('thickness', 0.15)
            },
            'placed': False,
            'room': item.get('default_room', 'structure'),
            'phase': item.get('_phase', 'unknown'),
            'generated_from': 'gridtruth_abstract',
            'mandatory': item.get('mandatory', True)
        }


def generate_walls(annotation_db_path: str):
    """
    Generate wall segments from spatial data

    Args:
        annotation_db_path: Path to annotations DB (Rule 0 compliant)

    Returns:
        list: Wall objects with position, end_point, thickness
    """
    # Get room bounds from annotation DB derivation
    from src.core.annotation_derivation import derive_room_bounds
    room_bounds = derive_room_bounds(annotation_db_path)

    if not room_bounds:
        print("    ⚠️  No room bounds derived - cannot generate walls")
        return []

    if not room_bounds:
        print("⚠️  No room_bounds in spatial data")
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


def generate_roof(annotation_db_path: str):
    """
    Generate roof slab from spatial data

    Args:
        annotation_db_path: Path to annotations DB (Rule 0 compliant)

    Returns:
        dict: Roof object or None if envelope missing
    """
    # Get building envelope from annotation DB
    from src.core.annotation_derivation import derive_building_envelope
    envelope = derive_building_envelope(annotation_db_path)

    if not envelope:
        return None

    if not envelope:
        return None

    x_min = envelope['x_min']
    x_max = envelope['x_max']
    y_min = envelope['y_min']
    y_max = envelope['y_max']
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


def generate_floor_slab(annotation_db_path: str):
    """Generate floor slab from spatial data"""
    # Get building envelope from annotation DB
    from src.core.annotation_derivation import derive_building_envelope
    envelope = derive_building_envelope(annotation_db_path)

    if not envelope:
        return None

    if not envelope:
        return None

    x_min = envelope['x_min']
    x_max = envelope['x_max']
    y_min = envelope['y_min']
    y_max = envelope['y_max']

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


def generate_ceiling(annotation_db_path: str):
    """Generate ceiling plane from spatial data"""
    # Get building envelope from annotation DB
    from src.core.annotation_derivation import derive_building_envelope
    envelope = derive_building_envelope(annotation_db_path)

    if not envelope:
        return None

    x_min = envelope['x_min']
    x_max = envelope['x_max']
    y_min = envelope['y_min']
    y_max = envelope['y_max']
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


def generate_drains(annotation_db_path: str):
    """
    Generate discharge perimeter gutters from spatial data

    Args:
        annotation_db_path: Path to annotations DB (Rule 0 compliant)

    Returns:
        list: Drain/gutter objects (4 perimeter segments)
    """
    # Get building envelope from annotation DB
    from src.core.annotation_derivation import derive_building_envelope
    envelope = derive_building_envelope(annotation_db_path)

    if not envelope:
        return []

    x_min = envelope['x_min']
    x_max = envelope['x_max']
    y_min = envelope['y_min']
    y_max = envelope['y_max']
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


def generate_doors(annotation_db_path: str, door_schedule=None):
    """
    Generate doors from spatial data following UBBL regulations

    UBBL Requirements:
    - Minimum door width: 750mm (main entrance 900mm preferred)
    - Door height: 2100mm (standard)
    - Placement: At room boundaries, prefer entry from corridor/circulation
    - Swing: Into room (away from corridor)

    Args:
        annotation_db_path: Path to annotations DB (Rule 0 compliant)
        door_schedule: Optional door schedule data from PDF extraction

    Returns:
        list: Door objects with positions inferred from room boundaries
    """
    # Get room bounds from annotation DB
    from src.core.annotation_derivation import derive_room_bounds
    room_bounds = derive_room_bounds(annotation_db_path)

    if not room_bounds:
        print("    ⚠️  No room bounds derived - cannot generate doors")
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


def generate_item(item, annotation_db_path: str, context=None):
    """
    Dispatcher - route to appropriate generator based on item type

    Strategy:
    1. If item has placement_zone: Use abstract generator (NEW)
    2. Else: Use legacy hardcoded generators (BACKWARD COMPATIBLE)

    Args:
        item: Template item dict with object_type
        annotation_db_path: Path to annotations DB (Rule 0 compliant)
        context: Optional extraction context (for door_schedule, etc.)

    Returns:
        list: Generated objects (empty if not supported)
    """
    # NEW: Abstract generator (config-driven)
    if 'placement_zone' in item:
        try:
            generator = GridTruthGenerator(annotation_db_path=annotation_db_path)
            result = generator.generate(item)
            if result:
                # Ensure result is always a list
                if isinstance(result, dict):
                    return [result]
                return result
        except Exception as e:
            print(f"    ⚠️  Abstract generator failed: {e}")
            # Fall through to legacy generators

    # LEGACY: Hardcoded generators (annotation DB only)
    object_type = item.get('object_type', '') or ''
    object_type_lower = object_type.lower()
    detection_id = item.get('detection_id', '')
    item_name = item.get('item', '').lower()

    if 'wall' in object_type_lower:
        return generate_walls(annotation_db_path)
    elif 'gutter' in object_type_lower or 'drain' in object_type_lower:
        return generate_drains(annotation_db_path)
    elif 'slab' in object_type_lower or 'floor' in item_name:
        floor = generate_floor_slab(annotation_db_path)
        return [floor] if floor else []
    elif 'ceiling' in object_type_lower or 'ceiling' in item_name:
        ceiling = generate_ceiling(annotation_db_path)
        return [ceiling] if ceiling else []
    elif 'roof' in object_type_lower:
        roof = generate_roof(annotation_db_path)
        return [roof] if roof else []
    elif 'door' in item_name:
        # Handle doors - use door_schedule from context if available
        door_schedule = None
        if context and isinstance(context, dict):
            door_schedule = context.get('door_schedule')
        return generate_doors(annotation_db_path, door_schedule)
    elif 'window' in item_name:
        # Windows not yet implemented
        print(f"    ⚠️  Window generation not yet implemented")
        return []
    else:
        # Not a structural item we can generate
        return []
