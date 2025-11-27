#!/usr/bin/env python3
"""
Room Inference Engine - Detect rooms and infer contents

Architecture:
1. Detect room boundaries from walls
2. Classify room type (size, location, fixtures)
3. Infer mandatory objects for each room type
4. Place objects using smart defaults

This replaces text search with intelligent inference.
"""

import math


class RoomInferenceEngine:
    """
    Infer objects based on room detection and classification

    Instead of searching for text labels, we:
    1. Detect enclosed spaces (rooms)
    2. Classify room type
    3. Infer what MUST be in that room
    4. Place objects using smart defaults
    """

    def __init__(self, walls, building_dims):
        """
        Args:
            walls: List of wall segments
            building_dims: Building dimensions (length, breadth, height)
        """
        self.walls = walls
        self.building_dims = building_dims
        self.rooms = []

    def detect_rooms(self):
        """
        Detect enclosed spaces from wall boundaries

        Returns:
            list: Room polygons with boundaries
        """
        # Simplified room detection for POC
        # In production, this would use wall connectivity analysis

        # For now, divide building into typical residential zones
        length = self.building_dims['length']
        breadth = self.building_dims['breadth']

        # Typical single-story house layout
        rooms = [
            {
                'name': 'Master Bedroom',
                'type': 'bedroom',
                'subtype': 'master',
                'bounds': {
                    'min': [0, 0],
                    'max': [length * 0.4, breadth * 0.5]
                },
                'area': (length * 0.4) * (breadth * 0.5),
                'center': [length * 0.2, breadth * 0.25]
            },
            {
                'name': 'Bedroom 2',
                'type': 'bedroom',
                'subtype': 'secondary',
                'bounds': {
                    'min': [0, breadth * 0.5],
                    'max': [length * 0.4, breadth]
                },
                'area': (length * 0.4) * (breadth * 0.5),
                'center': [length * 0.2, breadth * 0.75]
            },
            {
                'name': 'Bathroom 1',
                'type': 'bathroom',
                'subtype': 'master_ensuite',
                'bounds': {
                    'min': [length * 0.4, 0],
                    'max': [length * 0.6, breadth * 0.3]
                },
                'area': (length * 0.2) * (breadth * 0.3),
                'center': [length * 0.5, breadth * 0.15]
            },
            {
                'name': 'Bathroom 2',
                'type': 'bathroom',
                'subtype': 'common',
                'bounds': {
                    'min': [length * 0.4, breadth * 0.7],
                    'max': [length * 0.6, breadth]
                },
                'area': (length * 0.2) * (breadth * 0.3),
                'center': [length * 0.5, breadth * 0.85]
            },
            {
                'name': 'Kitchen',
                'type': 'kitchen',
                'subtype': 'residential',
                'bounds': {
                    'min': [length * 0.6, breadth * 0.6],
                    'max': [length, breadth]
                },
                'area': (length * 0.4) * (breadth * 0.4),
                'center': [length * 0.8, breadth * 0.8]
            },
            {
                'name': 'Living Room',
                'type': 'living',
                'subtype': 'main',
                'bounds': {
                    'min': [length * 0.6, 0],
                    'max': [length, breadth * 0.6]
                },
                'area': (length * 0.4) * (breadth * 0.6),
                'center': [length * 0.8, breadth * 0.3]
            }
        ]

        self.rooms = rooms
        return rooms

    def infer_room_contents(self, room):
        """
        Infer mandatory and typical objects for a room type

        Args:
            room: Room dict with type and bounds

        Returns:
            list: Inferred objects with positions
        """
        room_type = room['type']
        subtype = room['subtype']
        center = room['center']
        bounds = room['bounds']

        objects = []

        if room_type == 'bedroom':
            # MANDATORY: bed, wardrobe
            if subtype == 'master':
                # Queen bed in master bedroom
                objects.append({
                    'name': f"{room['name']}_bed",
                    'object_type': 'bed_queen_lod300',
                    'position': [center[0], center[1], 0.0],
                    'orientation': 90.0,  # Against wall
                    'room': room['name'],
                    'placement_logic': 'center_of_room'
                })
                # Double wardrobe
                objects.append({
                    'name': f"{room['name']}_wardrobe",
                    'object_type': 'wardrobe_double_lod300',
                    'position': [bounds['max'][0] - 0.3, center[1], 0.0],
                    'orientation': 270.0,
                    'room': room['name'],
                    'placement_logic': 'against_wall'
                })
            else:
                # Single bed in secondary bedroom
                objects.append({
                    'name': f"{room['name']}_bed",
                    'object_type': 'bed_single_lod300',
                    'position': [center[0], center[1], 0.0],
                    'orientation': 90.0,
                    'room': room['name'],
                    'placement_logic': 'center_of_room'
                })
                # Single wardrobe
                objects.append({
                    'name': f"{room['name']}_wardrobe",
                    'object_type': 'wardrobe_single_lod300',
                    'position': [bounds['max'][0] - 0.3, center[1], 0.0],
                    'orientation': 270.0,
                    'room': room['name'],
                    'placement_logic': 'against_wall'
                })

        elif room_type == 'bathroom':
            # MANDATORY: toilet, basin, shower
            corner_x = bounds['min'][0] + 0.5
            corner_y = bounds['min'][1] + 0.5

            objects.append({
                'name': f"{room['name']}_toilet",
                'object_type': 'floor_mounted_toilet_lod300',
                'position': [corner_x, corner_y, 0.0],
                'orientation': 180.0,
                'room': room['name'],
                'placement_logic': 'corner_placement'
            })
            objects.append({
                'name': f"{room['name']}_basin",
                'object_type': 'basin_round_residential_lod300',
                'position': [corner_x + 0.8, corner_y, 0.0],
                'orientation': 180.0,
                'room': room['name'],
                'placement_logic': 'wall_mounted'
            })
            objects.append({
                'name': f"{room['name']}_showerhead",
                'object_type': 'showerhead_fixed_lod200',
                'position': [bounds['max'][0] - 0.5, corner_y, 1.8],
                'orientation': 0.0,
                'room': room['name'],
                'placement_logic': 'shower_corner'
            })
            objects.append({
                'name': f"{room['name']}_floor_drain",
                'object_type': 'floor_drain_lod200',
                'position': [bounds['max'][0] - 0.5, corner_y, 0.0],
                'orientation': 0.0,
                'room': room['name'],
                'placement_logic': 'shower_area'
            })

        elif room_type == 'kitchen':
            # MANDATORY: sink, stove, refrigerator
            # TYPICAL: cabinets

            # Kitchen sink against wall
            objects.append({
                'name': f"{room['name']}_sink",
                'object_type': 'kitchen_sink_single_bowl_with_drainboard_lod300',
                'position': [center[0], bounds['max'][1] - 0.3, 0.9],
                'orientation': 0.0,
                'room': room['name'],
                'placement_logic': 'counter_height_against_wall'
            })
            # Stove next to sink
            objects.append({
                'name': f"{room['name']}_stove",
                'object_type': 'stove_residential_lod200',
                'position': [center[0] + 1.0, bounds['max'][1] - 0.3, 0.9],
                'orientation': 0.0,
                'room': room['name'],
                'placement_logic': 'counter_height'
            })
            # Refrigerator in corner
            objects.append({
                'name': f"{room['name']}_refrigerator",
                'object_type': 'refrigerator_residential_lod200',
                'position': [bounds['max'][0] - 0.4, bounds['max'][1] - 0.4, 0.0],
                'orientation': 270.0,
                'room': room['name'],
                'placement_logic': 'corner_placement'
            })
            # Base cabinets
            objects.append({
                'name': f"{room['name']}_base_cabinet",
                'object_type': 'kitchen_base_cabinet_900_lod300',
                'position': [center[0] - 0.5, bounds['max'][1] - 0.3, 0.0],
                'orientation': 0.0,
                'room': room['name'],
                'placement_logic': 'under_counter'
            })

        elif room_type == 'living':
            # TYPICAL: sofa, TV, dining table, chairs

            objects.append({
                'name': f"{room['name']}_sofa",
                'object_type': 'sofa_3seater_lod300',
                'position': [center[0], center[1], 0.0],
                'orientation': 90.0,
                'room': room['name'],
                'placement_logic': 'center_facing_tv'
            })
            objects.append({
                'name': f"{room['name']}_tv_console",
                'object_type': 'tv_console_1500_lod300',
                'position': [bounds['max'][0] - 0.3, center[1], 0.0],
                'orientation': 270.0,
                'room': room['name'],
                'placement_logic': 'against_wall_facing_sofa'
            })
            objects.append({
                'name': f"{room['name']}_dining_table",
                'object_type': 'table_dining_1500x900_lod300',
                'position': [center[0], bounds['min'][1] + 1.5, 0.0],
                'orientation': 0.0,
                'room': room['name'],
                'placement_logic': 'dining_area'
            })

        return objects

    def infer_all_contents(self):
        """
        Infer contents for all detected rooms

        Returns:
            list: All inferred objects
        """
        if not self.rooms:
            self.detect_rooms()

        all_objects = []

        for room in self.rooms:
            room_objects = self.infer_room_contents(room)
            all_objects.extend(room_objects)

        return all_objects


