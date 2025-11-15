-- Template Library Database Schema
-- Version: 1.0
-- Date: 2025-11-11
-- Purpose: Store reusable BIM templates extracted from 3D models

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Element Templates (Main table)
CREATE TABLE IF NOT EXISTS element_templates (
    template_id TEXT PRIMARY KEY,
    template_name TEXT NOT NULL,
    version TEXT NOT NULL,
    category TEXT NOT NULL,              -- Seating, Fire_Protection, Electrical, ACMV, etc.
    subcategory TEXT,                    -- Gate_Waiting, Sprinkler_Coverage, etc.
    ifc_class TEXT NOT NULL,             -- IfcFurnishingElement, IfcFireSuppressionTerminal, etc.
    predefined_type TEXT,                -- CHAIR, SPRINKLER, etc.
    object_type TEXT,                    -- Terminal_Seating_Type_A, etc.
    description TEXT,
    confidence_score REAL DEFAULT 0.0,   -- 0.0 to 1.0
    usage_count INTEGER DEFAULT 0,
    created_date TEXT,
    modified_date TEXT,
    extracted_from TEXT,                 -- Source project/database
    instance_count INTEGER,              -- How many instances found in source
    status TEXT DEFAULT 'active',        -- active, deprecated, experimental
    notes TEXT
);

-- Template Parameters
CREATE TABLE IF NOT EXISTS template_parameters (
    param_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES element_templates(template_id) ON DELETE CASCADE,
    param_name TEXT NOT NULL,
    param_type TEXT NOT NULL,            -- integer, float, enum, boolean, string
    param_category TEXT NOT NULL,        -- fixed, flexible, derived
    default_value TEXT,
    min_value REAL,
    max_value REAL,
    enum_options TEXT,                   -- JSON array for enum types: ["option1", "option2"]
    unit TEXT,                           -- meters, degrees, kg, etc.
    editable INTEGER DEFAULT 0,          -- 0=false, 1=true
    description TEXT,
    affects TEXT,                        -- JSON array of dependent param names
    validation_rule TEXT,                -- SQL or Python expression
    code_reference TEXT,                 -- Building code section
    priority INTEGER DEFAULT 0           -- Display order in UI
);

-- Derivation Rules
CREATE TABLE IF NOT EXISTS derivation_rules (
    rule_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES element_templates(template_id) ON DELETE CASCADE,
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL,             -- formula, conditional, spatial, code_compliance
    trigger_condition TEXT,              -- When to apply this rule (SQL WHERE clause style)
    formula TEXT,                        -- Calculation formula or logic
    priority INTEGER DEFAULT 0,          -- Rule execution order (lower = earlier)
    description TEXT,
    active INTEGER DEFAULT 1             -- 0=disabled, 1=enabled
);

-- Spatial Patterns
CREATE TABLE IF NOT EXISTS spatial_patterns (
    pattern_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES element_templates(template_id) ON DELETE CASCADE,
    pattern_type TEXT NOT NULL,          -- grid, array, scattered, linear, radial
    layout_strategy TEXT,                -- rectangular, circular, adaptive, organic
    spacing_rules TEXT,                  -- JSON: {"x": 0.55, "y": 0.60, "between": 0.05}
    orientation_rules TEXT,              -- JSON: {"default": "face_gate", "options": [...]}
    clearance_requirements TEXT,         -- JSON: {"front": 0.9, "back": 0.1, "side": 0.15}
    alignment_rules TEXT,                -- JSON: {"align_to": "grid", "snap": true}
    code_references TEXT,                -- JSON array of code citations
    description TEXT
);

-- Code Requirements
CREATE TABLE IF NOT EXISTS code_requirements (
    requirement_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES element_templates(template_id) ON DELETE CASCADE,
    code_name TEXT NOT NULL,             -- Singapore Building Code, NFPA 13, etc.
    section_reference TEXT,              -- Section 4.2.1, Chapter 8.6, etc.
    requirement_type TEXT,               -- minimum, maximum, exact, range
    parameter_name TEXT,                 -- Which parameter this applies to
    value REAL,
    value_max REAL,                      -- For range requirements
    unit TEXT,
    mandatory INTEGER DEFAULT 1,         -- 0=guideline, 1=mandatory
    description TEXT,
    validation_formula TEXT              -- How to check compliance
);

