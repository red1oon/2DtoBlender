# Master Reference Template - READ ONLY

## ⚠️ CRITICAL: THIS FILE IS READ ONLY

**File:** `core/master_reference_template.json`

**Status:** **READ ONLY - NEVER MODIFY**

---

## Purpose

The master reference template is a **PERMANENT COMPREHENSIVE COLLECTION** of all possible residential construction elements that can be extracted from architectural PDFs.

### What It Is

- ✅ Reference catalog of all residential building components
- ✅ High-level instruction set for OCR extraction engine
- ✅ Permanent collection (items remain even if not found in specific PDFs)
- ✅ Template-driven extraction (drives 100% of object detection)

### What It Is NOT

- ❌ Project-specific configuration file
- ❌ Output file (outputs go to `output_artifacts/`)
- ❌ Modifiable per-PDF settings
- ❌ Implementation status tracker

---

## Architecture

### Two-Tier System

```
┌─────────────────────────────────────────────┐
│  Tier 1: master_reference_template.json    │
│  (High-level "WHAT to search for")         │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Tier 2: vector_patterns.py                │
│  (Low-level "HOW to execute search")       │
└─────────────────────────────────────────────┘
```

**Analogy:** Think of it like Java bytecode → C implementation

- **Tier 1 (this file):** Says "Extract doors labeled D1-D5 from page 1"
- **Tier 2 (vector_patterns.py):** Implements how to search for text, transform coordinates, validate position

---

## Template Structure

### Extraction Sequence

Items are ordered by **construction sequence** (dependencies matter):

1. **Phase 1B - Calibration** (FIRST - establishes coordinate system)
   - Outer discharge drain perimeter

2. **Phase 1D - Elevations** (needed for heights)
   - FFL, lintel level, ceiling level, window sill height

3. **Phase 1A - Schedules** (needed for dimensions before position detection)
   - Door schedule, window schedule

4. **Phase 1C - Structure** (foundation first)
   - Floor slab, ceiling plane, roof structure

5. **Phase 1C - Walls** (after structure)
   - Interior walls, exterior walls

6. **Phase 2 - Openings** (after walls)
   - Doors, windows

7. **Phase 3 - Electrical** (after walls/rooms defined)
   - Switches, outlets, lights, fans

8. **Phase 4 - Plumbing** (after rooms defined)
   - Toilets, basins, sinks, showers, drains

9. **Phase 5 - Built-ins** (after rooms + walls)
   - Kitchen cabinets (base), kitchen cabinets (wall)

10. **Phase 6 - Furniture** (LAST - placed after rooms built)
    - Beds, wardrobes, dining tables, sofas, TV consoles, appliances

---

## Each Item Contains

```json
{
  "_phase": "Construction phase (ordering)",
  "_dependency": "What this depends on",
  "item": "Human-readable name",
  "detection_id": "Links to vector_patterns.py",
  "search_text": ["Keywords to search"],
  "pages": [0, 1],
  "object_type": "library_reference_lod300",
  "code_ref": "Optional pointer to implementation",
  "outputs": ["What gets added to context"]
}
```

---

## Implementation Status

### ✅ Fully Implemented (8/32 items)

Working for TB-LKTN HOUSE.pdf:

1. CALIBRATION_DRAIN_PERIMETER
2. STRUCTURAL_PLANE_GENERATION (floor/ceiling/roof)
3. WALL_VECTOR_LINES (interior walls)
4. BUILDING_PERIMETER (exterior walls)
5. TEXT_LABEL_SEARCH (doors, windows)
6. TEXT_MARKER_WITH_SYMBOL (switches, outlets, lights)

### ⚠️ Not Found in TB-LKTN HOUSE.pdf (15/32 items)

These items are **NOT removed from template** - they remain for other residential projects:

- Elevation text extraction (FFL, lintel, ceiling, sill)
- Schedule table extraction (door/window dimensions)
- Ceiling fans
- Plumbing fixtures (toilets, basins, sinks, showers, drains)
- Kitchen cabinets
- Furniture (beds, wardrobes, tables, sofas, appliances)

### 📋 Implementation Needed (9/32 items)

Detection methods defined but need full implementation:

- ELEVATION_TEXT_REGEX
- SCHEDULE_TABLE_EXTRACTION
- TOILET_BOWL_COMBO
- BASIN_SYMBOL, SINK_SYMBOL, SHOWER_SYMBOL, DRAIN_SYMBOL
- CABINET_VECTOR_PATTERN
- FURNITURE_RECTANGLE_WITH_TEXT
- APPLIANCE_RECTANGLE_WITH_TEXT, APPLIANCE_SYMBOL

**Note:** Items remain in template even if unimplemented. Template is a reference catalog, not a status tracker.

---

## Why Items Are Not Removed

### Example Scenario

**TB-LKTN HOUSE.pdf:**
- ❌ No ceiling fans found
- ❌ No plumbing fixtures labeled

**Other Residential PDF:**
- ✅ Has ceiling fans labeled "CF"
- ✅ Has toilets labeled "WC"

**Solution:** Keep all items in template. Each PDF extracts what it has.

### Template Philosophy

> "The master template is a **comprehensive catalog** of what COULD exist in residential construction, not what MUST exist in every PDF."

Items not found = `result: null` → skipped in output.

---

## Compliance Rules

### ✅ DO

- **Use template to drive extraction** - All objects must come from template sequence
- **Add new items** - If you discover new residential elements, add to template
- **Respect ordering** - Dependencies matter (calibration first, furniture last)
- **Keep comprehensive** - Template should cover ALL residential construction types

### ❌ DO NOT

- **Remove items** - Items remain even if not found in specific PDF
- **Modify during extraction** - Template is input, not output
- **Hardcode objects** - All extraction must be template-driven
- **Project-specific customization** - Template is universal for residential

---

## Validation

### Library Reference Validation

Every `object_type` in template MUST exist in `Ifc_Object_Library.db`:

```bash
# Check all object_types exist
sqlite3 DatabaseFiles/Ifc_Object_Library.db \
  "SELECT object_type FROM object_catalog WHERE object_type = 'door_single_900_lod300';"
```

**Current status:** 11/11 object_types validated ✅

### Template Integrity Check

```bash
# Validate JSON structure
python3 -m json.tool core/master_reference_template.json > /dev/null && echo "✅ Valid JSON"

# Count items
jq '.extraction_sequence | length' core/master_reference_template.json
# Expected: 32 items
```

---

## Related Documentation

- `CONSOLIDATION_COMPLETE.md` - Pipeline consolidation report
- `ANNOTATION_GROUND_TRUTH_WORKFLOW.md` - GIGO method for systematic capture
- `FINAL_PIPELINE_SUMMARY.md` - Complete extraction pipeline overview
- `PIPELINE_AUDIT_REPORT.md` - Detailed architectural audit

---

## Version Control

**Current Version:** 2.0 (Two-Tier Architecture)

**Change Log:**
- 2025-11-25: Added structural plane items (floor/ceiling/roof)
- 2025-11-25: Added READ ONLY notice
- 2025-11-24: Initial master template created

**Note:** Template additions are documented but items are never removed.

---

## Contact

**Questions about template items?**

Check implementation in `core/vector_patterns.py` using `detection_id` as lookup key.

**Want to add new detection method?**

1. Add item to `master_reference_template.json` extraction_sequence
2. Add pattern to `vector_patterns.py` VECTOR_PATTERNS dictionary
3. Implement execution method in VectorPatternExecutor class

---

**⚠️  REMINDER: THIS FILE IS READ ONLY - NEVER MODIFY ⚠️**