def merge_wall_segments(walls, angle_tolerance=5.0, gap_tolerance=0.2):
    """
    Merge collinear and continuous wall segments into single walls

    Args:
        walls: List of wall dicts with start_point, end_point
        angle_tolerance: Maximum angle difference for collinearity (degrees)
        gap_tolerance: Maximum gap between segments (meters)

    Returns:
        list: Merged wall segments
    """
    if not walls:
        return []

    # Group walls by approximate angle (0°, 90°, 180°, 270°)
    grouped = {0: [], 90: [], 180: [], 270: []}

    for wall in walls:
        dx = wall['end_point'][0] - wall['start_point'][0]
        dy = wall['end_point'][1] - wall['start_point'][1]

        angle = math.degrees(math.atan2(dy, dx)) % 360

        # Find nearest cardinal direction
        if angle < 45 or angle >= 315:
            grouped[0].append(wall)
        elif 45 <= angle < 135:
            grouped[90].append(wall)
        elif 135 <= angle < 225:
            grouped[180].append(wall)
        else:
            grouped[270].append(wall)

    merged = []

    # Merge each group
    for angle, group in grouped.items():
        if not group:
            continue

        # Sort by position (x for vertical, y for horizontal)
        if angle in [0, 180]:  # Horizontal
            group.sort(key=lambda w: (w['start_point'][1], w['start_point'][0]))
        else:  # Vertical
            group.sort(key=lambda w: (w['start_point'][0], w['start_point'][1]))

        # Merge consecutive segments
        current = group[0].copy()

        for next_wall in group[1:]:
            # Check if continuous (endpoints close)
            dist = math.sqrt(
                (current['end_point'][0] - next_wall['start_point'][0])**2 +
                (current['end_point'][1] - next_wall['start_point'][1])**2
            )

            if dist < gap_tolerance:
                # Extend current wall
                current['end_point'] = next_wall['end_point']
            else:
                # Start new wall
                merged.append(current)
                current = next_wall.copy()

        merged.append(current)

    print(f"  Merged {len(walls)} wall segments → {len(merged)} continuous walls")
    return merged
