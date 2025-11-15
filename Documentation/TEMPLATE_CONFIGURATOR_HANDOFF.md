# Template Configurator - Implementation Guide

**Date:** November 12, 2025
**Status:** ✅ Ready for implementation in parallel with DXF waiting
**Purpose:** Digitize consultant's auxiliary documents (Excel/PDF notes) into machine-readable rules

---

## Executive Summary: What This Tool Really Does

### The Problem

In real-world BIM projects, consultants provide:
```
📄 2D DWG files (geometry only - walls, beams, pipes)
📋 Design Intent Notes PDF ("Hall A is a waiting area")
📊 Space Program Excel (furniture schedules, seating density)
📊 MEP Equipment Schedule (sprinkler spacing, lighting standards)
```

**Manual BIM modelers** read all these documents and interpret them into 3D Revit models.
**Bonsai automated conversion** needs this intelligence in machine-readable format.

### The Solution

**Template Configurator** = Digital replacement for PDF notes + Excel schedules

```
Traditional Workflow:
  DWG + PDF notes + Excel schedules → Human reads → Manual Revit modeling
                    ↑ Slow, error-prone

Bonsai Workflow:
  DWG + Template Configurator JSON → Automated conversion → IFC output
                    ↑ Fast, consistent
```

### What Users Do

**Two modes depending on what they have:**

**Mode 1: "I have auxiliary documents"** (Excel/PDF)
- Upload DWG + Excel space program + PDF notes
- Configurator parses them automatically
- User reviews and approves
- Export configuration JSON

**Mode 2: "I only have DWG"** (no auxiliary docs)
- Upload DWG only
- Visual canvas shows detected spaces
- User paints functional purpose (drag-and-drop icons)
- User configures defaults (ceiling type, MEP rules)
- Export configuration JSON

**Result:** JSON configuration file → Used by `dxf_to_database.py` for conversion

---

## The Core Insight: Strategic Placement, Not Exact Placement

### Traditional 3D Modeling (What We're NOT Doing):
```
User places every single chair, light, sprinkler manually
  🪑🪑🪑🪑🪑  ← 50 clicks for 50 chairs
  💡💡💡💡💡  ← 30 clicks for 30 lights

Takes: 6 months, 3-5 modelers, $200K
```

### Template Configurator (Strategic Markers):
```
User drops ONE marker to indicate intent:
  "This area = Waiting Area" → 🪑 (drops bench icon)

System infers pattern:
  Building type: Transportation Hub
  Space type: Waiting Area
  Template: Terminal_Waiting_Bench
  Density: 1.5 m²/seat
  Auto-generate: 🪑🪑🪑🪑🪑 (50 benches in pattern)
  Auto-add: 💡💡💡💡💡 (lights per code)
  Auto-add: 🚿🚿🚿🚿🚿 (sprinklers per NFPA)

Takes: 15 minutes, 1 click, automated
```

**Key:** User indicates INTENT ("this is for waiting"), system fills DETAILS (exact placement, spacing, codes)

---

## 3-Tab Hybrid UI Design

### Tab 1: Import & Detect (Automated)

**Purpose:** Ingest DWG and optional auxiliary documents

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: Upload Files                                    │
│                                                          │
│ Primary Input (Required):                               │
│ ┌────────────────────────────────────────────────┐      │
│ │ [📁 Select DWG/DXF File]                       │      │
│ │ Selected: Terminal_1.dwg (14 MB)               │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ Auxiliary Documents (Optional - Auto-Parse):            │
│ ┌────────────────────────────────────────────────┐      │
│ │ [📊 Space Program Excel] (furniture schedules) │      │
│ │ Selected: T1_Space_Program.xlsx                │      │
│ │                                                 │      │
│ │ [📋 Design Notes PDF] (functional purposes)    │      │
│ │ Selected: T1_Design_Intent.pdf                 │      │
│ │                                                 │      │
│ │ [📊 MEP Equipment Schedule]                    │      │
│ │ Selected: T1_MEP_Schedule.xlsx                 │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ [Parse & Analyze ➜]                                     │
└─────────────────────────────────────────────────────────┘

