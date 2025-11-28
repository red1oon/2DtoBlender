#!/usr/bin/env python3
"""
Room Template Integration - Augment text-based extraction with room inference

Architecture:
1. Keep text-based extracted objects (doors, windows, switches) - 18 objects
2. Detect rooms from walls
3. Apply ready-made room templates (bedroom_master, bathroom, kitchen, etc.)
4. Add furniture/fixtures from templates - ~35-40 objects
5. Return complete house: ~55-60 objects total

Uses existing: LocalLibrary/room_templates.json
"""

import json
import math
import sys
from pathlib import Path

# Add standards module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from standards.placement_engine import (
    StandardsPlacementEngine,
    MSViolation,
    RoomTooSmallError,
    CollisionError
)
from standards.building_standards import MS_1184_HEIGHTS

# LIBRARY NAME MAPPING - Maps template names to actual library object_types
# Updated 2025-11-27: All room objects now have LOD300 variants in LocalLibrary
LIBRARY_NAME_MAPPING = {
    # Furniture (LOD300 clones created in local library)
    'armchair_lod300': 'armchair_lod300',
    'bookshelf_5tier_lod300': 'bookshelf_5tier_lod300',
    'coffee_table_lod300': 'coffee_table',  # Keep base (no LOD300 created yet)
    'dining_chair_lod300': 'dining_chair_lod300',
    'dresser_6drawer_lod300': 'dresser_6drawer_lod300',
    'nightstand_lod300': 'nightstand_lod300',
    'office_chair_ergonomic_lod300': 'office_chair_ergonomic_lod300',
    'table_study_lod300': 'table_study_lod300',
    'toilet_paper_holder_lod300': 'toilet_paper_holder_lod300',

    # Plumbing (LOD300 clones created in local library)
    'basin_round_residential_lod300': 'basin_residential_lod300',
    'bathroom_vanity_1000_lod300': 'bathroom_vanity_1000_lod300',
    'floor_drain_lod300': 'floor_drain_lod300',
    'kitchen_sink_single_bowl_with_drainboard_lod300': 'kitchen_sink_single_bowl_lod200',
    'showerhead_fixed_lod300': 'showerhead_fixed_lod200',
    'towel_rack_mounted_lod300': 'towel_rack_wall_lod300',
    'towel_rack_wall_lod300': 'towel_rack_wall_lod300',

    # Appliances (LOD300 clones created in local library)
    'refrigerator_residential_lod300': 'refrigerator_residential_lod300',
    'stove_residential_lod300': 'stove_residential_lod300',
}

def map_to_library_name(template_name: str) -> str:
    """Map template object_type to actual library object_type"""
    return LIBRARY_NAME_MAPPING.get(template_name, template_name)


def load_room_templates():
    """Load ready-made room templates"""
    # Use local template file from LocalLibrary
    template_path = Path(__file__).parent.parent / "LocalLibrary" / "room_templates.json"

    with open(template_path) as f:
        data = json.load(f)

    return data['room_templates']


def detect_rooms_simple(building_dims):
    """
    Simple room detection for residential house

    Uses typical residential layout pattern:
    - Master bedroom (front left)
    - Secondary bedroom (front right)
    - Bathrooms (middle zones)
    - Kitchen (rear right)
    - Living room (rear left)
    """
    length = building_dims['length']
    breadth = building_dims['breadth']
    height = building_dims.get('height', 3.0)

    rooms = [
        {
            'name': 'master_bedroom',
            'template': 'bedroom_master',
            'bounds': {
                'min_x': 0,
                'max_x': length * 0.45,
                'min_y': 0,
                'max_y': breadth * 0.45
            },
            'center': [length * 0.225, breadth * 0.225],
            'area': (length * 0.45) * (breadth * 0.45)
        },
        {
            'name': 'bedroom_2',
            'template': 'bedroom_standard',
            'bounds': {
                'min_x': length * 0.55,
                'max_x': length,
                'min_y': 0,
                'max_y': breadth * 0.40
            },
            'center': [length * 0.775, breadth * 0.20],
            'area': (length * 0.45) * (breadth * 0.40)
        },
        {
            'name': 'bathroom_master',
            'template': 'bathroom',
            'bounds': {
                'min_x': length * 0.45,
                'max_x': length * 0.55,
                'min_y': 0,
                'max_y': breadth * 0.30
            },
            'center': [length * 0.50, breadth * 0.15],
            'area': (length * 0.10) * (breadth * 0.30)
        },
        {
            'name': 'bathroom_common',
            'template': 'bathroom',
            'bounds': {
                'min_x': 0,
                'max_x': length * 0.25,
                'min_y': breadth * 0.45,
                'max_y': breadth * 0.70
            },
            'center': [length * 0.125, breadth * 0.575],
            'area': (length * 0.25) * (breadth * 0.25)
        },
        {
            'name': 'kitchen',
            'template': 'kitchen',
            'bounds': {
                'min_x': length * 0.60,
                'max_x': length,
                'min_y': breadth * 0.60,
                'max_y': breadth
            },
            'center': [length * 0.80, breadth * 0.80],
            'area': (length * 0.40) * (breadth * 0.40)
        },
        {
            'name': 'living_room',
            'template': 'living_room',
            'bounds': {
                'min_x': 0,
                'max_x': length * 0.55,
                'min_y': breadth * 0.55,
                'max_y': breadth
            },
            'center': [length * 0.275, breadth * 0.775],
            'area': (length * 0.55) * (breadth * 0.45)
        }
    ]

    return rooms


