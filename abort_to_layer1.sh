#!/bin/bash
set -e

echo "================================================================================"
echo "ABORT TO LAYER 1: Delete ELEC, keep FP"
echo "================================================================================"
echo ""

cd /home/red1/Documents/bonsai/2Dto3D

# Check if we have a database
if [ ! -f Terminal1_MainBuilding_FILTERED.db ]; then
    echo "❌ ERROR: No working database found"
    echo "   Run ./abort_to_layer0.sh first"
    exit 1
fi

# Delete ELEC only
echo "Deleting ELEC discipline..."
sqlite3 Terminal1_MainBuilding_FILTERED.db << 'SQL'
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

# Delete blend files (may have ELEC cached)
rm -f Terminal1*.blend *.blend.log *.blend.complete

echo ""
echo "================================================================================"
echo "LAYER 1 RESTORED"
echo "================================================================================"
sqlite3 Terminal1_MainBuilding_FILTERED.db "SELECT discipline, COUNT(*) FROM elements_meta GROUP BY discipline ORDER BY discipline;"
echo ""
echo "✅ Aborted to Layer 1 (ARC + STR + FP, ELEC removed)"
echo ""
echo "Next: Run ./layer1_to_layer2.sh to regenerate ELEC"
echo ""
