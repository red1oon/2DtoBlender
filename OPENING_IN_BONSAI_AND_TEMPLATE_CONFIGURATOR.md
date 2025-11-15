# Opening Database in Bonsai & Template Configurator Overview

**Date:** November 15, 2025
**Status:** Database ready to open | Template Configurator exists but needs update

---

## 📂 Part 1: Opening Your Generated Database in Bonsai Blender

### What We Just Created

**File:** `/home/red1/Documents/bonsai/2Dto3D/Generated_Terminal1_SAMPLE.db`
**Size:** 5.0 MB
**Elements:** 15,257 IFC elements
**Disciplines:** 7 (Architecture, Fire Protection, Structure, ACMV, Electrical, Plumbing, LPG)

### Database Schema (Bonsai-Compatible)

```sql
✅ elements_meta          -- Element metadata (GUID, discipline, IFC class)
✅ element_transforms     -- 3D positions (x, y, z coordinates)

⚠️ Missing for full Bonsai integration:
   - base_geometries      -- 3D geometry (shapes)
   - element_properties   -- IFC properties
   - spatial_structure    -- Building/storey hierarchy
```

**Current Status:** Metadata-only (no 3D geometry yet)

### How to Open in Bonsai Blender

#### Option 1: Direct Database Load (If Federation Module Supports)

```bash
# Launch Blender with Bonsai
~/blender-4.2.14/blender

# In Blender:
# 1. Bonsai menu → Federation → Load Database
# 2. Browse to: /home/red1/Documents/bonsai/2Dto3D/Generated_Terminal1_SAMPLE.db
# 3. Elements should appear grouped by discipline in Outliner
```

#### Option 2: Via Federation Module (Current Method)

```python
# In Blender Python console:
import bpy
import sqlite3

# Load federation tool
from bonsai.tool import federation as federation_tool

# Connect to database
db_path = "/home/red1/Documents/bonsai/2Dto3D/Generated_Terminal1_SAMPLE.db"
conn = sqlite3.connect(db_path)

# Query elements
cursor = conn.cursor()
cursor.execute("SELECT discipline, ifc_class, COUNT(*) FROM elements_meta GROUP BY discipline, ifc_class")
results = cursor.fetchall()

for disc, ifc_class, count in results:
    print(f"{disc}: {ifc_class} ({count} elements)")
```

### What You'll See in Outliner

```
Outliner (grouped by discipline):
├── 🏗️ Seating (Architecture) - 11,604 elements
│   ├── IfcBuildingElementProxy (11,429)
│   ├── IfcWall (82)
│   ├── IfcWindow (76)
│   └── IfcDoor (17)
│
├── 🔥 Fire Protection - 2,063 elements
│   ├── IfcBuildingElementProxy (1,881)
│   ├── IfcPipeSegment (182)
│
├── 🏛️ Structure - 634 elements
│   ├── IfcColumn (634)
│
├── ❄️ ACMV - 544 elements
│   └── IfcBuildingElementProxy (544)
│
├── ⚡ Electrical - 338 elements
│   └── IfcBuildingElementProxy (338)
│
├── 🚰 Plumbing - 54 elements
│   └── IfcPipeSegment (54)
│
└── 🔥 LPG - 20 elements
    └── IfcPipeSegment (20)
```

**Note:** Currently all show as "ElementProxy" because we don't have 3D geometry yet, just metadata positions.

### Next Steps to Make it Fully Viewable

**Add Missing Components:**

1. **Base Geometries** (3D shapes)
   ```sql
   CREATE TABLE base_geometries (
       id INTEGER PRIMARY KEY,
       guid TEXT,
       geometry_blob BLOB,  -- Tessellated mesh data
       bbox_min_x, bbox_min_y, bbox_min_z REAL,
       bbox_max_x, bbox_max_y, bbox_max_z REAL
   );
   ```

2. **Spatial Structure** (Building hierarchy)
   ```sql
   CREATE TABLE spatial_structure (
       id INTEGER PRIMARY KEY,
       guid TEXT,
       parent_guid TEXT,
       name TEXT,
       storey TEXT,
       elevation REAL
   );
   ```