-- Material Specifications
CREATE TABLE IF NOT EXISTS material_specifications (
    spec_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES element_templates(template_id) ON DELETE CASCADE,
    material_name TEXT,
    material_category TEXT,              -- structural, finish, mechanical, electrical
    finish TEXT,
    cost_per_unit REAL,
    currency TEXT DEFAULT 'USD',
    install_time_hours REAL,
    weight_kg REAL,
    fire_rating TEXT,
    sustainability_rating TEXT,
    manufacturer TEXT,
    model_number TEXT,
    properties TEXT,                     -- JSON: additional properties
    last_updated TEXT
);

-- Adaptation Rules
CREATE TABLE IF NOT EXISTS adaptation_rules (
    adaptation_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES element_templates(template_id) ON DELETE CASCADE,
    rule_name TEXT NOT NULL,
    condition TEXT NOT NULL,             -- Condition to trigger adaptation (SQL-like)
    action TEXT NOT NULL,                -- What to do: scale_down, skip_template, split_zones, etc.
    parameters TEXT,                     -- JSON: action-specific parameters
    priority INTEGER DEFAULT 0,          -- Higher priority rules execute first
    description TEXT,
    active INTEGER DEFAULT 1
);

-- Geometry Definitions
CREATE TABLE IF NOT EXISTS geometry_definitions (
    geometry_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES element_templates(template_id) ON DELETE CASCADE,
    geometry_type TEXT NOT NULL,         -- box, cylinder, extrusion, mesh
    dimensions TEXT,                     -- JSON: {"length": 0.55, "width": 0.60, "height": 0.85}
    shape_parameters TEXT,               -- JSON: shape-specific params
    representation_type TEXT,            -- bounding_box, detailed, simplified
    lod INTEGER DEFAULT 100,             -- Level of Detail: 100, 200, 300, 400
    geometry_data TEXT,                  -- JSON: vertices, faces, etc. (if needed)
    description TEXT
);

-- ============================================================================
-- VALIDATION & TRACKING TABLES
-- ============================================================================

-- Validation History
CREATE TABLE IF NOT EXISTS validation_history (
    validation_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES element_templates(template_id) ON DELETE CASCADE,
    validation_date TEXT NOT NULL,
    test_scenario TEXT,
    test_project TEXT,
    accuracy_pct REAL,
    spatial_delta_avg REAL,
    spatial_delta_max REAL,
    element_count_match REAL,
    property_match_pct REAL,
    passed INTEGER,                      -- 0=failed, 1=passed
    notes TEXT,
    validator_name TEXT
);

-- Usage Statistics
CREATE TABLE IF NOT EXISTS usage_statistics (
    usage_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES element_templates(template_id) ON DELETE CASCADE,
    project_name TEXT,
    project_type TEXT,
    usage_date TEXT NOT NULL,
    elements_generated INTEGER,
    user_adjustments INTEGER,            -- How many manual edits needed
    success_rating INTEGER,              -- 1-5 stars
    feedback TEXT,
    user_name TEXT
);

