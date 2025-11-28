# Known Issues - Rule 0 Derivation Logic

## 🟡 PARTIAL FIX: Grid Derivation Still Has Spacing Errors

**Status:** Major fixes pushed (commit cec1a16) - grids in correct order, but spacing still wrong

### ✅ FIXED: Vertical Grids No Longer Reversed
```
BEFORE (e4e5488): 5=0.0, 4=0.73, 3=1.5, 2=3.0, 1=4.12 (REVERSED)
AFTER (cec1a16):  1=0.0, 2=3.1, 3=7.27, 4=9.43, 5=11.45 (correct order)
EXPECTED:         1=0.0, 2=2.3, 3=5.4, 4=7.0, 5=8.5
```
**Fixed:** annotation_derivation.py now sorts by label (1,2,3,4,5) and reverses Y calculation

### ✅ PARTIAL FIX: Horizontal Grid B Position Correct
```
BEFORE (e4e5488): B=1.5, C=3.56, D=7.83, E=11.42 (wrong dimension matched)
AFTER (cec1a16):  B=1.3, C=3.09, D=6.78, E=9.9 (matches "1300mm" correctly)
EXPECTED:         B=1.3, C=4.4, D=8.1, E=11.2
```
**Fixed:** Dimension matching now filters out large dimensions (>5m) and prioritizes first grid pairs

### ❌ REMAINING ISSUE: Grid Spacing Still Wrong
Despite matching correct dimensions:
- X: Matched "1300mm" between A-B ✓
- Y: Matched "3100mm" between 1-2 (but PDF has "2300mm" dimension)
- Building size: 8.4m × 10.0m (expected ~11.2m × 8.5m)

**Hypothesis:** Grid clustering is selecting wrong grid set from multi-page PDF (8 pages total).
PDF has duplicate grid labels across pages (floor plan, elevations, sections). The clustering
algorithm may be mixing grids from different views.

**Next Steps:**
1. Debug grid clustering to ensure selecting MAIN FLOOR PLAN grids only
2. Check if page=1 filter is correct (main plan might be on different page)
3. Add debug output showing which grid cluster was selected and why

### Test Command
```bash
python3 src/core/annotation_derivation.py output_artifacts/TB-LKTN_HOUSE_ANNOTATION_FROM_2D.db
```

### Files Affected
- src/core/annotation_derivation.py (grid clustering lines 62-83, 103-124)
