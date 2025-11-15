#!/bin/bash
#=============================================================================
# Complete DXF → Database Conversion Pipeline
#=============================================================================
#
# This script runs the complete conversion from DXF to Database
#
# Prerequisites:
#   - Terminal 1 DXF file must exist (run convert_dwg_to_dxf.sh first)
#   - Template library must exist
#
# Usage: ./run_conversion.sh
#
#=============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================================="
echo "DXF → Database Conversion Pipeline"
echo "=========================================================="
echo ""

# Paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON="${HOME}/blender-4.5.3/4.5/python/bin/python3.11"
PYTHONPATH="${HOME}/Projects/IfcOpenShell/src"

INPUT_DXF="${SCRIPT_DIR}/2. BANGUNAN TERMINAL 1 .dxf"
OUTPUT_DB="${SCRIPT_DIR}/Generated_Terminal1.db"
TEMPLATE_DB="${SCRIPT_DIR}/Terminal1_Project/Templates/terminal_base_v1.0/template_library.db"
ORIGINAL_DB="${HOME}/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db"

# Check prerequisites
echo "Checking prerequisites..."
echo ""

if [ ! -f "$INPUT_DXF" ]; then
    echo -e "${RED}ERROR: DXF file not found!${NC}"
    echo "Expected: $INPUT_DXF"
    echo ""
    echo "Please convert DWG to DXF first:"
    echo "./convert_dwg_to_dxf.sh"
    exit 1
fi
echo -e "${GREEN}✓ DXF file found${NC} ($(du -h "$INPUT_DXF" | cut -f1))"

if [ ! -f "$TEMPLATE_DB" ]; then
    echo -e "${RED}ERROR: Template library not found!${NC}"
    echo "Expected: $TEMPLATE_DB"
    exit 1
fi
echo -e "${GREEN}✓ Template library found${NC} ($(du -h "$TEMPLATE_DB" | cut -f1))"

if [ ! -f "$ORIGINAL_DB" ]; then
    echo -e "${YELLOW}WARNING: Original database not found${NC}"
    echo "Expected: $ORIGINAL_DB"
    echo "Comparison will not be possible."
else
    echo -e "${GREEN}✓ Original database found${NC} ($(du -h "$ORIGINAL_DB" | cut -f1))"
fi

if [ ! -f "$PYTHON" ]; then
    echo -e "${RED}ERROR: Python not found!${NC}"
    echo "Expected: $PYTHON"
    exit 1
fi
echo -e "${GREEN}✓ Python found${NC}"

if [ ! -f "${SCRIPT_DIR}/dwg_parser.py" ]; then
    echo -e "${RED}ERROR: dwg_parser.py not found!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Parser script found${NC}"

if [ ! -f "${SCRIPT_DIR}/dxf_to_database.py" ]; then
    echo -e "${RED}ERROR: dxf_to_database.py not found!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Converter script found${NC}"

echo ""
echo "=========================================================="
echo "STEP 1: Parse DXF File"
echo "=========================================================="
echo ""

cd "$SCRIPT_DIR"
PYTHONPATH="$PYTHONPATH" "$PYTHON" dwg_parser.py "$INPUT_DXF" | tee /tmp/dxf_parse.log

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo -e "${RED}ERROR: DXF parsing failed!${NC}"
    echo "Check log: /tmp/dxf_parse.log"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ DXF parsing complete${NC}"
echo ""

echo "=========================================================="
echo "STEP 2: Convert to Database"
echo "=========================================================="
echo ""

# Remove old generated database if exists
if [ -f "$OUTPUT_DB" ]; then
    echo -e "${YELLOW}Removing old generated database...${NC}"
    rm "$OUTPUT_DB"
    echo ""
fi

echo "Running conversion..."
echo "This may take several minutes..."
echo ""

PYTHONPATH="$PYTHONPATH" "$PYTHON" dxf_to_database.py \
    "$INPUT_DXF" \
    "$OUTPUT_DB" \
    "$TEMPLATE_DB" \
    | tee /tmp/dxf_to_db.log

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo -e "${RED}ERROR: Database conversion failed!${NC}"
    echo "Check log: /tmp/dxf_to_db.log"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Database generation complete${NC}"
echo ""

# Check generated database
if [ ! -f "$OUTPUT_DB" ]; then
    echo -e "${RED}ERROR: Generated database not created!${NC}"
    exit 1
fi

echo "Generated database: $OUTPUT_DB"
echo "Size: $(du -h "$OUTPUT_DB" | cut -f1)"
echo ""

echo "=========================================================="
echo "STEP 3: Quick Statistics"
echo "=========================================================="
echo ""

echo "Element counts by discipline:"
echo ""
sqlite3 "$OUTPUT_DB" "SELECT discipline, COUNT(*) as count FROM elements_meta GROUP BY discipline ORDER BY count DESC" | column -t -s'|'
echo ""

echo "Total elements: $(sqlite3 "$OUTPUT_DB" "SELECT COUNT(*) FROM elements_meta")"
echo ""

if [ -f "$ORIGINAL_DB" ]; then
    echo "=========================================================="
    echo "STEP 4: Quick Comparison with Original"
    echo "=========================================================="
    echo ""

    echo "Original database element counts:"
    echo ""
    sqlite3 "$ORIGINAL_DB" "SELECT discipline, COUNT(*) as count FROM elements_meta GROUP BY discipline ORDER BY count DESC" | column -t -s'|'
    echo ""

    echo "Total elements (original): $(sqlite3 "$ORIGINAL_DB" "SELECT COUNT(*) FROM elements_meta")"
    echo ""
fi

echo "=========================================================="
echo -e "${GREEN}✓ Conversion Pipeline Complete!${NC}"
echo "=========================================================="
echo ""
echo "Output files:"
echo "  - Generated DB: $OUTPUT_DB"
echo "  - Parse log: /tmp/dxf_parse.log"
echo "  - Conversion log: /tmp/dxf_to_db.log"
echo ""
echo "Next steps:"
echo "1. Review logs for any warnings or errors"
echo "2. Run detailed comparison: python database_comparator.py"
echo "3. Open in Bonsai to visualize results"
echo ""
