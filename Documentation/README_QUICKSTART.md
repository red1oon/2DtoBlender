# Quick Start Guide - DWG to Database POC

**Status:** Phase 2 - Ready to convert DWG file
**Date:** November 12, 2025

---

## Overview

This proof-of-concept demonstrates that 2D DWG files can be converted to structured BIM databases using **hindsight-derived templates** from existing 3D models.

**Goal:** Generate `Generated_Terminal1.db` from Terminal 1 DWG and achieve 70%+ accuracy vs. the original `FullExtractionTesellated.db`.

---

## Prerequisites

✅ **Completed:**
- Template library extracted (44 templates)
- Spatial offsets analyzed
- Parser and converter scripts created
- Comparison script created

⏳ **Pending:**
- ODA File Converter installation (manual step required)
- DWG→DXF conversion

---

## Step-by-Step Instructions

### STEP 1: Install ODA File Converter

**Manual installation required:**

1. Download ODA File Converter:
   - Visit: https://www.opendesign.com/guestfiles/oda_file_converter
   - Select: **Linux x64**
   - Download: `ODAFileConverter_*.deb` (~50-100MB)

2. Install:
   ```bash
   cd ~/Downloads
   sudo dpkg -i ODAFileConverter_*.deb

   # If dependencies missing:
   sudo apt-get install -f
   ```

3. Verify:
   ```bash
   which ODAFileConverter
   # Should output: /usr/bin/ODAFileConverter
   ```

**See also:** `INSTALL_ODA_CONVERTER.md` for detailed instructions

---

### STEP 2: Convert DWG to DXF

Once ODA File Converter is installed:

```bash
cd /home/red1/Documents/bonsai/RawDWG
./convert_dwg_to_dxf.sh
```

**What it does:**
- Converts `2. BANGUNAN TERMINAL 1 .dwg` → `2. BANGUNAN TERMINAL 1 .dxf`
- Uses ACAD2018 DXF format (compatible with ezdxf)
- Takes ~1-2 minutes for 14MB file

**Expected output:**
```
✓ Conversion successful!
Output file: /home/red1/Documents/bonsai/RawDWG/2. BANGUNAN TERMINAL 1 .dxf
File size: ~20-30MB
```

---

### STEP 3: Run Full Conversion Pipeline

```bash
cd /home/red1/Documents/bonsai/RawDWG
./run_conversion.sh
```

**What it does:**
1. Parses DXF file (extract entities, layers, blocks)
2. Matches entities to templates
3. Generates `Generated_Terminal1.db` with same schema as original
4. Shows quick statistics

**Expected output:**
```
✓ DXF parsing complete
✓ Database generation complete
✓ Conversion Pipeline Complete!

Generated database: Generated_Terminal1.db
Size: ~50-100MB
Total elements: ~25,000-40,000
```

**Logs saved to:**
- `/tmp/dxf_parse.log` - DXF parsing log
- `/tmp/dxf_to_db.log` - Conversion log

---

### STEP 4: Validate Results

```bash
cd /home/red1/Documents/bonsai/RawDWG

PYTHONPATH=/home/red1/Projects/IfcOpenShell/src \
    ~/blender-4.5.3/4.5/python/bin/python3.11 \
    database_comparator.py \
    Generated_Terminal1.db \
    ~/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db \
    validation_report.md
```

**What it does:**
- Compares element counts by discipline
- Compares IFC class distribution
- Calculates accuracy percentages
- Generates detailed report

**Success criteria:**
- ✅ Overall accuracy > 70%
- ✅ All 8 disciplines present
- ✅ Average discipline accuracy > 70%

**Report saved to:** `validation_report.md`

---

## File Structure

