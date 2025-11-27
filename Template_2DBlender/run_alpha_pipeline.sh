#!/bin/bash
################################################################################
# TB-LKTN Alpha Pipeline Runner
# Version: 1.0-alpha
# Specification: TB-LKTN_COMPLETE_SPECIFICATION.md v1.1
################################################################################
#
# This script executes the complete 8-stage pipeline as specified:
#
#   Stage 1:   Extract Page 8 Schedule (door/window dimensions)
#   Stage 2:   Calibrate Grid Origin (HoughCircles + OCR)
#   Stage 3:   Deduce Room Bounds (grid-based inference)
#   Stage 3.5: Extract Roof Geometry (roof plan analysis)
#   Stage 4:   Place Doors (wall-center algorithm)
#   Stage 5:   Place Windows (exterior-wall algorithm)
#   Stage 6:   Consolidate Master Template (SSOT + generate walls)
#   Stage 7:   Convert to Blender Format (rotation mapping)
#   Stage 8:   Import to Blender (LOD300 geometry)
#
# Output: TB-LKTN_House.blend (3D BIM model with LOD300 objects)
#
# Note: Wall placements are generated internally in Stage 6 from the
#       building_envelope (calculated from room_bounds) to avoid
#       circular dependencies.
#
################################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
PDF_FILE="${1:-TB-LKTN HOUSE.pdf}"
OUTPUT_DIR="output_artifacts"
PYTHON="venv/bin/python3"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo ""
    echo "================================================================================"
    echo -e "${BLUE}$1${NC}"
    echo "================================================================================"
}

print_stage() {
    echo ""
    echo -e "${GREEN}$1${NC}"
    echo "--------------------------------------------------------------------------------"
}

print_error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Validate input
if [ ! -f "$PDF_FILE" ]; then
    print_error "PDF file not found: $PDF_FILE"
    echo "Usage: $0 [pdf_file]"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

print_header "🚀 TB-LKTN ALPHA PIPELINE v1.0"
echo "Input PDF: $PDF_FILE"
echo "Output Directory: $OUTPUT_DIR"
echo "Specification: TB-LKTN_COMPLETE_SPECIFICATION.md v1.1"
echo ""
echo "Rule 0 Compliance: ENABLED (all outputs deterministic)"
echo "Building Codes: UBBL 1984 (Malaysian Standards)"

# ============================================================================
# STAGE 1: Extract Page 8 Schedule
# ============================================================================
print_stage "📖 STAGE 1: Extract Page 8 Schedule"

if $PYTHON extract_page8_schedule_v2.py; then
    if [ -f "$OUTPUT_DIR/page8_schedules.json" ]; then
        DOOR_TYPES=$(jq '.door_schedule | length' "$OUTPUT_DIR/page8_schedules.json" 2>/dev/null || echo "0")
        WINDOW_TYPES=$(jq '.window_schedule | length' "$OUTPUT_DIR/page8_schedules.json" 2>/dev/null || echo "0")
        print_success "Page 8 schedule extracted: ${DOOR_TYPES} door types, ${WINDOW_TYPES} window types"
    else
        print_error "page8_schedules.json not found"
        exit 1
    fi
else
    print_error "Stage 1 failed"
    exit 1
fi

# ============================================================================
# STAGE 2: Calibrate Grid Origin
# ============================================================================
print_stage "🔍 STAGE 2: Calibrate Grid Origin"

if $PYTHON calibrate_grid_origin.py "$PDF_FILE"; then
    if [ -f "$OUTPUT_DIR/grid_calibration.json" ]; then
        ORIGIN_X=$(jq -r '.origin.x' "$OUTPUT_DIR/grid_calibration.json" 2>/dev/null || echo "N/A")
        ORIGIN_Y=$(jq -r '.origin.y' "$OUTPUT_DIR/grid_calibration.json" 2>/dev/null || echo "N/A")
        SCALE=$(jq -r '.scale_px_per_m' "$OUTPUT_DIR/grid_calibration.json" 2>/dev/null || echo "N/A")
        print_success "Grid calibrated: origin=($ORIGIN_X, $ORIGIN_Y)px, scale=${SCALE} px/m"
    else
        print_error "grid_calibration.json not found"
        exit 1
    fi
else
    print_error "Stage 2 failed"
    exit 1
fi

