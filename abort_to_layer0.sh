#!/bin/bash
set -e

echo "================================================================================"
echo "ABORT TO LAYER 0: Delete everything, start from BASE_ARC_STR.db"
echo "================================================================================"
echo ""

cd /home/red1/Documents/bonsai/2Dto3D

# Delete ALL working files
echo "Deleting all working files..."
rm -f Terminal1*.db Terminal1*.blend *.blend.log *.blend.complete

# Copy frozen Layer 0
echo "Restoring from frozen Layer 0 (BASE_ARC_STR.db)..."
cp BASE_ARC_STR.db Terminal1_MainBuilding_FILTERED.db

echo ""
echo "================================================================================"
echo "LAYER 0 RESTORED"
echo "================================================================================"
sqlite3 Terminal1_MainBuilding_FILTERED.db "SELECT discipline, COUNT(*) FROM elements_meta GROUP BY discipline ORDER BY discipline;"
echo ""
echo "✅ Aborted to Layer 0 (ARC + STR only)"
echo ""
echo "Next: Run ./layer0_to_layer1.sh to generate FP"
echo ""
