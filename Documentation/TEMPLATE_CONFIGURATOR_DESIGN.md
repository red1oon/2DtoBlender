=============================================================================
TEMPLATE CONFIGURATOR - DESIGN SPECIFICATION
=============================================================================

Document Type: Design Vision & Requirements
Created: November 12, 2025
Status: Conceptual Design (Pre-Implementation)
Purpose: Define the template manipulation interface for future development

=============================================================================
OVERVIEW
=============================================================================

The Template Configurator is a standalone application that allows users to:
1. Browse and explore extracted templates from BIM models
2. Modify template parameters to control BIM generation behavior
3. Create template variants for different project scenarios
4. Validate template applicability before applying to new DWG files

This tool turns static extracted templates into ADAPTABLE, USER-CONTROLLABLE
BIM generation rules.

=============================================================================
CORE CONCEPT
=============================================================================

Templates extracted from Terminal 1 represent "learned patterns" from that
specific project. However, when applying templates to Terminal 2, 3, or
entirely different projects, users need to ADAPT these templates to:

- Different architectural styles (spacing, densities, layouts)
- Different naming conventions (layer names, block names)
- Different design standards (heights, clearances, regulations)
- Different project phases (preliminary vs detailed design)

The Template Configurator provides the interface to make these adaptations
WITHOUT requiring manual 3D modeling.

=============================================================================
DESIGN PHILOSOPHY
=============================================================================

1. NON-DESTRUCTIVE EDITING
   - Original extracted templates are never modified
   - Users create "variants" or "configuration profiles"
   - Can always revert to original extracted values
   - Multiple profiles can coexist

2. VISUAL + NUMERICAL
   - Visual hierarchy browser (tree view of templates)
   - 3D visualization of spatial offsets
   - Numerical parameter editors
   - Live preview of impact on generation

3. VALIDATION-FIRST
   - Test templates against target DWG before full generation
   - Health checks show expected vs actual matches
   - Warnings for missing or low-confidence matches

4. BATCH OPERATIONS
   - Apply changes to multiple templates at once
   - Global rules across disciplines
   - Efficient workflow for large template libraries

=============================================================================
KEY PROPERTIES
=============================================================================

PROPERTY 1: VISUAL TEMPLATE HIERARCHY BROWSER
────────────────────────────────────────────────────────────────────────────

Display templates in organized tree structure:

📁 Terminal 1 Base Templates (v1.0)
  ├─ 🏛️ ARC (Architecture) - 13 templates
  │   ├─ IfcFurniture (Chairs) - 1,245 instances
  │   │   └─ Spatial: z_offset=0.45m, spacing=1.2m
  │   ├─ IfcDoor - 89 instances
  │   └─ IfcWall - 234 instances
  ├─ 🔥 FP (Fire Protection) - 9 templates
  │   ├─ IfcFireSuppressionTerminal (Sprinklers) - 456 instances
  │   │   └─ Spatial: z_offset=3.5m, grid_pattern=6m×6m
  │   └─ IfcPipeSegment (FP Pipes) - 1,890 instances
  └─ ... (other disciplines)

Each template shows:
- Instance count from source model
- Key spatial parameters
- Matching rules summary
- IFC class mapping

PROPERTY 2: PARAMETER EDITOR WITH LIVE PREVIEW
────────────────────────────────────────────────────────────────────────────

When a template is selected, display editable parameter panel:

┌─────────────────────────────────────────────┐
│ Template: ARC_IfcFurniture (Chairs)        │
├─────────────────────────────────────────────┤
│ Spatial Parameters:                         │
│  • Z-Offset: [0.45] meters                  │
│  • Minimum Spacing: [1.2] meters            │
│  • Density Override: [  ] chairs/m²         │
│                                             │
│ Matching Rules:                             │
│  • DWG Layer: [ARC-FURN*]                   │
│  • Block Names: [CHAIR*, SEAT*, BENCH*]     │
│  • Entity Types: [BLOCK, INSERT]            │
│                                             │
│ IFC Mapping:                                │
│  • IFC Class: [IfcFurniture ▼]             │
│  • Predefined Type: [CHAIR ▼]              │
│                                             │
│ Validation Rules:                           │
│  ☑ Skip if area < 10m² (empty halls)       │
│  ☑ Warn if density > 2 chairs/m²           │
│  ☐ Require accessibility clearance         │
└─────────────────────────────────────────────┘

