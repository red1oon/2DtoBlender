#!/bin/bash
#=============================================================================
# DWG to DXF Conversion Script
#=============================================================================
#
# This script converts Terminal 1 DWG file to DXF format using ODA File Converter
#
# Usage: ./convert_dwg_to_dxf.sh
#
#=============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================================="
echo "DWG to DXF Conversion Script"
echo "=================================================="
echo ""

# Check if ODA File Converter is installed
if ! command -v ODAFileConverter &> /dev/null; then
    echo -e "${RED}ERROR: ODAFileConverter not found!${NC}"
    echo ""
    echo "Please install ODA File Converter first:"
    echo "1. Download from: https://www.opendesign.com/guestfiles/oda_file_converter"
    echo "2. Install: sudo dpkg -i ODAFileConverter_*.deb"
    echo "3. Or see: INSTALL_ODA_CONVERTER.md"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ ODA File Converter found${NC}"
echo ""

# Set paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INPUT_DWG="${SCRIPT_DIR}/2. BANGUNAN TERMINAL 1 .dwg"
OUTPUT_DIR="${SCRIPT_DIR}"
OUTPUT_DXF="${OUTPUT_DIR}/2. BANGUNAN TERMINAL 1 .dxf"

# Check if input file exists
if [ ! -f "$INPUT_DWG" ]; then
    echo -e "${RED}ERROR: Input DWG file not found!${NC}"
    echo "Expected: $INPUT_DWG"
    exit 1
fi

echo "Input file: $INPUT_DWG"
echo "File size: $(du -h "$INPUT_DWG" | cut -f1)"
echo ""

# Check if output file already exists
if [ -f "$OUTPUT_DXF" ]; then
    echo -e "${YELLOW}WARNING: Output DXF file already exists!${NC}"
    echo "File: $OUTPUT_DXF"
    echo "Size: $(du -h "$OUTPUT_DXF" | cut -f1)"
    echo ""
    read -p "Overwrite? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Conversion cancelled."
        exit 0
    fi
    echo "Removing old DXF file..."
    rm "$OUTPUT_DXF"
    echo ""
fi

# Create temporary directory for conversion
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"
echo ""

# Copy DWG to temp directory (ODA File Converter works on directories)
echo "Preparing files..."
cp "$INPUT_DWG" "$TEMP_DIR/"

# Run conversion
echo "Converting DWG to DXF..."
echo "This may take 1-2 minutes for large files..."
echo ""

ODAFileConverter \
    "$TEMP_DIR" \
    "$TEMP_DIR" \
    "ACAD2018" \
    "DXF" \
    "0" \
    "1" \
    2>&1 | tee /tmp/oda_conversion.log

# Check if conversion succeeded
CONVERTED_DXF="${TEMP_DIR}/2. BANGUNAN TERMINAL 1 .dxf"
if [ ! -f "$CONVERTED_DXF" ]; then
    echo -e "${RED}ERROR: Conversion failed!${NC}"
    echo "Check log: /tmp/oda_conversion.log"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Move converted file to output directory
echo ""
echo "Moving converted file..."
mv "$CONVERTED_DXF" "$OUTPUT_DXF"

# Cleanup
echo "Cleaning up..."
rm -rf "$TEMP_DIR"

# Success!
echo ""
echo "=================================================="
echo -e "${GREEN}✓ Conversion successful!${NC}"
echo "=================================================="
echo ""
echo "Output file: $OUTPUT_DXF"
echo "File size: $(du -h "$OUTPUT_DXF" | cut -f1)"
echo ""
echo "Next steps:"
echo "1. Test parser: PYTHONPATH=/home/red1/Projects/IfcOpenShell/src ~/blender-4.5.3/4.5/python/bin/python3.11 dwg_parser.py \"$OUTPUT_DXF\""
echo "2. Run conversion: ./run_conversion.sh"
echo ""
