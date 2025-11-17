#!/usr/bin/env python3
"""
Master Routing Script - Master Template Charting System.

Integrates all components:
- Corridor detection
- Intelligent routing (trunk + branch lines)
- Hierarchical pipe sizing
- Code compliance validation
- Geometry generation and database export

Usage:
    python3 master_routing.py <database_path> [--discipline FP] [--config template.json]
"""

import sys
import sqlite3
import uuid
import struct
import json
import math
from pathlib import Path
from typing import List, Dict, Tuple
import argparse

from corridor_detection import CorridorDetector
from intelligent_routing import IntelligentRoutingEngine, TrunkLine, BranchLine
from code_compliance import CodeComplianceValidator


def pack_vertices(vertices: List[Tuple[float, float, float]]) -> bytes:
    """Pack vertices into binary BLOB."""
    return struct.pack(f'<{len(vertices)*3}f', *[coord for v in vertices for coord in v])


def pack_faces(faces: List[Tuple[int, int, int]]) -> bytes:
    """Pack faces into binary BLOB."""
    return struct.pack(f'<{len(faces)*3}I', *[idx for face in faces for idx in face])


def pack_normals(normals: List[Tuple[float, float, float]]) -> bytes:
    """Pack normals into binary BLOB."""
    return struct.pack(f'<{len(normals)*3}f', *[coord for n in normals for coord in n])


def compute_hash(vertices_blob: bytes, faces_blob: bytes) -> str:
    """Compute hash for geometry."""
    import hashlib
    hasher = hashlib.sha256()
    hasher.update(vertices_blob)
    hasher.update(faces_blob)
    return hasher.hexdigest()


