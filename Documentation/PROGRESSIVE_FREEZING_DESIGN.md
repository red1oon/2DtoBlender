=============================================================================
PROGRESSIVE FREEZING & CONSTRAINT RESOLUTION DESIGN
=============================================================================

Document Type: Advanced Refinement Strategy
Created: November 12, 2025
Status: Research & Design (Future Implementation)
Purpose: Solve the "moving target" problem in multi-pass BIM generation

=============================================================================
THE PROBLEM: OSCILLATION & DIVERGENCE
=============================================================================

When refining generated BIM elements across multiple passes, adjustments to
one element can disturb others, creating cascading changes that may never
converge to a stable solution.

Example Failure Case (Without Freezing):
────────────────────────────────────────────────────────────────────────────

Iteration 1:
  - Pipe A adjusted to avoid Wall X → moves to position P1
  - Pipe B adjusted to connect to Pipe A at P1

Iteration 2:
  - Pipe A adjusted to avoid new Duct C → moves to position P2
  - Pipe B now disconnected! → tries to reconnect, moves to P2
  - But moving Pipe B breaks connection to Valve D!

Iteration 3:
  - Valve D moves to reconnect to Pipe B
  - But Valve D now penetrates Wall Y!
  - Adjust Valve D → breaks connection again...

Result: ❌ Never converges! Infinite adjustments.

=============================================================================
THE SOLUTION: PROGRESSIVE FREEZING
=============================================================================

