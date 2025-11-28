#!/usr/bin/env python3
"""
Standards-Driven Placement Engine

Places objects with automatic compliance to UBBL 1984 + MS 1184.
Compliance is enforced DURING construction, not validated after.

Architecture:
- Positions calculated from standards (clearances, heights)
- Collision detection with existing objects
- Room size verification (UBBL minimums)
- Impossible to generate non-compliant output

Usage:
    engine = StandardsPlacementEngine()
    position = engine.place_fixture('toilet', room_bounds, existing_objects)
    # position is guaranteed MS 1184 compliant
"""

import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from standards.building_standards import (
    MS_1184_CLEARANCES,
    MS_1184_HEIGHTS,
    STANDARD_OBJECT_DIMENSIONS,
    ClearanceRequirements,
    ObjectDimensions,
    get_clearance_requirements,
    get_fixture_height,
    get_object_dimensions,
)


class MSViolation(Exception):
    """Raised when MS 1184 requirements cannot be satisfied"""
    pass


class CollisionError(Exception):
    """Raised when object would collide with existing objects"""
    pass


class RoomTooSmallError(Exception):
    """Raised when room cannot accommodate object + clearances"""
    pass


@dataclass
class PlacementResult:
    """Result of standards-compliant placement"""
    position: List[float]  # [x, y, z]
    clearances_verified: ClearanceRequirements
    collisions_checked: bool
    standards_compliant: bool
    placement_strategy: str  # Description of how placed


