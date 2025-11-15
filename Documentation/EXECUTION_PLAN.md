# Execution Plan - DWG to Database POC

**Date:** November 12, 2025
**Status:** Ready to Execute
**Approach:** Sampling-first for fast validation

---

## Summary

All scripts and documentation are ready. The **recommended approach** is to use **sampling** for fast iteration, then scale to full conversion once validated.

---

## Execution Path

### PATH A: Quick Validation (Recommended) ⚡

**Best for:** Fast feedback, iterative development

```bash
# 1. Install ODA (one-time, manual)
sudo dpkg -i ODAFileConverter_*.deb

# 2. Convert DWG to DXF (~2 min)
./convert_dwg_to_dxf.sh

# 3. Quick smoke test (~5 min)
./quick_test.sh 100

# 4. Statistical sample (~15 min)
./quick_test.sh 1000

# 5. If >70% accuracy, proceed to full conversion
./run_conversion.sh
```

**Total time:** ~25 minutes (vs 2+ hours for full conversion first)

**Advantages:**
- ✅ Fail fast if templates don't work
- ✅ Quick iteration on template refinement
- ✅ Validate concept before big time investment
- ✅ Statistical confidence with 1,000 samples (±3% margin)

---

### PATH B: Full Conversion (Traditional)

**Best for:** Final validation, production database

```bash
# 1. Install ODA (one-time, manual)
sudo dpkg -i ODAFileConverter_*.deb

# 2. Convert DWG to DXF (~2 min)
./convert_dwg_to_dxf.sh

# 3. Full conversion (~1-2 hours)
./run_conversion.sh

# 4. Validation (~1 min)
python database_comparator.py Generated_Terminal1.db \
    ~/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db \
    validation_report.md
```

**Total time:** ~2 hours

**Risk:** If templates fail, you wasted 2 hours

---

## Recommended Workflow

### Phase 1: Initial Validation (Day 1, ~30 min)

1. **Install ODA File Converter** (manual)
   ```bash
   # Download from: https://www.opendesign.com/guestfiles/oda_file_converter
   sudo dpkg -i ODAFileConverter_*.deb
   ```

2. **Convert DWG → DXF**
   ```bash
   cd /home/red1/Documents/bonsai/RawDWG
   ./convert_dwg_to_dxf.sh
   ```
   Expected output: `2. BANGUNAN TERMINAL 1 .dxf` (~20-30MB)

3. **Smoke Test** (100 elements)
   ```bash
   ./quick_test.sh 100
   ```

   **Check:**
   - ✅ Does it parse without errors?
   - ✅ Do ANY templates match?
   - ✅ Is output database valid?

   **If FAIL:** Fix parsing issues, retry smoke test

4. **Statistical Sample** (1,000 elements)
   ```bash
   ./quick_test.sh 1000
   ```

   **Check:**
   - ✅ All 8 disciplines present?
   - ✅ Accuracy > 50% per discipline?
   - ✅ IFC classes matching?

   **Review:** `Generated_Terminal1_SAMPLE.db`

---

### Phase 2: Template Refinement (Day 1-2, iterative)

**If Phase 1 accuracy is 50-70%:**

1. **Analyze failures**
   ```bash
   sqlite3 Generated_Terminal1_SAMPLE.db \
       "SELECT discipline, ifc_class, COUNT(*)
        FROM elements_meta
        GROUP BY discipline, ifc_class"
   ```

2. **Identify issues:**
   - Which disciplines have low counts?
   - Which IFC classes are missing?
   - Are layer names not matching?
   - Are block names different than expected?

3. **Refine templates:**
   - Update matching rules in `dxf_to_database.py`
   - Add new layer patterns
   - Add new block name patterns
   - Adjust spatial offsets

4. **Retest** (15 min iteration)
   ```bash
   ./quick_test.sh 1000
   ```

5. **Repeat until >70% accuracy**

**Time per iteration:** ~15 minutes
**Expected iterations:** 3-5
**Total refinement time:** 1-2 hours

---

### Phase 3: Full Validation (Day 2-3, ~2 hours)

**Once sample accuracy >70%:**

1. **Run full conversion**
   ```bash
   ./run_conversion.sh
   ```

   Expected:
   - Processing time: 1-2 hours
   - Output: `Generated_Terminal1.db` (~50-150MB)
   - Elements: 25,000-40,000 (vs 49,059 original)

2. **Compare with original**
   ```bash
   PYTHONPATH=/home/red1/Projects/IfcOpenShell/src \
       ~/blender-4.5.3/4.5/python/bin/python3.11 \
       database_comparator.py \
       Generated_Terminal1.db \
       ~/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db \
       validation_report.md
   ```

3. **Review validation report**
   - Element counts by discipline
   - IFC class distribution
   - Accuracy percentages
   - Success/fail criteria

---

## Decision Points

### After Smoke Test (100 elements):

