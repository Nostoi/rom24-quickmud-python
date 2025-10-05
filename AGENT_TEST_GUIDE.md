# AGENT.md Test Execution Guide

**Date**: 2025-10-05  
**Purpose**: Instructions for AGENT.md to run tests and gather data for confidence scoring

---

## Yes, AGENT.md Can Run Tests! ✅

AGENT.md is **fully capable** of running tests and gathering data. Here's how:

---

## Quick Start

### Option 1: Use the Test Data Gatherer Script (RECOMMENDED)

The `scripts/test_data_gatherer.py` script automates everything:

```bash
# Test all subsystems and get confidence scores
python3 scripts/test_data_gatherer.py --all -o test_results.json

# Test specific subsystem
python3 scripts/test_data_gatherer.py combat -v

# Save results to file
python3 scripts/test_data_gatherer.py resets -o resets_results.json
```

**Output includes**:

- Tests passed/failed/total
- Pass rate percentage
- Calculated confidence score (based on formula)
- Timestamp
- Full test output (if verbose)

### Option 2: Run Pytest Directly

For manual control:

```bash
# Full test suite
pytest -v --tb=short > test_baseline.txt 2>&1

# Specific subsystem
pytest tests/test_combat*.py tests/test_weapon*.py -v --tb=short

# Just collection (fast)
pytest --collect-only -q
```

---

## Workflow for AGENT.md

### 1. Validate Infrastructure (Phase 0)

```python
# From within an agent session, use:
run_in_terminal(
    command="pytest --collect-only -q",
    explanation="Validate test infrastructure can collect tests",
    isBackground=False
)
```

**Expected output**: `"501 tests collected in X.XXs"`

If errors appear, STOP and report infrastructure issues.

### 2. Run Test Data Gatherer (Phase 0.5)

```python
# Test all subsystems
run_in_terminal(
    command="python3 scripts/test_data_gatherer.py --all -o test_results.json",
    explanation="Run all subsystem tests and gather confidence data",
    isBackground=True  # This takes 5-10 minutes
)

# Or test specific subsystem
run_in_terminal(
    command="python3 scripts/test_data_gatherer.py combat -o combat_results.json",
    explanation="Test combat subsystem and calculate confidence",
    isBackground=False
)
```

### 3. Parse Results

```python
# Read the JSON output
import json
with open("test_results.json") as f:
    results = json.load(f)

# Extract metrics per subsystem
for subsystem, metrics in results.items():
    print(f"{subsystem}:")
    print(f"  Passed: {metrics['passed']}/{metrics['total']}")
    print(f"  Pass Rate: {metrics['pass_rate']*100:.1f}%")
    print(f"  Confidence: {metrics['confidence']:.2f}")
```

### 4. Update PYTHON_PORT_PLAN.md

Use the calculated confidence scores to update STATUS lines:

**Before** (estimated):

```
STATUS: completion:❌ implementation:partial correctness:suspect (confidence 0.45)
```

**After** (validated with tests):

```
STATUS: completion:❌ implementation:partial correctness:fails (confidence 0.38)
<!-- TEST-VALIDATED: 2025-10-05, 12/32 tests passed (37.5%) -->
```

### 5. Identify Gaps

Compare test results against confidence scores:

```python
# Load current confidence scores from PYTHON_PORT_PLAN.md
# Compare against test results
# Flag discrepancies where confidence doesn't match test reality
```

---

## Subsystem Test Mapping

The test_data_gatherer.py script knows how to map subsystems to tests:

| Subsystem                  | Test Files                                           |
| -------------------------- | ---------------------------------------------------- |
| **combat**                 | test_combat*.py, test_weapon*.py, test_damage\*.py   |
| **skills_spells**          | test_skills*.py, test_spells*.py, test_practice.py   |
| **movement_encumbrance**   | test_movement\*.py, test_encumbrance.py              |
| **world_loader**           | test_area\*.py, test_world.py, test_load_midgaard.py |
| **persistence**            | test*persistence.py, test*_\_save_.py                |
| **resets**                 | test_reset\*.py, test_spawning.py                    |
| **mob_programs**           | test_mobprog\*.py                                    |
| **npc_spec_funs**          | test_spec_funs\*.py                                  |
| **game_update_loop**       | test_game_loop\*.py                                  |
| ... and 18 more subsystems |

Full mapping is in `scripts/test_data_gatherer.py` → `SUBSYSTEM_TEST_MAP`

---

## Confidence Score Formula

The test_data_gatherer.py uses this formula:

