# 2DToBlender - Deterministic 2D PDF to Blender 3D BIM Pipeline

Extract architectural elements from 2D PDF drawings to LOD300 Blender models using deterministic text-based algorithms.

**Rule 0 Compliant:** All outputs derivable from source code and input data only. No manual intervention, no ML/AI.

---

## 🎯 Quick Start

### 1. Setup

```bash
# Clone repository
git clone https://github.com/red1oon/2DtoBlender.git
cd 2DtoBlender

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install pdfplumber numpy

# Validate library (first time only)
./bin/setup_library.sh
```

### 2. Run Pipeline

```bash
# Extract from PDF to JSON
./bin/RUN_COMPLETE_PIPELINE.sh "path/to/floorplan.pdf"

# Import to Blender
blender --background --python bin/blender_lod300_import.py -- \
  output_artifacts/OUTPUT_*_FINAL.json \
  path/to/Ifc_Object_Library.db \
  output.blend
```

---

## 📁 Project Structure

```
2DToBlender/
├── bin/                           # Main executables
│   ├── RUN_COMPLETE_PIPELINE.sh   # Main pipeline runner
│   ├── setup_library.sh           # Library validation
│   └── blender_lod300_import.py   # Blender import script
│
├── src/                           # Source code
│   ├── core/                      # Core extraction modules
│   │   ├── extraction_engine.py   # Main orchestrator
│   │   ├── vector_patterns.py     # Pattern detection
│   │   ├── calibration_engine.py  # PDF coordinate calibration
│   │   └── post_processor.py      # Post-processing fixes
│   │
│   ├── validators/                # Validation & QA
│   │   ├── comprehensive_test.py  # Full test suite
│   │   └── validate_*.py          # Individual validators
│   │
│   ├── standards/                 # Building codes
│   │   ├── building_standards.py  # UBBL 1984, MS 1184
│   │   └── placement_engine.py    # Standards-driven placement
│   │
│   └── tools/                     # Utility tools
│       ├── fix_library_base_rotations.py  # Geometry orientation fixer
│       └── geometry_generators.py         # Library generators
│
├── docs/                          # Documentation
│   └── TB-LKTN_COMPLETE_SPECIFICATION.md  # Complete specification
│
├── config/                        # Configuration files
│   ├── GridTruth_TB-LKTN.json    # Ground truth coordinates
│   └── master_template.json       # Extraction template
│
├── tests/                         # Test suite
│
├── .vscode/                       # VSCode workspace config
│
└── README.md                      # This file
```

---

## 🔧 Core Workflow

### Phase 1: Extraction
**Module:** `src/core/extraction_engine.py`

1. **Grid Calibration** - Extract building dimensions from PDF annotations
2. **Schedule Extraction** - Parse door/window tables (Page 8)
3. **Text Label Detection** - Find door/window markers (D1, W2, etc.)
4. **Wall Generation** - Detect wall vectors from PDF primitives
5. **Room Inference** - Derive room boundaries from walls

### Phase 2: Post-Processing
**Module:** `src/core/post_processor.py`

1. **Duplicate Removal** - Remove overlapping objects (tolerance: 0.5m)
2. **Height Assignment** - Set Z-coordinates by object type
3. **Grid Snapping** - Align to 100mm grid
4. **Wall-Mounted Placement** - Snap switches/outlets to walls

### Phase 3: Validation
**Modules:** `src/validators/`

1. **Structural Tests** - Object fields, positions, orientations
2. **Spatial Logic** - Building bounds, collisions, clearances
3. **UBBL Compliance** - Malaysian building code checks
4. **Room/Wall Validation** - Enclosure, connectivity

### Phase 4: Blender Import
**Module:** `bin/blender_lod300_import.py`

1. **Database Fetch** - LOD300 geometry from library
2. **Wall Creation** - Line segments from start/end points
3. **Roof Handling** - Sloped roofs using `end_point`
4. **Base Rotation** - Apply geometry orientation fixes
5. **Object Placement** - Position, rotation, scaling

---

## 🗄️ Database

### Schema
The LOD300 geometry library uses SQLite with two main tables:

| Table | Purpose |
|-------|---------|
| `base_geometries` | 3D mesh data (vertices, faces, normals as BLOBs) |
| `object_catalog` | Object metadata, IFC class, dimensions, rotation |

See [db/README.md](db/README.md) for full documentation.

### Setup
```bash
# Validate library and fix geometry orientations (first time setup)
./bin/setup_library.sh

# Or dry-run to check without changes
./bin/setup_library.sh --dry-run
```

### Schema Files
```
db/
├── schema/
│   ├── ifc_object_library.sql          # Full schema definition
│   └── migrations/
│       └── 002_add_base_rotation.sql   # Add rotation columns
└── README.md                           # Database documentation
```

Tools: `src/tools/fix_library_base_rotations.py` (called by `bin/setup_library.sh`)

---

## 🏗️ Key Features

### ✅ Rule 0 Compliance
- Deterministic algorithms only
- No manual coordinate entry
- No ML/AI inference
- Same input → same output

### ✅ Building Standards
- **UBBL 1984** - Malaysian Uniform Building By-Laws
- **MS 1184** - Code of Practice for Toilet Fixtures

### ✅ LOD300 Geometry
- Full 3D geometry from library database
- Parametric objects (doors, windows, fixtures)
- Material and finish specifications

### ✅ Automated QA
- 4-tier validation suite
- 35+ automated tests
- Compliance reporting

---

## 🛠️ Development

### VSCode Setup

This project includes `.vscode/` configuration:
- Python interpreter: `./venv/bin/python`
- Linting: Flake8
- File nesting enabled
- Launch configs for pipeline/import/validators

### Running Tests

```bash
# All validators
./src/validators/run_all_tests.sh

# Specific validator
python3 src/validators/validate_ubbl_compliance.py output.json
```

### Library Validation

```bash
# Check geometry orientations
./bin/setup_library.sh --dry-run

# Fix base_rotations
./bin/setup_library.sh
```

---

## 📖 Documentation

- **Main Specification:** `docs/TB-LKTN_COMPLETE_SPECIFICATION.md`
- **Algorithm Details:** See specification section 9
- **Building Standards:** See specification section 4

---

## 🚀 Example Projects

### TB-LKTN House
**Input:** 8-page architectural drawing PDF
**Output:** 142 objects (walls, doors, windows, fixtures, furniture)
**Accuracy:** 95% position, 90% detection
**Processing Time:** <15 seconds

---

## 📦 Requirements

- Python 3.8+
- pdfplumber
- numpy
- sqlite3 (built-in)
- Blender 4.2+ (for import)

---

## 🤝 Contributing

This is an internal project. For issues or suggestions, create an issue on GitHub.

---

## 📝 License

Internal project - Red1oon 2025

---

## 🔗 Links

- **GitHub:** https://github.com/red1oon/2DtoBlender
- **Issues:** https://github.com/red1oon/2DtoBlender/issues

---

**Note:** This repository contains code only. Large binary files (databases, PDF, blend files) are excluded and must be provided separately.
