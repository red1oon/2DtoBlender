# Known Issues - Rule 0 Derivation Logic

## 🔴 CRITICAL: Grid Derivation Returns Wrong Values

**Status:** Code pushed (commit e4e5488) but derivation logic has bugs

### Issue 1: Vertical Grids in Reverse Order
```
DERIVED:  5=0.0, 4=0.73, 3=1.5, 2=3.0, 1=4.12
EXPECTED: 1=0.0, 2=2.3, 3=5.4, 4=7.0, 5=8.5
```
**Cause:** annotation_derivation.py:243-244 sorts by PDF y-position
**Fix:** Need to sort by label order (1,2,3,4,5) not PDF coordinate

### Issue 2: Horizontal Grid Spacing Wrong
```
DERIVED:  B=1.5, C=3.56, D=7.83, E=11.42
EXPECTED: B=1.3, C=4.4, D=8.1, E=11.2
```
**Cause:** Scale calculation wrong or dimension text matching wrong
**Fix:** Debug derive_scale_from_dimensions() - which dimension matched?

### Impact
- Building depth: 4.12m instead of 8.5m
- Room bounds: All wrong sizes
- Furniture placement: Outside room bounds
- Walls: Going diagonal instead of orthogonal

### Files Affected
- src/core/annotation_derivation.py (lines 243-244 sorting logic)
- All downstream: gridtruth_generator.py, post_processor.py, etc.

### Test Command
```bash
python3 src/core/annotation_derivation.py output_artifacts/TB-LKTN_HOUSE_ANNOTATION_FROM_2D.db
```

### Expert Needed
Derivation logic needs fixing before continuing. Current code available at:
https://github.com/red1oon/2DtoBlender/tree/main/src/core