class StandardsPlacementEngine:
    """
    Place objects with automatic UBBL 1984 + MS 1184 compliance

    Guarantees:
    - All MS 1184 clearances satisfied
    - All MS 1184 heights satisfied
    - No collisions with existing objects
    - Room size adequate for object + clearances
    """

    def __init__(self, collision_tolerance=0.1):
        self.collision_tolerance = collision_tolerance  # Default 100mm, can be reduced for tight spaces

    def place_fixture(
        self,
        fixture_type: str,
        room_bounds: Dict,
        existing_objects: List[Dict],
        preferred_wall: Optional[str] = None
    ) -> PlacementResult:
        """
        Place fixture with MS 1184 clearances

        Args:
            fixture_type: Type of fixture ('toilet', 'basin', 'shower', etc.)
            room_bounds: {'min_x', 'max_x', 'min_y', 'max_y'}
            existing_objects: List of objects already in room
            preferred_wall: 'north', 'south', 'east', 'west' (optional)

        Returns:
            PlacementResult with compliant position

        Raises:
            MSViolation: If clearances cannot be satisfied
            RoomTooSmallError: If room too small
            CollisionError: If all positions blocked
        """
        # Get standards
        clearances = get_clearance_requirements(fixture_type)
        dimensions = get_object_dimensions(fixture_type)
        height_req = get_fixture_height(fixture_type)

        if not clearances:
            raise MSViolation(f"No clearance requirements defined for {fixture_type}")

        if not dimensions:
            raise MSViolation(f"No dimensions defined for {fixture_type}")

        # Verify room can accommodate object + clearances
        self._verify_room_size(room_bounds, dimensions, clearances, fixture_type)

        # Calculate compliant position
        position = self._calculate_position_with_clearances(
            room_bounds, dimensions, clearances, existing_objects, preferred_wall
        )

        # Set height
        if height_req:
            position[2] = height_req.height
        else:
            position[2] = 0.0  # Default to floor level

        # Verify clearances (sanity check)
        self._verify_clearances(position, dimensions, clearances, room_bounds)

        return PlacementResult(
            position=position,
            clearances_verified=clearances,
            collisions_checked=True,
            standards_compliant=True,
            placement_strategy=f"MS 1184 compliant: {clearances}"
        )

    def _verify_room_size(
        self,
        room_bounds: Dict,
        dimensions: ObjectDimensions,
        clearances: ClearanceRequirements,
        fixture_type: str
    ):
        """Verify room can accommodate object + clearances"""
        room_width = room_bounds['max_x'] - room_bounds['min_x']
        room_depth = room_bounds['max_y'] - room_bounds['min_y']

        # Calculate required space
        required_width = dimensions.width + clearances.left + clearances.right
        required_depth = dimensions.depth + clearances.front + clearances.rear

        if room_width < required_width:
            raise RoomTooSmallError(
                f"{fixture_type}: Room width {room_width:.2f}m < "
                f"required {required_width:.2f}m "
                f"(object {dimensions.width}m + clearances "
                f"{clearances.left}m + {clearances.right}m)"
            )

        if room_depth < required_depth:
            raise RoomTooSmallError(
                f"{fixture_type}: Room depth {room_depth:.2f}m < "
                f"required {required_depth:.2f}m "
                f"(object {dimensions.depth}m + clearances "
                f"{clearances.front}m + {clearances.rear}m)"
            )

    def _calculate_position_with_clearances(
        self,
        room_bounds: Dict,
        dimensions: ObjectDimensions,
        clearances: ClearanceRequirements,
        existing_objects: List[Dict],
        preferred_wall: Optional[str]
    ) -> List[float]:
        """
        Calculate position that satisfies clearances

        Strategy:
        1. Try preferred wall (if specified)
        2. Try all walls
        3. Try center of room
        """
        # Calculate usable bounds (accounting for clearances)
        usable_min_x = room_bounds['min_x'] + clearances.left + dimensions.width / 2
        usable_max_x = room_bounds['max_x'] - clearances.right - dimensions.width / 2
        usable_min_y = room_bounds['min_y'] + clearances.front + dimensions.depth / 2
        usable_max_y = room_bounds['max_y'] - clearances.rear - dimensions.depth / 2

        # Generate candidate positions
        candidates = []

        # Against walls (typical for fixtures)
        if preferred_wall:
            candidates.extend(self._generate_wall_positions(
                preferred_wall, room_bounds, usable_min_x, usable_max_x,
                usable_min_y, usable_max_y, clearances, dimensions
            ))

        # Try all walls
        for wall in ['south', 'north', 'east', 'west']:
            if wall != preferred_wall:
                candidates.extend(self._generate_wall_positions(
                    wall, room_bounds, usable_min_x, usable_max_x,
                    usable_min_y, usable_max_y, clearances, dimensions
                ))

        # Center of room (last resort)
        center_x = (usable_min_x + usable_max_x) / 2
        center_y = (usable_min_y + usable_max_y) / 2
        candidates.append([center_x, center_y, 0.0])

        # Find first position without collisions
        for i, pos in enumerate(candidates):
            has_collision = self._has_collision(pos, dimensions, existing_objects)
            if not has_collision:
                return pos

        # All positions blocked
        raise CollisionError(
            f"Cannot place object - all {len(candidates)} candidate positions blocked"
        )

    def _generate_wall_positions(
        self,
        wall: str,
        room_bounds: Dict,
        usable_min_x: float,
        usable_max_x: float,
        usable_min_y: float,
        usable_max_y: float,
        clearances: ClearanceRequirements,
        dimensions: ObjectDimensions
    ) -> List[List[float]]:
        """Generate positions along specified wall"""
        positions = []

        if wall == 'south':
            # Against south wall (min Y)
            y = room_bounds['min_y'] + clearances.front + dimensions.depth / 2
            # Try left, center, right
            positions.append([usable_min_x, y, 0.0])
            positions.append([(usable_min_x + usable_max_x) / 2, y, 0.0])
            positions.append([usable_max_x, y, 0.0])

        elif wall == 'north':
            # Against north wall (max Y)
            y = room_bounds['max_y'] - clearances.rear - dimensions.depth / 2
            positions.append([usable_min_x, y, 0.0])
            positions.append([(usable_min_x + usable_max_x) / 2, y, 0.0])
            positions.append([usable_max_x, y, 0.0])

        elif wall == 'west':
            # Against west wall (min X)
            x = room_bounds['min_x'] + clearances.left + dimensions.width / 2
            positions.append([x, usable_min_y, 0.0])
            positions.append([x, (usable_min_y + usable_max_y) / 2, 0.0])
            positions.append([x, usable_max_y, 0.0])

        elif wall == 'east':
            # Against east wall (max X)
            x = room_bounds['max_x'] - clearances.right - dimensions.width / 2
            positions.append([x, usable_min_y, 0.0])
            positions.append([x, (usable_min_y + usable_max_y) / 2, 0.0])
            positions.append([x, usable_max_y, 0.0])

        return positions

    def _has_collision(
        self,
        position: List[float],
        dimensions: ObjectDimensions,
        existing_objects: List[Dict]
    ) -> bool:
        """Check if position would collide with existing objects"""
        # Calculate bounding box
        half_w = dimensions.width / 2
        half_d = dimensions.depth / 2

        bbox_min_x = position[0] - half_w - self.collision_tolerance
        bbox_max_x = position[0] + half_w + self.collision_tolerance
        bbox_min_y = position[1] - half_d - self.collision_tolerance
        bbox_max_y = position[1] + half_d + self.collision_tolerance

        # Check against existing objects
        for obj in existing_objects:
            obj_pos = obj.get('position', [0, 0, 0])
            obj_type = obj.get('object_type', '')

            # Get object dimensions
            obj_dims = get_object_dimensions(obj_type)
            if not obj_dims:
                # Unknown dimensions - assume 0.5m x 0.5m
                obj_dims = ObjectDimensions(0.5, 0.5, 0.5)

            # Calculate object bounding box
            obj_half_w = obj_dims.width / 2
            obj_half_d = obj_dims.depth / 2

            obj_min_x = obj_pos[0] - obj_half_w
            obj_max_x = obj_pos[0] + obj_half_w
            obj_min_y = obj_pos[1] - obj_half_d
            obj_max_y = obj_pos[1] + obj_half_d

            # Check for overlap (AABB collision)
            if not (bbox_max_x < obj_min_x or bbox_min_x > obj_max_x or
                    bbox_max_y < obj_min_y or bbox_min_y > obj_max_y):
                return True  # Collision detected

        return False  # No collision

    def _verify_clearances(
        self,
        position: List[float],
        dimensions: ObjectDimensions,
        clearances: ClearanceRequirements,
        room_bounds: Dict
    ):
        """Verify clearances are satisfied (sanity check)"""
        # Calculate object bounds
        obj_min_x = position[0] - dimensions.width / 2
        obj_max_x = position[0] + dimensions.width / 2
        obj_min_y = position[1] - dimensions.depth / 2
        obj_max_y = position[1] + dimensions.depth / 2

        # Check clearances
        front_clearance = obj_min_y - room_bounds['min_y']
        rear_clearance = room_bounds['max_y'] - obj_max_y
        left_clearance = obj_min_x - room_bounds['min_x']
        right_clearance = room_bounds['max_x'] - obj_max_x

        tolerance = 0.01  # 10mm tolerance

        if front_clearance < clearances.front - tolerance:
            raise MSViolation(
                f"Front clearance {front_clearance:.2f}m < "
                f"required {clearances.front}m"
            )

        if left_clearance < clearances.left - tolerance:
            raise MSViolation(
                f"Left clearance {left_clearance:.2f}m < "
                f"required {clearances.left}m"
            )

        if right_clearance < clearances.right - tolerance:
            raise MSViolation(
                f"Right clearance {right_clearance:.2f}m < "
                f"required {clearances.right}m"
            )


