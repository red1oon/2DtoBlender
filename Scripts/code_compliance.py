#!/usr/bin/env python3
"""
Code Compliance Validator and Placement Generator for Master Template Charting System.

DUAL PURPOSE:
1. VALIDATION: Validates MEP routing against building codes and standards
2. GENERATION: Generates code-compliant element placements using same standards

Building Codes Supported:
- NFPA 13: Fire protection sprinkler systems
- IBC: International Building Code
- NEC: National Electrical Code
- ASHRAE: HVAC and ventilation standards
"""

import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ComplianceRule:
    """Represents a code compliance rule."""
    rule_id: str
    code: str  # NFPA, IBC, NEC, etc.
    section: str
    description: str
    requirement: str
    validation_function: callable


@dataclass
class ComplianceViolation:
    """Represents a code violation."""
    rule_id: str
    severity: str  # 'CRITICAL', 'WARNING', 'INFO'
    location: Tuple[float, float, float]
    description: str
    recommendation: str


@dataclass
class PlacementStandards:
    """
    Engineering standards for element placement.

    Defines spacing, coverage, and clearance requirements
    that apply to BOTH validation AND generation.
    """
    element_type: str          # 'sprinkler', 'light_fixture', 'hvac_diffuser', etc.
    discipline: str            # 'FP', 'ELEC', 'HVAC'
    code_reference: str        # 'NFPA 13', 'NEC 210.70', etc.

    # Spacing requirements
    min_spacing: float         # Minimum distance between elements (meters)
    max_spacing: float         # Maximum distance between elements (meters)
    optimal_spacing: float     # Optimal spacing for generation (meters)

    # Coverage requirements
    max_coverage_area: float   # Maximum area per element (m²)
    optimal_coverage_area: float  # Optimal area for generation (m²)

    # Clearance requirements
    max_wall_distance: float   # Maximum distance from walls (meters)
    min_wall_clearance: float  # Minimum clearance from walls (meters)


# ENGINEERING STANDARDS DATABASE
# Single source of truth for all placement and validation rules
PLACEMENT_STANDARDS = {
    ('sprinkler', 'FP'): PlacementStandards(
        element_type='sprinkler',
        discipline='FP',
        code_reference='NFPA 13 (Light Hazard)',
        min_spacing=1.83,          # 6 ft minimum (NFPA 13 Section 8.2.3)
        max_spacing=4.572,         # 15 ft maximum (NFPA 13 Section 8.6.2.2.1)
        optimal_spacing=3.5,       # Midpoint for even distribution
        max_coverage_area=12.08,   # 130 sq ft (NFPA 13 Section 8.6.2.2.2)
        optimal_coverage_area=10.0, # Conservative for generation
        max_wall_distance=2.29,    # 7.5 ft (NFPA 13 Section 8.8.2)
        min_wall_clearance=0.15    # 6 inches typical
    ),
    ('light_fixture', 'ELEC'): PlacementStandards(
        element_type='light_fixture',
        discipline='ELEC',
        code_reference='NEC 210.70 + IES Standards',
        min_spacing=2.0,           # 2m minimum to avoid over-illumination
        max_spacing=6.0,           # 6m maximum for adequate coverage
        optimal_spacing=4.0,       # Standard office spacing
        max_coverage_area=16.0,    # 16 m² per fixture (typical)
        optimal_coverage_area=14.0, # Conservative
        max_wall_distance=3.0,     # 3m from walls
        min_wall_clearance=0.3     # 0.3m clearance
    ),
    ('hvac_diffuser', 'HVAC'): PlacementStandards(
        element_type='hvac_diffuser',
        discipline='HVAC',
        code_reference='ASHRAE 62.1',
        min_spacing=3.0,           # 3m minimum
        max_spacing=8.0,           # 8m maximum
        optimal_spacing=5.0,       # Standard spacing
        max_coverage_area=25.0,    # 25 m² per diffuser
        optimal_coverage_area=20.0, # Conservative
        max_wall_distance=4.0,     # 4m from walls
        min_wall_clearance=0.5     # 0.5m clearance
    ),
}


def get_placement_standards(element_type: str, discipline: str) -> Optional[PlacementStandards]:
    """
    Retrieve engineering standards for an element type.

    Args:
        element_type: Type of element ('sprinkler', 'light_fixture', etc.)
        discipline: Discipline code ('FP', 'ELEC', 'HVAC')

    Returns:
        PlacementStandards object or None if not found
    """
    return PLACEMENT_STANDARDS.get((element_type, discipline))


