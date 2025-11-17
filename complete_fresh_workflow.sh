#!/bin/bash
set -e

echo "================================================================================"
echo "COMPLETE FRESH WORKFLOW: Layer 0 → Layer 1 → Layer 2"
echo "================================================================================"
echo ""
echo "This script runs all layers in sequence:"
echo "  Layer 0: BASE_ARC_STR.db (ARC + STR)"
echo "  Layer 1: Add FP (Fire Protection)"
echo "  Layer 2: Add ELEC (Electrical)"
echo ""
echo "For individual layer control, use:"
echo "  ./abort_to_layer0.sh   - Start over"
echo "  ./layer0_to_layer1.sh  - Generate/redo FP"
echo "  ./layer1_to_layer2.sh  - Generate/redo ELEC"
echo "  ./abort_to_layer1.sh   - Remove ELEC, keep FP"
echo ""
echo "================================================================================"
echo ""

cd /home/red1/Documents/bonsai/2Dto3D

# Abort to Layer 0
./abort_to_layer0.sh

# Layer 0 → Layer 1 (FP)
./layer0_to_layer1.sh

# Layer 1 → Layer 2 (ELEC)
./layer1_to_layer2.sh

echo ""
echo "================================================================================"
echo "COMPLETE WORKFLOW FINISHED"
echo "================================================================================"
echo "✅ All layers generated successfully"
echo "✅ Ready to load in Blender: Terminal1_MainBuilding_FILTERED.db"
echo ""