[Preview Impact] [Save as Variant] [Revert]

"Preview Impact" shows:
- Estimated element count for target DWG
- Comparison with original template statistics
- Confidence level of matches

PROPERTY 3: SCENARIO/VARIANT MANAGEMENT
────────────────────────────────────────────────────────────────────────────

Templates have multiple variants for different use cases:

Terminal1_Base_v1.0/ARC_IfcFurniture
  ├─ [Default] - Original extracted (1,245 instances)
  ├─ [High_Density_Variant] - For crowded spaces (z=0.45, spacing=0.9m)
  ├─ [Stadium_Seating] - For auditoriums (z=0.40, rows=tiered)
  └─ [Minimal_Variant] - For small waiting areas (skip if area < 20m²)

Users can:
- Create new variants from base template
- Switch between variants for different projects
- Compare variants side-by-side
- Export variant configurations

PROPERTY 4: SPATIAL OFFSET VISUALIZER
────────────────────────────────────────────────────────────────────────────

CRITICAL for understanding 2D→3D transformation.

Side View (Section):

   3.5m ──┼── 💧 Sprinklers (FP_IfcFireSuppressionTerminal)
          │
   2.8m ──┼── 💡 Lights (ELEC_IfcLightFixture)
          │
   2.0m ──┼── 🌡️ ACMV Diffusers (ACMV_IfcAirTerminal)
          │
   0.45m ─┼── 💺 Chairs (ARC_IfcFurniture)
          │
   0.0m ──┼──────────────── DWG Floor Plan (all entities at z=0)

Interactive features:
- Click and drag elements vertically to adjust z-offsets
- See 3D preview of positioned elements
- Understand relationship between DWG (2D) and BIM (3D)
- Visual validation of element stacking

PROPERTY 5: TEMPLATE VALIDATION & HEALTH CHECKS
────────────────────────────────────────────────────────────────────────────

Before applying templates to new DWG, run validation:

🔍 Template Health Report for "Terminal 2.dwg":

✅ ARC_IfcFurniture: 45 matches found (expected 30-50) ✓
✅ FP_IfcPipeSegment: 1,234 matches found (expected 1,000-2,000) ✓
⚠️  ELEC_IfcLightFixture: 12 matches found (expected 200-300) [LOW]
❌ ACMV_IfcDuctSegment: 0 matches found (expected 800+) [MISSING]

Recommendations:
• Check if ELEC layers use different naming (found "E-LIGHT" not "ELEC-LIGHT")
• ACMV ducts may be in separate file - review DWG file structure
• Overall coverage: 68% (2,456 / 3,600 expected elements)

This gives users confidence BEFORE running full generation.

PROPERTY 6: BATCH TEMPLATE OPERATIONS
────────────────────────────────────────────────────────────────────────────

Apply changes to multiple templates efficiently:

Batch Operations:
☑ Select 9 FP templates
  └─ Apply Global Rule: "Increase all z-offsets by +0.5m" (ceiling raised)

☑ Select all ARC furniture templates
  └─ Apply Global Rule: "Skip generation if room area < 15m²"

☑ Select all MEP templates (ACMV, ELEC, SP, CW, LPG)
  └─ Apply Global Rule: "Match layers with prefix 'M-' OR 'MEP-'"

Common batch operations:
- Global offset adjustments (building height changes)
- Layer naming convention updates (different projects)
- Density scaling (sparse vs dense layouts)
- Validation rule updates

=============================================================================
TEMPLATE MANIPULATION CAPABILITIES
=============================================================================

A) SPATIAL MANIPULATIONS:
──────────────────────────
- Adjust z-offsets (vertical positioning)
  * Individual element offsets
  * Discipline-wide offsets (e.g., all ACMV +0.5m)
  * Relative offsets (e.g., lights 0.3m below ceiling)

