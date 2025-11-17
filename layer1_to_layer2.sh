#!/bin/bash
set -e

echo "================================================================================"
echo "LAYER 1 → LAYER 2: Generate ELEC (Electrical)"
echo "================================================================================"
echo ""

cd /home/red1/Documents/bonsai/2Dto3D

# Check if we have Layer 1 (must have FP)
if [ ! -f Terminal1_MainBuilding_FILTERED.db ]; then
    echo "❌ ERROR: No working database found"
    echo "   Run ./layer0_to_layer1.sh first to create Layer 1"
    exit 1
fi

FP_COUNT=$(sqlite3 Terminal1_MainBuilding_FILTERED.db "SELECT COUNT(*) FROM elements_meta WHERE discipline = 'FP';")
if [ "$FP_COUNT" -eq 0 ]; then
    echo "⚠️  WARNING: No FP elements found - you may be missing Layer 1"
    echo "   Run ./layer0_to_layer1.sh first to generate FP"
    exit 1
fi

echo "✅ Layer 1 detected (FP: $FP_COUNT elements)"
echo ""

# Step 1: DELETE old ELEC (if exists) + blend cache
echo "Step 1: Cleaning up old ELEC discipline and blend cache..."

# Delete blend cache (stale after database changes)
rm -f Terminal1*.blend *.blend.log *.blend.complete

sqlite3 Terminal1_MainBuilding_FILTERED.db << 'SQL'
-- Delete old ELEC (guaranteed cleanup)
DELETE FROM material_assignments WHERE guid IN (SELECT guid FROM elements_meta WHERE discipline = 'ELEC');
DELETE FROM base_geometries WHERE guid IN (SELECT guid FROM elements_meta WHERE discipline = 'ELEC');
DELETE FROM element_transforms WHERE guid IN (SELECT guid FROM elements_meta WHERE discipline = 'ELEC');
DELETE FROM elements_meta WHERE discipline = 'ELEC';

-- Rebuild rtree
DELETE FROM elements_rtree;
INSERT INTO elements_rtree (id, minX, maxX, minY, maxY, minZ, maxZ)
SELECT rowid, center_x-0.5, center_x+0.5, center_y-0.5, center_y+0.5, center_z-0.5, center_z+0.5
FROM element_transforms;

VACUUM;
SQL

echo "✅ Old ELEC deleted (if any existed)"
echo ""

# Step 2: Generate ELEC fresh
echo "Step 2: Generating ELEC discipline..."
python3 Scripts/master_routing.py Terminal1_MainBuilding_FILTERED.db --discipline ELEC --device-type light_fixture --generate-devices

echo ""
echo "================================================================================"
echo "LAYER 2 COMPLETE"
echo "================================================================================"
sqlite3 Terminal1_MainBuilding_FILTERED.db "SELECT discipline, COUNT(*) FROM elements_meta GROUP BY discipline ORDER BY discipline;"
echo ""
echo "✅ Layer 2 ready (ARC + STR + FP + ELEC)"
echo ""
echo "Next: Load Terminal1_MainBuilding_FILTERED.db in Blender"
echo "Undo: Run ./layer1_to_layer2.sh again to regenerate ELEC"
echo "Abort to Layer 1: Run ./abort_to_layer1.sh to remove ELEC only"
echo "Abort to Layer 0: Run ./abort_to_layer0.sh to start over"
echo ""
