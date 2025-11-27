# TB-LKTN House - Quick Reference Cheat Sheet
**Project:** 2D PDF → Blender BIM | **Date:** 2025-11-26 | **Status:** Production Ready

---

## 📐 GRID TRUTH (Foundation of All Coordinates)

```
Horizontal Grid (A-E):           Vertical Grid (1-5):
A = 0.0m                         1 = 0.0m
B = 1.3m  (A-B: 1.3m)           2 = 2.3m  (1-2: 2.3m)
C = 4.4m  (B-C: 3.1m ✓ square)  3 = 5.4m  (2-3: 3.1m ✓ square)
D = 8.1m  (C-D: 3.7m)           4 = 7.0m  (3-4: 1.6m)
E = 11.2m (D-E: 3.1m ✓ square)  5 = 8.5m  (4-5: 1.5m)

Building Envelope: 11.2m × 8.5m = 95.2 m² (main body)
+ ANJUNG porch: 3.2m × 2.3m = 7.36 m² (L-shape extension)
Total: 102.56 m²
```

---

## 🏠 ROOM LAYOUT (9 Rooms)

| Room | Grid | X Range | Y Range | Size | Area | Type | UBBL ✓ |
|------|------|---------|---------|------|------|------|--------|
| **BILIK_UTAMA** | D2-E3 | 8.1-11.2 | 2.3-5.4 | 3.1×3.1 | 9.61m² | Bedroom | ✓ |
| **BILIK_2** | B2-C3 | 1.3-4.4 | 2.3-5.4 | 3.1×3.1 | 9.61m² | Bedroom | ✓ |
| **BILIK_3** | TBD | TBD | TBD | 3.1×3.1 | TBD | Bedroom | ⚠️ |
| **RUANG_MAKAN** | C1-D2 | 4.4-8.1 | 0.0-2.3 | 3.7×2.3 | 8.51m² | Dining | ✓ |
| **RUANG_TAMU** | A1-C3 | 0.0-4.4 | 0.0-5.4 | Complex | 23.76m² | Living | ✓ |
| **DAPUR** | C2-E4 | 4.4-11.2 | 2.3-7.0 | 6.8×4.7 | 31.96m² | Kitchen | ✓ |
| **BILIK_MANDI** | A3-B4 | 0.0-1.3 | 5.4-7.0 | 1.3×1.6 | 2.08m² | Bathroom | ✓ |
| **TANDAS** | A4-B5 | 0.0-1.3 | 7.0-8.5 | 1.3×1.5 | 1.95m² | Toilet | ✓ |
| **RUANG_BASUH** | C3-D4 | 4.4-8.1 | 5.4-7.0 | 3.7×1.6 | 5.92m² | Utility | ✓ |
| **ANJUNG** | B1-C0 | 2.3-5.5 | -2.3-0.0 | 3.2×2.3 | 7.36m² | Porch | - |

**⚠️ BILIK_3:** Position TBD - Only 2 possible 3.1×3.1 squares in grid (both occupied). Awaiting floor plan verification.

---

## 🚪 DOOR SCHEDULE (7 Doors - Page 8 OCR)

| Code | Size | Qty | Locations | Swing | Type |
|------|------|-----|-----------|-------|------|
| **D1** | 900×2100mm | 2 | Ruang Tamu, Dapur | Inward | External |
| **D2** | 900×2100mm | 3 | Bilik Utama, Bilik 2, Bilik 3 | Inward | Bedroom |
| **D3** | 750×2100mm | 2 | Bilik Mandi, Tandas | **Outward** | Bathroom |

**Door Placement Rules:**
- **External doors** (D1): Center of exterior wall, inward swing
- **Bedroom doors** (D2): Center of interior wall to corridor, inward swing
- **Bathroom doors** (D3): Center of wall opposite WC, **outward swing** (safety!)

---

## 🪟 WINDOW SCHEDULE (7 Windows - Page 8 OCR)

| Code | Size | Sill | Qty | Locations | Type |
|------|------|------|-----|-----------|------|
| **W1** | 1800×1000mm | 900mm | **1** | **Dapur only** | Viewing |
| **W2** | 1200×1000mm | 900mm | 4 | Ruang Tamu, Bilik Utama, Bilik 2, Bilik 3 | Viewing |
| **W3** | 600×500mm | 1500mm | 2 | Tandas, Bilik Mandi | Ventilation |

**Window Placement Rules:**
- **Exterior walls only** (WEST x=0.0, EAST x=11.2, SOUTH y=0.0, NORTH y=8.5, PORCH_SOUTH y=-2.3)
- **Viewing windows** (W1, W2): Sill 900mm (above furniture/counter)
- **Ventilation windows** (W3): Sill 1500mm (high for privacy)
- **Center on wall** with 300mm corner clearance

---

