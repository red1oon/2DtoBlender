# Testing Routine - 2Dto3D Workflow

**CRITICAL: Always start with a FRESH database for testing!**

---

## 🔄 Proper Testing Cycle

### **Step 1: Generate FRESH Database**

```bash
# Start from scratch - no contamination
python3 Scripts/dxf_to_database.py \
    "SourceFiles/TERMINAL1DXF/Terminal1.dxf" \
    Fresh_Terminal1.db \
    Templates/terminal_base_v1.0/template_library.db

# Generate 3D geometry
python3 Scripts/generate_3d_geometry.py Fresh_Terminal1.db
```

### **Step 2: Run Master Routing (ONCE ONLY)**

```bash
# Generate code-compliant sprinkler grid + route pipes
python3 Scripts/master_routing.py Fresh_Terminal1.db \
    --discipline FP \
    --generate-devices
```

**⚠️ IMPORTANT:** Only run this ONCE per database. Multiple runs will stack results!

### **Step 3: Test in Viewport (USER's part)**

```bash
# Open in Blender manually
~/blender-4.5.3/blender

# Then: File → Import → Bonsai Federation
# Select: Fresh_Terminal1.db
```

**Visual checks:**
- ✅ Sprinklers in grid pattern (not clustered lines)
- ✅ Pipes routing along corridors
- ✅ Branch lines connecting to sprinklers

### **Step 4: BonsaiTester Validation (Automated)**

```bash
# Run thorough database validation (avoids opening viewport)
~/Documents/bonsai/BonsaiTester/bonsai-test Fresh_Terminal1.db \
    --tier 2 \
    --output logs/bonsai_test_results.txt
```

**Validates:**
- Database schema integrity
- Geometry completeness
- Spatial index correctness
- IFC compliance

---

## ❌ Common Mistakes

### **DON'T: Run on same DB multiple times**
```bash
# This is WRONG - contaminated results!
python3 Scripts/master_routing.py Terminal1.db --generate-devices  # First run
python3 Scripts/master_routing.py Terminal1.db --generate-devices  # Second run (stacks!)
```

**Result:** Duplicate pipes, mixed sprinklers (old DXF + new generated)

### **DON'T: Let Claude open Blender**
- Viewport testing is USER's responsibility
- Claude should only prepare the database

### **DO: Fresh DB for each test**
```bash
# Proper way
rm -f Test_Terminal1.db  # Clean slate
python3 Scripts/dxf_to_database.py ...
python3 Scripts/generate_3d_geometry.py ...
python3 Scripts/master_routing.py ... --generate-devices  # Once!
```

---

## 🎯 Expected Results

### **Before (DXF only):**
- 219 sprinklers (clustered in lines from architect's drawing)
- 866 pipes (from DXF)
- ❌ Not code-compliant
- ❌ Uneven distribution

### **After (--generate-devices):**
- 273 sprinklers (21×13 grid, evenly distributed)
- 52 trunk segments (DN 100 / 4" main lines)
- 151 branch lines (DN 50 & DN 25 connections)
- ✅ NFPA 13 compliant coverage (10.98 m²/sprinkler vs 12.08 m² max)
- ✅ Grid pattern (not lines!)

---

## 📊 Quick Validation Queries

### **Check what's in database:**
```bash
sqlite3 Fresh_Terminal1.db "SELECT ifc_class, COUNT(*) FROM elements_meta GROUP BY ifc_class;"
```

### **Check sprinkler sources:**
```bash
sqlite3 Fresh_Terminal1.db "SELECT element_name, COUNT(*) FROM elements_meta WHERE discipline='FP' AND inferred_shape_type='sprinkler' GROUP BY element_name;"
```

**Expected output (fresh DB + generated):**
```
FP_IfcBuildingElementProxy|219    ← Original DXF sprinklers (to be replaced in future)
Generated_Sprinkler|273            ← NEW grid sprinklers
```

**Note:** Current implementation adds generated sprinklers but doesn't remove DXF ones yet. Future enhancement: replace DXF sprinklers entirely.

### **Check pipes:**
```bash
sqlite3 Fresh_Terminal1.db "SELECT COUNT(*) FROM elements_meta WHERE element_name LIKE 'Trunk%' OR element_name LIKE 'Branch%';"
```

**Expected:** ~203 pipe elements (52 trunk segments + 151 branches)

---

## 🔧 Troubleshooting

### **Problem: Too many elements in database**
**Cause:** Multiple runs on same database
**Solution:** Start fresh (Step 1)

### **Problem: Sprinklers still clustered in viewport**
**Cause:** Looking at old DXF sprinklers, not generated ones
**Solution:** Filter in Blender by `element_name = 'Generated_Sprinkler'`

### **Problem: No pipes visible**
**Cause:** Routing didn't export to database
**Solution:** Check `base_geometries` table has entries for trunk/branch lines

---

## 📝 Workflow Summary

```
Fresh DXF → dxf_to_database.py → DB (walls, doors, DXF sprinklers)
                ↓
         generate_3d_geometry.py → 3D meshes added
                ↓
  master_routing.py --generate-devices → Grid sprinklers generated
                                      → Trunk lines routed
                                      → Branch lines connected
                                      → All exported to DB
                ↓
          USER tests in Blender → Visual verification
                ↓
         BonsaiTester validates → Automated checks
```

---

**Last Updated:** Nov 17, 2025
**Version:** 1.0 (PlacementGenerator integrated)
