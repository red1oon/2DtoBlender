#!/usr/bin/env python3
"""
Building Standards Module

Source of Truth: TB-LKTN_COMPLETE_SPECIFICATION.md Section 4 & 13
Standards: UBBL 1984, MS 1184 (Malaysian Standards)

All dimensions in meters unless specified.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


# =============================================================================
# UBBL 1984 (Uniform Building By-Laws 1984)
# =============================================================================

@dataclass
class RoomRequirements:
    """UBBL By-Law 42-44: Minimum room requirements"""
    min_area: float  # m²
    min_width: float  # m
    min_height: float  # m


UBBL_ROOM_REQUIREMENTS = {
    'bedroom': RoomRequirements(
        min_area=6.5,   # UBBL By-Law 42
        min_width=2.0,  # UBBL By-Law 42
        min_height=2.5  # UBBL By-Law 42
    ),
    'kitchen': RoomRequirements(
        min_area=0.0,   # No minimum area requirement
        min_width=0.0,
        min_height=2.25  # UBBL By-Law 43
    ),
    'bathroom': RoomRequirements(
        min_area=1.5,   # UBBL By-Law 44 (bathroom only)
        min_width=0.75,  # UBBL By-Law 44
        min_height=2.0   # UBBL By-Law 44
    ),
    'bathroom_wc': RoomRequirements(
        min_area=2.0,   # UBBL By-Law 44 (bathroom + WC)
        min_width=0.75,
        min_height=2.0
    ),
    'toilet': RoomRequirements(
        min_area=1.5,   # UBBL By-Law 44
        min_width=0.75,
        min_height=2.0
    )
}


@dataclass
class DoorRequirements:
    """UBBL door requirements"""
    min_width_mm: int   # Minimum clear width
    height_mm: int      # Standard height
    swing_direction: Optional[str] = None  # 'inward', 'outward', or None


UBBL_DOOR_REQUIREMENTS = {
    'main_entrance': DoorRequirements(
        min_width_mm=900,
        height_mm=2100
    ),
    'bedroom': DoorRequirements(
        min_width_mm=800,
        height_mm=2100
    ),
    'bathroom': DoorRequirements(
        min_width_mm=700,
        height_mm=2100,
        swing_direction='outward'  # MANDATORY: Safety (unconscious person blocking)
    ),
    'toilet': DoorRequirements(
        min_width_mm=700,
        height_mm=2100,
        swing_direction='outward'  # MANDATORY: Safety
    ),
    'general': DoorRequirements(
        min_width_mm=750,
        height_mm=2100
    )
}


@dataclass
class WindowRequirements:
    """UBBL By-Law 39: Natural light and ventilation"""
    natural_light_percentage: float  # % of floor area
    ventilation_percentage: float    # % of floor area (openable)
    bathroom_min_area: float         # m² per bathroom unit


UBBL_WINDOW_REQUIREMENTS = WindowRequirements(
    natural_light_percentage=10.0,  # UBBL By-Law 39: ≥10%
    ventilation_percentage=5.0,      # UBBL By-Law 39: ≥5%
    bathroom_min_area=0.2            # UBBL By-Law 39: ≥0.2 m²
)


@dataclass
class EgressRequirements:
    """International/IRC: Bedroom emergency egress"""
    min_opening_area: float      # m²
    min_width: float            # m
    min_height: float           # m
    max_sill_height: float      # m


EGRESS_REQUIREMENTS = EgressRequirements(
    min_opening_area=0.53,  # 5.7 sq ft
    min_width=0.508,        # 20 inches
    min_height=0.610,       # 24 inches
    max_sill_height=1.118   # 44 inches
)


# =============================================================================
# MS 1184 (Malaysian Standard for Accessible Design)
# =============================================================================

@dataclass
class ClearanceRequirements:
    """MS 1184: Mandatory clearances around fixtures"""
    front: float   # meters
    rear: float    # meters
    left: float    # meters
    right: float   # meters
    top: Optional[float] = None     # meters (for wall-mounted)
    bottom: Optional[float] = None  # meters (for wall-mounted)


MS_1184_CLEARANCES = {
    'toilet': ClearanceRequirements(
        front=0.6,   # MS 1184 MANDATORY
        rear=0.0,
        left=0.3,    # MS 1184 MANDATORY
        right=0.3    # MS 1184 MANDATORY
    ),
    'basin': ClearanceRequirements(
        front=0.5,   # MS 1184 MANDATORY
        rear=0.0,
        left=0.2,    # MS 1184 MANDATORY
        right=0.2    # MS 1184 MANDATORY
    ),
    'basin_wall_mounted': ClearanceRequirements(
        front=0.2,   # Minimal for very small Malaysian bathrooms
        rear=0.05,   # Tiny gap to avoid exact touching
        left=0.05,   # Minimal for tight spaces (50mm)
        right=0.05   # Minimal for tight spaces (50mm)
    ),
    'shower': ClearanceRequirements(
        front=0.6,
        rear=0.0,
        left=0.3,
        right=0.3
    ),
    'kitchen_sink': ClearanceRequirements(
        front=0.6,
        rear=0.0,
        left=0.3,
        right=0.3
    ),
    'stove': ClearanceRequirements(
        front=0.5,
        rear=0.0,
        left=0.2,
        right=0.2
    ),
    'refrigerator': ClearanceRequirements(
        front=0.6,  # Door swing clearance
        rear=0.1,   # Ventilation
        left=0.1,
        right=0.1
    ),
    'door_accessible': ClearanceRequirements(
        front=1.0,  # Wheelchair turning radius
        rear=0.8,
        left=0.0,
        right=0.0
    )
}


@dataclass
class FixtureHeightRequirements:
    """MS 1184: Fixture mounting heights"""
    height: float           # meters from floor
    tolerance: float = 0.05  # ±50mm tolerance


MS_1184_HEIGHTS = {
    'basin_rim': FixtureHeightRequirements(
        height=0.85,  # MS 1184 MANDATORY: 850mm
        tolerance=0.02
    ),
    'light_switch': FixtureHeightRequirements(
        height=1.2,   # Standard: 1200mm
        tolerance=0.1
    ),
    'power_outlet': FixtureHeightRequirements(
        height=0.3,   # Standard: 300mm
        tolerance=0.05
    ),
    'window_sill_viewing': FixtureHeightRequirements(
        height=0.9,   # Standard: 900mm (above furniture)
        tolerance=0.1
    ),
    'window_sill_ventilation': FixtureHeightRequirements(
        height=1.5,   # Standard: 1500mm (privacy)
        tolerance=0.1
    ),
    'showerhead': FixtureHeightRequirements(
        height=1.8,   # Standard: 1800mm
        tolerance=0.1
    ),
    'towel_rack': FixtureHeightRequirements(
        height=1.2,   # Standard: 1200mm
        tolerance=0.1
    ),
    'ceiling_light': FixtureHeightRequirements(
        height=2.95,  # Ceiling height (typical)
        tolerance=0.05
    ),
    'ceiling_fan': FixtureHeightRequirements(
        height=2.8,   # Below ceiling, above head clearance
        tolerance=0.1
    )
}


# =============================================================================
# Standard Object Dimensions (for placement calculations)
# =============================================================================

@dataclass
class ObjectDimensions:
    """Physical dimensions of standard objects"""
    width: float   # meters (X-axis)
    depth: float   # meters (Y-axis)
    height: float  # meters (Z-axis)


STANDARD_OBJECT_DIMENSIONS = {
    # Plumbing
    'toilet': ObjectDimensions(0.4, 0.6, 0.4),
    'basin': ObjectDimensions(0.5, 0.4, 0.2),
    'basin_wall_mounted': ObjectDimensions(0.35, 0.35, 0.15),  # Smaller for tight spaces
    'shower': ObjectDimensions(0.3, 0.3, 0.2),  # Showerhead fixture (not shower area)
    'shower_area': ObjectDimensions(0.9, 0.9, 2.2),
    'kitchen_sink': ObjectDimensions(0.6, 0.5, 0.2),

    # Appliances
    'stove': ObjectDimensions(0.6, 0.6, 0.9),
    'refrigerator': ObjectDimensions(0.7, 0.7, 1.8),

    # Furniture
    'bed_single': ObjectDimensions(1.0, 2.0, 0.5),
    'bed_queen': ObjectDimensions(1.5, 2.0, 0.5),
    'wardrobe_single': ObjectDimensions(0.9, 0.6, 2.0),
    'wardrobe_double': ObjectDimensions(1.8, 0.6, 2.0),
    'sofa_3seater': ObjectDimensions(2.0, 0.9, 0.8),
    'dining_table': ObjectDimensions(1.5, 0.9, 0.75),
    'study_desk': ObjectDimensions(1.2, 0.6, 0.75),
}


# =============================================================================
# Placement Constraints (from spec Section 5 & 6)
# =============================================================================

PLACEMENT_CONSTRAINTS = {
    'door': {
        'corner_clearance': 0.1,  # 100mm from corners (spec Section 5.3)
        'min_wall_length': 1.0,   # Minimum wall length for door placement
    },
    'window': {
        'corner_clearance': 0.3,  # 300mm from corners (spec Section 6.1)
        'min_wall_length': 1.2,   # Minimum wall length for window placement
    }
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_room_requirements(room_type: str) -> RoomRequirements:
    """Get UBBL requirements for room type"""
    room_type_lower = room_type.lower()

    if 'bedroom' in room_type_lower or 'bilik' in room_type_lower:
        return UBBL_ROOM_REQUIREMENTS['bedroom']
    elif 'bathroom' in room_type_lower or 'bilik_mandi' in room_type_lower:
        # Check if has WC
        if 'wc' in room_type_lower or 'tandas' in room_type_lower:
            return UBBL_ROOM_REQUIREMENTS['bathroom_wc']
        return UBBL_ROOM_REQUIREMENTS['bathroom']
    elif 'toilet' in room_type_lower or 'tandas' in room_type_lower:
        return UBBL_ROOM_REQUIREMENTS['toilet']
    elif 'kitchen' in room_type_lower or 'dapur' in room_type_lower:
        return UBBL_ROOM_REQUIREMENTS['kitchen']
    else:
        # Default to general habitable room
        return UBBL_ROOM_REQUIREMENTS['bedroom']


def get_door_requirements(room_type: str) -> DoorRequirements:
    """Get UBBL door requirements for room type"""
    room_type_lower = room_type.lower()

    if 'main' in room_type_lower or 'entrance' in room_type_lower or 'ruang_tamu' in room_type_lower:
        return UBBL_DOOR_REQUIREMENTS['main_entrance']
    elif 'bedroom' in room_type_lower or 'bilik' in room_type_lower:
        return UBBL_DOOR_REQUIREMENTS['bedroom']
    elif 'bathroom' in room_type_lower or 'bilik_mandi' in room_type_lower or 'tandas' in room_type_lower:
        return UBBL_DOOR_REQUIREMENTS['bathroom']
    else:
        return UBBL_DOOR_REQUIREMENTS['general']


def get_clearance_requirements(object_type: str) -> Optional[ClearanceRequirements]:
    """Get MS 1184 clearance requirements for object type"""
    obj_lower = object_type.lower()

    for key in MS_1184_CLEARANCES.keys():
        if key in obj_lower:
            return MS_1184_CLEARANCES[key]

    return None


def get_fixture_height(fixture_type: str) -> Optional[FixtureHeightRequirements]:
    """Get MS 1184 height requirements for fixture type"""
    fixture_lower = fixture_type.lower()

    for key in MS_1184_HEIGHTS.keys():
        if key in fixture_lower:
            return MS_1184_HEIGHTS[key]

    return None


def get_object_dimensions(object_type: str) -> Optional[ObjectDimensions]:
    """Get standard dimensions for object type"""
    obj_lower = object_type.lower()

    for key in STANDARD_OBJECT_DIMENSIONS.keys():
        if key in obj_lower:
            return STANDARD_OBJECT_DIMENSIONS[key]

    return None


def validate_room_area(room_type: str, actual_area: float) -> bool:
    """Check if room meets UBBL minimum area"""
    requirements = get_room_requirements(room_type)
    return actual_area >= requirements.min_area


def validate_door_width(room_type: str, actual_width_mm: int) -> bool:
    """Check if door meets UBBL minimum width"""
    requirements = get_door_requirements(room_type)
    return actual_width_mm >= requirements.min_width_mm


def calculate_required_bathroom_window_area() -> float:
    """Calculate required window area for bathroom (UBBL By-Law 39)"""
    return UBBL_WINDOW_REQUIREMENTS.bathroom_min_area


def calculate_required_natural_light_area(floor_area: float) -> float:
    """Calculate required window area for natural light (UBBL By-Law 39)"""
    return floor_area * (UBBL_WINDOW_REQUIREMENTS.natural_light_percentage / 100.0)


def calculate_required_ventilation_area(floor_area: float) -> float:
    """Calculate required openable window area (UBBL By-Law 39)"""
    return floor_area * (UBBL_WINDOW_REQUIREMENTS.ventilation_percentage / 100.0)


if __name__ == "__main__":
    # Test standards module
    print("UBBL 1984 + MS 1184 Standards Module")
    print("=" * 80)

    print("\n✓ Bedroom requirements:", UBBL_ROOM_REQUIREMENTS['bedroom'])
    print("✓ Bathroom door:", UBBL_DOOR_REQUIREMENTS['bathroom'])
    print("✓ Toilet clearances:", MS_1184_CLEARANCES['toilet'])
    print("✓ Basin height:", MS_1184_HEIGHTS['basin_rim'])

    print("\n✓ Standards module loaded successfully")
