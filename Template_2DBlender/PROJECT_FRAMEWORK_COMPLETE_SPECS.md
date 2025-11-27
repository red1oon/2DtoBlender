# 2D to Blender BIM - Project Framework

**Project:** PDF Architectural Drawing → Blender BIM Model
**Target:** 98% Accuracy, Production-Ready
**Updated:** 2025-11-26

---

# PART I: PROJECT RULES

## Rule 0: Fix Source Code Only

**If output is wrong → fix SOURCE code, not output.**

**Enforcement:**
- ✅ TEXT-ONLY algorithms (no image recognition, no ML/AI)
- ✅ Hardcoded parameters in source code
- ✅ Same input → same output (deterministic)
- ❌ NO manual tweaking of extraction results
- ❌ NO AI-assisted cleanup of outputs
- ❌ NO post-processing tools to "fix" bad extractions

**Why:** Ensures reproducibility, prevents technical debt, enables automation, guarantees traceability.

---

## Rule 1: Consolidation

**Progress Reporting:** ONE file → `PROGRESS.md`
**Output Artifacts:** ONE folder → `output_artifacts/`
**Existing APIs:** Search before creating → Check StandingInstructions.txt

---

## Rule 2: Library Validation

**Master template MUST be validated against Ifc_Object_Library.db**

```bash
python3 validators/validate_library_references.py \
    core/master_reference_template.json \
    DatabaseFiles/Ifc_Object_Library.db
```

**Status:** ✅ 30/30 object_types found (100%)

---

## Rule 3: Two-Tier Architecture

**TIER 1:** `master_reference_template.json` - High-level instructions (what to search)
**TIER 2:** `vector_patterns.py` - Low-level execution (how to detect)

**Why:** Template stays concise, complex logic centralized, pattern reuse.

---

## Rule 4: No Tools Outside Framework

**Forbidden:**
- ❌ Post-processing scripts
- ❌ Tools that bypass validation

**Allowed:**
- ✅ Enhance extraction_engine.py
- ✅ Enhance vector_patterns.py
- ✅ Tools in validators/

---

## Rule 5: Master Doc Authority

**CRITICAL:** Nothing can proceed unless explicitly defined in this document.

- ❌ DO NOT execute any process not documented here
- ❌ DO NOT assume a step exists
- ❌ DO NOT invent workflows
- ✅ IF unclear or undefined → STOP and define it here first

---

# PART II: PIPELINE ARCHITECTURE

## Pipeline Overview

```
Stage 0: PDF → Primitives (text, lines, curves, rects)
   ↓
Stage 1: Context (calibration, schedules, dimensions, elevations)
   ↓
Stage 1.5: Readiness Check (verify completeness)
   ↓
Stage 2.1: Walls (semantic layer)
Stage 2.2: Patterns (doors, windows)
Stage 2.3: Relationships (spatial links)
   ↓
Stage 3: Object Placement (with coordinates)
   ↓
Stage 4: Blender Import (LOD300 geometry)
```

---

## Stage 0: PDF → Primitives

**Script:** `core/primitive_extractor.py`

**Input:** PDF file

**Output:** SQLite database with primitives tables

**Algorithm:**
- Use pdfplumber to extract text, lines, curves, rectangles
- Store with PDF coordinates (NO transformation)
- Include AutoCAD SHX text (via `page.annots`)

**Tables:**
- `primitives_text`: text, x, y, bbox
- `primitives_lines`: x0, y0, x1, y1, linewidth
- `primitives_curves`: x0, y0, x1, y1, pts_json
- `primitives_rects`: x0, y0, x1, y1, area

---

## Stage 1: Context Extraction

**Scripts:** calibration_engine.py, legend_extractor.py, dimension_extractor.py, elevation_extractor.py

### 1.1: Calibration
- Method 1: Grid reference analysis
- Method 2: Scale notation text search
- Method 3: DISCHARGE marker perimeter
- Output: scale_m_per_pt, offset_x, offset_y

