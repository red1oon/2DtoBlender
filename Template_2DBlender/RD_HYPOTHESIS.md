# R&D Hypothesis - Text Extraction Coordinate Problem

## 🔬 Scientific Analysis Framework

### Current Problem
- **Symptom**: 360 out of 1149 text items (31%) have (0,0) coordinates
- **Impact**: Critical labels (DISCHARGE, dimensions) unusable for calibration
- **Pattern**: Specific text types affected (annotations vs regular text)

---

## 📊 Data Analysis

### What We Know:
1. **789 text items (69%) have proper coordinates** - Regular text extraction works
2. **360 text items (31%) have (0,0) coordinates** - Specific extraction method failing
3. **Affected items include**:
   - DISCHARGE labels
   - Dimension values (1300, 1600, 3100, 3700)
   - Floor plan labels
   - Schedule titles

### Working vs Not Working:
| Text | Coordinates | Type |
|------|-------------|------|
| "G2" | (111.04, 69.28) | ✅ Grid label |
| "A", "B", "C" | Valid | ✅ Grid label |
| "W3" | (178.72, 166.47) | ✅ Window label |
| "DISCHARGE" | (0.0, 0.0) | ❌ Annotation |
| "1300" | (0.0, 0.0) | ❌ Dimension |
| "1. FLOOR PLAN" | (0.0, 0.0) | ❌ Title |

---

## 🧪 HYPOTHESIS

### Primary Hypothesis:
**PDF annotations (Type 3 fonts, form fields, or AutoCAD SHX text) are stored differently than regular text objects.**

### Supporting Evidence:
1. pdfplumber extracts regular text via `extract_words()` ✅
2. Annotations need special handling via `page.annots`
3. Current code tries `annot.get('x0', 0)` but annotations might use `rect[]` field
4. Fallback to 0 when field not found

### Mathematical Model:
```
P(coordinates) = {
    0.69 if regular_text (extract_words)
    0.00 if annotation (current method)
    ?.?? if annotation (corrected method)
}
```

---

## 🔍 Minimal POC Test Plan

### Test 1: Understand PDF Structure
```python
# What fields do annotations actually have?
for annot in page.annots:
    print(annot.keys())  # See actual structure
```

### Test 2: Extract Methods Comparison
```python
# Method A: Regular text
words = page.extract_words()

# Method B: Annotations with rect
annots_rect = [a for a in page.annots if 'rect' in a]

# Method C: Annotations with bbox
annots_bbox = [a for a in page.annots if 'bbox' in a]

# Compare success rates
```

### Test 3: Coordinate System Verification
```python
# Are annotation coordinates in same space as text?
# PDF has multiple coordinate systems:
# - User space (0,0 at bottom-left)
# - Device space (0,0 at top-left)
# - Annotation space (might be different)
```

---

## 📐 Mathematical Validation

### Coordinate Transformation Required:
If annotation space ≠ page space:
```
x_page = x_annot * scale_x + offset_x
y_page = height - (y_annot * scale_y + offset_y)  # Flip Y-axis
```

### Success Criteria:
1. **No (0,0) coordinates** for critical labels
2. **Spatial consistency**: Grid A < Grid B < Grid C (x-coordinates)
3. **Dimension clustering**: Similar Y for horizontal dimensions

---

## 🎯 Proposed Solution Path

### Phase 1: Diagnosis (POC)
1. Extract sample page with all methods
2. Identify which extraction method each text type needs
3. Map field names to coordinate extraction

### Phase 2: Implementation
1. Multi-method extraction with appropriate fallbacks
2. Coordinate validation (reject 0,0 for critical labels)
3. Coordinate transformation if needed

### Phase 3: Validation
1. Mathematical checks (perimeter closure)
2. Relative position checks (A before B)
3. Dimension consistency (sum of parts = whole)

---

## ⚗️ Research References

### PDF Specification (ISO 32000)
- Section 12.5: Annotations
- Section 9.4: Text Objects
- Section 8.3: Coordinate Systems

### pdfplumber Documentation
- `extract_words()`: For regular text
- `page.annots`: For annotations
- `page.chars`: For character-level extraction

### Alternative Libraries to Research
- PyMuPDF (fitz): Different annotation handling
- pdfrw: Low-level PDF manipulation
- pdfminer.six: Alternative extraction pipeline

---

## 📊 Expected Outcome

With proper extraction:
```
Before: 360/1149 (31%) with (0,0)
After:  0/1149 (0%) with (0,0) for critical labels
        <50/1149 (<5%) with (0,0) for non-critical items
```

This enables:
1. ✅ Reliable calibration (using real DISCHARGE positions)
2. ✅ Accurate dimensions (using actual annotation positions)
3. ✅ Closed perimeter (all walls connected)
4. ✅ Mathematical validation possible