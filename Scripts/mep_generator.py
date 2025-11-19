#!/usr/bin/env python3
"""
MEP Generator Classes for Mini Bonsai GUI
==========================================

Modular classes for clash-free MEP element generation from zone configs.

Architecture:
    ZoneManager       - Loads/manages zone configurations
    ClashChecker      - Ensures elements don't overlap
    DisciplineGenerator - Base class for discipline-specific generators
    FPGenerator       - Fire Protection elements
    ELECGenerator     - Electrical elements
    ACMVGenerator     - HVAC/Air conditioning elements

Usage:
    from mep_generator import MEPGeneratorOrchestrator

    orchestrator = MEPGeneratorOrchestrator(zones_config, building_config)
    elements = orchestrator.generate_all()
"""

import math
import json
import uuid
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from abc import ABC, abstractmethod


class ZoneManager:
    """Manages zone configurations for MEP placement."""

    def __init__(self, zones_config_path: str):
        with open(zones_config_path) as f:
            self.config = json.load(f)

        self.stratification = self.config.get('vertical_stratification', {})
        self.clearances = self.config.get('discipline_clearances', {})

    def get_zones(self, zone_type: str) -> List[Dict]:
        """Get zones of a specific type (toilet_zones, ac_equipment, etc.)."""
        return [z for z in self.config.get(zone_type, []) if z.get('enabled', True)]

    def get_z_offset(self, element_type: str) -> float:
        """Get vertical offset for element type to prevent clashes."""
        return self.stratification.get(element_type, -0.5)

    def get_clearance(self, disc1: str, disc2: str) -> float:
        """Get minimum horizontal clearance between disciplines."""
        key = f"{disc1}_to_{disc2}"
        return self.clearances.get(key, 0.3)


class ClashChecker:
    """Checks and prevents element clashes."""

    def __init__(self, clearance: float = 0.3):
        self.clearance = clearance
        self.occupied = []  # List of (x, y, z, radius, discipline) tuples

    def add_occupied(self, x: float, y: float, z: float, radius: float, discipline: str):
        """Register an occupied space."""
        self.occupied.append((x, y, z, radius, discipline))

    def check_clash(self, x: float, y: float, z: float, radius: float, discipline: str) -> bool:
        """
        Check if position clashes with existing elements.
        Returns True if clash detected.
        """
        for ox, oy, oz, oradius, odisc in self.occupied:
            # Check horizontal distance
            dist_xy = math.sqrt((x - ox)**2 + (y - oy)**2)
            min_dist = radius + oradius + self.clearance

            # Check if vertically separated (different Z levels = no clash)
            z_separation = abs(z - oz)
            if z_separation < 0.1:  # Same level
                if dist_xy < min_dist:
                    return True

        return False

    def find_clear_position(self, x: float, y: float, z: float,
                            radius: float, discipline: str,
                            max_attempts: int = 10) -> Tuple[float, float]:
        """
        Find nearest clear position if original clashes.
        Returns adjusted (x, y) coordinates.
        """
        if not self.check_clash(x, y, z, radius, discipline):
            return x, y

        # Try shifting in cardinal directions
        for attempt in range(1, max_attempts + 1):
            offset = attempt * self.clearance
            for dx, dy in [(offset, 0), (-offset, 0), (0, offset), (0, -offset)]:
                new_x, new_y = x + dx, y + dy
                if not self.check_clash(new_x, new_y, z, radius, discipline):
                    return new_x, new_y

        # Return original if no clear position found
        return x, y


class DisciplineGenerator(ABC):
    """Abstract base class for discipline-specific generators."""

    def __init__(self, zone_manager: ZoneManager, clash_checker: ClashChecker,
                 building_bounds: Dict):
        self.zone_manager = zone_manager
        self.clash_checker = clash_checker
        self.bounds = building_bounds  # {min_x, max_x, min_y, max_y, slab_cx, slab_cy}
        self.elements = []

    @property
    @abstractmethod
    def discipline(self) -> str:
        """Return discipline code (FP, ELEC, ACMV)."""
        pass

    @abstractmethod
    def generate(self, floors_config: Dict) -> List[Dict]:
        """Generate elements for all floors. Returns list of element dicts."""
        pass

    def _create_guid(self) -> str:
        """Generate unique GUID."""
        return str(uuid.uuid4()).replace('-', '')[:22]

    def _register_element(self, x: float, y: float, z: float, radius: float):
        """Register element with clash checker."""
        self.clash_checker.add_occupied(x, y, z, radius, self.discipline)