```python
def calculate_confidence(passed: int, total: int) -> float:
    if total == 0:
        return 0.20  # No tests = very low confidence

    pass_rate = passed / total

    if pass_rate == 1.0:
        return 0.95  # Perfect, but some integration risk
    elif pass_rate >= 0.95:
        return 0.85
    elif pass_rate >= 0.90:
        return 0.75
    elif pass_rate >= 0.80:
        return 0.65
    elif pass_rate >= 0.70:
        return 0.55
    else:
        return max(0.20, pass_rate * 0.60)
```

**Why not 1.00 for 100% pass?**  
Even with all tests passing, there may be:

- Integration gaps with other subsystems
- Edge cases not covered by tests
- ROM parity issues not yet tested

Confidence 0.95 indicates "very high confidence, minimal risk"

---

## Example Agent Session

Here's how an agent session using AGENT.md would work:

```python
# 1. Validate infrastructure
result = run_in_terminal(
    command="pytest --collect-only -q | tail -3",
    explanation="Check if tests can collect",
    isBackground=False
)
# Verify: "501 tests collected"

# 2. Run test data gatherer for incomplete subsystems
result = run_in_terminal(
    command="python3 scripts/test_data_gatherer.py combat -o combat_test_data.json",
    explanation="Test combat subsystem to validate confidence score",
    isBackground=False
)

# 3. Read results
combat_data = read_file("combat_test_data.json", 1, 100)
# Parse JSON to get: passed=45, total=52, confidence=0.78

# 4. Update PYTHON_PORT_PLAN.md
# Find combat subsystem block, update STATUS line with test-validated confidence

# 5. Generate tasks based on failing tests
# If tests show specific failures, create targeted P0 tasks to fix them
```

---

## When to Run Tests

### Always Run (Phase 0)

- Test collection check: `pytest --collect-only -q`
- Takes <5 seconds
- Ensures infrastructure is functional

### Run When Needed (Phase 0.5)

- Confidence scores appear outdated (>7 days old)
- Confidence scores marked UNVALIDATED
- User requests test-based validation
- Before major confidence score updates

### Don't Run

- Infrastructure is broken (collection fails)
- Recent test baseline exists (<7 days)
- Session budget is limited (tests take 5-10 minutes)
- Only doing architectural analysis (not validation)

---

## Parsing Test Output

### From test_data_gatherer.py (JSON)

```json
{
  "combat": {
    "subsystem": "combat",
    "passed": 45,
    "failed": 7,
    "total": 52,
    "pass_rate": 0.865,
    "confidence": 0.65,
    "timestamp": "2025-10-05T16:30:00"
  }
}
```

### From pytest directly (text)

```
============================= test session starts ==============================
...
============================== 45 passed, 7 failed in 23.45s ===================
```

Extract with regex:

```python
import re
match = re.search(r"(\d+) passed(?:, (\d+) failed)?", output)
passed = int(match.group(1))
failed = int(match.group(2)) if match.group(2) else 0
```

---

## Updating PYTHON_PORT_PLAN.md Markers

Add test validation markers to the plan:

```markdown
<!-- LAST-TEST-RUN: 2025-10-05 -->
<!-- TEST-PASS-RATE: 78.5% (394 passed / 501 total) -->
<!-- VALIDATION-STATUS: validated -->
```

Update subsystem blocks with test results:

```markdown
### combat — Parity Audit 2025-10-05

STATUS: completion:❌ implementation:full correctness:fails (confidence 0.65)

<!-- TEST-VALIDATED: 2025-10-05, 45/52 tests passed (86.5%) -->

KEY RISKS: THAC0_calculation, damage_reduction, special_attacks
```

---

## Summary

**YES, AGENT.md can run tests!**

✅ **Phase 0**: Always validates test infrastructure  
✅ **Phase 0.5**: Can run full test suite or subsystem tests  
✅ **Tools**: test_data_gatherer.py automates everything  
✅ **Data**: JSON output with pass/fail/confidence metrics  
✅ **Integration**: Updates PYTHON_PORT_PLAN.md with validated scores  
✅ **Analysis**: Identifies gaps between confidence and test reality

The agent has full capability to execute tests, parse results, calculate confidence scores, and update the plan with validated data.

**Recommended workflow**:

1. Phase 0: Validate infrastructure
2. Phase 0.5: Run test_data_gatherer.py
3. Phase 1: Analyze results and update confidence scores
4. Phase 2: Investigate subsystems with failing tests
5. Phase 3: Generate tasks to fix failures
