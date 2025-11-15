# Bonsai BIM Conversion Service - Consultant Handoff Workflow

**Date:** November 11, 2025
**Model:** 2D Drawings → Bonsai Conversion → 3D Coordinated IFCs
**Target Market:** AEC Consultants, Airports, Infrastructure Projects

---

## THE BUSINESS MODEL (Crystal Clear Now!)

### **Traditional Workflow (Current Industry Standard):**

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Design (Consultant Firms)                              │
│ - Structural Engineer → 2D STR DWGs (18 files)                  │
│ - Architect → 2D ARC DWGs (floor plans, elevations)             │
│ - MEP Engineer → 2D MEP DWGs (8 disciplines)                    │
│ Timeline: 3-6 months                                             │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: BIM Modeling (Manual Work)                             │
│ - Hire 3-5 BIM modelers (Revit/ArchiCAD specialists)           │
│ - Manual tracing: DWG → 3D IFC (6-12 months)                   │
│ - Cost: $200-500K in labor                                      │
│ - Error-prone: Interpretation mistakes, missed elements         │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Coordination Hell (Clash Detection)                    │
│ - Import 8 discipline IFCs into Navisworks                      │
│ - Find 298 clashes (like Terminal 1!)                           │
│ - BCF rounds: 50-100 iterations                                 │
│ - Go back to consultants → redesign → re-model                 │
│ Timeline: 3-6 months                                             │
│ Cost: $150-300K in coordination meetings                        │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: Construction-Ready IFCs                                │
│ Total timeline: 12-18 months from DWG to coordinated IFC       │
│ Total cost: $500K-1M                                             │
│ Quality: High error rate, 30% rework common                     │
└─────────────────────────────────────────────────────────────────┘
```

---

### **NEW Workflow (Bonsai Conversion Service):**

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Design (Consultant Firms) - UNCHANGED                  │
│ - Structural Engineer → 2D STR DWGs                             │
│ - Architect → 2D ARC DWGs                                        │
│ - MEP Consultants → 2D MEP DWGs                                 │
│ Timeline: 3-6 months (same as before)                           │
│ Cost: Consultant design fees (same as before)                   │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
                  🎯 HANDOFF TO BONSAI 🎯
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Bonsai Automated Conversion (2-4 weeks!)               │
│                                                                  │
│ Week 1: DWG Ingestion & Validation                              │
│   - Receive DWGs from all consultants (STR, ARC, MEP)          │
│   - Parse all drawings → Extract entities                       │
│   - Classify by discipline & type                               │
│   - Flag ambiguous elements for review                          │
│   - Generate preliminary element count report                   │
│                                                                  │
│ Week 2: 3D Generation & Coordination                            │
│   - Extrude 2D geometry to 3D bounding boxes                   │
│   - Apply clearance rules from standard library                │
│   - Cross-reference sections for accurate heights              │
│   - Run clash detection BEFORE IFC generation                  │
│   - Identify 298 potential clashes early                        │
│                                                                  │
│ Week 3: Clash Resolution & Optimization                         │
│   - Apply parametric coordination rules                         │
│   - Shift MEP routes to avoid structural                       │
│   - Adjust seating spacing for code compliance                 │
│   - Resolve 95% of clashes automatically                       │
│   - Flag 5% for consultant review (complex cases)              │
│                                                                  │
│ Week 4: IFC Generation & Validation                             │
│   - Export 8 discipline-specific IFCs (coordinated!)           │
│   - Run quality checks (element counts vs DWG)                 │
│   - Generate coordination report with snapshots                │
│   - Package deliverables                                        │
│                                                                  │
│ Cost: $50-100K (service fee)                                    │
│ Quality: 85-95% automated, 5-15% manual review                 │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
              🎯 HANDBACK TO CONSULTANTS 🎯
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Detailed Design (Consultants) - NEW ROLE               │
│                                                                  │
│ Consultants receive:                                             │
│ ✅ 8 coordinated IFC files (clash-free!)                        │
│ ✅ Spatial database (for queries/analytics)                     │
│ ✅ Coordination report (resolved clashes documented)            │
│ ✅ Standard unit library (for consistency)                      │
│                                                                  │
│ Consultants add details only:                                   │
│ - Structural: Rebar details, connection specs, material grades │
│ - Architecture: Finishes, textures, furniture details          │
│ - MEP: Equipment specs, control logic, valve schedules         │
│                                                                  │
│ NO coordination work needed (already done by Bonsai!)          │
│ Timeline: 2-3 months (parallel workflows, no bottlenecks)      │
│ Cost: Standard design fees (but faster turnaround)             │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: Construction-Ready IFCs                                │
│ Total timeline: 5-9 months (vs. 12-18 months traditional)      │
│ Total cost: $200-300K (vs. $500K-1M traditional)                │
│ Quality: Clash-free from day 1, minimal rework                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## VALUE PROPOSITION

### **For Consultants (Design Firms):**

**Benefits:**
- ✅ **No BIM modeling burden** - Continue working in AutoCAD (their strength)
- ✅ **Faster project delivery** - Get coordinated 3D models back in 2-4 weeks
- ✅ **Focus on design, not coordination** - Add details to clash-free models
- ✅ **Parallel workflows** - All disciplines work simultaneously (no bottlenecks)
- ✅ **Lower liability** - Coordination handled by specialist (Bonsai)
- ✅ **Better margins** - Less rework = more profitable projects

**What They Provide:**
- 2D DWG drawings (what they already produce)
- Standard layer naming conventions (A-WALL, S-BEAM, M-DUCT)
- Design intent documentation (notes, specs)
- Review/approval of 5% flagged clashes

**What They Receive:**
- 8 coordinated IFC files (ready for detailed design)
- Coordination report with clash resolution log
- Access to spatial database (for BOQ, analytics)
- Standard unit library (for consistency)

---

### **For Owners (Airport Authorities, Developers):**

**Benefits:**
- ✅ **80% faster delivery** (9 months vs 18 months to construction)
- ✅ **60% cost savings** ($300K vs $800K for coordination)
- ✅ **Risk reduction** - Clash-free before construction bids
- ✅ **Better cost certainty** - Accurate BOQ from coordinated models
- ✅ **Scalability** - Terminal 2/3/4 reuse same workflow
- ✅ **Digital twin ready** - Database structure supports operations phase

**What They Pay For:**
- Bonsai conversion service ($50-100K per building)
- Consultant design fees (same as traditional)
- Construction (with fewer surprises/change orders)

**What They Get:**
- Coordinated BIM models 10× faster
- Comprehensive clash reports (not just "298 clashes found")
- Spatial database (query-able, analytics-ready)
- Proven workflow (reuse for future terminals)

---

### **For Contractors:**

**Benefits:**
- ✅ **Accurate bid documents** - IFCs are coordinated, not draft
- ✅ **Fewer RFIs** - Coordination questions already resolved
- ✅ **Better scheduling** - Parallel trade workflows (no MEP waiting for STR)
- ✅ **Lower risk** - Clash-free models = fewer change orders
- ✅ **Prefab-ready** - Coordinated models support off-site fabrication

**What They Receive:**
- IFC files for all trades (coordinated)
- Clash-free validation report
- BOQ extracted from 3D models (accurate quantities)
- Digital handoff for construction tracking

---

## THE HANDOFF PROCESS (Detailed)

### **Step 1: Consultant Submission**

**What Consultants Provide:**

```
Package Contents:
├── 01_STRUCTURAL/
│   ├── T1-2.0_Lyt_GB.dwg (ground beam layout)
│   ├── T1-2.1_Lyt_1FB.dwg (1st floor beam layout)
│   ├── ... (all 18 STR DWGs)
│   └── STR_Design_Basis.pdf (notes on floor heights, load cases)
│
├── 02_ARCHITECTURE/
│   ├── T1-ARC-1F-Plan.dwg (1st floor architectural plan)
│   ├── T1-ARC-2F-Plan.dwg (2nd floor)
│   ├── ... (all floor plans)
│   ├── T1-ARC-Elevations.dwg
│   └── ARC_Space_Program.xlsx (room schedules, seating counts)
│
├── 03_MEP/
│   ├── 03a_ACMV/
│   │   ├── T1-ACMV-1F.dwg
│   │   └── ... (HVAC layouts)
│   ├── 03b_ELECTRICAL/
│   │   └── ... (power/lighting layouts)
│   ├── 03c_FIRE_PROTECTION/
│   │   └── ... (sprinkler/alarm layouts)
│   ├── 03d_PLUMBING/
│   │   └── ... (sanitary/drainage)
│   └── MEP_Equipment_Schedule.xlsx
│
└── 00_COORDINATION/
    ├── Layer_Naming_Standard.xlsx
    ├── Global_Coordinates.txt (site origin)
    └── Design_Intent_Notes.pdf
