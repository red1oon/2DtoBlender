# Building Type Templates - Layer Mapping Patterns

**Based on Phase 1 Smart Mapping Results**

---

## Concept: Reusable Layer Patterns by Building Type

Instead of mapping every project from scratch, we create **template pattern libraries** for common building types. Each template captures:
- Common layer naming conventions
- Discipline-specific prefixes/keywords
- Regional variations
- Confidence thresholds

---

## Template Structure

```json
{
  "building_type": "airport_terminal",
  "region": "malaysia",
  "confidence_threshold": 0.7,
  "pattern_library": {
    "exact_prefixes": { ... },
    "keywords": { ... },
    "regional_terms": { ... }
  },
  "metadata": {
    "source_projects": ["Terminal 1", "KLIA2"],
    "last_updated": "2025-11-15",
    "accuracy": "91.4%"
  }
}
```

---

## 🏢 Building Type 1: Airport Terminal

**Characteristics:**
- Large open spaces (high ACMV requirements)
- Critical fire safety ("bomba" requirements)
- Passenger flow optimization
- 24/7 operations (redundant systems)

**Discovered Patterns (from Terminal 1):**

```python
AIRPORT_TERMINAL = {
  "exact_prefixes": {
    "z-ac-": "ACMV",      # Air conditioning (very common)
    "z-fire-": "FP",       # Fire systems
    "z-cw-": "CW",         # Chilled water
    "z-lpg-": "LPG",       # Gas systems
    "z-lift-": "ARC",      # Elevators/lifts
    "c-bomba": "FP",       # Fire dept requirements
    "ch-": "ARC",          # Ceiling height/finishes
  },

  "keywords": {
    "FP": ["bomba", "fire", "sprinkler", "smoke", "detector"],
    "ACMV": ["ac-", "ac ", "hvac", "duct", "griille", "tower", "cooling"],
    "SP": ["wet", "sw-", "rh-", "san", "sani", "drain", "rwdp"],
    "ARC": ["wall", "win", "window", "door", "furniture", "stair", "roof"],
    "STR": ["col", "column", "beam", "grid", "truss"],
  },

  "regional_terms": {
    "malaysia": {
      "bomba": "FP",     # Fire department
      "parit": "SP",     # Drainage
      "kira": "ARC",     # Calculate/dimensions
    }
  },

  "typical_layers": [
    "C-BOMBA HATCH", "z-ac-pump", "z-fire-alarm",
    "GRID1", "wall", "WIN", "z-cw-tank"
  ],

  "confidence_adjustments": {
    "ac-": +0.1,  # Higher weight for ACMV in airports
    "fire": +0.1, # Higher weight for fire safety
  }
}
```

**Expected Coverage:** 85-95% auto-mapping

---

## 🏥 Building Type 2: Hospital

**Characteristics:**
- Medical gas systems (O2, vacuum, compressed air)
- Intensive HVAC (infection control)
- Emergency power systems
- Patient room standardization

**Predicted Patterns:**

```python
HOSPITAL = {
  "exact_prefixes": {
    "z-ac-": "ACMV",
    "z-med-": "SP",        # Medical gases
    "z-o2-": "SP",         # Oxygen
    "z-vac-": "SP",        # Medical vacuum
    "z-ca-": "SP",         # Compressed air
    "z-fire-": "FP",
    "z-emer-": "ELEC",     # Emergency power
    "ward-": "ARC",        # Ward layouts
  },

  "keywords": {
    "SP": ["o2", "oxygen", "vacuum", "medical", "gas", "nurse"],
    "ACMV": ["isolation", "hepa", "negative pressure", "positive pressure"],
    "ELEC": ["emergency", "ups", "generator", "backup"],
    "ARC": ["ward", "room", "bed", "nurse station", "corridor"],
  },

  "unique_features": [
    "Medical gas manifolds",
    "Nurse call systems",
    "Isolation rooms",
    "Operating theaters"
  ],

  "confidence_adjustments": {
    "medical": +0.2,  # Strong indicator
    "ward": +0.15,
  }
}
```

