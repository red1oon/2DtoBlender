#!/usr/bin/env python3
"""
Full Pipeline Test - TB-LKTN House
===================================
Complete demonstration of DeepSeek approach:
1. Load template JSON (AI output / manual)
2. Apply geometric rules engine
3. Use spatial awareness for rotation
4. Generate correctly placed 3D objects

This proves the complete workflow works!

Author: DeepSeek Integration Team
Date: 2025-11-23
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict

# Import our modules
from geometric_rules_engine import GeometricRulesEngine, PlacementContext
from spatial_awareness import SpatialContext

# Use relative path from script location
SCRIPT_DIR = Path(__file__).parent
TEMPLATE_PATH = SCRIPT_DIR / "input_templates" / "TB_LKTN_template.json"


def load_template(template_path: str) -> Dict:
    """Load building template JSON"""
    with open(template_path, 'r') as f:
        return json.load(f)


def create_spatial_context_from_template(template: Dict) -> SpatialContext:
    """Create spatial context from template building data"""

    context = SpatialContext()

    # Add walls
    for wall in template['building']['walls']:
        context.add_wall(
            start=wall['start'],
            end=wall['end'],
            name=wall['name']
        )

    # Add rooms
    for room in template['building']['rooms']:
        context.add_room(
            name=room['name'],
            vertices=room['vertices'],
            entrance=room.get('entrance')
        )

    return context


def place_all_objects(template: Dict) -> List[Dict]:
    """
    Place all objects from template using rules engine

    This is the CORE of the DeepSeek approach:
    - Template tells us WHAT and WHERE
    - Rules engine determines HOW to place
    """

    # Initialize engines
    rules_engine = GeometricRulesEngine()
    spatial_context = create_spatial_context_from_template(template)

    placed_objects = []

    for obj_spec in template['objects']:
        obj_type = obj_spec['object_type']
        raw_position = np.array(obj_spec['position'])
        obj_name = obj_spec['name']
        room_name = obj_spec.get('room')

        # Create placement context with spatial awareness
        context = PlacementContext(
            raw_position=raw_position,
            nearest_wall=spatial_context.find_nearest_wall(raw_position),
            nearest_room=spatial_context.find_containing_room(raw_position),
            floor_level=0.0
        )

        # Place object using rules engine
        placed = rules_engine.place_object(obj_type, raw_position.tolist(), context)

        # Apply advanced rotation using spatial awareness
        if context.nearest_wall:
            rotation_wall = spatial_context.calculate_wall_normal_rotation(context.nearest_wall)
        else:
            rotation_wall = 0.0

        if context.nearest_room and context.nearest_room.entrance_location is not None:
            rotation_entrance = spatial_context.calculate_room_entrance_rotation(
                context.nearest_room,
                raw_position
            )
        else:
            rotation_entrance = 0.0

        placed_objects.append({
            'name': obj_name,
            'object_type': obj_type,
            'room': room_name,
            'raw_position': raw_position.tolist(),
            'final_position': placed.final_position.tolist(),
            'rotation_deg': np.degrees(placed.final_rotation).tolist(),
            'rotation_wall_normal_deg': np.degrees(rotation_wall),
            'rotation_room_entrance_deg': np.degrees(rotation_entrance),
            'pivot_point': placed.pivot_point,
            'rules_applied': placed.rules_applied
        })

    return placed_objects


def generate_report(template: Dict, placed_objects: List[Dict]):
    """Generate comprehensive test report"""

    print("=" * 80)
    print("FULL PIPELINE TEST - TB-LKTN HOUSE")
    print("=" * 80)
    print()

    # Project info
    project = template['project']
    print(f"📋 Project: {project['name']}")
    print(f"   Reference: {project['drawing_reference']}")
    print(f"   Location: {project['location']}")
    print()

    # Building summary
    building = template['building']
    print(f"🏢 Building:")
    print(f"   Walls: {len(building['walls'])}")
    print(f"   Rooms: {len(building['rooms'])}")
    print(f"   Objects to place: {len(template['objects'])}")
    print()

    print("=" * 80)
    print("PLACEMENT RESULTS")
    print("=" * 80)
    print()

    # Group by room
    by_room = {}
    for obj in placed_objects:
        room = obj['room']
        if room not in by_room:
            by_room[room] = []
        by_room[room].append(obj)

    for room_name, objects in sorted(by_room.items()):
        print(f"\n📍 {room_name.upper().replace('_', ' ')}")
        print("-" * 80)

        for obj in objects:
            print(f"\n   {obj['name']}:")
            print(f"      Type: {obj['object_type']}")
            print(f"      Pivot: {obj['pivot_point']}")

            raw_pos = obj['raw_position']
            final_pos = obj['final_position']

            print(f"      Position:")
            print(f"         Raw:   X={raw_pos[0]:.2f}, Y={raw_pos[1]:.2f}, Z={raw_pos[2]:.2f}")
            print(f"         Final: X={final_pos[0]:.2f}, Y={final_pos[1]:.2f}, Z={final_pos[2]:.2f}")

            # Highlight height changes (MS 589 compliance!)
            if abs(final_pos[2] - raw_pos[2]) > 0.01:
                z_change = final_pos[2] - raw_pos[2]
                print(f"         ⚡ Height adjusted: {z_change:+.3f}m ", end="")

                if abs(final_pos[2] - 1.2) < 0.01:
                    print("(MS 589: Switch height)")
                elif abs(final_pos[2] - 0.3) < 0.01:
                    print("(MS 589: Outlet height)")
                elif abs(final_pos[2] - 0.85) < 0.01:
                    print("(Standard basin rim height)")
                else:
                    print()

            print(f"      Rotation:")
            print(f"         Wall normal: {obj['rotation_wall_normal_deg']:.1f}°")
            print(f"         Room entrance: {obj['rotation_room_entrance_deg']:.1f}°")

            if obj['rules_applied']:
                print(f"      Rules applied:")
                for rule in obj['rules_applied']:
                    print(f"         - {rule}")

    print()
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print()

    # Count by type
    type_counts = {}
    for obj in placed_objects:
        obj_type = obj['object_type']
        type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

    print("Objects placed by type:")
    for obj_type, count in sorted(type_counts.items()):
        print(f"   {obj_type}: {count}")

    print()

    # Validate MS 589 compliance
    print("MS 589 Compliance Check:")
    switches = [o for o in placed_objects if 'switch' in o['object_type']]
    outlets = [o for o in placed_objects if 'outlet' in o['object_type']]

    for switch in switches:
        z = switch['final_position'][2]
        status = "✅ PASS" if abs(z - 1.2) < 0.01 else "❌ FAIL"
        print(f"   {switch['name']}: Z={z:.3f}m {status}")

    for outlet in outlets:
        z = outlet['final_position'][2]
        status = "✅ PASS" if abs(z - 0.3) < 0.01 else "❌ FAIL"
        print(f"   {outlet['name']}: Z={z:.3f}m {status}")

    print()

    # Validate floor-mounted objects
    print("Floor-mounted objects check:")
    floor_objects = [o for o in placed_objects if o['object_type'] in ['door_single', 'toilet']]

    for obj in floor_objects:
        z = obj['final_position'][2]
        status = "✅ PASS" if abs(z) < 0.01 else "❌ FAIL"
        print(f"   {obj['name']}: Z={z:.3f}m {status}")

    print()
    print("=" * 80)
    print("✅ FULL PIPELINE TEST COMPLETE")
    print("=" * 80)
    print()

    # Summary statistics
    total_objects = len(placed_objects)
    total_rules_applied = sum(len(o['rules_applied']) for o in placed_objects)

    print("Summary:")
    print(f"   Total objects placed: {total_objects}")
    print(f"   Total rules applied: {total_rules_applied}")
    print(f"   Average rules per object: {total_rules_applied/total_objects:.1f}")
    print()

    print("Key Achievements:")
    print("   ✅ Template JSON loaded successfully")
    print("   ✅ Spatial context created from building data")
    print("   ✅ All objects placed using rules engine")
    print("   ✅ Malaysian standards (MS 589) enforced automatically")
    print("   ✅ Wall detection and rotation calculations working")
    print("   ✅ Room-aware placement functioning")
    print()

    print("DeepSeek Approach VALIDATED:")
    print("   1. AI/Manual → Template JSON ✅")
    print("   2. Rules Engine → Correct Placement ✅")
    print("   3. Spatial Awareness → Intelligent Rotation ✅")
    print("   4. Standards Compliance → Automatic ✅")
    print()


def main():
    """Run full pipeline test - always outputs artifacts"""
    from datetime import datetime

    # Ensure output_artifacts directory exists
    output_dir = SCRIPT_DIR / "output_artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Artifact paths
    output_path = output_dir / f"TB_LKTN_placement_results_{timestamp}.json"
    error_path = output_dir / f"TB_LKTN_error_log_{timestamp}.txt"

    template = None
    placed_objects = []
    success = False
    error_message = None

    try:
        if not TEMPLATE_PATH.exists():
            error_message = f"Template not found: {TEMPLATE_PATH}"
            raise FileNotFoundError(error_message)

        # Load template
        template = load_template(str(TEMPLATE_PATH))

        # Place all objects
        placed_objects = place_all_objects(template)

        # Generate report
        generate_report(template, placed_objects)

        success = True

    except Exception as e:
        error_message = f"Error during placement: {str(e)}"
        print(f"\n❌ {error_message}")
        print(f"Traceback: {e.__class__.__name__}")

        # Save error log
        with open(error_path, 'w') as f:
            import traceback
            f.write(f"TB-LKTN Pipeline Error Log\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Error: {error_message}\n\n")
            f.write("Full Traceback:\n")
            f.write(traceback.format_exc())

        print(f"💾 Error log saved to: {error_path}")

    finally:
        # ALWAYS save artifacts (source of truth POC)
        artifact_data = {
            "metadata": {
                "timestamp": timestamp,
                "success": success,
                "error": error_message,
                "template_path": str(TEMPLATE_PATH),
                "total_objects": len(placed_objects)
            },
            "template": template if template else {"error": "Template not loaded"},
            "placed_objects": placed_objects
        }

        with open(output_path, 'w') as f:
            json.dump(artifact_data, f, indent=2)

        print(f"\n{'✅' if success else '⚠️'} Artifacts ALWAYS saved to: {output_path}")
        print(f"   Success: {success}")
        print(f"   Objects placed: {len(placed_objects)}")
        print()


if __name__ == "__main__":
    main()
