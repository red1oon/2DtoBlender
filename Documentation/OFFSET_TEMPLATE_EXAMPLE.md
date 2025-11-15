# Template Offset Example: Making DB2 Match DB1

**Date:** November 11, 2025
**Purpose:** Document how templates store offsets so generated database matches original

---

## The Problem

**DB1 (Original - FullExtractionTesellated.db):**
- Elements have specific 3D positions
- Example: Chairs at z=0.45m (seat height)
- Example: Sprinklers at z=3.5m (ceiling mounted)

**DWG (2D Input):**
- Elements shown at ground level (z=0)
- No height information
- Just x,y coordinates

**DB2 (Generated - our goal):**
- Must match DB1's positions
- Need to apply same offsets
- Use template to "remember" where things should be

---

## Solution: Master Template with Offsets

Templates store the "remembered" offsets from analyzing DB1.

### Example 1: ARC_IfcFurniture (Chairs)

**What we learn from DB1:**
```sql
-- Analyze original database
SELECT
    AVG(center_z) as avg_height,
    element_name
FROM element_transforms t
JOIN elements_meta m ON t.guid = m.guid
WHERE m.discipline = 'ARC'
  AND m.ifc_class = 'IfcFurniture'
GROUP BY element_name;

-- Result (hypothetical):
-- Terminal_Chair_TypeA | avg_height: 0.45m
```

**What we store in template:**
```json
{
  "template_id": "ARC_IfcFurniture_001",
  "template_name": "ARC_IfcFurniture",
  "ifc_class": "IfcFurniture",
  "discipline": "ARC",

  "spatial_offsets": {
    "z_offset": 0.45,
    "reason": "Seat height above floor",
    "unit": "meters"
  },

  "matching_rules": {
    "layer_patterns": ["ARC-FURNITURE", "ARC-SEATING"],
    "block_patterns": ["CHAIR", "SEAT"]
  }
}
```

**How we use it when generating DB2:**
```python
# Read DWG: Chair block at (10.5, 5.2, 0.0)
dwg_position = (10.5, 5.2, 0.0)

# Load template offset
template = load_template("ARC_IfcFurniture_001")
z_offset = template["spatial_offsets"]["z_offset"]  # 0.45m

# Apply offset for DB2
db2_position = (
    dwg_position[0],       # x: 10.5
    dwg_position[1],       # y: 5.2
    dwg_position[2] + z_offset  # z: 0.0 + 0.45 = 0.45
)

# Insert into DB2
INSERT INTO element_transforms (guid, center_x, center_y, center_z)
VALUES (new_guid, 10.5, 5.2, 0.45)
```

**Result:** DB2 chair position matches DB1! ✅

---

### Example 2: FP_IfcFireSuppressionTerminal (Sprinklers)

**What we learn from DB1:**
```sql
-- Analyze sprinkler heights
SELECT
    AVG(center_z) as avg_height,
    MIN(center_z) as min_height,
    MAX(center_z) as max_height
FROM element_transforms t
JOIN elements_meta m ON t.guid = m.guid
WHERE m.discipline = 'FP'
  AND m.ifc_class = 'IfcFireSuppressionTerminal';

-- Result (hypothetical):
-- avg_height: 3.5m, min: 3.2m, max: 3.8m
```

**What we store in template:**
```json
{
  "template_id": "FP_IfcFireSuppressionTerminal_001",
  "template_name": "FP_IfcFireSuppressionTerminal",
  "ifc_class": "IfcFireSuppressionTerminal",
  "discipline": "FP",

  "spatial_offsets": {
    "z_offset": 3.5,
    "z_offset_min": 3.2,
    "z_offset_max": 3.8,
    "z_offset_variance": "depends_on_storey",
    "reason": "Ceiling mounted, typical terminal height",
    "unit": "meters"
  },

  "storey_adjustments": {
    "Ground": 3.5,
    "Level 1": 7.0,  // 3.5m + 3.5m floor height
    "Level 2": 10.5
  },

  "matching_rules": {
    "layer_patterns": ["FP-SPRINKLER", "FP-FIRE"],
    "block_patterns": ["SPRINKLER", "SPK", "SPKHEAD"]
  }
}
```

**How we use it:**
```python
# Read DWG: Sprinkler block at (25.3, 18.7, 0.0) on layer "FP-SPRINKLER"
dwg_position = (25.3, 18.7, 0.0)
dwg_storey = determine_storey_from_context()  # "Ground"

# Load template
template = load_template("FP_IfcFireSuppressionTerminal_001")

# Get offset for specific storey
if dwg_storey in template["storey_adjustments"]:
    z_offset = template["storey_adjustments"][dwg_storey]
else:
    z_offset = template["spatial_offsets"]["z_offset"]  # Default: 3.5m

# Apply offset for DB2
db2_position = (
    dwg_position[0],       # x: 25.3
    dwg_position[1],       # y: 18.7
    dwg_position[2] + z_offset  # z: 0.0 + 3.5 = 3.5
)

# Insert into DB2
INSERT INTO element_transforms (guid, center_x, center_y, center_z)
VALUES (new_guid, 25.3, 18.7, 3.5)
```