3. **Element Properties** (IFC attributes)
   ```sql
   CREATE TABLE element_properties (
       id INTEGER PRIMARY KEY,
       guid TEXT,
       pset_name TEXT,
       property_name TEXT,
       property_value TEXT
   );
   ```

**Implementation:**
```python
# In dxf_to_database.py, add after populate_database():

def add_simple_geometries(self):
    """Add placeholder box geometries for visualization."""
    conn = sqlite3.connect(str(self.output_db))
    cursor = conn.cursor()

    # For each element, create simple box based on position
    cursor.execute("SELECT guid, center_x, center_y, center_z FROM element_transforms")
    for guid, x, y, z in cursor.fetchall():
        # Create simple 1m cube at position
        geometry_blob = create_box_mesh(x, y, z, 1.0, 1.0, 1.0)
        cursor.execute("""
            INSERT INTO base_geometries
            (guid, geometry_blob, bbox_min_x, bbox_min_y, bbox_min_z,
             bbox_max_x, bbox_max_y, bbox_max_z)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (guid, geometry_blob, x-0.5, y-0.5, z-0.5, x+0.5, y+0.5, z+0.5))

    conn.commit()
    conn.close()
```

---

## 🛠️ Part 2: Template Configurator Recap

### What It Does

The **Template Configurator** is a **PyQt5 GUI tool** that helps users:

1. **Upload files:**
   - DWG/DXF (2D geometry)
   - Excel space program (optional)
   - PDF design notes (optional)

2. **Configure spaces visually:**
   - See detected spaces/rooms
   - Assign functional types (e.g., "Waiting Area", "Toilet", "Office")
   - Set parameters (seating density, ceiling height, etc.)

3. **Set global defaults:**
   - Building type (Airport, Hospital, Office, etc.)
   - MEP standards (sprinkler spacing, lighting lux, HVAC requirements)
   - Material/finish preferences

4. **Export JSON configuration:**
   - Machine-readable rules
   - Used by `dxf_to_database.py` for better conversion accuracy

### Current Status

**What Exists:**
```
/home/red1/Documents/bonsai/2Dto3D/TemplateConfigurator/
├── main.py              # Entry point (PyQt5 app)
├── ui/                  # 3-tab interface
│   ├── tab_import.py   # File upload
│   ├── tab_spaces.py   # Space configuration
│   └── tab_defaults.py # Global settings
├── models/             # Data models
├── database/           # Template DB connection
└── parsers/            # File parsers (planned)
```

**What Works:**
- ✅ 3-tab GUI interface
- ✅ File upload dialogs
- ✅ Template database connection (44 templates)
- ✅ Space configuration forms
- ✅ Global defaults forms
- ✅ JSON export

**What's Missing:**
- ⚠️ Real DWG parsing (currently mock data)
- ⚠️ 2D visual canvas (currently list-based)
- ⚠️ Excel parsing (planned)
- ⚠️ PDF parsing (planned)
- ⚠️ Integration with new smart layer mapper

### The Vision (How It Should Work)

**Step 1: Import Files**
```
User: Uploads Terminal_1.dxf

System:
  ✓ Parses DXF (26,519 entities)
  ✓ Runs smart layer mapper (81% auto-classified)
  ✓ Detects spaces/rooms
  ✓ Estimates elements needed

Shows: "Detected 50 spaces, 26K entities, 7 disciplines"
```

**Step 2: Configure Spaces (Visual Canvas)**
```
┌─────────────────────────────────────────────────┐
│ 2D Floor Plan View                               │
│                                                  │
│     ┌──────────┐                                │
│     │  Hall A  │  ← Click to configure          │
│     │          │                                 │
│     └──────────┘                                │
│                                                  │
│ Functional Type: [Waiting Area ▼]               │
│ Template: [Terminal Gate Seating ▼]             │
│ Seating: [176 seats auto-calculated]            │
│ Lighting: [354 fixtures, 500 lux]               │
│ Sprinklers: [Auto per NFPA 13]                  │
│                                                  │
│ [Preview in 3D] [Apply] [Next Space]            │
└─────────────────────────────────────────────────┘
```

