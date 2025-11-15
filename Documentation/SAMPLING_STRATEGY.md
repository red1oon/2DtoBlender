# Sampling Strategy for Large Database Validation

**Created:** November 12, 2025
**Purpose:** Fast validation using statistical sampling instead of full conversion

---

## The Problem

**Full conversion of Terminal 1:**
- 49,059 elements total
- Could take **hours** to process
- Large memory footprint
- Slow feedback cycle
- Hard to iterate on templates

**Better approach: Sample first, validate concept, then scale**

---

## Sampling Approach

### Philosophy

> "Better to validate 1,000 elements correctly than process 50,000 incorrectly"

**Key insight from your extraction work:**
- You successfully extracted templates from 49,059 elements in 30 seconds
- Because you focused on **patterns**, not individual elements
- **Same principle applies here** - validate patterns, not every element

---

## Three-Phase Testing Strategy

### Phase 1: Smoke Test (5 minutes)
**Goal:** Does anything work at all?

```bash
./quick_test.sh 100
```

**What it tests:**
- Can DXF be parsed?
- Do ANY templates match?
- Is database schema correct?
- Are there obvious errors?

**Sample size:** 100 elements (0.2% of total)

**Success criteria:**
- ✅ Parsing works without errors
- ✅ At least 50% of entities match templates
- ✅ Database schema valid

**If fails:** Fix parsing/template issues before proceeding

---

### Phase 2: Statistical Sample (15 minutes)
**Goal:** Validate template accuracy across all disciplines

```bash
./quick_test.sh 1000
```

**Sampling strategy:**
```
Discipline-based stratified sampling:
  ARC:  300 elements (0.85% of 35,338)
  FP:   200 elements (2.9% of 6,880)
  ELEC: 100 elements (8.5% of 1,172)
  ACMV: 100 elements (6.2% of 1,621)
  SP:   100 elements (10.2% of 979)
  STR:  100 elements (7.0% of 1,429)
  CW:   50 elements  (3.5% of 1,431)
  LPG:  50 elements  (24% of 209)

Total: 1,000 elements (~2% of total)
```

**Why this works:**
- Covers all 8 disciplines
- Higher sampling rate for smaller disciplines (LPG: 24%)
- Lower rate for large disciplines (ARC: 0.85%)
- Still representative of overall accuracy

**Success criteria:**
- ✅ All 8 disciplines present
- ✅ Accuracy > 70% per discipline
- ✅ IFC class distribution matches expected

**If fails:** Refine templates, re-test Phase 2 (fast iteration)

---

### Phase 3: Full Conversion (1-2 hours)
**Goal:** Complete database for production use

```bash
./run_conversion.sh
```

**When to run:**
- ✅ Phase 2 passed with >70% accuracy
- ✅ Template issues resolved
- ✅ Ready for final validation

**Sample size:** All 49,059 elements

**Success criteria:**
- ✅ Same as Phase 2, but full coverage
- ✅ Ready for Bonsai integration

---

## Statistical Validity

### Why 1,000 Elements is Enough

**Confidence interval calculation:**
```
Population: 49,059 elements
Sample: 1,000 elements
Confidence level: 95%
Margin of error: ±3.1%

If sample shows 75% accuracy:
  True accuracy: 71.9% - 78.1%
```

**For 2,000 elements:**
```
Margin of error: ±2.2%
If sample shows 75% accuracy:
  True accuracy: 72.8% - 77.2%
```

**Conclusion:** 1,000-2,000 elements gives reliable accuracy estimate

---

## Sampling Methods

### Method 1: Random Sampling (Simplest)
```python
import random
sampled = random.sample(all_entities, 1000)
```

**Pros:**
- Simple to implement
- Statistically valid

**Cons:**
- May miss rare element types
- Could oversample common types (IfcPlate: 33,324)

---

### Method 2: Stratified Sampling (Recommended)
```python
# Sample from each discipline proportionally
samples_per_discipline = {
    'ARC': 300,
    'FP': 200,
    'ELEC': 100,
    # ...
}

for discipline, count in samples_per_discipline.items():
    entities = filter_by_discipline(all_entities, discipline)
    sampled += random.sample(entities, min(count, len(entities)))
```

**Pros:**
- Guarantees coverage of all disciplines
- Balances rare vs common types
- Better for template validation

**Cons:**
- Slightly more complex

---

### Method 3: Template-Aware Sampling (Advanced)
```python
# Sample elements that match each template
for template in templates:
    matching_entities = filter_by_template(all_entities, template)
    sampled += random.sample(matching_entities, min(20, len(matching_entities)))
```

**Pros:**
- Tests EVERY template type
- Catches template-specific issues
- Most thorough validation

