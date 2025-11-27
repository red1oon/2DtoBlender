# QA Review Findings - TB-LKTN House
**Review Date:** 2025-11-26
**Reviewer:** QA Expert
**Document Reviewed:** MASTER_SPECIFICATION.md + master_template.json

---

## CRITICAL ERRORS FOUND

### 1. Window Count Mismatch ❌

**Issue:** master_template.json has 10 windows, but Page 8 schedule specifies only 7.

**Evidence from page8_schedules.json (OCR):**
```
Line 1182-1203: SIZE = 1800mm X 1000mm
Line 1261-1267: LOCATION = Dapur  ← Only ONE location!

Line 1206-1227: SIZE = 1200mm X 1000mm
Line 1270-1370: LOCATION = Ruang Tamu, Bilik Utama, Bilik 2 & Bilik 3  ← FOUR locations

Line 1230-1249: SIZE = 600mm X 500mm
Line 1302-1330: LOCATION = Tandas & Bilik Mandi  ← TWO locations
```

**Correct Schedule:**
| Code | Size | Quantity | Rooms |
|------|------|----------|-------|
| W1 | 1800×1000mm | **1 NOS** | Dapur |
| W2 | 1200×1000mm | **4 NOS** | Ruang Tamu, Bilik Utama, Bilik 2, Bilik 3 |
| W3 | 600×500mm | **2 NOS** | Tandas, Bilik Mandi |
| **TOTAL** | | **7 windows** | |

**Current (WRONG):**
- W1: 4 units ❌
- W2: 4 units ✓
- W3: 2 units ✓
- Total: 10 ❌

**Corrected:**
- W1: 1 unit ✓
- W2: 4 units ✓
- W3: 2 units ✓
- **Total: 7 units** ✓