- Modify spacing/density rules
  * Minimum/maximum spacing between elements
  * Density per unit area
  * Distribution patterns (uniform, clustered, linear)

- Define distribution patterns
  * Grid patterns (6m × 6m sprinkler grid)
  * Linear patterns (along walls, corridors)
  * Radial patterns (around central points)
  * Clustered patterns (furniture groupings)

- Set boundary conditions
  * Skip if room area < threshold
  * Skip if room type doesn't match
  * Apply only in specific zones

B) MATCHING RULE MANIPULATIONS:
────────────────────────────────
- Edit layer name patterns
  * Wildcards: "ARC-FURN*" matches "ARC-FURN01", "ARC-FURNITURE"
  * Regex: "^(ARC|ARCH)-FURN" for flexible matching
  * Case sensitivity options

- Add/remove block name mappings
  * Map multiple block names to same template
  * Handle variations: "CHAIR", "CHAIR_01", "SEATING"

- Adjust entity type filters
  * BLOCK, INSERT, POLYLINE, LINE, CIRCLE, etc.
  * Combine multiple entity types

- Create conditional matching
  * If layer X AND block Y, use template Z
  * Priority ordering for overlapping rules

C) IFC MAPPING MANIPULATIONS:
──────────────────────────────
- Change IFC class
  * e.g., IfcFurniture → IfcFurnishingElement
  * Validate against IFC schema

- Modify predefined types
  * IfcDoorTypeEnum: DOOR, GATE, TRAPDOOR
  * IfcWallTypeEnum: STANDARD, POLYGONAL, SHEAR

- Set custom property sets
  * Add project-specific properties
  * Map to COBie, Uniclass, or other standards

- Map to different IFC schema versions
  * IFC2x3 vs IFC4 vs IFC4.3
  * Handle deprecated/changed classes

D) VALIDATION RULE MANIPULATIONS:
──────────────────────────────────
- Set thresholds
  * Minimum element count (warn if < 10)
  * Maximum element count (warn if > 10,000)
  * Density thresholds (chairs/m², fixtures/room)

- Define exclusion zones
  * Skip generation in specific areas
  * Respect clearances around doors, corridors

- Create warnings vs hard errors
  * Warning: "Low match count, review settings"
  * Error: "No matches found, cannot proceed"

- Specify required vs optional elements
  * Required: Structure, walls, doors
  * Optional: Furniture, decorative elements

=============================================================================
IMPLEMENTATION APPROACH
=============================================================================

RECOMMENDED: Phased Implementation
────────────────────────────────────────────────────────────────────────────

PHASE 1: Prove Core POC First (Current Priority)
  1. Extract spatial offsets from DB1
  2. Convert Terminal 1 DWG → DXF → DB2
  3. Validate DB2 vs DB1 (70%+ accuracy = success)

  Result: Hardcoded templates prove the concept works

PHASE 2: Build Simple CLI Configurator
  1. Command-line tool to view/edit template parameters
  2. Export modified templates to JSON
  3. dxf_to_database.py reads JSON overrides

  Result: Basic parameter manipulation without GUI complexity

PHASE 3: Build Desktop GUI Configurator
  1. PyQt6/PySide6 application
  2. Visual template browser + parameter editor
  3. 3D offset visualizer
  4. Template validation tools

  Result: Professional tool for template management

PHASE 4 (Optional): Web-Based Configurator
  1. Flask/FastAPI backend
  2. React/Vue.js frontend
  3. Multi-user access, cloud deployment

  Result: Enterprise-ready solution

TECHNOLOGY STACK (For Phase 3 GUI):
────────────────────────────────────────────────────────────────────────────

Desktop GUI (Recommended for POC):
- PyQt6 or PySide6 (professional, native look)
  * Pros: Native performance, rich widgets, 3D support
  * Cons: Learning curve for Qt

- Tkinter (simpler alternative)
  * Pros: Built into Python, simpler to learn
  * Cons: Less polished UI, limited 3D support

UI Layout:
- Left Panel: Template tree browser (QTreeView)
- Center Panel: Parameter editor (QFormLayout with input widgets)
- Right Panel: 3D preview (Qt3D) or statistics panel
- Bottom Panel: Validation results, logs

