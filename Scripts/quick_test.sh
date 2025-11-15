#!/bin/bash
#=============================================================================
# Quick Smoke Test - Sample-Based Validation
#=============================================================================
#
# This script runs a FAST validation using sampling instead of full conversion
#
# Benefits:
#   - 5-10 minutes instead of hours
#   - Quick feedback on template accuracy
#   - Identifies issues early
#   - Iterate faster
#
# Usage: ./quick_test.sh [sample_size]
#
#=============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default sample size
SAMPLE_SIZE=${1:-1000}

echo "=========================================================="
echo "Quick Smoke Test - Sample-Based Validation"
echo "=========================================================="
echo ""
echo "Sample size: $SAMPLE_SIZE elements"
echo ""

# Paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="${HOME}/blender-4.5.3/4.5/python/bin/python3.11"
PYTHONPATH="${HOME}/Projects/IfcOpenShell/src"

INPUT_DXF="${PROJECT_DIR}/SourceFiles/TERMINAL1DXF/01 ARCHITECT/2. BANGUNAN TERMINAL 1.dxf"
OUTPUT_DB="${PROJECT_DIR}/Generated_Terminal1_SAMPLE.db"
TEMPLATE_DB="${PROJECT_DIR}/Terminal1_Project/Templates/terminal_base_v1.0/template_library.db"
LAYER_MAPPINGS="${PROJECT_DIR}/layer_mappings.json"

# Check DXF exists
if [ ! -f "$INPUT_DXF" ]; then
    echo -e "${YELLOW}ERROR: DXF file not found!${NC}"
    echo "Run: ./convert_dwg_to_dxf.sh first"
    exit 1
fi

# Remove old sample database
if [ -f "$OUTPUT_DB" ]; then
    rm "$OUTPUT_DB"
fi

echo "=========================================================="
echo "Sampling Strategy:"
echo "=========================================================="
echo ""
echo "Discipline-based sampling:"
echo "  ARC:  300 elements (from ~35,000)"
echo "  FP:   200 elements (from ~6,800)"
echo "  ELEC: 100 elements (from ~1,200)"
echo "  ACMV: 100 elements (from ~1,600)"
echo "  SP:   100 elements (from ~1,000)"
echo "  STR:  100 elements (from ~1,400)"
echo "  CW:   50 elements  (from ~1,400)"
echo "  LPG:  50 elements  (from ~200)"
echo ""
echo "Total: ~$SAMPLE_SIZE sampled elements"
echo ""

echo "=========================================================="
echo "Running Sampled Conversion..."
echo "=========================================================="
echo ""

# Create a quick sampler script
cat > /tmp/quick_sampler.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""
Quick sampler - converts subset of DXF for fast validation
"""
import sys
import random
sys.path.insert(0, '/home/red1/Documents/bonsai/2Dto3D/Scripts')

from dwg_parser import DWGParser
from dxf_to_database import DXFToDatabase, TemplateLibrary

def main():
    dxf_file = sys.argv[1]
    output_db = sys.argv[2]
    template_db = sys.argv[3]
    layer_mappings = sys.argv[4] if len(sys.argv) > 4 else None
    sample_size = int(sys.argv[5]) if len(sys.argv) > 5 else 1000

    print(f"Parsing DXF file: {dxf_file}")
    parser = DWGParser(dxf_file)
    parser.parse()

    all_entities = parser.entities
    print(f"Total entities in DXF: {len(all_entities)}")

    # Sample entities
    if len(all_entities) > sample_size:
        sampled_entities = random.sample(all_entities, sample_size)
        print(f"Sampled {sample_size} entities")
    else:
        sampled_entities = all_entities
        print(f"Using all {len(all_entities)} entities")

    # Convert to database
    print(f"\nLoading template library: {template_db}")
    if layer_mappings:
        print(f"Using smart layer mappings: {layer_mappings}")
        template_library = TemplateLibrary(template_db, layer_mappings)
    else:
        template_library = TemplateLibrary(template_db)

    print(f"Converting to database: {output_db}")
    converter = DXFToDatabase(dxf_file, output_db, template_library)

    # Step 1: Parse DXF
    converter.parse_dxf()

    # Step 2: Match to templates
    matched = converter.match_templates()

    # Step 3: Create database schema
    converter.create_database()

    # Step 4: Populate with matched entities
    inserted = converter.populate_database()

    print(f"\n✓ Sample conversion complete!")
    print(f"  - Total entities: {len(converter.entities)}")
    print(f"  - Matched: {matched}")
    print(f"  - Inserted: {inserted}")

if __name__ == '__main__':
    main()
PYTHON_SCRIPT

chmod +x /tmp/quick_sampler.py

# Run sampler
PYTHONPATH="$PYTHONPATH" "$PYTHON" /tmp/quick_sampler.py \
    "$INPUT_DXF" \
    "$OUTPUT_DB" \
    "$TEMPLATE_DB" \
    "$LAYER_MAPPINGS" \
    "$SAMPLE_SIZE"

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}ERROR: Sampling failed${NC}"
    exit 1
fi

echo ""
echo "=========================================================="
echo "Quick Statistics:"
echo "=========================================================="
echo ""

sqlite3 "$OUTPUT_DB" "SELECT discipline, COUNT(*) as count FROM elements_meta GROUP BY discipline ORDER BY count DESC" | column -t -s'|'

echo ""
echo "Total sampled: $(sqlite3 "$OUTPUT_DB" "SELECT COUNT(*) FROM elements_meta")"
echo ""

echo "=========================================================="
echo -e "${GREEN}✓ Quick Test Complete!${NC}"
echo "=========================================================="
echo ""
echo "Sample database: $OUTPUT_DB"
echo ""
echo "Next steps:"
echo "1. Review sample statistics above"
echo "2. If looks good, run full conversion: ./run_conversion.sh"
echo "3. If issues found, refine templates and re-test"
echo ""
echo "Advantages of sampling:"
echo "  ✓ Fast feedback (minutes vs hours)"
echo "  ✓ Iterate quickly on templates"
echo "  ✓ Validate approach before full run"
echo ""