class FPGenerator(DisciplineGenerator):
    """Fire Protection generator - sprinklers and pipes."""

    @property
    def discipline(self) -> str:
        return 'FP'

    def generate(self, floors_config: Dict, fp_config: Dict) -> List[Dict]:
        """Generate FP elements using grid placement with clash checking."""
        elements = []

        sprinkler_config = fp_config.get('sprinkler', {})
        pipe_config = fp_config.get('pipe', {})

        spacing = sprinkler_config.get('spacing_m', 3.5)
        z_offset_sprinkler = self.zone_manager.get_z_offset('FP_sprinkler')
        z_offset_pipe_main = self.zone_manager.get_z_offset('FP_pipe_main')
        z_offset_pipe_branch = self.zone_manager.get_z_offset('FP_pipe_branch')

        margin = 10.0  # Stay away from building edges

        min_x = self.bounds['min_x'] + margin
        max_x = self.bounds['max_x'] - margin
        min_y = self.bounds['min_y'] + margin
        max_y = self.bounds['max_y'] - margin
        slab_cx = self.bounds['slab_cx']
        slab_cy = self.bounds['slab_cy']

        for floor_id, floor_data in floors_config.items():
            if floor_id == 'ROOF':
                continue

            elevation = floor_data.get('elevation_m', 0.0)
            floor_height = floor_data.get('floor_to_floor_m', 4.0)
            ceiling_z = elevation + floor_height

            # Generate sprinkler grid
            y = min_y
            row_heads = []
            while y <= max_y:
                x = min_x
                row = []
                while x <= max_x:
                    sprinkler_z = ceiling_z + z_offset_sprinkler

                    # Check for clashes and find clear position
                    clear_x, clear_y = self.clash_checker.find_clear_position(
                        x, y, sprinkler_z, 0.05, 'FP'
                    )

                    elements.append({
                        'guid': self._create_guid(),
                        'discipline': 'FP',
                        'ifc_class': 'IfcFireSuppressionTerminal',
                        'floor': floor_id,
                        'center_x': clear_x,
                        'center_y': clear_y,
                        'center_z': sprinkler_z,
                        'rotation_z': 0,
                        'length': 0.05,
                        'layer': f'SPRINKLER_{floor_id}',
                        'source_file': 'zones_config.json',
                        'polyline_points': None,
                        'sprinkler_config': {
                            'head_radius': sprinkler_config.get('head_radius_m', 0.025),
                            'head_length': sprinkler_config.get('head_length_m', 0.08)
                        }
                    })

                    self._register_element(clear_x, clear_y, sprinkler_z, 0.05)
                    row.append((clear_x, clear_y))
                    x += spacing
                row_heads.append(row)
                y += spacing

            # Generate pipe network
            pipe_z_main = ceiling_z + z_offset_pipe_main
            pipe_z_branch = ceiling_z + z_offset_pipe_branch

            if row_heads:
                # Main pipe along Y axis
                main_length = max_y - min_y
                elements.append({
                    'guid': self._create_guid(),
                    'discipline': 'FP',
                    'ifc_class': 'IfcPipeSegment',
                    'floor': floor_id,
                    'center_x': slab_cx,
                    'center_y': slab_cy,
                    'center_z': pipe_z_main,
                    'rotation_z': math.pi/2,
                    'length': main_length,
                    'layer': f'FP_MAIN_{floor_id}',
                    'source_file': 'zones_config.json',
                    'polyline_points': None,
                    'pipe_config': {
                        'radius': pipe_config.get('main_radius_m', 0.05),
                        'length': main_length
                    }
                })

                # Branch pipes
                for row in row_heads:
                    if row:
                        row_y = row[0][1]
                        branch_length = max_x - min_x
                        elements.append({
                            'guid': self._create_guid(),
                            'discipline': 'FP',
                            'ifc_class': 'IfcPipeSegment',
                            'floor': floor_id,
                            'center_x': slab_cx,
                            'center_y': row_y,
                            'center_z': pipe_z_branch,
                            'rotation_z': 0,
                            'length': branch_length,
                            'layer': f'FP_BRANCH_{floor_id}',
                            'source_file': 'zones_config.json',
                            'polyline_points': None,
                            'pipe_config': {
                                'radius': pipe_config.get('branch_radius_m', 0.025),
                                'length': branch_length
                            }
                        })

            # Generate smoke detectors (sparser grid than sprinklers)
            detector_spacing = spacing * 2  # Every other sprinkler position
            y = min_y
            while y <= max_y:
                x = min_x
                while x <= max_x:
                    detector_z = ceiling_z + z_offset_sprinkler - 0.05  # Slightly below sprinklers
                    elements.append({
                        'guid': self._create_guid(),
                        'discipline': 'FP',
                        'ifc_class': 'IfcAlarm',
                        'floor': floor_id,
                        'center_x': x,
                        'center_y': y,
                        'center_z': detector_z,
                        'rotation_z': 0,
                        'length': 0.1,
                        'layer': f'SMOKE_DETECTOR_{floor_id}',
                        'source_file': 'zones_config.json',
                        'polyline_points': None,
                        'alarm_config': {
                            'type': 'smoke_detector',
                            'radius': 0.05
                        }
                    })
                    x += detector_spacing
                y += detector_spacing

            # Generate break glass points near exits/corridors (wall-mounted)
            break_glass_positions = [
                (min_x + 2, slab_cy, 1.2),  # West entrance
                (max_x - 2, slab_cy, 1.2),  # East entrance
                (slab_cx, min_y + 2, 1.2),  # South entrance
                (slab_cx, max_y - 2, 1.2),  # North entrance
            ]

            for bgx, bgy, bgz in break_glass_positions:
                elements.append({
                    'guid': self._create_guid(),
                    'discipline': 'FP',
                    'ifc_class': 'IfcAlarm',
                    'floor': floor_id,
                    'center_x': bgx,
                    'center_y': bgy,
                    'center_z': elevation + bgz,
                    'rotation_z': 0,
                    'length': 0.1,
                    'layer': f'BREAK_GLASS_{floor_id}',
                    'source_file': 'zones_config.json',
                    'polyline_points': None,
                    'alarm_config': {
                        'type': 'break_glass',
                        'width': 0.1,
                        'height': 0.15
                    }
                })

            # Fire hose reels (wall-mounted cabinets)
            hose_reel_positions = [
                (min_x + 5, slab_cy - 10),
                (min_x + 5, slab_cy + 10),
                (max_x - 5, slab_cy - 10),
                (max_x - 5, slab_cy + 10),
            ]
            for hx, hy in hose_reel_positions:
                elements.append({
                    'guid': self._create_guid(),
                    'discipline': 'FP',
                    'ifc_class': 'IfcFireSuppressionTerminal',
                    'floor': floor_id,
                    'center_x': hx,
                    'center_y': hy,
                    'center_z': elevation + 1.0,  # Mounted at 1m height
                    'rotation_z': 0,
                    'length': 0.6,
                    'layer': f'HOSE_REEL_{floor_id}',
                    'source_file': 'zones_config.json',
                    'polyline_points': None,
                    'hose_reel_config': {
                        'width': 0.6,
                        'depth': 0.2,
                        'height': 0.8
                    }
                })

            # Fire extinguishers (near exits and high-risk areas)
            extinguisher_positions = [
                (slab_cx - 10, min_y + 5),
                (slab_cx + 10, min_y + 5),
                (slab_cx - 10, max_y - 5),
                (slab_cx + 10, max_y - 5),
            ]
            for ex, ey in extinguisher_positions:
                elements.append({
                    'guid': self._create_guid(),
                    'discipline': 'FP',
                    'ifc_class': 'IfcFireSuppressionTerminal',
                    'floor': floor_id,
                    'center_x': ex,
                    'center_y': ey,
                    'center_z': elevation + 0.8,
                    'rotation_z': 0,
                    'length': 0.15,
                    'layer': f'EXTINGUISHER_{floor_id}',
                    'source_file': 'zones_config.json',
                    'polyline_points': None,
                    'extinguisher_config': {
                        'type': 'ABC',
                        'height': 0.5
                    }
                })

        return elements