Database Access:
- SQLite connection to template_library.db
- Read-only access to original templates
- Read/write access to variant configurations

File Format for Variants:
- JSON configuration files
- Store only deltas/overrides from base template
- Human-readable, version-controllable

=============================================================================
DATA FLOW
=============================================================================

Template Configurator Workflow:
────────────────────────────────────────────────────────────────────────────

1. LOAD TEMPLATES
   Template Configurator
         ↓
   [Load template_library.db]
         ↓
   [Display template tree]

2. EDIT PARAMETERS
   User selects template
         ↓
   [Load template parameters]
         ↓
   [Display in editor form]
         ↓
   [User modifies values]
         ↓
   [Preview impact (optional)]

3. SAVE VARIANT
   [Save as new variant]
         ↓
   [Export to JSON config file]
         ↓
   Terminal1_Project/Templates/terminal_base_v1.0/variants/
      └─ high_density_variant.json

4. APPLY TO DWG
   dxf_to_database.py
         ↓
   [Load base templates from DB]
         ↓
   [Load variant JSON (if specified)]
         ↓
   [Merge: Base + Overrides = Active Config]
         ↓
   [Parse DXF with active config]
         ↓
   [Generate database]

Configuration File Format Example:
────────────────────────────────────────────────────────────────────────────

{
  "variant_name": "High_Density_Terminal",
  "base_template_version": "terminal_base_v1.0",
  "created": "2025-11-12",
  "description": "Adjusted for high-density passenger areas",

  "template_overrides": [
    {
      "template_name": "ARC_IfcFurniture",
      "parameters": {
        "z_offset": 0.45,
        "minimum_spacing": 0.9,
        "density_override": 1.8
      },
      "matching_rules": {
        "layer_pattern": "ARC-FURN*",
        "block_names": ["CHAIR*", "SEAT*", "BENCH*", "SEATING*"]
      }
    },
    {
      "template_name": "FP_IfcFireSuppressionTerminal",
      "parameters": {
        "z_offset": 3.8,
        "grid_spacing": 5.5
      }
    }
  ],

  "global_rules": [
    {
      "rule": "all_MEP_layers",
      "layer_prefix": ["M-", "MEP-", "MECH-", "ELEC-", "PLUMB-"]
    },
    {
      "rule": "skip_small_rooms",
      "min_area_m2": 15.0
    }
  ]
}

=============================================================================
CRITICAL DESIGN PRINCIPLE
=============================================================================

NON-DESTRUCTIVE EDITING
────────────────────────────────────────────────────────────────────────────

Original extracted templates represent "ground truth" from Terminal 1.
These should NEVER be modified directly.

Instead:
✅ User creates "variants" or "configuration profiles"
✅ Each profile stores deltas/overrides from base template
✅ Can always revert to original extracted values
✅ Multiple profiles can coexist

Example Directory Structure:
────────────────────────────────────────────────────────────────────────────

Terminal1_Project/Templates/terminal_base_v1.0/
├── template_library.db          (ORIGINAL - never modified)
├── metadata.json                 (ORIGINAL - never modified)
└── variants/
    ├── default.json              (No overrides, uses original)
    ├── high_density.json         (Furniture spacing reduced)
    ├── stadium_seating.json      (Tiered seating pattern)
    ├── minimal_furniture.json    (Sparse furniture, skip small rooms)
    └── terminal2_adapted.json    (Layer name adjustments for Terminal 2)

When generating from DWG:
────────────────────────────────────────────────────────────────────────────

python3 dxf_to_database.py \
    Terminal2.dxf \
    Generated_Terminal2.db \
    Terminal1_Project/Templates/terminal_base_v1.0/template_library.db \
    --variant variants/terminal2_adapted.json

The script:
1. Loads base templates from template_library.db
2. Loads overrides from terminal2_adapted.json
3. Merges them to create active configuration
4. Uses active configuration for generation

=============================================================================
USER WORKFLOWS
=============================================================================

WORKFLOW 1: Apply Existing Templates to New Project
────────────────────────────────────────────────────────────────────────────

