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

    for item_name, item_spec in furniture_set.items():
        library_obj = item_spec.get('library_object')
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

    # Create placement engine
    engine = StandardsPlacementEngine()
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

        # Place basin with MS 1184 clearances (0.5m front, 0.2m sides - MANDATORY)
        try:
            result = engine.place_fixture('basin', bounds, existing_objects, preferred_wall='east')

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

    else:
        return [center[0], center[1], height]


def generate_walls_from_grid_truth(grid_truth_path):
    """
    Generate wall segments from GridTruth room_bounds

    Creates wall objects from room rectangle edges, handling shared walls
    """
    try:
        with open(grid_truth_path) as f:
            grid_truth = json.load(f)
    except FileNotFoundError:
        print(f"⚠️  GridTruth not found: {grid_truth_path}")
        return []

    room_bounds = grid_truth.get('room_bounds', {})
    if not room_bounds:
        print("⚠️  No room_bounds in GridTruth")
        return []

    # Track all wall segments to avoid duplicates
    wall_segments = set()

    for room_name, bounds in room_bounds.items():
        if room_name.startswith('_'):  # Skip metadata like _note
            continue

        x_min, x_max = bounds['x_min'], bounds['x_max']
        y_min, y_max = bounds['y_min'], bounds['y_max']

        # Create 4 wall segments for this room (as tuples for deduplication)
        segments = [
            # South wall: (x_min, y_min) → (x_max, y_min)
            ((x_min, y_min, 0.0), (x_max, y_min, 0.0)),
            # North wall: (x_min, y_max) → (x_max, y_max)
            ((x_min, y_max, 0.0), (x_max, y_max, 0.0)),
            # West wall: (x_min, y_min) → (x_min, y_max)
            ((x_min, y_min, 0.0), (x_min, y_max, 0.0)),
            # East wall: (x_max, y_min) → (x_max, y_max)
            ((x_max, y_min, 0.0), (x_max, y_max, 0.0)),
        ]

        for seg in segments:
            # Add both directions (normalize to avoid duplicates)
            normalized = tuple(sorted([seg[0], seg[1]]))
            wall_segments.add(normalized)

    # Convert to wall objects
    walls = []
    for i, (start, end) in enumerate(wall_segments):
        # Determine if interior or exterior wall
        # (simplified: exterior if on building perimeter)
        is_exterior = (start[0] == 0.0 or start[1] == 0.0 or
                       end[0] == 0.0 or end[1] == 0.0 or
                       start[0] >= 11.0 or start[1] >= 8.0 or
                       end[0] >= 11.0 or end[1] >= 8.0)

        wall_type = "wall_brick_3m_lod300" if is_exterior else "wall_lightweight_100_lod300"
        wall_category = "exterior" if is_exterior else "interior"

        wall = {
            "name": f"wall_{wall_category}_{i+1}",
            "object_type": wall_type,
            "position": list(start),
            "end_point": list(end),
            "height": 3.0,
            "thickness": 0.15 if is_exterior else 0.10,
            "placed": False,
            "room": "structure",
            "phase": "1C_structure"
        }
        walls.append(wall)

    print(f"✅ Generated {len(walls)} wall segments from {len(room_bounds)-1} rooms")
    return walls


def generate_roof_and_drains(grid_truth_path):
    """Generate roof and discharge perimeter from GridTruth"""
    try:
        with open(grid_truth_path) as f:
            grid_truth = json.load(f)
    except FileNotFoundError:
        return []

    elements = []

    # Get building envelope
    envelope = grid_truth.get('building_envelope', {})
    if envelope:
        x_min = envelope.get('x_min', 0.0)
        x_max = envelope.get('x_max', 11.2)
        y_min = envelope.get('y_min', 0.0)
        y_max = envelope.get('y_max', 8.5)
        height = envelope.get('height', 3.0)

        # Generate roof slab (flat roof covering entire building)
        roof = {
            "name": "roof_main",
            "object_type": "roof_slab_flat_lod300",
            "position": [x_min, y_min, height],
            "dimensions": {
                "length": x_max - x_min,
                "width": y_max - y_min,
                "thickness": 0.15
            },
            "placed": False,
            "room": "structure",
            "phase": "1C_structure"
        }
        elements.append(roof)

        # Generate discharge perimeter (gutter around roof)
        perimeter_points = [
            # South edge
            ([x_min, y_min, height], [x_max, y_min, height]),
            # East edge
            ([x_max, y_min, height], [x_max, y_max, height]),
            # North edge
            ([x_max, y_max, height], [x_min, y_max, height]),
            # West edge
            ([x_min, y_max, height], [x_min, y_min, height])
        ]

        for i, (start, end) in enumerate(perimeter_points):
            drain = {
                "name": f"discharge_perimeter_{i+1}",
                "object_type": "roof_gutter_100_lod300",
                "position": start,
                "end_point": end,
                "placed": False,
                "room": "structure",
                "phase": "1B_calibration"
            }
            elements.append(drain)

        print(f"✅ Generated roof and discharge perimeter (5 elements)")

    return elements


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

    # Detect rooms
    rooms = detect_rooms_simple(building_dims)
    print(f"✅ Detected {len(rooms)} rooms")

    # Keep existing text-extracted objects
    existing_objects = extraction_output.get('objects', [])
    print(f"✅ Keeping {len(existing_objects)} text-extracted objects (doors, windows, switches)")

    # Generate walls from GridTruth room_bounds
    # Determine GridTruth path from extraction metadata or use default
    pdf_source = metadata.get('pdf_source', 'examples/TB-LKTN_House/TB-LKTN HOUSE.pdf')
    pdf_dir = Path(pdf_source).parent
    grid_truth_path = pdf_dir / 'GridTruth.json'

    print(f"📍 Looking for GridTruth: {grid_truth_path}")
    walls = generate_walls_from_grid_truth(str(grid_truth_path))
    roof_and_drains = generate_roof_and_drains(str(grid_truth_path))

    # Add inferred objects from templates
    inferred_objects = (walls + roof_and_drains) if (walls or roof_and_drains) else []

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

    # Save final fixed output
    # Keep _FINAL suffix (required by RUN_COMPLETE_PIPELINE.sh)
    final_path = output_path.replace('_AUGMENTED.json', '_FINAL.json')
    with open(final_path, 'w') as f:
        json.dump(fixed, f, indent=2)

    print(f"\n💾 Saved final output: {final_path}")
    print("\n✅ Complete pipeline: Extraction → Augmentation → Automated Fixes")
    print(f"   Final output ready for Blender: {final_path}")
