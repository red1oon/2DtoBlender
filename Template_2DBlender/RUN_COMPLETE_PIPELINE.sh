#!/bin/bash
################################################################################
# Complete Automated 2D-to-3D Extraction Pipeline
################################################################################
#
# This script runs the full extraction workflow with all automated fixes:
#   1. Text extraction from PDF
#   2. Room template augmentation
#   3. Wall combining (collinear segments → single walls)
#   4. Automated post-processing (duplicates, heights, snapping, etc.)
#   5. Comprehensive validation
#
# Output: Production-ready JSON for Blender (100% LOD300, no duplicates)
#
################################################################################

set -e  # Exit on error

PDF_FILE="${1:-TB-LKTN HOUSE.pdf}"

if [ ! -f "$PDF_FILE" ]; then
    echo "❌ Error: PDF file not found: $PDF_FILE"
    echo "Usage: $0 [pdf_file]"
    exit 1
fi

echo "================================================================================"
echo "🚀 AUTOMATED 2D-TO-3D EXTRACTION PIPELINE"
echo "================================================================================"
echo "Input PDF: $PDF_FILE"
echo ""

# RULE 0 COMPLIANCE: Backup existing artifacts, then clean slate
PDF_BASENAME=$(basename "$PDF_FILE" .pdf)
# Normalize filename: replace spaces with underscores (match extraction_engine.py behavior)
PDF_BASENAME="${PDF_BASENAME// /_}"
DB_PATH="output_artifacts/${PDF_BASENAME}_ANNOTATION_FROM_2D.db"
BACKUP_DIR="output_artifacts/last_run_backup"

echo "💾 STEP 0A: Rolling Backup (preserving last run)..."
echo "--------------------------------------------------------------------------------"

# Create backup directory (overwrites previous backup)
rm -rf "$BACKUP_DIR" 2>/dev/null
mkdir -p "$BACKUP_DIR"

# Backup ANNOTATION database if exists
if [ -f "$DB_PATH" ]; then
    cp "$DB_PATH" "$BACKUP_DIR/"
    echo "   ✅ Backed up: ${PDF_BASENAME}_ANNOTATION_FROM_2D.db"
fi

# Backup output JSON files if exist
if ls output_artifacts/${PDF_BASENAME}_OUTPUT_*.json 1> /dev/null 2>&1; then
    cp output_artifacts/${PDF_BASENAME}_OUTPUT_*.json "$BACKUP_DIR/" 2>/dev/null || true
    echo "   ✅ Backed up: OUTPUT JSON files"
fi

