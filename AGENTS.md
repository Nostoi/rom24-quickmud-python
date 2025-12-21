# QuickMUD Development Guide for AI Agents

## 🤖 Autonomous Mode (ENABLED)

**When explicitly directed by user**, agent may enter autonomous task completion mode:

### Activation Criteria
- User explicitly says "start autonomous mode" or gives clear directive to "complete all tasks"
- User specifies scope (P0 only, P0+P1, or all tasks)
- User sets time limit and error handling policy

### Autonomous Workflow
1. ✅ Create comprehensive todo list from ARCHITECTURAL_TASKS.md
2. 🔄 Execute tasks sequentially without waiting for approval
3. 🔨 Fix errors immediately before proceeding to next task
4. ✅ Run full test suite after each major task
5. 📊 Run `scripts/test_data_gatherer.py` to verify ROM parity
6. 📝 Update ARCHITECTURAL_TASKS.md and PROJECT_COMPLETION_STATUS.md
7. 🎯 Stop at time limit or scope completion

### Quality Gates (MANDATORY)
- **After each task**: Run acceptance tests specified in ARCHITECTURAL_TASKS.md
- **After each task**: Run full test suite (200+ tests) to catch regressions
- **After all tasks**: Run `scripts/test_data_gatherer.py` for final parity verification
- **On any test failure**: Fix immediately before proceeding

### Stopping Conditions
- All tasks in scope complete
- Time limit reached
- Unrecoverable error (after 3 fix attempts)
- User interruption

**Current Session**: Autonomous mode ACTIVE
- **Scope**: P0 + P1 tasks (7 tasks)
- **Time Limit**: 2 hours
- **Error Policy**: Fix immediately
- **Started**: 2025-12-19 13:30 CST

---

## Task Tracking (CRITICAL - READ FIRST!)

QuickMUD uses **THREE** task tracking systems. **ALWAYS update the appropriate file when completing work.**

### 1. TODO.md - High-Level Project Phases ✅ COMPLETE
- **Purpose**: 14 major project steps (data models → networking → deployment)
- **Status**: ALL STEPS COMPLETE - use for historical reference only
- **DO NOT UPDATE** - this tracks completed infrastructure work

### 2. ARCHITECTURAL_TASKS.md - ROM Parity Integration Tasks ✅ COMPLETE
- **Purpose**: Architecture-level integration gaps identified by AGENT.md analysis
- **Status**: ALL 7 P0/P1 tasks completed (2025-12-19)
- **When to Update**: Historical reference only - DO NOT UPDATE
- **Use Instead**: `ROM_PARITY_FEATURE_TRACKER.md` for remaining work
- **Completed Tasks**:
  - ✅ `[P0] Implement ROM LastObj/LastMob state tracking in reset_handler`
  - ✅ `[P0] Integrate encumbrance limits with inventory management`
  - ✅ `[P0] Complete help command dispatcher integration`
  - ✅ `[P0] Implement cross-area reference validation`
  - ✅ `[P1] Complete portal traversal with follower cascading`
  - ✅ `[P1] Implement trust-based help topic filtering`
  - ✅ `[P1] Complete format edge case error handling`

**✅ LEGACY FILE** - Use `ROM_PARITY_FEATURE_TRACKER.md` for active work

### 3. ROM_PARITY_FEATURE_TRACKER.md - Complete ROM Parity Feature List 🎯 PRIMARY
- **Purpose**: Comprehensive tracking of ALL ROM 2.4b C features needed for 100% parity
- **Status**: Single source of truth for remaining parity work
- **When to Update**: When implementing any ROM parity features
- **Coverage**: 100% feature mapping (advanced mechanics, not just basic functionality)
- **Priority Levels**: P0-P3 matrix for implementation planning
- **Features**: Detailed breakdown of every missing ROM feature with C references

**🎯 PRIMARY SOURCE OF TRUTH** - **USE THIS FILE** for:
- Identifying next parity work
- Checking implementation status
- Planning development roadmap
- Tracking progress toward 100% ROM parity

### 4. PROJECT_COMPLETION_STATUS.md - Subsystem Confidence Tracking
- **Purpose**: Tracks 27 subsystems by confidence score (0.00-1.00)
- **Updated By**: `scripts/test_data_gatherer.py` (automated) or manual analysis
- **When to Update**: After major subsystem work or test additions
- **Confidence Levels**:
  - ✅ Complete: ≥0.80 (production-ready)
  - ⚠️ Needs Work: <0.80 (incomplete)

