#!/bin/bash
#=============================================================================
# Complete Fresh Generation - Clean MEP System Generation
#=============================================================================
set -e

echo "================================================================================"
echo "COMPLETE FRESH MEP GENERATION"
echo "================================================================================"
echo ""

DB_NAME="Terminal1_MainBuilding_FILTERED.db"
BASE_CLEAN="Fresh_Terminal1_FIXED.db"

echo "Step 1: Start from clean base (ARC + STR from DXF)"
if [ ! -f "$BASE_CLEAN" ]; then
    echo "❌ Base file not found: $BASE_CLEAN"
    exit 1
fi

cp "$BASE_CLEAN" "$DB_NAME"
echo "✅ Copied $BASE_CLEAN to $DB_NAME"
echo ""

echo "Step 2: Generate Fire Protection (FP) system with colors"
echo "  - Auto-cleanup removes old FP elements"
echo "  - Generates sprinklers + pipes with RED colors"
python3 Scripts/master_routing.py "$DB_NAME" --discipline FP --generate-devices
echo ""

echo "Step 3: Generate Electrical (ELEC) system with colors"
echo "  - Auto-cleanup removes old ELEC elements"
echo "  - Generates lights + conduits with YELLOW colors"
python3 Scripts/master_routing.py "$DB_NAME" --discipline ELEC --device-type light_fixture --generate-devices
echo ""

echo "Step 4: Verify final result"
sqlite3 "$DB_NAME" << SQL
SELECT 
  '================================================================================' as separator;
SELECT 'FINAL DATABASE STATUS' as status;
SELECT 
  '================================================================================' as separator;
SELECT 
  e.discipline,
  COUNT(*) as elements,
  SUM(CASE WHEN ma.rgba IS NOT NULL THEN 1 ELSE 0 END) as with_color,
  ROUND(100.0 * SUM(CASE WHEN ma.rgba IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) || '%' as pct_colored,
  CASE e.discipline
    WHEN 'FP' THEN 'RED'
    WHEN 'ELEC' THEN 'YELLOW'
    WHEN 'ARC' THEN 'LIGHT GRAY'
    WHEN 'STR' THEN 'GRAY'
  END as color_name
FROM elements_meta e
LEFT JOIN material_assignments ma ON e.guid = ma.guid
GROUP BY e.discipline
ORDER BY e.discipline;
SELECT 
  '================================================================================' as separator;
SQL

echo ""
echo "================================================================================"
echo "✅ COMPLETE FRESH GENERATION FINISHED!"
echo "================================================================================"
echo ""
echo "Next: Load $DB_NAME in Blender Full Load mode"
echo "  - FP (red): Sprinklers + pipes"
echo "  - ELEC (yellow): Lights + conduits"
echo "  - ARC (light gray): Walls, doors, windows"
echo "  - STR (gray): Columns"
echo ""