# ============================================================================
# STAGE 3: Deduce Room Bounds
# ============================================================================
print_stage "🏠 STAGE 3: Deduce Room Bounds"

if $PYTHON deduce_room_bounds_v2.py; then
    if [ -f "$OUTPUT_DIR/room_bounds.json" ]; then
        ROOM_COUNT=$(jq '. | length' "$OUTPUT_DIR/room_bounds.json" 2>/dev/null || echo "0")
        print_success "Room bounds deduced: ${ROOM_COUNT} rooms"
    else
        print_error "room_bounds.json not found"
        exit 1
    fi
else
    print_error "Stage 3 failed"
    exit 1
fi

# ============================================================================
# STAGE 3.5: Extract Roof Geometry
# ============================================================================
print_stage "🏘️  STAGE 3.5: Extract Roof Geometry"

if $PYTHON extract_roof_geometry.py; then
    if [ -f "$OUTPUT_DIR/roof_geometry.json" ]; then
        ROOF_TYPE=$(jq -r '.main_roof.type' "$OUTPUT_DIR/roof_geometry.json" 2>/dev/null || echo "N/A")
        OVERHANG=$(jq -r '.main_roof.overhangs_m.NORTH' "$OUTPUT_DIR/roof_geometry.json" 2>/dev/null || echo "N/A")
        print_success "Roof extracted: ${ROOF_TYPE}, ${OVERHANG}m eaves"
    else
        print_error "roof_geometry.json not found"
        exit 1
    fi
else
    print_error "Stage 3.5 failed"
    exit 1
fi

# ============================================================================
# STAGE 4: Place Doors
# ============================================================================
print_stage "🚪 STAGE 4: Place Doors"

if $PYTHON generate_door_placements_v2.py; then
    if [ -f "$OUTPUT_DIR/door_placements.json" ]; then
        DOOR_COUNT=$(jq '. | length' "$OUTPUT_DIR/door_placements.json" 2>/dev/null || echo "0")
        print_success "Doors placed: ${DOOR_COUNT} doors"
    else
        print_error "door_placements.json not found"
        exit 1
    fi
else
    print_error "Stage 4 failed"
    exit 1
fi

# ============================================================================
# STAGE 5: Place Windows
# ============================================================================
print_stage "🪟 STAGE 5: Place Windows"

if $PYTHON generate_window_placements_v2.py; then
    if [ -f "$OUTPUT_DIR/window_placements.json" ]; then
        WINDOW_COUNT=$(jq '. | length' "$OUTPUT_DIR/window_placements.json" 2>/dev/null || echo "0")
        print_success "Windows placed: ${WINDOW_COUNT} windows"
    else
        print_error "window_placements.json not found"
        exit 1
    fi
else
    print_error "Stage 5 failed"
    exit 1
fi

# ============================================================================
# STAGE 6: Consolidate Master Template (+ Generate Walls)
# ============================================================================
print_stage "🔧 STAGE 6: Consolidate Master Template"

if $PYTHON consolidate_master_template.py; then
    if [ -f "master_template.json" ]; then
        TOTAL_DOORS=$(jq '.door_placements | length' master_template.json 2>/dev/null || echo "0")
        TOTAL_WINDOWS=$(jq '.window_placements | length' master_template.json 2>/dev/null || echo "0")
        TOTAL_WALLS=$(jq '.wall_placements | length' master_template.json 2>/dev/null || echo "0")
        FLOOR_AREA=$(jq -r '.validation.total_floor_area_m2' master_template.json 2>/dev/null || echo "0")
        print_success "Master template consolidated: ${TOTAL_DOORS} doors + ${TOTAL_WINDOWS} windows + ${TOTAL_WALLS} walls"
        echo "   ✓ Floor area: ${FLOOR_AREA}m²"
        echo "   ✓ Walls generated internally from building envelope"
        echo "   ✓ This is now the SINGLE SOURCE OF TRUTH (SSOT)"
    else
        print_error "master_template.json not found"
        exit 1
    fi
else
    print_error "Stage 6 failed"
    exit 1
fi

# ============================================================================
# STAGE 7: Convert to Blender Format
# ============================================================================
print_stage "🎨 STAGE 7: Convert to Blender Format"

