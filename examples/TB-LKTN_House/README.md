# TB-LKTN House Example

Example project for the TB-LKTN House residential design.

## Structure

```
TB-LKTN_House/
├── README.md                           # This file
├── TB-LKTN HOUSE.pdf                   # Source PDF (store here, excluded from git)
└── output/                             # Generated outputs (excluded from git)
    └── TB-LKTN_reference_output.json   # Example pipeline output
```

## Files

### Input (Not in Git)
- `TB-LKTN HOUSE.pdf` - 8-page architectural drawing
  - **Excluded:** Binary PDF (see .gitignore)
  - **Location:** Place source PDF here for testing

### Generated Output (Not in Git)
- `output/` - Pipeline-generated files
  - **Excluded:** All outputs gitignored (examples/*/output/)
  - **Contains:** Reference output for validation

## Running Pipeline on This Example

```bash
# 1. Place source PDF in this example folder
cp "TB-LKTN HOUSE.pdf" /home/red1/Documents/bonsai/2DtoBlender/examples/TB-LKTN_House/

# 2. Run pipeline from working directory
cd /home/red1/Documents/bonsai/2DBlenderWork
./bin/RUN_COMPLETE_PIPELINE.sh "../2DtoBlender/examples/TB-LKTN_House/TB-LKTN HOUSE.pdf"

# 3. Output goes to output_artifacts/ in working directory
ls -l output_artifacts/TB-LKTN_HOUSE_OUTPUT_*.json

# 4. (Optional) Save reference output to examples
cp output_artifacts/TB-LKTN_HOUSE_OUTPUT_*.json \
   ../2DtoBlender/examples/TB-LKTN_House/output/TB-LKTN_reference_output.json

# 5. (Optional) Compare against reference
diff output_artifacts/TB-LKTN_HOUSE_OUTPUT_*.json \
     ../2DtoBlender/examples/TB-LKTN_House/output/TB-LKTN_reference_output.json
```

## 📋 Testing Workflow

**Where to Look:**
1. **Input PDFs:** `examples/TB-LKTN_House/` (this folder)
2. **Generated Output:** `2DBlenderWork/output_artifacts/`
3. **Reference Output:** `examples/TB-LKTN_House/output/` (for comparison)

**Rule 0 Compliance:**
- Pipeline reads ONLY the source PDF
- Pipeline generates output in working dir
- Reference output is for comparison ONLY
- Code NEVER reads from examples/output/

**Purpose:**
- Examples show project structure
- Reference outputs for regression testing
- Clear separation: source (tracked) vs generated (gitignored)