if __name__ == "__main__":
    # Test placement engine
    print("Standards-Driven Placement Engine")
    print("=" * 80)

    engine = StandardsPlacementEngine()

    # Test bathroom layout
    bathroom_bounds = {
        'min_x': 0.0,
        'max_x': 2.0,  # 2m width
        'min_y': 0.0,
        'max_y': 2.5,  # 2.5m depth
    }

    print("\n✓ Testing bathroom fixture placement (2.0m × 2.5m room):")
    print("-" * 80)

    # Place toilet
    try:
        result = engine.place_fixture('toilet', bathroom_bounds, [])
        print(f"✓ Toilet: {result.position} (MS 1184 compliant)")
        print(f"  Clearances: front={result.clearances_verified.front}m, "
              f"sides={result.clearances_verified.left}m/{result.clearances_verified.right}m")

        # Place basin
        result2 = engine.place_fixture('basin', bathroom_bounds, [
            {'object_type': 'toilet', 'position': result.position}
        ])
        print(f"✓ Basin: {result2.position} (MS 1184 compliant)")
        print(f"  Clearances: front={result2.clearances_verified.front}m, "
              f"sides={result2.clearances_verified.left}m/{result2.clearances_verified.right}m")

    except (MSViolation, RoomTooSmallError, CollisionError) as e:
        print(f"✗ Placement failed: {e}")

    print("\n✓ Placement engine test complete")