def apply_furniture_template(room, template_data):
    """
    Apply ready-made furniture set from template

    Args:
        room: Room dict with bounds and center
        template_data: Template from LocalLibrary/room_templates.json

    Returns:
        list: Furniture objects with positions
    """
    objects = []

    furniture_set = template_data.get('furniture_set', {})
    bounds = room['bounds']
    center = room['center']
    room_width = bounds['max_x'] - bounds['min_x']

    # Two-pass approach: first pass for independent items, second pass for dependent items
    # This ensures base_cabinets are generated before wall_cabinets that depend on them
    for pass_num in [1, 2]:
        for item_name, item_spec in furniture_set.items():
            quantity_formula = item_spec.get('quantity_formula', '')
            is_dependent = 'match_' in str(quantity_formula)

            # Pass 1: non-dependent items, Pass 2: dependent items
            if pass_num == 1 and is_dependent:
                continue
            if pass_num == 2 and not is_dependent:
                continue

            library_obj = item_spec.get('library_object')
            library_pattern = item_spec.get('library_object_pattern')

            # Handle pattern-based objects (e.g., kitchen cabinets with widths)
            if library_pattern and not library_obj:
                widths = item_spec.get('widths', [900])  # Default to 900mm if not specified
                quantity_formula = item_spec.get('quantity_formula', 'fit_to_counter_length')

                # Calculate how many cabinets to generate
                cabinets_to_generate = []

                if quantity_formula == 'fit_to_counter_length':
                    # Assume 60% of room width is counter space
                    counter_length = room_width * 0.6
                    remaining = counter_length

                    # Fit cabinets (prefer 900mm, fill gaps with 600mm)
                    for width_mm in sorted(widths, reverse=True):
                        width_m = width_mm / 1000
                        while remaining >= width_m:
                            cabinets_to_generate.append(width_mm)
                            remaining -= width_m

                elif quantity_formula == 'match_base_cabinets':
                    # Match previously generated base cabinets
                    base_cabinets = [obj for obj in objects if 'base_cabinet' in obj['name']]
                    for bc in base_cabinets:
                        # Extract width from base cabinet object_type (e.g., kitchen_base_cabinet_900_lod300)
                        bc_type = bc['object_type']
                        if '_600_' in bc_type:
                            cabinets_to_generate.append(600)
                        elif '_900_' in bc_type:
                            cabinets_to_generate.append(900)
                        else:
                            cabinets_to_generate.append(900)  # Default

                # Generate cabinet objects
                for i, width_mm in enumerate(cabinets_to_generate):
                    cabinet_obj = {
                        'name': f"{room['name']}_{item_name}_{i+1}",
                        'object_type': library_pattern.format(width=width_mm),
                        'position': calculate_position(
                            item_spec.get('placement_rule', 'linear_along_wall'),
                            bounds, center, i, item_spec
                        ),
                        'orientation': 90.0,
                        'room': room['name'],
                        'placed': False,
                        '_phase': '6_furniture',
                        'source': 'template_inference'
                    }
                    objects.append(cabinet_obj)

                continue

            # Handle regular library_object
            if not library_obj:
                continue

            quantity = item_spec.get('quantity', 1)
            placement_rule = item_spec.get('placement_rule', 'center')

            # Apply placement rule
            for i in range(quantity):
                position = calculate_position(placement_rule, bounds, center, i, item_spec)

                objects.append({
                    'name': f"{room['name']}_{item_name}_{i+1}",
                    'object_type': map_to_library_name(library_obj),
                    'position': position,
                    'orientation': 90.0,  # Default, will be refined by wall detection
                    'room': room['name'],
                    'placed': False,
                    '_phase': '6_furniture',
                    'source': 'template_inference'
                })

    return objects


