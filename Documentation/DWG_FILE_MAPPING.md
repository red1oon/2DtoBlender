# Terminal 1 DWG File Mapping

**Source:** Engineer feedback
**Date:** November 11, 2025

---

## FILE STRUCTURE

### **File #1: "2. BANGUNAN TERMINAL 1.dwg" (14MB)**
**Discipline:** ARCHITECTURE (ARC)
**Contains:**
- Floor plans (walls, doors, windows)
- Room layouts
- Seating arrangements
- Circulation paths
- Amenity zones
- Possibly fire exits, restrooms, gates

**Output IFC:** SJTII-ARC-A-TER1-00-R0-Clean.ifc (35,338 elements)

---

### **File #2: "2. TERMINAL-1.zip" (18 DWG files)**
**Disciplines:** STRUCTURE (STR) + MEP + Others
**Contains:**

#### Structural (Primary):
- Ground beam layouts (GB)
- Floor beam layouts (1FB-6FB)
- Slab details (GS-4FS)
- Cross-sections
- Foundation details

#### MEP (Possibly embedded):
- ACMV routes (ducts, equipment)
- Electrical (conduits, panels, lights)
- Fire Protection (sprinklers, alarms)
- Plumbing (pipes, fixtures)
- Chilled Water (CW)
- LPG

**Output IFCs:**
- SJTII-STR-S-TER1-00-R0-Clean.ifc (1,429 elements)
- SJTII-ACMV-A-TER1-00-R0-Clean.ifc (1,621 elements)
- SJTII-ELEC-A-TER1-00-R0-Clean.ifc (1,172 elements)
- SJTII-FP-A-TER1-00-R0-Clean.ifc (6,880 elements)
- SJTII-SP-A-TER1-00-R0-Clean.ifc (979 elements)
- SJTII-CW-A-TER1-00-R0-Clean.ifc (1,431 elements)
- SJTII-LPG-A-TER1-00-RO-Clean.ifc (209 elements)

---

## PROPOSED UI WORKFLOW

### **Option A: Manual File Assignment**

```
┌────────────────────────────────────────────────────────────┐
│ Bonsai Import DWG - Discipline Mapper                     │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ Load Architecture DWG(s):                                 │
│ [Browse...] 2. BANGUNAN TERMINAL 1.dwg         [Add More] │
│                                                            │
│ Load Structural DWG(s):                                   │
│ [Browse...] 2. TERMINAL-1.zip                  [Add More] │
│ ├─ T1-2.0_Lyt_GB_e2P2_240711.dwg                         │
│ ├─ T1-2.1_Lyt_1FB_e1P1_240530.dwg                        │
│ ├─ ... (16 more files)                                    │
│                                                            │
│ Load MEP DWG(s): (Optional)                               │
│ [Browse...] (No files selected)                           │
│                                                            │
│ Advanced Options:                                         │
│ ☑ Auto-detect discipline from layers                     │
│ ☐ Manual layer mapping                                    │
│ ☐ Import as single merged model                          │
│                                                            │
│         [Cancel]  [Parse DWGs → Database]                │
└────────────────────────────────────────────────────────────┘
```

**Workflow:**
1. User loads "BANGUNAN TERMINAL 1.dwg" → Tags as ARC
2. User loads "TERMINAL-1.zip" → Tags as STR+MEP
3. System parses layers within each file:
   - ARC file: A-WALL, A-DOOR, A-FURN → Architecture
   - STR files: S-BEAM, S-COLS, S-SLAB → Structure
   - If M-DUCT found → ACMV
   - If E-POWER found → Electrical
   - If FP-PIPE found → Fire Protection
4. Database populated with discipline classification

---

### **Option B: Smart Layer Detection (Auto)**

```
┌────────────────────────────────────────────────────────────┐
│ Bonsai Import DWG - Auto Discipline Detection             │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ Load DWG Files/Folders:                                   │
│ [Browse...] /RawDWG/                                      │
│                                                            │
│ Files Detected:                                           │
│ ✓ 2. BANGUNAN TERMINAL 1.dwg (14MB)                      │
│ ✓ 2. TERMINAL-1.zip (18 files extracted)                 │
│                                                            │
│ Layer Analysis:                                           │
│ ┌────────────────────────────────────────────────────────┐│
│ │ File: BANGUNAN TERMINAL 1.dwg                          ││
│ │   Layers Found: 127 layers                             ││
│ │   ✓ A-WALL (45 entities) → Architecture               ││
│ │   ✓ A-DOOR (18 entities) → Architecture               ││
│ │   ✓ A-FURN-SEAT (892 blocks) → Architecture (Seating) ││
│ │   ✓ A-GRID (grid lines) → Skip (annotation)           ││
│ │   ? LAYER-X (unknown) → [Manual Review Required]      ││
│ │                                                         ││
│ │ File: T1-2.0_Lyt_GB_e2P2_240711.dwg                    ││
│ │   Layers Found: 84 layers                              ││
│ │   ✓ S-BEAM-GB (234 entities) → Structure              ││
│ │   ✓ S-COLS (67 entities) → Structure                  ││
│ │   ✓ M-DUCT (12 entities) → ACMV (MEP)                 ││
│ │   ✓ E-PANEL (3 blocks) → Electrical (MEP)             ││
│ │                                                         ││
│ │ ... (16 more files)                                    ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ Summary:                                                  │
│   ARC: 35,412 entities detected (1 file)                 │
│   STR: 1,458 entities detected (18 files)                │
│   ACMV: 1,621 entities detected (embedded in STR files)  │
│   ELEC: 1,172 entities detected (embedded in STR files)  │
│   FP: 6,880 entities detected (embedded in STR files)    │
│   Unknown: 247 entities (manual review required)         │
│                                                            │
│   [Review Mappings]  [Cancel]  [Import to Database]      │
└────────────────────────────────────────────────────────────┘
```

