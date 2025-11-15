# Phase 2: Bonsai Integration Plan

**Date:** November 11, 2025
**Status:** Ready to Begin
**Goal:** Generate 3D models from DWG using templates, validate by comparison

---

## Overview

**Phase 1 (COMPLETE ✅):**
- 44 templates extracted from Terminal 1
- Database schema and tools working
- All scripts tested and documented

**Phase 2 (NEXT):**
- Integrate templates into Bonsai workflow
- Generate 3D IFC from DWG using templates
- Validate: Compare generated vs original database
- **This proves templates actually work!**

---

## Architecture: Bonsai Integration

```
┌─────────────────────────────────────────────────────────────┐
│ USER ACTION                                                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ User in Bonsai/Blender:                                     │
│ 1. Menu: Federation → Import DWG Project                   │
│ 2. Select folder: RawDWG/                                  │
│ 3. Choose templates: terminal_base_v1.0                    │
│ 4. Click: Generate Model                                    │
│                                                              │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│ BONSAI ADDON PROCESSING                                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Step 1: DWG Parser                                          │
│   ├─ Read: 2. BANGUNAN TERMINAL 1.dwg                      │
│   ├─ Extract: Blocks, layers, polylines                    │
│   └─ Output: List of DWG entities                          │
│                                                              │
│ Step 2: Template Loader                                     │
│   ├─ Load: terminal_base_v1.0/template_library.db          │
│   ├─ Query: All 44 templates                               │
│   └─ Output: Template definitions ready                    │
│                                                              │
│ Step 3: Entity Matcher                                      │
│   ├─ For each DWG entity:                                   │
│   │   └─ Match against templates                           │
│   ├─ Example:                                               │
│   │   Block "SPRINKLER-HEAD" → FP_IfcFireSuppressionTerminal│
│   └─ Output: Matched entity list                           │
│                                                              │
│ Step 4: IFC Generator                                       │
│   ├─ For each matched entity:                               │
│   │   └─ Create IFC element using template                 │
│   ├─ Example:                                               │
│   │   Create IfcFireSuppressionTerminal                    │
│   │   - GUID: generate new                                 │
│   │   - Type: from template                                │
│   │   - Properties: from template                          │
│   └─ Output: IFC elements                                   │
│                                                              │
│ Step 5: Database Writer                                     │
│   ├─ Create: Generated_Terminal1.db                        │
│   ├─ Insert: All generated elements                        │
│   └─ Output: New database                                   │
│                                                              │
│ Step 6: IFC Exporter                                        │
│   ├─ Group by discipline                                    │
│   ├─ Export 8 IFC files                                     │
│   └─ Output: IFC files ready                               │
│                                                              │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│ VALIDATION (The Real Test!)                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Compare Two Databases:                                       │
│                                                              │
│ Original: FullExtractionTesellated.db                       │
│   └─ 49,059 elements (human-modeled)                       │
│                                                              │
│ Generated: Generated_Terminal1.db                           │
│   └─ ?,??? elements (template-generated)                   │
│                                                              │
│ Metrics:                                                     │
│   ├─ Element count accuracy: X%                            │
│   ├─ IFC class matching: X%                                │
│   ├─ Discipline coverage: X%                               │
│   └─ Template usage: X templates used                      │
│                                                              │
│ Success Criteria:                                            │
│   ✅ >70% element count accuracy = Templates work!          │
│   ✅ >90% IFC class matching = Correct types                │
│   ✅ 8/8 disciplines present = Complete coverage            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Components to Build

### 1. DWG Parser Module
**File:** `dwg_parser.py`

**Purpose:** Read DWG files, extract entities

**Dependencies:**
```python
import ezdxf  # DXF/DWG parsing library
```

**Key Functions:**
```python
def parse_dwg(dwg_path: str) -> List[DWGEntity]:
    """
    Parse DWG file and extract all entities.

    Returns:
        List of entities with:
        - entity_type (block, polyline, etc.)
        - layer (ARC-WALL, FP-PIPE, etc.)
        - name (SPRINKLER-HEAD, CHAIR-01, etc.)
        - attributes (any properties)
    """
    pass

def extract_blocks(dwg) -> List[Block]:
    """Extract all block instances."""
    pass

def extract_layers(dwg) -> List[Layer]:
    """Extract layer information."""
    pass
```

**Complexity:** MEDIUM
**Time estimate:** 2-3 hours

---

### 2. Template Matcher Module
**File:** `template_matcher.py`

**Purpose:** Match DWG entities against templates

**Key Functions:**
```python
def load_templates(template_db: str) -> List[Template]:
    """Load all templates from database."""
    pass

