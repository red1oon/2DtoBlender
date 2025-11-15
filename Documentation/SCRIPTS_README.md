# RawDWG Scripts and Tools

**Location:** `/home/red1/Documents/bonsai/RawDWG/`
**Purpose:** Template extraction and management for DWG → IFC conversion

---

## Overview

This folder contains all the scripts and tools for the **template-driven BIM generation** POC. Everything needed for the workflow is centralized here for easy access.

---

## Folder Structure

```
RawDWG/
├── *.py                              # Python scripts (executable)
├── *.sql                             # Database schemas
├── *.md                              # Documentation
├── Terminal1_Project/                # Project template sets
│   └── Templates/
│       └── terminal_base_v1.0/
│           ├── template_library.db   # 44 templates extracted
│           └── metadata.json         # Template set metadata
├── test_template_library.db          # Test database
└── extraction_log.txt                # Latest extraction log
```

---

## Core Scripts

### 1. `init_template_library.py` ✅
**Purpose:** Initialize new template library databases

**Usage:**
```bash
python3 init_template_library.py [output_path]
```

**Examples:**
```bash
# Create in current directory
python3 init_template_library.py template_library.db

# Create in template set directory
python3 init_template_library.py Terminal1_Project/Templates/my_set/template_library.db
```

**What it does:**
- Creates template_library.db with complete schema (14 tables, 3 views)
- Loads 8 default categories
- Validates schema integrity
- Returns clear success/failure messages

---

### 2. `create_template_metadata.py` ✅
**Purpose:** Create and validate metadata.json for template sets

**Usage:**
```bash
# Create default metadata
python3 create_template_metadata.py create [template_dir]

# Create with interactive prompts
python3 create_template_metadata.py create [template_dir] --interactive

# Validate existing metadata
python3 create_template_metadata.py validate [template_dir]
```

**Examples:**
```bash
# Quick creation (defaults)
python3 create_template_metadata.py create Terminal1_Project/Templates/terminal_base_v1.0/

# Interactive mode (guided)
python3 create_template_metadata.py create Terminal1_Project/Templates/terminal_base_v1.0/ --interactive

# Validate
python3 create_template_metadata.py validate Terminal1_Project/Templates/terminal_base_v1.0/
```

**What it does:**
- Creates metadata.json with version, author, statistics
- Auto-detects template counts from database
- Validates structure and required fields
- Supports interactive mode for detailed input

---

### 3. `extract_templates.py` ✅
**Purpose:** Extract templates from Terminal 1 database

**Usage:**
```bash
python3 extract_templates.py [source_db] [template_lib_db] [options]
```

**Options:**
- `--discipline DISC` - Extract only specified discipline (ARC, FP, ELEC, etc.)
- `--all` - Extract all disciplines (default)

**Examples:**
```bash
# Extract all disciplines
python3 extract_templates.py \
    /home/red1/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db \
    Terminal1_Project/Templates/terminal_base_v1.0/template_library.db

# Extract only Fire Protection
python3 extract_templates.py \
    /home/red1/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db \
    Terminal1_Project/Templates/terminal_base_v1.0/template_library.db \
    --discipline FP

# Extract Electrical
python3 extract_templates.py \
    /home/red1/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db \
    Terminal1_Project/Templates/terminal_base_v1.0/template_library.db \
    --discipline ELEC
```

**What it does:**
- Connects to Terminal 1 database (FullExtractionTesellated.db)
- Analyzes element patterns by discipline and IFC class
- Extracts instance counts, materials, types
- Creates templates with confidence scores
- Saves to template_library.db
- Logs extraction statistics

**Latest Results:**
- **44 templates extracted** from Terminal 1
- Disciplines: ARC (13), FP (9), ELEC (3), ACMV (4), SP (3), STR (4), CW (5), LPG (3)
- Source: 49,059 elements analyzed

---

## Database Schema

### `create_template_library_schema.sql`
Complete SQL schema for template library database.

**Tables (14):**
- `element_templates` - Main template definitions
- `template_parameters` - Fixed, flexible, derived parameters
- `derivation_rules` - Logic and formulas
- `spatial_patterns` - Layout strategies
- `code_requirements` - Building code compliance
- `material_specifications` - Material and cost data
- `adaptation_rules` - Variance handling
- `geometry_definitions` - 3D geometry specs
- `validation_history` - Accuracy tracking
- `usage_statistics` - Usage metrics
- `template_relationships` - Inter-template dependencies
- `template_set_metadata` - Version info
- `template_categories` - Organization
- `schema_version` - Version control

**Views (3):**
- `v_complete_templates` - All template data joined
- `v_active_templates` - Only active templates
- `v_template_statistics` - Summary statistics

---

## Documentation Files

### Methodology
- **`POC_METHODOLOGY_COMPLETE.md`** - Complete POC methodology (53 KB)
  - System architecture
  - Folder structure
  - Database schema
  - Validation approach
  - 8-week roadmap
  - User workflows

- **`IMPLEMENTATION_PROGRESS.md`** - Progress tracking (9 KB)
  - What's completed
  - Current status
  - Next steps
  - Commands reference

