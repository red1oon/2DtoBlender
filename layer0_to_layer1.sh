#!/bin/bash
set -e

echo "================================================================================"
echo "LAYER 0 → LAYER 1: Generate FP (Fire Protection)"
echo "================================================================================"
echo ""

cd /home/red1/Documents/bonsai/2Dto3D

# Check if we have a base to work from
if [ ! -f Terminal1_MainBuilding_FILTERED.db ]; then
    echo "⚠️  No working database found - creating from Layer 0..."
    cp BASE_ARC_STR.db Terminal1_MainBuilding_FILTERED.db
    echo "✅ Layer 0 copied"
fi

# Step 1: DELETE old FP (if exists) + blend cache
echo "Step 1: Cleaning up old FP discipline and blend cache..."

# Delete blend cache (stale after database changes)
rm -f Terminal1*.blend *.blend.log *.blend.complete

sqlite3 Terminal1_MainBuilding_FILTERED.db << 'SQL'
-- Delete old FP (guaranteed cleanup)
DELETE FROM material_assignments WHERE guid IN (SELECT guid FROM elements_meta WHERE discipline = 'FP');
DELETE FROM base_geometries WHERE guid IN (SELECT guid FROM elements_meta WHERE discipline = 'FP');
DELETE FROM element_transforms WHERE guid IN (SELECT guid FROM elements_meta WHERE discipline = 'FP');
DELETE FROM elements_meta WHERE discipline = 'FP';

-- Rebuild rtree
DELETE FROM elements_rtree;
INSERT INTO elements_rtree (id, minX, maxX, minY, maxY, minZ, maxZ)
SELECT rowid, center_x-0.5, center_x+0.5, center_y-0.5, center_y+0.5, center_z-0.5, center_z+0.5
FROM element_transforms;

VACUUM;
SQL

echo "✅ Old FP deleted (if any existed)"
echo ""

# Step 2: Generate FP fresh
echo "Step 2: Generating FP discipline..."
python3 Scripts/master_routing.py Terminal1_MainBuilding_FILTERED.db --discipline FP --generate-devices

echo ""
echo "================================================================================"
echo "LAYER 1 COMPLETE"
echo "================================================================================"
sqlite3 Terminal1_MainBuilding_FILTERED.db "SELECT discipline, COUNT(*) FROM elements_meta GROUP BY discipline ORDER BY discipline;"
echo ""
echo "✅ Layer 1 ready (ARC + STR + FP)"
echo ""
echo "Next: Run ./layer1_to_layer2.sh to add ELEC"
echo "Undo: Run ./layer0_to_layer1.sh again to regenerate FP"
echo "Abort: Run ./abort_to_layer0.sh to start over"
echo ""
