#!/bin/bash
# Run ALL validators to get complete testing coverage

OUTPUT_FILE="$1"

if [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: ./run_all_tests.sh <output.json>"
    exit 1
fi

echo "================================================================================"
echo "🧪 COMPLETE VALIDATION SUITE - TESTING EVERYTHING"
echo "================================================================================"
echo "File: $OUTPUT_FILE"
echo ""

PYTHON="venv/bin/python"

# Run all 6 validators
echo "1/6: Exhaustive Tests (21 tests)..."
$PYTHON validators/exhaustive_tests.py "$OUTPUT_FILE" 2>&1 | grep -E "(TEST|PASS|FAIL|WARNING|Total)"

echo ""
echo "2/6: Spatial Logic (7 tests)..."
$PYTHON validators/validate_spatial_logic.py "$OUTPUT_FILE" 2>&1 | grep -E "(TEST|PASS|FAIL|WARNING|objects)"

echo ""
echo "3/6: Room & Walls (4 tests)..."
$PYTHON validators/validate_room_walls.py "$OUTPUT_FILE" 2>&1 | grep -E "(TEST|PASS|FAIL|duplicate|doors)"

echo ""
echo "4/6: Architectural Elements (13 tests)..."
$PYTHON validators/test_architectural_elements.py "$OUTPUT_FILE" 2>&1 | grep -E "(TEST|PASS|FAIL|Roof|Walls|Sanitary)"

echo ""
echo "5/6: 3D Spatial Arithmetic (12 tests)..."
$PYTHON validators/test_3d_spatial_arithmetic.py "$OUTPUT_FILE" 2>&1 | grep -E "(TEST|PASS|FAIL|WARNING|Objects|Scene|ROOM)"

echo ""
echo "6/6: Deep Validation (8 categories)..."
$PYTHON validators/test_deep_validation.py "$OUTPUT_FILE" 2>&1 | grep -E "(DIMENSIONAL|STRUCTURAL|BUILDING CODE|IFC|TOPOLOGY|MEP|CONSTRUCTION|DATA QUALITY|SCORE)"

echo ""
echo "================================================================================"
echo "✅ ALL VALIDATORS COMPLETE"
echo "================================================================================"