**Workflow:**
1. User loads all DWGs (no manual tagging)
2. System parses layers automatically:
   - Layer starts with "A-" → Architecture
   - Layer starts with "S-" → Structure
   - Layer starts with "M-" → ACMV
   - Layer starts with "E-" → Electrical
   - Layer starts with "FP-" → Fire Protection
   - Layer starts with "P-" or "SP-" → Plumbing
3. System shows preview of classification
4. User reviews and corrects misclassifications
5. Import proceeds

---

### **Option C: Hybrid (Recommended)**

**Start with Auto-Detection, Allow Manual Override:**

```python
# Proposed UI logic
def import_dwg_workflow(file_paths):
    # Step 1: User provides files
    dwg_files = load_dwg_files(file_paths)

    # Step 2: Auto-detect discipline from filename + layers
    classifications = {}
    for dwg in dwg_files:
        if 'BANGUNAN' in dwg.name.upper() or 'ARC' in dwg.name.upper():
            classifications[dwg] = 'ARC'  # Filename hint
        elif 'TERMINAL-1.zip' in dwg.source:
            classifications[dwg] = 'STR+MEP'  # Multi-discipline

        # Layer-level classification
        dwg.layer_map = auto_classify_layers(dwg.layers)

    # Step 3: Show preview UI
    show_classification_preview(classifications)

    # Step 4: User can override:
    # - "This file is ARC, not STR" (file-level)
    # - "This layer is ELEC, not ACMV" (layer-level)

    # Step 5: Import with confirmed classifications
    import_to_database(classifications)
```

**UI Elements:**
- **File-level tagging:** Dropdown per file (ARC | STR | MEP | AUTO)
- **Layer-level review:** Expandable table showing layer → discipline mapping
- **Confidence scores:** "95% confident this is ARC, 5% uncertain"
- **Manual override:** Click to reassign layer to different discipline

---

## LAYER NAMING CONVENTIONS (Auto-Detection Rules)

### **Architecture (ARC):**
```
Prefix patterns:
- A-*         (standard: A-WALL, A-DOOR, A-WINDOW)
- ARC-*       (variant: ARC-WALL)
- ARCH-*      (variant: ARCH-WALL)
- *-WALL      (suffix: 01-WALL, EXT-WALL)
- *-DOOR
- *-WINDOW
- *-FURN*     (furniture: A-FURN-SEAT)
- *-SEAT*     (seating: SEAT-AREA)
```

### **Structure (STR):**
```
Prefix patterns:
- S-*         (standard: S-BEAM, S-COLS, S-SLAB)
- STR-*       (variant: STR-BEAM)
- STRUCT-*    (variant: STRUCT-BEAM)
- *-BEAM
- *-COLUMN
- *-SLAB
- *-FOOTING
- *-TRUSS
- *-REBAR     (reinforcement)
```

### **ACMV (Mechanical/HVAC):**
```
Prefix patterns:
- M-*         (standard: M-DUCT, M-AHU, M-EQUIP)
- ACMV-*      (variant: ACMV-DUCT)
- HVAC-*      (variant: HVAC-DUCT)
- *-DUCT
- *-AHU       (air handling unit)
- *-FCU       (fan coil unit)
- *-CHILLER
- *-VAV       (variable air volume)
```

### **Electrical (ELEC):**
```
Prefix patterns:
- E-*         (standard: E-POWER, E-LIGHT, E-PANEL)
- ELEC-*      (variant: ELEC-POWER)
- ELECT-*     (variant: ELECT-POWER)
- *-POWER
- *-LIGHT*    (lighting: E-LIGHT-FIX)
- *-PANEL     (electrical panels)
- *-CONDUIT
- *-CABLE
```

