#!/usr/bin/env python3
"""
Intelligent MEP Routing Engine for Master Template Charting System.

Routes trunk lines along corridors and generates branch lines perpendicular
to mains, following best practices and code compliance requirements.
"""

import sqlite3
import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import uuid

from corridor_detection import Corridor, CorridorDetector


@dataclass
class RoutingDevice:
    """Represents a device to be connected (sprinkler, light, etc.)."""
    guid: str
    x: float
    y: float
    z: float
    discipline: str
    device_type: str


@dataclass
class TrunkLine:
    """Represents a main trunk line along a corridor."""
    trunk_id: int
    corridor_id: int
    start_point: Tuple[float, float, float]
    end_point: Tuple[float, float, float]
    routing_points: List[Tuple[float, float, float]]
    diameter: float  # DN size in meters
    device_count: int  # Number of devices served
    discipline: str


@dataclass
class BranchLine:
    """Represents a branch line from trunk to device."""
    branch_id: int
    trunk_id: int
    trunk_connection_point: Tuple[float, float, float]
    device_location: Tuple[float, float, float]
    device_guid: str
    diameter: float  # DN size in meters
    length: float
    discipline: str


class IntelligentRoutingEngine:
    """Routes MEP systems along corridors with trunk/branch hierarchy."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.corridors: List[Corridor] = []
        self.devices: List[RoutingDevice] = []
        self.trunk_lines: List[TrunkLine] = []
        self.branch_lines: List[BranchLine] = []

    def load_corridors(self):
        """Detect corridors using CorridorDetector."""
        print("Loading corridors...")
        detector = CorridorDetector(self.db_path)
        self.corridors = detector.detect_corridors()
        print(f"✅ Loaded {len(self.corridors)} corridors\n")

    def load_devices(self, discipline: str, device_type: str):
        """
        Load devices from database (sprinklers, lights, etc.).

        Args:
            discipline: 'FP', 'ELEC', etc.
            device_type: 'sprinkler', 'light_fixture', etc.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT em.guid, et.center_x, et.center_y, et.center_z, em.discipline, em.inferred_shape_type
            FROM elements_meta em
            JOIN element_transforms et ON em.guid = et.guid
            WHERE em.discipline = ? AND em.inferred_shape_type = ?
            ORDER BY et.center_x, et.center_y
        """, (discipline, device_type))

        self.devices = []
        for row in cursor.fetchall():
            guid, x, y, z, disc, dev_type = row
            device = RoutingDevice(guid, x, y, z, disc, dev_type)
            self.devices.append(device)

        conn.close()
        print(f"Loaded {len(self.devices)} {device_type} devices for {discipline}")

    def generate_devices_from_standards(self, discipline: str, device_type: str, room_bounds: Dict[str, float], z_height: float = 4.0, spacing: float = 3.0):
        """
        GENERATE code-compliant device placements instead of loading from database.

        Integrates with PlacementGenerator to create evenly-distributed grid.

        Args:
            discipline: 'FP', 'ELEC', 'HVAC'
            device_type: 'sprinkler', 'light_fixture', 'hvac_diffuser'
            room_bounds: Dict with 'min_x', 'max_x', 'min_y', 'max_y'
            z_height: Height above floor (meters)
            spacing: Spacing between devices (meters) - NEW: from config
        """
        from code_compliance import PlacementGenerator

        print(f"\n{'='*80}")
        print(f"GENERATING DEVICES FROM ENGINEERING STANDARDS")
        print(f"{'='*80}")
        print(f"Discipline: {discipline}")
        print(f"Device Type: {device_type}")
        print(f"Room Bounds: X:[{room_bounds['min_x']:.1f}, {room_bounds['max_x']:.1f}], Y:[{room_bounds['min_y']:.1f}, {room_bounds['max_y']:.1f}]")
        print(f"Config: Spacing={spacing}m, Height={z_height}m")  # NEW: Show config values

        # Generate positions using standards
        placements = PlacementGenerator.generate_grid_placement(
            room_bounds=room_bounds,
            element_type=device_type,
            discipline=discipline,
            z_height=z_height,
            spacing_override=spacing  # NEW: Pass spacing from config
        )

        # Convert to RoutingDevice objects
        self.devices = []
        for x, y, z in placements:
            guid = str(uuid.uuid4())
            device = RoutingDevice(guid, x, y, z, discipline, device_type)
            self.devices.append(device)

        print(f"✅ Generated {len(self.devices)} {device_type} devices using code-compliant grid distribution")

    def assign_devices_to_corridors(self, max_distance: float = 10.0) -> Dict[int, List[RoutingDevice]]:
        """
        Assign devices to nearest corridors.

        Args:
            max_distance: Maximum distance from corridor to assign device (meters)

        Returns:
            Dictionary mapping corridor_id to list of assigned devices
        """
        corridor_devices = {c.corridor_id: [] for c in self.corridors}
        unassigned_devices = []

        for device in self.devices:
            # Find nearest corridor
            min_distance = float('inf')
            nearest_corridor = None

            for corridor in self.corridors:
                # Calculate distance from device to corridor centerline
                distance = self._distance_to_corridor(device, corridor)

                if distance < min_distance:
                    min_distance = distance
                    nearest_corridor = corridor

            # Assign device if within range
            if nearest_corridor and min_distance <= max_distance:
                corridor_devices[nearest_corridor.corridor_id].append(device)
            else:
                unassigned_devices.append(device)

        print(f"\nDevice Assignment Summary:")
        for corridor_id, devices in corridor_devices.items():
            if devices:
                print(f"  Corridor #{corridor_id}: {len(devices)} devices")

        if unassigned_devices:
            print(f"  Unassigned: {len(unassigned_devices)} devices (will use standalone routing)")

        return corridor_devices

    def _distance_to_corridor(self, device: RoutingDevice, corridor: Corridor) -> float:
        """
        Calculate minimum distance from device to corridor centerline.

        Args:
            device: Device to check
            corridor: Corridor to check

        Returns:
            Minimum distance in meters
        """
        min_dist = float('inf')

        # Check distance to each centerline segment
        for i in range(len(corridor.centerline_points) - 1):
            p1 = corridor.centerline_points[i]
            p2 = corridor.centerline_points[i + 1]

            # Distance from point to line segment
            dist = self._point_to_segment_distance(device.x, device.y, p1[0], p1[1], p2[0], p2[1])

            if dist < min_dist:
                min_dist = dist

        return min_dist

    def _point_to_segment_distance(self, px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
        """
        Calculate distance from point (px, py) to line segment (x1,y1)-(x2,y2).
        """
        dx = x2 - x1
        dy = y2 - y1
        segment_length_sq = dx*dx + dy*dy

        if segment_length_sq == 0:
            # Segment is a point
            return math.sqrt((px - x1)**2 + (py - y1)**2)

        # Calculate projection parameter t
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / segment_length_sq))

        # Find closest point on segment
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        # Return distance
        return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)

    def generate_trunk_lines(self, corridor_devices: Dict[int, List[RoutingDevice]], trunk_diameter_dn: int = 100) -> List[TrunkLine]:
        """
        Generate trunk lines along corridors.

        Args:
            corridor_devices: Mapping of corridor_id to devices
            trunk_diameter_dn: DN size for trunk lines (default 100mm = 4")

        Returns:
            List of TrunkLine objects
        """
        print(f"\n{'='*80}")
        print("GENERATING TRUNK LINES ALONG CORRIDORS")
        print(f"{'='*80}")

        trunk_lines = []
        trunk_id = 1

        for corridor in self.corridors:
            devices = corridor_devices.get(corridor.corridor_id, [])

            if len(devices) < 2:
                # Not enough devices to justify trunk line
                continue

            # Get routing points along corridor centerline
            routing_points_2d = corridor.get_trunk_routing_points(segment_length=5.0)

            # Get average device Z height for trunk elevation
            avg_z = sum(d.z for d in devices) / len(devices)

            # Convert to 3D points
            routing_points = [(x, y, avg_z) for x, y in routing_points_2d]

            trunk = TrunkLine(
                trunk_id=trunk_id,
                corridor_id=corridor.corridor_id,
                start_point=routing_points[0],
                end_point=routing_points[-1],
                routing_points=routing_points,
                diameter=trunk_diameter_dn / 1000.0,  # Convert DN to meters
                device_count=len(devices),
                discipline=devices[0].discipline if devices else 'FP'
            )

            trunk_lines.append(trunk)

            print(f"Trunk #{trunk_id} (Corridor #{corridor.corridor_id}):")
            print(f"  Serves {len(devices)} devices")
            print(f"  DN {trunk_diameter_dn} ({trunk.diameter*1000:.0f}mm)")
            print(f"  Routing points: {len(routing_points)}")

            trunk_id += 1

        self.trunk_lines = trunk_lines
        print(f"\n✅ Generated {len(trunk_lines)} trunk lines")
        return trunk_lines

    def generate_branch_lines(
        self,
        corridor_devices: Dict[int, List[RoutingDevice]],
        branch_diameter_dn: int = 50,
        drop_diameter_dn: int = 25
    ) -> List[BranchLine]:
        """
        Generate branch lines from trunks to devices.

        Args:
            corridor_devices: Mapping of corridor_id to devices
            branch_diameter_dn: DN size for branch lines (default 50mm = 2")
            drop_diameter_dn: DN size for final drops (default 25mm = 1")

        Returns:
            List of BranchLine objects
        """
        print(f"\n{'='*80}")
        print("GENERATING BRANCH LINES (PERPENDICULAR TO TRUNKS)")
        print(f"{'='*80}")

        branch_lines = []
        branch_id = 1

        for trunk in self.trunk_lines:
            devices = corridor_devices.get(trunk.corridor_id, [])

            for device in devices:
                # Find nearest point on trunk routing line
                connection_point, distance = self._nearest_point_on_trunk(device, trunk)

                # Determine diameter based on distance (long branches use DN 50, short drops use DN 25)
                diameter_dn = branch_diameter_dn if distance > 3.0 else drop_diameter_dn
                diameter_m = diameter_dn / 1000.0

                branch = BranchLine(
                    branch_id=branch_id,
                    trunk_id=trunk.trunk_id,
                    trunk_connection_point=connection_point,
                    device_location=(device.x, device.y, device.z),
                    device_guid=device.guid,
                    diameter=diameter_m,
                    length=distance,
                    discipline=device.discipline
                )

                branch_lines.append(branch)
                branch_id += 1

        self.branch_lines = branch_lines

        # Statistics
        dn50_count = sum(1 for b in branch_lines if b.diameter == 0.05)
        dn25_count = sum(1 for b in branch_lines if b.diameter == 0.025)

        print(f"\n✅ Generated {len(branch_lines)} branch lines:")
        print(f"  DN 50 branches: {dn50_count}")
        print(f"  DN 25 drops:    {dn25_count}")

        return branch_lines

    def _nearest_point_on_trunk(self, device: RoutingDevice, trunk: TrunkLine) -> Tuple[Tuple[float, float, float], float]:
        """
        Find nearest point on trunk routing line to device.

        Returns:
            (nearest_point, distance) tuple
        """
        min_distance = float('inf')
        nearest_point = trunk.routing_points[0]

        for i in range(len(trunk.routing_points) - 1):
            p1 = trunk.routing_points[i]
            p2 = trunk.routing_points[i + 1]

            # Project device onto trunk segment
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dz = p2[2] - p1[2]
            segment_length_sq = dx*dx + dy*dy + dz*dz

            if segment_length_sq == 0:
                point = p1
            else:
                t = max(0, min(1, ((device.x - p1[0]) * dx + (device.y - p1[1]) * dy + (device.z - p1[2]) * dz) / segment_length_sq))
                point = (p1[0] + t * dx, p1[1] + t * dy, p1[2] + t * dz)

            # Calculate distance
            dist = math.sqrt((device.x - point[0])**2 + (device.y - point[1])**2 + (device.z - point[2])**2)

            if dist < min_distance:
                min_distance = dist
                nearest_point = point

        return nearest_point, min_distance

    def route_system(
        self,
        discipline: str,
        device_type: str,
        trunk_diameter_dn: int = 100,
        branch_diameter_dn: int = 50,
        drop_diameter_dn: int = 25,
        generate_devices: bool = False,
        device_spacing: float = 3.0,
        device_height: float = 4.0
    ):
        """
        Complete routing workflow for a discipline.

        Args:
            discipline: 'FP', 'ELEC', etc.
            device_type: 'sprinkler', 'light_fixture', etc.
            trunk_diameter_dn: Main trunk diameter (DN 100 = 4")
            branch_diameter_dn: Branch line diameter (DN 50 = 2")
            drop_diameter_dn: Drop line diameter (DN 25 = 1")
            generate_devices: If True, generate grid; if False, load from DB
            device_spacing: Spacing between devices in meters (NEW: from config)
            device_height: Height above floor in meters (NEW: from config)
        """
        print(f"\n{'='*80}")
        print(f"INTELLIGENT ROUTING: {discipline} {device_type.upper()}")
        print(f"{'='*80}\n")

        # Load corridors
        self.load_corridors()

        # Load or generate devices
        if generate_devices:
            # Get building bounds for grid generation
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT MIN(center_x), MAX(center_x), MIN(center_y), MAX(center_y) FROM element_transforms")
            min_x, max_x, min_y, max_y = cursor.fetchone()
            conn.close()

            room_bounds = {
                'min_x': min_x,
                'max_x': max_x,
                'min_y': min_y,
                'max_y': max_y
            }

            self.generate_devices_from_standards(
                discipline, device_type, room_bounds,
                z_height=device_height,  # NEW: Use config value
                spacing=device_spacing   # NEW: Pass spacing to generator
            )
        else:
            self.load_devices(discipline, device_type)

        # Assign devices to corridors
        corridor_devices = self.assign_devices_to_corridors(max_distance=10.0)

        # Generate trunk lines along corridors
        self.generate_trunk_lines(corridor_devices, trunk_diameter_dn)

        # Generate branch lines perpendicular to trunks
        self.generate_branch_lines(corridor_devices, branch_diameter_dn, drop_diameter_dn)

        # Summary
        print(f"\n{'='*80}")
        print("ROUTING SUMMARY")
        print(f"{'='*80}")
        print(f"Discipline:   {discipline}")
        print(f"Device Type:  {device_type}")
        print(f"Devices:      {len(self.devices)}")
        print(f"Trunk Lines:  {len(self.trunk_lines)} (DN {trunk_diameter_dn})")
        print(f"Branch Lines: {len(self.branch_lines)} (DN {branch_diameter_dn}/{drop_diameter_dn})")
        print(f"{'='*80}\n")


def main():
    """Test intelligent routing."""
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python3 intelligent_routing.py <database_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}")
        sys.exit(1)

    # Test with Fire Protection sprinklers
    router = IntelligentRoutingEngine(db_path)
    router.route_system(
        discipline='FP',
        device_type='sprinkler',
        trunk_diameter_dn=100,  # 4" main
        branch_diameter_dn=50,  # 2" branches
        drop_diameter_dn=25     # 1" drops
    )

    print("\n✅ Intelligent routing complete!")
    print("✅ Ready to generate geometry and export to database!")


if __name__ == "__main__":
    main()