class ELECGenerator(DisciplineGenerator):
    """Electrical generator - lights and conduits."""

    @property
    def discipline(self) -> str:
        return 'ELEC'

    def generate(self, floors_config: Dict, elec_config: Dict) -> List[Dict]:
        """Generate ELEC elements with offset from FP to prevent clashes."""
        elements = []

        light_config = elec_config.get('light_fixture', {})
        conduit_config = elec_config.get('conduit', {})

        spacing = light_config.get('spacing_m', 4.0)
        z_offset_light = self.zone_manager.get_z_offset('ELEC_light')
        z_offset_conduit_main = self.zone_manager.get_z_offset('ELEC_conduit_main')
        z_offset_conduit_branch = self.zone_manager.get_z_offset('ELEC_conduit_branch')

        margin = 10.0
        grid_offset = spacing / 2  # Offset from FP grid

        min_x = self.bounds['min_x'] + margin
        max_x = self.bounds['max_x'] - margin
        min_y = self.bounds['min_y'] + margin
        max_y = self.bounds['max_y'] - margin
        slab_cx = self.bounds['slab_cx']
        slab_cy = self.bounds['slab_cy']

        for floor_id, floor_data in floors_config.items():
            if floor_id == 'ROOF':
                continue

            elevation = floor_data.get('elevation_m', 0.0)
            floor_height = floor_data.get('floor_to_floor_m', 4.0)
            ceiling_z = elevation + floor_height

            # Generate light grid (offset from sprinkler grid)
            y = min_y + grid_offset
            row_lights = []
            while y <= max_y:
                x = min_x + grid_offset
                row = []
                while x <= max_x:
                    light_z = ceiling_z + z_offset_light

                    # Check for clashes
                    clear_x, clear_y = self.clash_checker.find_clear_position(
                        x, y, light_z, 0.3, 'ELEC'
                    )

                    elements.append({
                        'guid': self._create_guid(),
                        'discipline': 'ELEC',
                        'ifc_class': 'IfcLightFixture',
                        'floor': floor_id,
                        'center_x': clear_x,
                        'center_y': clear_y,
                        'center_z': light_z,
                        'rotation_z': 0,
                        'length': light_config.get('width_m', 0.6),
                        'layer': f'LIGHT_{floor_id}',
                        'source_file': 'zones_config.json',
                        'polyline_points': None,
                        'light_config': {
                            'width': light_config.get('width_m', 0.6),
                            'depth': light_config.get('depth_m', 0.6),
                            'thickness': light_config.get('thickness_m', 0.05)
                        }
                    })

                    self._register_element(clear_x, clear_y, light_z, 0.3)
                    row.append((clear_x, clear_y))
                    x += spacing
                row_lights.append(row)
                y += spacing

            # Generate conduit network
            conduit_z_main = ceiling_z + z_offset_conduit_main
            conduit_z_branch = ceiling_z + z_offset_conduit_branch

            if row_lights:
                # Main conduit (offset from FP main)
                main_length = max_y - min_y
                elements.append({
                    'guid': self._create_guid(),
                    'discipline': 'ELEC',
                    'ifc_class': 'IfcCableCarrierSegment',
                    'floor': floor_id,
                    'center_x': slab_cx + 2,  # Offset from FP
                    'center_y': slab_cy,
                    'center_z': conduit_z_main,
                    'rotation_z': math.pi/2,
                    'length': main_length,
                    'layer': f'ELEC_MAIN_{floor_id}',
                    'source_file': 'zones_config.json',
                    'polyline_points': None,
                    'conduit_config': {
                        'length': main_length,
                        'width': conduit_config.get('main_width_m', 0.15),
                        'height': conduit_config.get('main_height_m', 0.08)
                    }
                })

                # Branch conduits
                for row in row_lights:
                    if row:
                        row_y = row[0][1]
                        branch_length = max_x - min_x
                        elements.append({
                            'guid': self._create_guid(),
                            'discipline': 'ELEC',
                            'ifc_class': 'IfcCableCarrierSegment',
                            'floor': floor_id,
                            'center_x': slab_cx,
                            'center_y': row_y,
                            'center_z': conduit_z_branch,
                            'rotation_z': 0,
                            'length': branch_length,
                            'layer': f'ELEC_BRANCH_{floor_id}',
                            'source_file': 'zones_config.json',
                            'polyline_points': None,
                            'conduit_config': {
                                'length': branch_length,
                                'width': conduit_config.get('branch_width_m', 0.1),
                                'height': conduit_config.get('branch_height_m', 0.05)
                            }
                        })

            # Generate power outlets along perimeter (wall-mounted)
            outlet_height = 0.4  # Standard outlet height from floor
            outlet_spacing = 6.0  # Every 6 meters along walls

            # West and East walls
            for wall_x in [min_x + 1, max_x - 1]:
                y_pos = min_y + outlet_spacing
                while y_pos <= max_y - outlet_spacing:
                    elements.append({
                        'guid': self._create_guid(),
                        'discipline': 'ELEC',
                        'ifc_class': 'IfcElectricAppliance',
                        'floor': floor_id,
                        'center_x': wall_x,
                        'center_y': y_pos,
                        'center_z': elevation + outlet_height,
                        'rotation_z': 0,
                        'length': 0.1,
                        'layer': f'OUTLET_{floor_id}',
                        'source_file': 'zones_config.json',
                        'polyline_points': None,
                        'outlet_config': {
                            'type': 'power_outlet',
                            'width': 0.08,
                            'height': 0.12
                        }
                    })
                    y_pos += outlet_spacing

            # North and South walls
            for wall_y in [min_y + 1, max_y - 1]:
                x_pos = min_x + outlet_spacing
                while x_pos <= max_x - outlet_spacing:
                    elements.append({
                        'guid': self._create_guid(),
                        'discipline': 'ELEC',
                        'ifc_class': 'IfcElectricAppliance',
                        'floor': floor_id,
                        'center_x': x_pos,
                        'center_y': wall_y,
                        'center_z': elevation + outlet_height,
                        'rotation_z': 0,
                        'length': 0.1,
                        'layer': f'OUTLET_{floor_id}',
                        'source_file': 'zones_config.json',
                        'polyline_points': None,
                        'outlet_config': {
                            'type': 'power_outlet',
                            'width': 0.08,
                            'height': 0.12
                        }
                    })
                    x_pos += outlet_spacing

            # Light switches near doors (4 per floor, at entrances)
            switch_positions = [
                (min_x + 3, slab_cy),
                (max_x - 3, slab_cy),
                (slab_cx, min_y + 3),
                (slab_cx, max_y - 3),
            ]
            for sx, sy in switch_positions:
                elements.append({
                    'guid': self._create_guid(),
                    'discipline': 'ELEC',
                    'ifc_class': 'IfcElectricAppliance',
                    'floor': floor_id,
                    'center_x': sx,
                    'center_y': sy,
                    'center_z': elevation + 1.2,  # Switch height
                    'rotation_z': 0,
                    'length': 0.08,
                    'layer': f'SWITCH_{floor_id}',
                    'source_file': 'zones_config.json',
                    'polyline_points': None,
                    'outlet_config': {
                        'type': 'light_switch',
                        'width': 0.08,
                        'height': 0.12
                    }
                })

            # CCTV cameras (ceiling-mounted at strategic locations)
            cctv_positions = [
                (min_x + 8, min_y + 8),   # SW corner
                (max_x - 8, min_y + 8),   # SE corner
                (min_x + 8, max_y - 8),   # NW corner
                (max_x - 8, max_y - 8),   # NE corner
                (slab_cx, min_y + 10),    # South entrance
                (slab_cx, max_y - 10),    # North entrance
            ]
            for cx, cy in cctv_positions:
                elements.append({
                    'guid': self._create_guid(),
                    'discipline': 'ELEC',
                    'ifc_class': 'IfcElectricAppliance',
                    'floor': floor_id,
                    'center_x': cx,
                    'center_y': cy,
                    'center_z': ceiling_z - 0.3,  # Ceiling mounted
                    'rotation_z': 0,
                    'length': 0.15,
                    'layer': f'CCTV_{floor_id}',
                    'source_file': 'zones_config.json',
                    'polyline_points': None,
                    'cctv_config': {
                        'type': 'dome',
                        'radius': 0.1
                    }
                })

            # PA speakers (ceiling-mounted for announcements)
            pa_positions = [
                (slab_cx - 12, slab_cy - 10),
                (slab_cx + 12, slab_cy - 10),
                (slab_cx - 12, slab_cy + 10),
                (slab_cx + 12, slab_cy + 10),
            ]
            for px, py in pa_positions:
                elements.append({
                    'guid': self._create_guid(),
                    'discipline': 'ELEC',
                    'ifc_class': 'IfcElectricAppliance',
                    'floor': floor_id,
                    'center_x': px,
                    'center_y': py,
                    'center_z': ceiling_z - 0.2,
                    'rotation_z': 0,
                    'length': 0.25,
                    'layer': f'PA_SPEAKER_{floor_id}',
                    'source_file': 'zones_config.json',
                    'polyline_points': None,
                    'speaker_config': {
                        'type': 'ceiling',
                        'diameter': 0.2
                    }
                })

            # Exit signs (illuminated, above exits)
            exit_sign_positions = [
                (min_x + 2, slab_cy),   # West exit
                (max_x - 2, slab_cy),   # East exit
                (slab_cx, min_y + 2),   # South exit
                (slab_cx, max_y - 2),   # North exit
                # Internal circulation exits
                (slab_cx - 10, slab_cy),
                (slab_cx + 10, slab_cy),
            ]
            for ex_x, ex_y in exit_sign_positions:
                elements.append({
                    'guid': self._create_guid(),
                    'discipline': 'ELEC',
                    'ifc_class': 'IfcLightFixture',
                    'floor': floor_id,
                    'center_x': ex_x,
                    'center_y': ex_y,
                    'center_z': elevation + 2.5,  # Above door height
                    'rotation_z': 0,
                    'length': 0.3,
                    'layer': f'EXIT_SIGN_{floor_id}',
                    'source_file': 'zones_config.json',
                    'polyline_points': None,
                    'exit_sign_config': {
                        'width': 0.3,
                        'height': 0.15,
                        'illuminated': True
                    }
                })

            # Emergency lights (battery backup, along escape routes)
            emergency_spacing = 8.0
            # Along main corridors
            for corr_y in [slab_cy - 8, slab_cy, slab_cy + 8]:
                x_pos = min_x + 5
                while x_pos <= max_x - 5:
                    elements.append({
                        'guid': self._create_guid(),
                        'discipline': 'ELEC',
                        'ifc_class': 'IfcLightFixture',
                        'floor': floor_id,
                        'center_x': x_pos,
                        'center_y': corr_y,
                        'center_z': ceiling_z - 0.1,
                        'rotation_z': 0,
                        'length': 0.3,
                        'layer': f'EMERGENCY_LIGHT_{floor_id}',
                        'source_file': 'zones_config.json',
                        'polyline_points': None,
                        'emergency_config': {
                            'type': 'twin_spot',
                            'battery_backup': True
                        }
                    })
                    x_pos += emergency_spacing

            # Wayfinding signage (directional signs for gates, restrooms, exits)
            wayfinding_positions = [
                # Main circulation junctions
                (slab_cx - 15, slab_cy, 'GATES_A-B'),
                (slab_cx + 15, slab_cy, 'GATES_C-D'),
                (slab_cx, slab_cy - 12, 'DEPARTURE'),
                (slab_cx, slab_cy + 12, 'ARRIVAL'),
                # Near entrances
                (min_x + 8, slab_cy, 'INFO_WC'),
                (max_x - 8, slab_cy, 'INFO_WC'),
            ]
            for wx, wy, sign_type in wayfinding_positions:
                elements.append({
                    'guid': self._create_guid(),
                    'discipline': 'ELEC',
                    'ifc_class': 'IfcLightFixture',
                    'floor': floor_id,
                    'center_x': wx,
                    'center_y': wy,
                    'center_z': elevation + 2.6,  # Above head height
                    'rotation_z': 0,
                    'length': 0.6,
                    'layer': f'WAYFINDING_{floor_id}',
                    'source_file': 'zones_config.json',
                    'polyline_points': None,
                    'signage_config': {
                        'type': sign_type,
                        'width': 0.6,
                        'height': 0.3,
                        'backlit': True
                    }
                })

            # Emergency call points (SOS/help buttons near restrooms and exits)
            emergency_call_positions = [
                (min_x + 5, min_y + 8),   # Near NW corner
                (max_x - 5, min_y + 8),   # Near NE corner
                (min_x + 5, max_y - 8),   # Near SW corner
                (max_x - 5, max_y - 8),   # Near SE corner
            ]
            for ecx, ecy in emergency_call_positions:
                elements.append({
                    'guid': self._create_guid(),
                    'discipline': 'ELEC',
                    'ifc_class': 'IfcElectricAppliance',
                    'floor': floor_id,
                    'center_x': ecx,
                    'center_y': ecy,
                    'center_z': elevation + 1.2,  # Wall-mounted at reach height
                    'rotation_z': 0,
                    'length': 0.15,
                    'layer': f'EMERGENCY_CALL_{floor_id}',
                    'source_file': 'zones_config.json',
                    'polyline_points': None,
                    'call_point_config': {
                        'type': 'SOS',
                        'width': 0.12,
                        'height': 0.18
                    }
                })

        return elements