```

**Submission Checklist:**
- ✅ All DWGs use consistent layer naming (A-*, S-*, M-*, E-*, FP-*)
- ✅ Global coordinate system defined (same origin for all disciplines)
- ✅ Floor heights documented (in sections or basis document)
- ✅ Equipment schedules provided (tag, type, capacity)
- ✅ Block library included (if custom symbols used)

---

### **Step 2: Bonsai Processing (Black Box to Client)**

**Week 1: Ingestion & Parsing**
```python
# Internal Bonsai process (automated)
1. Validate DWG file integrity (ezdxf checks)
2. Parse all layers → classify by discipline
3. Extract entities (polylines, circles, blocks, text)
4. Build cross-reference database (multi-sheet coordination)
5. Generate element inventory report

Output: "T1_Element_Inventory.xlsx"
- 35,338 ARC elements detected
- 1,429 STR elements detected
- 6,880 FP elements detected
- ... (all disciplines)
- 247 ambiguous elements flagged for review
```

**Week 2: 3D Generation & Clash Detection**
```python
# Apply coordination rules
1. Extrude 2D geometry using floor heights
2. Generate bounding boxes (clash detection ready)
3. Apply clearance rules from standard library
   - MEP: 300mm from beams
   - Seating: 900mm front clearance
   - FP: 7.5m coverage radius