1. Open Template Configurator
2. Load Terminal 1 template library
3. Run "Validate Against DWG" → select Terminal2.dwg
4. Review health report:
   - "ELEC layer names don't match (found E-* not ELEC-*)"
5. Create new variant: "Terminal2_Adapted"
6. Edit ELEC templates → change layer pattern to "E-*"
7. Re-validate → health report improves
8. Save variant
9. Run generation:
   python3 dxf_to_database.py Terminal2.dxf Generated_Terminal2.db \
       template_library.db --variant Terminal2_Adapted.json
10. Review results in Bonsai

WORKFLOW 2: Create Density Variants for Different Spaces
────────────────────────────────────────────────────────────────────────────

1. Load Terminal 1 templates
2. Create variant: "High_Density_Waiting_Areas"
3. Select ARC_IfcFurniture template
4. Modify parameters:
   - minimum_spacing: 1.2m → 0.9m
   - density_override: 1.5 chairs/m²
5. Add validation rule: "Only apply in rooms tagged WAITING_AREA"
6. Save variant
7. Create another variant: "Low_Density_VIP_Lounge"
8. Same template, different parameters:
   - minimum_spacing: 1.2m → 2.0m
   - density_override: 0.5 chairs/m²
9. When generating, user chooses which variant to apply to which areas

WORKFLOW 3: Adapt for Different Building Heights
────────────────────────────────────────────────────────────────────────────

1. Terminal 3 has higher ceilings (4m vs 3.5m)
2. Load Terminal 1 templates
3. Create variant: "High_Ceiling_Terminal3"
4. Batch select all ceiling-mounted templates:
   - FP_IfcFireSuppressionTerminal (Sprinklers)
   - ELEC_IfcLightFixture (Lights)
   - ACMV_IfcAirTerminal (Diffusers)
5. Batch operation: "Increase z_offset by +0.5m"
6. Preview 3D offset visualization → verify positions look correct
7. Save variant
8. Apply to Terminal 3 DWG

WORKFLOW 4: Handle Missing or Non-Standard Elements
────────────────────────────────────────────────────────────────────────────

1. Validate Terminal 4 DWG against Terminal 1 templates
2. Health report shows: "0 matches for ACMV_IfcDuctSegment"
3. Investigate DWG file → ducts are on layer "DUCT-SUPPLY" not "ACMV-DUCT"
4. Create variant: "Terminal4_ACMV_Fix"
5. Edit ACMV_IfcDuctSegment template
6. Add layer pattern: "DUCT-*"
7. Re-validate → matches found
8. Save and apply

=============================================================================
VALIDATION & TESTING STRATEGY
=============================================================================

Before full implementation, validate design with users:
────────────────────────────────────────────────────────────────────────────

1. Paper Prototypes / Mockups
   - Show UI layouts to potential users
   - Get feedback on workflow intuitiveness
   - Identify missing features

2. CLI Prototype First
   - Build command-line version (faster to implement)
   - Test core functionality: load, edit, save, validate
   - Identify technical challenges

3. Minimal GUI (Single Template Editor)
   - Build interface for editing ONE template
   - Test PyQt6 implementation
   - Validate 3D visualization approach

4. Iterative Expansion
   - Add template browser
   - Add batch operations
   - Add validation tools
   - Add variant management

=============================================================================
SUCCESS METRICS
=============================================================================

The Template Configurator is successful if:
────────────────────────────────────────────────────────────────────────────

✅ Users can adapt templates to new projects in < 30 minutes
✅ Validation tools catch 90%+ of common issues before generation
✅ 3D offset visualization helps users understand spatial relationships
✅ Variant system allows non-destructive experimentation
✅ Batch operations save time when modifying multiple templates
✅ Generated BIM quality improves (higher accuracy vs manual adjustment)

=============================================================================
RISKS & MITIGATIONS
=============================================================================

RISK 1: Too Complex for Users
────────────────────────────────────────────────────────────────────────────
Mitigation:
- Start with simple, guided workflows
- Provide preset variants for common scenarios
- Include "wizards" for common tasks
- Comprehensive tooltips and documentation

