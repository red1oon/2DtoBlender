#!/usr/bin/env python3
"""
Extraction Engine - Class-Based Architecture for 2D to Blender BIM

Orchestrator for PDF extraction pipeline.
Imports modular components from separate files.
"""

import math
import re
from datetime import datetime

# Import modular components
from src.core.calibration import CalibrationEngine
from src.core.geometry_validator import GeometryValidator
from src.core.wall_detection import WallDetector, WallValidator
from src.core.inference_chain import InferenceChain
from src.core.schedule_extractor import ScheduleExtractor
from src.core.opening_detector import OpeningDetector
from src.core.room_detector import RoomBoundaryDetector, RoomLabelExtractor
from src.core.elevation_extractor import ElevationExtractor


# =============================================================================
# WALL DETECTOR
# =============================================================================

# NOTE: CalibrationEngine and GeometryValidator moved to separate modules
# Keeping wall detection classes here temporarily (to be refactored next)

# =============================================================================
# GEOMETRY VALIDATOR
# =============================================================================

# =============================================================================
# WINDOW SILL HEIGHT INFERENCE (Phase 1D)
# =============================================================================

def infer_window_sill_heights(windows, elevations, window_schedule):
    """
    Infer window sill heights based on window types and elevations

    Logic:
    - W1 (large windows): Sill at 1.0m (living room, bedroom)
    - W2 (standard windows): Sill at 1.0m (bedrooms)
    - W3 (small windows): Sill at 1.5m (bathrooms, ventilation)

    Args:
        windows: List of window positions
        elevations: Elevation data with window_sill height
        window_schedule: Window dimensions by type

    Returns:
        list: Windows with sill_height and lintel_height added
    """
    default_sill = elevations.get('window_sill', 1.0)

    for window in windows:
        window_type = window['window_type']
        width = window_schedule[window_type]['width']
        height = window_schedule[window_type]['height']

        # Inference rules based on window size
        if width >= 1.8:
            # Large windows (W1) - living room, low sill for view
            sill_height = min(default_sill, 1.0)
        elif width >= 1.2:
            # Standard windows (W2) - bedrooms, standard sill
            sill_height = default_sill
        elif width >= 0.6:
            # Small windows (W3) - bathrooms, high sill for privacy
            sill_height = max(default_sill, 1.5)
        else:
            # Very small - ventilation only
            sill_height = 2.0

        window['sill_height'] = sill_height
        window['lintel_height'] = sill_height + height

        # Update Z position to sill height
        window['position'][2] = sill_height

    return windows


# =============================================================================
# MAIN ORCHESTRATOR - TWO-TIER EXTRACTION PIPELINE
# =============================================================================