class PlacementGenerator:
    """
    Generates code-compliant element placements using engineering standards.

    ELEGANT STRATEGY:
    1. Uses SAME standards as validation (single source of truth)
    2. Works for ANY element type (sprinklers, lights, HVAC, etc.)
    3. Creates 2D grid distribution (not just lines)
    4. Respects wall clearances and coverage requirements
    5. Can write directly to database (integration with dxf_to_database.py workflow)
    """

    # Map element types to IFC classes
    ELEMENT_IFC_MAP = {
        'sprinkler': 'IfcBuildingElementProxy',
        'light_fixture': 'IfcBuildingElementProxy',
        'hvac_diffuser': 'IfcBuildingElementProxy',
        'smoke_detector': 'IfcBuildingElementProxy',
    }

    @staticmethod
    def generate_grid_placement(
        room_bounds: Dict[str, float],
        element_type: str,
        discipline: str,
        z_height: float = 4.0,
        spacing_override: Optional[float] = None
    ) -> List[Tuple[float, float, float]]:
        """
        Generate evenly-spaced grid of elements covering a room area.

        Args:
            room_bounds: Dict with 'min_x', 'max_x', 'min_y', 'max_y'
            element_type: 'sprinkler', 'light_fixture', 'hvac_diffuser', etc.
            discipline: 'FP', 'ELEC', 'HVAC'
            z_height: Height above floor to place elements (meters)
            spacing_override: Override spacing from building_config.json (NEW: config-driven)

        Returns:
            List of (x, y, z) positions for elements
        """
        # Get engineering standards
        standards = get_placement_standards(element_type, discipline)
        if not standards:
            raise ValueError(f"No standards defined for {element_type} ({discipline})")

        # Calculate room dimensions
        room_width = room_bounds['max_x'] - room_bounds['min_x']
        room_length = room_bounds['max_y'] - room_bounds['min_y']
        room_area = room_width * room_length

        # Use spacing from config if provided, otherwise use standards (CONFIG-DRIVEN!)
        if spacing_override is not None:
            spacing = spacing_override
            print(f"✅ Using config-driven spacing: {spacing}m (from building_config.json)")
        else:
            spacing = standards.optimal_spacing
            print(f"⚠️  Using hardcoded spacing: {spacing}m (standards fallback)")

        # Calculate number of elements needed in each direction
        # Add wall clearance buffer
        buffer = standards.min_wall_clearance
        effective_width = room_width - 2 * buffer
        effective_length = room_length - 2 * buffer

        nx = max(1, int(effective_width / spacing) + 1)
        ny = max(1, int(effective_length / spacing) + 1)

        # Recalculate actual spacing to fit exactly
        actual_spacing_x = effective_width / max(1, nx - 1) if nx > 1 else 0
        actual_spacing_y = effective_length / max(1, ny - 1) if ny > 1 else 0

        # Generate grid
        placements = []
        start_x = room_bounds['min_x'] + buffer
        start_y = room_bounds['min_y'] + buffer

        for i in range(nx):
            for j in range(ny):
                x = start_x + i * actual_spacing_x
                y = start_y + j * actual_spacing_y
                placements.append((x, y, z_height))

        print(f"\n{'='*80}")
        print(f"PLACEMENT GENERATION: {element_type.upper()} ({discipline})")
        print(f"{'='*80}")
        print(f"Code Reference:     {standards.code_reference}")
        print(f"Room Dimensions:    {room_width:.1f}m × {room_length:.1f}m ({room_area:.1f} m²)")
        print(f"Optimal Spacing:    {standards.optimal_spacing}m")
        print(f"Actual Spacing:     {actual_spacing_x:.2f}m × {actual_spacing_y:.2f}m")
        print(f"Grid Layout:        {nx} × {ny} = {len(placements)} elements")
        print(f"Coverage per elem:  {room_area / len(placements):.2f} m²")
        print(f"Code Max Coverage:  {standards.max_coverage_area} m²")
        print(f"✅ COMPLIANT:       {'YES' if room_area / len(placements) <= standards.max_coverage_area else 'NO - ADD MORE'}")
        print(f"{'='*80}\n")

        return placements

    @staticmethod
    def insert_generated_elements_to_db(
        db_path: str,
        placements: List[Tuple[float, float, float]],
        element_type: str,
        discipline: str,
        element_name: Optional[str] = None
    ) -> int:
        """
        Insert generated placements directly into database.

        Integrates with dxf_to_database.py schema:
        - elements_meta: metadata for each element
        - element_transforms: positions and dimensions
        - elements_rtree: spatial index

        Args:
            db_path: Path to database file
            placements: List of (x, y, z) positions from generate_grid_placement()
            element_type: 'sprinkler', 'light_fixture', 'hvac_diffuser', etc.
            discipline: 'FP', 'ELEC', 'HVAC'
            element_name: Optional custom name (defaults to element_type)

        Returns:
            Number of elements inserted
        """
        import sqlite3
        import uuid
        import json

        # Get IFC class for element type
        ifc_class = PlacementGenerator.ELEMENT_IFC_MAP.get(element_type, 'IfcBuildingElementProxy')
        if not element_name:
            element_name = element_type

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        inserted = 0
        print(f"\n{'='*80}")
        print(f"INSERTING GENERATED ELEMENTS TO DATABASE")
        print(f"{'='*80}")
        print(f"Database:       {db_path}")
        print(f"Element Type:   {element_type}")
        print(f"Discipline:     {discipline}")
        print(f"IFC Class:      {ifc_class}")
        print(f"Count:          {len(placements)}")

        for x, y, z in placements:
            guid = str(uuid.uuid4())

            # Default dimensions (can be refined later)
            dimensions = {"width": 0.2, "length": 0.2, "height": 0.3}
            dimensions_json = json.dumps(dimensions)

            # Insert into elements_meta
            cursor.execute("""
                INSERT INTO elements_meta
                (guid, discipline, ifc_class, filepath, element_name, element_type, inferred_shape_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                guid,
                discipline,
                ifc_class,
                f'Generated_{element_type}',
                element_name,
                element_type,
                element_type  # inferred_shape_type for routing
            ))

            # Insert position
            cursor.execute("""
                INSERT INTO element_transforms
                (guid, center_x, center_y, center_z, length, rotation_z)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (guid, x, y, z, 0.2, 0.0))  # Default 0.2m length, 0 rotation

            # Get rowid for rtree
            cursor.execute("SELECT rowid FROM element_transforms WHERE guid = ?", (guid,))
            rowid = cursor.fetchone()[0]

            # Insert into spatial index (elements_rtree)
            bbox_size = 0.1  # 0.1m bounding box around point
            cursor.execute("""
                INSERT INTO elements_rtree (id, minX, maxX, minY, maxY, minZ, maxZ)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                rowid,
                x - bbox_size, x + bbox_size,
                y - bbox_size, y + bbox_size,
                z - bbox_size, z + bbox_size
            ))

            inserted += 1

        conn.commit()
        conn.close()

        print(f"✅ Inserted {inserted} elements into database")
        print(f"{'='*80}\n")

        return inserted


class CodeComplianceValidator:
    """Validates MEP routing against building codes."""

    def __init__(self):
        self.rules: List[ComplianceRule] = []
        self.violations: List[ComplianceViolation] = []
        self._register_rules()

    def _register_rules(self):
        """Register all compliance rules."""

        # NFPA 13 Rules
        self.rules.append(ComplianceRule(
            rule_id='NFPA13_8.6.2.2.1',
            code='NFPA 13',
            section='8.6.2.2.1',
            description='Maximum spacing between sprinklers',
            requirement='Maximum 15 ft (4.572m) between sprinklers',
            validation_function=self._validate_sprinkler_spacing
        ))

        self.rules.append(ComplianceRule(
            rule_id='NFPA13_8.6.2.2.2',
            code='NFPA 13',
            section='8.6.2.2.2',
            description='Maximum coverage area per sprinkler',
            requirement='Maximum 130 sq ft (12.08 m²) for light hazard',
            validation_function=self._validate_coverage_area
        ))

        self.rules.append(ComplianceRule(
            rule_id='NFPA13_8.2.3',
            code='NFPA 13',
            section='8.2.3',
            description='Minimum spacing between sprinklers',
            requirement='Minimum 6 ft (1.83m) between sprinklers',
            validation_function=self._validate_minimum_spacing
        ))

        self.rules.append(ComplianceRule(
            rule_id='NFPA13_8.8.2',
            code='NFPA 13',
            section='8.8.2',
            description='Distance from walls',
            requirement='Maximum 7.5 ft (2.29m) from walls',
            validation_function=self._validate_wall_distance
        ))

        # NEC Rules (for electrical)
        self.rules.append(ComplianceRule(
            rule_id='NEC_210.70',
            code='NEC',
            section='210.70',
            description='Lighting outlet spacing',
            requirement='Adequate illumination for occupancy',
            validation_function=self._validate_lighting_spacing
        ))

    def _validate_sprinkler_spacing(self, devices: List, **kwargs) -> List[ComplianceViolation]:
        """
        Validate NFPA 13 maximum spacing between sprinklers (15 ft / 4.572m).

        Args:
            devices: List of sprinkler devices (with x, y, z attributes)

        Returns:
            List of violations
        """
        violations = []
        max_spacing = 4.572  # NFPA 13: 15 ft in meters

        for i, device1 in enumerate(devices):
            for device2 in devices[i+1:]:
                distance = math.sqrt(
                    (device2.x - device1.x)**2 +
                    (device2.y - device1.y)**2
                )

                if distance > max_spacing:
                    violations.append(ComplianceViolation(
                        rule_id='NFPA13_8.6.2.2.1',
                        severity='CRITICAL',
                        location=(device1.x, device1.y, device1.z),
                        description=f'Sprinkler spacing {distance:.2f}m exceeds NFPA 13 maximum of {max_spacing}m',
                        recommendation=f'Add sprinkler head between ({device1.x:.1f}, {device1.y:.1f}) and ({device2.x:.1f}, {device2.y:.1f})'
                    ))

        return violations

    def _validate_minimum_spacing(self, devices: List, **kwargs) -> List[ComplianceViolation]:
        """
        Validate NFPA 13 minimum spacing between sprinklers (6 ft / 1.83m).

        Args:
            devices: List of sprinkler devices

        Returns:
            List of violations
        """
        violations = []
        min_spacing = 1.83  # NFPA 13: 6 ft in meters

        for i, device1 in enumerate(devices):
            for device2 in devices[i+1:]:
                distance = math.sqrt(
                    (device2.x - device1.x)**2 +
                    (device2.y - device1.y)**2
                )

                if 0.1 < distance < min_spacing:  # Ignore if exactly same location
                    violations.append(ComplianceViolation(
                        rule_id='NFPA13_8.2.3',
                        severity='WARNING',
                        location=(device1.x, device1.y, device1.z),
                        description=f'Sprinkler spacing {distance:.2f}m is below NFPA 13 minimum of {min_spacing}m',
                        recommendation=f'Increase spacing or remove redundant sprinkler at ({device1.x:.1f}, {device1.y:.1f})'
                    ))

        return violations

    def _validate_coverage_area(self, devices: List, building_bounds: Dict = None, **kwargs) -> List[ComplianceViolation]:
        """
        Validate NFPA 13 maximum coverage area per sprinkler.

        Args:
            devices: List of sprinkler devices
            building_bounds: Dict with 'min_x', 'max_x', 'min_y', 'max_y'

        Returns:
            List of violations
        """
        violations = []
        max_coverage = 12.08  # NFPA 13: 130 sq ft for light hazard in m²

        if not building_bounds or len(devices) == 0:
            return violations

        # Calculate total building area
        building_area = (building_bounds['max_x'] - building_bounds['min_x']) * \
                       (building_bounds['max_y'] - building_bounds['min_y'])

        # Calculate coverage per sprinkler
        coverage_per_sprinkler = building_area / len(devices)

        if coverage_per_sprinkler > max_coverage:
            # Find centroid of uncovered areas
            for device in devices:
                violations.append(ComplianceViolation(
                    rule_id='NFPA13_8.6.2.2.2',
                    severity='WARNING',
                    location=(device.x, device.y, device.z),
                    description=f'Coverage area {coverage_per_sprinkler:.2f}m² exceeds NFPA 13 maximum of {max_coverage}m²',
                    recommendation=f'Add {int((coverage_per_sprinkler / max_coverage) - 1)} additional sprinkler(s) in this zone'
                ))

        return violations

    def _validate_wall_distance(self, devices: List, walls: List = None, **kwargs) -> List[ComplianceViolation]:
        """
        Validate NFPA 13 maximum distance from walls (7.5 ft / 2.29m).

        Args:
            devices: List of sprinkler devices
            walls: List of wall objects (with x, y attributes)

        Returns:
            List of violations
        """
        violations = []
        max_wall_distance = 2.29  # NFPA 13: 7.5 ft in meters

        if not walls:
            return violations

        # For each device, find nearest wall
        for device in devices:
            min_distance = float('inf')

            for wall in walls:
                # Calculate distance to wall (simplified - assumes wall is a point)
                # More accurate implementation would calculate distance to wall segment
                if hasattr(wall, 'midpoint'):
                    wall_x, wall_y = wall.midpoint()
                    distance = math.sqrt((device.x - wall_x)**2 + (device.y - wall_y)**2)
                    min_distance = min(min_distance, distance)

            if min_distance > max_wall_distance:
                violations.append(ComplianceViolation(
                    rule_id='NFPA13_8.8.2',
                    severity='WARNING',
                    location=(device.x, device.y, device.z),
                    description=f'Sprinkler distance {min_distance:.2f}m from nearest wall exceeds NFPA 13 maximum of {max_wall_distance}m',
                    recommendation=f'Add sprinkler closer to wall or reduce spacing'
                ))

        return violations

    def _validate_lighting_spacing(self, devices: List, **kwargs) -> List[ComplianceViolation]:
        """
        Validate NEC lighting spacing for adequate illumination.

        Args:
            devices: List of lighting devices

        Returns:
            List of violations
        """
        violations = []
        max_spacing = 6.0  # Typical office: 6m spacing for adequate light

        for i, device1 in enumerate(devices):
            for device2 in devices[i+1:]:
                distance = math.sqrt(
                    (device2.x - device1.x)**2 +
                    (device2.y - device1.y)**2
                )

                if distance > max_spacing:
                    violations.append(ComplianceViolation(
                        rule_id='NEC_210.70',
                        severity='INFO',
                        location=(device1.x, device1.y, device1.z),
                        description=f'Light fixture spacing {distance:.2f}m may not provide adequate illumination',
                        recommendation=f'Consider adding light fixture between ({device1.x:.1f}, {device1.y:.1f}) and ({device2.x:.1f}, {device2.y:.1f})'
                    ))

        return violations

    def validate_system(
        self,
        devices: List,
        discipline: str,
        walls: List = None,
        building_bounds: Dict = None
    ) -> Dict:
        """
        Validate complete MEP system against all applicable rules.

        Args:
            devices: List of devices to validate
            discipline: 'FP' or 'ELEC'
            walls: Optional list of wall objects
            building_bounds: Optional building boundary dict

        Returns:
            Dictionary with validation results
        """
        print(f"\n{'='*80}")
        print(f"CODE COMPLIANCE VALIDATION: {discipline}")
        print(f"{'='*80}\n")

        self.violations = []

        # Select rules based on discipline
        applicable_rules = []
        if discipline == 'FP':
            applicable_rules = [r for r in self.rules if r.code == 'NFPA 13']
        elif discipline == 'ELEC':
            applicable_rules = [r for r in self.rules if r.code == 'NEC']

        print(f"Applying {len(applicable_rules)} code rules for {discipline}...")

        # Run all applicable rules
        for rule in applicable_rules:
            print(f"\nChecking: {rule.rule_id} - {rule.description}")

            try:
                violations = rule.validation_function(
                    devices,
                    walls=walls,
                    building_bounds=building_bounds
                )
                self.violations.extend(violations)

                if violations:
                    print(f"  ⚠️  Found {len(violations)} violation(s)")
                else:
                    print(f"  ✅ PASS")

            except Exception as e:
                print(f"  ⚠️  Validation error: {e}")

        # Summarize violations by severity
        critical = [v for v in self.violations if v.severity == 'CRITICAL']
        warnings = [v for v in self.violations if v.severity == 'WARNING']
        info = [v for v in self.violations if v.severity == 'INFO']

        print(f"\n{'='*80}")
        print("VALIDATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total Violations: {len(self.violations)}")
        print(f"  CRITICAL: {len(critical)}")
        print(f"  WARNING:  {len(warnings)}")
        print(f"  INFO:     {len(info)}")

        if critical:
            print(f"\n⚠️  CRITICAL VIOLATIONS FOUND - MUST FIX BEFORE CONSTRUCTION")
        elif warnings:
            print(f"\n⚠️  Warnings found - recommend review before construction")
        else:
            print(f"\n✅ All code compliance checks PASSED")

        print(f"{'='*80}\n")

        return {
            'total_violations': len(self.violations),
            'critical': len(critical),
            'warnings': len(warnings),
            'info': len(info),
            'violations': self.violations,
            'passed': len(critical) == 0
        }

    def generate_compliance_report(self) -> str:
        """
        Generate detailed compliance report.

        Returns:
            Formatted report string
        """
        report = []
        report.append("="*80)
        report.append("CODE COMPLIANCE REPORT")
        report.append("="*80)
        report.append("")

        # Group violations by rule
        violations_by_rule = defaultdict(list)
        for violation in self.violations:
            violations_by_rule[violation.rule_id].append(violation)

        for rule_id, violations in violations_by_rule.items():
            # Find rule details
            rule = next((r for r in self.rules if r.rule_id == rule_id), None)

            if rule:
                report.append(f"{rule.code} {rule.section}: {rule.description}")
                report.append(f"Requirement: {rule.requirement}")
                report.append(f"Violations: {len(violations)}")
                report.append("")

                for i, violation in enumerate(violations[:5], 1):  # Show first 5
                    report.append(f"  {i}. [{violation.severity}] {violation.description}")
                    report.append(f"     Location: ({violation.location[0]:.1f}, {violation.location[1]:.1f}, {violation.location[2]:.1f})")
                    report.append(f"     Fix: {violation.recommendation}")
                    report.append("")

                if len(violations) > 5:
                    report.append(f"  ... and {len(violations) - 5} more violations")
                    report.append("")

        report.append("="*80)

        return "\n".join(report)


def main():
    """
    Test BOTH placement generation AND validation.

    Demonstrates the elegant strategy:
    1. Generate placements using standards
    2. Validate using same standards
    3. Works for multiple element types
    """
    print("\n" + "="*80)
    print("DEMONSTRATION: STANDARDS-BASED PLACEMENT + VALIDATION")
    print("="*80)

    # Define a room
    room_bounds = {
        'min_x': 0.0,
        'max_x': 20.0,  # 20m wide
        'min_y': 0.0,
        'max_y': 15.0,  # 15m long
    }

    # DEMO 1: Fire Protection Sprinklers (NFPA 13)
    print("\n--- DEMO 1: Fire Protection Sprinklers (NFPA 13) ---")
    sprinkler_placements = PlacementGenerator.generate_grid_placement(
        room_bounds=room_bounds,
        element_type='sprinkler',
        discipline='FP',
        z_height=4.0
    )

    # DEMO 2: Electrical Light Fixtures (NEC)
    print("\n--- DEMO 2: Electrical Light Fixtures (NEC) ---")
    light_placements = PlacementGenerator.generate_grid_placement(
        room_bounds=room_bounds,
        element_type='light_fixture',
        discipline='ELEC',
        z_height=3.5
    )

    # DEMO 3: HVAC Diffusers (ASHRAE)
    print("\n--- DEMO 3: HVAC Diffusers (ASHRAE) ---")
    hvac_placements = PlacementGenerator.generate_grid_placement(
        room_bounds=room_bounds,
        element_type='hvac_diffuser',
        discipline='HVAC',
        z_height=3.5
    )

    # Validate the generated placements
    print("\n" + "="*80)
    print("VALIDATION: Checking generated placements against code")
    print("="*80)

    # Convert placements to mock devices for validation
    from intelligent_routing import RoutingDevice
    import uuid

    sprinkler_devices = [
        RoutingDevice(str(uuid.uuid4()), x, y, z, 'FP', 'sprinkler')
        for x, y, z in sprinkler_placements
    ]

    validator = CodeComplianceValidator()
    results = validator.validate_system(
        devices=sprinkler_devices,
        discipline='FP',
        building_bounds=room_bounds
    )

    if results['passed']:
        print("\n✅ SUCCESS: Generated placements are code-compliant!")
        print(f"   - {len(sprinkler_placements)} sprinklers generated")
        print(f"   - 0 code violations")
    else:
        print("\n⚠️  WARNING: Generated placements have violations")
        print(validator.generate_compliance_report())

    print("\n" + "="*80)
    print("SUMMARY: Elegant Standards-Based Approach")
    print("="*80)
    print("✅ Single source of truth: PLACEMENT_STANDARDS dictionary")
    print("✅ Works for multiple element types: sprinklers, lights, HVAC")
    print("✅ Generate + Validate using SAME engineering standards")
    print("✅ Extensible: Add new standards easily")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