**Step 3: Review & Export**
```
Spaces configured: 48/50 (96%)
  ✓ Waiting areas: 8 spaces (seating configured)
  ✓ Toilets: 12 spaces (fixtures configured)
  ✓ Circulation: 18 spaces (lighting only)
  ⚠️ 2 spaces need review

Global Defaults:
  Building Type: Airport Terminal ✓
  Fire Protection: NFPA 13 Light Hazard ✓
  Lighting: MS 1525 (500 lux public areas) ✓
  ACMV: ASHRAE 62.1 ✓

[Export Configuration JSON]
```

**Step 4: Run Conversion**
```bash
python dxf_to_database.py \
    --input Terminal_1.dxf \
    --output Generated_Terminal1.db \
    --templates terminal_base_v1.0/template_library.db \
    --layer-mappings layer_mappings.json \
    --config terminal_1_config.json  # ← From Template Configurator!
```

**Result:**
- Accuracy: 70% → **95%+** (with configuration)
- Elements: 15,257 → **45,000+** (with inferred MEP)
- User time: 6 months → **2 hours** (including configuration)

### How Template Configurator Improves Accuracy

**Without Configurator (Current - 57.5%):**
```
Layer "FURNITURE" → Auto-mapped to ARC
  → Generic IfcBuildingElementProxy
  → No specific properties
  → No spacing logic
```

**With Configurator (Target - 95%+):**
```
Layer "FURNITURE" + User config ("Waiting Area")
  → ARC_IfcFurniture with template "Terminal_Gate_Seating"
  → Properties: Material=Metal/Plastic, LoadCapacity=150kg
  → Spacing: 0.65m between seats, 1.2m between rows
  → Auto-generate: 176 seats in pattern
  → Auto-add: 354 lights (500 lux), 697 sprinklers (NFPA 13)
```

### Integration with Smart Mapper

**New Workflow (Phase 1 Smart Mapper + Template Configurator):**

```
1. Smart Layer Mapper runs automatically
   ↓
   Classifies 81% of layers
   Maps 15,257 elements

2. Template Configurator opens
   ↓
   Shows pre-classified spaces
   User reviews 19% unmapped
   User configures functional types

3. Export enhanced JSON
   ↓
   layer_mappings.json (from smart mapper)
   + terminal_1_config.json (from configurator)

4. Run conversion with both
   ↓
   dxf_to_database.py --layer-mappings ... --config ...

5. Result: 95%+ accuracy, 45K+ elements
```

---

## 🎯 What Needs to Happen Next

### To Open Database in Bonsai NOW:

**Quick Test (View Metadata):**
```bash
# Launch Blender
~/blender-4.2.14/blender

# Open Python console, paste:
import sqlite3
conn = sqlite3.connect("/home/red1/Documents/bonsai/2Dto3D/Generated_Terminal1_SAMPLE.db")
cursor = conn.cursor()
cursor.execute("SELECT discipline, COUNT(*) FROM elements_meta GROUP BY discipline")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]} elements")
```

**To See in 3D Viewport:**
Need to add:
1. Base geometries (placeholder boxes)
2. Spatial structure (building/storey)
3. Integration script for Federation module

### To Update Template Configurator:

**Priority Updates:**

1. **Integrate Smart Layer Mapper** (1-2 days)
   - Replace mock DWG parser with real `dwg_parser.py`
   - Load `layer_mappings.json` automatically
   - Show pre-classified layers in UI

2. **Add 2D Visual Canvas** (2-3 days)
   - Display DXF floor plan
   - Click to select spaces
   - Drag-and-drop functional type icons
   - Real-time element count updates

3. **Export Enhanced JSON** (1 day)
   - Combine layer mappings + user configurations
   - Include array parameters (seating density, etc.)
   - Export in format `dxf_to_database.py` expects

4. **Test End-to-End** (1 day)
   - Upload Terminal 1 DXF
   - Configure spaces
   - Export JSON
   - Run conversion
   - Validate in Bonsai

**Total Time: 5-7 days**

