# Working Directory

**All development happens here:** `/home/red1/Documents/bonsai/2DtoBlender/`

## Directory Structure

```
2DtoBlender/                    # Main working tree (this directory)
├── bin/                        # Pipeline scripts
├── src/                        # Source code
│   ├── core/                   # Core extraction engine
│   └── tools/                  # Database tools
├── config/                     # Configuration files
├── db/                         # Database schema & docs
├── docs/                       # Specification
├── examples/                   # Example projects with PDFs
│   └── TB-LKTN_House/
│       ├── TB-LKTN HOUSE.pdf  # Source PDF (in repo)
│       └── output/            # Generated outputs (gitignored)
│
├── output_artifacts/          # Pipeline outputs (gitignored)
├── staging/                   # Work in progress (gitignored)
│   └── experts/               # Expert consultation files
├── venv/                      # Python environment (gitignored)
│
└── .git/                      # Git repo
```

## Gitignored Directories

These directories exist locally but are excluded from git:
- `output_artifacts/` - All pipeline outputs
- `staging/` - Work files, expert requests, temporary data
- `venv/` - Python virtual environment
- `examples/*/output/` - Example outputs

## Running Pipeline

```bash
cd /home/red1/Documents/bonsai/2DtoBlender

# Activate environment
source venv/bin/activate

# Run pipeline on example
./bin/RUN_COMPLETE_PIPELINE.sh "examples/TB-LKTN_House/TB-LKTN HOUSE.pdf"

# Outputs go to:
# - output_artifacts/
# - examples/TB-LKTN_House/output/
```

## Expert Collaboration

All expert consultation files in: `staging/experts/`
- `request.txt` - Current diagnostic analysis
- Always updated, never committed to git

---

**ONE TREE, ONE LOCATION - Everything here!**
