# Database Audit Engine - Specification

**Version:** 1.0
**Date:** 2025-11-19
**Status:** Draft

---

## Overview

A standalone Python tool that audits the federation database and outputs a human-readable text report describing the geometry, semantics, and metrics - without requiring Blender.

### Purpose
- **Eliminate visual testing cycle** - No need to open Blender to check results
- **Speed up debugging** - 10-20 seconds vs 2-3 minutes per iteration
- **Accessibility** - Text-based representation for visually impaired users
- **WYSIWYG guarantee** - Report matches what Blender would render

---

## Architecture

### Data Flow

```
Database (vertices/faces BLOBs)
    ↓
Decode Layer (mirrors blend_cache.py)
    ↓
Geometry Objects (in-memory)
    ↓
Analysis Engine
    ↓
Text Report (stdout or file)
```

### Key Principle

The decode layer must **exactly replicate** how `blend_cache.py` interprets the database. Since we store vertices at world positions with no additional transforms, the database IS the final geometry.

---

## Six Report Layers

### Layer 0: Spatial Layout (Orientation & Position)

Provides spatial context so humans can instantly validate correctness.

```
SPATIAL LAYOUT (Top-down view, North = +Y)
═══════════════════════════════════════════════════════════

BUILDING POSITION
─────────────────────────────────────────────────────────
Center: (X=-3.2, Y=-0.5) - slightly SW of origin
Extent: X[-23, 16] Y[-20, 19] Z[0, 12]
Orientation: Long axis runs E-W

QUADRANT ANALYSIS (from origin)
─────────────────────────────────────────────────────────
  NE (+X, +Y): 312 elements (43%)
  NW (-X, +Y): 198 elements (27%)
  SE (+X, -Y): 156 elements (21%)
  SW (-X, -Y): 74 elements (10%) ⚠️ Sparse

PERIMETER WALLS (clockwise from North)
─────────────────────────────────────────────────────────
  North: 39.4m at Y=19.3, from X=-23 to X=16
  East:  27.1m at X=16.4, from Y=-20 to Y=7
  South: 39.4m at Y=-19.8, from X=-23 to X=16
  West:  28.4m at X=-22.9, from Y=-20 to Y=7
  Closure: ✓ Forms closed rectangle (gap < 0.5m)

COLUMN GRID
─────────────────────────────────────────────────────────
  Grid origin: (-20, -15)
  Spacing: 6.0m (X) × 5.0m (Y)
  Pattern: 6 columns × 8 rows = 48 expected
  Actual: 45 detected (3 missing in NE corner)

MAJOR ZONES BY POSITION
─────────────────────────────────────────────────────────
  Center (0±5m): Main hall - high element density
  North wing (Y>10): Office areas - 12 interior walls
  South wing (Y<-10): Service areas - 8 interior walls
  East side (X>10): Entry/lobby - windows detected
  West side (X<-10): Back-of-house - no windows
```

**Why this layer is critical:**
- Human reads "North wall at Y=19.3" → instantly validates position
- "SW quadrant sparse" → knows something is missing
- "Grid origin at (-20, -15)" → can verify alignment
- No image AI needed - spatial description humans can validate

### Layer 1: Geometry (What Blender Sees)

Unpacks vertices/faces and reports physical properties.

```
GEOMETRY AUDIT
═══════════════════════════════════════════════════════════

BUILDING ENVELOPE
─────────────────────────────────────────────────────────
Bounding box: X[-23.0, 16.4] Y[-20.1, 19.3] Z[0.0, 12.0]
Dimensions: 39.4m × 39.4m × 12.0m
Expected: 67.7m × 40.1m × 24.5m
Status: ⚠️ Smaller than expected

WALLS (72 elements)
─────────────────────────────────────────────────────────
Top 5 by length:
  1. 39.4m E-W at Y=19.3 (North perimeter)
  2. 39.4m E-W at Y=-19.8 (South perimeter)
  3. 28.4m N-S at X=-22.9 (West perimeter)
  4. 27.1m N-S at X=16.4 (East perimeter)
  5. 10.4m E-W at Y=5.2 (Interior)

COLUMNS (45 elements)
─────────────────────────────────────────────────────────
Shape: Cylindrical (12 segments)
Dimensions: 0.75m diameter × 4.0m height
Distribution: Grid pattern detected
```

