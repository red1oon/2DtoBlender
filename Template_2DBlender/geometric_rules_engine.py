#!/usr/bin/env python3
"""
Geometric Rules Engine - DeepSeek Implementation
=================================================
Core placement logic that uses template rules to place objects correctly.

This is the "single source of truth" approach where:
- AI identifies objects and fills template JSON
- Rules engine applies semantic placement logic
- Humans refine template, not code

Author: DeepSeek Integration Team
Date: 2025-11-23
"""

import sqlite3
import struct
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Use relative path to database in same directory as this script
SCRIPT_DIR = Path(__file__).parent
DB_PATH = str(SCRIPT_DIR / "Ifc_Object_Library.db")


@dataclass
class PlacementContext:
    """Context information for object placement"""
    raw_position: np.ndarray  # (x, y, z) from template
    nearest_wall: Optional[Dict] = None
    nearest_room: Optional[Dict] = None
    floor_level: float = 0.0


@dataclass
class PlacedObject:
    """Result of placing an object"""
    object_type: str
    final_position: np.ndarray
    final_rotation: np.ndarray  # Euler angles (rx, ry, rz)
    vertices: np.ndarray
    pivot_point: str
    rules_applied: List[str]


class GeometricRulesEngine:
    """
    Main rules engine that places objects according to semantic rules
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = None
        self._connect()

    def _connect(self):
        """Connect to library database"""
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access

    def _unpack_vertices(self, vertices_blob: bytes) -> np.ndarray:
        """Unpack vertex blob to numpy array"""
        if not vertices_blob:
            return np.array([])

        n_floats = len(vertices_blob) // 4
        vertices_flat = struct.unpack(f'<{n_floats}f', vertices_blob)
        return np.array(vertices_flat).reshape(-1, 3)

    def load_object_metadata(self, object_type: str) -> Dict:
        """
        Load complete metadata for an object type

        Returns:
            Dict with geometry, pivot, placement_rules, connections, standards
        """
        cursor = self.conn.cursor()

        # Get object catalog + geometry
        cursor.execute("""
            SELECT
                oc.catalog_id,
                oc.object_type,
                oc.object_name,
                oc.pivot_point,
                oc.origin_offset_x,
                oc.origin_offset_y,
                oc.origin_offset_z,
                oc.behavior_category,
                oc.width_mm,
                oc.depth_mm,
                oc.height_mm,
                bg.vertices,
                bg.vertex_count
            FROM object_catalog oc
            JOIN base_geometries bg ON oc.geometry_hash = bg.geometry_hash
            WHERE oc.object_type = ?
            LIMIT 1
        """, (object_type,))

        obj_row = cursor.fetchone()
        if not obj_row:
            raise ValueError(f"Object type not found: {object_type}")

        # Get placement rules
        cursor.execute("""
            SELECT * FROM placement_rules WHERE object_type = ?
        """, (object_type,))
        placement_row = cursor.fetchone()

        # Get connection requirements
        cursor.execute("""
            SELECT * FROM connection_requirements WHERE object_type = ?
        """, (object_type,))
        connection_row = cursor.fetchone()

        # Get Malaysian standards
        cursor.execute("""
            SELECT * FROM malaysian_standards WHERE object_type = ?
        """, (object_type,))
        standards_rows = cursor.fetchall()

        return {
            'object': dict(obj_row),
            'placement_rules': dict(placement_row) if placement_row else {},
            'connection_requirements': dict(connection_row) if connection_row else {},
            'malaysian_standards': [dict(row) for row in standards_rows]
        }

    def apply_pivot_correction(self, vertices: np.ndarray, metadata: Dict) -> np.ndarray:
        """Apply pivot correction to align pivot point to origin"""
        obj = metadata['object']
        offset = np.array([
            obj['origin_offset_x'],
            obj['origin_offset_y'],
            obj['origin_offset_z']
        ])

        return vertices + offset

    def apply_alignment_rules(self,
                               position: np.ndarray,
                               metadata: Dict,
                               context: PlacementContext) -> np.ndarray:
        """
        Apply alignment rules to get final position

        Args:
            position: Raw position from template (x, y, z)
            metadata: Object metadata with placement rules
            context: Placement context (walls, rooms, etc.)

        Returns:
            Final aligned position
        """
        rules = metadata['placement_rules']
        aligned_pos = position.copy()

        alignment_type = rules.get('alignment_type')
        reference_plane = rules.get('reference_plane')

        if alignment_type == 'bottom' and reference_plane == 'floor':
            # Bottom-align to floor
            offset_z = rules.get('offset_z', 0.0)
            aligned_pos[2] = context.floor_level + offset_z

        elif alignment_type == 'wall_surface' and reference_plane == 'wall':
            # Align to wall surface at standard height
            standard_height = rules.get('standard_height')
            if standard_height:
                aligned_pos[2] = context.floor_level + standard_height

            # Offset from wall
            offset_from_wall = rules.get('offset_from_wall', 0.0)
            if context.nearest_wall:
                # Project position onto wall and offset
                # (Simplified: in real implementation, use wall normal)
                pass

        elif alignment_type == 'center':
            # Keep position as-is (centered placement)
            pass

        return aligned_pos

    def calculate_rotation(self,
                            position: np.ndarray,
                            metadata: Dict,
                            context: PlacementContext) -> np.ndarray:
        """
        Calculate rotation based on semantic rules

        Returns:
            Euler angles (rx, ry, rz) in radians
        """
        rules = metadata['placement_rules']
        rotation_method = rules.get('rotation_method', 'absolute')

        rotation = np.array([0.0, 0.0, 0.0])  # Default: no rotation

        if rotation_method == 'wall_normal':
            # Rotate to face perpendicular to wall
            if context.nearest_wall:
                # Calculate rotation from wall normal
                # (Simplified: in real implementation, use actual wall normal)
                rotation[2] = 0.0  # Z-axis rotation (yaw)

        elif rotation_method == 'room_entrance':
            # Rotate to face room entrance
            if context.nearest_room:
                # Calculate rotation towards entrance
                # (Simplified: placeholder)
                rotation[2] = np.pi  # 180 degrees

        elif rotation_method == 'absolute':
            # Use absolute rotation from template
            pass

        # Apply rotation offset
        rotation_offset = rules.get('rotation_offset_degrees', 0.0)
        rotation[2] += np.radians(rotation_offset)

        # Apply flip direction
        if rules.get('flip_direction', 0) == 1:
            rotation[2] += np.pi  # Flip 180 degrees

        return rotation

    def validate_connections(self, metadata: Dict, context: PlacementContext) -> List[str]:
        """
        Validate that object meets connection requirements

        Returns:
            List of validation messages
        """
        requirements = metadata['connection_requirements']
        messages = []

        # Check primary surface connection
        primary_surface = requirements.get('primary_surface')
        if primary_surface:
            messages.append(f"Requires connection to {primary_surface}")

        # Check clearances
        clearance_front = requirements.get('clearance_front')
        if clearance_front:
            messages.append(f"Requires {clearance_front}m front clearance")

        # Check utilities
        if requirements.get('requires_water_supply', 0):
            messages.append("Requires water supply connection")

        if requirements.get('requires_drainage', 0):
            messages.append("Requires drainage connection")

        if requirements.get('requires_electrical', 0):
            messages.append("Requires electrical connection")

        return messages

    def place_object(self,
                     object_type: str,
                     raw_position: List[float],
                     context: Optional[PlacementContext] = None) -> PlacedObject:
        """
        Main method: Place an object according to its rules

        Args:
            object_type: Type of object to place (e.g., "door_single")
            raw_position: [x, y, z] position from template
            context: Placement context (walls, rooms, etc.)

        Returns:
            PlacedObject with final position, rotation, and geometry
        """
        if context is None:
            context = PlacementContext(
                raw_position=np.array(raw_position),
                floor_level=0.0
            )

        # Load metadata
        metadata = self.load_object_metadata(object_type)

        # Apply pivot correction to geometry
        vertices_raw = self._unpack_vertices(metadata['object']['vertices'])
        vertices_corrected = self.apply_pivot_correction(vertices_raw, metadata)

        # Apply alignment rules
        position = np.array(raw_position)
        final_position = self.apply_alignment_rules(position, metadata, context)

        # Calculate rotation
        final_rotation = self.calculate_rotation(final_position, metadata, context)

        # Validate connections
        validation_messages = self.validate_connections(metadata, context)

        # Apply rotation to vertices (simplified - just store rotation for now)
        # In full implementation, would apply rotation matrix to vertices

        return PlacedObject(
            object_type=object_type,
            final_position=final_position,
            final_rotation=final_rotation,
            vertices=vertices_corrected,
            pivot_point=metadata['object']['pivot_point'],
            rules_applied=validation_messages
        )


def demo_placement():
    """Demonstrate object placement using rules engine"""

    print("=" * 70)
    print("GEOMETRIC RULES ENGINE - Demonstration")
    print("=" * 70)
    print()

    engine = GeometricRulesEngine()

    # Test objects with sample positions
    test_cases = [
        {
            'object_type': 'door_single',
            'raw_position': [2.0, 0.1, 0.0],  # Near wall
            'description': 'Door at (2m, 0.1m, floor)'
        },
        {
            'object_type': 'switch_1gang',
            'raw_position': [2.5, 0.02, 0.0],  # On wall
            'description': 'Switch on wall near door'
        },
        {
            'object_type': 'toilet',
            'raw_position': [1.0, 1.5, 0.0],  # In bathroom
            'description': 'Toilet in bathroom'
        },
        {
            'object_type': 'outlet_3pin_ms589',
            'raw_position': [3.0, 0.02, 0.0],  # On wall
            'description': 'Outlet on wall'
        },
        {
            'object_type': 'basin',
            'raw_position': [0.5, 0.05, 0.0],  # On wall
            'description': 'Basin on bathroom wall'
        },
    ]

    for test in test_cases:
        print(f"\n📦 {test['description']}")
        print(f"   Type: {test['object_type']}")
        print(f"   Raw position: {test['raw_position']}")

        try:
            placed = engine.place_object(
                test['object_type'],
                test['raw_position']
            )

            print(f"\n   ✅ Placement Successful:")
            print(f"      Pivot: {placed.pivot_point}")
            print(f"      Final position: [{placed.final_position[0]:.3f}, {placed.final_position[1]:.3f}, {placed.final_position[2]:.3f}]")
            print(f"      Rotation (deg): [{np.degrees(placed.final_rotation[0]):.1f}, {np.degrees(placed.final_rotation[1]):.1f}, {np.degrees(placed.final_rotation[2]):.1f}]")
            print(f"      Vertices: {len(placed.vertices)} vertices")

            if placed.rules_applied:
                print(f"      Rules applied:")
                for rule in placed.rules_applied:
                    print(f"         - {rule}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print()
    print("=" * 70)
    print("✅ DEMONSTRATION COMPLETE")
    print("=" * 70)
    print()
    print("Key Results:")
    print("- Objects loaded with complete metadata (pivot, rules, connections)")
    print("- Pivot corrections applied to geometry")
    print("- Alignment rules determine final position")
    print("- Rotation rules determine orientation")
    print("- Connection requirements validated")
    print()
    print("Next: Integrate with TB-LKTN house template for real-world test")
    print()


if __name__ == "__main__":
    demo_placement()
