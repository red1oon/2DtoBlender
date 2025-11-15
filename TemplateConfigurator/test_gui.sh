#!/bin/bash
#
# Quick test script for Template Configurator GUI
# Tests the smart import tab with 2D canvas
#

cd "$(dirname "$0")"

echo "========================================="
echo "Template Configurator GUI Test"
echo "========================================="
echo ""
echo "Features to test:"
echo "  1. Upload DXF file"
echo "  2. Smart mapping (81.3% auto-classification)"
echo "  3. 2D visual canvas with discipline colors"
echo "  4. Review unmapped layers"
echo "  5. Export mappings to JSON"
echo ""
echo "Starting GUI..."
echo ""

python3 main.py