def match_entity_to_template(entity: DWGEntity, templates: List[Template]) -> Optional[Template]:
    """
    Find best matching template for DWG entity.

    Matching strategies:
    - Block name fuzzy match (SPRINKLER* → FP_IfcFireSuppressionTerminal)
    - Layer name match (FP-PIPE → FP_IfcPipeSegment)
    - Entity type match (POLYLINE + layer → template)

    Returns:
        Best matching template or None
    """
    pass

def calculate_confidence(entity: DWGEntity, template: Template) -> float:
    """Calculate match confidence score (0.0 to 1.0)."""
    pass
```

**Complexity:** MEDIUM
**Time estimate:** 2-3 hours

---

### 3. IFC Generator Module
**File:** `ifc_generator.py`

**Purpose:** Create IFC elements from templates

**Dependencies:**
```python
import ifcopenshell
import ifcopenshell.api
```

**Key Functions:**
```python
def create_ifc_from_template(template: Template, entity: DWGEntity, ifc_file) -> IfcElement:
    """
    Create IFC element based on template definition.

    Steps:
    1. Create IFC entity of correct class (from template.ifc_class)
    2. Set properties (from template.properties)
    3. Set type (from template.object_type)
    4. Generate GUID

    Returns:
        Created IFC element
    """
    pass

def create_ifc_file() -> ifcopenshell.file:
    """Create new IFC file with proper structure."""
    pass

def group_by_discipline(elements: List[IfcElement]) -> Dict[str, List[IfcElement]]:
    """Group elements by discipline for export."""
    pass
```

**Complexity:** MEDIUM-HIGH
**Time estimate:** 4-5 hours

---

### 4. Database Writer Module
**File:** `database_writer.py`

**Purpose:** Write generated elements to database (same schema as extraction)

**Key Functions:**
```python
def create_database(db_path: str):
    """Create new database with extraction schema."""
    pass

def insert_element(db, element: IfcElement, template: Template):
    """
    Insert element into database.

    Tables to populate:
    - elements_meta (guid, discipline, ifc_class, etc.)
    - element_transforms (position data - if available)
    """
    pass

def finalize_database(db):
    """Add indexes, validate integrity."""
    pass
```

**Complexity:** MEDIUM
**Time estimate:** 2-3 hours

---

### 5. Bonsai UI Module
**File:** `bonsai/bim/module/federation/ui_template_generation.py`

**Purpose:** User interface for template-based generation

**UI Components:**
```python
class TemplateFederationPanel:
    """
    Blender panel for template-based DWG import.

    UI Elements:
    - Folder picker (select project folder)
    - Template set dropdown (list available template sets)
    - Generate button
    - Progress bar
    - Results display
    """
    pass

class OperatorGenerateFromTemplates:
    """
    Blender operator to run generation process.

    Steps:
    1. Validate inputs
    2. Call DWG parser
    3. Call template matcher
    4. Call IFC generator
    5. Write database
    6. Export IFCs
    7. Show results
    """
    pass
```

**Complexity:** MEDIUM
**Time estimate:** 3-4 hours

---

### 6. Database Comparator Module
**File:** `database_comparator.py`

**Purpose:** Compare original vs generated databases (validation)

**Key Functions:**
```python
def compare_databases(original_db: str, generated_db: str) -> ComparisonReport:
    """
    Compare two databases element by element.

    Metrics:
    - Element count by discipline
    - IFC class distribution
    - Coverage percentage
    - Missing elements

    Returns:
        Detailed comparison report
    """
    pass

def generate_html_report(report: ComparisonReport) -> str:
    """Generate HTML validation report."""
    pass