### **Fire Protection (FP):**
```
Prefix patterns:
- FP-*        (standard: FP-PIPE, FP-SPRK)
- FIRE-*      (variant: FIRE-SPRINKLER)
- *-SPRK*     (sprinkler: FP-SPRK-HEAD)
- *-HYDRANT
- *-ALARM     (fire alarm)
- *-EXTING*   (extinguisher)
- *-HOSE*     (hose reel)
```

### **Plumbing (SP):**
```
Prefix patterns:
- P-*         (standard: P-PIPE, P-DRAIN)
- SP-*        (sanitary plumbing: SP-PIPE)
- PLUMB-*     (variant: PLUMB-PIPE)
- *-DRAIN*    (drainage)
- *-SEWER
- *-WATER     (water supply)
- *-FIXTURE   (plumbing fixtures)
```

### **Chilled Water (CW):**
```
Prefix patterns:
- CW-*        (standard: CW-PIPE)
- CHW-*       (variant: CHW-PIPE)
- *-CHW*      (chilled water)
```

### **LPG (Gas):**
```
Prefix patterns:
- LPG-*       (standard: LPG-PIPE)
- GAS-*       (variant: GAS-PIPE)
- *-GAS*
```

### **Skip (Annotations - Don't Import):**
```
Skip patterns:
- *-GRID      (grid lines)
- *-DIM*      (dimensions)
- *-TEXT      (text annotations)
- *-ANNO*     (annotations)
- *-XREF*     (external references)
- *-DEFPOINTS (AutoCAD system layer)
- *-VIEWPORT  (viewports)
- 0           (default layer, usually empty)
```

---

## IMPLEMENTATION NOTES

### **Database Schema Addition:**

```sql
-- Track file-to-discipline mapping
CREATE TABLE dwg_source_files (
    file_id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    discipline_hint TEXT,        -- ARC, STR, MEP, AUTO
    file_size_bytes INTEGER,
    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track layer-to-discipline mapping
CREATE TABLE dwg_layer_mapping (
    layer_id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES dwg_source_files(file_id),
    layer_name TEXT NOT NULL,
    discipline TEXT NOT NULL,     -- ARC, STR, ACMV, ELEC, FP, etc.
    entity_count INTEGER,
    classification_confidence REAL,  -- 0.0-1.0 (auto-detection confidence)
    manual_override BOOLEAN DEFAULT 0
);

-- Link elements to source layers
ALTER TABLE elements_meta ADD COLUMN source_layer_id INTEGER REFERENCES dwg_layer_mapping(layer_id);
```

---

## EXAMPLE USAGE

### **Scenario: Import Terminal 1 DWGs**

**User Actions:**
1. Open Bonsai → Federation → Import DWG
2. Browse to `/Documents/bonsai/RawDWG/`
3. Select "2. BANGUNAN TERMINAL 1.dwg" + "2. TERMINAL-1.zip"
4. Click "Parse Files"

**System Actions:**
```
Parsing DWG files...
✓ 2. BANGUNAN TERMINAL 1.dwg (14MB)
  - 127 layers found
  - 35,412 entities detected
  - Primary discipline: ARC (98% confidence)

✓ 2. TERMINAL-1.zip (extracting...)
  - 18 files extracted
  - T1-2.0_Lyt_GB_e2P2_240711.dwg
    - 84 layers found
    - 456 entities detected
    - Disciplines: STR (78%), ACMV (12%), ELEC (10%)
  - ... (17 more files)

Summary:
  ARC: 35,412 entities (1 file, 98% confidence)
  STR: 1,458 entities (18 files, 92% confidence)
  ACMV: 1,621 entities (embedded, 87% confidence)
  ELEC: 1,172 entities (embedded, 89% confidence)
  FP: 6,880 entities (embedded, 94% confidence)
  SP: 979 entities (embedded, 91% confidence)
  CW: 1,431 entities (embedded, 93% confidence)
  LPG: 209 entities (embedded, 88% confidence)
  Unknown: 247 entities (requires manual review)

[Review Classifications] [Import to Database]
```

**User Reviews:**
- Checks "Unknown: 247 entities" list
- Sees layer "CUSTOM-LAYER-X" with 100 entities
- Manually assigns to "ARC" (furniture, custom blocks)
- Clicks "Import to Database"

**Result:**
- 49,059 elements imported
- Database populated with discipline classifications
- Ready for 3D generation

---

## DECISION: Which Option to Implement?

**Recommendation: Option C (Hybrid)**

**Rationale:**
- ✅ **User-friendly:** Auto-detection handles 90% of cases
- ✅ **Flexible:** Manual override for special cases
- ✅ **Transparent:** User sees classification before import
- ✅ **Learnable:** System improves with each project
- ✅ **No rigid file structure:** Works with consultant's existing naming

**POC Implementation:**
1. Parse all DWGs in folder
2. Run layer auto-classification (pattern matching)
3. Show preview table (layer → discipline)
4. Allow manual corrections
5. Import to database with full traceability

---

**This solves the "how do we know which DWG is which?" problem elegantly.**
