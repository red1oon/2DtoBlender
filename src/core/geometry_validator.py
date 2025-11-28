#!/usr/bin/env python3
"""
Geometry Validator - Validate extracted geometry for physical plausibility

Ensures walls and openings conform to Malaysian UBBL building standards.

Classes:
    GeometryValidator: Validates wall and opening geometry

Example:
    >>> validator = GeometryValidator(building_dims={'width': 9.8, 'length': 8.0})
    >>> warnings = validator.validate_wall(wall_dict)
    >>> warnings = validator.validate_opening(door_dict, opening_type='door')
"""

from typing import Dict, List, Tuple


class GeometryValidator:
    """
    Validate extracted geometry for physical plausibility

    Ensures walls and openings conform to building standards (Malaysian UBBL).
    Raises ValueError for critical issues, returns warnings for non-critical issues.

    Attributes:
        building_width (float): Building width in meters
        building_length (float): Building length in meters

    Methods:
        validate_wall(wall: Dict) -> List[str]
        validate_opening(opening: Dict, opening_type: str = 'door') -> List[str]
    """

    def __init__(self, building_dims: Dict[str, float]):
        """
        Initialize geometry validator

        Args:
            building_dims: Dictionary with 'width' and 'length' in meters
        """
        self.building_width = building_dims['width']
        self.building_length = building_dims['length']

    def validate_wall(self, wall: Dict) -> List[str]:
        """
        Validate wall geometry

        Checks:
        1. Minimum wall length (0.3m)
        2. Maximum wall length (1.5× building max dimension)
        3. Wall thickness range (50mm-500mm)
        4. Zero-length walls (start == end)
        5. Wall within building bounds

        Args:
            wall: Wall dict with start_point, end_point, length, thickness, wall_id

        Returns:
            list: Warning messages (non-critical issues)

        Raises:
            ValueError: If wall geometry is invalid (critical issue)
        """
        warnings = []

        # Check 1: Minimum wall length
        if wall['length'] < 0.3:
            raise ValueError(
                f"Wall {wall['wall_id']} too short: {wall['length']:.2f}m "
                f"(minimum 0.3m for structural wall)"
            )

        # Check 2: Maximum wall length (sanity check)
        max_length = max(self.building_width, self.building_length) * 1.5
        if wall['length'] > max_length:
            warnings.append(
                f"Wall {wall['wall_id']} unusually long: {wall['length']:.2f}m "
                f"(building max dimension: {max_length:.2f}m)"
            )

        # Check 3: Wall thickness range
        if wall['thickness'] < 0.05:
            raise ValueError(
                f"Wall {wall['wall_id']} too thin: {wall['thickness']:.2f}m "
                f"(minimum 50mm)"
            )
        if wall['thickness'] > 0.5:
            warnings.append(
                f"Wall {wall['wall_id']} very thick: {wall['thickness']:.2f}m "
                f"(typical: 100-200mm)"
            )

        # Check 4: Zero-length wall (start == end)
        dx = wall['end_point'][0] - wall['start_point'][0]
        dy = wall['end_point'][1] - wall['start_point'][1]
        if abs(dx) < 0.01 and abs(dy) < 0.01:
            raise ValueError(
                f"Wall {wall['wall_id']} has zero length (start == end point)"
            )

        # Check 5: Wall within building bounds
        for point in [wall['start_point'], wall['end_point']]:
            if not self._point_in_bounds(point):
                warnings.append(
                    f"Wall {wall['wall_id']} extends outside building bounds: "
                    f"({point[0]:.2f}, {point[1]:.2f})"
                )

        return warnings

    def validate_opening(self, opening: Dict, opening_type: str = 'door') -> List[str]:
        """
        Validate door/window dimensions

        Validates against Malaysian UBBL standards:
        - Doors: 600-1200mm width, 2000-2400mm height
        - Windows: 300-3000mm width, 300-2000mm height

        Args:
            opening: Opening dict with width, height, position
            opening_type: 'door' or 'window'

        Returns:
            list: Warning messages

        Raises:
            ValueError: If opening dimensions are invalid
        """
        warnings = []

        # Typical ranges (Malaysian UBBL standards)
        if opening_type == 'door':
            min_width, max_width = 0.6, 1.2  # 600mm to 1200mm
            min_height, max_height = 2.0, 2.4  # 2000mm to 2400mm
        else:  # window
            min_width, max_width = 0.3, 3.0  # 300mm to 3000mm
            min_height, max_height = 0.3, 2.0  # 300mm to 2000mm

        # Check width
        if opening['width'] < min_width:
            raise ValueError(
                f"{opening_type.title()} {opening.get('door_type', opening.get('window_type'))} "
                f"too narrow: {opening['width']:.2f}m (min: {min_width}m)"
            )
        if opening['width'] > max_width:
            warnings.append(
                f"{opening_type.title()} {opening.get('door_type', opening.get('window_type'))} "
                f"very wide: {opening['width']:.2f}m (typical max: {max_width}m)"
            )

        # Check height
        if opening['height'] < min_height:
            warnings.append(
                f"{opening_type.title()} height unusually low: {opening['height']:.2f}m"
            )
        if opening['height'] > max_height:
            warnings.append(
                f"{opening_type.title()} height unusually high: {opening['height']:.2f}m"
            )

        # Check position
        pos = opening['position']
        if not self._point_in_bounds(pos):
            warnings.append(
                f"{opening_type.title()} position outside building: "
                f"({pos[0]:.2f}, {pos[1]:.2f})"
            )

        return warnings

    def _point_in_bounds(self, point: Tuple[float, float], margin: float = 1.0) -> bool:
        """
        Check if point is within building bounds with margin

        Args:
            point: (x, y) coordinates in meters
            margin: Margin in meters (default: 1.0m)

        Returns:
            bool: True if point within bounds
        """
        x, y = point[0], point[1]
        return (
            -margin <= x <= self.building_width + margin and
            -margin <= y <= self.building_length + margin
        )