class ACMVGenerator(DisciplineGenerator):
    """ACMV generator - ducts and diffusers."""

    @property
    def discipline(self) -> str:
        return 'ACMV'

    def generate(self, floors_config: Dict, acmv_config: Dict) -> List[Dict]:
        """Generate ACMV elements with zone-based placement."""
        elements = []

        diffuser_config = acmv_config.get('diffuser', {})
        duct_config = acmv_config.get('duct', {})

        spacing = diffuser_config.get('spacing_m', 5.0)
        z_offset_diffuser = self.zone_manager.get_z_offset('ACMV_diffuser')
        z_offset_duct_main = self.zone_manager.get_z_offset('ACMV_duct_main')
        z_offset_duct_branch = self.zone_manager.get_z_offset('ACMV_duct_branch')

        margin = 12.0  # Stay away from building edges
        grid_offset = spacing / 2  # Offset from other grids

        min_x = self.bounds['min_x'] + margin
        max_x = self.bounds['max_x'] - margin
        min_y = self.bounds['min_y'] + margin
        max_y = self.bounds['max_y'] - margin
        slab_cx = self.bounds['slab_cx']
        slab_cy = self.bounds['slab_cy']

        for floor_id, floor_data in floors_config.items():
            if floor_id == 'ROOF':
                continue

            elevation = floor_data.get('elevation_m', 0.0)
            floor_height = floor_data.get('floor_to_floor_m', 4.0)
            ceiling_z = elevation + floor_height

            # Generate diffuser grid (offset from ELEC grid)
            y = min_y + grid_offset * 1.5  # Additional offset from ELEC
            row_diffusers = []
            while y <= max_y:
                x = min_x + grid_offset * 1.5
                row = []
                while x <= max_x:
                    diffuser_z = ceiling_z + z_offset_diffuser

                    # Check for clashes
                    clear_x, clear_y = self.clash_checker.find_clear_position(
                        x, y, diffuser_z, 0.25, 'ACMV'
                    )

                    elements.append({
                        'guid': self._create_guid(),
                        'discipline': 'ACMV',
                        'ifc_class': 'IfcAirTerminal',
                        'floor': floor_id,
                        'center_x': clear_x,
                        'center_y': clear_y,
                        'center_z': diffuser_z,
                        'rotation_z': 0,
                        'length': diffuser_config.get('size_m', 0.6),
                        'layer': f'DIFFUSER_{floor_id}',
                        'source_file': 'zones_config.json',
                        'polyline_points': None,
                        'diffuser_config': {
                            'size': diffuser_config.get('size_m', 0.6),
                            'depth': diffuser_config.get('depth_m', 0.15)
                        }
                    })

                    self._register_element(clear_x, clear_y, diffuser_z, 0.25)
                    row.append((clear_x, clear_y))
                    x += spacing
                row_diffusers.append(row)
                y += spacing

            # Generate duct network
            duct_z_main = ceiling_z + z_offset_duct_main
            duct_z_branch = ceiling_z + z_offset_duct_branch

            if row_diffusers:
                # Main duct along Y axis (offset from FP and ELEC)
                main_length = max_y - min_y
                elements.append({
                    'guid': self._create_guid(),
                    'discipline': 'ACMV',
                    'ifc_class': 'IfcDuctSegment',
                    'floor': floor_id,
                    'center_x': slab_cx - 3,  # Offset from ELEC
                    'center_y': slab_cy,
                    'center_z': duct_z_main,
                    'rotation_z': math.pi/2,
                    'length': main_length,
                    'layer': f'ACMV_MAIN_{floor_id}',
                    'source_file': 'zones_config.json',
                    'polyline_points': None,
                    'duct_config': {
                        'length': main_length,
                        'width': duct_config.get('main_width_m', 0.4),
                        'height': duct_config.get('main_height_m', 0.3)
                    }
                })

                # Branch ducts
                for row in row_diffusers:
                    if row:
                        row_y = row[0][1]
                        branch_length = max_x - min_x
                        elements.append({
                            'guid': self._create_guid(),
                            'discipline': 'ACMV',
                            'ifc_class': 'IfcDuctSegment',
                            'floor': floor_id,
                            'center_x': slab_cx,
                            'center_y': row_y,
                            'center_z': duct_z_branch,
                            'rotation_z': 0,
                            'length': branch_length,
                            'layer': f'ACMV_BRANCH_{floor_id}',
                            'source_file': 'zones_config.json',
                            'polyline_points': None,
                            'duct_config': {
                                'length': branch_length,
                                'width': duct_config.get('branch_width_m', 0.25),
                                'height': duct_config.get('branch_height_m', 0.2)
                            }
                        })

        return elements


