# Spatial Filter Guide - Extracting Main Building Only

**Purpose:** Extract only the main building from DXF files that contain multiple structures, site areas, or large title blocks.

---

## Why Use Spatial Filtering?

DXF architectural drawings often include:
- ✓ Main building
- ✓ Additional structures/annexes
- ✓ Site boundaries and fences
- ✓ Title blocks and specifications (can extend 1-3km!)
- ✓ Multiple buildings on campus

**Without filtering:** Extraction creates a database with a "building" that's 5-10× too large

**With filtering:** Extract only the 60-80m main building to match IFC scope

---

## How to Find the Main Building Bounding Box

### Method 1: Automated Density Analysis (Recommended)

Run the analysis script:
```bash
python3 << 'EOF'
import ezdxf
import sqlite3

# 1. Get target size from IFC
ifc_db = "/path/to/8_IFC/enhanced_federation.db"
conn = sqlite3.connect(ifc_db)
cursor = conn.cursor()
cursor.execute("SELECT MIN(center_x), MAX(center_x), MIN(center_y), MAX(center_y) FROM element_transforms")
bounds = cursor.fetchone()
conn.close()

target_width = bounds[1] - bounds[0]  # e.g., 68m
target_depth = bounds[3] - bounds[2]  # e.g., 48m

# 2. Find densest cluster in DXF
dxf_file = "/path/to/architecture.dxf"
doc = ezdxf.readfile(dxf_file)
modelspace = doc.modelspace()

# Count entities in 50m grid cells
grid_size = 50000  # mm
cells = {}

for entity in modelspace:
    # Extract coordinates...
    # Bin into cells...
    # Find densest region...

# 3. Output bounding box
print(f"SPATIAL_FILTER = {{")
print(f"    'min_x': {bbox_min_x},")
print(f"    'max_x': {bbox_max_x},")
print(f"    'min_y': {bbox_min_y},")
print(f"    'max_y': {bbox_max_y}")
print(f"}}")
EOF
```

### Method 2: Manual Selection in AutoCAD

1. Open DXF in AutoCAD
2. Turn off title block layers (`0`, `6-SPEC`, etc.)
3. Zoom to main building
4. Use `LIST` command on building corners
5. Note min/max X,Y coordinates

---

## Using Spatial Filter in Extraction

### Example 1: Terminal 1 Jetty Building

```python
#!/usr/bin/env python3
from Scripts.dxf_to_database import DXFToDatabase, TemplateLibrary

# Define spatial filter (coordinates in millimeters)
SPATIAL_FILTER = {
    'min_x': -1614493.85,  # Based on density analysis
    'max_x': -1546714.07,  # Captures 67.8m width
    'min_y': 255547.03,    # Captures 48.1m depth
    'max_y': 303608.30
}

# Load template library
template_lib = TemplateLibrary("Templates/terminal_base_v1.0/template_library.db")

# Create converter WITH spatial filter
converter = DXFToDatabase(
    dxf_path="SourceFiles/TERMINAL1DXF/01 ARCHITECT/2. BANGUNAN TERMINAL 1.dxf",
    output_db="Terminal1_MainBuilding.db",
    template_library=template_lib,
    spatial_filter=SPATIAL_FILTER  # ← Enable filtering
)

# Extract (will only process entities within bounding box)
entities = converter.parse_dxf()
matched = converter.match_templates()
converter.assign_intelligent_z_heights(building_type="airport")
converter.create_database()
inserted = converter.populate_database()

print(f"✅ Extracted {inserted:,} elements from main building only")
```

### Example 2: Without Spatial Filter (Extract Everything)

```python
# No spatial filter - extracts entire DXF
converter = DXFToDatabase(
    dxf_path="architecture.dxf",
    output_db="entire_complex.db",
    template_library=template_lib
    # spatial_filter=None (default)
)
```

---

## Validation

After extraction, **ALWAYS validate** that building dimensions match IFC:

