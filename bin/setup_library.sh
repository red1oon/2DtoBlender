#!/bin/bash
################################################################################
# Library Setup and Validation Script
#
# RULE 0 COMPLIANCE:
# - Validates and fixes library database systematically
# - Idempotent: safe to run multiple times
# - No manual intervention required
#
# USAGE:
#   ./bin/setup_library.sh [--dry-run]
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_PATH="$PROJECT_ROOT/LocalLibrary/Ifc_Object_Library.db"

DRY_RUN=""
if [ "$1" == "--dry-run" ]; then
    DRY_RUN="--dry-run"
fi

echo "================================================================================"
echo "🔧 LIBRARY SETUP & VALIDATION"
echo "================================================================================"
echo "Project: $PROJECT_ROOT"
echo "Database: $DB_PATH"
echo ""

# Check database exists
if [ ! -f "$DB_PATH" ]; then
    echo "❌ Error: Database not found: $DB_PATH"
    echo "   Please ensure LocalLibrary/Ifc_Object_Library.db exists"
    exit 1
fi

echo "✅ Database found"
echo ""

# Run base_rotation fixer
echo "📐 STEP 1: Analyzing geometry orientations..."
echo "--------------------------------------------------------------------------------"
python3 "$PROJECT_ROOT/src/tools/fix_library_base_rotations.py" \
    --database "$DB_PATH" \
    $DRY_RUN

echo ""
echo "================================================================================"
if [ -n "$DRY_RUN" ]; then
    echo "✅ VALIDATION COMPLETE (dry run)"
    echo "   Run without --dry-run to apply fixes"
else
    echo "✅ LIBRARY SETUP COMPLETE"
    echo "   Database is ready for pipeline use"
fi
echo "================================================================================"
