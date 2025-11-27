#!/usr/bin/env python3
"""
Stage 6: Consolidate Master Template (SINGLE SOURCE OF TRUTH)

Inputs:
  - output_artifacts/page8_schedules.json (Stage 1)
  - output_artifacts/grid_calibration.json (Stage 2)
  - output_artifacts/room_bounds.json (Stage 3)
  - output_artifacts/roof_geometry.json (Stage 3.5) [optional]
  - output_artifacts/door_placements.json (Stage 4)
  - output_artifacts/window_placements.json (Stage 5)

Output:
  - master_template.json (SSOT for all downstream processing)

Purpose:
  Merge all stage outputs into single JSON file with metadata,
  validation totals, and corrections log.

  Also generates wall placements internally from building_envelope
  (calculated from room_bounds) to avoid circular dependency.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def load_json(filepath):
    """Load JSON file, return empty dict if not found."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  Warning: {filepath} not found, using empty data")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing {filepath}: {e}")
        sys.exit(1)

def calculate_building_envelope(room_bounds):
    """Calculate building envelope from room bounds."""
    if not room_bounds:
        return {}

    # CRITICAL: Calculate main building bounds EXCLUDING porch
    # Porch (type="porch") is a separate structure, not part of main envelope
    x_coords = []
    y_coords = []

    for room_name, room_data in room_bounds.items():
        # Skip porch when calculating main building envelope
        if room_data.get('type') == 'porch':
            continue

        if 'x' in room_data and 'y' in room_data:
            x_coords.extend(room_data['x'])
            y_coords.extend(room_data['y'])

    if not x_coords or not y_coords:
        return {}

    # Main building bounds (habitable rooms only)
    min_x = min(x_coords)
    max_x = max(x_coords)
    min_y = min(y_coords)
    max_y = max(y_coords)

    width = max_x - min_x
    height = max_y - min_y
    area = width * height

    # ========================================================================
    # PORCH DETECTION (Rule 0 Compliant - derived from grid row 0)
    # ========================================================================
    # Porch is detected in Stage 3 (deduce_room_bounds_v2.py) from grid row "0"
    # If grid row 0 exists, porch is automatically detected and added to room_bounds
    # ========================================================================
    porch_data = room_bounds.get("ANJUNG", None)

    if porch_data:
        porch_polygon = porch_data.get("polygon", [])
        porch_width = porch_data.get("width_m", 0.0)
        porch_depth = porch_data.get("depth_m", 0.0)
        porch_area = porch_data.get("area_m2", 0.0)
        porch_x_start = porch_data["x"][0]
        porch_x_end = porch_data["x"][1]
        porch_y_start = porch_data["y"][0]
        porch_y_end = porch_data["y"][1]
    else:
        # No porch detected
        porch_polygon = []
        porch_width = 0.0
        porch_depth = 0.0
        porch_area = 0.0
        porch_x_start = min_x
        porch_x_end = min_x
        porch_y_start = min_y
        porch_y_end = min_y

    envelope = {
        "type": "L_shape_with_porch" if porch_data else "rectangular",
        "main_body": {
            "min": {"x": min_x, "y": min_y},
            "max": {"x": max_x, "y": max_y},
            "width_m": round(width, 2),
            "height_m": round(height, 2),
            "area_m2": round(area, 2)
        },
        "total_area_m2": round(area + porch_area, 2),
        "exterior_walls": {
            "WEST": {"x": min_x, "y_min": min_y, "y_max": max_y, "length_m": height, "mandatory": True},
            "EAST": {"x": max_x, "y_min": min_y, "y_max": max_y, "length_m": height, "mandatory": True},
            "SOUTH": {"y": min_y, "x_min": min_x, "x_max": max_x, "length_m": width, "mandatory": True},
            "NORTH": {"y": max_y, "x_min": min_x, "x_max": max_x, "length_m": width, "mandatory": True}
        }
    }

    # Add porch info if detected
    if porch_data:
        envelope["porch"] = {
            "name": "ANJUNG",
            "polygon": porch_polygon,
            "width_m": round(porch_width, 2),
            "depth_m": round(porch_depth, 2),
            "area_m2": round(porch_area, 2),
            "grid_cell": porch_data.get("grid_cell", "B0-C1"),
            "derivation": porch_data.get("derivation", "grid_row_0_detection")
        }
        envelope["porch_polygon"] = porch_polygon  # For backward compatibility
        envelope["exterior_walls"]["PORCH_SOUTH"] = {
            "y": porch_y_start,
            "x_min": porch_x_start,
            "x_max": porch_x_end,
            "length_m": porch_width,
            "mandatory": True
        }

    return envelope