def apply_electrical_template(room, template_data):
    """Apply electrical pattern from template"""
    objects = []

    electrical = template_data.get('electrical_pattern', {})
    bounds = room['bounds']
    center = room['center']

    # Ceiling lights
    if 'ceiling_light' in electrical:
        spec = electrical['ceiling_light']
        objects.append({
            'name': f"{room['name']}_ceiling_light",
            'object_type': 'ceiling_light_surface_lod300',
            'position': [center[0], center[1], spec.get('height', 2.95)],
            'orientation': 0.0,
            'room': room['name'],
            'placed': False,
            '_phase': '3_electrical',
            'source': 'template_inference'
        })

    # Ceiling fans
    if 'ceiling_fan' in electrical:
        spec = electrical['ceiling_fan']
        objects.append({
            'name': f"{room['name']}_ceiling_fan",
            'object_type': 'ceiling_fan_3blade_lod300',
            'position': [center[0], center[1] - 0.5, spec.get('height', 2.8)],
            'orientation': 0.0,
            'room': room['name'],
            'placed': False,
            '_phase': '3_electrical',
            'source': 'template_inference'
        })

    # Wall switches
    if 'switches' in electrical:
        spec = electrical['switches']
        qty = spec.get('quantity', 1)
        for i in range(qty):
            objects.append({
                'name': f"{room['name']}_switch_{i+1}",
                'object_type': 'switch_1gang_lod300',
                'position': [bounds['min_x'] + 0.2, bounds['min_y'] + 0.2, spec.get('height', 1.4)],
                'orientation': 90.0,
                'room': room['name'],
                'placed': False,
                '_phase': '3_electrical',
                'source': 'template_inference'
            })

    # Outlets
    if 'outlets' in electrical:
        spec = electrical['outlets']
        # Parse quantity formula or use direct number
        qty_formula = spec.get('quantity_formula', '2')
        if isinstance(qty_formula, str) and 'per' in qty_formula:
            qty = 3  # Default for formulas
        else:
            qty = 2

        for i in range(qty):
            x = bounds['min_x'] + (i + 1) * (bounds['max_x'] - bounds['min_x']) / (qty + 1)
            objects.append({
                'name': f"{room['name']}_outlet_{i+1}",
                'object_type': 'outlet_3pin_ms589_lod300',
                'position': [x, bounds['min_y'] + 0.2, spec.get('height', 0.3)],
                'orientation': 90.0,
                'room': room['name'],
                'placed': False,
                '_phase': '3_electrical',
                'source': 'template_inference'
            })

    return objects