```

**Complexity:** MEDIUM
**Time estimate:** 2-3 hours

---

## Implementation Order

### Week 1: Core Modules (Foundation)

**Day 1-2: DWG Parser**
- Install ezdxf: `pip install ezdxf`
- Build parser
- Test on Terminal 1 DWG
- Verify entity extraction

**Day 3-4: Template Matcher**
- Load templates from database
- Implement fuzzy matching
- Test matching logic
- Tune confidence scores

**Day 5: Integration Test**
- Parse DWG → Match templates
- Generate statistics report
- Validate matching accuracy

### Week 2: IFC Generation

**Day 6-7: IFC Generator**
- Create IFC elements from templates
- Handle all 8 disciplines
- Test with sample data

**Day 8-9: Database Writer**
- Write elements to database
- Match extraction schema
- Validate data integrity

**Day 10: End-to-End Test**
- DWG → Templates → IFC → Database
- Compare vs original
- Measure accuracy

### Week 3: Bonsai UI

**Day 11-12: UI Components**
- Create Blender panel
- Add folder picker
- Add template selector

**Day 13-14: Integration**
- Connect UI to backend
- Test in Blender
- Polish UX

**Day 15: Final Validation**
- Full workflow test
- Generate validation report
- Document results

---

## Success Criteria

### Minimum Viable (70% threshold):
- ✅ Parse DWG successfully
- ✅ Match 70%+ entities to templates
- ✅ Generate IFC files (all 8 disciplines)
- ✅ Create database with same schema
- ✅ Element count accuracy >70%

### Target Goal (90% threshold):
- ✅ Match 90%+ entities
- ✅ Element count accuracy >90%
- ✅ IFC class matching 100%
- ✅ All disciplines present
- ✅ UI integrated smoothly

### Stretch Goal (95% threshold):
- ✅ Match 95%+ entities
- ✅ Spatial accuracy <0.5m (if positions available)
- ✅ Property accuracy >95%
- ✅ Performance <2 minutes for full generation

---

## Technical Dependencies

### Python Libraries
```bash
# Already available in Bonsai/Blender
import ifcopenshell
import sqlite3
import json

# Need to install
pip install ezdxf  # DWG/DXF parsing
```

### File Access
- Read: `/home/red1/Documents/bonsai/RawDWG/*.dwg`
- Read: `/home/red1/Documents/bonsai/RawDWG/Terminal1_Project/Templates/*/template_library.db`
- Write: `/home/red1/Documents/bonsai/RawDWG/Terminal1_Project/Output/Generated_Terminal1.db`

### Blender/Bonsai Integration
- Location: `~/Projects/IfcOpenShell/src/bonsai/bonsai/bim/module/federation/`
- Existing: Federation module already exists
- Add: Template-based generation as new operator

---

## Validation Strategy

### The Real Test:
```python
# Step 1: Generate from DWG
Generated_Terminal1.db = generate_from_dwg(
    dwg="Terminal 1.dwg",
    templates="terminal_base_v1.0"
)

# Step 2: Compare databases
comparison = compare_databases(
    original="FullExtractionTesellated.db",
    generated="Generated_Terminal1.db"
)

# Step 3: Success?
if comparison.element_count_accuracy > 0.70:
    print("✅ SUCCESS: Templates work!")
    print(f"   Accuracy: {comparison.element_count_accuracy}%")
else:
    print("❌ NEEDS WORK: Templates need refinement")
    print(f"   Missing: {comparison.missing_elements}")
```

---

## Risk Mitigation

### Risk 1: DWG Format Issues
**Risk:** DWG format unreadable or corrupted
**Mitigation:** Convert DWG → DXF first (Bonsai can do this)

### Risk 2: Template Matching Fails
**Risk:** Can't match DWG entities to templates
**Mitigation:**
- Start with known patterns (SPRINKLER, CHAIR)
- Add fuzzy matching
- Log unmatched entities for analysis

### Risk 3: IFC Generation Errors
**Risk:** Can't create valid IFC elements
**Mitigation:**
- Use ifcopenshell.api (high-level, safe)
- Validate IFC files after generation
- Test with simple elements first

### Risk 4: Performance Issues
**Risk:** Takes too long (>10 minutes)
**Mitigation:**
- Batch processing
- Progress indicators
- Optimize database queries

---

## Next Immediate Steps

1. ✅ **Decision made:** Skip 2D test, go to Phase 2
2. ⏳ **Install ezdxf:** `pip install ezdxf`
3. ⏳ **Create `dwg_parser.py`:** Start with basic DWG reading
4. ⏳ **Test parser:** Can we read Terminal 1 DWG?
5. ⏳ **Build from there:** Parser → Matcher → Generator

---

## Expected Timeline

- **Week 1:** Core modules (Parser, Matcher) - 40 hours
- **Week 2:** IFC generation & database - 40 hours
- **Week 3:** Bonsai UI integration - 40 hours
- **Total:** ~120 hours (~3 weeks full-time)

**But:** Working incrementally, testing each component

---

**Status:** ✅ Plan complete, ready to start implementation
**Next Action:** Build DWG parser module
**Goal:** Prove templates work by generating & comparing databases

---

**Document Version:** 1.0
**Created:** 2025-11-11