### Layer 2: Semantics (What Objects Mean)

Uses metadata from elements_meta table.

```
SEMANTIC CLASSIFICATION
═══════════════════════════════════════════════════════════

BY IFC CLASS
─────────────────────────────────────────────────────────
IfcWall: 72 (ARC discipline)
IfcColumn: 45 (STR discipline)
IfcBeam: 111 (STR discipline)
IfcSlab: 90 (STR discipline)
IfcPlate: 418 (ARC discipline - roof)
IfcWindow: 4 (ARC discipline)
IfcDoor: 0 ⚠️ None detected

BY DISCIPLINE
─────────────────────────────────────────────────────────
ARC (Architectural): 494 elements
STR (Structural): 246 elements
MEP (Mechanical/Electrical/Plumbing): 0 ⚠️

BY FLOOR
─────────────────────────────────────────────────────────
1F: 517 elements
3F: 115 elements
4F-6F: 28 elements
ROOF: 80 elements
```

### Layer 3: Analytics (Space Characteristics)

Analyzes relationships, systems, compliance.

```
SPACE ANALYTICS
═══════════════════════════════════════════════════════════

PERIMETER ANALYSIS
─────────────────────────────────────────────────────────
North wall: W1 (39.4m) ✓
South wall: W2 (39.4m) ✓
East wall: W3 (27.1m) ✓
West wall: W4 (28.4m) ✓
Closure check: ✓ Perimeter forms closed rectangle

STRUCTURAL GRID
─────────────────────────────────────────────────────────
Pattern: 6 × 8 grid detected
Spacing X: 5.8m (consistent)
Spacing Y: 4.9m (consistent)
Missing columns: None ✓

OPENINGS
─────────────────────────────────────────────────────────
Windows: 4 total
  - South wall: 4 windows
  - Other walls: 0
Doors: 0 ⚠️ No doors detected

MEP COVERAGE
─────────────────────────────────────────────────────────
Electrical: Not present
HVAC: Not present
Fire protection: Not present
Note: MEP disciplines not yet extracted
```

### Layer 4: Summary (Aggregate Metrics)

Total counts, areas, volumes.

```
BUILDING SUMMARY
═══════════════════════════════════════════════════════════

METRICS
─────────────────────────────────────────────────────────
Total elements: 740
Total wall length: 584.6m
Total floor area: ~1,580 m² (estimated from slabs)
Building volume: ~18,960 m³ (bbox)

ELEMENT COUNTS
─────────────────────────────────────────────────────────
Walls: 72
Columns: 45
Beams: 111
Slabs: 90
Plates: 418
Windows: 4
Doors: 0

GEOMETRY STATS
─────────────────────────────────────────────────────────
Total vertices: 10,360
Total faces: 17,760
Average vertices/element: 14
Average faces/element: 24
```

### Layer 5: Shape Classification (Complexity)

Percentage of primitive vs complex shapes.

```
SHAPE CLASSIFICATION
═══════════════════════════════════════════════════════════

BY PRIMITIVE TYPE
─────────────────────────────────────────────────────────
Box-like: 89% (659 elements)
  - Walls (extruded): 72
  - Beams (oriented): 111
  - Slabs (flat): 90
  - Plates (thin): 418

Cylindrical: 6% (45 elements)
  - Columns: 45

Complex: 5% (36 elements)
  - Multi-segment walls: 36

MESH EFFICIENCY
─────────────────────────────────────────────────────────
Simplest: 8 vertices (2-point walls)
Most complex: 24 vertices (4-point walls)
Average: 14 vertices

Render performance: ✓ Good (mostly primitives)
```

