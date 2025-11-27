# TB-LKTN House Example

Example project for the TB-LKTN House residential design.

## Structure

```
TB-LKTN_House/
├── README.md                  # This file
├── TB-LKTN HOUSE.pdf         # Source PDF (included in repo)
├── GridTruth.json             # Ground truth calibration (included in repo)
└── output/                    # ALL outputs from this PDF (gitignored)
    ├── *.json                 # JSON outputs
    ├── *.db                   # Database files
    ├── *.blend                # Blender files
    └── *.log                  # Logs
```

**Crystal clear concept:** One PDF → One output/ folder with everything it generates

## What Goes Where

### Inputs (included in repo)
- `TB-LKTN HOUSE.pdf` - Source PDF for testing
  - **Included in repository** so users can run examples
  - Pipeline reads from here

- `GridTruth.json` - Verified ground truth dimensions
  - Expert-verified real-world measurements (11.2m × 8.5m)
  - Grid lines, room bounds, elevations
  - Used for calibration validation
  - **Fundamental reference data - committed to repo**

### All Outputs (gitignored)
- `output/` - **Everything** the pipeline generates
  - JSON outputs (placement data, validation)
  - Database files (if generated)
  - Blender files (.blend)
  - Logs and debug outputs
  - **Everything in output/ is excluded from git**

## Running Pipeline

```bash
# 1. Run pipeline on example (PDF and GridTruth.json already in folder)
cd /home/red1/Documents/bonsai/2DtoBlender
./bin/RUN_COMPLETE_PIPELINE.sh "examples/TB-LKTN_House/TB-LKTN HOUSE.pdf"

# Pipeline automatically finds GridTruth.json in same folder as PDF

# 2. Outputs are in output_artifacts/ - copy to example folder for reference
cp output_artifacts/TB-LKTN_HOUSE_OUTPUT_*.json examples/TB-LKTN_House/output/
cp output_artifacts/TB-LKTN*.db examples/TB-LKTN_House/output/ 2>/dev/null || true
cp *.blend examples/TB-LKTN_House/output/ 2>/dev/null || true

# 3. For regression testing, compare outputs
diff -r output_artifacts/ examples/TB-LKTN_House/output/
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