After parsing:

┌─────────────────────────────────────────────────────────┐
│ Step 2: Detection Summary                               │
│                                                          │
│ DWG Analysis:                                           │
│ ✅ 35,338 ARC elements (walls, doors, seating blocks)  │
│ ✅ 1,429 STR elements (beams, columns)                 │
│ ✅ 6,880 FP elements (sprinkler symbols, pipes)        │
│ ✅ 1,172 ELEC elements (light fixtures, outlets)       │
│ ⚠️  247 ambiguous elements (need user input)            │
│                                                          │
│ From Excel Space Program:                               │
│ ✅ Hall A: Waiting Area (1,200 m², 800 seats)          │
│ ✅ Hall B: Retail (350 m², 15 shops)                   │
│ ✅ Toilets: 12 locations (male/female/accessible)      │
│                                                          │
│ From Design Notes PDF:                                  │
│ ✅ Ceiling: Acoustic tiles 600x600mm @ 18.5m height    │
│ ✅ Lighting: 500 lux, 4m spacing                       │
│ ✅ Fire protection: NFPA sprinklers, 3m spacing        │
│                                                          │
│ Detected Empty Spaces (need configuration):             │
│ ⚠️  Hall C (2,400 m²) - Purpose unknown                 │
│ ⚠️  East Wing (800 m²) - Purpose unknown                │
│                                                          │
│ [Next: Configure Spaces ➜]                              │
└─────────────────────────────────────────────────────────┘
```

**What Happens:**
1. Parse DWG layers → Detect disciplines, element types
2. Parse Excel (if provided) → Extract room types, furniture counts, dimensions
3. Parse PDF (if provided) → NLP extract keywords ("waiting area", "restaurant", ceiling types)
4. Show user what was detected
5. Highlight gaps (empty spaces, ambiguous elements)

---

### Tab 2: Configure Spaces (Visual Drag-and-Drop) ⭐

**Purpose:** User paints functional purpose onto detected spaces

```
┌─────────────────────────────────────────────────────────────────┐
│ Space Configuration (2D Visual Canvas)                          │
│                                                                  │
│ ┌──────────────┐  ┌─────────────────────────────────────────┐  │
│ │ Toolbox:     │  │ DWG Preview (Top-Down 2D)               │  │
│ │              │  │                                         │  │
│ │ 🪑 Waiting   │  │  ╔══════════╗ ╔════════════════╗       │  │
│ │    Area      │  │  ║ Hall A   ║ ║ Hall C         ║       │  │
│ │              │  │  ║ (Parsed  ║ ║ [Empty Space]  ║       │  │
│ │ 🍽️ Restaurant│  │  ║ from     ║ ║ 2,400 m²       ║       │  │
│ │              │  │  ║ Excel)   ║ ║                ║       │  │
│ │ 🏢 Office    │  │  ║          ║ ║ ← Drop icon    ║       │  │
│ │    Space     │  │  ║ 🪑🪑🪑   ║ ║   here to      ║       │  │
│ │              │  │  ║ 🪑🪑🪑   ║ ║   assign       ║       │  │
│ │ 🎮 Games     │  │  ╚══════════╝ ╚════════════════╝       │  │
│ │    Court     │  │                                         │  │
│ │              │  │  ╔════╗ ╔════╗ ╔════╗                  │  │
│ │ 🏪 Retail    │  │  ║ WC ║ ║ WC ║ ║ WC ║ Toilets (Auto)  │  │
│ │              │  │  ╚════╝ ╚════╝ ╚════╝                  │  │
│ │ 🚽 Toilet    │  │                                         │  │
│ │              │  │  ╔═══════════════════════════════════╗ │  │
│ │ 🏭 Warehouse │  │  ║ East Wing [Empty] 800 m²          ║ │  │
│ │              │  │  ║                                   ║ │  │
│ │ 🅿️ Parking   │  │  ╚═══════════════════════════════════╝ │  │
│ │              │  │                                         │  │
│ └──────────────┘  └─────────────────────────────────────────┘  │
│                                                                  │
│ Instructions:                                                    │
│ 1. Drag icons from toolbox to empty spaces                      │
│ 2. OR: Click space → Select purpose from dropdown               │
│ 3. Green = Auto-parsed from Excel/PDF                           │
│ 4. Yellow = Needs user input                                    │
│ 5. Click configured space to edit parameters                    │
│                                                                  │
│ [← Back] [Save Draft] [Next: Configure Defaults ➜]             │
└─────────────────────────────────────────────────────────────────┘