```python
import sqlite3

# Check extracted database
conn = sqlite3.connect("Terminal1_MainBuilding.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT
        MIN(center_x), MAX(center_x),
        MIN(center_y), MAX(center_y)
    FROM element_transforms
""")
bounds = cursor.fetchone()

width = bounds[1] - bounds[0]
depth = bounds[3] - bounds[2]

print(f"Extracted building: {width:.1f}m × {depth:.1f}m")
print(f"Expected (from IFC): 68.6m × 56.8m")

# CRITICAL CHECK
tolerance = 20  # meters
assert abs(width - 68.6) < tolerance, f"Width mismatch: {width}m vs 68.6m"
assert abs(depth - 56.8) < tolerance, f"Depth mismatch: {depth}m vs 56.8m"

print("✅ Dimensions validated!")
```

---

## Common Filter Patterns

### Pattern 1: Match IFC Extent Exactly
```python
# Use IFC bounds + 10% margin
margin = 1.1
half_width = (ifc_width * margin * 1000) / 2  # Convert to mm, add margin
half_depth = (ifc_depth * margin * 1000) / 2

SPATIAL_FILTER = {
    'min_x': center_x - half_width,
    'max_x': center_x + half_width,
    'min_y': center_y - half_depth,
    'max_y': center_y + half_depth
}
```

### Pattern 2: Filter by Layer AND Spatial
```python
# First filter by building layers
building_layers = ['wall', 'window', 'door', 'column', 'roof']

# Then apply spatial filter to those layers
# (Modify _extract_entity to check layer first)
```

### Pattern 3: Multiple Buildings
```python
# Extract Building A
FILTER_BUILDING_A = {'min_x': ..., 'max_x': ..., ...}

# Extract Building B
FILTER_BUILDING_B = {'min_x': ..., 'max_x': ..., ...}

# Run extraction twice with different filters
```

---

## Troubleshooting

### Issue: Extracted building still too large

**Cause:** Bounding box includes adjacent structures

**Solution:** Reduce filter size by 10-20%
```python
# Shrink by 20%
shrink_factor = 0.8
new_width = current_width * shrink_factor
```

### Issue: Missing elements at building edges

**Cause:** Filter too tight

**Solution:** Expand filter by 5-10m
```python
# Add 5m margin (5000mm)
margin = 5000
SPATIAL_FILTER = {
    'min_x': original_min_x - margin,
    'max_x': original_max_x + margin,
    ...
}
```

### Issue: Wrong building extracted

**Cause:** Density analysis found wrong cluster

**Solution:** Use Manual AutoCAD method or check layer names
- Look for layer names with building identifiers
- Check if DXF has separate building outline layers

---

## Best Practices

1. ✅ **Always validate** extracted dimensions against IFC
2. ✅ **Start conservative** (tight filter) and expand if needed
3. ✅ **Document filter values** in code comments
4. ✅ **Test extraction** with spatial filter before full run
5. ✅ **Compare element counts** to IFC to ensure you got the right scope

---

## Integration with Comparison Scripts

Add dimension check to all comparison scripts:

```python
def validate_building_dimensions(test_db, reference_db, tolerance=20):
    """Validate extracted building matches reference dimensions."""

    # Get test dimensions
    test_bounds = get_bounds(test_db)
    test_width = test_bounds[1] - test_bounds[0]

    # Get reference dimensions
    ref_bounds = get_bounds(reference_db)
    ref_width = ref_bounds[1] - ref_bounds[0]

    # Critical check
    if abs(test_width - ref_width) > tolerance:
        raise ValueError(f"Building size mismatch! {test_width}m vs {ref_width}m")

    return True
```

---

## Summary

**Spatial filtering is now STANDARD for DXF extraction** to handle real-world architectural drawings that contain multiple structures and large title blocks.

**The workflow:**
1. Analyze IFC to get target building size
2. Find densest cluster in DXF (automated script)
3. Apply spatial filter during extraction
4. **VALIDATE dimensions match IFC** ← Critical!
5. Proceed with 2D-to-3D conversion

**This prevents the "5km wide building" problem** and ensures DXF extraction matches IFC scope.