**If <30% match:**
- ❌ Major issues with parsing or template matching
- 🔧 Fix: Check layer names, block names, entity types
- 🔄 Retry smoke test

**If 30-60% match:**
- ⚠️ Templates need refinement
- 🔧 Fix: Adjust matching rules, add patterns
- 🔄 Proceed to statistical sample

**If >60% match:**
- ✅ Good start!
- ➡️ Proceed to statistical sample

---

### After Statistical Sample (1,000 elements):

**If <50% accuracy:**
- ❌ Templates don't capture patterns well
- 🔧 Fix: Major template refinement needed
- 📊 Analyze: Which disciplines/classes failing?
- 🔄 Iterate on templates, retest sample

**If 50-70% accuracy:**
- ⚠️ Partial success, needs refinement
- 🔧 Fix: Refine specific templates
- 📊 Analyze: Focus on failing disciplines
- 🔄 Iterate 2-3 times on sample

**If >70% accuracy:**
- ✅ POC validated!
- ➡️ Proceed to full conversion
- 🎯 Goal achieved for POC

---

### After Full Conversion:

**If ≥70% accuracy:**
- ✅ **POC SUCCESS!**
- 📝 Document findings
- 🚀 Proceed to Phase 3 (Bonsai integration)
- 🔄 Apply templates to Terminal 2, 3

**If <70% accuracy:**
- ⚠️ Sample was optimistic (statistical variance)
- 🔧 Refine templates further
- 🔄 Re-run full conversion
- 📊 Target 75-80% to account for variance

---

## Time Estimates

### Optimistic Path (Everything works):
- Install ODA: 10 min
- Convert DWG: 2 min
- Smoke test: 5 min
- Sample test: 15 min
- Full conversion: 2 hours
- **Total: ~2.5 hours**

### Realistic Path (Some refinement):
- Install ODA: 10 min
- Convert DWG: 2 min
- Smoke test: 5 min
- Sample test: 15 min
- Template refinement: 1-2 hours (3-5 iterations × 15 min)
- Full conversion: 2 hours
- **Total: ~4-5 hours**

### Pessimistic Path (Major template work):
- Install ODA: 10 min
- Convert DWG: 2 min
- Smoke test: 5 min
- Sample test: 15 min
- Template refinement: 4-6 hours (many iterations)
- Full conversion: 2 hours
- **Total: ~7-9 hours (spread over 2-3 days)**

---

## Success Criteria

### Minimum (POC Pass):
- ✅ DXF parsing works
- ✅ >70% accuracy overall
- ✅ All 8 disciplines present
- ✅ Database schema matches original

### Target (Production Ready):
- ✅ >85% accuracy overall
- ✅ >80% per discipline
- ✅ IFC class distribution >90% match
- ✅ Spatial offsets correct

---

## Files and Commands Reference

### Key Scripts:
```bash
./convert_dwg_to_dxf.sh          # DWG → DXF conversion
./quick_test.sh [sample_size]    # Fast sampling test
./run_conversion.sh              # Full conversion pipeline
database_comparator.py           # Validation tool
```

### Key Databases:
```
FullExtractionTesellated.db      # Original (327MB, 49,059 elements)
template_library.db              # Templates (248KB, 44 templates)
Generated_Terminal1_SAMPLE.db    # Sample output (testing)
Generated_Terminal1.db           # Full output (final)
```

### Key Docs:
```
README_QUICKSTART.md             # Detailed instructions
SAMPLING_STRATEGY.md             # Why sampling works
STATUS.md                        # Current project status
INSTALL_ODA_CONVERTER.md         # ODA setup guide
```

---

## What to Do Next

**IMMEDIATE NEXT STEP:**

1. **Install ODA File Converter** (user action required)
   - Download: https://www.opendesign.com/guestfiles/oda_file_converter
   - Install: `sudo dpkg -i ODAFileConverter_*.deb`

2. **Then run:**
   ```bash
   cd /home/red1/Documents/bonsai/RawDWG
   ./convert_dwg_to_dxf.sh
   ./quick_test.sh 1000
   ```

3. **Review results and decide:**
   - >70%? → Run full conversion
   - 50-70%? → Refine templates, retest
   - <50%? → Investigate issues

---

## Expected Outcome

**If templates work (>70% accuracy):**

This proves:
- ✅ Templates capture reusable BIM patterns
- ✅ 2D DWG can be converted to structured 3D database
- ✅ Approach can scale to Terminal 2, 3, etc.
- ✅ No manual 3D modeling needed

**Value:**
- Automate BIM generation from 2D drawings
- Reuse templates across projects
- Faster project delivery
- Reduced manual modeling effort

**Next steps:**
- Phase 3: Bonsai UI integration
- Multi-terminal testing
- Template library expansion
- Production deployment

---

**Last Updated:** November 12, 2025
**Status:** Ready to Execute
**Blocker:** ODA File Converter installation (manual)
**Recommended Path:** Sampling-first approach