After user drops 🍽️ Restaurant icon on Hall C:

┌─────────────────────────────────────────────────────────┐
│ Hall C Configuration                                     │
│                                                          │
│ Space Type: 🍽️ Restaurant                               │
│ Area: 2,400 m² (detected from DWG)                      │
│                                                          │
│ Furniture Template:                                      │
│   [▼ Restaurant - Fast Food]                            │
│       Restaurant - Fast Food (4-seat tables, high turn) │
│       Restaurant - Fine Dining (2-seat + 4-seat mix)    │
│       Restaurant - Cafeteria (long tables, benches)     │
│                                                          │
│ Auto-Generated Elements (Preview):                      │
│   ✅ Tables: 120 units (4-seat, 2.0m spacing)           │
│   ✅ Chairs: 480 units (around tables)                  │
│   ✅ Ceiling tiles: 6,666 units (0.6×0.6m)              │
│   ✅ Lights: 150 units (4m spacing, 500 lux)            │
│   ✅ Sprinklers: 267 units (3m spacing)                 │
│   ✅ HVAC diffusers: 60 units (6m spacing)              │
│   ✅ Grease exhaust (kitchen area): 4 units             │
│   ✅ Floor drains: 8 units (kitchen/bar)                │
│                                                          │
│ Confidence: 85% (Good - typical restaurant pattern)     │
│                                                          │
│ [Edit Advanced Parameters] [✓ Confirm] [✗ Cancel]       │
└─────────────────────────────────────────────────────────┘
```

**Key Features:**
- **Visual canvas** shows DWG outline (2D top-down)
- **Auto-parsed spaces** shown in green (from Excel/PDF)
- **Empty spaces** highlighted in yellow (need user input)
- **Drag-and-drop** functional purpose icons
- **One click** triggers full inference chain
- **Preview** shows what will be generated (transparency = user sees impact)

---

### Tab 3: Configure Defaults (Form-Based)

**Purpose:** Set global defaults and MEP standards

```
┌─────────────────────────────────────────────────────────┐
│ Global Configuration & Defaults                         │
│                                                          │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Building Type Selection                           │   │
│ │                                                    │   │
│ │ Primary Type: [▼ Transportation Hub]              │   │
│ │                                                    │   │
│ │ Sub-Types (Multi-Select):                         │   │
│ │   ☑ Airport Terminal                              │   │
│ │   ☐ Bus Terminal                                  │   │
│ │   ☐ Ferry Terminal                                │   │
│ │   ☐ Train Station                                 │   │
│ │                                                    │   │
│ │ Description:                                       │   │
│ │ Transportation hubs include waiting lobbies,      │   │
│ │ high-capacity toilets, retail spaces, and MEP     │   │
│ │ systems designed for high foot traffic.           │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Ceiling Configuration (Global Default)            │   │
│ │                                                    │   │
│ │ Type: [▼ Acoustic Tile 600×600mm]                 │   │
│ │       Acoustic Tile 600×600mm (typical)           │   │
│ │       Acoustic Tile 1200×600mm (large span)       │   │
│ │       Exposed Concrete (industrial)               │   │
│ │       Gypsum Board (office/retail)                │   │
│ │       No Ceiling (warehouse/court)                │   │
│ │                                                    │   │
│ │ Default Height: [18.5] meters (from DWG sections) │   │
│ │ Grid Spacing: [0.6] × [0.6] meters                │   │
│ │                                                    │   │
│ │ Override per space: ☑ Allow space-specific config │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ ┌───────────────────────────────────────────────────┐   │
│ │ MEP Standards & Inference Rules                   │   │
│ │                                                    │   │
│ │ Fire Protection:                                  │   │
│ │   Code: [▼ NFPA 13 - Light Hazard]                │   │
│ │   Sprinkler Spacing: [3.0] meters                 │   │
│ │   Coverage Radius: [7.5] meters                   │   │
│ │   Height Below Ceiling: [0.3] meters              │   │
│ │   Auto-route pipes: ☑ Enable                      │   │
│ │   Confidence: [95]% (Code-required)               │   │
│ │                                                    │   │
│ │ Electrical - Lighting:                            │   │
│ │   Target Illuminance: [500] lux (office/retail)   │   │
│ │   Fixture Spacing: [4.0] meters                   │   │
│ │   Type: [▼ Recessed LED 40W]                      │   │
│ │   Height: [18.0] meters (0.5m below ceiling)      │   │
│ │   Auto-route conduits: ☑ Enable                   │   │
│ │   Confidence: [90]% (Standard practice)           │   │
│ │                                                    │   │
│ │ ACMV - Air Distribution:                          │   │
│ │   Supply Diffuser Spacing: [6.0] meters           │   │
│ │   Return Grille Spacing: [8.0] meters             │   │
│ │   Duct Routing: ☑ Auto-route per structural grid │   │
│ │   Air Changes/Hour: [8] (transportation hub)      │   │
│ │   Confidence: [85]% (Typical for building type)   │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Seating Density Standards                         │   │
│ │                                                    │   │
│ │ Waiting Area:                                     │   │
│ │   Template: [▼ Terminal Padded Bench]             │   │
│ │   Density: [1.5] m²/seat                          │   │
│ │   Row Spacing: [2.0] meters (circulation)         │   │
│ │   Pattern: [▼ Rows facing center]                 │   │
│ │                                                    │   │
│ │ Office:                                           │   │
│ │   Template: [▼ Office Workstation]                │   │
│ │   Density: [6.0] m²/person (desk + circulation)   │   │
│ │                                                    │   │
│ │ Restaurant:                                       │   │
│ │   Template: [▼ 4-Seat Table]                      │   │
│ │   Density: [2.0] m²/seat                          │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Advanced Inference Options                        │   │
│ │                                                    │   │
│ │ Enable Intelligent Inference:                     │   │
│ │   ☑ Ceiling tiles (from room boundaries)          │   │
│ │   ☑ Floor finishes (from space type)              │   │
│ │   ☑ Sprinklers (code-required)                    │   │
│ │   ☑ Lighting (illuminance standards)              │   │
│ │   ☑ HVAC diffusers (air change rates)             │   │
│ │   ☑ MEP routing (shortest path + clearances)      │   │
│ │   ☐ Furniture (only if not in DWG)                │   │
│ │                                                    │   │
│ │ Minimum Confidence Threshold: [70]%               │   │
│ │   Elements below this → flagged for review        │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ [← Back] [Save Template] [Export Configuration ➜]      │
└─────────────────────────────────────────────────────────┘
```

**What This Tab Does:**
- Sets **global defaults** (ceiling type, MEP standards)
- Defines **building type** (Transportation Hub, Office, etc.)
- Configures **inference rules** (enable/disable, thresholds)
- Shows **confidence levels** (transparency for user)
- Allows **per-space overrides** (Hall C restaurant ≠ default)

---

## Output: Configuration JSON

After user completes all tabs, export configuration file:

```json
{
  "project": {
    "name": "Terminal_1_Conversion",
    "building_type": "Transportation Hub",
    "sub_types": ["Airport Terminal"],
    "created": "2025-11-12T10:30:00Z"
  },

  "global_defaults": {
    "ceiling": {
      "type": "Acoustic_Tile_600x600",
      "height": 18.5,
      "grid_spacing": [0.6, 0.6]
    },
    "mep_standards": {
      "fire_protection": {
        "code": "NFPA_13_Light_Hazard",
        "sprinkler_spacing": 3.0,
        "coverage_radius": 7.5,
        "height_below_ceiling": 0.3,
        "auto_route_pipes": true,
        "confidence": 0.95
      },
      "lighting": {
        "illuminance": 500,
        "spacing": 4.0,
        "type": "Recessed_LED_40W",
        "height": 18.0,
        "confidence": 0.90
      },
      "hvac": {
        "supply_spacing": 6.0,
        "return_spacing": 8.0,
        "air_changes_per_hour": 8,
        "confidence": 0.85
      }
    }
  },

  "spaces": [
    {
      "id": "Hall_A",
      "name": "Hall A - Waiting Area",
      "functional_type": "waiting_area",
      "area_m2": 1200,
      "source": "excel_space_program",
      "furniture": {
        "template": "Terminal_Padded_Bench",
        "density_m2_per_seat": 1.5,
        "total_seats": 800,
        "pattern": "rows_facing_center"
      },
      "overrides": null
    },
    {
      "id": "Hall_C",
      "name": "Hall C - Restaurant",
      "functional_type": "restaurant",
      "area_m2": 2400,
      "source": "user_configured",
      "furniture": {
        "template": "Restaurant_Fast_Food",
        "table_type": "4_Seat_Table",
        "density_m2_per_seat": 2.0,
        "total_seats": 480
      },
      "overrides": {
        "hvac": {
          "grease_exhaust": true,
          "supply_spacing": 4.0
        }
      },
      "confidence": 0.85
    },
    {
      "id": "Toilet_Block_1",
      "name": "Toilet Block 1",
      "functional_type": "toilet",
      "area_m2": 80,
      "source": "dwg_detected",
      "inference_chain": [
        "sprinklers_wet_area",
        "water_supply",
        "drainage_critical",
        "extract_fans",
        "waterproof_lighting",
        "ceramic_floor",
        "ceramic_walls"
      ],
      "confidence": 0.90
    }
  ],

  "inference_rules": {
    "enabled": [
      "ceiling_tiles",
      "floor_finishes",
      "sprinklers",
      "lighting",
      "hvac_diffusers",
      "mep_routing"
    ],
    "disabled": [
      "furniture_auto_add"
    ],
    "min_confidence_threshold": 0.70
  },

  "validation": {
    "total_spaces_configured": 15,
    "spaces_from_excel": 12,
    "spaces_from_user": 3,
    "average_confidence": 0.88,
    "elements_flagged_for_review": 247,
    "estimated_total_elements": 49059
  }
}
```

**This JSON is used by `dxf_to_database.py` during conversion!**

---

## Integration with Conversion Pipeline

### Without Template Configurator (Current State):
```bash
python dxf_to_database.py \
    --input Terminal_1.dxf \
    --output Generated_Terminal1.db \
    --templates terminal_base_v1.0/template_library.db

