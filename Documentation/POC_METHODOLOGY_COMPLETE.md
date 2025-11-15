# POC Methodology: Template-Driven BIM Generation

**Date:** November 11, 2025
**Version:** 1.0
**Status:** Final Design - Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Core Concept](#core-concept)
3. [Architecture Overview](#architecture-overview)
4. [POC Folder Structure](#poc-folder-structure)
5. [Tool 1: Template Studio](#tool-1-template-studio)
6. [Tool 2: Bonsai Addon](#tool-2-bonsai-addon)
7. [Template Set Architecture](#template-set-architecture)
8. [Validation Methodology](#validation-methodology)
9. [Success Criteria](#success-criteria)
10. [Implementation Roadmap](#implementation-roadmap)
11. [User Workflows](#user-workflows)
12. [Technical Specifications](#technical-specifications)

---

## Executive Summary

### The Goal

Create a **template-driven system** that can:
1. Extract patterns from existing 3D models (Terminal 1 database)
2. Store patterns as reusable templates (template library)
3. Apply templates to new 2D DWGs (Terminal 2+)
4. Generate complete 8-discipline 3D models automatically
5. Validate accuracy by recreating Terminal 1 from scratch

### The Validation Test

**Blind Trial:**
- Input: Raw Terminal 1 DWGs (same files consultants provided)
- Input: template_library.db (extracted patterns, no peeking at 3D database!)
- Process: Addon generates 3D model from templates only
- Output: Generated_Terminal1.db (new database)
- Validation: Compare original vs generated (measure accuracy)

**Success Threshold:** 90%+ element count accuracy, <0.5m spatial delta

---

## Core Concept

### Working Backwards from the "Finishing Line"

```
┌──────────────────────────────────────────────────────────────┐
│ PHASE 1: LEARNING (Terminal 1 as Teacher)                    │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ Terminal 1 (Finished Product) = "Answer Key"                │
│          ↓                                                    │
│    Work Backwards                                            │
│          ↓                                                    │
│ Extract Patterns = "Metadata Templates"                     │
│          ↓                                                    │
│ Package as template_library.db (5-10MB)                     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ PHASE 2: VALIDATION (Blind Test - No Peeking!)              │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ Input: Raw Terminal 1 DWGs + template_library.db            │
│ ❌ NO ACCESS to original 3D database                        │
│          ↓                                                    │
│ Apply Templates Forward                                      │
│          ↓                                                    │
│ Generate: New 3D model from scratch                         │
│          ↓                                                    │
│ Output: Generated_Terminal1.db                              │
│                                                               │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ PHASE 3: COMPARISON (Did We Recreate It?)                   │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ Compare: Original DB vs Generated DB                         │
│          ↓                                                    │
│ Metrics: Element counts, positions, properties              │
│          ↓                                                    │
│ Result: 95% accuracy = Templates Work! ✅                   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Analogy: iDempiere Metadata

Like iDempiere uses metadata (table definitions, field properties) to generate UI forms, we use **BIM templates** (element definitions, spatial rules) to generate 3D models.

**Key Insight:** Templates are not hardcoded logic - they're **editable metadata** that encode domain knowledge.

---

## Architecture Overview

### Two-Tool System

```
┌─────────────────────────────────────────────────────────────┐
│ TOOL 1: Template Studio (Standalone Python App)            │
│ Purpose: Template Management & Refinement                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Users: BIM Specialists, Template Curators                   │
│                                                              │
│ Features:                                                    │
│ ├─ Extract templates from 3D databases                      │
│ ├─ View/edit template parameters                           │
│ ├─ Test templates on mock scenarios                        │
│ ├─ Validate accuracy (database comparison)                 │
│ └─ Export template sets (versioned)                        │
│                                                              │
│ Tech Stack:                                                  │
│ └─ Python + PyQt6/Streamlit + SQLite                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                         ↓
              (exports template_library.db)
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ TOOL 2: Bonsai Addon (Blender Plugin)                      │
│ Purpose: Production DWG → IFC Conversion                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Users: Project Teams, Consultants                           │
│                                                              │
│ Features:                                                    │
│ ├─ Simple UI: Select project folder                        │
│ ├─ Choose template set (v1.0, v1.5, v2.0, etc.)           │
│ ├─ Generate 8-discipline model (automated)                 │
│ ├─ Review in Blender 3D view + Outliner                   │
│ └─ Export 8 IFC files                                      │
│                                                              │
│ Tech Stack:                                                  │
│ └─ Blender addon + IfcOpenShell + SQLite                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Why Separate Tools?

**Different User Roles:**
- Template Studio: Power users who refine templates
- Bonsai Addon: End users who just want results

**Separation of Complexity:**
- Template Studio: Complex parameter tuning, validation
- Bonsai Addon: Simple folder selection, one-click generation

**Independent Development:**
- Template Studio: Rapid iteration (improve templates weekly)
- Bonsai Addon: Stable releases (quarterly)

---

## POC Folder Structure

### Complete Project Organization

```
/home/red1/Documents/bonsai/RawDWG/
│
├─── Terminal1_Project/                    ← Project folder
│    │
│    ├─── DWG/                             ← Source DWG files
│    │    ├─ 2. BANGUNAN TERMINAL 1.dwg  (ARC)
│    │    └─ 2. TERMINAL-1/               (STR - 18 files)
│    │
│    ├─── Templates/                       ← Template sets (multiple!)
│    │    │
│    │    ├─── terminal_base_v1.0/        ← Baseline extraction
│    │    │    ├─ template_library.db     (90 templates)
│    │    │    ├─ metadata.json           (set info)
│    │    │    └─ README.md               (documentation)
│    │    │
│    │    ├─── terminal_refined_v1.5/     ← Improved version
│    │    │    ├─ template_library.db     (105 templates)
│    │    │    ├─ metadata.json
│    │    │    └─ CHANGELOG.md            (what changed)
│    │    │
│    │    ├─── terminal_experimental_v2.0/ ← Cutting edge
│    │    │    ├─ template_library.db     (120 templates)
│    │    │    ├─ metadata.json
│    │    │    └─ README.md
│    │    │
│    │    └─── singapore_airport_standard/ ← Regional standard
│    │         ├─ template_library.db     (150 templates)
│    │         ├─ metadata.json
│    │         └─ certification.pdf       (authority-approved)
│    │
│    └─── Output/                          ← Generated results
│         │
│         ├─── Run_2025-11-11_v1.0/       ← Timestamped run
│         │    ├─ Generated_Terminal1.db  (comparison target)
│         │    ├─ Terminal1_ARC.ifc
│         │    ├─ Terminal1_STR.ifc
│         │    ├─ Terminal1_FP.ifc
│         │    ├─ Terminal1_ELEC.ifc
│         │    ├─ Terminal1_ACMV.ifc
│         │    ├─ Terminal1_SP.ifc
│         │    ├─ Terminal1_CW.ifc
│         │    ├─ Terminal1_LPG.ifc
│         │    ├─ generation_report.html  (what was generated)
│         │    └─ validation_report.html  (accuracy metrics)
│         │
│         └─── Run_2025-11-11_v1.5/       ← Different template set
│              ├─ Generated_Terminal1.db
│              ├─ ... (8 IFC files)
│              └─ validation_report.html  (v1.5 vs v1.0 comparison)
│
└─── Terminal2_Project/                    ← New project (production)
     ├─── DWG/
     │    ├─ Terminal2_ARC.dwg
     │    └─ Terminal2_STR/
     │
     ├─── Templates/                       ← Reuse proven templates
     │    └─── singapore_airport_standard/ (copy from Terminal1)
     │
     └─── Output/
          └─── Run_2025-11-15_production/
               ├─ Generated_Terminal2.db
               └─ ... (8 IFCs)
```

### Key Design Decisions

**1. DWGs and Templates in Same Project Folder**
- Convenience: One folder contains everything
- Portability: Copy folder = copy entire project
- Simplicity: Bonsai just needs one folder path

**2. Multiple Template Sets in Templates/ Folder**
- Iteration: v1.0 → v1.5 → v2.0 progression
- A/B Testing: Compare different approaches
- Regional Variants: Singapore vs Malaysia standards
- Client-Specific: Budget vs Premium specifications

**3. Timestamped Output Folders**
- Comparison: Side-by-side validation
- Traceability: Which template set was used
- Safety: Never overwrite previous runs

---

## Tool 1: Template Studio

### Purpose

Standalone Python application for BIM specialists to:
- Extract templates from existing 3D databases
- Edit template parameters and rules
- Test templates on mock scenarios
- Validate accuracy via database comparison
- Export versioned template sets

### Main Window UI

```
┌─────────────────────────────────────────────────────────────┐
│ Bonsai Template Studio v1.0                  [_][□][×]      │
├───────────┬─────────────────────────────────────────────────┤
│           │                                                  │
│ 📁 Library│  Template: Gate_Seating_8x15                    │
│           │  ┌──────────────────────────────────────────┐   │
│ Seating   │  │ Category: Seating                         │   │
│ ├─ Gate   │  │ Type: Rectangular Grid                   │   │
│ ├─ Lounge │  │ Version: 2.1                             │   │
│ └─ Food   │  │ Confidence: 98%                          │   │
│           │  │ Usage: 47 projects                       │   │
│ Fire      │  └──────────────────────────────────────────┘   │
│ ├─ Sprink │                                                  │
│ └─ Alarms │  ═══ PARAMETERS ═══════════════════════════    │
│           │                                                  │
│ Electrical│  [Fixed] [Flexible] [Derived] [Rules]          │
│           │                                                  │
│ ACMV      │  ┌─ Flexible Parameters ────────────────────┐   │
│           │  │                                           │   │
│ Plumbing  │  │ row_count                                │   │
│           │  │ ├─ Type: Integer                         │   │
│ Structure │  │ ├─ Range: [0 - 20]    Default: 8        │   │
│           │  │ ├─ Editable: ✓ Yes                      │   │
│ [+ New]   │  │ └─ Desc: Number of rows                 │   │
│ [Import]  │  │     0 = empty hall (skip template)      │   │
│ [Export]  │  │                                           │   │
│           │  │ seats_per_row                            │   │
│           │  │ ├─ Range: [8 - 20]    Default: 15       │   │
│           │  │ └─ Affects: total_seats, layout_width   │   │
│           │  │                                           │   │
│           │  │ density_mode                             │   │
│           │  │ ├─ Options: comfort|standard|high        │   │
│           │  │ └─ Affects: spacing, aisle_frequency    │   │
│           │  │                                           │   │
│           │  │ [+ Add Parameter]                        │   │
│           │  └───────────────────────────────────────────┘   │
│           │                                                  │
│           │  [Test] [3D Preview] [Save Changes]             │
│           │                                                  │
├───────────┴─────────────────────────────────────────────────┤
│ Status: 127 templates loaded | Last save: 2 min ago         │
└─────────────────────────────────────────────────────────────┘
```

### Core Features

#### 1. Template Viewer
- Hierarchical tree view by category
- Search by name, parameters, usage
- Template details panel (metadata, statistics, history)

#### 2. Parameter Editor
- Edit with live validation
- Add new parameters (wizard)
- Define derivation rules (formula builder)
- Code compliance checks

#### 3. Template Tester
- Test on mock room polygons
- Live 3D preview (matplotlib/plotly)
- Automated variance scenario testing
- Compare against reference database

#### 4. Template Extractor
- Extract from existing 3D databases
- Pattern detection algorithms
- Auto-detect variants
- Guided wizard workflow

#### 5. Validation Dashboard
- Database comparison metrics
- Element count accuracy
- Spatial position delta
- Property match percentage
- Detailed failure analysis

### Technology Stack

```python
# UI Framework
PyQt6           # Native desktop app (professional)
# OR
Streamlit       # Web-based (rapid prototyping)

# Data
SQLite          # template_library.db
Pandas          # Data analysis
NumPy           # Spatial calculations

# Visualization
Matplotlib      # 3D preview
Plotly          # Interactive charts

# Testing
Pytest          # Automated template validation

# Distribution
PyInstaller     # Standalone .exe
# OR
Docker          # Web app deployment
```

---

## Tool 2: Bonsai Addon

### Purpose

Blender plugin for project teams to:
- Import DWG projects (simple folder selection)
- Choose template set (v1.0, v1.5, v2.0, etc.)
- Generate 8-discipline 3D model automatically
- Review results in Blender 3D view
- Export IFC files

### User Interface

#### Main Dialog

```
┌─────────────────────────────────────────────────────────────┐
│ Bonsai Federation - Import DWG Project                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ 1. Select Project Folder                                    │
│    ┌────────────────────────────────────────────────────┐  │
│    │ /home/.../RawDWG/Terminal1_Project/   [Browse...] │  │
│    └────────────────────────────────────────────────────┘  │
│                                                              │
│    ✓ Found: 2 DWG files (ARC), 18 DWG files (STR)          │
│    ✓ Found: 4 template sets in Templates/ folder           │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ 2. Select Template Set                                      │
│                                                              │
│    ○ terminal_base_v1.0                                     │
│      └─ 90 templates | Baseline extraction                 │
│                                                              │
│    ○ terminal_refined_v1.5                                  │
│      └─ 105 templates | Improved seating + FP              │
│                                                              │
│    ● terminal_experimental_v2.0  ← Selected                 │
│      └─ 120 templates | Edge case handling                 │
│                                                              │
│    ○ singapore_airport_standard                             │
│      └─ 150 templates | Authority approved                 │
│                                                              │
│    [View Template Set Details...]                           │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ 3. Output Options                                           │
│                                                              │
│    Output Folder: Terminal1_Project/Output/                │
│                   Run_2025-11-11_v2.0/     [Browse...]     │
│                                                              │
│    ☑ Generate database (for comparison)                    │
│    ☑ Generate 8 IFC files (one per discipline)             │
│    ☑ Generate validation report (if reference exists)      │
│    ☐ Open in Blender 3D view after generation              │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│                  [Cancel]  [Generate Model]                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Progress Dialog

```
┌─────────────────────────────────────────────────────────────┐
│ Generating 8-Discipline Model...                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Using: terminal_experimental_v2.0 (120 templates)          │
│                                                              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68%                    │
│                                                              │
│ [✓] Parsed DWG files (35,412 entities)                     │
│ [✓] ARC: Generated 35,338 elements                         │
│ [✓] STR: Generated 1,429 elements                          │
│ [✓] FP: Generated 6,698 elements                           │
│ [⋯] ELEC: Generating... (1,147/1,189)                      │
│ [ ] ACMV: Pending...                                        │
│ [ ] SP: Pending...                                          │
│ [ ] CW: Pending...                                          │
│ [ ] LPG: Pending...                                         │
│                                                              │
│ Estimated time remaining: 45 seconds                        │
│                                                              │
│                          [Cancel]                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Completion Dialog

```
┌─────────────────────────────────────────────────────────────┐
│ Generation Complete! ✅                                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Output Location:                                             │
│ Terminal1_Project/Output/Run_2025-11-11_v2.0/              │
│                                                              │
│ Generated:                                                   │
│ ✓ Database: Generated_Terminal1.db (329 MB)                │
│ ✓ 8 IFC files (total: 98 MB)                               │
│                                                              │
│ Statistics:                                                  │
│ └─ Total elements: 48,942 (across 8 disciplines)           │
│                                                              │
│ Validation (vs. reference database):                        │
│ └─ Overall accuracy: 94.7% ✅                               │
│    [View Detailed Report]                                   │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ [Open Output Folder]  [Open in Blender]  [Close]           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

**Simplicity:**
- Just 3 steps: Select folder, choose template set, click generate
- No template editing (use Template Studio for that)
- Auto-discovery of DWGs and template sets

**Flexibility:**
- Multiple template sets to choose from
- Timestamped output (never overwrite)
- Optional validation (if reference DB exists)

**Integration:**
- Works within existing Bonsai workflow
- Results visible in Blender Outliner
- Standard IFC export

### Technology Stack

```python
# Framework
Blender Addon API  # bpy module

# Template Loading
sqlite3            # Read template_library.db

# DWG Parsing
ezdxf              # Python DWG/DXF parser
# OR
ifcopenshell       # IFC-based DWG parser

# IFC Generation
ifcopenshell       # Create IFC elements

# Database Writing
sqlite3            # Same schema as extraction DB
```

---

## Template Set Architecture

### Template Library Database Schema

```sql
-- template_library.db

-- Element Templates
CREATE TABLE element_templates (
    template_id TEXT PRIMARY KEY,
    template_name TEXT NOT NULL,
    version TEXT NOT NULL,
    category TEXT NOT NULL,         -- Seating, Fire, ACMV, etc.
    subcategory TEXT,
    ifc_class TEXT NOT NULL,
    description TEXT,
    confidence_score REAL,
    usage_count INTEGER DEFAULT 0,
    created_date TEXT,
    modified_date TEXT,
    extracted_from TEXT,            -- Source project
    status TEXT DEFAULT 'active'    -- active, deprecated, experimental
);

-- Template Parameters
CREATE TABLE template_parameters (
    param_id TEXT PRIMARY KEY,
    template_id TEXT REFERENCES element_templates(template_id),
    param_name TEXT NOT NULL,
    param_type TEXT NOT NULL,       -- integer, float, enum, boolean
    param_category TEXT NOT NULL,   -- fixed, flexible, derived
    default_value TEXT,
    min_value REAL,
    max_value REAL,
    enum_options TEXT,              -- JSON array for enum types
    unit TEXT,                      -- meters, degrees, etc.
    editable BOOLEAN,
    description TEXT,
    affects TEXT,                   -- JSON array of dependent params
    validation_rule TEXT            -- SQL or Python expression
);

-- Derivation Rules
CREATE TABLE derivation_rules (
    rule_id TEXT PRIMARY KEY,
    template_id TEXT REFERENCES element_templates(template_id),
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL,        -- formula, conditional, spatial
    trigger_condition TEXT,         -- When to apply this rule
    formula TEXT,                   -- Calculation formula
    priority INTEGER,               -- Rule execution order
    description TEXT
);

-- Spatial Patterns
CREATE TABLE spatial_patterns (
    pattern_id TEXT PRIMARY KEY,
    template_id TEXT REFERENCES element_templates(template_id),
    pattern_type TEXT NOT NULL,     -- grid, array, scattered, linear
    layout_strategy TEXT,           -- rectangular, circular, adaptive
    spacing_rules TEXT,             -- JSON object
    orientation_rules TEXT,         -- JSON object
    clearance_requirements TEXT,    -- JSON object
    code_references TEXT            -- JSON array
);

-- Code Requirements
CREATE TABLE code_requirements (
    requirement_id TEXT PRIMARY KEY,
    template_id TEXT REFERENCES element_templates(template_id),
    code_name TEXT NOT NULL,        -- Building Code, Fire Code, etc.
    section_reference TEXT,
    requirement_type TEXT,          -- minimum, maximum, exact
    parameter_name TEXT,
    value REAL,
    unit TEXT,
    mandatory BOOLEAN,
    description TEXT
);

-- Material Specifications
CREATE TABLE material_specifications (
    spec_id TEXT PRIMARY KEY,
    template_id TEXT REFERENCES element_templates(template_id),
    material_name TEXT,
    finish TEXT,
    cost_per_unit REAL,
    install_time_hours REAL,
    weight_kg REAL,
    fire_rating TEXT,
    properties TEXT                 -- JSON object
);

-- Adaptation Rules
CREATE TABLE adaptation_rules (
    adaptation_id TEXT PRIMARY KEY,
    template_id TEXT REFERENCES element_templates(template_id),
    condition TEXT NOT NULL,        -- When to adapt
    action TEXT NOT NULL,           -- What to do
    parameters TEXT,                -- JSON object
    priority INTEGER,
    description TEXT
);

-- Validation History
CREATE TABLE validation_history (
    validation_id TEXT PRIMARY KEY,
    template_id TEXT REFERENCES element_templates(template_id),
    validation_date TEXT,
    test_scenario TEXT,
    accuracy_pct REAL,
    spatial_delta_avg REAL,
    spatial_delta_max REAL,
    element_count_match REAL,
    notes TEXT
);

-- Usage Statistics
CREATE TABLE usage_statistics (
    usage_id TEXT PRIMARY KEY,
    template_id TEXT REFERENCES element_templates(template_id),
    project_name TEXT,
    usage_date TEXT,
    elements_generated INTEGER,
    user_adjustments INTEGER,       -- How many manual edits needed
    success_rating INTEGER          -- 1-5 stars
);
```

### Template Metadata (metadata.json)

```json
{
  "template_set_name": "terminal_experimental_v2.0",
  "version": "2.0.0",
  "created_date": "2025-11-11",
  "author": "BIM Team",
  "description": "Experimental template set with edge case handling",

  "source": {
    "extracted_from": "Terminal 1 (Singapore Airport)",
    "reference_database": "FullExtractionTesellated.db",
    "extraction_date": "2025-11-05"
  },

  "statistics": {
    "total_templates": 120,
    "by_category": {
      "Seating": 15,
      "Fire_Protection": 12,
      "Electrical": 18,
      "ACMV": 22,
      "Plumbing": 14,
      "Structure": 8,
      "Chilled_Water": 16,
      "LPG": 15
    }
  },

  "validation": {
    "tested_on": "Terminal 1 DWGs (blind test)",
    "accuracy": {
      "element_count": "94.7%",
      "spatial_position": "0.18m avg delta",
      "property_match": "96.2%"
    },
    "test_date": "2025-11-11"
  },

  "compatibility": {
    "bonsai_addon_version": ">=1.0.0",
    "ifc_version": "IFC4",
    "region": "Singapore",
    "building_codes": [
      "Singapore Building Code 2019",
      "SCDF Fire Code 2018"
    ]
  },

  "changelog": {
    "v2.0.0": [
      "Added variance handling for empty halls (row_count=0)",
      "Improved duct routing around beam intersections",
      "Added 15 new LPG templates",
      "Fixed sprinkler coverage for high ceilings",
      "Enhanced seating templates with 3 density modes"
    ],
    "v1.5.0": [
      "Improved FP templates",
      "Fixed aisle width calculations",
      "Added 10 ACMV duct templates"
    ],
    "v1.0.0": [
      "Initial baseline extraction (90 templates)"
    ]
  },

  "notes": [
    "Experimental set - use v1.5 for production",
    "Edge case handling may produce unexpected results",
    "LPG templates need more validation"
  ]
}
```

### Example Template Record

```json
{
  "template_id": "seating_gate_8x15_v2",
  "template_name": "Gate_Seating_8x15",
  "version": "2.1",
  "category": "Seating",
  "subcategory": "Gate_Waiting",
  "ifc_class": "IfcFurnishingElement",
  "description": "Standard gate waiting area seating (120 seats)",

  "parameters": {
    "fixed": [
      {
        "name": "min_aisle_width",
        "value": 1.0,
        "unit": "meters",
        "reason": "Building Code Section 4.2.1 (accessibility)"
      },
      {
        "name": "min_front_clearance",
        "value": 0.9,
        "unit": "meters",
        "reason": "Accessibility code requirement"
      }
    ],

    "flexible": [
      {
        "name": "row_count",
        "type": "integer",
        "min": 0,
        "max": 20,
        "default": 8,
        "editable": true,
        "description": "Number of rows (0 = empty hall, skip template)"
      },
      {
        "name": "seats_per_row",
        "type": "integer",
        "min": 8,
        "max": 20,
        "default": 15,
        "editable": true,
        "affects": ["total_seats", "layout_width"]
      },
      {
        "name": "density_mode",
        "type": "enum",
        "options": ["comfort", "standard", "high_density"],
        "default": "standard",
        "editable": true,
        "affects": ["seat_spacing", "aisle_frequency"]
      },
      {
        "name": "orientation",
        "type": "enum",
        "options": ["face_gate", "face_north", "face_south", "auto"],
        "default": "auto",
        "editable": true
      }
    ],

    "derived": [
      {
        "name": "total_seats",
        "formula": "row_count * seats_per_row",
        "unit": "count"
      },
      {
        "name": "layout_width",
        "formula": "(seats_per_row * seat_width) + (aisles * aisle_width)",
        "unit": "meters"
      }
    ]
  },

  "spatial_pattern": {
    "pattern_type": "grid",
    "layout_strategy": "rectangular",
    "spacing": {
      "seat_width": 0.55,
      "seat_depth": 0.60,
      "between_seats": 0.05,
      "between_rows": 0.10,
      "aisle_frequency": 8,
      "aisle_width": 1.2
    },
    "clearances": {
      "front": 0.9,
      "back": 0.1,
      "side": 0.15
    }
  },

  "adaptation_rules": [
    {
      "condition": "room_area < required_area * 0.7",
      "action": "scale_down_rows",
      "parameters": {"scale_factor": 0.7}
    },
    {
      "condition": "row_count == 0",
      "action": "skip_template",
      "message": "Empty hall - no seating required"
    },
    {
      "condition": "room_shape == 'L-shaped'",
      "action": "split_into_zones",
      "parameters": {"strategy": "maximize_coverage"}
    }
  ],

  "code_requirements": [
    {
      "code": "Building Code 2019",
      "section": "4.2.1",
      "requirement": "min_aisle_width >= 1.0",
      "mandatory": true
    },
    {
      "code": "Accessibility Code",
      "requirement": "min_front_clearance >= 0.9",
      "mandatory": true
    }
  ],

  "material_spec": {
    "material": "Fire-rated fabric, steel frame",
    "finish": "Standard commercial grade",
    "cost_per_unit": 350,
    "install_time_hours": 0.5,
    "weight_kg": 25,
    "fire_rating": "B-s1,d0"
  },

  "validation": {
    "confidence_score": 0.98,
    "usage_count": 47,
    "extracted_from": "Terminal 1, Gate 12",
    "instance_count": 120,
    "last_validated": "2025-11-11",
    "accuracy": {
      "element_count": "100%",
      "spatial_delta": "0.05m avg",
      "property_match": "99%"
    }
  }
}
```

---

## Validation Methodology

### Database Comparison Strategy

```python
class DatabaseComparator:
    """
    Compare original (human-modeled) vs generated (addon-created)
    """

    def compare_databases(self, original_db, generated_db):
        """
        Multi-level comparison
        """
        results = {
            'element_counts': self.compare_element_counts(),
            'spatial_accuracy': self.compare_spatial_positions(),
            'property_accuracy': self.compare_properties(),
            'geometry_accuracy': self.compare_geometries(),
            'relationship_accuracy': self.compare_relationships()
        }
        return results
```

### Comparison Metrics

#### 1. Element Count Accuracy

```sql
-- Compare element counts by discipline
SELECT
    discipline,
    COUNT(*) as original_count,
    (SELECT COUNT(*)
     FROM generated.elements_meta
     WHERE discipline = original.discipline) as generated_count,
    ROUND(100.0 * generated_count / original_count, 1) as accuracy_pct,
    (generated_count - original_count) as delta
FROM original.elements_meta original
GROUP BY discipline
ORDER BY accuracy_pct DESC;
```

**Expected Output:**

```
Discipline  | Original | Generated | Accuracy | Delta
------------|----------|-----------|----------|-------
STR         | 1,429    | 1,429     | 100.0%   | 0
FP          | 6,880    | 6,698     | 97.4%    | -182
ARC         | 35,338   | 35,338    | 100.0%   | 0
ELEC        | 1,189    | 1,201     | 101.0%   | +12
ACMV        | 1,621    | 1,542     | 95.1%    | -79
SP          | 991      | 940       | 94.9%    | -51
CW          | 1,419    | 1,301     | 91.7%    | -118
LPG         | 198      | 167       | 84.3%    | -31
------------|----------|-----------|----------|-------
TOTAL       | 49,065   | 48,616    | 99.1%    | -449
```

#### 2. Spatial Accuracy

```python
def compare_spatial_positions(self, orig, gen):
    """
    Match elements by type/location, calculate position delta
    """

    # For each original element, find nearest generated element
    spatial_deltas = []

    for orig_elem in orig.elements:
        nearest_gen = find_nearest_element(orig_elem, gen.elements)

        if nearest_gen:
            delta_3d = calculate_distance_3d(
                (orig_elem.x, orig_elem.y, orig_elem.z),
                (nearest_gen.x, nearest_gen.y, nearest_gen.z)
            )

            spatial_deltas.append({
                'orig_guid': orig_elem.guid,
                'gen_guid': nearest_gen.guid,
                'delta_m': delta_3d,
                'within_tolerance': delta_3d < 0.5  # 500mm
            })

    return {
        'avg_delta': mean(spatial_deltas),
        'max_delta': max(spatial_deltas),
        'within_tolerance_pct': percent_within_tolerance(spatial_deltas)
    }
```

**Expected Output:**

```
Spatial Accuracy Report
-----------------------
Elements Matched: 48,616 / 49,065 (99.1%)

Position Delta:
  Average: 0.18m  ✅
  Median:  0.12m  ✅
  Max:     0.87m  ✅

Within Tolerance (<0.5m): 97.2%  ✅

By Discipline:
  ARC:  0.05m avg (seating, walls)  ✅
  STR:  0.02m avg (columns, beams)  ✅
  FP:   0.08m avg (sprinklers)      ✅
  ELEC: 0.15m avg (lighting)        ✅
  ACMV: 0.32m avg (ducts)           ⚠️
  SP:   0.21m avg (pipes)           ✅
```

#### 3. Property Accuracy

```python
def compare_properties(self, orig, gen):
    """
    Compare element properties (material, dimensions, classifications)
    """

    property_matches = []

    for orig_elem in orig.elements:
        gen_elem = find_matching_element(orig_elem, gen.elements)

        if gen_elem:
            property_matches.append({
                'material_match': orig_elem.material == gen_elem.material,
                'dimensions_match': dimensions_similar(orig_elem, gen_elem, tol=0.01),
                'classification_match': orig_elem.ifc_class == gen_elem.ifc_class,
                'object_type_match': orig_elem.object_type == gen_elem.object_type
            })

    return {
        'material_accuracy': percent_match('material_match'),
        'dimensions_accuracy': percent_match('dimensions_match'),
        'classification_accuracy': percent_match('classification_match')
    }
```

**Expected Output:**

```
Property Accuracy Report
------------------------
Material Match:       96.2%  ✅
Dimensions Match:     98.5%  ✅
Classification Match: 100.0% ✅
Object Type Match:    94.7%  ✅
```

#### 4. Validation Report (HTML)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Validation Report - Terminal 1 (v2.0)</title>
</head>
<body>
    <h1>Database Comparison Report</h1>
    <p><strong>Generated:</strong> 2025-11-11 14:32:15</p>
    <p><strong>Template Set:</strong> terminal_experimental_v2.0</p>

    <div class="summary">
        <h2>Overall Accuracy: 94.7% ✅</h2>
    </div>

    <div class="discipline-breakdown">
        <h2>Discipline Breakdown</h2>
        <table>
            <tr>
                <th>Discipline</th>
                <th>Original</th>
                <th>Generated</th>
                <th>Accuracy</th>
                <th>Status</th>
            </tr>
            <tr class="pass">
                <td>ARC</td>
                <td>35,338</td>
                <td>35,338</td>
                <td>100.0%</td>
                <td>✅</td>
            </tr>
            <!-- More rows... -->
        </table>
    </div>

    <div class="spatial-accuracy">
        <h2>Spatial Accuracy</h2>
        <p>Average Delta: 0.18m ✅</p>
        <p>Within Tolerance: 97.2% ✅</p>
        <canvas id="spatial-histogram"></canvas>
    </div>

    <div class="missing-elements">
        <h2>Missing Elements (449 total)</h2>
        <ul>
            <li>ACMV: 79 duct fittings (complex elbows at beams)</li>
            <li>CW: 118 pipe segments (routing not templated)</li>
            <li>LPG: 31 elements (insufficient templates)</li>
        </ul>
        <p><strong>Recommendation:</strong> Add templates for duct fittings and LPG routing</p>
    </div>

    <div class="verdict">
        <h2>Verdict</h2>
        <p class="pass">✅ PASS - Template set achieves 94.7% accuracy</p>
        <p>Ready for production use on similar projects (Terminal 2/3/4)</p>
    </div>
</body>
</html>
```

---

## Success Criteria

### Quantitative Thresholds

```python
SUCCESS_CRITERIA = {
    # Element Count Accuracy
    'element_count_accuracy': {
        'excellent': 95,   # 95%+ = Excellent
        'good': 90,        # 90-95% = Good
        'acceptable': 85,  # 85-90% = Acceptable
        'needs_work': 70,  # 70-85% = Needs work
        'fail': 0          # <70% = Fail
    },

    # Spatial Accuracy
    'spatial_accuracy': {
        'excellent': 0.10,  # <10cm avg delta = Excellent
        'good': 0.20,       # <20cm = Good
        'acceptable': 0.50, # <50cm = Acceptable
        'needs_work': 1.00, # <1m = Needs work
        'fail': float('inf') # >1m = Fail
    },

    # Critical Disciplines (must work)
    'critical_disciplines': {
        'required': ['STR', 'FP', 'ARC'],
        'min_accuracy': 90  # 90% minimum
    },

    # Optional Disciplines (can be lower)
    'optional_disciplines': {
        'disciplines': ['LPG', 'SP', 'CW'],
        'min_accuracy': 70  # 70% acceptable
    },

    # Property Accuracy
    'property_accuracy': {
        'ifc_class_match': 100,     # Must be 100%
        'material_match': 95,       # 95%+ acceptable
        'dimensions_match': 95      # 95%+ acceptable
    }
}
```

### POC Success Definition

**✅ POC PASSES if:**
- Overall element count accuracy ≥ 90%
- Critical disciplines (STR, FP, ARC) ≥ 90% accuracy
- Spatial position delta < 0.5m for 95% of elements
- IFC class accuracy = 100%
- Property accuracy ≥ 95%

**⚠️ NEEDS WORK if:**
- Overall accuracy 70-90%
- Spatial delta 0.5-1.0m (usable but needs refinement)
- Some optional disciplines missing

**❌ POC FAILS if:**
- Overall accuracy < 70%
- Spatial delta > 1.0m (unusable)
- Critical disciplines missing or < 70% accuracy

---

## Implementation Roadmap

### Phase 1: Template Extraction (Week 1-2)

**Goal:** Extract baseline templates from Terminal 1 database

```
Day 1-3: Database Analysis
├─ Query FullExtractionTesellated.db
├─ Identify patterns (seating grids, sprinkler spacing, etc.)
├─ Detect variants (3 seating types, 2 sprinkler types)
└─ Document findings

Day 4-7: Template Extraction
├─ Write extraction scripts (Python + SQL)
├─ Extract 90+ templates
├─ Package as terminal_base_v1.0/
└─ Create metadata.json

Day 8-10: Validation Setup
├─ Create database comparison scripts
├─ Define metrics (count, spatial, property)
├─ Build validation report generator
└─ Test on sample data
```

**Deliverables:**
- `terminal_base_v1.0/template_library.db` (90 templates)
- Extraction scripts (reusable)
- Validation framework

---

### Phase 2: Bonsai Integration (Week 3-4)

**Goal:** Build addon to use templates

```
Day 11-14: UI Development
├─ Create folder picker dialog
├─ Template set selector
├─ Progress bar
└─ Completion report

Day 15-18: Core Logic
├─ DWG parser (ezdxf)
├─ Template matcher (fuzzy matching)
├─ IFC generator (ifcopenshell)
└─ Database writer (sqlite3)

Day 19-20: Testing
├─ Run on Terminal 1 DWGs
├─ Generate database
├─ Compare with original
└─ Document results
```

**Deliverables:**
- Bonsai addon (basic version)
- Generated_Terminal1.db
- Validation report (v1.0 accuracy)

---

### Phase 3: Template Refinement (Week 5-6)

**Goal:** Improve accuracy to 90%+

```
Day 21-24: Template Studio
├─ Build parameter editor UI
├─ Template tester
├─ Validation dashboard
└─ Export functionality

Day 25-28: Refinement
├─ Analyze v1.0 failures
├─ Adjust parameters
├─ Add missing templates
├─ Create terminal_refined_v1.5/

Day 29-30: Re-validation
├─ Run with v1.5 templates
├─ Compare: v1.0 vs v1.5
├─ Document improvements
└─ Iterate if needed
```

**Deliverables:**
- Template Studio (prototype)
- `terminal_refined_v1.5/` (105 templates)
- Comparison report (v1.0: 85% → v1.5: 92%)

---

### Phase 4: Production Ready (Week 7-8)

**Goal:** Achieve 95% accuracy, prepare demo

```
Day 31-35: Final Refinement
├─ Edge case handling
├─ Variance adaptations
├─ Create terminal_experimental_v2.0/
└─ Final validation run

Day 36-38: Documentation
├─ User guide (Bonsai addon)
├─ Template curator guide (Template Studio)
├─ Technical specs
└─ Demo script

Day 39-40: Demo Preparation
├─ Polish UI
├─ Prepare presentation
├─ Test run through
└─ Q&A preparation
```

**Deliverables:**
- `terminal_experimental_v2.0/` (120 templates, 95% accuracy)
- Complete documentation
- Demo-ready system
- Production deployment plan

---

## User Workflows

### Workflow 1: Template Curator (Template Studio)

**Goal:** Extract and refine templates

```
1. Launch Template Studio
   └─ Open existing library OR create new

2. Extract Templates from Database
   ├─ Select: FullExtractionTesellated.db
   ├─ Choose discipline: FP (Fire Protection)
   ├─ Run pattern detection
   └─ Review: 12 templates found

3. Edit Template Parameters
   ├─ Select: Sprinkler_Grid_7.5m
   ├─ Adjust: coverage_radius (7.5m → 9.0m for high ceilings)
   ├─ Add: ceiling_height_threshold parameter
   └─ Save changes

4. Test Template
   ├─ Create mock room: 15m × 20m, 4.5m ceiling
   ├─ Apply template
   ├─ Verify: 24 sprinklers placed correctly
   └─ Check: Code compliance (all passed)

5. Validate Against Reference
   ├─ Load: Terminal 1 database (ground truth)
   ├─ Generate: Using updated template
   ├─ Compare: Original vs Generated
   └─ Result: 97.4% accuracy (improved from 95%)

6. Export Template Set
   ├─ Name: terminal_refined_v1.5
   ├─ Version: 1.5.0
   ├─ Add changelog notes
   └─ Export to: Terminal1_Project/Templates/
```

---

### Workflow 2: Project Team (Bonsai Addon)

**Goal:** Generate 3D model from DWGs

```
1. Prepare Project Folder
   ├─ Create: Terminal2_Project/
   ├─ Add DWGs: Terminal2_Project/DWG/
   └─ Copy templates: Terminal2_Project/Templates/

2. Open Bonsai in Blender
   └─ Menu: Federation → Import DWG Project

3. Select Project
   ├─ Browse: Terminal2_Project/
   ├─ System detects: 2 ARC DWGs, 20 STR DWGs
   └─ System finds: 2 template sets available

4. Choose Template Set
   ├─ View details of each set
   ├─ Select: singapore_airport_standard (proven)
   └─ Confirm selection

5. Configure Output
   ├─ Output folder: Auto-generated timestamp
   ├─ Enable: Database generation
   ├─ Enable: Validation report
   └─ Enable: IFC export

6. Generate Model
   ├─ Click: Generate Model
   ├─ Wait: 2-5 minutes (progress bar)
   └─ Complete: 8 disciplines generated

7. Review Results
   ├─ Open: validation_report.html (94% accuracy)
   ├─ View: Blender 3D view (all disciplines)
   ├─ Check: Outliner (organized collections)
   └─ Verify: No critical clashes

8. Manual Adjustments (if needed)
   ├─ Select: Gate 5 Seating collection
   ├─ Move: +2m north (fit space better)
   ├─ Delete: 3 sprinklers (redundant)
   └─ Save changes

9. Export Final IFCs
   ├─ Menu: Export → IFC by Discipline
   ├─ Generated: 8 IFC files
   └─ Deliver: To client/team
```

---

## Technical Specifications

### System Requirements

**Template Studio:**
```
OS: Windows 10+, macOS 11+, Linux (Ubuntu 20.04+)
Python: 3.9+
RAM: 4GB minimum, 8GB recommended
Storage: 10GB (for large databases)
Dependencies:
  - PyQt6 or Streamlit
  - Pandas, NumPy
  - Matplotlib, Plotly
  - SQLite3
```

**Bonsai Addon:**
```
Blender: 3.6+
IfcOpenShell: Latest
Python: 3.11 (Blender's Python)
RAM: 8GB minimum, 16GB recommended
Storage: 5GB (for large projects)
Dependencies:
  - ezdxf (DWG parsing)
  - ifcopenshell (IFC generation)
  - sqlite3 (database handling)
```

---

### File Size Estimates

```
Template Library: 5-10 MB (120 templates)
DWG Files: 10-100 MB (varies by project)
Generated Database: 300-500 MB (50K elements)
IFC Files: 100-200 MB total (8 disciplines)
Validation Reports: 1-5 MB (HTML + charts)
```

---

### Performance Targets

```
Template Extraction: 10-30 minutes (one-time)
Database Comparison: 1-5 minutes (validation)
DWG Parsing: 30-120 seconds (depends on file size)
Model Generation: 2-5 minutes (50K elements)
IFC Export: 30-90 seconds (all disciplines)
```

---

## Conclusion

### Key Achievements

This POC methodology provides:

1. **Objective Validation:** Quantitative metrics (90%+ accuracy)
2. **Iterative Refinement:** v1.0 → v1.5 → v2.0 progression
3. **Production Readiness:** Proven templates reusable on new projects
4. **User Control:** Templates editable, not black-box AI
5. **Scalability:** Template library grows with each project

### Success Indicators

**If we achieve:**
- 95% element count accuracy
- <0.2m average spatial delta
- 100% IFC class match
- <5% manual adjustments needed

**Then we can claim:**
- Template-driven approach validated ✅
- Ready for Terminal 2/3/4 production use ✅
- Significant time/cost savings (6 months → 2 weeks) ✅
- Industry-first methodology ✅

---

**Document Version:** 1.0
**Status:** Complete - Ready for Implementation
**Next Step:** Begin Phase 1 (Template Extraction)

---

**Questions? Contact BIM Team**