def apply_plumbing_template(room, template_name):
    """
    Apply plumbing fixtures for bathrooms/kitchen

    NOW USES STANDARDS-DRIVEN PLACEMENT:
    - MS 1184 clearances enforced
    - Collision detection
    - Room size verification
    """
    objects = []
    bounds = room['bounds']
    center = room['center']

    # Calculate room size
    room_width = bounds['max_x'] - bounds['min_x']
    room_depth = bounds['max_y'] - bounds['min_y']

    # Zero collision tolerance for very small Malaysian bathrooms (tight fit required)
    collision_tolerance = 0.0 if room_width < 1.5 else 0.1  # 0mm for small, 100mm for normal

    # Create placement engine
    engine = StandardsPlacementEngine(collision_tolerance=collision_tolerance)
    existing_objects = []  # Track placed objects for collision detection

    if 'bathroom' in template_name:
        # Place toilet with MS 1184 clearances (0.6m front, 0.3m sides - MANDATORY)
        try:
            result = engine.place_fixture('toilet', bounds, existing_objects, preferred_wall='south')
            toilet_obj = {
                'name': f"{room['name']}_toilet",
                'object_type': 'floor_mounted_toilet_lod300',
                'position': result.position,
                'orientation': 180.0,
                'room': room['name'],
                'placed': True,
                '_phase': '4_plumbing',
                'source': 'template_inference',
                'standards_compliant': True,
                'clearances': {
                    'front': result.clearances_verified.front,
                    'sides': result.clearances_verified.left
                }
            }
            objects.append(toilet_obj)
            existing_objects.append(toilet_obj)
        except (MSViolation, RoomTooSmallError, CollisionError) as e:
            print(f"⚠️  Cannot place toilet in {room['name']}: {e}")

        # Place basin with MS 1184 clearances
        # Use smaller wall-mounted basin for tight Malaysian bathrooms
        try:
            result = engine.place_fixture('basin_wall_mounted', bounds, existing_objects, preferred_wall='north')  # North wall for different Y

            # Get MS 1184 height (850mm MANDATORY)
            basin_height = MS_1184_HEIGHTS['basin_rim'].height

            basin_obj = {
                'name': f"{room['name']}_basin",
                'object_type': map_to_library_name('basin_round_residential_lod300'),
                'position': [result.position[0], result.position[1], basin_height],
                'orientation': 270.0,
                'room': room['name'],
                'placed': True,
                '_phase': '4_plumbing',
                'source': 'template_inference',
                'standards_compliant': True,
                'clearances': {
                    'front': result.clearances_verified.front,
                    'sides': result.clearances_verified.left
                }
            }
            objects.append(basin_obj)
            existing_objects.append(basin_obj)
        except (MSViolation, RoomTooSmallError, CollisionError) as e:
            print(f"⚠️  Cannot place basin in {room['name']}: {e}")

        # Place shower
        try:
            result = engine.place_fixture('shower', bounds, existing_objects, preferred_wall='north')

            # Showerhead at MS 1184 height
            showerhead_height = MS_1184_HEIGHTS['showerhead'].height

            shower_obj = {
                'name': f"{room['name']}_showerhead",
                'object_type': map_to_library_name('showerhead_fixed_lod300'),
                'position': [result.position[0], result.position[1], showerhead_height],
                'orientation': 0.0,
                'room': room['name'],
                'placed': True,
                '_phase': '4_plumbing',
                'source': 'template_inference',
                'standards_compliant': True
            }
            objects.append(shower_obj)
            existing_objects.append(shower_obj)
        except (MSViolation, RoomTooSmallError, CollisionError) as e:
            print(f"⚠️  Cannot place shower in {room['name']}: {e}")

        # Floor drain (in shower area or room center)
        drain_pos = existing_objects[-1]['position'] if existing_objects else [center[0], center[1], 0.0]
        objects.append({
            'name': f"{room['name']}_floor_drain",
            'object_type': map_to_library_name('floor_drain_lod300'),
            'position': [drain_pos[0], drain_pos[1], 0.0],
            'orientation': 0.0,
            'room': room['name'],
            'placed': True,
            '_phase': '4_plumbing',
            'source': 'template_inference',
            'standards_compliant': True
        })

    elif 'toilet' in template_name:
        # Toilet room (smaller than bathroom, usually only has toilet + basin)
        try:
            result = engine.place_fixture('toilet', bounds, existing_objects, preferred_wall='south')
            toilet_obj = {
                'name': f"{room['name']}_toilet",
                'object_type': 'floor_mounted_toilet_lod300',
                'position': result.position,
                'orientation': 180.0,
                'room': room['name'],
                'placed': True,
                '_phase': '4_plumbing',
                'source': 'template_inference',
                'standards_compliant': True
            }
            objects.append(toilet_obj)
            existing_objects.append(toilet_obj)
        except (MSViolation, RoomTooSmallError, CollisionError) as e:
            print(f"⚠️  Cannot place toilet in {room['name']}: {e}")

        # Place basin (wall-mounted to save space)
        try:
            result = engine.place_fixture('basin_wall_mounted', bounds, existing_objects, preferred_wall='east')
            basin_height = MS_1184_HEIGHTS['basin_rim'].height

            basin_obj = {
                'name': f"{room['name']}_basin",
                'object_type': 'basin_wall_mounted',  # Wall-mounted for small toilets
                'position': [result.position[0], result.position[1], basin_height],
                'orientation': 270.0,
                'room': room['name'],
                'placed': True,
                '_phase': '4_plumbing',
                'source': 'template_inference',
                'standards_compliant': True
            }
            objects.append(basin_obj)
            existing_objects.append(basin_obj)
        except (MSViolation, RoomTooSmallError, CollisionError) as e:
            print(f"⚠️  Cannot place basin in {room['name']}: {e}")

    elif 'kitchen' in template_name:
        # Place kitchen sink with MS 1184 clearances
        try:
            result = engine.place_fixture('kitchen_sink', bounds, existing_objects, preferred_wall='north')

            sink_obj = {
                'name': f"{room['name']}_sink",
                'object_type': map_to_library_name('kitchen_sink_single_bowl_with_drainboard_lod300'),
                'position': [result.position[0], result.position[1], 0.9],  # Counter height
                'orientation': 0.0,
                'room': room['name'],
                'placed': True,
                '_phase': '4_plumbing',
                'source': 'template_inference',
                'standards_compliant': True
            }
            objects.append(sink_obj)
            existing_objects.append(sink_obj)
        except (MSViolation, RoomTooSmallError, CollisionError) as e:
            print(f"⚠️  Cannot place sink in {room['name']}: {e}")

        # Place stove with clearances
        try:
            result = engine.place_fixture('stove', bounds, existing_objects, preferred_wall='north')

            stove_obj = {
                'name': f"{room['name']}_stove",
                'object_type': map_to_library_name('stove_residential_lod300'),
                'position': [result.position[0], result.position[1], 0.9],  # Counter height
                'orientation': 0.0,
                'room': room['name'],
                'placed': True,
                '_phase': '6_furniture',
                'source': 'template_inference',
                'standards_compliant': True
            }
            objects.append(stove_obj)
            existing_objects.append(stove_obj)
        except (MSViolation, RoomTooSmallError, CollisionError) as e:
            print(f"⚠️  Cannot place stove in {room['name']}: {e}")

        # Place refrigerator with clearances
        try:
            result = engine.place_fixture('refrigerator', bounds, existing_objects, preferred_wall='east')

            fridge_obj = {
                'name': f"{room['name']}_refrigerator",
                'object_type': map_to_library_name('refrigerator_residential_lod300'),
                'position': result.position,
                'orientation': 270.0,
                'room': room['name'],
                'placed': True,
                '_phase': '6_furniture',
                'source': 'template_inference',
                'standards_compliant': True
            }
            objects.append(fridge_obj)
            existing_objects.append(fridge_obj)
        except (MSViolation, RoomTooSmallError, CollisionError) as e:
            print(f"⚠️  Cannot place refrigerator in {room['name']}: {e}")

    return objects