# Problems:
# - Doesn't know Hall C is a restaurant
# - Uses generic defaults (low accuracy)
# - Can't infer missing elements
# - Result: 70% accuracy (minimum POC success)
```

### With Template Configurator (Enhanced):
```bash
# Step 1: User configures via GUI → Exports config.json

# Step 2: Conversion uses config
python dxf_to_database.py \
    --input Terminal_1.dxf \
    --output Generated_Terminal1.db \
    --templates terminal_base_v1.0/template_library.db \
    --config Terminal_1_config.json  # ← From configurator!

# Benefits:
# ✅ Knows Hall C = restaurant (applies correct template)
# ✅ Uses user-specified MEP standards (code-compliant)
# ✅ Infers missing elements (ceiling, lights, sprinklers)
# ✅ Result: 90-95% accuracy (production-ready)
```

---

## Implementation Priority (Revised)

### Phase 1: Core GUI (Week 1) - START HERE

**Milestone:** Basic app launches, loads DWG, shows detected elements

**Tasks:**
1. **Setup project structure**
   ```
   RawDWG/TemplateConfigurator/
   ├── main.py                    # Entry point
   ├── requirements.txt           # PyQt5, ezdxf, sqlite3
   ├── ui/
   │   ├── main_window.py        # 3-tab interface
   │   ├── tab_import.py         # Tab 1: Import & Detect
   │   ├── tab_spaces.py         # Tab 2: Visual canvas (placeholder)
   │   └── tab_defaults.py       # Tab 3: Form-based config
   ├── models/
   │   ├── project.py            # Project data model
   │   ├── space.py              # Space configuration model
   │   └── config.py             # JSON export/import
   ├── parsers/
   │   ├── dwg_parser.py         # DXF parsing (reuse existing)
   │   ├── excel_parser.py       # Parse space program Excel
   │   └── pdf_parser.py         # Extract text from design notes
   └── database/
       └── template_db.py        # Connect to template_library.db
   ```

2. **Implement Tab 1: Import & Detect**
   - File upload dialogs (DWG + Excel + PDF)
   - Parse DWG layers → Show element counts
   - Parse Excel (if provided) → Extract space program
   - Parse PDF (basic keyword extraction)
   - Show detection summary

3. **Test with Terminal 1 data**
   ```bash
   cd /home/red1/Documents/bonsai/RawDWG/TemplateConfigurator
   python main.py

   # Load: ../Terminal_1.dwg
   # Load: (mock) Terminal_1_Space_Program.xlsx
   # Verify: Shows 35,338 ARC elements, etc.
   ```

**Success Criteria:**
- ✅ GUI launches without errors
- ✅ Loads DWG and shows layer summary
- ✅ Parses Excel and shows room types
- ✅ 3 tabs visible (Tab 2/3 can be placeholders)

---

### Phase 2: Visual Canvas (Week 2)

**Milestone:** User can drag-and-drop functional purpose onto spaces

**Tasks:**
1. **Implement Tab 2: Visual canvas**
   - 2D rendering of DWG outline (simplified)
   - Detect rectangular spaces (rooms/halls)
   - Show toolbox with functional purpose icons
   - Drag-and-drop icon → Assign purpose to space
   - Click space → Show configuration dialog

2. **Space configuration dialog**
   - Space type selector
   - Template picker (from template_library.db)
   - Preview of auto-generated elements
   - Save configuration

3. **Visual feedback**
   - Green = Auto-parsed from Excel
   - Yellow = Needs user input
   - Blue = User configured

**Success Criteria:**
- ✅ Canvas shows DWG outline
- ✅ User can drop icon on space
- ✅ Configuration dialog appears
- ✅ Shows preview of generated elements

---

### Phase 3: Defaults & Export (Week 2-3)

**Milestone:** User can configure defaults and export JSON

**Tasks:**
1. **Implement Tab 3: Form-based defaults**
   - Building type selector (10 types from BUILDING_TYPE_SELECTOR.md)
   - Ceiling configuration
   - MEP standards (sprinkler spacing, lighting, HVAC)
   - Seating density templates
   - Inference rule toggles

2. **JSON export**
   - Collect all configuration (tabs 1-3)
   - Generate configuration JSON
   - Save to file
   - Validate schema

3. **Integration test**
   - Export config.json
   - Run `dxf_to_database.py --config config.json`
   - Verify conversion uses config correctly

**Success Criteria:**
- ✅ All default parameters configurable
- ✅ Exports valid JSON
- ✅ Conversion script reads JSON successfully
- ✅ Generated database reflects user config

---

### Phase 4: Advanced Features (Week 3-4)

**Milestone:** Production-ready with all features

**Tasks:**
1. **Excel/PDF parsing intelligence**
   - NLP for PDF notes (keywords: "waiting", "restaurant")
   - Excel cell parsing (room schedules, furniture counts)
   - Auto-populate configuration from auxiliary docs

2. **Template management**
   - Browse templates from template_library.db
   - Edit template parameters
   - Create new templates
   - Import/export template sets

3. **Validation & error checking**
   - Warn if space has no configuration
   - Flag low-confidence inferences
   - Validate JSON before export
   - Show coverage % (configured vs total spaces)

4. **UI polish**
   - Icons for functional purposes
   - Tooltips and help text
   - Progress indicators
   - Error messages

**Success Criteria:**
- ✅ Auto-parse Excel/PDF and populate >80% automatically
- ✅ User only needs to configure 20% (empty spaces)
- ✅ Validation catches errors before export
- ✅ Professional UI (ready for stakeholder demo)

---

### Phase 5: Visual DXF Preview (Future - Week 4+)

**Milestone:** Full 2D rendering with real DXF geometry

**Tasks:**
1. **Advanced DXF rendering**
   - Render walls, doors, windows (not just outline)
   - Zoom/pan controls
   - Layer visibility toggles
   - Measure tool

2. **Drag-and-paint refinement**
   - Paint room purpose with brush tool
   - Drag furniture onto canvas (exact placement)
   - Visual inference preview (show generated elements)

3. **Real-time preview**
   - Toggle "Show Inferred Elements"
   - Display sprinklers, lights, ceiling tiles
   - Adjust and see updates immediately

**Success Criteria:**
- ✅ Full DXF geometry rendered
- ✅ User can visually verify configuration
- ✅ Real-time preview of inferred elements
- ✅ Matches professional CAD viewer quality

---

## Technology Stack

### Recommended:

```python
# Core GUI Framework
PyQt5           # Rich widgets, better visuals than Tkinter

