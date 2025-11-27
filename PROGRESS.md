# Project Progress

## Latest Update: 2025-11-28

### Examples Structure Finalized ✅

**Crystal Clear Concept**: One PDF → One output/ folder with everything it generates

#### Structure:
```
examples/TB-LKTN_House/
├── README.md                  # Documentation
├── TB-LKTN HOUSE.pdf         # Source PDF (gitignored)
└── output/                    # ALL outputs (gitignored)
    ├── *.json                 # Placement data, validation
    ├── *.db                   # Database files
    ├── *.blend                # Blender files
    └── *.log                  # Logs
```

#### Benefits:
- **Simple**: Immediately obvious where inputs/outputs belong
- **Self-contained**: Each example is complete
- **Rule 0 Compliant**: No manual data, outputs are reference only
- **Regression Testing**: Easy to diff entire output/ folders

#### Commits:
- af04bf5 - docs(examples): Clarify crystal clear structure
- e502764 - Previous template system cleanup
- 434ae65 - Two-template system clarification

---

## Previous Work

### Database Documentation Added
- `db/README.md` - Complete database documentation
- `db/schema/ifc_object_library.sql` - Full schema definition
- `db/schema/migrations/002_add_base_rotation.sql` - Rotation migration

### Two-Template System Clarified
- **TIER 1**: `src/core/master_reference_template.json` - Extraction instructions
- **TIER 2**: `config/master_template.json` → Moved to examples (Rule 0 violation)
- Spec Section 1.2, 1.5, 14 updated

### Rule 0 Compliance
- Removed `config/master_template_CORRECTED.json` (unused)
- Moved hardcoded placement data to examples/
- All outputs now derivable from source code + input PDF only