Core Concept (Analogy: Rubik's Cube):
────────────────────────────────────────────────────────────────────────────

Just like solving a Rubik's Cube:
1. Solve the cross (required corners) → LOCK them
2. Solve first layer (strong edges) → LOCK them
3. Solve second layer (medium) → LOCK them
4. Orient last layer (weak) → finalize

Once a piece is correctly positioned, LOCK IT so subsequent moves don't
disturb it. This ensures forward progress toward solution.

In BIM Generation:
────────────────────────────────────────────────────────────────────────────

1. Place structural elements (walls, slabs) → FREEZE
2. Place primary MEP (mains, risers) → FREEZE
3. Place secondary MEP (branches) → FREEZE
4. Place terminals (fixtures, diffusers) → finalize

Elements are frozen when:
  ✓ All constraints satisfied
  ✓ Position stable for N iterations
  ✓ No pending adjustments
  ✓ Validation checks passed

Frozen elements become ANCHORS that constrain subsequent adjustments.

=============================================================================
CONSTRAINT HIERARCHY (THE KEY INSIGHT)
=============================================================================

Elements have STRENGTH levels determining adjustment priority:

┌─────────────┬──────────────────────┬────────────────────┬──────────────┐
│ Strength    │ Examples             │ Adjustment Policy  │ Freeze After │
├─────────────┼──────────────────────┼────────────────────┼──────────────┤
│ REQUIRED    │ Structural walls     │ Never adjust       │ Immediately  │
│ (1000)      │ Explicitly placed    │ Must stay in place │              │
│             │ Boundary elements    │                    │              │
├─────────────┼──────────────────────┼────────────────────┼──────────────┤
│ STRONG      │ Doors, windows       │ Adjust only if     │ 2 iterations │
│ (100)       │ MEP mains/risers     │ absolutely needed  │              │
│             │ Primary circulation  │                    │              │
├─────────────┼──────────────────────┼────────────────────┼──────────────┤
│ MEDIUM      │ MEP branches         │ Can adjust to fit  │ 5 iterations │
│ (10)        │ Furniture            │ other elements     │              │
│             │ Secondary elements   │                    │              │
├─────────────┼──────────────────────┼────────────────────┼──────────────┤
│ WEAK        │ Terminals (fixtures) │ Freely adjustable  │ Never frozen │
│ (1)         │ Light fixtures       │ Fit to environment │ (always flex)│
│             │ Sprinklers           │                    │              │
└─────────────┴──────────────────────┴────────────────────┴──────────────┘

Constraint Satisfaction Order:
────────────────────────────────────────────────────────────────────────────

1. REQUIRED constraints ALWAYS satisfied (highest priority)
2. STRONG constraints satisfied if possible (don't break REQUIRED)
3. MEDIUM constraints satisfied if possible (don't break STRONG)
4. WEAK constraints sacrificed first (lowest priority)

This creates a HIERARCHY where strong elements constrain weak elements,
never the reverse.

=============================================================================
MATHEMATICAL FORMULATION
=============================================================================

State Space:
────────────────────────────────────────────────────────────────────────────

S = {s₁, s₂, ..., sₙ}  where sᵢ = state of element i

sᵢ = {
  position: (x, y, z),
  rotation: θ,
  connections: [c₁, c₂, ...],
  status: {tentative, validated, frozen},
  strength: {required, strong, medium, weak}
}

Constraint Set:
────────────────────────────────────────────────────────────────────────────

C = {c₁, c₂, ..., cₘ}  where cⱼ = constraint j

cⱼ = {
  type: {geometric, topological, semantic},
  strength: {required, strong, medium, weak},
  affected_elements: [i, j, k, ...],
  satisfaction_fn: f(sᵢ, sⱼ, ...) → [0, 1]  // 0=violated, 1=satisfied
}

Constraint Types:
────────────────────────────────────────────────────────────────────────────

Geometric Constraints:
  - no_clash(i, j): elements i and j don't intersect
  - distance(i, j, d): distance between i and j equals d
  - aligned(i, j, axis): elements i and j aligned on axis
  - within_bounds(i, boundary): element i inside boundary
  - clearance(i, j, d): minimum distance d between i and j

Topological Constraints:
  - connected(i, j): elements i and j are connected
  - network_continuity(N): network N has no isolated segments
  - flow_direction(i→j): flow from i to j (not j to i)
  - endpoint_snap(i, j, tolerance): i's endpoint within tolerance of j

Semantic Constraints:
  - layer_consistency(i): element on correct layer for its type
  - spacing_rule(elements, spacing): elements spaced per rule
  - code_compliance(i, code): element meets building code
  - dimensional_sanity(i, min, max): element size within bounds

Freezing Function:
────────────────────────────────────────────────────────────────────────────

freeze(element i) = {
  if status(i) == frozen:
    return  // Already frozen, immutable

  if ∀ cⱼ ∈ constraints_affecting(i):
    satisfaction(cⱼ) >= threshold(strength(cⱼ))  // Constraints satisfied
    AND
    strength(cⱼ) >= minimum_strength              // Only meaningful constraints
    AND
    stable_for(i) >= freeze_threshold(strength(i)) // Stable for N iterations

  then:
    status(i) = frozen
    frozen_at_iteration = current_iteration
    log_freeze(i, reason="all constraints satisfied")
    propagate_freeze(connected_elements)  // May trigger cascade
}

Stability Threshold by Strength:
────────────────────────────────────────────────────────────────────────────

freeze_threshold(strength) = {
  REQUIRED: 0 iterations  // Freeze immediately
  STRONG:   2 iterations  // Stable for 2 passes
  MEDIUM:   5 iterations  // Stable for 5 passes
  WEAK:     ∞             // Never freeze (always adjustable)
}

=============================================================================
ITERATION ALGORITHM
=============================================================================

Pseudocode:
────────────────────────────────────────────────────────────────────────────

def solve_with_progressive_freezing(elements, constraints, max_iterations=50):
    iteration = 0
    stability_counter = {e.id: 0 for e in elements}

    while iteration < max_iterations:
        changed_count = 0

        # ═══════════════════════════════════════════════════════════════
        # PHASE 1: Process constraints by strength (Required → Weak)
        # ═══════════════════════════════════════════════════════════════

        for strength in [REQUIRED, STRONG, MEDIUM, WEAK]:
            for constraint in get_constraints_by_strength(strength):
                # Skip if all affected elements are frozen
                if all(e.status == FROZEN for e in constraint.affected_elements):
                    continue

                # Check satisfaction
                satisfaction = constraint.evaluate()

                if satisfaction < 1.0:  # Constraint not satisfied
                    # Try to satisfy by adjusting unfrozen elements
                    adjustable = [e for e in constraint.affected_elements
                                  if e.status != FROZEN]

                    if len(adjustable) == 0:
                        # All elements frozen, constraint cannot be satisfied
                        log_warning(f"Frozen constraint violation: {constraint}")
                        continue

                    # Adjust elements to satisfy constraint
                    # Prefer adjusting weaker elements over stronger
                    adjustable.sort(key=lambda e: e.strength)

                    success = attempt_satisfaction(constraint, adjustable)

                    if success:
                        changed_count += len(adjustable)
                        for e in adjustable:
                            stability_counter[e.id] = 0  # Reset stability
                    else:
                        log_warning(f"Could not satisfy: {constraint}")

        # ═══════════════════════════════════════════════════════════════
        # PHASE 2: Update stability counters and check for freezing
        # ═══════════════════════════════════════════════════════════════

        for element in elements:
            if element.status == FROZEN:
                continue  # Already frozen

            # Check if element changed this iteration
            if element.changed_this_iteration:
                stability_counter[element.id] = 0
            else:
                stability_counter[element.id] += 1

            # Check if eligible for freezing
            threshold = freeze_threshold(element.strength)

            if threshold == float('inf'):
                continue  # WEAK elements never freeze

            if stability_counter[element.id] >= threshold:
                # Check if all constraints satisfied
                constraints_satisfied = all(
                    c.evaluate() >= 0.95  # Allow 5% tolerance
                    for c in get_constraints_affecting(element)
                )

                if constraints_satisfied:
                    freeze(element)
                    print(f"🔒 Iteration {iteration}: Frozen {element.name} "
                          f"(stable for {stability_counter[element.id]} iterations)")

        # ═══════════════════════════════════════════════════════════════
        # PHASE 3: Check convergence criteria
        # ═══════════════════════════════════════════════════════════════

        frozen_count = sum(1 for e in elements if e.status == FROZEN)
        total_count = len(elements)

        print(f"Iteration {iteration}: {frozen_count}/{total_count} frozen, "
              f"{changed_count} adjustments")

        # Success: All elements frozen or stable
        if frozen_count == total_count or changed_count == 0:
            print(f"✅ Converged in {iteration} iterations")
            return True

        iteration += 1

    # Failed to converge
    print(f"❌ Did not converge in {max_iterations} iterations")
    print(f"   Frozen: {frozen_count}/{total_count}")
    return False

=============================================================================
CONSTRAINT STRENGTH ASSIGNMENT
=============================================================================

Automatic Assignment Function:
────────────────────────────────────────────────────────────────────────────

def assign_constraint_strength(element):
    """
    Determine constraint strength based on element properties.
    This is THE KEY to making progressive freezing work correctly.
    """

    # ═══════════════════════════════════════════════════════════════
    # REQUIRED: Structural, explicitly placed in DWG
    # ═══════════════════════════════════════════════════════════════

    if element.discipline == "STR":
        # Structural elements define the building geometry
        return REQUIRED

    if element.layer.contains("FIXED") or element.layer.contains("REF"):
        # Explicitly marked as fixed reference
        return REQUIRED

    if element.explicitly_dimensioned_in_dwg():
        # Has dimension annotations → user-specified position
        return REQUIRED

    if element.is_boundary_element():
        # Walls, slabs that define spatial bounds
        return REQUIRED

    # ═══════════════════════════════════════════════════════════════
    # STRONG: Primary distribution, major architectural
    # ═══════════════════════════════════════════════════════════════

    if element.ifc_class in ["IfcDoor", "IfcWindow", "IfcStair", "IfcRamp"]:
        # Major architectural circulation elements
        return STRONG

    if element.is_mep_main():
        # Risers, mains, primary distribution (hard to relocate)
        return STRONG

    if element.storey == "GROUND" and element.discipline == "ARC":
        # Ground floor layout often drives other floors
        return STRONG

    if element.ifc_class in ["IfcBeam", "IfcColumn"] and element.discipline == "STR":
        # Primary structural elements
        return STRONG

    # ═══════════════════════════════════════════════════════════════
    # MEDIUM: Secondary distribution, fitted elements
    # ═══════════════════════════════════════════════════════════════

    if element.is_mep_branch():
        # Branch pipes, ducts (can route around obstacles)
        return MEDIUM

    if element.ifc_class in ["IfcFurniture", "IfcCovering", "IfcRailing"]:
        # Furniture and finishing elements (adjustable)
        return MEDIUM

    if element.ifc_class.contains("Fitting"):
        # Fittings adjust to connect elements
        return MEDIUM

    # ═══════════════════════════════════════════════════════════════
    # WEAK: Terminals, fixtures (adjust to fit environment)
    # ═══════════════════════════════════════════════════════════════

    if element.ifc_class.contains("Terminal"):
        # All terminal elements (freely repositionable)
        return WEAK

    if element.ifc_class in ["IfcFireSuppressionTerminal",
                             "IfcLightFixture",
                             "IfcAirTerminal",
                             "IfcFlowTerminal"]:
        # Specific terminal fixtures
        return WEAK

    if element.ifc_class in ["IfcSensor", "IfcAlarm", "IfcController"]:
        # Control devices (mount anywhere suitable)
        return WEAK

    # ═══════════════════════════════════════════════════════════════
    # DEFAULT: Medium (balanced adjustability)
    # ═══════════════════════════════════════════════════════════════

    return MEDIUM

=============================================================================
WORKED EXAMPLE: DUCT OVERSHOOT WITH PROGRESSIVE FREEZING
=============================================================================

Initial State:
────────────────────────────────────────────────────────────────────────────

Elements:
  Wall_50 (REQUIRED):
    Position: x=50, y=0 to y=100, z=0 to z=4
    Status: tentative
    From DWG: POLYLINE on layer "ARC-WALL"

  Duct_A (STRONG, main supply):
    Start: (10, 50, 11.225), End: (90, 50, 11.225)
    Length: 80m  ← OVERSHOOTS WALL!
    Status: tentative
    From DWG: POLYLINE on layer "ACMV-SUPPLY-DUCT"

  Duct_B (MEDIUM, branch):
    Start: (50, 50, 11.225), End: (50, 90, 11.225)
    Status: tentative
    Connects to Duct_A at start point

  Diffuser_C (WEAK, terminal):
    Position: (50, 80, 11.225)
    Status: tentative
    Connects to Duct_B

Constraints:
  C1 (REQUIRED): Wall_50 has no_clash with all elements
  C2 (STRONG): Duct_A has network_continuity
  C3 (MEDIUM): Duct_B connected to Duct_A
  C4 (WEAK): Diffuser_C connected to Duct_B

Iteration 0 (Initial Analysis):
────────────────────────────────────────────────────────────────────────────

Process REQUIRED constraints:
  C1: Wall_50 clashes with Duct_A → satisfaction = 0.0 ❌

  Adjustable elements: Duct_A (STRONG, not frozen)

  Resolution: Trim Duct_A at wall intersection
    - Detect intersection: Duct_A line intersects Wall_50 at (50, 50, 11.225)
    - Split Duct_A:
        Duct_A1: (10, 50, 11.225) → (50, 50, 11.225)  [40m]
        Duct_A2: (50, 50, 11.225) → (90, 50, 11.225)  [40m]
    - Insert Fitting_F at (50, 50, 11.225) to connect through wall

  Wall_50: No changes needed, all constraints satisfied
    Stability: 1 iteration, threshold: 0 → FREEZE Wall_50 🔒

Status after Iteration 0:
  Wall_50: FROZEN 🔒
  Duct_A1, Duct_A2, Fitting_F: tentative (just created)
  Duct_B: tentative
  Diffuser_C: tentative

Iteration 1:
────────────────────────────────────────────────────────────────────────────

Process REQUIRED constraints:
  C1: Wall_50 frozen, no clashes → ✓

Process STRONG constraints:
  C2: Duct_A1, Duct_A2 have network_continuity via Fitting_F → ✓

  Duct_A1, Duct_A2: No changes, stability = 1 iteration
    Threshold for STRONG: 2 iterations → not frozen yet

Process MEDIUM constraints:
  C3: Duct_B should connect to Duct_A at (50, 50)
    Fitting_F now at (50, 50) → adjust Duct_B start to snap
    Duct_B.start = (50, 50, 11.225)  ✓
    Duct_B changed → stability = 0

Process WEAK constraints:
  C4: Diffuser_C should connect to Duct_B at (50, 80)
    Duct_B unchanged at end → Diffuser_C already correct ✓

Iteration 2:
────────────────────────────────────────────────────────────────────────────

Process REQUIRED constraints: All frozen ✓

Process STRONG constraints:
  Duct_A1, Duct_A2, Fitting_F: No changes
    Stability = 2 iterations, threshold = 2 → FREEZE all 🔒

Process MEDIUM constraints:
  Duct_B: No changes, stability = 1 iteration
    Threshold = 5 → not frozen yet

Process WEAK constraints:
  Diffuser_C: No changes, stability = 1 iteration

Iteration 3-6:
────────────────────────────────────────────────────────────────────────────

  Duct_B: No changes, stability increases: 2, 3, 4, 5
  Iteration 6: stability = 5, threshold reached → FREEZE Duct_B 🔒

  Diffuser_C: No changes, but WEAK elements never freeze

Final State (Iteration 7):
────────────────────────────────────────────────────────────────────────────

✅ Converged!

Frozen elements:
  🔒 Wall_50 (iteration 0)
  🔒 Duct_A1 (iteration 2)
  🔒 Duct_A2 (iteration 2)
  🔒 Fitting_F (iteration 2)
  🔒 Duct_B (iteration 6)

Unfrozen (adjustable):
  Diffuser_C (WEAK, remains flexible for future adjustments)

Result:
  - Duct properly trimmed at wall
  - Fitting inserted for wall penetration
  - Branch duct correctly connected
  - Diffuser positioned optimally
  - No oscillation or divergence!

=============================================================================
DATABASE SCHEMA FOR FREEZING
=============================================================================

Track Element Resolution Status:
────────────────────────────────────────────────────────────────────────────

CREATE TABLE element_resolution_status (
    guid TEXT PRIMARY KEY,
    status TEXT NOT NULL,  -- 'tentative', 'validated', 'frozen'
    constraint_strength TEXT NOT NULL,  -- 'required', 'strong', 'medium', 'weak'
    stability_iterations INTEGER DEFAULT 0,
    frozen_at_iteration INTEGER,
    freeze_reason TEXT,
    pending_adjustments TEXT,  -- JSON array of adjustments needed
    last_adjusted_iteration INTEGER,
    adjustment_count INTEGER DEFAULT 0,
    FOREIGN KEY (guid) REFERENCES elements_meta(guid)
);

Track Constraints:
────────────────────────────────────────────────────────────────────────────

CREATE TABLE resolution_constraints (
    constraint_id TEXT PRIMARY KEY,
    constraint_type TEXT NOT NULL,  -- 'geometric', 'topological', 'semantic'
    strength TEXT NOT NULL,  -- 'required', 'strong', 'medium', 'weak'
    affected_elements TEXT,  -- JSON array of guids
    satisfaction_score REAL,  -- 0.0 to 1.0
    description TEXT,
    created_at_iteration INTEGER,
    last_evaluated_iteration INTEGER,
    violation_count INTEGER DEFAULT 0
);

Track Iteration History (for debugging and replay):
────────────────────────────────────────────────────────────────────────────

CREATE TABLE resolution_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iteration INTEGER NOT NULL,
    guid TEXT NOT NULL,
    action TEXT NOT NULL,  -- 'adjusted', 'frozen', 'validated', 'created', 'deleted'
    before_state TEXT,  -- JSON: {position, rotation, connections, ...}
    after_state TEXT,   -- JSON
    reason TEXT,
    constraint_id TEXT,  -- Which constraint triggered this
    timestamp TEXT,
    FOREIGN KEY (guid) REFERENCES elements_meta(guid),
    FOREIGN KEY (constraint_id) REFERENCES resolution_constraints(constraint_id)
);

Track Convergence Metrics:
────────────────────────────────────────────────────────────────────────────

CREATE TABLE convergence_metrics (
    iteration INTEGER PRIMARY KEY,
    total_elements INTEGER,
    frozen_elements INTEGER,
    tentative_elements INTEGER,
    validated_elements INTEGER,
    adjustments_made INTEGER,
    constraints_satisfied INTEGER,
    constraints_violated INTEGER,
    timestamp TEXT
);

=============================================================================
ADVANCED: CONSTRAINT PROPAGATION & CASCADING FREEZES
=============================================================================

When an element is frozen, it may enable freezing of connected elements:

Cascade Freezing Logic:
────────────────────────────────────────────────────────────────────────────

def propagate_freeze(frozen_element):
    """
    When an element is frozen, check if connected elements can now freeze.
    """

    connected = get_connected_elements(frozen_element)

    for element in connected:
        if element.status == FROZEN:
            continue  # Already frozen

        # Check if all constraints involving this element are now satisfiable
        constraints = get_constraints_affecting(element)

        # Count how many affected elements are frozen
        frozen_neighbors = sum(
            1 for c in constraints
            for e in c.affected_elements
            if e.status == FROZEN
        )

        total_neighbors = sum(len(c.affected_elements) for c in constraints)

        # If most neighbors are frozen, this element is highly constrained
        constraint_ratio = frozen_neighbors / total_neighbors if total_neighbors > 0 else 0

        if constraint_ratio > 0.8:  # 80% of neighbors frozen
            # This element is highly constrained, may be able to freeze early
            if all_constraints_satisfied(element):
                print(f"🔗 Cascade freeze: {element.name} "
                      f"(triggered by {frozen_element.name})")
                freeze(element)
                # Recursively propagate
                propagate_freeze(element)

Example Cascade:
────────────────────────────────────────────────────────────────────────────

Wall_A frozen → Door_1 in Wall_A can snap to wall → Door_1 frozen
               → Window_1 in Wall_A can snap to wall → Window_1 frozen
               → Wall_B perpendicular to Wall_A can finalize corner → Wall_B frozen
                  → Door_2 in Wall_B can snap → Door_2 frozen
                     → ... cascade continues

This dramatically speeds up convergence!

=============================================================================
OPTIMIZATION: MINIMIZE TOTAL DEVIATION
=============================================================================

The Fuzzy Formula (Multi-Objective Optimization):
────────────────────────────────────────────────────────────────────────────

When adjusting elements to satisfy constraints, minimize deviation from
original DWG positions:

Objective Function:

  E(S) = Σᵢ wᵢ · δᵢ(S)

  Where:
    δᵢ(S) = ||position(element i) - original_position(element i)||
            // Euclidean distance moved

    wᵢ = weight based on constraint strength:
      REQUIRED: w = 0    (never adjust, δ = 0)
      STRONG:   w = 1    (minimize adjustments)
      MEDIUM:   w = 10   (more willing to adjust)
      WEAK:     w = 100  (freely adjust)

  Minimize E(S) subject to:
    Hard constraints (REQUIRED): f(S) = 0 (exactly satisfied)
    Soft constraints (others): f(S) ≥ 0 (minimize violation)

Solution Methods:
────────────────────────────────────────────────────────────────────────────

1. Gradient Descent:
   - Compute ∂E/∂sᵢ for each element
   - Move in direction of negative gradient
   - Freeze when gradient < ε (local minimum reached)

2. Quadratic Programming:
   - Formulate as QP problem (if constraints are linear/quadratic)
   - Use QP solver (e.g., CVXOPT, scipy.optimize.minimize)
   - Exact solution guaranteed

3. Simulated Annealing:
   - For complex non-convex cases
   - Randomly perturb positions, accept if E decreases
   - Gradually reduce temperature (perturbation magnitude)
   - Can escape local minima

4. Constraint Satisfaction Problem (CSP) Solver:
   - Formulate as CSP with discrete variables
   - Use backtracking search with constraint propagation
   - Guaranteed to find solution if one exists

=============================================================================
PRACTICAL IMPLEMENTATION PHASES
=============================================================================

Phase 2 (POC - Simple Freezing):
────────────────────────────────────────────────────────────────────────────

Goal: Prove concept works with basic freezing

Implementation:
  ✓ Freeze by discipline order: STR → ARC → MEP
  ✓ No constraint solver yet
  ✓ Just prevent earlier disciplines from being adjusted by later ones
  ✓ Single-pass, hard-coded priorities

Acceptance: 70%+ accuracy vs DB1, converges in single pass

Phase 3 (Basic Constraint Solving):
────────────────────────────────────────────────────────────────────────────

Goal: Implement constraint hierarchy and multi-pass refinement

Implementation:
  ✓ Assign Required/Strong/Medium/Weak to all elements
  ✓ Multi-pass iteration with stability counters
  ✓ Freeze based on constraint satisfaction
  ✓ Basic geometric constraints (no_clash, within_bounds)
  ✓ Basic topological constraints (connected)

Acceptance: 85%+ accuracy, converges in < 10 iterations

Phase 4 (Full Constraint Propagation):
────────────────────────────────────────────────────────────────────────────

Goal: Production-ready with advanced resolution

Implementation:
  ✓ Full constraint library (geometric, topological, semantic)
  ✓ Cascade freezing (propagate_freeze)
  ✓ Automatic backtracking if contradictions detected
  ✓ Optimization: minimize total adjustment (E(S))
  ✓ Detailed logging and replay capability

Acceptance: 95%+ accuracy, converges in < 50 iterations

=============================================================================
FAILURE MODES & RECOVERY
=============================================================================

Scenario 1: No Convergence (Oscillation)
────────────────────────────────────────────────────────────────────────────

Detection: iteration count exceeds max_iterations

Diagnosis:
  - Check resolution_history for cyclic patterns
  - Identify elements that keep adjusting back and forth
  - Likely cause: conflicting constraints with equal strength

Recovery:
  - Manually adjust constraint strengths
  - Add explicit priority rules
  - Freeze problematic elements manually
  - Relax constraint satisfaction thresholds (0.95 → 0.90)

Scenario 2: Over-Constrained (No Solution)
────────────────────────────────────────────────────────────────────────────

Detection: Many frozen constraint violations

Diagnosis:
  - Query resolution_constraints WHERE satisfaction_score < 0.5
  - Identify contradictory constraints
  - Likely cause: DWG has impossible geometry (user error)

Recovery:
  - Flag contradictory constraints for user review
  - Suggest which elements to adjust manually
  - Provide visualization of constraint conflicts
  - Allow user to disable specific constraints

Scenario 3: Under-Constrained (Multiple Solutions)
────────────────────────────────────────────────────────────────────────────

Detection: Elements remain tentative with all constraints satisfied

Diagnosis:
  - Elements have freedom of movement (ambiguous placement)
  - Multiple valid positions exist
  - Likely cause: Missing constraints or weak specifications

Recovery:
  - Add default placement rules (e.g., "center in space")
  - Use template defaults (spacing grids)
  - Flag for user review: "Position ambiguous, using default"

=============================================================================
FUTURE RESEARCH DIRECTIONS
=============================================================================

1. Machine Learning for Constraint Strength:
   - Train model on manual corrections
   - Learn which elements are typically fixed vs adjusted
   - Automatically assign strengths based on context

2. Parallel Constraint Solving:
   - Independent constraints solved in parallel
   - Merge solutions at synchronization points
   - Speedup: N-core system solves N times faster

3. Incremental Constraint Solving:
   - When DWG changes, only re-solve affected elements
   - Frozen elements remain frozen unless directly impacted
   - Fast iteration during design process

4. User-Guided Prioritization:
   - UI allows user to mark "this is correct, don't change it"
   - Manually freeze/unfreeze elements
   - Override automatic constraint strengths

5. Probabilistic Constraint Satisfaction:
   - Constraints have confidence scores
   - Solution maximizes probability of being correct
   - Handles uncertainty in DWG interpretation

=============================================================================
CONCLUSION
=============================================================================

Progressive freezing with constraint hierarchy solves the "moving target"
problem that would otherwise prevent multi-pass refinement from converging.

Key insights:
  ✓ Rubik's Cube analogy: solve in stages, lock solved pieces
  ✓ Constraint hierarchy: strong elements constrain weak, not reverse
  ✓ Stability-based freezing: freeze when stable for N iterations
  ✓ Cascade propagation: frozen elements enable neighbor freezing
  ✓ Minimize deviation: adjust weak elements, preserve strong

Implementation path:
  Phase 2: Simple discipline-based freezing (POC)
  Phase 3: Constraint hierarchy + multi-pass (production)
  Phase 4: Full optimization + advanced features (enterprise)

This design provides a rigorous, mathematically-grounded solution to
ensuring convergence while maintaining solution quality.

=============================================================================
DOCUMENT STATUS
=============================================================================

Status: RESEARCH & DESIGN SPECIFICATION
Implementation: Post-POC (Phase 3+)
Priority: HIGH (critical for production quality)
Owner: TBD
Review Date: After Phase 2 validation complete

=============================================================================
REFERENCES
=============================================================================

Related Documents:
- MULTI_PASS_REFINEMENT_DESIGN.md - Overall refinement strategy
- CRASH_RESILIENCE_DESIGN.md - How to handle long-running processes
- TEMPLATE_CONFIGURATOR_DESIGN.md - UI for constraint configuration

Academic References:
- Cassowary Algorithm (Badros et al., 1999) - Linear constraint solving
- Constraint Satisfaction Problems (Russell & Norvig, AI textbook)
- Multi-objective Optimization (Deb, 2001) - Pareto-optimal solutions

=============================================================================
LAST UPDATED: 2025-11-12
=============================================================================