# File Parsing
ezdxf           # DXF/DWG parsing (already using)
openpyxl        # Excel parsing (space programs)
PyPDF2          # PDF text extraction (design notes)

# Database
sqlite3         # Template library (built-in Python)

# Visualization (Phase 5)
matplotlib      # Charts, graphs
PyQt5.QtWidgets # Canvas for 2D rendering

# Data Handling
json            # Config export (built-in)
dataclasses     # Data models (built-in Python 3.7+)

# Testing
pytest          # Unit tests
```

### Installation:

```bash
cd /home/red1/Documents/bonsai/RawDWG/TemplateConfigurator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install PyQt5 ezdxf openpyxl PyPDF2 matplotlib pytest

# Save requirements
pip freeze > requirements.txt

# Run app
python main.py
```

---

## Testing Plan

### Test 1: Import Terminal 1 DWG
```bash
python main.py

# Actions:
1. Upload: ../2. BANGUNAN TERMINAL 1 .dwg
2. Verify: Shows element counts by discipline
3. Verify: Detects spaces (halls, toilets)

# Expected:
✅ 35,338 ARC elements
✅ 6,880 FP elements
✅ Detects 15+ spaces
```

### Test 2: Parse Mock Excel
```bash
# Create mock space program:
# Terminal_1_Space_Program.xlsx
# | Room ID | Name       | Area | Type          | Seats |
# |---------|------------|------|---------------|-------|
# | Hall_A  | Waiting    | 1200 | Waiting Area  | 800   |
# | Hall_B  | Retail     | 350  | Retail        | -     |