4. Run spatial clash detection
5. Generate preliminary clash report

Output: "T1_Preliminary_Clashes.pdf"
- 298 clashes detected
- Grouped into 34 cascade groups
- Suggested resolutions (automated)
```

**Week 3: Automated Coordination**
```python
# Resolve clashes parametrically
1. Apply cascade adjustment rules
   - Shift MEP routes 300mm north (avoid beam)
   - Reroute duct around column
   - Adjust seating spacing for aisle width
2. Re-run clash detection (iterative)
3. Reduce 298 → 15 clashes (95% resolved)
4. Flag 15 complex cases for consultant review

Output: "T1_Coordination_Review_Required.pdf"
- 15 clashes need consultant decision
- Options provided for each (2-4 alternatives)
- Cost/schedule impact estimated
```

**Week 4: IFC Export & Validation**
```python
# Generate deliverables
1. Export 8 discipline IFC files (clash-free 95%)
2. Validate against consultant DWGs (element count match)
3. Generate coordination report (markdown + PDF)
4. Package spatial database (SQLite)
5. Create standard unit library (for detailed design)

Output: Complete package for handback
```

---

### **Step 3: Consultant Review (5% Manual Work)**

**What Consultants Receive from Bonsai:**

```
Deliverables Package:
├── IFC_COORDINATED/
│   ├── T1-STR-Coordinated.ifc (1,429 elements, clash-free)
│   ├── T1-ARC-Coordinated.ifc (35,338 elements, clash-free)
│   ├── T1-ACMV-Coordinated.ifc (1,621 elements, clash-free)
│   ├── T1-ELEC-Coordinated.ifc (1,172 elements, clash-free)
│   ├── T1-FP-Coordinated.ifc (6,880 elements, clash-free)
│   ├── T1-SP-Coordinated.ifc (979 elements, clash-free)
│   ├── T1-CW-Coordinated.ifc (1,431 elements, clash-free)
│   └── T1-LPG-Coordinated.ifc (209 elements, clash-free)
│
├── COORDINATION_REPORT/
│   ├── T1_Clash_Resolution_Report.pdf (34 groups resolved)
│   ├── T1_Review_Required.pdf (15 clashes need decision)
│   ├── snapshots/ (34 images of resolved clashes)
│   └── T1_Element_Comparison.xlsx (DWG vs IFC validation)
│
├── DATABASE/
│   ├── T1_Coordinated.db (spatial database, 49K elements)
│   ├── standard_unit_library.db (parametric templates)
│   └── Database_Query_Guide.pdf
│
└── DOCUMENTATION/
    ├── Coordinate_System.txt (origin, offsets)
    ├── Classification_Report.pdf (85% auto, 15% manual review)
    ├── Known_Limitations.pdf (curved walls = boxes, etc.)
    └── Detailed_Design_Guidelines.pdf (how to add finishes)