---

## Implementation

### Files

```
Scripts/
├── audit_database.py      # Main audit engine
├── audit_decode.py        # Decode layer (mirrors blend_cache.py)
├── audit_analyze.py       # Analysis functions
└── audit_report.py        # Report formatting
```

### Usage

**Standalone:**
```bash
python3 audit_database.py ~/Documents/bonsai/2Dto3D/DatabaseFiles/Terminal1_ARC_STR.db
```

**After generation (auto-run):**
```bash
python3 generate_arc_str_database.py --audit
```

### Output Options

- `--stdout` - Print to terminal (default)
- `--file report.txt` - Save to file
- `--json report.json` - Machine-readable format
- `--verbose` - Include all elements, not just summaries

---

## Decode Layer Specification

### Must Mirror blend_cache.py Exactly

**Vertex unpacking:**
```python
def unpack_vertices(blob: bytes, count: int) -> List[Tuple[float, float, float]]:
    """Unpack vertices exactly as blend_cache.py does."""
    coords = struct.unpack(f'<{count * 3}f', blob)
    return [(coords[i], coords[i+1], coords[i+2]) for i in range(0, len(coords), 3)]
```

**Face unpacking:**
```python
def unpack_faces(blob: bytes, count: int) -> List[Tuple[int, int, int]]:
    """Unpack faces exactly as blend_cache.py does."""
    indices = struct.unpack(f'<{count * 3}I', blob)
    return [(indices[i], indices[i+1], indices[i+2]) for i in range(0, len(indices), 3)]
```

**No transforms applied** - vertices are already at world positions.

### Schema Version Check

To ensure audit stays in sync with blend_cache.py:

```python
SUPPORTED_SCHEMA_VERSION = "1.0"

def check_schema_version(conn):
    """Warn if database schema doesn't match expected version."""
    # Check extraction_metadata or add schema_version table
```

---

## Analysis Functions

### Perimeter Detection

```python
def detect_perimeter_walls(walls):
    """Find the 4 longest walls and check if they form closed rectangle."""
    # Sort by length
    # Check if endpoints connect within tolerance
    # Return closure status and gap size
```

### Grid Detection

```python
def detect_column_grid(columns):
    """Detect regular grid pattern in column positions."""
    # Extract X, Y positions
    # Find regular spacing using numpy diff
    # Return grid dimensions and spacing
```

### Orientation Classification

```python
def classify_orientation(wall):
    """Determine if wall runs E-W or N-S."""
    # Compare X extent vs Y extent
    # Return 'E-W' or 'N-S'
```

### Shape Classification

```python
def classify_shape(vertex_count, face_count):
    """Classify element shape based on mesh complexity."""
    if vertex_count == 8 and face_count == 12:
        return 'box'
    elif vertex_count == 26 and face_count in [44, 48]:
        return 'cylinder'
    elif vertex_count > 8:
        return 'complex'
```

---

## Dependencies

**Required:**
- sqlite3 (stdlib)
- struct (stdlib)
- math (stdlib)

**Optional (for advanced analysis):**
- numpy - grid detection, statistics
- shapely - polygon operations (if needed)

---

## Success Criteria

1. **Accuracy** - Report matches what Blender renders
2. **Speed** - Full audit < 5 seconds
3. **Readability** - Human can understand building without seeing it
4. **Actionable** - Issues clearly marked with ⚠️
5. **Maintainable** - Easy to update if blend_cache.py changes

---

## Future Enhancements

- Room detection (enclosed wall loops)
- Clash detection preview
- Comparison between databases (diff report)
- Export to HTML with collapsible sections
- Integration with CI/CD for automated testing

---

## References

- `blend_cache.py` - Source of truth for decode logic
- `generate_arc_str_database.py` - Database generation
- `geometry_generators.py` - Geometry creation patterns