**Cons:**
- Requires pre-matching
- More computation

**When to use:** Phase 3, after Phase 2 passes

---

## Iteration Workflow

```
┌─────────────────────────────────────┐
│ Phase 1: Smoke Test (100 elements) │
└──────────────┬──────────────────────┘
               │
               ├─ PASS → Continue
               └─ FAIL → Fix parsing/basic issues
                         ↓
┌─────────────────────────────────────────┐
│ Phase 2: Sample Test (1,000 elements)  │
└──────────────┬──────────────────────────┘
               │
               ├─ >70% accuracy → Phase 3
               ├─ 50-70% → Refine templates, retry Phase 2
               └─ <50% → Major template issues, investigate
                         ↓
┌─────────────────────────────────────────┐
│ Analyze failing cases:                  │
│ - Which disciplines failed?             │
│ - Which IFC classes don't match?        │
│ - Layer naming issues?                  │
│ - Block name patterns wrong?            │
└──────────────┬──────────────────────────┘
               │
               ├─ Update templates
               ├─ Update matching rules
               └─ Retry Phase 2 (15 min feedback!)
                         ↓
┌─────────────────────────────────────────┐
│ Phase 3: Full Conversion (49K elements)│
│ (Only after Phase 2 >70%)               │
└─────────────────────────────────────────┘
```

---

## Comparison: Sampling vs Full

| Aspect | Sampling (1,000) | Full (49,059) |
|--------|------------------|---------------|
| **Time** | 15 min | 1-2 hours |
| **Memory** | <500 MB | 2-4 GB |
| **Feedback** | Immediate | Delayed |
| **Iteration** | Fast | Slow |
| **Accuracy** | ±3% margin | Exact |
| **Use case** | Development, testing | Production |

**Best practice:**
- Use sampling during development (fast iteration)
- Use full conversion for final validation
- Always sample first, scale later

---

## Quick Test Commands

### Smoke test (100 elements):
```bash
cd /home/red1/Documents/bonsai/RawDWG
./quick_test.sh 100
```

### Statistical sample (1,000 elements):
```bash
./quick_test.sh 1000
```

### Larger sample (2,000 elements):
```bash
./quick_test.sh 2000
```

### Full conversion (all elements):
```bash
./run_conversion.sh
```

---

## Expected Output

### Quick Test Output:
```
========================================================
Quick Smoke Test - Sample-Based Validation
========================================================

Sample size: 1000 elements

Sampling Strategy:
  ARC:  300 elements (from ~35,000)
  FP:   200 elements (from ~6,800)
  ...

Running Sampled Conversion...

Total entities in DXF: 125,423
Sampled 1,000 entities
Converting to database...

✓ Sample conversion complete!

Quick Statistics:
ARC   287
FP    198
ELEC  95
...

Total sampled: 982

✓ Quick Test Complete!

Advantages of sampling:
  ✓ Fast feedback (minutes vs hours)
  ✓ Iterate quickly on templates
  ✓ Validate approach before full run
```

---

## When to Use Each Approach

### Use Sampling When:
- ✅ Developing templates
- ✅ Testing new matching rules
- ✅ Debugging issues
- ✅ Validating concept
- ✅ Iterating on accuracy
- ✅ Limited time/resources

### Use Full Conversion When:
- ✅ Final validation passed
- ✅ Ready for production
- ✅ Need complete database
- ✅ Bonsai integration testing
- ✅ Accuracy >70% confirmed

---

## Advantages of This Approach

1. **Fast iteration cycles**
   - 15 min feedback vs 2 hours
   - Test → Fix → Retest loop

2. **Resource efficient**
   - Less memory usage
   - Faster processing
   - Easier debugging

3. **Risk reduction**
   - Validate before investing time in full run
   - Catch issues early
   - Fail fast, fix fast

4. **Statistical confidence**
   - 1,000 samples = ±3% accuracy
   - Reliable for decision making
   - Good enough for POC validation

5. **Aligns with your extraction approach**
   - You extracted patterns, not all elements
   - Same principle: validate patterns first

---

## Bottom Line

**Your intuition is correct:**
> Sampling is the smart way to validate large databases

**Recommended workflow:**
1. Start with quick_test.sh (1,000 elements)
2. Iterate until >70% accuracy
3. Then run full conversion for final validation

**Time saved:**
- Without sampling: 2 hours per test × 5 iterations = 10 hours
- With sampling: 15 min per test × 5 iterations = 75 min

**Result: 8+ hours saved, faster POC validation!**

---

**Last Updated:** November 12, 2025
**Recommendation:** Use sampling for all development/testing