def generate_interior_walls_from_rooms(room_bounds):
    """
    Pure math: Derive interior partition walls from room boundaries.

    Algorithm:
      For each pair of rooms, check if they share an edge.
      If shared edge exists, create a partition wall at that location.

    Args:
        room_bounds: Dict of room_name -> {x: [min, max], y: [min, max]}

    Returns:
        List of interior wall placement dicts
    """
    INTERIOR_WALL_STANDARDS = {
        "thickness_m": 0.075,     # 75mm lightweight partition
        "height_m": 2.7,
        "object_type": "wall_lightweight_75_lod300"
    }

    TOLERANCE = 0.1  # 10cm tolerance for edge matching

    interior_walls = []
    rooms = list(room_bounds.items())
    processed_walls = set()  # Avoid duplicate walls

    for i, (name1, room1) in enumerate(rooms):
        x1_min, x1_max = room1['x']
        y1_min, y1_max = room1['y']

        for name2, room2 in rooms[i+1:]:
            x2_min, x2_max = room2['x']
            y2_min, y2_max = room2['y']

            # Check vertical wall (room1 east edge == room2 west edge OR vice versa)
            if abs(x1_max - x2_min) < TOLERANCE:
                # Room1 is west of room2, shared edge at x1_max
                y_overlap_min = max(y1_min, y2_min)
                y_overlap_max = min(y1_max, y2_max)
                if y_overlap_max > y_overlap_min:
                    wall_key = (round(x1_max, 2), round(y_overlap_min, 2), round(y_overlap_max, 2), 'V')
                    if wall_key not in processed_walls:
                        processed_walls.add(wall_key)
                        interior_walls.append({
                            "element_id": f"WALL_INT_{name1}_{name2}_V",
                            "wall_name": f"INTERIOR_{name1}_{name2}",
                            "wall_type": "interior",
                            "position": [x1_max, y_overlap_min, 0.0],
                            "end_point": [x1_max, y_overlap_max, 0.0],
                            "thickness": INTERIOR_WALL_STANDARDS["thickness_m"],
                            "height": INTERIOR_WALL_STANDARDS["height_m"],
                            "length_m": round(y_overlap_max - y_overlap_min, 2),
                            "object_type": INTERIOR_WALL_STANDARDS["object_type"],
                            "mandatory": False
                        })

            elif abs(x2_max - x1_min) < TOLERANCE:
                # Room2 is west of room1, shared edge at x2_max
                y_overlap_min = max(y1_min, y2_min)
                y_overlap_max = min(y1_max, y2_max)
                if y_overlap_max > y_overlap_min:
                    wall_key = (round(x2_max, 2), round(y_overlap_min, 2), round(y_overlap_max, 2), 'V')
                    if wall_key not in processed_walls:
                        processed_walls.add(wall_key)
                        interior_walls.append({
                            "element_id": f"WALL_INT_{name2}_{name1}_V",
                            "wall_name": f"INTERIOR_{name2}_{name1}",
                            "wall_type": "interior",
                            "position": [x2_max, y_overlap_min, 0.0],
                            "end_point": [x2_max, y_overlap_max, 0.0],
                            "thickness": INTERIOR_WALL_STANDARDS["thickness_m"],
                            "height": INTERIOR_WALL_STANDARDS["height_m"],
                            "length_m": round(y_overlap_max - y_overlap_min, 2),
                            "object_type": INTERIOR_WALL_STANDARDS["object_type"],
                            "mandatory": False
                        })

            # Check horizontal wall (room1 north edge == room2 south edge OR vice versa)
            if abs(y1_max - y2_min) < TOLERANCE:
                # Room1 is south of room2, shared edge at y1_max
                x_overlap_min = max(x1_min, x2_min)
                x_overlap_max = min(x1_max, x2_max)
                if x_overlap_max > x_overlap_min:
                    wall_key = (round(y1_max, 2), round(x_overlap_min, 2), round(x_overlap_max, 2), 'H')
                    if wall_key not in processed_walls:
                        processed_walls.add(wall_key)
                        interior_walls.append({
                            "element_id": f"WALL_INT_{name1}_{name2}_H",
                            "wall_name": f"INTERIOR_{name1}_{name2}",
                            "wall_type": "interior",
                            "position": [x_overlap_min, y1_max, 0.0],
                            "end_point": [x_overlap_max, y1_max, 0.0],
                            "thickness": INTERIOR_WALL_STANDARDS["thickness_m"],
                            "height": INTERIOR_WALL_STANDARDS["height_m"],
                            "length_m": round(x_overlap_max - x_overlap_min, 2),
                            "object_type": INTERIOR_WALL_STANDARDS["object_type"],
                            "mandatory": False
                        })

            elif abs(y2_max - y1_min) < TOLERANCE:
                # Room2 is south of room1, shared edge at y2_max
                x_overlap_min = max(x1_min, x2_min)
                x_overlap_max = min(x1_max, x2_max)
                if x_overlap_max > x_overlap_min:
                    wall_key = (round(y2_max, 2), round(x_overlap_min, 2), round(x_overlap_max, 2), 'H')
                    if wall_key not in processed_walls:
                        processed_walls.add(wall_key)
                        interior_walls.append({
                            "element_id": f"WALL_INT_{name2}_{name1}_H",
                            "wall_name": f"INTERIOR_{name2}_{name1}",
                            "wall_type": "interior",
                            "position": [x_overlap_min, y2_max, 0.0],
                            "end_point": [x_overlap_max, y2_max, 0.0],
                            "thickness": INTERIOR_WALL_STANDARDS["thickness_m"],
                            "height": INTERIOR_WALL_STANDARDS["height_m"],
                            "length_m": round(x_overlap_max - x_overlap_min, 2),
                            "object_type": INTERIOR_WALL_STANDARDS["object_type"],
                            "mandatory": False
                        })

    return interior_walls