**Result:** DB2 sprinkler position matches DB1! ✅

---

## Master Template Table Structure

We need to store these offsets in the template database:

```sql
-- Add offset columns to template_parameters table
INSERT INTO template_parameters (
    param_id,
    template_id,
    param_name,
    param_type,
    param_category,
    default_value,
    unit,
    description
) VALUES (
    'OFFSET_Z_ARC_FURNITURE',
    'ARC_IfcFurniture_001',
    'z_offset',
    'float',
    'fixed',  -- Fixed because derived from DB1
    '0.45',
    'meters',
    'Vertical offset for furniture placement (seat height)'
);

INSERT INTO template_parameters (
    param_id,
    template_id,
    param_name,
    param_type,
    param_category,
    default_value,
    unit,
    description
) VALUES (
    'OFFSET_Z_FP_SPRINKLER',
    'FP_IfcFireSuppressionTerminal_001',
    'z_offset',
    'float',
    'fixed',
    '3.5',
    'meters',
    'Vertical offset for sprinkler placement (ceiling height)'
);
```

---

## Workflow: Extracting Offsets from DB1

### Step 1: Analyze DB1 for Each Template

```python
def extract_spatial_offsets(db1_path, discipline, ifc_class):
    """
    Analyze DB1 to find typical z-offsets for a template.

    Returns:
        {
            'z_offset_avg': 3.5,
            'z_offset_min': 3.2,
            'z_offset_max': 3.8,
            'z_offset_std': 0.15
        }
    """
    conn = sqlite3.connect(db1_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            AVG(t.center_z) as avg_z,
            MIN(t.center_z) as min_z,
            MAX(t.center_z) as max_z,
            COUNT(*) as count
        FROM element_transforms t
        JOIN elements_meta m ON t.guid = m.guid
        WHERE m.discipline = ? AND m.ifc_class = ?
    """, (discipline, ifc_class))

    result = cursor.fetchone()

    return {
        'z_offset_avg': round(result[0], 2),
        'z_offset_min': round(result[1], 2),
        'z_offset_max': round(result[2], 2),
        'instance_count': result[3]
    }

# Example usage:
offsets = extract_spatial_offsets(
    "FullExtractionTesellated.db",
    "FP",
    "IfcFireSuppressionTerminal"
)

print(offsets)
# {'z_offset_avg': 3.5, 'z_offset_min': 3.2, 'z_offset_max': 3.8, 'instance_count': 697}
```

### Step 2: Store in Template

```python
def store_offset_in_template(template_db, template_id, offset_data):
    """Store extracted offset in template."""
    conn = sqlite3.connect(template_db)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO template_parameters (
            param_id, template_id, param_name, param_type,
            param_category, default_value, min_value, max_value, unit
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        f"OFFSET_Z_{template_id}",
        template_id,
        "z_offset",
        "float",
        "fixed",
        str(offset_data['z_offset_avg']),
        offset_data['z_offset_min'],
        offset_data['z_offset_max'],
        "meters"
    ))

    conn.commit()
```

### Step 3: Use When Generating DB2

```python
def apply_template_offset(dwg_position, template):
    """Apply template offset to DWG position."""

    # Load z_offset from template
    z_offset = get_template_parameter(template, "z_offset")

    # Apply offset
    return (
        dwg_position[0],  # x unchanged
        dwg_position[1],  # y unchanged
        dwg_position[2] + float(z_offset)  # z + offset
    )

# Example:
dwg_pos = (10.5, 5.2, 0.0)
template = load_template("ARC_IfcFurniture_001")
db2_pos = apply_template_offset(dwg_pos, template)
# Result: (10.5, 5.2, 0.45)
```

---

## Complete Example: Chairs

### DB1 (Original):
```
Chair 1: guid=abc123, x=10.5, y=5.2, z=0.45
Chair 2: guid=def456, x=12.0, y=5.2, z=0.45
Chair 3: guid=ghi789, x=13.5, y=5.2, z=0.45
...
(176 chairs total)
```

### DWG (Input):
```
CHAIR-01 block at (10.5, 5.2, 0)
CHAIR-01 block at (12.0, 5.2, 0)
CHAIR-01 block at (13.5, 5.2, 0)
...
(~176 chair blocks)
```

### Template (Master offset):
```json
{
  "z_offset": 0.45
}
```

### DB2 (Generated - matches DB1):
```
Chair 1: guid=xyz123, x=10.5, y=5.2, z=0.45  ✅
Chair 2: guid=uvw456, x=12.0, y=5.2, z=0.45  ✅
Chair 3: guid=rst789, x=13.5, y=5.2, z=0.45  ✅
...
(~176 chairs total)
```

**Result:** DB2 matches DB1 structure! 🎉

---

## Next Steps

1. **Update extract_templates.py** to analyze z-offsets from DB1
2. **Store offsets** in template_parameters table
3. **Update dxf_to_database.py** to read and apply offsets
4. **Test** with one template type (e.g., furniture)
5. **Validate** positions match between DB1 and DB2

---

**Key Insight:** The template is the "memory" of DB1. It remembers how things were positioned, so DB2 can recreate the same structure from 2D DWG.

---

**Last Updated:** 2025-11-11
