# POC Layering Strategy - 2Dto3D

## Principle

**POC (Proof of Concept) development requires fresh runs, but slow operations should be frozen as checkpoints.**

## Frozen Layers (Checkpoints)

Each layer is a **known-good database state** that serves as a restart point.

### Layer 0: BASE_ARC_STR.db (FROZEN)
- **Content:** ARC (911 elements) + STR (30 elements) from DXF extraction
- **Source:** DXF files → `Scripts/dxf_to_database.py`
- **Why frozen:** DXF extraction is slow (~minutes)
- **When to regenerate:** Only if DXF files change or extraction logic changes
- **File:** `BASE_ARC_STR.db` (DO NOT MODIFY)

### Layer 1: BASE_ARC_STR_FP.db (OPTIONAL FROZEN)
- **Content:** Layer 0 + FP discipline (sprinklers + pipes)
- **Source:** Layer 0 + `Scripts/master_routing.py --discipline FP --generate-devices`
- **Why frozen:** If testing ELEC repeatedly, freeze this to skip FP regeneration
- **When to regenerate:** When FP routing logic changes
- **File:** `BASE_ARC_STR_FP.db` (optional checkpoint)

### Layer 2: Terminal1_MainBuilding_FILTERED.db (WORKING FILE)
- **Content:** Layer 1 + ELEC discipline (lights + conduits)
- **Source:** Layer 1 + `Scripts/master_routing.py --discipline ELEC --device-type light_fixture --generate-devices`
- **Why NOT frozen:** This is the working file, regenerated every run
- **File:** `Terminal1_MainBuilding_FILTERED.db` (deleted and regenerated each run)

## Workflow: complete_fresh_workflow.sh

```bash
#!/bin/bash
# POC Fresh Run - Regenerates everything after Layer 0

# Step 1: Delete everything after Layer 0
rm -f Terminal1*.db Terminal1*.blend *.blend.log

# Step 2: Start from frozen Layer 0
cp BASE_ARC_STR.db Terminal1_MainBuilding_FILTERED.db

# Step 3: Generate FP (creates Layer 1)
python3 Scripts/master_routing.py Terminal1_MainBuilding_FILTERED.db --discipline FP --generate-devices

# Optional: Freeze Layer 1 for future use
# cp Terminal1_MainBuilding_FILTERED.db BASE_ARC_STR_FP.db

# Step 4: Generate ELEC (creates Layer 2)
python3 Scripts/master_routing.py Terminal1_MainBuilding_FILTERED.db --discipline ELEC --device-type light_fixture --generate-devices
```

## When to Restart from Each Layer

| If this breaks... | Restart from... | Command |
|-------------------|-----------------|---------|
| DXF extraction | Regenerate Layer 0 | `python3 Scripts/dxf_to_database.py ...` |
| FP generation | Layer 0 | `./complete_fresh_workflow.sh` |
| ELEC generation | Layer 1 (if frozen) | `cp BASE_ARC_STR_FP.db Terminal1_MainBuilding_FILTERED.db && python3 Scripts/master_routing.py ... --discipline ELEC` |
| Blender loading | Current Layer 2 | Just reload Blender (no regeneration needed) |

## Rules

1. **NEVER modify frozen layers** (BASE_ARC_STR.db, BASE_ARC_STR_FP.db)
2. **ALWAYS delete Terminal1*.db before fresh runs** (avoid layering on dirty state)
3. **ALWAYS run from clean checkpoint** (don't fix-on-fix-on-fix)
4. **Freeze slow operations** (DXF extraction, heavy processing)
5. **Don't freeze fast operations** (MEP generation is fast, regenerate fresh)

## Current Status (Nov 17, 2025)

✅ **Layer 0 frozen:** BASE_ARC_STR.db (ARC: 911, STR: 30)
⚠️ **Layer 1 not frozen:** Regenerate FP every run (fast enough)
🔄 **Layer 2 working file:** Terminal1_MainBuilding_FILTERED.db (deleted each run)

## Regenerating Layer 0 (if needed)

**Only do this if DXF files change or extraction logic changes!**

```bash
# Extract from DXF (slow - ~5 minutes)
python3 Scripts/dxf_to_database.py \
    SourceFiles/TERMINAL1DXF/... \
    BASE_ARC_STR_TEMP.db

# Verify it only has ARC + STR
sqlite3 BASE_ARC_STR_TEMP.db "SELECT discipline, COUNT(*) FROM elements_meta GROUP BY discipline;"

# If good, replace frozen Layer 0
mv BASE_ARC_STR_TEMP.db BASE_ARC_STR.db
```

## What NOT to Do

❌ **DON'T copy a dirty base and clean it with SQL** (wasteful, confusing)
❌ **DON'T layer fixes on top of broken state** (run fresh from checkpoint)
❌ **DON'T modify Terminal1_MainBuilding_FILTERED.db manually** (regenerate from layer)
❌ **DON'T skip deletion step** (POC requires fresh starts)

## What TO Do

✅ **DO delete Terminal1*.db before each test run**
✅ **DO start from frozen Layer 0 checkpoint**
✅ **DO regenerate MEP disciplines fresh each time**
✅ **DO freeze slow operations as new layers if needed**
✅ **DO document what each frozen layer contains**