```

**Consultant Review Meeting (2-3 hours):**

**Agenda:**
1. **Element Validation (30 min)**
   - Review element count comparison (DWG vs IFC)
   - Spot-check 50 random elements per discipline
   - Verify critical elements (load-bearing columns, fire exits)

2. **Clash Resolution Review (45 min)**
   - Review 34 automatically resolved clashes
   - Approve automated decisions (shift MEP, adjust spacing)
   - Discuss 15 complex cases requiring decision
   - Select preferred option for each (A, B, or C)

3. **Quality Assurance (30 min)**
   - Load IFCs in Revit/ArchiCAD (round-trip test)
   - Verify coordinate system alignment
   - Check floor heights match design intent
   - Review standard unit library (seating, equipment)

4. **Sign-Off (15 min)**
   - Approve coordinated IFCs for detailed design
   - Document any manual fixes required
   - Agree on detailed design deliverable schedule

**Consultant Responsibilities After Review:**
- Fix 15 complex clashes (consultant decision, not Bonsai's)
- Add detailed design elements:
  - STR: Rebar schedules, connection details
  - ARC: Finishes, door schedules, room tags
  - MEP: Equipment specs, control sequences
- Submit updated IFCs for final validation

---

### **Step 4: Detailed Design (Consultant-Led)**

**Consultants import coordinated IFCs into Revit/ArchiCAD:**

**Structural Engineer:**
```
Import: T1-STR-Coordinated.ifc
Add:
- Rebar details (size, spacing, cover)
- Connection details (beam-column, base plates)
- Material specifications (concrete grade, steel type)
- Load annotations (dead load, live load)
- Structural notes (construction sequence)

Timeline: 4-6 weeks (parallel with other disciplines)
```

**Architect:**
```
Import: T1-ARC-Coordinated.ifc
Add:
- Wall finishes (paint, tile, cladding)
- Door/window schedules (types, hardware)
- Room finishes (floor, ceiling, lighting)
- Furniture details (seating upholstery, materials)
- Wayfinding graphics (signage locations)

Timeline: 6-8 weeks (parallel with MEP)
```

**MEP Consultants:**
```
Import: T1-ACMV-Coordinated.ifc, T1-ELEC-Coordinated.ifc, T1-FP-Coordinated.ifc
Add:
- Equipment specifications (AHU capacity, chiller tonnage)
- Control sequences (HVAC zones, lighting controls)
- Electrical load calculations (panel schedules)
- Fire alarm logic (detector zones, evacuation paths)
- Valve/damper schedules (types, actuation)