**Expected Coverage:** 80-90% auto-mapping

---

## 🏠 Building Type 3: Residential High-Rise

**Characteristics:**
- Repetitive unit layouts
- Domestic MEP systems
- Minimal fire suppression (sprinklers less common)
- Standard ACMV (individual units)

**Predicted Patterns:**

```python
RESIDENTIAL_HIGHRISE = {
  "exact_prefixes": {
    "unit-": "ARC",
    "apt-": "ARC",
    "z-ac-": "ACMV",
    "z-sw-": "SP",         # Sewage/wastewater
    "z-domestic-": "SP",
    "balcony-": "ARC",
  },

  "keywords": {
    "ARC": ["unit", "apartment", "bedroom", "living", "kitchen",
            "balcony", "lobby", "corridor"],
    "SP": ["toilet", "bathroom", "wc", "shower", "domestic"],
    "ACMV": ["split unit", "fccu", "condenser"],
    "ELEC": ["db", "distribution board", "meter"],
  },

  "unique_features": [
    "Unit type plans (Type A, B, C)",
    "Domestic water tanks",
    "Waste chutes",
    "Lift lobbies"
  ],

  "confidence_adjustments": {
    "unit": +0.2,
    "apartment": +0.2,
  }
}
```

**Expected Coverage:** 75-85% auto-mapping

---

## 🏢 Building Type 4: Office Tower

**Characteristics:**
- Open plan layouts
- Raised floor systems
- Central ACMV (VRV/VRF)
- IT infrastructure heavy

**Predicted Patterns:**

```python
OFFICE_TOWER = {
  "exact_prefixes": {
    "z-ac-": "ACMV",
    "z-data-": "ELEC",
    "z-raised-": "ARC",    # Raised flooring
    "z-fcu-": "ACMV",      # Fan coil units
    "office-": "ARC",
  },

  "keywords": {
    "ARC": ["office", "pantry", "meeting", "board room", "reception",
            "workstation", "partition", "raised floor"],
    "ACMV": ["fcu", "vrf", "vrv", "ahu", "fahu"],
    "ELEC": ["data", "ups", "server", "comms", "it"],
    "SP": ["pantry", "toilet", "wc"],
  },

  "unique_features": [
    "Floor void spaces",
    "Data centers",
    "Meeting room clusters",
    "Core layouts"
  ],

  "confidence_adjustments": {
    "fcu": +0.15,
    "workstation": +0.15,
  }
}
```

**Expected Coverage:** 80-90% auto-mapping

---

## 🛒 Building Type 5: Retail/Mall

**Characteristics:**
- Large atriums
- Multiple tenant spaces
- Food court MEP
- Extensive signage/lighting

**Predicted Patterns:**

```python
RETAIL_MALL = {
  "exact_prefixes": {
    "tenant-": "ARC",
    "shop-": "ARC",
    "z-ac-": "ACMV",
    "z-exhaust-": "ACMV",  # Kitchen exhaust
    "z-grease-": "SP",     # Grease traps
    "atrium-": "ARC",
  },

  "keywords": {
    "ARC": ["shop", "tenant", "atrium", "escalator", "food court",
            "anchor", "retail", "mall", "corridor"],
    "ACMV": ["kitchen exhaust", "fume hood", "make-up air", "atrium"],
    "SP": ["grease", "food waste", "floor trap"],
    "ELEC": ["signage", "display", "tenant db"],
  },

  "unique_features": [
    "Tenant demarcation lines",
    "Food court clusters",
    "Anchor tenant spaces",
    "Escalator voids"
  ],

  "confidence_adjustments": {
    "tenant": +0.2,
    "food court": +0.15,
  }
}
```

**Expected Coverage:** 75-85% auto-mapping

---

## 🎯 How to Use Building Type Templates

### Workflow:

**Step 1: Detect Building Type**
```python
def detect_building_type(layer_names):
    # Score each template against layer names
    scores = {
        'airport_terminal': score_template(AIRPORT_TERMINAL, layer_names),
        'hospital': score_template(HOSPITAL, layer_names),
        'residential': score_template(RESIDENTIAL_HIGHRISE, layer_names),
        'office': score_template(OFFICE_TOWER, layer_names),
        'retail': score_template(RETAIL_MALL, layer_names),
    }

    best_match = max(scores.items(), key=lambda x: x[1])
    return best_match  # ('airport_terminal', 0.87)
```

**Step 2: Apply Template**
```python
template = load_template(detected_type)
mappings = apply_template_patterns(dxf_layers, template)
# Expected 75-95% coverage depending on type
```

**Step 3: Learn & Improve**
```python
# After user reviews 25% unmapped layers:
corrections = user_review_unmapped_layers(mappings)

# Update template for future projects
template.learn_from_corrections(corrections)
template.save()  # Now 85-95% coverage next time!
```

---

## 📊 Template Evolution Strategy

### Phase 1: Bootstrap (Current)
- Extract patterns from Terminal 1 → **Airport Terminal template**
- Auto-mapping: 81% layers, 91% entities ✅

### Phase 2: Expansion (Next 3 months)
- Process Terminal 2 → Refine airport template (→ 95%)
- Add 1 hospital project → Create hospital template
- Add 1 office project → Create office template

### Phase 3: Regional Variants (6 months)
- Malaysia variant (bomba, parit, etc.) ✅
- Singapore variant (NEA codes, PUB standards)
- Middle East variant (Ashghar codes, Arabic terms)

### Phase 4: Hybrid Types (12 months)
- Mixed-use: Retail + Office + Residential
- Transportation: Airport + Train + Ferry terminal
- Healthcare: Hospital + Clinic + Research

---

## 🎓 Learning from Outliner Grouping (Your Idea!)

**Blender Outliner Collections = Visual Pattern Recognition**

When we load the mapped elements into Blender:
```
Outliner
├── 🔥 Fire Protection (FP) - 2,063 entities
│   ├── C-BOMBA HATCH (849)
│   ├── z-fire-alarm (184)
│   └── z-fire-smoke-grille (167)
│
├── ❄️ ACMV - 780 entities
│   ├── z-ac-pump (148)
│   ├── z-ac-griille (125)
│   └── z-ac-tower (45)
│
├── 🏗️ Structure (STR) - 1,101 entities
│   ├── COL (402)
│   ├── ENGRS COLUMN T1 (192)
│   └── GRID1 (162)
│
└── ❓ Unmapped - 2,272 entities (need review)
    ├── LINE1 (1,092)
    ├── RC (315)
    └── ... (see visually what makes sense!)
```

**The Aha! Moment:**
By **seeing** the unmapped entities in 3D grouped by layer, patterns become obvious:
- "Oh, LINE1 is all perimeter walls → ARC!"
- "RC is roof contours → ARC!"
- "S is structural sections → STR!"

This visual feedback loop makes Phase 2 (user review) much faster!

---

## 💡 Next Steps

**Immediate (This Session):**
1. ✅ Phase 1 complete (81% mapped!)
2. Use layer_mappings.json to re-run conversion
3. See actual results in database

**Short-term (Next Session):**
1. Build Phase 2: Interactive review UI (terminal or web-based)
2. Review 31 unmapped layers with visual context
3. Target: 95%+ coverage

**Medium-term (This Month):**
1. Process Terminal 2 → validate template reusability
2. Extract hospital/office patterns from other projects
3. Build template library manager

**Long-term (3-6 Months):**
1. Auto-detect building type from layer analysis
2. Regional variant templates
3. ML-powered suggestions

---

**Generated from:** Phase 1 Smart Mapping Results
**Date:** November 15, 2025
**Coverage:** 81.3% layers, 91.4% entities
**Confidence:** High (95% for fire, ACMV, CW, LPG systems)