### Background
- **`FINAL_UNDERSTANDING.md`** - Template-driven concept (like iDempiere)
- **`TEMPLATE_EXTRACTION_STRATEGY.md`** - Reverse engineering approach
- **`SIMPLE_PRACTICAL_APPROACH.md`** - Practical workflow
- **`HONEST_ASSESSMENT_ALGORITHMS.md`** - Technical challenges
- **`INTELLIGENCE_LAYER_MEP_DERIVATION.md`** - MEP generation strategy

---

## Quick Start Workflow

### Step 1: Create New Template Set
```bash
# 1. Create directory
mkdir -p Terminal1_Project/Templates/my_template_v1.0/

# 2. Initialize database
python3 init_template_library.py \
    Terminal1_Project/Templates/my_template_v1.0/template_library.db

# 3. Create metadata
python3 create_template_metadata.py create \
    Terminal1_Project/Templates/my_template_v1.0/
```

### Step 2: Extract Templates
```bash
# Extract all disciplines from Terminal 1
python3 extract_templates.py \
    /home/red1/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db \
    Terminal1_Project/Templates/my_template_v1.0/template_library.db
```

### Step 3: Validate
```bash
# Check template count
sqlite3 Terminal1_Project/Templates/my_template_v1.0/template_library.db \
    "SELECT COUNT(*) FROM element_templates;"

# View statistics
sqlite3 Terminal1_Project/Templates/my_template_v1.0/template_library.db \
    "SELECT * FROM v_template_statistics;"

# Validate metadata
python3 create_template_metadata.py validate \
    Terminal1_Project/Templates/my_template_v1.0/
```

---

## Useful Database Queries

### View All Templates
```bash
sqlite3 template_library.db "SELECT template_name, ifc_class, instance_count, confidence_score FROM element_templates ORDER BY instance_count DESC;"
```

### Count by Category
```bash
sqlite3 template_library.db "SELECT * FROM v_template_statistics;"
```

### Find Specific Template
```bash
sqlite3 template_library.db "SELECT * FROM element_templates WHERE template_name LIKE '%Sprinkler%';"
```

### Export Templates to CSV
```bash
sqlite3 -header -csv template_library.db "SELECT * FROM element_templates;" > templates.csv
```

---

## Template Set: terminal_base_v1.0

**Location:** `Terminal1_Project/Templates/terminal_base_v1.0/`

**Status:** ✅ Extracted and ready

**Statistics:**
- Total templates: **44**
- Extracted from: Terminal 1 (FullExtractionTesellated.db)
- Extraction date: 2025-11-11
- Source elements: 49,059

**By Discipline:**
- ARC (Architecture): 13 templates
- FP (Fire Protection): 9 templates
- ELEC (Electrical): 3 templates
- ACMV (Mechanical): 4 templates
- SP (Plumbing): 3 templates
- STR (Structure): 4 templates
- CW (Chilled Water): 5 templates
- LPG (Gas): 3 templates

**Database Size:** 188 KB
**Metadata:** metadata.json (complete)

---

## Next Steps

### For POC Development:
1. ✅ **Phase 1 Complete:** Template extraction working
2. ⏳ **Phase 2 Next:** Build Bonsai addon integration
   - Create folder picker UI
   - Template set selector
   - DWG parser
   - IFC generator

### For Template Refinement:
1. Add template parameters (dimensions, spacing rules)
2. Add derivation rules (formulas, logic)
3. Add spatial patterns (grid layouts, spacing)
4. Add code requirements (clearances, minimums)
5. Test variance scenarios

### For Production:
1. Extract additional template sets (v1.5, v2.0)
2. Build Template Studio (parameter editor UI)
3. Validate accuracy (generate → compare)
4. Deploy to Bonsai addon

---

## Troubleshooting

### "Database not found"
**Solution:** Check path is absolute, not relative
```bash
# Wrong
python3 extract_templates.py database.db template.db

# Correct
python3 extract_templates.py /home/red1/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db Terminal1_Project/Templates/terminal_base_v1.0/template_library.db
```

### "Template already exists"
**Solution:** This is normal - script skips duplicates. Or delete and re-extract:
```bash
rm Terminal1_Project/Templates/terminal_base_v1.0/template_library.db
python3 init_template_library.py Terminal1_Project/Templates/terminal_base_v1.0/template_library.db
python3 extract_templates.py ...
```

### "No templates extracted"
**Solution:** Check discipline code spelling (must be uppercase):
```bash
# Wrong
--discipline fp

# Correct
--discipline FP
```

---

## File Permissions

All scripts are executable:
```bash
chmod +x *.py
```

---

## Dependencies

**Python 3.9+** with standard library:
- sqlite3
- json
- pathlib
- datetime
- collections

No external packages required! ✅

---

## Version History

- **v1.0** (2025-11-11): Initial release
  - Database schema created
  - 3 core scripts working
  - 44 templates extracted from Terminal 1
  - Complete documentation

---

## Support

For issues or questions:
1. Check `IMPLEMENTATION_PROGRESS.md` for current status
2. Review `POC_METHODOLOGY_COMPLETE.md` for design decisions
3. Check extraction logs in `extraction_log.txt`

---

**Last Updated:** 2025-11-11
**Status:** ✅ Foundation complete, ready for Bonsai integration
