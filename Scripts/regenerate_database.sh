#!/bin/bash
# Regenerate database with standardized codes and real dimensions
# Run after updating discipline codes and dimension extraction

set -e  # Exit on error

DB_FILE="Terminal1_MainBuilding_FILTERED.db"
BACKUP_DIR="old_backups"

echo "=================================================================="
echo "DATABASE REGENERATION - Standardized Codes + Real Dimensions"
echo "=================================================================="
echo ""

# Step 0: Backup existing database
echo "Step 0: Backing up existing database..."
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/${DB_FILE%.db}_$(date +%Y%m%d_%H%M%S).db"
cp "$DB_FILE" "$BACKUP_FILE"
echo "✅ Backup saved: $BACKUP_FILE"
echo ""

# Step 1: Extract wall angles and lengths from DXF
echo "Step 1: Extracting wall angles and lengths from DXF..."
python3 Scripts/extract_wall_angles.py
echo ""

# Step 2: Regenerate 3D geometry with real dimensions
echo "Step 2: Regenerating 3D geometry with real dimensions..."
python3 Scripts/generate_3d_geometry.py "$DB_FILE"
echo ""

# Step 3: Fix R-tree bounding boxes
echo "Step 3: Updating R-tree bounding boxes from actual geometry..."
python3 Scripts/fix_rtree_bboxes.py "$DB_FILE"
echo ""

# Step 4: Add material assignments (discipline colors)
echo "Step 4: Adding discipline-based material assignments..."
python3 Scripts/add_material_assignments.py "$DB_FILE"
echo ""

echo "=================================================================="
echo "✅ DATABASE REGENERATION COMPLETE"
echo "=================================================================="
echo ""
echo "Summary of changes:"
echo "  ✅ Discipline codes standardized (ARC, FP, STR, ELEC)"
echo "  ✅ Wall lengths extracted from DXF (real dimensions)"
echo "  ✅ Geometry regenerated with parametric shapes"
echo "  ✅ R-tree bboxes updated (Preview mode ready)"
echo "  ✅ Material colors assigned by discipline"
echo ""
echo "Next step: Run BonsaiTester validation"
echo "  ~/Documents/bonsai/BonsaiTester/bonsai-test $DB_FILE"
echo ""