def generate_wall_placements(building_envelope, room_bounds=None):
    """
    Generate wall placements from building envelope + interior walls from room bounds.

    Args:
        building_envelope: Building envelope dict with exterior_walls
        room_bounds: Room bounds dict (optional, for interior walls)

    Returns:
        List of wall placement dicts
    """
    # Malaysian building standards
    WALL_STANDARDS = {
        "thickness_m": 0.25,      # 250mm cavity brick wall (MS 1064:1986)
        "height_m": 2.7,          # 2.7m floor-to-ceiling
        "object_type": "wall_brick_cavity_250_lod300"
    }

    wall_placements = []

    # 1. Generate exterior walls from building envelope
    exterior_walls = building_envelope.get('exterior_walls', {})

    for wall_name, wall_data in exterior_walls.items():
        # Determine start and end points based on wall orientation
        if 'x' in wall_data:  # Vertical wall (EAST/WEST)
            x = wall_data['x']
            y_min = wall_data['y_min']
            y_max = wall_data['y_max']
            start_point = [x, y_min, 0.0]
            end_point = [x, y_max, 0.0]
        else:  # Horizontal wall (NORTH/SOUTH)
            y = wall_data['y']
            x_min = wall_data['x_min']
            x_max = wall_data['x_max']
            start_point = [x_min, y, 0.0]
            end_point = [x_max, y, 0.0]

        wall_placement = {
            "element_id": f"WALL_{wall_name}",
            "wall_name": wall_name,
            "wall_type": "exterior",
            "position": start_point,
            "end_point": end_point,
            "thickness": WALL_STANDARDS["thickness_m"],
            "height": WALL_STANDARDS["height_m"],
            "length_m": wall_data["length_m"],
            "object_type": WALL_STANDARDS["object_type"],
            "mandatory": wall_data.get("mandatory", True)
        }
        wall_placements.append(wall_placement)

    # 2. Generate interior partition walls from room bounds (pure math derivation)
    if room_bounds:
        interior_walls = generate_interior_walls_from_rooms(room_bounds)
        wall_placements.extend(interior_walls)

    return wall_placements


def calculate_validation_metrics(room_bounds, door_placements, window_placements):
    """Calculate validation totals."""
    total_doors = len(door_placements) if isinstance(door_placements, list) else 0
    total_windows = len(window_placements) if isinstance(window_placements, list) else 0

    # Calculate floor area
    total_floor_area = 0.0
    if isinstance(room_bounds, dict):
        for room_data in room_bounds.values():
            if 'area_m2' in room_data:
                total_floor_area += room_data['area_m2']

    # Calculate window area
    total_window_area = 0.0
    if isinstance(window_placements, list):
        for win in window_placements:
            if 'width_mm' in win and 'height_mm' in win:
                area_m2 = (win['width_mm'] / 1000.0) * (win['height_mm'] / 1000.0)
                total_window_area += area_m2

    # Natural light ratio (UBBL requires ≥10%)
    natural_light_ratio = (total_window_area / total_floor_area * 100) if total_floor_area > 0 else 0

    # Ventilation area (assume 50% of windows are operable, UBBL requires ≥5%)
    ventilation_area = total_window_area * 0.5
    ventilation_ratio = (ventilation_area / total_floor_area * 100) if total_floor_area > 0 else 0

    return {
        "total_doors": total_doors,
        "total_windows": total_windows,
        "total_floor_area_m2": round(total_floor_area, 2),
        "total_window_area_m2": round(total_window_area, 2),
        "natural_light_ratio_percent": round(natural_light_ratio, 1),
        "ventilation_ratio_percent": round(ventilation_ratio, 1),
        "ubbl_light_compliant": natural_light_ratio >= 10.0,
        "ubbl_ventilation_compliant": ventilation_ratio >= 5.0
    }

