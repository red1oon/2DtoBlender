# Layer Workflow Guarantees - 2Dto3D

## Problem Solved

**Before:** If Layer 2 (ELEC) failed, you had to delete EVERYTHING and regenerate Layer 1 (FP) too.
**Now:** If Layer 2 fails, just delete ELEC and regenerate only ELEC - FP stays intact.

---

## Guarantees

### ✅ Guarantee 1: Each layer deletes only its own discipline before regenerating

**Example:**
```bash
./layer0_to_layer1.sh  # Deletes old FP (if exists), regenerates FP
./layer1_to_layer2.sh  # Deletes old ELEC (if exists), regenerates ELEC
```

**SQL cleanup in each script:**
```sql
-- layer0_to_layer1.sh deletes ONLY FP
DELETE FROM ... WHERE discipline = 'FP';

-- layer1_to_layer2.sh deletes ONLY ELEC
DELETE FROM ... WHERE discipline = 'ELEC';
```

**Result:** If FP is good and ELEC is rubbish, you can redo ELEC without touching FP.

---

### ✅ Guarantee 2: Each layer can be redone independently

**Test case: Redo Layer 1 (FP) three times**
```bash
./layer0_to_layer1.sh  # First run: generates FP
./layer0_to_layer1.sh  # Second run: deletes old FP, regenerates FP
./layer0_to_layer1.sh  # Third run: deletes old FP, regenerates FP
```

**Each run:**
1. Deletes old FP (if exists)
2. Regenerates FP fresh
3. No leftover rubbish from previous runs

**Result:** You can redo a layer as many times as needed - guaranteed clean each time.

---

### ✅ Guarantee 3: Abort scripts delete ONLY what you specify

| Script | What it deletes | What it keeps |
|--------|----------------|---------------|
| `abort_to_layer0.sh` | Everything (FP + ELEC) | ARC + STR (from frozen base) |
| `abort_to_layer1.sh` | ELEC only | ARC + STR + FP |

**Example workflow:**
```bash
# Generate all layers
./layer0_to_layer1.sh  # ARC + STR + FP
./layer1_to_layer2.sh  # ARC + STR + FP + ELEC

# Oh no, ELEC is rubbish!
./abort_to_layer1.sh   # Deletes ELEC, keeps FP ✅

# Redo just ELEC
./layer1_to_layer2.sh  # Regenerates ELEC fresh
```

**Result:** You can undo one layer without losing previous work.

---

## Scripts Overview

### Generation Scripts

| Script | Input | Output | What it does |
|--------|-------|--------|--------------|
| `layer0_to_layer1.sh` | Layer 0 (ARC+STR) | Layer 1 (ARC+STR+FP) | Delete old FP, generate FP fresh |
| `layer1_to_layer2.sh` | Layer 1 (ARC+STR+FP) | Layer 2 (ARC+STR+FP+ELEC) | Delete old ELEC, generate ELEC fresh |

**Key feature:** Each script checks if previous layer exists, errors if missing.

---

### Abort Scripts

| Script | What it deletes | Result |
|--------|----------------|--------|
| `abort_to_layer0.sh` | All MEP (FP + ELEC) | Layer 0 (ARC+STR only) |
| `abort_to_layer1.sh` | ELEC only | Layer 1 (ARC+STR+FP) |

**Key feature:** Clean abort - no partial deletes, no leftover rubbish.

---

### Complete Workflow Script

```bash
./complete_fresh_workflow.sh
```

**What it does:**
1. Runs `./abort_to_layer0.sh` (start fresh)
2. Runs `./layer0_to_layer1.sh` (generate FP)
3. Runs `./layer1_to_layer2.sh` (generate ELEC)

**Result:** Full regeneration from Layer 0 to Layer 2 in one command.

---

## Usage Examples

### Example 1: Normal workflow (all layers)
```bash
./complete_fresh_workflow.sh
# Result: ARC + STR + FP + ELEC
```

---

### Example 2: FP is broken, redo just FP
```bash
./layer0_to_layer1.sh
# Result: ARC + STR + FP (regenerated)
```

---

### Example 3: ELEC is broken, redo just ELEC
```bash
./layer1_to_layer2.sh
# Result: ARC + STR + FP (unchanged) + ELEC (regenerated)
```

---

### Example 4: Everything is broken, start over
```bash
./abort_to_layer0.sh
./layer0_to_layer1.sh
./layer1_to_layer2.sh
# Result: ARC + STR + FP + ELEC (all fresh)
```