---

## 🚀 Recommended Next Steps

### Option A: Quick Visualization (Today)

**Goal:** See the 15,257 elements in Blender right now

**Tasks:**
1. Add simple box geometries to database (1-2 hours)
2. Write Blender import script (1 hour)
3. Load and view in Outliner (15 minutes)

**Result:** Visual confirmation that conversion worked!

### Option B: Complete Template Configurator (This Week)

**Goal:** Full end-to-end workflow with GUI

**Tasks:**
1. Update Template Configurator with smart mapper
2. Add 2D visual canvas
3. Test full workflow Terminal 1 → Terminal 2
4. Measure accuracy improvement

**Result:** Production-ready tool for all future projects!

### Option C: Both in Parallel (Recommended)

**Day 1:** Quick visualization (Option A)
  - Proves concept works
  - Motivates team
  - Shows stakeholders

**Days 2-7:** Template Configurator updates (Option B)
  - Production-quality tool
  - Reusable for all projects
  - Scalable to other building types

---

## 💡 The Big Picture

### What We Have Now:

```
DXF File (2D)
    ↓
Smart Layer Mapper (automatic, 81% accuracy)
    ↓
layer_mappings.json
    ↓
dxf_to_database.py (conversion)
    ↓
Generated_Terminal1_SAMPLE.db (15,257 elements, 57.5% coverage)
    ↓
Ready to open in Bonsai (metadata only, no geometry yet)
```

### What We're Building Toward:

```
DXF File (2D) + Excel + PDF
    ↓
Smart Layer Mapper (automatic, 81%)
    ↓
Template Configurator (user configures 19%, adds intelligence)
    ↓
layer_mappings.json + terminal_1_config.json
    ↓
dxf_to_database.py (enhanced conversion)
    ↓
Complete Database (45K+ elements, 95% coverage, with 3D geometry)
    ↓
Open in Bonsai → Full 3D BIM model → Federation features work!
```

### Timeline:

- **Today:** ✅ Smart mapper working (81% auto-classification)
- **This Week:** Add visualization + update configurator
- **Next Week:** Test on Terminal 2 (validate reusability)
- **Month 1:** Production deployment, train users
- **Month 2-3:** Scale to other building types

---

## 📁 File Locations

**Generated Database:**
```
/home/red1/Documents/bonsai/2Dto3D/Generated_Terminal1_SAMPLE.db
```

**Template Configurator:**
```
/home/red1/Documents/bonsai/2Dto3D/TemplateConfigurator/
```

**Documentation:**
```
/home/red1/Documents/bonsai/2Dto3D/Documentation/
  ├── TEMPLATE_CONFIGURATOR_DESIGN.md
  ├── TEMPLATE_CONFIGURATOR_HANDOFF.md
  └── TEMPLATE_CONFIGURATOR_UPDATES.md
```

**Smart Mapper:**
```
/home/red1/Documents/bonsai/2Dto3D/Scripts/smart_layer_mapper.py
/home/red1/Documents/bonsai/2Dto3D/layer_mappings.json
```

---

## ✅ Summary

**Can you open the database in Bonsai Blender?**
- **Yes!** The metadata is there and Bonsai-compatible
- **But:** No 3D geometry yet, so elements won't show in viewport
- **Quick fix:** Add placeholder box geometries (1-2 hours)
- **Full fix:** Integrate with Federation module properly (1-2 days)

**Template Configurator?**
- **Exists!** PyQt5 GUI tool in `TemplateConfigurator/` folder
- **Purpose:** Help users configure spaces, set defaults, export JSON
- **Status:** Working UI, needs smart mapper integration
- **Next:** Connect real DWG parser, add 2D canvas, test end-to-end

**The Vision:**
Smart mapper (automatic 81%) + Template Configurator (user adds 14% intelligence) = **95%+ accuracy** automated BIM generation from 2D drawings!

---

**Ready to proceed? Which path interests you most:**
1. Quick visualization (see the 15K elements in Blender today)
2. Template Configurator update (build the full production tool)
3. Both in parallel (prove it works, then make it production-ready)

Let me know!