def calculate_position(placement_rule, bounds, center, index, spec):
    """Calculate object position based on placement rule"""
    # Extract height from spec (default to 0.0 for floor objects)
    height = spec.get('height', 0.0) if spec else 0.0

    if placement_rule == 'center':
        return [center[0], center[1], height]

    elif placement_rule == 'center_against_wall':
        return [center[0], bounds['min_y'] + 1.0, height]

    elif placement_rule == 'corner_or_wall':
        return [bounds['max_x'] - 0.5, center[1], height]

    elif placement_rule == 'against_wall':
        return [center[0], bounds['max_y'] - 0.5, height]

    elif placement_rule == 'linear_along_wall' or placement_rule == 'above_base_cabinets':
        # Space cabinets along wall (for kitchen cabinets)
        # Assume cabinets are 0.9m wide (900mm), place along north wall
        cabinet_width = 0.9  # meters
        spacing = 0.05  # 50mm gap between cabinets
        room_width = bounds['max_x'] - bounds['min_x']

        # Start from left side of room
        start_x = bounds['min_x'] + cabinet_width / 2
        x_pos = start_x + index * (cabinet_width + spacing)

        # Along north wall (max_y)
        y_pos = bounds['max_y'] - 0.3  # 300mm from wall

        return [x_pos, y_pos, height]

    else:
        return [center[0], center[1], height]