RISK 2: Parameter Changes Have Unexpected Consequences
────────────────────────────────────────────────────────────────────────────
Mitigation:
- Live preview of impact
- Validation before full generation
- Undo/revert functionality
- Clear warnings for risky changes

RISK 3: Performance Issues with Large Template Libraries
────────────────────────────────────────────────────────────────────────────
Mitigation:
- Lazy loading (load template details on demand)
- Database indexing
- Efficient tree view rendering
- Background processing for validation

RISK 4: Version Control and Template Drift
────────────────────────────────────────────────────────────────────────────
Mitigation:
- Git-friendly JSON format for variants
- Version tracking in metadata
- Diff tools to compare template versions
- Clear naming conventions

=============================================================================
FUTURE ENHANCEMENTS (Post-MVP)
=============================================================================

1. MACHINE LEARNING INTEGRATION
   - Auto-suggest parameter adjustments based on validation results
   - Learn from user corrections
   - Predict optimal settings for new projects

2. COLLABORATIVE FEATURES
   - Share template libraries across teams
   - Template marketplace (community templates)
   - Review/approval workflows

3. ADVANCED 3D VISUALIZATION
   - Full 3D preview of generated BIM (before full processing)
   - Clash detection preview
   - Comparison view (Template 1 vs Template 2 results)

4. INTEGRATION WITH BIM AUTHORING TOOLS
   - Export to Bonsai directly
   - Export to Revit, ArchiCAD
   - Two-way sync (edit in Bonsai → update templates)

5. AUTOMATED TESTING
   - Template unit tests (verify they work as expected)
   - Regression testing (ensure changes don't break existing workflows)
   - Benchmark tracking (accuracy over time)

=============================================================================
RELATIONSHIP TO POC PHASES
=============================================================================

Current POC Focus (Phase 1 & 2):
────────────────────────────────────────────────────────────────────────────
- Prove that templates CAN be extracted
- Prove that templates CAN be applied to generate BIM
- Prove that generated BIM matches original (70%+ accuracy)
- All with HARDCODED templates

Template Configurator (Phase 3+):
────────────────────────────────────────────────────────────────────────────
- Once concept is proven, build user interface
- Allow users to ADAPT templates for their needs
- Make the system PRACTICAL for real-world use
- Enable scaling to multiple projects

The configurator is the bridge between "proof of concept" and "production tool."

=============================================================================
IMPLEMENTATION TIMELINE (Post-POC)
=============================================================================

Week 1-2: CLI Configurator
  - Load templates from DB
  - Edit parameters via command line
  - Save variants to JSON
  - Basic validation

Week 3-4: GUI Skeleton
  - PyQt6 setup
  - Template tree browser
  - Basic parameter forms
  - Load/save functionality

Week 5-6: Core Features
  - Full parameter editor
  - Variant management
  - Validation tools
  - Preview system

Week 7-8: Advanced Features
  - 3D offset visualizer
  - Batch operations
  - Health report generator
  - Polish and testing

Total: ~8 weeks for MVP configurator (post-POC completion)

=============================================================================
CONCLUSION
=============================================================================

The Template Configurator is the USER-FACING TOOL that makes template-driven
BIM generation PRACTICAL. Without it, templates are static and limited.
With it, templates become adaptable, reusable, and powerful.

However, it should be built AFTER proving the core POC concept. We need
real-world data from successful conversions to know:
- Which parameters actually matter
- What validation checks are most useful
- What workflows users need
- What edge cases to handle

Build the configurator when the POC proves the concept works.

=============================================================================
DOCUMENT STATUS
=============================================================================

Status: CONCEPTUAL DESIGN
Next Steps: Complete POC Phase 1 & 2, then revisit for implementation
Owner: To be determined based on POC success
Review Date: After Phase 2 validation complete

=============================================================================
REFERENCES
=============================================================================

Related Documents:
- POC_METHODOLOGY_COMPLETE.md - Overall system design
- CURRENT_APPROACH.md - How templates are applied
- OFFSET_TEMPLATE_EXAMPLE.md - Spatial offset concept
- PHASE2_PLAN.md - Current implementation focus

=============================================================================
LAST UPDATED: 2025-11-12
=============================================================================