def complete_pdf_extraction(pdf_path, building_width=9.8, building_length=8.0, building_height=3.0):
    """
    Complete PDF → OUTPUT.json extraction pipeline (Two-Tier Architecture)

    NEW APPROACH (corrected):
    1. Load master_reference_template.json (TIER 1 - high-level instructions)
    2. For each item in extraction_sequence:
       - Lookup detection_id in vector_patterns.py (TIER 2 - low-level execution)
       - Execute pattern matching
       - If found → add to objects array with "placed": false
       - If not found → skip
    3. Generate output JSON: metadata + summary (hash total) + objects

    Args:
        pdf_path: Path to PDF file
        building_width: Building width in meters
        building_length: Building length in meters
        building_height: Building height in meters

    Returns:
        dict: Output JSON with metadata + summary + objects (placed: false)
    """
    import pdfplumber
    import json
    from datetime import datetime
    import os

    print(f"🔧 Starting TWO-TIER extraction from: {pdf_path}")
    print("=" * 80)

    # STEP 1: Load Master Reference Template (TIER 1)
    print("\n📖 STEP 1: Loading Master Reference Template...")
    master_template_path = os.path.join(os.path.dirname(__file__), "master_reference_template.json")

    try:
        with open(master_template_path, 'r') as f:
            master_template = json.load(f)
            extraction_sequence = master_template['extraction_sequence']
            print(f"  ✅ Loaded {len(extraction_sequence)} items from master template")
    except FileNotFoundError:
        print(f"  ❌ ERROR: master_reference_template.json not found at {master_template_path}")
        return None

    # STEP 2: Initialize extraction components
    print("\n🔧 STEP 2: Initializing extraction components...")

    with pdfplumber.open(pdf_path) as pdf:
        # Initialize calibration engine (needed for all coordinate transforms)
        calibration_engine = CalibrationEngine(pdf, building_width, building_length)

        # Initialize vector pattern executor (TIER 2)
        from vector_patterns import VectorPatternExecutor
        vector_executor = VectorPatternExecutor(pdf, calibration_engine)

        print("  ✅ Calibration engine initialized")
        print("  ✅ Vector pattern executor initialized")

        # STEP 3: Sequential extraction following master template
        print("\n🔍 STEP 3: Sequential extraction (following master template order)...")

        objects = []  # Will be populated with found objects
        calibration_data = None  # Will be set after calibration
        extraction_context = {}  # Shared context between extraction phases

        # Pre-extract walls for orientation calculation
        print("\n  🧱 Pre-extracting walls for orientation calculation...")
        dimensions = {"length": building_width, "breadth": building_length, "height": building_height}
        wall_detector = WallDetector(calibration_engine, dimensions)

        # Extract walls from first page after calibration is available
        # Note: This will run after calibration is done in the sequence

        # Track expected vs actual objects for debugging
        expected_lod300_objects = []
        found_lod300_objects = []
        failed_lod300_objects = []

        # Iterate through extraction sequence
        for idx, item in enumerate(extraction_sequence, 1):
            phase = item.get('_phase', 'unknown')
            item_name = item['item']
            detection_id = item['detection_id']
            search_text = item.get('search_text', [])
            pages = item.get('pages', [0])
            object_type = item.get('object_type')

            # Track expected LOD300 objects
            if object_type and 'lod300' in object_type.lower():
                expected_lod300_objects.append({
                    'item': item_name,
                    'object_type': object_type,
                    'detection_id': detection_id,
                    'search_text': search_text
                })

            print(f"\n  [{idx}/{len(extraction_sequence)}] {phase}: {item_name}")
            print(f"    Detection ID: {detection_id}")
            if object_type:
                print(f"    Object Type: {object_type}")
            if search_text:
                print(f"    Search Text: {search_text}")

            try:
                # Execute pattern matching via VectorPatternExecutor
                result = vector_executor.execute(
                    detection_id=detection_id,
                    search_text=search_text,
                    pages=pages,
                    object_type=object_type,
                    context=extraction_context
                )

                # Handle result based on detection type
                if result:
                    if detection_id == "CALIBRATION_DRAIN_PERIMETER":
                        # Store calibration data
                        calibration_data = result
                        extraction_context['calibration'] = calibration_data
                        print(f"    ✅ Calibration: scale_x={calibration_data['scale_x']:.6f}, scale_y={calibration_data['scale_y']:.6f}")

                        # Extract walls immediately after calibration for orientation calculation
                        print(f"\n  🧱 Extracting walls (needed for orientation)...")
                        try:
                            internal_walls = wall_detector.extract_from_vectors(pdf.pages[0])
                            # Generate outer walls from building dimensions
                            outer_walls = [
                                {"start_point": [0, 0, 0], "end_point": [building_width, 0, 0]},  # North
                                {"start_point": [0, building_length, 0], "end_point": [building_width, building_length, 0]},  # South
                                {"start_point": [0, 0, 0], "end_point": [0, building_length, 0]},  # East
                                {"start_point": [building_width, 0, 0], "end_point": [building_width, building_length, 0]}   # West
                            ]
                            all_walls = outer_walls + internal_walls
                            extraction_context['walls'] = all_walls
                            print(f"    ✅ Walls extracted: {len(outer_walls)} exterior + {len(internal_walls)} interior = {len(all_walls)} total")
                        except Exception as e:
                            print(f"    ⚠️  Wall extraction failed: {str(e)}")
                            extraction_context['walls'] = []

                        # Calibration succeeded - now generate drain objects via GridTruth
                        # (calibration is just coord transform metadata, we need actual drain objects)
                        if object_type and item.get('mandatory', False):
                            print(f"    📍 Generating discharge drain objects from GridTruth...")
                            try:
                                from gridtruth_generator import generate_item as gridtruth_generate
                                pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
                                grid_truth_path = os.path.join(pdf_dir, 'GridTruth.json')

                                drain_objects = gridtruth_generate(item, grid_truth_path, extraction_context)
                                if drain_objects:
                                    for obj in drain_objects:
                                        obj['_phase'] = phase
                                        obj['placed'] = False
                                        objects.append(obj)
                                    print(f"    ✅ Generated {len(drain_objects)} discharge drains from GridTruth")
                            except Exception as e:
                                print(f"    ⚠️  Drain generation failed: {str(e)}")

                    elif detection_id == "ELEVATION_TEXT_REGEX":
                        # Store elevation data
                        if 'elevations' not in extraction_context:
                            extraction_context['elevations'] = {}
                        elevation_key = item_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
                        extraction_context['elevations'][elevation_key] = result
                        print(f"    ✅ {item_name}: {result}m")

                    elif detection_id == "SCHEDULE_TABLE_EXTRACTION":
                        # Store schedule data
                        if 'door' in item_name.lower():
                            extraction_context['door_schedule'] = result
                            print(f"    ✅ Found {len(result)} door types")
                        elif 'window' in item_name.lower():
                            extraction_context['window_schedule'] = result
                            print(f"    ✅ Found {len(result)} window types")

                    elif object_type:
                        # Add to objects array with "placed": false
                        if isinstance(result, list):
                            for obj in result:
                                obj['_phase'] = phase
                                obj['placed'] = False
                                objects.append(obj)

                                # Track LOD300 objects
                                if 'lod300' in object_type.lower():
                                    found_lod300_objects.append({
                                        'item': item_name,
                                        'object_type': object_type,
                                        'name': obj.get('name'),
                                        'position': obj.get('position'),
                                        'orientation': obj.get('orientation')
                                    })

                            print(f"    ✅ Found {len(result)} instances")
                        else:
                            result['_phase'] = phase
                            result['placed'] = False
                            objects.append(result)

                            # Track LOD300 objects
                            if 'lod300' in object_type.lower():
                                found_lod300_objects.append({
                                    'item': item_name,
                                    'object_type': object_type,
                                    'name': result.get('name'),
                                    'position': result.get('position'),
                                    'orientation': result.get('orientation')
                                })

                            print(f"    ✅ Found 1 instance")
                    else:
                        # Result found but no object_type (metadata only, e.g., door labels)
                        # Check if mandatory - may need GridTruth generation
                        is_mandatory = item.get('mandatory', False)

                        if is_mandatory:
                            print(f"    ✅ Extracted successfully (metadata only)")
                            print(f"    ⚠️  No objects created (object_type=null) - trying GridTruth fallback (MANDATORY)")

                            try:
                                from gridtruth_generator import generate_item as gridtruth_generate
                                pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
                                grid_truth_path = os.path.join(pdf_dir, 'GridTruth.json')

                                generated_objects = gridtruth_generate(item, grid_truth_path, extraction_context)

                                if generated_objects:
                                    for obj in generated_objects:
                                        obj['_phase'] = phase
                                        obj['placed'] = False
                                        objects.append(obj)
                                    print(f"    ✅ GridTruth fallback SUCCESS: {len(generated_objects)} items generated")
                                else:
                                    print(f"    ⚠️  GridTruth fallback returned no objects")
                            except Exception as e:
                                print(f"    ⚠️  GridTruth fallback failed: {str(e)}")
                        else:
                            print(f"    ✅ Extracted successfully (metadata only)")
                else:
                    # TEMPLATE CONTRACT ENFORCEMENT
                    # Check if this is a mandatory item
                    is_mandatory = item.get('mandatory', False)

                    if is_mandatory:
                        # Mandatory item failed PDF extraction - try GridTruth fallback
                        print(f"    ⚠️  PDF extraction failed - trying GridTruth fallback (MANDATORY)")

                        try:
                            from gridtruth_generator import generate_item as gridtruth_generate

                            # Determine GridTruth path from PDF location
                            pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
                            grid_truth_path = os.path.join(pdf_dir, 'GridTruth.json')

                            # Try to generate from GridTruth (pass context for door_schedule, etc.)
                            generated_objects = gridtruth_generate(item, grid_truth_path, extraction_context)

                            if generated_objects:
                                # Success! Add to output
                                objects.extend(generated_objects)
                                print(f"    ✅ GridTruth fallback SUCCESS: {len(generated_objects)} items generated")
                            else:
                                # Both PDF and GridTruth failed for mandatory item
                                error_msg = (
                                    f"\n{'='*80}\n"
                                    f"❌ PIPELINE FAILURE: MANDATORY ITEM NOT FULFILLED\n"
                                    f"{'='*80}\n"
                                    f"Template item: {item_name}\n"
                                    f"Object type: {object_type}\n"
                                    f"Phase: {item.get('_phase', 'unknown')}\n"
                                    f"\n"
                                    f"  • PDF extraction: FAILED (not found)\n"
                                    f"  • GridTruth fallback: FAILED (cannot generate)\n"
                                    f"\n"
                                    f"Action required:\n"
                                    f"  1. Verify GridTruth.json exists at: {grid_truth_path}\n"
                                    f"  2. Verify GridTruth has required sections (room_bounds, building_envelope)\n"
                                    f"  3. Verify template item is correctly marked as mandatory\n"
                                    f"{'='*80}\n"
                                )
                                raise RuntimeError(error_msg)
                        except ImportError:
                            raise RuntimeError("gridtruth_generator module not found - cannot fallback")
                        except Exception as e:
                            raise RuntimeError(f"GridTruth fallback failed: {str(e)}")
                    else:
                        # Optional item - just log and skip
                        if object_type and 'lod300' in object_type.lower():
                            failed_lod300_objects.append({
                                'item': item_name,
                                'object_type': object_type,
                                'detection_id': detection_id,
                                'search_text': search_text,
                                'reason': 'Not found in PDF (optional)'
                            })
                            print(f"    ⚠️  Optional item not found - skipping")
                        else:
                            print(f"    ⚠️  Not found - skipping")

            except Exception as e:
                # Track LOD300 failures
                if object_type and 'lod300' in object_type.lower():
                    failed_lod300_objects.append({
                        'item': item_name,
                        'object_type': object_type,
                        'detection_id': detection_id,
                        'error': str(e)
                    })
                    print(f"    ❌ EXTRACTION FAILED - LOD300 object error: {str(e)}")
                else:
                    print(f"    ❌ Error: {str(e)}")
                continue

        # STEP 3.5: LOD300 OBJECTS DEBUG SUMMARY
        print("\n" + "=" * 80)
        print("🔍 LOD300 OBJECTS DEBUG SUMMARY (Master Template = Reference of Truth)")
        print("=" * 80)
        print(f"\nExpected LOD300 objects from master template: {len(expected_lod300_objects)}")
        print(f"Found: {len(found_lod300_objects)}")
        print(f"Failed/Missing: {len(failed_lod300_objects)}")

        if found_lod300_objects:
            print(f"\n✅ FOUND LOD300 OBJECTS ({len(found_lod300_objects)}):")
            for obj in found_lod300_objects:
                pos = obj.get('position', [0,0,0])
                orient = obj.get('orientation', 0.0)
                print(f"  ✅ {obj['item']}: {obj['name']} ({obj['object_type']})")
                print(f"     Position: [{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]  Orientation: {orient:.1f}°")

        if failed_lod300_objects:
            print(f"\n❌ FAILED/MISSING LOD300 OBJECTS ({len(failed_lod300_objects)}):")
            for obj in failed_lod300_objects:
                print(f"  ❌ {obj['item']} ({obj['object_type']})")
                print(f"     Detection ID: {obj['detection_id']}")
                print(f"     Search Text: {obj.get('search_text', 'N/A')}")
                print(f"     Reason: {obj.get('reason', obj.get('error', 'Unknown'))}")

        # Calculate success rate
        success_rate = (len(found_lod300_objects) / max(len(expected_lod300_objects), 1)) * 100
        print(f"\n📊 LOD300 Extraction Success Rate: {success_rate:.1f}% ({len(found_lod300_objects)}/{len(expected_lod300_objects)})")

        if success_rate < 100:
            print(f"⚠️  WARNING: Some LOD300 objects from master template were not extracted!")
            print(f"   Action Required: Review failed objects and fix detection patterns")
        else:
            print(f"✅ SUCCESS: All LOD300 objects from master template were extracted!")

        print("=" * 80)

        # STEP 4: Generate output JSON with new structure
        print("\n📊 STEP 4: Generating output JSON...")

        # Count objects by phase
        by_phase = {}
        for obj in objects:
            phase = obj.get('_phase', 'unknown')
            by_phase[phase] = by_phase.get(phase, 0) + 1

        # Build output JSON structure
        output_json = {
            "extraction_metadata": {
                "extracted_by": "extraction_engine.py v2.0 (two-tier)",
                "extraction_date": datetime.now().strftime("%Y-%m-%d"),
                "extraction_time": datetime.now().strftime("%H:%M:%S"),
                "pdf_source": os.path.basename(pdf_path),
                "extraction_version": "2.0_two_tier",
                "calibration": extraction_context.get('calibration', {
                    "method": "default_fallback",
                    "scale_x": 0.0353,
                    "scale_y": 0.0353,
                    "confidence": 60
                })
            },

            "summary": {
                "total_objects": len(objects),
                "by_phase": by_phase
            },

            "objects": objects
        }

        print(f"  ✅ Total objects found: {len(objects)}")
        print(f"  ✅ Objects by phase:")
        for phase, count in sorted(by_phase.items()):
            print(f"     - {phase}: {count}")

        print("\n" + "=" * 80)
        print("✅ TWO-TIER EXTRACTION COMPLETE")
        print("=" * 80)
        print(f"\nOutput JSON structure:")
        print(f"  • extraction_metadata (who, when, calibration)")
        print(f"  • summary (hash total: {len(objects)} objects)")
        print(f"  • objects array ({len(objects)} items with 'placed': false)")
        print(f"\n💡 Next steps:")
        print(f"  1. Validate library references (validate_library_references.py)")
        print(f"  2. Place in Blender (mark 'placed': true)")
        print(f"  3. Verify hash total (summary.total_objects == count(placed))")

        return output_json


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys
    import json
    import os

    if len(sys.argv) < 2:
        print("Usage: python3 extraction_engine.py <pdf_path> [output_json] [--building-width W] [--building-length L]")
        print("\nExample:")
        print("  python3 extraction_engine.py 'TB-LKTN HOUSE.pdf'")
        print("  python3 extraction_engine.py 'TB-LKTN HOUSE.pdf' --building-width 9.8 --building-length 8.0")
        print("  python3 extraction_engine.py 'TB-LKTN HOUSE.pdf' custom_output.json")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Parse optional building dimensions
    building_width = 9.8
    building_length = 8.0
    building_height = 3.0
    output_path = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--building-width' and i + 1 < len(sys.argv):
            building_width = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--building-length' and i + 1 < len(sys.argv):
            building_length = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--building-height' and i + 1 < len(sys.argv):
            building_height = float(sys.argv[i + 1])
            i += 2
        elif not sys.argv[i].startswith('--'):
            output_path = sys.argv[i]
            i += 1
        else:
            i += 1

    # Default output to output_artifacts folder with timestamp
    if not output_path:
        # Create output_artifacts folder if it doesn't exist
        os.makedirs("output_artifacts", exist_ok=True)

        # Generate timestamped filename following pattern: <PDFname>_OUTPUT_<timestamp>.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_name = os.path.basename(pdf_path).replace('.pdf', '').replace(' ', '_')
        output_path = f"output_artifacts/{pdf_name}_OUTPUT_{timestamp}.json"

    # Run complete two-tier extraction
    output_json = complete_pdf_extraction(pdf_path, building_width, building_length, building_height)

    if output_json:
        # Save to JSON
        with open(output_path, 'w') as f:
            json.dump(output_json, f, indent=2)

        print(f"\n💾 Saved to: {output_path}")
        print(f"📁 Full path: {os.path.abspath(output_path)}")
        print(f"\n✅ Output JSON structure:")
        print(f"   • extraction_metadata: calibration data + timestamps")
        print(f"   • summary: hash total ({output_json['summary']['total_objects']} objects)")
        print(f"   • objects: all found items with 'placed': false")
    else:
        print("\n❌ Extraction failed - see errors above")
        sys.exit(1)