def main():
    print("=" * 80)
    print("STAGE 6: MASTER TEMPLATE CONSOLIDATION")
    print("=" * 80)

    # Define paths
    artifacts_dir = Path("output_artifacts")

    # Load all stage outputs
    print("\n📖 Loading stage outputs...")
    page8_schedules = load_json(artifacts_dir / "page8_schedules.json")
    grid_calibration = load_json(artifacts_dir / "grid_calibration.json")
    room_bounds = load_json(artifacts_dir / "room_bounds.json")
    door_placements = load_json(artifacts_dir / "door_placements.json")
    window_placements = load_json(artifacts_dir / "window_placements.json")
    roof_geometry = load_json(artifacts_dir / "roof_geometry.json")
    roof_objects = load_json(artifacts_dir / "roof_objects.json")
    porch_objects = load_json(artifacts_dir / "porch_objects.json")
    floor_slab = load_json(artifacts_dir / "floor_slab.json")
    bathroom_fixtures = load_json(artifacts_dir / "bathroom_fixtures.json")
    furniture_fixtures = load_json(artifacts_dir / "furniture_fixtures.json")

    print(f"   ✓ Page 8 schedules: {len(page8_schedules.get('door_schedule', {}))} door types, {len(page8_schedules.get('window_schedule', {}))} window types")
    print(f"   ✓ Grid calibration: Origin at ({grid_calibration.get('origin', {}).get('x', 'N/A')}, {grid_calibration.get('origin', {}).get('y', 'N/A')})")
    print(f"   ✓ Room bounds: {len(room_bounds)} rooms")
    print(f"   ✓ Door placements: {len(door_placements) if isinstance(door_placements, list) else 0} doors")
    print(f"   ✓ Window placements: {len(window_placements) if isinstance(window_placements, list) else 0} windows")
    print(f"   ✓ Roof geometry: {'loaded' if roof_geometry else 'not available'}")
    print(f"   ✓ Roof objects: {len(roof_objects) if isinstance(roof_objects, list) else 0} items")
    print(f"   ✓ Porch objects: {len(porch_objects) if isinstance(porch_objects, list) else 0} items")
    print(f"   ✓ Floor slab: {len(floor_slab) if isinstance(floor_slab, list) else 0} items")
    print(f"   ✓ Bathroom fixtures: {len(bathroom_fixtures) if isinstance(bathroom_fixtures, list) else 0} items")
    print(f"   ✓ Furniture/fixtures: {len(furniture_fixtures) if isinstance(furniture_fixtures, list) else 0} items")

    # Calculate building envelope
    print("\n🏗️  Calculating building envelope...")
    building_envelope = calculate_building_envelope(room_bounds)
    if building_envelope:
        main_body = building_envelope.get('main_body', {})
        porch = building_envelope.get('porch', {})
        print(f"   ✓ Main body: {main_body.get('width_m', 0)}m × {main_body.get('height_m', 0)}m = {main_body.get('area_m2', 0)}m²")
        if porch:
            print(f"   ✓ Porch: {porch.get('width_m', 0)}m × {porch.get('depth_m', 0)}m = {porch.get('area_m2', 0)}m²")
        print(f"   ✓ Total area: {building_envelope.get('total_area_m2', 0)}m²")

    # Generate wall placements from building envelope + interior walls from room bounds
    print("\n🧱 Generating wall placements...")
    wall_placements = generate_wall_placements(building_envelope, room_bounds) if building_envelope else []
    if wall_placements:
        exterior_count = sum(1 for w in wall_placements if w.get('wall_type') == 'exterior')
        interior_count = sum(1 for w in wall_placements if w.get('wall_type') == 'interior')
        print(f"   ✓ Generated {len(wall_placements)} walls ({exterior_count} exterior + {interior_count} interior)")

    # Calculate validation metrics
    print("\n📊 Calculating validation metrics...")
    validation = calculate_validation_metrics(room_bounds, door_placements, window_placements)
    print(f"   ✓ Total doors: {validation['total_doors']}")
    print(f"   ✓ Total windows: {validation['total_windows']}")
    print(f"   ✓ Floor area: {validation['total_floor_area_m2']}m²")
    print(f"   ✓ Natural light: {validation['natural_light_ratio_percent']}% {'✅' if validation['ubbl_light_compliant'] else '⚠️'}")
    print(f"   ✓ Ventilation: {validation['ventilation_ratio_percent']}% {'✅' if validation['ubbl_ventilation_compliant'] else '⚠️'}")

    # Add mandatory flags to door/window schedules
    door_schedule = page8_schedules.get('door_schedule', {})
    for door_code in door_schedule:
        door_schedule[door_code]["mandatory"] = True

    window_schedule = page8_schedules.get('window_schedule', {})
    for window_code in window_schedule:
        window_schedule[window_code]["mandatory"] = True

    # Create building_elements section
    building_elements = {
        "roof": {
            "type": roof_geometry.get('roof_type', 'TBD') if roof_geometry else 'TBD',
            "description": "Main roof structure from PDF",
            "mandatory": True,
            "status": "extracted" if roof_geometry else "not_extracted",
            "geometry": roof_geometry if roof_geometry else None
        },
        "porch": {
            "type": "TBD",
            "description": "Front porch/canopy from PDF",
            "mandatory": True,
            "status": "not_extracted"
        },
        "discharge_drain": {
            "type": "plumbing",
            "description": "Discharge drain system from PDF",
            "mandatory": True,
            "status": "not_extracted"
        }
    }

    # Consolidate into master template
    print("\n🔧 Consolidating master template...")
    master_template = {
        "metadata": {
            "project_name": "TB-LKTN House",
            "source_pdf": "TB-LKTN HOUSE.pdf",
            "pipeline_version": "1.0-alpha",
            "created": datetime.now().isoformat(),
            "rule_0_compliant": True,
            "description": "Master template - SINGLE SOURCE OF TRUTH for all downstream processing"
        },
        "processing_rules": {
            "iteration_approach": "APPROACH_B_CHECKLIST_DRIVEN",
            "description": "When building output JSON, iterate through CHECKLIST FIRST, then lookup matching PDF data for each checklist item",
            "enforcement": [
                "for each checklist_item: find_matching_PDF_data() → add_to_json()",
                "Every checklist item is explicitly considered",
                "Missing items are easily detected",
                "NO iteration through PDF data first"
            ],
            "rationale": "Ensures completeness, prevents missing checklist items, maintains specification order, enables gap detection"
        },
        "grid_calibration": grid_calibration,
        "building_envelope": building_envelope,
        "building_elements": building_elements,
        "room_bounds": room_bounds,
        "door_schedule": door_schedule,
        "window_schedule": window_schedule,
        "door_placements": door_placements if isinstance(door_placements, list) else [],
        "window_placements": window_placements if isinstance(window_placements, list) else [],
        "wall_placements": wall_placements,
        "roof_objects": roof_objects if isinstance(roof_objects, list) else [],
        "porch_objects": porch_objects if isinstance(porch_objects, list) else [],
        "floor_slab": floor_slab if isinstance(floor_slab, list) else [],
        "bathroom_fixtures": bathroom_fixtures if isinstance(bathroom_fixtures, list) else [],
        "furniture_fixtures": furniture_fixtures if isinstance(furniture_fixtures, list) else [],
        "validation": validation,
        "corrections_applied": [
            "Initial alpha version - no corrections yet"
        ]
    }

    # Save master template
    output_path = Path("master_template.json")
    with open(output_path, 'w') as f:
        json.dump(master_template, f, indent=2)

    print("\n" + "=" * 80)
    print("✅ MASTER TEMPLATE CONSOLIDATION COMPLETE")
    print("=" * 80)
    print(f"\nSaved to: {output_path}")
    print(f"Total elements: {validation['total_doors'] + validation['total_windows']}")
    print("\nThis file is now the SINGLE SOURCE OF TRUTH for:")
    print("  - Stage 7: Blender export conversion")
    print("  - Stage 8: LOD300 import")
    print("  - QA validation")
    print("  - Future corrections and iterations")
    print("=" * 80)

if __name__ == "__main__":
    main()