def augment_with_room_templates(extraction_output):
    """
    Augment text-based extraction with room template inference

    Args:
        extraction_output: Output JSON from extraction_engine.py (18 objects)

    Returns:
        dict: Augmented output with ~55-60 objects total
    """
    print("\n" + "="*80)
    print("🏠 AUGMENTING WITH ROOM TEMPLATES (Ready-Made Sets)")
    print("="*80)

    # Load templates
    templates = load_room_templates()
    print(f"✅ Loaded {len(templates)} room templates")

    # Get building dimensions
    metadata = extraction_output.get('extraction_metadata', {})
    building_dims = metadata.get('building_dimensions', {
        'length': 9.8,
        'breadth': 8.0,
        'height': 3.0
    })

    # Use real extracted room bounds instead of fake percentage-based detection
    # Import annotation derivation to get real room bounds from PDF extraction
    import sys
    from pathlib import Path as P
    sys.path.insert(0, str(P(__file__).parent.parent))
    from core.annotation_derivation import derive_room_bounds

    # Get annotation DB path from metadata
    pdf_source = metadata.get('pdf_source', 'examples/TB-LKTN_House/TB-LKTN HOUSE.pdf')
    pdf_basename = Path(pdf_source).stem.replace(' ', '_')
    annotation_db = Path('output_artifacts') / f'{pdf_basename}_ANNOTATION_FROM_2D.db'

    # Derive real room bounds from annotations
    real_room_bounds = derive_room_bounds(str(annotation_db))

    # Map Malaysian room names to templates
    room_template_mapping = {
        'RUANG_TAMU': 'living_room',
        'RUANG_MAKAN': 'living_room',  # Dining area (part of living room template)
        'DAPUR': 'kitchen',
        'BILIK_UTAMA': 'bedroom_master',
        'BILIK_2': 'bedroom_standard',
        'BILIK_3': 'bedroom_standard',
        'BILIK_MANDI': 'bathroom',
        'TANDAS': 'toilet',
        'RUANG_BASUH': 'utility_room'
    }

    # Convert real bounds to room format expected by template system
    rooms = []
    for room_name, bounds in real_room_bounds.items():
        if room_name not in room_template_mapping:
            continue  # Skip rooms without template mapping

        template_name = room_template_mapping[room_name]

        # Convert bounds to expected format
        width = bounds['x_max'] - bounds['x_min']
        depth = bounds['y_max'] - bounds['y_min']
        center_x = (bounds['x_min'] + bounds['x_max']) / 2
        center_y = (bounds['y_min'] + bounds['y_max']) / 2

        rooms.append({
            'name': room_name.lower(),
            'template': template_name,
            'bounds': {
                'min_x': bounds['x_min'],
                'max_x': bounds['x_max'],
                'min_y': bounds['y_min'],
                'max_y': bounds['y_max']
            },
            'center': [center_x, center_y],
            'area': width * depth
        })

    print(f"✅ Using {len(rooms)} real extracted rooms (not percentage-based)")

    # Keep existing text-extracted objects
    existing_objects = extraction_output.get('objects', [])
    print(f"✅ Keeping {len(existing_objects)} text-extracted objects (doors, windows, switches)")

    # Generate walls from GridTruth room_bounds
    # Determine GridTruth path from extraction metadata or use default
    pdf_source = metadata.get('pdf_source', 'examples/TB-LKTN_House/TB-LKTN HOUSE.pdf')
    pdf_dir = Path(pdf_source).parent
    grid_truth_path = pdf_dir / 'GridTruth.json'

    # NOTE: Structural elements (walls/roof/drains) now generated by extraction_engine
    # via GridTruth fallback when PDF extraction fails (template contract enforcement)
    # This module only adds room-specific furniture/fixtures from templates

    # Add inferred objects from templates (furniture/fixtures only)
    inferred_objects = []

    for room in rooms:
        template_name = room['template']

        # Check if template exists
        if template_name not in templates:
            print(f"  ⚠️  Template '{template_name}' not found, using fallback")
            continue

        template_data = templates[template_name]

        print(f"\n  📦 Applying '{template_name}' template to {room['name']}:")

        # Apply furniture set
        furniture = apply_furniture_template(room, template_data)
        print(f"     + {len(furniture)} furniture items")
        inferred_objects.extend(furniture)

        # Apply electrical pattern
        electrical = apply_electrical_template(room, template_data)
        print(f"     + {len(electrical)} electrical items")
        inferred_objects.extend(electrical)

        # Apply plumbing (bathroom/kitchen)
        plumbing = apply_plumbing_template(room, template_name)
        print(f"     + {len(plumbing)} plumbing items")
        inferred_objects.extend(plumbing)

    # Combine all objects
    all_objects = existing_objects + inferred_objects

    # Update summary
    by_phase = {}
    by_source = {'text_extraction': len(existing_objects), 'template_inference': len(inferred_objects)}

    for obj in all_objects:
        phase = obj.get('_phase', 'unknown')
        by_phase[phase] = by_phase.get(phase, 0) + 1

    extraction_output['objects'] = all_objects
    extraction_output['summary'] = {
        'total_objects': len(all_objects),
        'by_phase': by_phase,
        'by_source': by_source
    }

    print("\n" + "="*80)
    print(f"✅ AUGMENTATION COMPLETE")
    print("="*80)
    print(f"Text extraction:     {len(existing_objects)} objects")
    print(f"Template inference:  {len(inferred_objects)} objects")
    print(f"─────────────────────────────────────")
    print(f"TOTAL:               {len(all_objects)} objects")
    print(f"\nBreakdown by phase:")
    for phase, count in sorted(by_phase.items()):
        print(f"  {phase}: {count}")

    return extraction_output


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 2:
        print("Usage: python3 integrate_room_templates.py <extraction_output.json> [pdf_path]")
        sys.exit(1)

    input_path = sys.argv[1]
    pdf_path = sys.argv[2] if len(sys.argv) > 2 else None

    # Load extraction output
    with open(input_path) as f:
        extraction_output = json.load(f)

    # Add PDF path to metadata if provided
    if pdf_path:
        extraction_output['extraction_metadata']['pdf_source'] = pdf_path

    # Augment with templates
    augmented = augment_with_room_templates(extraction_output)

    # Save augmented output
    output_path = input_path.replace('.json', '_AUGMENTED.json')
    with open(output_path, 'w') as f:
        json.dump(augmented, f, indent=2)

    print(f"\n💾 Saved augmented output: {output_path}")

    # Run automated post-processing
    print("\n" + "="*80)
    print("🚀 RUNNING AUTOMATED POST-PROCESSING...")
    print("="*80)

    # Import post-processor
    sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
    from post_processor import automated_post_process
    from wall_combiner import process_walls

    # Get master template path
    master_template_path = Path(__file__).parent.parent / 'core' / 'master_reference_template.json'

    # Run wall combiner first
    print("\n🧱 Step 1: Combining collinear wall segments...")
    augmented['objects'] = process_walls(augmented['objects'])

    # Run post-processor
    print("\n🔧 Step 2: Running automated fixes...")
    fixed = automated_post_process(augmented, master_template_path)

    # [THIRD-D] Step 3: Validate in 3D Canvas (staging layer)
    print("\n🎯 Step 3: Validating objects in 3D canvas...")
    from src.core.building_canvas import validate_with_canvas

    # Find GridTruth.json and validation_rules.json
    pdf_dir = os.path.dirname(pdf_path) if pdf_path else os.path.dirname(input_json_path)
    gridtruth_path = os.path.join(pdf_dir, 'GridTruth.json')
    validation_rules_path = os.path.join(os.path.dirname(__file__),
                                         '../LocalLibrary/validation_rules.json')

    if os.path.exists(gridtruth_path) and os.path.exists(validation_rules_path):
        # Validate and possibly fix objects in 3D canvas
        validated_objects = validate_with_canvas(
            fixed['objects'],
            gridtruth_path,
            validation_rules_path
        )

        # Replace objects with validated ones
        fixed['objects'] = validated_objects

        # Update summary count
        fixed['summary']['total_objects'] = len(validated_objects)
    else:
        print(f"\n⚠️  Skipping 3D canvas validation (GridTruth.json or validation_rules.json not found)")

    # Save final fixed output
    # Keep _FINAL suffix (required by RUN_COMPLETE_PIPELINE.sh)
    final_path = output_path.replace('_AUGMENTED.json', '_FINAL.json')
    with open(final_path, 'w') as f:
        json.dump(fixed, f, indent=2)

    print(f"\n💾 Saved final output: {final_path}")
    print("\n✅ Complete pipeline: Extraction → Augmentation → Automated Fixes")
    print(f"   Final output ready for Blender: {final_path}")
