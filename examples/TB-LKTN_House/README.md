# TB-LKTN House Example

Example project for the TB-LKTN House residential design.

## Structure

```
TB-LKTN_House/
├── README.md                  # This file
├── TB-LKTN HOUSE.pdf         # Source PDF (included in repo for testing)
└── output/                    # ALL outputs from this PDF (gitignored: examples/*/output/)
    ├── *.json                 # JSON outputs
    ├── *.db                   # Database files
    ├── *.blend                # Blender files
    └── *.log                  # Logs
```

**Crystal clear concept:** One PDF → One output/ folder with everything it generates

## What Goes Where

### Input (included in repo)
- `TB-LKTN HOUSE.pdf` - Source PDF for testing
  - **Included in repository** so users can run examples
  - Pipeline reads from here

### All Outputs (gitignored)
- `output/` - **Everything** the pipeline generates
  - JSON outputs (placement data, validation)
  - Database files (if generated)
  - Blender files (.blend)
  - Logs and debug outputs
  - **Everything in output/ is excluded from git**

## Running Pipeline

```bash
# 1. Place PDF in example folder (if not already there)
cp "TB-LKTN HOUSE.pdf" /home/red1/Documents/bonsai/2DtoBlender/examples/TB-LKTN_House/

# 2. Run pipeline
cd /home/red1/Documents/bonsai/2DBlenderWork
./bin/RUN_COMPLETE_PIPELINE.sh "../2DtoBlender/examples/TB-LKTN_House/TB-LKTN HOUSE.pdf"

# 3. Copy ALL outputs to example output/ folder
cp output_artifacts/TB-LKTN_HOUSE_OUTPUT_*.json \
   ../2DtoBlender/examples/TB-LKTN_House/output/

# (Optional) Copy other generated files
cp *.blend ../2DtoBlender/examples/TB-LKTN_House/output/ 2>/dev/null || true
cp *.db ../2DtoBlender/examples/TB-LKTN_House/output/ 2>/dev/null || true

# 4. Compare entire output folder for regression testing
diff -r output_artifacts/ ../2DtoBlender/examples/TB-LKTN_House/output/
```

## 📋 Testing Workflow

**Simple concept:**
- PDF goes here → Run pipeline → Everything it creates goes in output/

**Locations:**
1. **Source PDF:** `examples/TB-LKTN_House/TB-LKTN HOUSE.pdf`
2. **All outputs:** `examples/TB-LKTN_House/output/*`

**Rule 0 Compliance:**
- Pipeline reads ONLY the source PDF
- Pipeline NEVER reads from output/ (outputs are reference only)
- For regression testing: compare new output/ vs old output/

**Benefits:**
- Crystal clear: One PDF = One output folder
- Easy regression testing: diff entire output/ folders
- Self-contained: Each example is complete
- Gitignored: No generated files in repo