**Check this file** to identify which subsystems need attention.

### Task Tracking Workflow

**When starting work:**
1. Check `ROM_PARITY_FEATURE_TRACKER.md` for specific parity features to implement
2. Check `PROJECT_COMPLETION_STATUS.md` for subsystem confidence levels
3. Use `CURRENT_STATUS_SUMMARY.md` for overall project overview

**When completing work:**
1. ✅ Mark features complete in `ROM_PARITY_FEATURE_TRACKER.md`
2. Update subsystem confidence in `PROJECT_COMPLETION_STATUS.md` if applicable
3. Run `pytest` to verify no regressions
4. Update `CURRENT_STATUS_SUMMARY.md` for major milestones

**Example completion format:**
```markdown
### 1. Reset System (confidence 0.38) - LastObj/LastMob State Tracking

**✅ [P0] Implement ROM LastObj/LastMob state tracking in reset_handler** - COMPLETED 2025-12-19

- **FILES**: `mud/spawning/reset_handler.py`, `mud/loaders/reset_loader.py`
- **COMPLETED BY**: [Your completion notes here]
- **TESTS ADDED**: `tests/test_reset_state_tracking.py` (15 tests)
- **ACCEPTANCE**: ✅ `pytest tests/test_area_loader.py::test_midgaard_reset_validation` passes
```

### Quick Reference: Which File to Update?

| Work Type | Update File |
|-----------|-------------|
| **ROM parity feature implementation** | `ROM_PARITY_FEATURE_TRACKER.md` 🎯 **PRIMARY** |
| Subsystem confidence changed significantly | `PROJECT_COMPLETION_STATUS.md` |
| Session summary or milestone | `CURRENT_STATUS_SUMMARY.md` |
| Builder tools or OLC work | Individual completion reports (e.g., `BUILDER_TOOLS_COMPLETION.md`) |
| Architectural integration (HISTORICAL) | `ARCHITECTURAL_TASKS.md` ✅ **COMPLETE** |
| General todos (infrastructure) | `TODO.md` (rarely - mostly complete) |

---

## Build/Lint/Test Commands
```bash
# Run all tests (200+ tests, ~16s)
pytest

# Run single test file
pytest tests/test_combat.py

# Run specific test function
pytest tests/test_combat.py::test_rescue_checks_group_permission

# Run tests matching keyword
pytest -k "movement"

# Run with coverage (CI requirement: ≥80%)
pytest --cov=mud --cov-report=term --cov-fail-under=80

# Lint with ruff
ruff check .
ruff format --check .

# Type check with mypy (strict on specific modules)
mypy mud/net/ansi.py mud/security/hash_utils.py --follow-imports=skip
```

## Code Style Guidelines

**Imports:** `from __future__ import annotations` first; stdlib, third-party, local (alphabetical within groups)  
**Types:** Strict annotations throughout; use `TYPE_CHECKING` guard for circular imports  
**Naming:** `snake_case` functions/vars, `PascalCase` classes, `UPPER_CASE` constants, `_prefix` for private  
**Docstrings:** Required for public functions; include ROM C source references for parity code  
**Error handling:** Defensive programming with try/except; specific exceptions where possible  
**Formatting:** Line length 120 (ruff/black), double quotes, 4-space indent

## ROM Parity Rules (CRITICAL)
- **RNG:** Use `rng_mm.number_*` family, NEVER `random.*` in combat/affects  
- **Math:** Use `c_div`/`c_mod` for C integer semantics, NEVER `//` or `%`  
- **Comments:** Reference ROM C sources (e.g., `# mirroring ROM src/fight.c:one_hit`)  
- **Tests:** Golden files derived from ROM behavior; assert exact C semantics  
- See `port.instructions.md` for exhaustive parity rules

## Test Fixtures (from conftest.py)
```python
movable_char_factory(name, room_vnum, points=100)  # Test character with movement
movable_mob_factory(vnum, room_vnum, points=100)   # Test mob with movement  
object_factory(proto_kwargs)                       # Object without placement
place_object_factory(room_vnum, vnum=..., proto_kwargs=...)  # Object in room
portal_factory(room_vnum, to_vnum, closed=False)   # Portal object
ensure_can_move(entity, points=100)                # Setup movement fields
```

## CI Workflow
Pre-commit hooks run `black`, `ruff --fix`, and fixture lint. CI runs: help data drift check, ruff/flake8 lint, mypy type check (select modules), pytest with 80% coverage, telnet tests (Linux only). All must pass.