### 1.2: Schedules
- Find "width X height" patterns
- Match to door/window IDs (D1-D3, W1-W3)
- Output: item_id, width_mm, height_mm

### 1.3: Dimensions
- Extract grid spacing
- Calculate building_width_m, building_length_m

### 1.4: Elevations
- Search FFL, LINTEL, CEILING, SILL keywords
- Extract numerical values
- Calculate heights

---

## Stage 1.5: Readiness Check

**Checks:**
1. Primitives count: >10,000 lines, >1,000 text
2. Context completeness: All 4 tables populated
3. Key markers: DISCHARGE (21), D1-D3 (18), W1-W3 (40)
4. Calibration confidence: >0.9

---

## Stage 2: Pattern Recognition

### Stage 2.1: Walls (semantic_wall_detection.py)

**Algorithm:**
1. Extract 4 exterior walls from building footprint
2. Cluster interior walls (DBSCAN)
3. Merge collinear segments
4. Validate (MIN_WALL_LENGTH, MIN_LINE_WIDTH)

**Output:** `semantic_walls` table (~20 walls)

**Tuning:** Edit constants if over/under-segmented

---

### Stage 2.2: Patterns (pattern_recognition.py)

**Algorithm:**
1. Text label search (D1-D3, W1-W3)
2. Geometry proximity matching (KDTree)
3. Wall containment (bbox intersection)
4. Schedule validation (dimension matching)

**Output:** `patterns_identified` table (~18 patterns)

**Tuning:** Edit thresholds if patterns missed

---

### Stage 2.3: Relationships (derive_spatial_relationships.py)

**Algorithm:**
1. ON relationships (bbox intersection)
2. IN relationships (containment)
3. NEAR relationships (distance threshold)
4. ALIGNED relationships (alignment tolerance)

**Output:** `spatial_relationships` table

---

## Stage 3: Object Placement

**Script:** `core/extraction_engine.py`

**Algorithm:**
1. Read master_reference_template.json sequentially
2. Execute pattern matching from vector_patterns.py
3. Transform PDF coords → building coords
4. Output positioned objects

**Output:** `output_artifacts/TB-LKTN_HOUSE_OUTPUT_*.json`

---

## Stage 4: Blender Import

**Script:** `blender_lod300_import.py`

**Algorithm:**
1. Read extraction JSON
2. Fetch vertices/faces/normals from library database
3. Create Blender mesh at position
4. Mark as placed

**Output:** Final BIM model in Blender

---

# PART III: CRITICAL IMPLEMENTATION NOTES

## Mandatory Verification

**Stage 0:**
```sql
SELECT COUNT(*) FROM primitives_text; -- Expect >1000
SELECT COUNT(*) FROM primitives_lines; -- Expect >10000
```

**Stage 1:**
```sql
SELECT key, value FROM context_calibration
WHERE key IN ('building_width_m', 'building_length_m', 'scale_m_per_pt');
-- Expect: 8-15m, 8-15m, 0.030-0.040
```

**Stage 2.1:**
```sql
SELECT COUNT(*), wall_type FROM semantic_walls GROUP BY wall_type;
-- Expect: 4 exterior, 11-21 interior
```

---

## Page Selection Strategy

**Floor Plan (page 1):** Labels, dimensions
**Electrical Plan (page 2):** Clean geometry (NO duplicate walls!)
**Roof Plan (page 3):** Roof structure
**Elevations (pages 4-7):** Height data only

**Critical:** Floor + Electrical show SAME building. Extract labels from page 1, geometry from page 2.

---

## Success Metrics

**Target (Final):**
- Position Accuracy: 98% (<10cm error)
- Object Detection: 96%
- Wall Accuracy: 95%
- Opening Placement: 90%
- Overall Confidence: **98%**

---

**Status:** Stages 0, 1, 1.5, 2.1 complete | Stage 2.2 ready to execute
**Next:** Execute pattern_recognition.py for Stage 2.2
