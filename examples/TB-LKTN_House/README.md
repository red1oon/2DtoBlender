# TB-LKTN House Example

Example project files for the TB-LKTN House residential design.

## Files

### Input (Not in Git)
- `TB-LKTN HOUSE.pdf` - 8-page architectural drawing (excluded: binary)
  - Location: Store in `2DBlenderWork/` for testing
  - Source: Project sample PDF

### Reference Output (Example Only)
- `TB-LKTN_reference_output.json` - Example of expected pipeline output
  - **⚠️  NOT FOR PIPELINE INPUT**: This is example output, not configuration
  - **Purpose:** Shows structure of what pipeline SHOULD generate from PDF
  - **Rule 0 Note:** Pipeline must derive this from PDF, not read this file
  - **Usage:** Compare against actual pipeline output for validation

## Running Pipeline on This Example

```bash
# From working directory
cd /home/red1/Documents/bonsai/2DBlenderWork

# Run pipeline
./bin/RUN_COMPLETE_PIPELINE.sh "TB-LKTN HOUSE.pdf"

# Compare output against reference (optional validation)
diff output_artifacts/TB-LKTN_HOUSE_OUTPUT_*.json \
     ../2DtoBlender/examples/TB-LKTN_House/TB-LKTN_reference_output.json
```

## ⚠️  Important Notes

**Rule 0 Compliance:**
- Pipeline MUST derive all data from PDF input
- Reference output is for validation ONLY, not pipeline input
- Code must NEVER read from examples/ directory

**Purpose:**
- This example demonstrates expected pipeline output structure
- Reference file shows what correct extraction looks like
- Used for regression testing and validation