```
/home/red1/Documents/bonsai/RawDWG/
├── 2. BANGUNAN TERMINAL 1 .dwg        ← Input DWG file (14MB)
├── 2. BANGUNAN TERMINAL 1 .dxf        ← Converted DXF (created by Step 2)
├── Generated_Terminal1.db             ← Generated database (created by Step 3)
│
├── Terminal1_Project/
│   └── Templates/
│       └── terminal_base_v1.0/
│           ├── template_library.db    ← 44 templates with spatial offsets
│           ├── OFFSET_ANALYSIS.md     ← Z-height analysis report
│           └── metadata.json
│
├── Scripts/
│   ├── dwg_parser.py                  ← DXF parser (uses ezdxf)
│   ├── dxf_to_database.py             ← DXF→Database converter
│   ├── database_comparator.py         ← Validation tool
│   ├── extract_templates.py           ← (Phase 1, already run)
│   └── extract_spatial_offsets.py     ← (Phase 1, already run)
│
├── convert_dwg_to_dxf.sh              ← Step 2 script
├── run_conversion.sh                  ← Step 3 script
│
├── Documentation/
│   ├── CURRENT_APPROACH.md            ← Conversion methodology
│   ├── OFFSET_TEMPLATE_EXAMPLE.md     ← How spatial offsets work
│   └── INSTALL_ODA_CONVERTER.md       ← ODA installation guide
│
└── validation_report.md               ← Validation results (created by Step 4)
```

---

## Quick Reference Commands

### Check template library:
```bash
sqlite3 Terminal1_Project/Templates/terminal_base_v1.0/template_library.db \
    "SELECT template_name, ifc_class, instance_count
     FROM element_templates
     ORDER BY instance_count DESC
     LIMIT 10"
```

### Check generated database:
```bash
sqlite3 Generated_Terminal1.db \
    "SELECT discipline, COUNT(*) as count
     FROM elements_meta
     GROUP BY discipline"
```

### Check original database:
```bash
sqlite3 ~/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db \
    "SELECT discipline, COUNT(*) as count
     FROM elements_meta
     GROUP BY discipline"
```

---

## Troubleshooting

### "ODAFileConverter: command not found"
- ODA File Converter not installed
- Follow STEP 1 instructions
- Or see: `INSTALL_ODA_CONVERTER.md`

### "DXF file not found"
- Run STEP 2 first: `./convert_dwg_to_dxf.sh`
- Check if DWG file exists: `ls -lh "2. BANGUNAN TERMINAL 1 .dwg"`

### "Template library not found"
- Template extraction not completed
- Check: `ls -lh Terminal1_Project/Templates/terminal_base_v1.0/template_library.db`
- If missing, re-run Phase 1 extraction

### "Python not found"
- Check Python path: `ls -lh ~/blender-4.5.3/4.5/python/bin/python3.11`
- Adjust path in scripts if Blender is installed elsewhere

### Low accuracy (<70%)
- Review logs: `/tmp/dxf_parse.log` and `/tmp/dxf_to_db.log`
- Check which disciplines are missing
- May need template refinement (Phase 3)

---

## Expected Timeline

- **STEP 1:** 5-10 minutes (manual download + install)
- **STEP 2:** 1-2 minutes (DWG→DXF conversion)
- **STEP 3:** 3-5 minutes (DXF parsing + database generation)
- **STEP 4:** 1 minute (validation)

**Total:** ~10-20 minutes

---

## What Happens Next

### If accuracy ≥ 70%: ✅ POC SUCCESS!
**This proves:**
- Templates capture reusable patterns
- 2D DWG can be converted to structured BIM
- Approach can be applied to Terminal 2, 3, etc.

**Next steps:**
- Refine templates for higher accuracy
- Integrate with Bonsai UI
- Test on other terminals

### If accuracy < 70%: ⚠️ Need Refinement
**Investigation needed:**
- Which disciplines are missing?
- Which IFC classes don't match?
- Are layer naming conventions different than expected?
- Do we need better matching rules?

**Phase 3 work:**
- Analyze validation report
- Refine template matching rules
- Extract additional spatial patterns
- Implement Progressive Freezing (if needed)

---

## Key Documents to Read

1. **prompt.txt** - Complete project overview
2. **CURRENT_APPROACH.md** - Conversion methodology
3. **OFFSET_TEMPLATE_EXAMPLE.md** - How spatial offsets work
4. **OFFSET_ANALYSIS.md** - Z-height data for all templates

---

## Support

**Logs to check:**
- `/tmp/dxf_parse.log` - DXF parsing errors
- `/tmp/dxf_to_db.log` - Conversion errors
- `/tmp/oda_conversion.log` - DWG→DXF conversion errors

**Files to inspect:**
- `validation_report.md` - Detailed accuracy breakdown
- Template library: `Terminal1_Project/Templates/terminal_base_v1.0/template_library.db`

---

**Last Updated:** November 12, 2025
**Status:** Ready to convert DWG file (pending ODA File Converter installation)