# Upload Excel in configurator
# Expected:
✅ Auto-populates Hall_A, Hall_B configuration
✅ Shows waiting area = 800 seats
```

### Test 3: Visual Configuration
```bash
# User actions:
1. Open Tab 2 (Visual Canvas)
2. See Hall_C as empty space (yellow)
3. Drag 🍽️ Restaurant icon onto Hall_C
4. Configure: Fast Food template
5. See preview: 120 tables, 480 chairs, etc.

# Expected:
✅ Hall_C turns blue (configured)
✅ Preview shows auto-generated elements
✅ Confidence score displayed
```

### Test 4: Export & Integration
```bash
# User actions:
1. Complete all tabs
2. Click "Export Configuration"
3. Save: Terminal_1_config.json

# Run conversion:
python ../dxf_to_database.py \
    --input Terminal_1.dxf \
    --output Generated_Terminal1.db \
    --config Terminal_1_config.json

# Verify:
✅ Conversion uses config correctly
✅ Hall_C has restaurant furniture
✅ MEP spacing matches user config
✅ Accuracy improves from 70% → 90%+
```

---

## Success Metrics

### MVP (Week 1-2):
- ✅ Launch GUI
- ✅ Load DWG and show summary
- ✅ Configure spaces (basic)
- ✅ Export JSON

### Full Features (Week 3-4):
- ✅ Auto-parse Excel/PDF (80%+ auto-populated)
- ✅ Visual drag-and-drop
- ✅ All 10 building types supported
- ✅ Inference rule editor
- ✅ Validation and error checking

### Production-Ready (Week 4+):
- ✅ Professional UI (stakeholder demo-ready)
- ✅ DXF visual preview
- ✅ Real-time inference preview
- ✅ Template management
- ✅ Import/export configurations

---

## Why Build This Now?

### Benefits of Parallel Development:

1. **No dependencies on DXF files** - Can start immediately
2. **User feedback early** - Refine UI before conversion testing
3. **Improves POC accuracy** - From 70% → 90%+ with user config
4. **Demonstrates adaptability** - Shows templates are flexible
5. **Reusable for production** - Will be needed for all future projects

### Risk Mitigation:

- ✅ Standalone app (easy to test, no integration dependencies)
- ✅ Clear scope (3-tab UI, well-defined)
- ✅ Incremental development (Phase 1 → 5)
- ✅ Real data available (Terminal 1 DWG, template_library.db)

---

## Quick Start for New Chat Session

### Copy-Paste This:

```
I want to build the Template Configurator app while waiting for DXF files.

