# Next Session: Start Here

**Date:** 2025-11-16
**Status:** Database schema fixed, Preview mode geometry invisible

---

## What We Fixed Today

✅ **Database schema now matches working IFC database exactly:**
- element_transforms: PRIMARY KEY = guid (was id)
- base_geometries: PRIMARY KEY = geometry_hash (was id)
- element_instances: Table created (was missing!)
- element_geometry: Corrected to VIEW (was wrong table)
- Schema verified by systematic comparison with `/home/red1/Documents/bonsai/8_IFC/enhanced_federation.db`

✅ **The core query works:**
```bash
python3 /home/red1/Documents/bonsai/2Dto3D/Scripts/simple_truth.py
# Returns: "THE QUERY WORKS - Element WILL render in Preview mode"
```

---

## Current Problem

**Preview mode loads the data BUT geometry is invisible/too far away**

**Evidence:**
- Console log shows: "✅ BBOX VISUALIZATION ENABLED - 15,257 elements"
- GPU batches created successfully (278,496 vertices for Seating alone)
- User reports: "two white boxes visible in the distance"
- **BUT:** Viewport appears mostly empty

**Root Cause Discovery:**

**Working IFC Database:**
```
Building coordinates: X: 85m to 154m (70m wide)
Building center: ~120m from origin
```

**Our DXF Database:**
```
Building coordinates: X: 0m to 5,383m (5.4km wide!)
Building center: 2,691m from origin (2.7 KILOMETERS away!)
```

**The Issue:** Our building starts at origin (0,0,0) and extends 5.4km, so its CENTER is 2.7km away. The working IFC building is centered around 120m from origin.

When Preview mode frames the viewport, it centers on (2691m, 1641m) which is too far for comfortable viewing, or the viewport clip plane cuts it off.

---

## What To Do Next

**Option 1: Apply global_offset to center building at origin**
- Set `global_offset` to (-2691, -1641, -27)
- This shifts building center from (2691, 1641, 27) to (0, 0, 0)
- Matches working IFC pattern of centering building

**Option 2: Investigate why working IFC renders at 120m but ours doesn't at 2.7km**
- Is there a viewport clip plane issue?
- Is there a scale threshold in Preview mode?
- Load working IFC in Preview and measure actual viewport behavior

**Option 3: Scale down the entire building**
- If 5.4km is too large for Blender viewport
- Scale all coordinates by 0.1 or 0.01
- But this breaks real-world scale

---

## Key Files

**Working Reference:**
- `/home/red1/Documents/bonsai/8_IFC/enhanced_federation.db` - SINGLE SOURCE OF TRUTH

**Our Database:**
- `/home/red1/Documents/bonsai/2Dto3D/Terminal1_3D_FINAL.db` - Schema correct, positioning issue

**Test Scripts:**
- `Scripts/simple_truth.py` - Proves query works
- `Scripts/compare_preview_loads.py` - Compares what both DBs load
- `Scripts/compare_databases.py` - Full schema comparison

**Latest Console Log:**
- `/home/red1/Documents/bonsai/consolelogs/console_20251116_165149.log`
- Shows Preview loaded successfully but geometry at wrong location

---

## Recommended Next Step

**Load the working IFC database in Preview mode first:**
1. In Blender → Federation → Load `/home/red1/Documents/bonsai/8_IFC/enhanced_federation.db`
2. Click Preview
3. Observe:
   - Where is the viewport camera positioned?
   - What does global_offset contain?
   - How far from origin is the geometry?
   - What does "working" actually look like?

**Then apply the same pattern to our DXF database.**

Don't modify our database further until we understand what "working" actually means.

---

## Stop Doing

❌ Changing element sizes (already tried 1×, 77×, 100× - not the issue)
❌ Changing R-tree units (already correct - meters)
❌ Changing schema (already matches working DB exactly)
❌ Guessing at solutions without data

## Start Doing

✅ Load working database to see actual behavior
✅ Measure viewport camera position when working DB loads
✅ Compare global_offset values
✅ Apply same offset pattern to our DB

---

**The database is fundamentally correct. The issue is coordinate positioning/offset, not schema or data.**