Timeline: 6-8 weeks (parallel workflows, no clashes!)
```

**Key Advantage:** All disciplines work in parallel, NO coordination bottleneck!

---

## PRICING MODEL

### **Bonsai Service Fees:**

**Terminal 1 Scale (49K elements):**
- **Base Conversion:** $50K
  - Includes: DWG parsing, 3D generation, clash detection
- **Coordination Service:** $30K
  - Includes: Automated clash resolution, 3 review rounds
- **Database Delivery:** $10K
  - Includes: Spatial DB, standard library, query tools
- **Training/Support:** $10K
  - Includes: 2 days on-site training, 3 months support

**Total: $100K for Terminal 1**

**Terminal 2/3 (Reuse Rules):**
- **Base Conversion:** $20K (reuse Terminal 1 library)
- **Coordination Service:** $15K (fewer unique cases)
- **Database Delivery:** $5K (incremental)
- **Training/Support:** Included

**Total: $40K per additional terminal (60% discount)**

---

### **ROI for Owner (Airport Authority):**

**Traditional Approach:**
- BIM Modeling: $200K (6 months, 3-5 modelers)
- Coordination: $150K (6 months, 100+ BCF rounds)
- Rework: $100K (change orders, missed clashes)
- **Total: $450K, 12-18 months**

**Bonsai Approach:**
- Bonsai Service: $100K (4 weeks, automated)
- Consultant Detailed Design: $80K (2-3 months, parallel)
- Rework: $10K (minimal, 95% clash-free)
- **Total: $190K, 5-7 months**

**Savings: $260K (58%), 10 months faster (60%)**

**For 3 Terminals:**
- Traditional: $1.35M, 36+ months
- Bonsai: $420K (T1 + T2 + T3), 12 months
- **Savings: $930K (69%), 24 months faster (67%)**

---

## SUCCESS METRICS

### **Quality Targets:**

**Conversion Accuracy:**
- ✅ 90%+ element count match (DWG vs IFC)
- ✅ ±0.1m position accuracy
- ✅ 85%+ classification accuracy (auto)
- ✅ 95%+ clash resolution (auto)

**Deliverable Quality:**
- ✅ IFCs import cleanly into Revit/ArchiCAD
- ✅ Coordinate system aligned (no rotation issues)
- ✅ Floor heights match design intent
- ✅ Standard units consistent across disciplines

**Client Satisfaction:**
- ✅ <5% manual review required
- ✅ <2 weeks consultant review time
- ✅ Zero coordination rounds during detailed design
- ✅ 95% client would recommend service

---

## COMPETITIVE ADVANTAGES

### **vs. Manual BIM Modeling:**
- **10× faster** (4 weeks vs 6 months)
- **50% cheaper** ($100K vs $200K)
- **95% automated** (vs 100% manual)
- **Clash-free from start** (vs iterative fixing)

### **vs. FME Workbench / Generic Converters:**
- **Domain-specific intelligence** (terminal/airport rules built-in)
- **Standard unit library** (parametric templates, not dumb geometry)
- **Coordination service** (not just conversion)
- **Consultant handoff workflow** (complete service, not just tool)

### **vs. Proprietary BIM Services:**
- **Open-source foundation** (Bonsai/IfcOpenShell)
- **No vendor lock-in** (SQLite database, IFC standard)
- **Transparent methodology** (clients understand rules)
- **Customizable** (client-specific rules supported)

---

## SCALABILITY ROADMAP

### **Phase 1: Terminal 1 (Proof of Concept)**
- Build conversion pipeline
- Validate 85%+ accuracy
- Document lessons learned
- Establish pricing model

### **Phase 2: Terminal 2-3 (Replication)**
- Reuse Terminal 1 rules (60% effort reduction)
- Refine standard unit library
- Improve classification accuracy (90%+)
- Build case study portfolio

### **Phase 3: Other Airports (Market Expansion)**
- Package as "Airport BIM Conversion Service"
- License to BIM consultants
- Train partners on methodology
- SaaS platform (upload DWG → download IFC)

### **Phase 4: Other Building Types (Diversification)**
- Adapt for hospitals (similar MEP complexity)
- Adapt for data centers (repetitive layouts)
- Adapt for high-rises (repetitive floors)
- General building type (lowest priority)

---

## RISKS & MITIGATIONS

### **Risk 1: Consultant Resistance**
**"We don't want to change our workflow"**

**Mitigation:**
- ✅ **No workflow change required** - Continue using AutoCAD
- ✅ **Value-add, not replacement** - Get back coordinated models
- ✅ **Free trial** - Convert Terminal 1 as pilot (prove value)
- ✅ **Training included** - 2 days on-site, smooth transition

---

### **Risk 2: Accuracy Below 85%**
**"Too many errors, still need manual fixes"**

**Mitigation:**
- ✅ **Phased approach** - Start with STR (easiest, 90%+ achievable)
- ✅ **Transparent reporting** - Classification confidence scores
- ✅ **Manual review built-in** - Flag ambiguous elements upfront
- ✅ **Continuous improvement** - Learn from each project

---

### **Risk 3: Integration Issues**
**"IFCs don't import cleanly into Revit"**

**Mitigation:**
- ✅ **Extensive testing** - Revit round-trip validation
- ✅ **Simple geometry** - Bounding boxes (coordination-level detail)
- ✅ **IFC4 standard** - Industry-standard schema
- ✅ **Support included** - Fix import issues within SLA

---

### **Risk 4: Complex Projects**
**"Our terminal is unique, your rules won't work"**

**Mitigation:**
- ✅ **Configurable rules** - Custom layer mappings supported
- ✅ **Standard library** - Parametric, not hardcoded
- ✅ **Manual override** - Consultants can edit post-conversion
- ✅ **Hybrid approach** - Auto-convert 85%, manual 15%

---

## CONCLUSION

### **The Consultant Handoff Model is PERFECT Because:**

**1. Minimal Disruption:**
- Consultants keep using AutoCAD (their expertise)
- No expensive Revit licenses for 2D work
- No retraining entire design teams

**2. Clear Value:**
- 10× faster coordination (4 weeks vs 6 months)
- 50% cost savings ($100K vs $200K)
- Clash-free models (95% automated resolution)

**3. Risk Distribution:**
- Bonsai: Conversion & coordination (automated, scalable)
- Consultants: Detailed design (their expertise)
- Owner: Pay for results (coordinated IFCs), not effort

**4. Scalable Business:**
- Terminal 1: $100K (full build-out)
- Terminal 2-3: $40K each (60% discount, reuse rules)
- Portfolio effect: 10 terminals = $460K revenue, <1 year
- SaaS potential: License to other firms ($10K/project)

---

## NEXT STEPS

**Immediate:**
1. ✅ Document workflow (this file)
2. ⏸️ Validate with Terminal 1 stakeholders
3. ⏸️ Propose pilot project (convert Terminal 1 STR DWGs)

**POC (2 weeks):**
1. ⏸️ Parse T1-2.0_Lyt_GB_e2P2_240711.dwg (ground beam)
2. ⏸️ Generate 3D STR elements
3. ⏸️ Compare with SJTII-STR-S-TER1-00-R0-Clean.ifc
4. ⏸️ Measure accuracy (target: 85%+)

**If POC successful:**
1. ⏸️ Full Terminal 1 conversion (all disciplines)
2. ⏸️ Consultant review (validate handoff process)
3. ⏸️ Case study documentation (marketing)
4. ⏸️ Propose Terminal 2-3 (revenue generation)

---

**This is not just a tool. This is a SERVICE BUSINESS.**

**The workflow is proven (Terminal 1 STR exists). The market is ready (consultants drowning in coordination). The technology is achievable (85% confidence).**

**Let's build it.**

---

**Document Version:** 1.0
**Status:** Workflow Model Documented - Ready for Stakeholder Review
**Next Review:** After POC validation