Context:
- Location: /home/red1/Documents/bonsai/RawDWG/
- Read: TEMPLATE_CONFIGURATOR_HANDOFF.md (this document)
- Purpose: Digitize consultant's auxiliary documents (Excel/PDF) into machine-readable config

Let's start with Phase 1: Core GUI structure (Week 1)
- Create project structure (TemplateConfigurator/ directory)
- Implement Tab 1: Import & Detect
- Test with Terminal 1 DWG

Technology: Python 3.11 + PyQt5
References:
- DWG file: /home/red1/Documents/bonsai/RawDWG/2. BANGUNAN TERMINAL 1 .dwg
- Templates: /home/red1/Documents/bonsai/RawDWG/Terminal1_Project/Templates/terminal_base_v1.0/template_library.db
```

---

## Key Files to Reference

### Documentation:
1. **TEMPLATE_CONFIGURATOR_HANDOFF.md** - This document (implementation guide)
2. **BUILDING_TYPE_SELECTOR.md** - 10 building types with inference rules
3. **CONSULTANT_HANDOFF_WORKFLOW.md** - Real-world workflow context
4. **MAJOR_EXPECTATIONS_FRAMEWORK.md** - Critical accuracy pillars
5. **INTELLIGENT_INFERENCE_STRATEGY.md** - 5 inference categories

### Database:
- `Terminal1_Project/Templates/terminal_base_v1.0/template_library.db`
- Schema: `create_template_library_schema.sql`

### Python Scripts (Reference):
- `dwg_parser.py` - DXF parsing (reuse for Tab 1)
- `dxf_to_database.py` - Conversion script (integration target)
- `extract_templates.py` - Template extraction (reference for DB queries)

### Test Data:
- `2. BANGUNAN TERMINAL 1 .dwg` - Terminal 1 DWG file
- (Need to create) Mock Excel space program for testing

---

## Bottom Line

**What:** Template Configurator - Digitizes consultant notes into machine-readable config

**Why:** Bridges gap between 2D DWG (geometry) and 3D BIM (intelligence)

**When:** NOW - parallel with DXF waiting

**How:** 3-tab hybrid UI (Import → Visual Config → Form Defaults)

**Result:** JSON config → 70% accuracy becomes 90%+ accuracy

---

**Let's build this! 🚀**

---

**Last Updated:** November 12, 2025
**Status:** Ready to start implementation
**Priority:** High - Critical for POC success (70% → 90%+ accuracy)