class MEPGeneratorOrchestrator:
    """Orchestrates all MEP discipline generators."""

    def __init__(self, zones_config_path: str, building_config_path: str):
        self.zone_manager = ZoneManager(zones_config_path)
        self.clash_checker = ClashChecker(clearance=0.3)

        with open(building_config_path) as f:
            self.building_config = json.load(f)

        self.bounds = None  # Set by calculate_bounds()

    def calculate_bounds(self, structural_elements: List[Dict]) -> Dict:
        """Calculate building bounds from structural elements."""
        if not structural_elements:
            return {
                'min_x': -25, 'max_x': 25,
                'min_y': -45, 'max_y': 30,
                'slab_cx': 0, 'slab_cy': -7.5
            }

        min_x = min(e['center_x'] for e in structural_elements)
        max_x = max(e['center_x'] for e in structural_elements)
        min_y = min(e['center_y'] for e in structural_elements)
        max_y = max(e['center_y'] for e in structural_elements)

        return {
            'min_x': min_x, 'max_x': max_x,
            'min_y': min_y, 'max_y': max_y,
            'slab_cx': (min_x + max_x) / 2,
            'slab_cy': (min_y + max_y) / 2
        }

    def generate_all(self, structural_elements: List[Dict]) -> List[Dict]:
        """Generate all MEP elements with clash checking."""
        self.bounds = self.calculate_bounds(structural_elements)

        mep_config = self.building_config.get('mep_config', {})
        floors_config = self.building_config.get('floors', {})
        gen_options = self.building_config.get('generation_options', {})

        all_elements = []

        # Generate FP first
        if gen_options.get('generate_fire_protection', False):
            fp_gen = FPGenerator(self.zone_manager, self.clash_checker, self.bounds)
            fp_elements = fp_gen.generate(floors_config, mep_config.get('fire_protection', {}))
            all_elements.extend(fp_elements)
            print(f"  FP: {len(fp_elements)} elements")

        # Generate ELEC (uses clash checker to avoid FP)
        if gen_options.get('generate_electrical', False):
            elec_gen = ELECGenerator(self.zone_manager, self.clash_checker, self.bounds)
            elec_elements = elec_gen.generate(floors_config, mep_config.get('electrical', {}))
            all_elements.extend(elec_elements)
            print(f"  ELEC: {len(elec_elements)} elements")

        # Generate ACMV (uses clash checker to avoid FP and ELEC)
        if gen_options.get('generate_acmv', False):
            acmv_gen = ACMVGenerator(self.zone_manager, self.clash_checker, self.bounds)
            acmv_elements = acmv_gen.generate(floors_config, mep_config.get('acmv', {}))
            all_elements.extend(acmv_elements)
            print(f"  ACMV: {len(acmv_elements)} elements")

        return all_elements


if __name__ == '__main__':
    # Test the generators
    import sys

    base_dir = Path(__file__).parent.parent
    zones_path = base_dir / 'zones_config.json'
    building_path = base_dir / 'building_config.json'

    if not zones_path.exists():
        print(f"ERROR: {zones_path} not found")
        sys.exit(1)

    orchestrator = MEPGeneratorOrchestrator(str(zones_path), str(building_path))

    # Test with dummy structural elements
    test_structural = [
        {'center_x': -25, 'center_y': -45, 'ifc_class': 'IfcColumn'},
        {'center_x': 25, 'center_y': 30, 'ifc_class': 'IfcColumn'},
    ]

    elements = orchestrator.generate_all(test_structural)
    print(f"\nGenerated {len(elements)} total MEP elements")