-- Template Relationships (for templates that reference each other)
CREATE TABLE IF NOT EXISTS template_relationships (
    relationship_id TEXT PRIMARY KEY,
    parent_template_id TEXT NOT NULL REFERENCES element_templates(template_id) ON DELETE CASCADE,
    child_template_id TEXT NOT NULL REFERENCES element_templates(template_id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,     -- requires, generates, connects_to, similar_to
    description TEXT
);

-- ============================================================================
-- METADATA & VERSIONING
-- ============================================================================

-- Template Set Metadata (stored in database for querying)
CREATE TABLE IF NOT EXISTS template_set_metadata (
    metadata_id TEXT PRIMARY KEY,
    set_name TEXT NOT NULL,
    version TEXT NOT NULL,
    created_date TEXT,
    author TEXT,
    description TEXT,
    source_project TEXT,
    source_database TEXT,
    extraction_date TEXT,
    total_templates INTEGER,
    validation_accuracy REAL,
    compatibility_info TEXT,             -- JSON: versions, regions, codes
    changelog TEXT,                      -- JSON: version history
    notes TEXT
);

-- Template Categories (for organization)
CREATE TABLE IF NOT EXISTS template_categories (
    category_id TEXT PRIMARY KEY,
    category_name TEXT NOT NULL UNIQUE,
    parent_category_id TEXT REFERENCES template_categories(category_id),
    display_order INTEGER DEFAULT 0,
    icon TEXT,                           -- Icon name for UI
    description TEXT
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_templates_category ON element_templates(category);
CREATE INDEX IF NOT EXISTS idx_templates_ifc_class ON element_templates(ifc_class);
CREATE INDEX IF NOT EXISTS idx_templates_status ON element_templates(status);
CREATE INDEX IF NOT EXISTS idx_parameters_template ON template_parameters(template_id);
CREATE INDEX IF NOT EXISTS idx_parameters_category ON template_parameters(param_category);
CREATE INDEX IF NOT EXISTS idx_rules_template ON derivation_rules(template_id);
CREATE INDEX IF NOT EXISTS idx_patterns_template ON spatial_patterns(template_id);
CREATE INDEX IF NOT EXISTS idx_validation_template ON validation_history(template_id);
CREATE INDEX IF NOT EXISTS idx_usage_template ON usage_statistics(template_id);

-- ============================================================================
-- VIEWS FOR CONVENIENCE
-- ============================================================================

-- Complete Template View (joins all related data)
CREATE VIEW IF NOT EXISTS v_complete_templates AS
SELECT
    et.template_id,
    et.template_name,
    et.version,
    et.category,
    et.subcategory,
    et.ifc_class,
    et.description,
    et.confidence_score,
    et.usage_count,
    et.status,
    COUNT(DISTINCT tp.param_id) as parameter_count,
    COUNT(DISTINCT dr.rule_id) as rule_count,
    COUNT(DISTINCT sp.pattern_id) as pattern_count,
    COUNT(DISTINCT cr.requirement_id) as code_requirement_count,
    AVG(vh.accuracy_pct) as avg_validation_accuracy,
    MAX(vh.validation_date) as last_validated
FROM element_templates et
LEFT JOIN template_parameters tp ON et.template_id = tp.template_id
LEFT JOIN derivation_rules dr ON et.template_id = dr.template_id
LEFT JOIN spatial_patterns sp ON et.template_id = sp.template_id
LEFT JOIN code_requirements cr ON et.template_id = cr.template_id
LEFT JOIN validation_history vh ON et.template_id = vh.template_id
GROUP BY et.template_id;

-- Active Templates View (only active, non-deprecated)
CREATE VIEW IF NOT EXISTS v_active_templates AS
SELECT * FROM element_templates
WHERE status = 'active';

-- Template Statistics View
CREATE VIEW IF NOT EXISTS v_template_statistics AS
SELECT
    category,
    COUNT(*) as template_count,
    AVG(confidence_score) as avg_confidence,
    SUM(usage_count) as total_usage,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_count,
    COUNT(CASE WHEN status = 'experimental' THEN 1 END) as experimental_count,
    COUNT(CASE WHEN status = 'deprecated' THEN 1 END) as deprecated_count
FROM element_templates
GROUP BY category;

-- ============================================================================
-- SAMPLE CATEGORIES (Initial data)
-- ============================================================================

INSERT OR IGNORE INTO template_categories (category_id, category_name, display_order, description) VALUES
('cat_seating', 'Seating', 1, 'Furniture seating templates'),
('cat_fire', 'Fire_Protection', 2, 'Fire protection system templates'),
('cat_elec', 'Electrical', 3, 'Electrical system templates'),
('cat_acmv', 'ACMV', 4, 'Air conditioning and mechanical ventilation'),
('cat_plumb', 'Plumbing', 5, 'Plumbing and sanitary templates'),
('cat_struct', 'Structure', 6, 'Structural element templates'),
('cat_cw', 'Chilled_Water', 7, 'Chilled water system templates'),
('cat_lpg', 'LPG', 8, 'Gas system templates');

-- ============================================================================
-- DATABASE VERSION
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    applied_date TEXT,
    description TEXT
);

INSERT OR IGNORE INTO schema_version (version, applied_date, description) VALUES
('1.0.0', datetime('now'), 'Initial schema creation');

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