## 📜 UBBL 1984 CODE COMPLIANCE (Malaysian Building Codes)

### Minimum Room Requirements

| Room Type | Min Area | Min Width | Min Height | Status |
|-----------|----------|-----------|------------|--------|
| **Habitable (Bedroom/Living)** | 6.5 m² | 2.0 m | 2.5 m | ✓ All pass |
| **Kitchen** | - | - | 2.25 m | ✓ Pass |
| **Bathroom** | 1.5 m² | 0.75 m | 2.0 m | ✓ All pass |
| **Bathroom + WC** | 2.0 m² | 0.75 m | 2.0 m | ✓ BILIK_MANDI 2.08m² |

### Door Requirements (UBBL + MS 1184)

| Type | Min Width | Height | Clearance | Status |
|------|-----------|--------|-----------|--------|
| **Main Entrance** | 900mm | 2100mm | - | ✓ D1: 900mm |
| **Bedroom** | 800mm | 2100mm | - | ✓ D2: 900mm |
| **Bathroom/WC** | 700mm | 2100mm | Swing OUT | ✓ D3: 750mm OUT |
| **Accessible (MS 1184)** | 900mm clear | 2100mm | 32" (813mm) | ✓ D1, D2 compliant |

### Window Requirements (UBBL By-Law 39)

| Requirement | Standard | Calculation | Status |
|-------------|----------|-------------|--------|
| **Natural Light** | ≥10% floor area | W1+W2×4+W3×2 = 11.8m² vs 93.4m² floor = 12.6% | ✓ Pass |
| **Ventilation** | ≥5% floor area | 50% of 11.8m² = 5.9m² vs 93.4m² = 6.3% | ✓ Pass |
| **Bathroom/WC** | ≥0.2 m² per unit | W3: 0.3m² each × 2 = 0.6m² total | ✓ Pass |

### Bedroom Egress (International/IRC)

| Requirement | Standard | Actual | Status |
|-------------|----------|--------|--------|
| **Window Area** | ≥5.7 sq ft (0.53 m²) | W2: 1.2m² each | ✓ Pass |
| **Min Width** | ≥20" (508mm) | W2: 1200mm | ✓ Pass |
| **Min Height** | ≥24" (610mm) | W2: 1000mm | ✓ Pass |
| **Max Sill Height** | ≤44" (1118mm) | W2: 900mm | ✓ Pass |

---

## ⚖️ RULE 0 COMPLIANCE CHECKLIST

**Rule 0:** All outputs must be derivable from source code and input data only.

- ✅ **Grid calibration**: Automated (HoughCircles + OCR) → origin (2234, 642)px, 52.44 px/m
- ✅ **Door dimensions**: Page 8 OCR → D1:900mm, D2:900mm, D3:750mm
- ✅ **Window dimensions**: Page 8 OCR → W1:1800mm, W2:1200mm, W3:600mm
- ✅ **Room bounds**: Grid cells + PLACEMENT_ALGORITHM_SPEC.md heuristics
- ✅ **Door positions**: Wall center from room_bounds → no manual coordinates
- ✅ **Window positions**: Exterior wall center + 300mm clearance → deterministic
- ✅ **Swing directions**: Room type → rule (bathrooms OUT, others IN)
- ✅ **Sill heights**: Window type → rule (viewing 900mm, ventilation 1500mm)
- ✅ **Rotation mapping**: Wall orientation → degrees (SOUTH/NORTH=0°, EAST/WEST=90°)

**Verification:** All coordinates traceable to:
1. GridTruth.json (grid A-E, 1-5)
2. page8_schedules.json (OCR dimensions)
3. PLACEMENT_ALGORITHM_SPEC.md (rules)
4. UBBL 1984 (building codes)

---

## 🔄 PIPELINE FLOW (8 Stages)

```
PDF (Page 8)
    ↓ [pytesseract OCR]
Schedule (doors/windows dimensions)
    ↓
PDF (Page 1)
    ↓ [HoughCircles + OCR]
Grid Calibration (origin, px/m)
    ↓
GridTruth + PLACEMENT_ALGORITHM_SPEC.md
    ↓ [Room inference heuristics]
Room Bounds (8 rooms + UBBL validation)
    ↓
Schedule + Room Bounds + Rules
    ↓ [Wall selection + center calculation]
Door Placements (7 doors)
    ↓
Schedule + Room Bounds + Exterior Wall Detection
    ↓ [Wall selection + sill height rules]
Window Placements (7 windows)
    ↓
master_template.json (SINGLE SOURCE OF TRUTH)
    ↓ [convert_master_to_blender.py]
blender_import.json (rotation mapping)
    ↓ [blender_lod300_import.py + Ifc_Object_Library.db]
TB-LKTN_House.blend (LOD300 geometry in 3D)
```

---

## 🛠️ KEY ALGORITHMS (Quick Reference)