def generate_pipe_geometry(start: Tuple[float, float, float], end: Tuple[float, float, float], diameter: float):
    """
    Generate pipe/conduit segment geometry between two points.

    Args:
        start: (x, y, z) start point
        end: (x, y, z) end point
        diameter: Pipe diameter in meters

    Returns:
        (vertices, faces, normals) tuple
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    length = math.sqrt(dx*dx + dy*dy + dz*dz)

    if length < 0.01:
        return None, None, None

    # Midpoint
    mid_x = (start[0] + end[0]) / 2
    mid_y = (start[1] + end[1]) / 2
    mid_z = (start[2] + end[2]) / 2

    # Simple box approximation
    half_d = diameter / 2
    half_l = length / 2

    # Align along dominant axis
    if abs(dx) > abs(dy) and abs(dx) > abs(dz):
        # Horizontal (X-axis)
        vertices = [
            (mid_x - half_l, mid_y - half_d, mid_z - half_d),
            (mid_x + half_l, mid_y - half_d, mid_z - half_d),
            (mid_x + half_l, mid_y + half_d, mid_z - half_d),
            (mid_x - half_l, mid_y + half_d, mid_z - half_d),
            (mid_x - half_l, mid_y - half_d, mid_z + half_d),
            (mid_x + half_l, mid_y - half_d, mid_z + half_d),
            (mid_x + half_l, mid_y + half_d, mid_z + half_d),
            (mid_x - half_l, mid_y + half_d, mid_z + half_d),
        ]
    elif abs(dy) > abs(dz):
        # Horizontal (Y-axis)
        vertices = [
            (mid_x - half_d, mid_y - half_l, mid_z - half_d),
            (mid_x + half_d, mid_y - half_l, mid_z - half_d),
            (mid_x + half_d, mid_y + half_l, mid_z - half_d),
            (mid_x - half_d, mid_y + half_l, mid_z - half_d),
            (mid_x - half_d, mid_y - half_l, mid_z + half_d),
            (mid_x + half_d, mid_y - half_l, mid_z + half_d),
            (mid_x + half_d, mid_y + half_l, mid_z + half_d),
            (mid_x - half_d, mid_y + half_l, mid_z + half_d),
        ]
    else:
        # Vertical (Z-axis)
        vertices = [
            (mid_x - half_d, mid_y - half_d, mid_z - half_l),
            (mid_x + half_d, mid_y - half_d, mid_z - half_l),
            (mid_x + half_d, mid_y + half_d, mid_z - half_l),
            (mid_x - half_d, mid_y + half_d, mid_z - half_l),
            (mid_x - half_d, mid_y - half_d, mid_z + half_l),
            (mid_x + half_d, mid_y - half_d, mid_z + half_l),
            (mid_x + half_d, mid_y + half_d, mid_z + half_l),
            (mid_x - half_d, mid_y + half_d, mid_z + half_l),
        ]

    # Standard box faces
    faces = [
        (0, 1, 2), (0, 2, 3),  # Bottom
        (4, 7, 6), (4, 6, 5),  # Top
        (0, 4, 5), (0, 5, 1),  # Front
        (2, 6, 7), (2, 7, 3),  # Back
        (0, 3, 7), (0, 7, 4),  # Left
        (1, 5, 6), (1, 6, 2),  # Right
    ]

    normals = [
        (0, 0, -1), (0, 0, -1),  # Bottom
        (0, 0, 1), (0, 0, 1),    # Top
        (0, -1, 0), (0, -1, 0),  # Front
        (0, 1, 0), (0, 1, 0),    # Back
        (-1, 0, 0), (-1, 0, 0),  # Left
        (1, 0, 0), (1, 0, 0)     # Right
    ]

    return vertices, faces, normals


class MasterRoutingEngine:
    """Master routing engine that integrates all components."""

    def __init__(self, db_path: str, config_path: str = None):
        self.db_path = db_path
        self.config = self.load_config(config_path)
        self.stats = {
            'trunks_generated': 0,
            'branches_generated': 0,
            'total_length_m': 0.0,
            'violations': {'critical': 0, 'warnings': 0, 'info': 0}
        }

    def load_config(self, config_path: str = None) -> Dict:
        """Load JSON template configuration."""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            # Load building_config.json (NEW CONFIG-DRIVEN ARCHITECTURE)
            default_path = Path(__file__).parent.parent / 'building_config.json'
            if default_path.exists():
                with open(default_path, 'r') as f:
                    config = json.load(f)
                    print(f"✅ Loaded config-driven parameters from building_config.json")
                    print(f"   Building Type: {config.get('building_info', {}).get('building_type', 'N/A')}")
                    print(f"   Target Floor: {config.get('poc_config', {}).get('target_floor', 'N/A')}")
                    return config
            else:
                print("⚠️  Warning: No building_config.json found, using hardcoded defaults")
                print("   Run: python3 Scripts/preprocess_building.py --analyze")
                return {}

    def route_discipline(self, discipline: str, device_type: str, generate_devices: bool = False):
        """
        Complete routing workflow for a discipline.

        Args:
            discipline: 'FP', 'ELEC', etc.
            device_type: 'sprinkler', 'light_fixture', etc.
            generate_devices: If True, generate grid placements; if False, load from DB
        """
        print(f"\n{'='*80}")
        print(f"MASTER ROUTING: {discipline} - {device_type.upper()}")
        print(f"{'='*80}\n")

        # Get configuration for discipline from NEW config structure (mep_strategy)
        mep_strategy = self.config.get('mep_strategy', {})
        if discipline == 'FP':
            config = mep_strategy.get('FP', {})
        elif discipline == 'ELEC':
            config = mep_strategy.get('ELEC', {})
        else:
            print(f"⚠️  No configuration for discipline {discipline}, using defaults")
            config = {}

        # Extract parameters from NEW config structure
        if discipline == 'FP':
            trunk_diameter = config.get('trunk_pipe_diameter', 0.1)  # meters
            branch_diameter = config.get('branch_pipe_diameter', 0.025)
            drop_diameter = config.get('branch_pipe_diameter', 0.025)
            trunk_dn = int(trunk_diameter * 1000)  # Convert to DN
            branch_dn = int(branch_diameter * 1000)
            drop_dn = int(drop_diameter * 1000)
            device_spacing = config.get('sprinkler_spacing', 3.0)  # NEW: spacing from config
            device_height = config.get('fixture_height_above_floor', 3.8)  # NEW: height from config
            print(f"   FP Config: sprinkler_spacing={device_spacing}m, height={device_height}m")
        elif discipline == 'ELEC':
            trunk_diameter = config.get('cable_tray_width', 0.3)
            branch_diameter = config.get('conduit_diameter', 0.02)
            drop_diameter = config.get('conduit_diameter', 0.02)
            trunk_dn = int(trunk_diameter * 1000)
            branch_dn = int(branch_diameter * 1000)
            drop_dn = int(drop_diameter * 1000)
            device_spacing = config.get('fixture_spacing', 6.0)  # NEW: spacing from config
            device_height = config.get('fixture_height_above_floor', 4.0)  # NEW: height from config
            print(f"   ELEC Config: fixture_spacing={device_spacing}m, height={device_height}m")
        else:
            trunk_dn, branch_dn, drop_dn = 100, 50, 25
            device_spacing, device_height = 3.0, 4.0

        # Step 1: Intelligent routing
        print("Step 1: Intelligent Routing (Corridor-Based)")
        router = IntelligentRoutingEngine(self.db_path)
        router.route_system(
            discipline=discipline,
            device_type=device_type,
            trunk_diameter_dn=trunk_dn,
            branch_diameter_dn=branch_dn,
            drop_diameter_dn=drop_dn,
            generate_devices=generate_devices,
            device_spacing=device_spacing,  # NEW: Pass spacing from config
            device_height=device_height      # NEW: Pass height from config
        )

        # Step 2: Code compliance validation
        print("\nStep 2: Code Compliance Validation")
        validator = CodeComplianceValidator()

        # Load building bounds for validation
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MIN(center_x), MAX(center_x), MIN(center_y), MAX(center_y) FROM element_transforms")
        min_x, max_x, min_y, max_y = cursor.fetchone()
        building_bounds = {'min_x': min_x, 'max_x': max_x, 'min_y': min_y, 'max_y': max_y}
        conn.close()

        validation_results = validator.validate_system(
            devices=router.devices,
            discipline=discipline,
            walls=router.corridors,  # Pass corridors as walls for distance validation
            building_bounds=building_bounds
        )

        # Update stats
        self.stats['violations']['critical'] += validation_results['critical']
        self.stats['violations']['warnings'] += validation_results['warnings']
        self.stats['violations']['info'] += validation_results['info']

        # Step 3: Generate geometry and export to database
        print("\nStep 3: Geometry Generation and Database Export")
        self.export_to_database(router, discipline, config)

        # Print compliance report
        if validation_results['violations']:
            print("\n" + validator.generate_compliance_report())

        return router, validation_results

    def export_to_database(self, router: IntelligentRoutingEngine, discipline: str, config: Dict):
        """
        Export routing to database.

        Args:
            router: IntelligentRoutingEngine instance with routing data
            discipline: Discipline code
            config: Configuration dict
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get IFC class names from config
        if discipline == 'FP':
            trunk_ifc_class = 'IfcPipeSegment'
            branch_ifc_class = 'IfcPipeSegment'
        elif discipline == 'ELEC':
            trunk_ifc_class = 'IfcCableCarrierSegment'
            branch_ifc_class = 'IfcCableCarrierSegment'
        else:
            trunk_ifc_class = 'IfcFlowSegment'
            branch_ifc_class = 'IfcFlowSegment'

        # Export generated devices (if any)
        if hasattr(router, 'devices') and router.devices:
            # Check if devices were generated (not loaded from DB)
            device_sample = router.devices[0]
            if hasattr(device_sample, 'guid') and len(device_sample.guid) == 36:  # UUID format
                # These are generated devices - export them to database
                print(f"Exporting {len(router.devices)} generated devices...")

                from code_compliance import PlacementGenerator

                for device in router.devices:
                    # Skip if device already exists in database
                    cursor.execute("SELECT COUNT(*) FROM elements_meta WHERE guid = ?", (device.guid,))
                    if cursor.fetchone()[0] > 0:
                        continue  # Already in DB

                    # Get IFC class for device type
                    ifc_class = PlacementGenerator.ELEMENT_IFC_MAP.get(device.device_type, 'IfcBuildingElementProxy')

                    # Insert into elements_meta
                    cursor.execute("""
                        INSERT INTO elements_meta
                        (guid, discipline, ifc_class, filepath, element_name, element_type, inferred_shape_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        device.guid,
                        device.discipline,
                        ifc_class,
                        'Generated_Grid',
                        f'Generated_{device.device_type}',
                        device.device_type,
                        device.device_type
                    ))

                    # Insert position
                    cursor.execute("""
                        INSERT INTO element_transforms
                        (guid, center_x, center_y, center_z, length, rotation_z)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (device.guid, device.x, device.y, device.z, 0.2, 0.0))

                    # Insert into spatial index
                    cursor.execute("SELECT rowid FROM element_transforms WHERE guid = ?", (device.guid,))
                    rowid = cursor.fetchone()[0]

                    bbox_size = 0.1
                    cursor.execute("""
                        INSERT INTO elements_rtree (id, minX, maxX, minY, maxY, minZ, maxZ)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rowid,
                        device.x - bbox_size, device.x + bbox_size,
                        device.y - bbox_size, device.y + bbox_size,
                        device.z - bbox_size, device.z + bbox_size
                    ))

                print(f"✅ Exported {len(router.devices)} generated devices to database")

        # Export trunk lines
        print(f"Exporting {len(router.trunk_lines)} trunk lines...")
        for trunk in router.trunk_lines:
            for i in range(len(trunk.routing_points) - 1):
                start = trunk.routing_points[i]
                end = trunk.routing_points[i + 1]

                # Generate geometry
                vertices, faces, normals = generate_pipe_geometry(start, end, trunk.diameter)

                if not vertices:
                    continue

                # Create element
                guid = str(uuid.uuid4())

                cursor.execute("""
                    INSERT INTO elements_meta (guid, discipline, ifc_class, element_name, element_type, inferred_shape_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (guid, discipline, trunk_ifc_class, f'Trunk Line #{trunk.trunk_id} Seg {i+1}', 'TEMPLATE_TRUNK', 'box'))

                # Calculate segment center and length
                cx = (start[0] + end[0]) / 2
                cy = (start[1] + end[1]) / 2
                cz = (start[2] + end[2]) / 2
                length = math.sqrt((end[0]-start[0])**2 + (end[1]-start[1])**2 + (end[2]-start[2])**2)

                cursor.execute("""
                    INSERT INTO element_transforms (guid, center_x, center_y, center_z, length)
                    VALUES (?, ?, ?, ?, ?)
                """, (guid, cx, cy, cz, length))

                # Store geometry
                v_blob = pack_vertices(vertices)
                f_blob = pack_faces(faces)
                n_blob = pack_normals(normals)
                geom_hash = compute_hash(v_blob, f_blob)

                cursor.execute("""
                    INSERT OR REPLACE INTO base_geometries (guid, geometry_hash, vertices, faces, normals)
                    VALUES (?, ?, ?, ?, ?)
                """, (guid, geom_hash, v_blob, f_blob, n_blob))

                self.stats['trunks_generated'] += 1
                self.stats['total_length_m'] += length

        # Export branch lines
        print(f"Exporting {len(router.branch_lines)} branch lines...")
        for branch in router.branch_lines:
            start = branch.trunk_connection_point
            end = branch.device_location

            # Generate geometry
            vertices, faces, normals = generate_pipe_geometry(start, end, branch.diameter)

            if not vertices:
                continue

            # Create element
            guid = str(uuid.uuid4())

            cursor.execute("""
                INSERT INTO elements_meta (guid, discipline, ifc_class, element_name, element_type, inferred_shape_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (guid, discipline, branch_ifc_class, f'Branch Line #{branch.branch_id}', 'TEMPLATE_BRANCH', 'box'))

            cx = (start[0] + end[0]) / 2
            cy = (start[1] + end[1]) / 2
            cz = (start[2] + end[2]) / 2

            cursor.execute("""
                INSERT INTO element_transforms (guid, center_x, center_y, center_z, length)
                VALUES (?, ?, ?, ?, ?)
            """, (guid, cx, cy, cz, branch.length))

            # Store geometry
            v_blob = pack_vertices(vertices)
            f_blob = pack_faces(faces)
            n_blob = pack_normals(normals)
            geom_hash = compute_hash(v_blob, f_blob)

            cursor.execute("""
                INSERT OR REPLACE INTO base_geometries (guid, geometry_hash, vertices, faces, normals)
                VALUES (?, ?, ?, ?, ?)
            """, (guid, geom_hash, v_blob, f_blob, n_blob))

            self.stats['branches_generated'] += 1
            self.stats['total_length_m'] += branch.length

        conn.commit()
        conn.close()

        print(f"✅ Exported {self.stats['trunks_generated']} trunk segments")
        print(f"✅ Exported {self.stats['branches_generated']} branch lines")
        print(f"✅ Total routing length: {self.stats['total_length_m']:.1f}m")

    def generate_summary_report(self) -> str:
        """Generate final summary report."""
        report = []
        report.append("\n" + "="*80)
        report.append("MASTER ROUTING - FINAL SUMMARY")
        report.append("="*80)
        report.append(f"Database: {self.db_path}")
        report.append(f"Configuration: {self.config.get('template_name', 'Default')}")
        report.append("")
        report.append("ROUTING STATISTICS:")
        report.append(f"  Trunk segments:  {self.stats['trunks_generated']}")
        report.append(f"  Branch lines:    {self.stats['branches_generated']}")
        report.append(f"  Total length:    {self.stats['total_length_m']:.1f}m")
        report.append("")
        report.append("CODE COMPLIANCE:")
        report.append(f"  Critical violations: {self.stats['violations']['critical']}")
        report.append(f"  Warnings:            {self.stats['violations']['warnings']}")
        report.append(f"  Info:                {self.stats['violations']['info']}")
        report.append("")

        if self.stats['violations']['critical'] > 0:
            report.append("⚠️  CRITICAL VIOLATIONS FOUND - REVIEW REQUIRED BEFORE CONSTRUCTION")
        elif self.stats['violations']['warnings'] > 0:
            report.append("⚠️  Warnings found - recommend review")
        else:
            report.append("✅ All code compliance checks PASSED")

        report.append("="*80)

        return "\n".join(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Master Template Charting System - Intelligent MEP Routing'
    )
    parser.add_argument('database', help='Path to database file')
    parser.add_argument('--discipline', '-d', default='FP', choices=['FP', 'ELEC', 'HVAC', 'PLB'],
                       help='Discipline to route (default: FP)')
    parser.add_argument('--device-type', '-t', default=None,
                       help='Device type (default: auto-detect from discipline)')
    parser.add_argument('--config', '-c', default=None,
                       help='Path to custom JSON template configuration')
    parser.add_argument('--all-disciplines', '-a', action='store_true',
                       help='Route all disciplines (FP, ELEC)')
    parser.add_argument('--generate-devices', '-g', action='store_true',
                       help='GENERATE devices using code-compliant grid (instead of loading from DXF)')

    args = parser.parse_args()

    if not Path(args.database).exists():
        print(f"ERROR: Database not found: {args.database}")
        sys.exit(1)

    # Initialize master routing engine
    engine = MasterRoutingEngine(args.database, args.config)

    # Auto-detect device type if not specified
    device_type_map = {
        'FP': 'sprinkler',
        'ELEC': 'light_fixture',
        'HVAC': 'diffuser',
        'PLB': 'sink'
    }

    if args.all_disciplines:
        # Route all disciplines
        disciplines = [('FP', 'sprinkler'), ('ELEC', 'light_fixture')]
        for discipline, device_type in disciplines:
            engine.route_discipline(discipline, device_type, generate_devices=args.generate_devices)
    else:
        # Route single discipline
        device_type = args.device_type or device_type_map.get(args.discipline, 'sprinkler')
        engine.route_discipline(args.discipline, device_type, generate_devices=args.generate_devices)

    # Print final summary
    print(engine.generate_summary_report())

    print("\n✅ Master routing complete!")
    print("✅ Ready for Full Load in Bonsai/Blender!")


if __name__ == "__main__":
    main()