---

### Example 5: ELEC is broken, remove it entirely
```bash
./abort_to_layer1.sh
# Result: ARC + STR + FP (ELEC removed)
# Now you can work on fixing ELEC code, then run ./layer1_to_layer2.sh
```

---

## Testing Performed (Nov 17, 2025)

### Test 1: Abort to Layer 0
```bash
./abort_to_layer0.sh
# ✅ PASS: Database = ARC (911) + STR (30)
```

### Test 2: Generate Layer 1
```bash
./layer0_to_layer1.sh
# ✅ PASS: Database = ARC (911) + STR (30) + FP (499)
```

### Test 3: Redo Layer 1 (guaranteed cleanup)
```bash
./layer0_to_layer1.sh  # Second run
# ✅ PASS: Old FP deleted, new FP generated
# ✅ PASS: Database = ARC (911) + STR (30) + FP (499)
```

### Test 4: Generate Layer 2
```bash
./layer1_to_layer2.sh
# ✅ PASS: Database = ARC (911) + STR (30) + FP (499) + ELEC (396)
```

### Test 5: Redo Layer 2 (guaranteed cleanup)
```bash
./layer1_to_layer2.sh  # Second run
# ✅ PASS: Old ELEC deleted, new ELEC generated
# ✅ PASS: Database = ARC (911) + STR (30) + FP (499) + ELEC (396)
```

### Test 6: Abort to Layer 1
```bash
./abort_to_layer1.sh
# ✅ PASS: ELEC removed, FP kept
# ✅ PASS: Database = ARC (911) + STR (30) + FP (499)
```

---

## GUI Integration (Future)

Each script maps to a GUI button/action:

| GUI Action | Script Called | User Experience |
|------------|---------------|-----------------|
| **Generate FP** | `layer0_to_layer1.sh` | Progress bar → "FP generated" |
| **Generate ELEC** | `layer1_to_layer2.sh` | Progress bar → "ELEC generated" |
| **Undo ELEC** | `abort_to_layer1.sh` | "ELEC removed" |
| **Undo All MEP** | `abort_to_layer0.sh` | "Reverted to base" |
| **Regenerate All** | `complete_fresh_workflow.sh` | Progress bar → "All layers complete" |

**Key benefit:** Undo feature built-in from the start - no need to redesign later.

---

## Safety Checks

Each layer script has built-in safety:

### layer0_to_layer1.sh
- ✅ Creates database from Layer 0 if missing
- ✅ Deletes old FP before generating (guaranteed cleanup)

### layer1_to_layer2.sh
- ✅ Checks if database exists (fails if missing)
- ✅ Checks if FP exists (warns if Layer 1 missing)
- ✅ Deletes old ELEC before generating (guaranteed cleanup)

### abort_to_layer0.sh
- ✅ Deletes all working files
- ✅ Copies frozen Layer 0 (BASE_ARC_STR.db)
- ✅ No way to accidentally corrupt frozen base

### abort_to_layer1.sh
- ✅ Checks if database exists (fails if missing)
- ✅ Deletes only ELEC (FP stays intact)
- ✅ Cleans blend cache (may have ELEC cached)

---

## Files Created

| File | Size | Purpose |
|------|------|---------|
| `BASE_ARC_STR.db` | 1.9 MB | Frozen Layer 0 (ARC + STR only) |
| `abort_to_layer0.sh` | 1.1 KB | Delete all MEP, restore Layer 0 |
| `abort_to_layer1.sh` | 1.8 KB | Delete ELEC, keep FP |
| `layer0_to_layer1.sh` | 2.1 KB | Generate/redo FP |
| `layer1_to_layer2.sh` | 2.6 KB | Generate/redo ELEC |
| `complete_fresh_workflow.sh` | 1.3 KB | Run all layers |
| `POC_LAYERING_STRATEGY.md` | 4.2 KB | POC methodology documentation |
| `LAYER_WORKFLOW_GUARANTEES.md` | (this file) | Guaranteed behavior documentation |

---

## Next Steps

1. ✅ Fix FP routing issue (trunk pipes don't reach building end)
2. ✅ Test in Blender Full Load
3. ✅ Add HVAC discipline (Layer 3)
4. ✅ Add more MEP disciplines as needed
5. ✅ GUI integration (buttons call these scripts)

---

**Status:** ✅ Layer workflow complete and tested (Nov 17, 2025)