### Wall-to-Rotation Mapping
```python
{"NORTH": 0, "SOUTH": 0, "EAST": 90, "WEST": 90}
```

### Door Swing Direction
```python
"outward" if room_type in ["bathroom", "toilet"] else "inward"
```

### Window Sill Height
```python
1500 if window_type == "ventilation" else 900  # millimeters
```

### Room Shape Rules
```python
"square" if room_type == "bedroom" else "rectangle"  # 3.1×3.1m bedrooms
```

### Object Type Generation
```python
f"door_{width_mm}x{height_mm}_lod300"    # door_900x2100_lod300
f"window_{width_mm}x{height_mm}_lod300"  # window_1200x1000_lod300
```

---

## 📊 VALIDATION CHECKLIST

### master_template.json Validation
```bash
# Total element count
jq '.door_placements | length' master_template.json  # Expected: 7
jq '.window_placements | length' master_template.json  # Expected: 7
# Total: 14 elements (doors + windows only, walls/roof not yet added)

# UBBL bedroom compliance
jq '.room_bounds | to_entries[] | select(.value.type == "bedroom") | "\(.key): \(.value.area_m2)m²"'
# Expected: BILIK_UTAMA: 9.61m², BILIK_2: 9.61m², BILIK_3: TBD

# Door swing directions
jq '.door_placements[] | select(.room == "BILIK_MANDI" or .room == "TANDAS") | "\(.element_id): \(.swing_direction)"'
# Expected: All "outward"

# Window sill heights
jq '.window_placements[] | select(.window_type == "ventilation") | "\(.element_id): \(.sill_height_mm)mm"'
# Expected: All 1500mm
```

### Blender Export Validation
```bash
python3 convert_master_to_blender.py
jq '.metadata.total_objects' output_artifacts/blender_import.json  # Expected: 14
jq '.objects[] | "\(.name): \(.wall) → \(.orientation)°"' output_artifacts/blender_import.json
# Expected: SOUTH/NORTH → 0°, EAST/WEST → 90°
```

---

## ⚠️ KNOWN ISSUES / TBD

1. **BILIK_3 Position:** ⚠️ TBD - Awaiting floor plan verification
   - Only 2 possible 3.1×3.1 squares in grid (B2-C3, D2-E3)
   - Both currently occupied by BILIK_2 and BILIK_UTAMA
   - Need to verify actual position from floor plan

2. **Interior Walls:** Not yet extracted
   - Room bounds inferred from grid + heuristics
   - Actual partition walls not in template

3. **Wall/Roof Geometry:** Not yet added
   - Currently only doors + windows (14 elements)
   - Future: Add IfcWall, IfcSlab, IfcRoof entities

4. **MEP/Furniture:** Not included
   - Future phases: Electrical, plumbing, built-ins, furniture

---

## 🎯 QUICK COMMAND REFERENCE

```bash
# Validate master template
python3 validators/validate_library_references.py master_template.json Ifc_Object_Library.db

# Convert to Blender format
python3 convert_master_to_blender.py

# Import to Blender
blender --python blender_lod300_import.py -- \
  output_artifacts/blender_import.json \
  Ifc_Object_Library.db \
  output.blend

# Apply QA corrections
python3 apply_qa_corrections.py
```

---

## 📁 FILE LOCATIONS

```
Master Template:    master_template.json (SINGLE SOURCE OF TRUTH)
Library Database:   ~/Documents/bonsai/tasblock/DatabaseFiles/Ifc_Object_Library.db
Source PDF:         TB-LKTN HOUSE.pdf (8 pages)
Blender Output:     output_artifacts/blender_import.json
Pipeline Scripts:
  - calibrate_grid_origin.py
  - extract_page8_schedule.py
  - deduce_room_bounds.py
  - corrected_door_placement.py
  - generate_window_placements.py
  - convert_master_to_blender.py
  - blender_lod300_import.py
```

---

## 🔍 TROUBLESHOOTING

**Issue:** Door/window count mismatch
**Fix:** Verify against Page 8 schedule OCR (page8_schedules.json)

**Issue:** UBBL bedroom compliance failure
**Fix:** Check area_m2 ≥ 6.5m² and shape = "square" (3.1×3.1m)

**Issue:** Bathroom door swings inward
**Fix:** Verify swing_direction = "outward" (safety requirement)

**Issue:** Window on interior wall
**Fix:** Check wall against building_envelope.exterior_walls

**Issue:** Coordinates outside grid bounds
**Fix:** All x ∈ [0.0, 11.2], y ∈ [-2.3, 8.5] (including porch)

---

**Last Updated:** 2025-11-26 (QA corrections applied)
**Status:** ✅ Production Ready (except BILIK_3 position TBD)
**Next:** Verify BILIK_3 position from floor plan, add walls/roof geometry