if $PYTHON convert_master_to_blender.py; then
    if [ -f "$OUTPUT_DIR/blender_import.json" ]; then
        BLENDER_OBJECTS=$(jq '.metadata.total_objects' "$OUTPUT_DIR/blender_import.json" 2>/dev/null || echo "0")
        print_success "Blender format generated: ${BLENDER_OBJECTS} objects"
        echo "   ✓ Rotation mapping: NORTH/SOUTH=0°, EAST/WEST=90°"
    else
        print_error "blender_import.json not found"
        exit 1
    fi
else
    print_error "Stage 7 failed"
    exit 1
fi

# ============================================================================
# STAGE 8: Import to Blender (Optional - requires Blender)
# ============================================================================
print_stage "🎬 STAGE 8: Import to Blender (Optional)"

if command -v blender &> /dev/null; then
    BLENDER_PATH=$(command -v blender)
    echo "Blender found: $BLENDER_PATH"
    echo "To run Stage 8, execute:"
    echo "  blender --background --python blender_lod300_import.py -- \\"
    echo "    $OUTPUT_DIR/blender_import.json \\"
    echo "    LocalLibrary/Ifc_Object_Library.db \\"
    echo "    TB-LKTN_House.blend"
else
    print_warning "Blender not found in PATH"
    echo "Install Blender to run Stage 8 (3D import)"
fi

# ============================================================================
# PIPELINE SUMMARY
# ============================================================================
print_header "✅ ALPHA PIPELINE COMPLETE"

echo ""
echo "📊 PIPELINE SUMMARY"
echo "--------------------------------------------------------------------------------"
echo "Stage 1:   Page 8 Schedule     → $OUTPUT_DIR/page8_schedules.json"
echo "Stage 2:   Grid Calibration    → $OUTPUT_DIR/grid_calibration.json"
echo "Stage 3:   Room Bounds         → $OUTPUT_DIR/room_bounds.json"
echo "Stage 3.5: Roof Extraction     → $OUTPUT_DIR/roof_geometry.json"
echo "Stage 4:   Door Placements     → $OUTPUT_DIR/door_placements.json"
echo "Stage 5:   Window Placements   → $OUTPUT_DIR/window_placements.json"
echo "Stage 6:   Master Template     → master_template.json (SSOT + walls generated)"
echo "Stage 7:   Blender Export      → $OUTPUT_DIR/blender_import.json"
echo "Stage 8:   Blender Import      → (manual step - see above)"
echo ""

# Validation summary
if [ -f "master_template.json" ]; then
    echo "🔍 VALIDATION SUMMARY"
    echo "--------------------------------------------------------------------------------"

    DOORS=$(jq -r '.validation.total_doors' master_template.json 2>/dev/null || echo "0")
    WINDOWS=$(jq -r '.validation.total_windows' master_template.json 2>/dev/null || echo "0")
    FLOOR=$(jq -r '.validation.total_floor_area_m2' master_template.json 2>/dev/null || echo "0")
    LIGHT=$(jq -r '.validation.natural_light_ratio_percent' master_template.json 2>/dev/null || echo "0")
    VENT=$(jq -r '.validation.ventilation_ratio_percent' master_template.json 2>/dev/null || echo "0")
    LIGHT_OK=$(jq -r '.validation.ubbl_light_compliant' master_template.json 2>/dev/null || echo "false")
    VENT_OK=$(jq -r '.validation.ubbl_ventilation_compliant' master_template.json 2>/dev/null || echo "false")

    echo "Total Doors:        $DOORS"
    echo "Total Windows:      $WINDOWS"
    echo "Floor Area:         ${FLOOR}m²"
    echo -n "Natural Light:      ${LIGHT}% "
    if [ "$LIGHT_OK" = "true" ]; then
        print_success "(UBBL compliant ≥10%)"
    else
        print_warning "(Below UBBL 10% minimum)"
    fi
    echo -n "Ventilation:        ${VENT}% "
    if [ "$VENT_OK" = "true" ]; then
        print_success "(UBBL compliant ≥5%)"
    else
        print_warning "(Below UBBL 5% minimum)"
    fi
fi

echo ""
echo "📄 NEXT STEPS"
echo "--------------------------------------------------------------------------------"
echo "1. Review master_template.json for accuracy"
echo "2. Apply any necessary corrections (see apply_qa_corrections.py)"
echo "3. Run Stage 8 to import into Blender"
echo "4. Validate 3D model in Blender"
echo ""
print_header "🏆 Alpha Pipeline Complete - Ready for QA Review"