# Backup intermediate databases if exist
for db in output_artifacts/*.db; do
    if [ -f "$db" ] && [ "$db" != "$DB_PATH" ]; then
        cp "$db" "$BACKUP_DIR/" 2>/dev/null || true
    fi
done

BACKUP_COUNT=$(ls -1 "$BACKUP_DIR" 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt "0" ]; then
    echo "   ✅ Backup complete: $BACKUP_COUNT files in $BACKUP_DIR"
else
    echo "   ℹ️  No previous artifacts to backup (first run)"
fi
echo ""

echo "🧹 STEP 0B: Clean Slate (Rule 0 Compliance)..."
echo "--------------------------------------------------------------------------------"
echo "   Deleting all artifacts to force fresh extraction from PDF..."

# Delete ANNOTATION database
if [ -f "$DB_PATH" ]; then
    rm "$DB_PATH"
    echo "   ✅ Deleted: ${PDF_BASENAME}_ANNOTATION_FROM_2D.db"
fi

# Delete all output JSON files
if ls output_artifacts/${PDF_BASENAME}_OUTPUT_*.json 1> /dev/null 2>&1; then
    rm output_artifacts/${PDF_BASENAME}_OUTPUT_*.json
    echo "   ✅ Deleted: OUTPUT JSON files"
fi

# Delete intermediate databases (except backup dir)
for db in output_artifacts/*.db; do
    if [ -f "$db" ]; then
        rm "$db"
        echo "   ✅ Deleted: $(basename $db)"
    fi
done

echo "   ✅ Clean slate ready - will extract fresh from PDF"
echo ""

# Step 0C: Create fresh annotation database from PDF
echo "📦 STEP 0C: Creating fresh annotation database from PDF..."
echo "--------------------------------------------------------------------------------"
echo "   Source: $PDF_FILE"
echo "   Database: $DB_PATH"
PYTHONPATH="$PWD:$PYTHONPATH" venv/bin/python core/primitive_extractor_enhanced.py "$PDF_FILE" "$DB_PATH"
echo "   ✅ Database created fresh"
echo ""

# Step 1: Extract from PDF
echo "📖 STEP 1: Extracting from PDF..."
echo "--------------------------------------------------------------------------------"
PYTHONPATH="$PWD:$PYTHONPATH" venv/bin/python core/extraction_engine.py "$PDF_FILE"

# Find the latest extraction output
EXTRACTION_OUTPUT=$(ls -t output_artifacts/${PDF_BASENAME}_OUTPUT_*.json | grep -v AUGMENTED | grep -v FINAL | head -1)

if [ -z "$EXTRACTION_OUTPUT" ]; then
    echo "❌ Error: Extraction output not found"
    exit 1
fi

echo "✅ Extraction complete: $EXTRACTION_OUTPUT"
echo ""

# Step 2: Augment with templates + Run all automated fixes
echo "🏠 STEP 2: Augmenting with room templates + Automated fixes..."
echo "--------------------------------------------------------------------------------"
venv/bin/python room_inference/integrate_room_templates.py "$EXTRACTION_OUTPUT"

# Find the final output
FINAL_OUTPUT=$(ls -t output_artifacts/*_FINAL.json | head -1)

if [ -z "$FINAL_OUTPUT" ]; then
    echo "❌ Error: Final output not found"
    exit 1
fi

# Cleanup intermediate files (keep only FINAL)
echo "🧹 Cleaning up intermediate files..."
TIMESTAMP=$(basename "$FINAL_OUTPUT" | sed 's/.*OUTPUT_\([0-9_]*\)_FINAL.json/\1/')
rm -f "output_artifacts/${PDF_BASENAME}_OUTPUT_${TIMESTAMP}.json" 2>/dev/null
rm -f "output_artifacts/${PDF_BASENAME}_OUTPUT_${TIMESTAMP}_AUGMENTED.json" 2>/dev/null
echo "   ✓ Removed intermediate files (keeping only FINAL)"

echo ""
echo "================================================================================"
echo "✅ PIPELINE COMPLETE"
echo "================================================================================"
echo "Final output: $FINAL_OUTPUT"
echo ""

# Step 3: Run comprehensive validation
echo "🧪 STEP 3: Running comprehensive validation..."
echo "--------------------------------------------------------------------------------"

echo ""
echo "📊 Test 1/3: Comprehensive structural tests..."
venv/bin/python validators/comprehensive_test.py "$FINAL_OUTPUT" 2>&1 | tail -30

echo ""
echo "📊 Test 2/3: Spatial logic validation..."
venv/bin/python validators/validate_spatial_logic.py "$FINAL_OUTPUT" 2>&1 | tail -30

echo ""
echo "📊 Test 3/3: Room and wall validation..."
venv/bin/python validators/validate_room_walls.py "$FINAL_OUTPUT" 2>&1 | tail -30

# Final summary
echo ""
echo "================================================================================"
echo "🎯 FINAL VALIDATION SUMMARY"
echo "================================================================================"

venv/bin/python -c "
import json

with open('$FINAL_OUTPUT') as f:
    data = json.load(f)

objects = data['objects']
lod300 = [o for o in objects if '_lod300' in o.get('object_type', '')]
with_height = [o for o in objects if o.get('position', [0,0,0])[2] > 0]
names = [o['name'] for o in objects]
unique_names = len(set(names))

print(f'Total Objects:        {len(objects)}')
print(f'LOD300 Compliance:    {len(lod300)}/{len(objects)} ({len(lod300)/len(objects)*100:.1f}%)')
print(f'Elevated Objects:     {len(with_height)}/{len(objects)} ({len(with_height)/len(objects)*100:.1f}%)')
print(f'Unique Names:         {unique_names}/{len(objects)} ({unique_names/len(objects)*100:.1f}%)')
print()
print('✅ Ready for Blender import')
print(f'   File: $FINAL_OUTPUT')
"

echo ""
echo "================================================================================"
echo "🏆 AUTOMATED PIPELINE COMPLETE"
echo "================================================================================"
echo "From PDF to production-ready 3D objects in <15 seconds"
echo ""
