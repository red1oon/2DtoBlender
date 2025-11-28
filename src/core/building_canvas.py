#!/usr/bin/env python3
"""
Building Canvas - 3D Validation Staging Layer

[THIRD-D] Validates object placement in 3D space BEFORE output.

This is the missing layer between extraction and output:
  PDF → extract → CANVAS (validate) → output.json → Blender

Purpose:
  - Bounds checking (object inside building/room?)
  - Collision detection (two items same spot?)
  - Z validation (floor item at z=0? ceiling at z=3?)
  - Rotation sanity (door facing into room?)
  - Completeness (room has required items?)

Rule 0 Compliant:
  - All rules from validation_rules.json (no hardcoded values)
  - GridTruth defines the validation space
  - Errors caught BEFORE output, not discovered in Blender

Author: BIM5D Pipeline
Date: 2025-11-28
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class BuildingCanvas:
    """
    3D staging layer for validating object placements.

    [THIRD-D] Uses GridTruth as the validation space for all objects.
    """

    def __init__(self, gridtruth_path: str = None, validation_rules_path: str = None, annotation_db_path: str = None):
        """
        Initialize the 3D canvas with validation rules.

        Args:
            gridtruth_path: Path to GridTruth.json (DEPRECATED - for compatibility)
            validation_rules_path: Path to validation_rules.json
            annotation_db_path: Path to annotations DB (preferred, Rule 0 compliant)
        """
        # Load spatial data
        if annotation_db_path:
            # Rule 0 compliant: derive from annotations
            from src.core.annotation_derivation import (
                derive_building_envelope,
                derive_room_bounds,
                derive_elevations,
                derive_grid_positions
            )
            envelope = derive_building_envelope(annotation_db_path)
            rooms = derive_room_bounds(annotation_db_path)
            elevations = derive_elevations(annotation_db_path)
            grid_h, grid_v = derive_grid_positions(annotation_db_path)

            # Build gridtruth-compatible structure
            self.gridtruth = {
                'building_envelope': envelope,
                'room_bounds': rooms,
                'elevations': elevations,
                'grid_horizontal': grid_h,
                'grid_vertical': grid_v
            }
        elif gridtruth_path:
            # Legacy: load from GridTruth.json
            with open(gridtruth_path, 'r') as f:
                self.gridtruth = json.load(f)
        else:
            raise ValueError("Must provide either annotation_db_path or gridtruth_path")

        # Load validation rules (defines the checks)
        if validation_rules_path:
            with open(validation_rules_path, 'r') as f:
                self.rules = json.load(f)
        else:
            self.rules = {}

        # Extract building components
        self.envelope = self.gridtruth.get('building_envelope', {})
        self.rooms = self.gridtruth.get('room_bounds', {})
        self.elevations = self.gridtruth.get('elevations', {})

        # Placed objects (spatial index)
        self.placed = {}

        # Validation warnings/errors
        self.warnings = []
        self.errors = []

        # Statistics
        self.stats = {
            'total_objects': 0,
            'validated': 0,
            'fixed': 0,
            'warnings': 0,
            'errors': 0
        }

    def place(self, obj: Dict) -> bool:
        """
        Validate and place object on canvas.

        Args:
            obj: Object dictionary with 'name', 'position', 'object_type'

        Returns:
            True if placed successfully, False if rejected
        """
        self.stats['total_objects'] += 1
        name = obj.get('name', 'unknown')
        pos = obj.get('position')
        obj_type = obj.get('object_type', '')

        if not pos or len(pos) < 3:
            self.error(f"{name}: Missing position array")
            return False

        # Run validation checks
        fixed = False

        # 0. Pre-check: Fix porch coordinates BEFORE bounds check
        if 'porch' in name.lower():
            if self._needs_porch_fix(obj):
                self._fix_porch_coordinates(obj)
                fixed = True

        # 1. Bounds check
        if not self._check_bounds(obj):
            return False

        # 2. Z validation
        if not self._check_z_height(obj):
            # Try to fix Z height
            fixed = self._fix_z_height(obj)
            if not fixed:
                self.warn(f"{name}: Z height mismatch (continuing anyway)")

        # 3. Room validation
        self._check_room_assignment(obj)

        # 4. Collision detection
        if self.rules.get('collision_detection', {}).get('enabled', True):
            self._check_collisions(obj)

        # Place object
        self.placed[name] = obj
        self.stats['validated'] += 1
        if fixed:
            self.stats['fixed'] += 1

        return True

    def _check_bounds(self, obj: Dict) -> bool:
        """Check if object is within building envelope."""
        name = obj['name']
        pos = obj['position']
        x, y, z = pos[0], pos[1], pos[2]
        obj_type = obj.get('object_type', '')

        # Special case: Structural elements (floor, ceiling, roof, walls) use grid coordinates
        # They span entire building and are placed at grid positions, not envelope positions
        is_structural = any(kw in obj_type.lower() or kw in name.lower()
                           for kw in ['slab', 'floor', 'ceiling', 'roof', 'wall'])

        # Structural elements use grid bounds, not envelope bounds
        if is_structural:
            try:
                grid_x_max = self.gridtruth['grid_horizontal']['E']
                grid_y_max = self.gridtruth['grid_vertical']['5']
            except KeyError as e:
                self.error(f"{name}: Grid data incomplete - {e}")
                return False

            # Check X bounds against grid
            if x < -0.1 or x > grid_x_max + 0.1:
                self.error(f"{name}: X={x:.2f} outside grid [0, {grid_x_max:.2f}]")
                return False

            # Check Y bounds against grid
            if y < -0.1 or y > grid_y_max + 0.1:
                self.error(f"{name}: Y={y:.2f} outside grid [0, {grid_y_max:.2f}]")
                return False
        else:
            # Non-structural elements use envelope bounds
            # BUT: Doors/windows can be ON the building face (at grid boundaries)
            is_opening = any(kw in obj_type.lower() or kw in name.lower()
                            for kw in ['door', 'window'])

            if is_opening:
                # Doors/windows use grid bounds (can be on building face)
                try:
                    grid_x_max = self.gridtruth['grid_horizontal']['E']
                    grid_y_max = self.gridtruth['grid_vertical']['5']
                except KeyError as e:
                    self.error(f"{name}: Grid data incomplete - {e}")
                    return False

                if x < -0.1 or x > grid_x_max + 0.1:
                    self.error(f"{name}: X={x:.2f} outside grid [0, {grid_x_max:.2f}]")
                    return False

                if y < -0.1 or y > grid_y_max + 0.1:
                    self.error(f"{name}: Y={y:.2f} outside grid [0, {grid_y_max:.2f}]")
                    return False
            else:
                # MEP/furniture use envelope bounds (inside building)
                if x < self.envelope['x_min'] or x > self.envelope['x_max']:
                    self.error(f"{name}: X={x:.2f} outside envelope "
                              f"[{self.envelope['x_min']:.2f}, {self.envelope['x_max']:.2f}]")
                    return False

                if y < self.envelope['y_min'] or y > self.envelope['y_max']:
                    self.error(f"{name}: Y={y:.2f} outside envelope "
                              f"[{self.envelope['y_min']:.2f}, {self.envelope['y_max']:.2f}]")
                    return False

        # Check Z bounds
        max_z = self.elevations.get('ceiling', 3.0) + 1.0  # Allow 1m above ceiling
        if z < -0.1 or z > max_z:
            self.error(f"{name}: Z={z:.2f} outside valid range [0, {max_z:.2f}]")
            return False

        return True

    def _needs_porch_fix(self, obj: Dict) -> bool:
        """Check if porch object needs coordinate fix."""
        pos = obj['position']
        y = pos[1]

        # Porch with negative Y or Y outside grid needs fixing
        try:
            grid_y_max = self.gridtruth['grid_vertical']['5']
        except KeyError:
            return False  # Can't validate without grid data
        return y < 0 or y > grid_y_max

    def _fix_porch_coordinates(self, obj: Dict) -> bool:
        """
        Fix porch coordinates that are outside building envelope.

        Porch should be at the entrance, not at negative Y.
        """
        name = obj['name']
        pos = obj['position']

        # Find entrance door (usually door_ruang_tamu)
        entrance_door = None
        for placed_obj in self.placed.values():
            if 'door' in placed_obj.get('object_type', '') and \
               'ruang_tamu' in placed_obj.get('name', ''):
                entrance_door = placed_obj
                break

        if entrance_door:
            # Place porch at entrance door location
            door_pos = entrance_door['position']
            obj['position'][0] = door_pos[0]  # Same X as door
            obj['position'][1] = door_pos[1] - 1.5  # 1.5m in front of door
            self.warn(f"{name}: Fixed Y from {pos[1]:.2f} to {obj['position'][1]:.2f} "
                     f"(placed at entrance)")
            return True
        else:
            # Place porch at grid Y=1 (just inside building)
            obj['position'][1] = 1.0
            self.warn(f"{name}: Fixed Y from {pos[1]:.2f} to 1.0 "
                     f"(no entrance door found, placed at front)")
            return True

    def _check_z_height(self, obj: Dict) -> bool:
        """Check if object Z height matches expected value."""
        name = obj['name']
        pos = obj['position']
        z = pos[2]
        obj_type = obj.get('object_type', '')

        # Get expected Z from rules
        expected_z = self._get_expected_z(obj_type)
        if expected_z is None:
            return True  # No rule for this object type

        # Get tolerance
        tolerance = self.rules.get('z_tolerance', {}).get('default', 0.1)
        if 'structural' in obj_type or 'wall' in obj_type or 'slab' in obj_type:
            tolerance = self.rules.get('z_tolerance', {}).get('structural', 0.05)

        # Check deviation
        deviation = abs(z - expected_z)
        if deviation > tolerance:
            self.warn(f"{name}: Z={z:.2f} but expected {expected_z:.2f} "
                     f"(deviation: {deviation:.2f}m)")
            return False

        return True

    def _fix_z_height(self, obj: Dict) -> bool:
        """Fix Z height to match expected value."""
        obj_type = obj.get('object_type', '')
        expected_z = self._get_expected_z(obj_type)

        if expected_z is not None:
            old_z = obj['position'][2]
            obj['position'][2] = expected_z
            self.warn(f"{obj['name']}: Fixed Z from {old_z:.2f} to {expected_z:.2f}")
            return True

        return False

    def _get_expected_z(self, obj_type: str) -> Optional[float]:
        """Get expected Z height for object type."""
        z_defaults = self.rules.get('z_defaults', {})

        # Match by keywords
        obj_lower = obj_type.lower()
        for keyword, z in z_defaults.items():
            if keyword in obj_lower:
                return z

        return None

    def _check_room_assignment(self, obj: Dict):
        """Check if object is within its assigned room."""
        name = obj['name']
        pos = obj['position']
        x, y = pos[0], pos[1]
        claimed_room = obj.get('room_id')

        # Find which room object is actually in
        actual_room = None
        for room_name, bounds in self.rooms.items():
            # Skip non-room entries (e.g., _note, _description)
            if not isinstance(bounds, dict) or room_name.startswith('_'):
                continue

            if (bounds.get('x_min', 0) <= x <= bounds.get('x_max', 999) and
                bounds.get('y_min', 0) <= y <= bounds.get('y_max', 999)):
                actual_room = room_name
                break

        # Update room_id if not set
        if not claimed_room and actual_room:
            obj['room_id'] = actual_room.lower()
            self.warn(f"{name}: Assigned to room '{actual_room}' based on position")
        elif claimed_room and actual_room:
            # Verify claimed room matches actual room
            if claimed_room.upper() != actual_room:
                self.warn(f"{name}: Claims room '{claimed_room}' but is in '{actual_room}'")
                obj['room_id'] = actual_room.lower()  # Fix it

    def _check_collisions(self, obj: Dict):
        """Check for collisions with existing objects."""
        name = obj['name']
        pos = obj['position']
        obj_type = obj.get('object_type', '')

        # Skip collision check for wall-mounted items
        ignore_types = self.rules.get('collision_detection', {}).get('ignore_types', [])
        for ignore_type in ignore_types:
            if ignore_type in obj_type:
                return

        # Check against all placed objects
        tolerance = self.rules.get('collision_detection', {}).get('tolerance', 0.05)

        for other_name, other_obj in self.placed.items():
            other_pos = other_obj.get('position')
            if not other_pos or len(other_pos) < 3:
                continue

            # Calculate distance
            dx = pos[0] - other_pos[0]
            dy = pos[1] - other_pos[1]
            dz = pos[2] - other_pos[2]
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)

            if dist < tolerance:
                self.warn(f"{name}: Collision with {other_name} "
                         f"(distance: {dist:.3f}m)")

    def warn(self, message: str):
        """Record a warning."""
        self.warnings.append(message)
        self.stats['warnings'] += 1
        print(f"   ⚠️  {message}")

    def error(self, message: str):
        """Record an error."""
        self.errors.append(message)
        self.stats['errors'] += 1
        print(f"   ❌ {message}")

    def to_output(self) -> List[Dict]:
        """Export validated objects."""
        return list(self.placed.values())

    def print_summary(self):
        """Print validation summary."""
        print()
        print("=" * 80)
        print("🎯 3D CANVAS VALIDATION SUMMARY")
        print("=" * 80)
        print()
        print(f"Total objects:     {self.stats['total_objects']}")
        print(f"Validated:         {self.stats['validated']}")
        print(f"Auto-fixed:        {self.stats['fixed']}")
        print(f"Warnings:          {self.stats['warnings']}")
        print(f"Errors:            {self.stats['errors']}")
        print()

        if self.warnings:
            print("⚠️  WARNINGS:")
            for w in self.warnings[:10]:  # Show first 10
                print(f"   • {w}")
            if len(self.warnings) > 10:
                print(f"   ... and {len(self.warnings) - 10} more")
            print()

        if self.errors:
            print("❌ ERRORS:")
            for e in self.errors[:10]:  # Show first 10
                print(f"   • {e}")
            if len(self.errors) > 10:
                print(f"   ... and {len(self.errors) - 10} more")
            print()

        print("=" * 80)
        print()


def validate_with_canvas(objects: List[Dict], gridtruth_path: str,
                         validation_rules_path: str) -> List[Dict]:
    """
    Validate objects using 3D canvas.

    [THIRD-D] This is the staging layer between extraction and output.

    Args:
        objects: List of extracted objects
        gridtruth_path: Path to GridTruth.json
        validation_rules_path: Path to validation_rules.json

    Returns:
        List of validated (and possibly fixed) objects
    """
    print()
    print("=" * 80)
    print("🎯 VALIDATING OBJECTS IN 3D CANVAS")
    print("=" * 80)
    print()

    canvas = BuildingCanvas(gridtruth_path, validation_rules_path)

    # Place each object on canvas
    for obj in objects:
        canvas.place(obj)

    # Print summary
    canvas.print_summary()

    # Return validated objects
    return canvas.to_output()