**Impact:** 3 windows incorrectly placed (W1_2, W1_3, W1_4 don't exist per schedule)

---

### 2. Bedroom Shape Inconsistency ❌

**Issue:** Specification claims "all bedrooms are squares" but BILIK_3 is a rectangle.

**Evidence from master_template.json:**
```json
"BILIK_3": {
  "grid": "C1-D2",
  "x": [4.4, 8.1],  // 3.7m wide
  "y": [0.0, 2.3],  // 2.3m deep
  "shape": "rectangle",  ← NOT square!
  "area_m2": 8.51
}
```

**Calculation:** 3.7m × 2.3m = 8.51 m²

**MASTER_SPECIFICATION.md states (line 627):**
> "BILIK_2: 6.8×1.5m → 3.1×3.1m (square per spec)"

**Contradiction:** Spec says bedrooms are squares, but BILIK_3 is rectangle.

**Options:**
1. **Fix template:** Make BILIK_3 square (3.1×3.1m) to match spec
2. **Fix spec:** Document that BILIK_3 is exception (rectangle bedroom allowed)

**Recommendation:** Document BILIK_3 as architectural exception (grid constraints C1-D2 = 3.7×2.3).

---

### 3. Building Envelope Shape Incorrect ❌

**Issue:** Specification describes envelope as "rectangular 11.2m × 8.5m" but floor plan shows L-shape with ANJUNG porch.

**Current (WRONG):**
```json
"building_envelope": {
  "type": "rectangular_main_body",
  "area_m2": 95.2
}
```

**Corrected (from floor plan analysis):**
```json
"building_envelope": {
  "type": "L-shape",
  "main_body": {
    "x": [0.0, 11.2],
    "y": [0.0, 8.5],
    "area_m2": 95.2
  },
  "porch": {
    "name": "ANJUNG",
    "x": [2.3, 5.5],  // 3.2m wide
    "y": [-2.3, 0.0],  // 2.3m projection
    "area_m2": 7.36,
    "notes": "Front porch - excluded from main grid"
  },
  "polygon": [
    [0.0, 0.0], [11.2, 0.0], [11.2, 8.5], [0.0, 8.5], [0.0, 0.0],  // Main body
    [2.3, 0.0], [2.3, -2.3], [5.5, -2.3], [5.5, 0.0]  // Porch cutout
  ]
}
```

**Impact:** Exterior wall detection incorrect (porch walls not identified).

---

### 4. Missing Room: RUANG_MAKAN ❓

**Issue:** Floor plan shows RUANG_MAKAN (dining room) but not in room_bounds.

**Investigation needed:**
- Is RUANG_MAKAN part of RUANG_TAMU (open plan living/dining)?
- Or separate room that was missed?

**Action:** Review floor plan OCR for "RUANG_MAKAN" or "MAKAN" text.

---

## CORRECTIONS REQUIRED

### master_template.json

**1. Remove W1_2, W1_3, W1_4 (only W1_1 exists):**
```json
// BEFORE (10 windows)
"window_placements": [
  {"element_id": "W1_1", ...},  ← KEEP (Dapur)
  {"element_id": "W1_2", ...},  ← DELETE
  {"element_id": "W1_3", ...},  ← DELETE
  {"element_id": "W1_4", ...},  ← DELETE
  {"element_id": "W2_5", ...},  ← RENUMBER to W2_1
  ...
]

// AFTER (7 windows)
"window_placements": [
  {"element_id": "W1_1", "room": "DAPUR", ...},
  {"element_id": "W2_1", "room": "RUANG_TAMU", ...},
  {"element_id": "W2_2", "room": "BILIK_UTAMA", ...},
  {"element_id": "W2_3", "room": "BILIK_2", ...},
  {"element_id": "W2_4", "room": "BILIK_3", ...},
  {"element_id": "W3_1", "room": "BILIK_MANDI", ...},
  {"element_id": "W3_2", "room": "TANDAS", ...}
]
```

**2. Update validation.total_windows:**
```json
"validation": {
  "total_windows": 7,  // was 10
  "windows_requiring_review": 0
}
```

**3. Update metadata.sources:**
```json
"corrections_applied": [
  ...existing corrections...,
  "W1 count: 4 → 1 (Page 8 schedule: Dapur only)",
  "W2 element IDs: W2_5-W2_8 → W2_1-W2_4 (renumbered after W1 correction)",
  "Total windows: 10 → 7 (verified against Page 8 OCR)"
]
```

**4. Add BILIK_3 shape note:**
```json
"BILIK_3": {
  ...
  "shape": "rectangle",
  "notes": "Rectangle bedroom (grid constraint C1-D2) - architectural exception to square rule"
}
```

**5. Update building_envelope:**
```json
"building_envelope": {
  "type": "L-shape",
  "main_body": {...},
  "porch": {
    "name": "ANJUNG",
    "bounds": {"x": [2.3, 5.5], "y": [-2.3, 0.0]}
  },
  "polygon": [...]
}
```

---

### MASTER_SPECIFICATION.md

**1. Fix window counts throughout document:**
- Line 23: "10 windows" → "7 windows"
- Section 4.3: "W1×4" → "W1×1", "W2×4" → "W2×4", "W3×2" → "W3×2"
- Part IV summary: "17 elements" → "14 elements (7 doors + 7 windows)"

**2. Fix bedroom shape statement:**
- Add exception: "Bedrooms are 3.1×3.1m squares (except BILIK_3: 3.7×2.3m rectangle per grid constraint)"

**3. Update building envelope description:**
- Change "rectangular 11.2m × 8.5m" to "L-shape with ANJUNG porch (main: 11.2m × 8.5m, porch: 3.2m × 2.3m)"

**4. Update validation criteria:**
```
## 5.3 Page 8 Schedule Compliance

Expected Output:
D1: 900×2100mm (2 instances)
D2: 900×2100mm (3 instances)
D3: 750×2100mm (2 instances)
W1: 1800×1000mm (1 instance)  ← CORRECTED from 4
W2: 1200×1000mm (4 instances)
W3: 600×500mm (2 instances)
```

---

## QA VERDICT

**Status:** ❌ **FAIL - CRITICAL ERRORS**

**Blocking Issues:**
1. ❌ Window count incorrect (10 vs 7 per schedule)
2. ❌ Building envelope shape incorrect (rectangle vs L-shape)
3. ❌ Specification contradicts data (bedroom shape claim)

**Non-Blocking Issues:**
4. ❓ RUANG_MAKAN missing (needs investigation)

**Recommendation:** **FIX CRITICAL ERRORS BEFORE QA SIGN-OFF**

---

## FIX PRIORITY

**HIGH (Must fix before production):**
1. ✅ Correct window counts (remove W1_2, W1_3, W1_4)
2. ✅ Update total element count (17 → 14)
3. ✅ Add L-shape building envelope with porch

**MEDIUM (Should fix for consistency):**
4. ✅ Document BILIK_3 as architectural exception
5. ✅ Update all references to "10 windows" in docs

**LOW (Nice to have):**
6. ⚠ Investigate RUANG_MAKAN room
7. ⚠ Add porch (ANJUNG) to room_bounds if needed

---

## NEXT ACTIONS

1. **Developer:** Fix master_template.json (remove 3 windows, update validation)
2. **Developer:** Update MASTER_SPECIFICATION.md (correct counts, add L-shape envelope)
3. **Developer:** Re-run pipeline validation scripts
4. **QA:** Re-review after corrections applied
5. **QA:** Sign-off when all critical errors resolved

---

**Review Status:** ❌ FAILED (3 critical errors)
**Re-review Required:** YES
**Estimated Fix Time:** 30 minutes

---

**Prepared by:** QA Expert
**Date:** 2025-11-26
**Document Version:** 1.0
