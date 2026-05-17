# Plan — 2026-05-17 — mobile_update wander-gate enforcement

## Goal
Add deterministic ROM-backed enforcement coverage for `mobile_update()` wander restrictions that are still represented as skipped/conditional integration tests.

## ROM source of truth
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/update.c:495-507`

## Python surface
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/ai/__init__.py:_maybe_wander`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_mob_ai.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/INTEGRATION_TEST_COVERAGE_TRACKER.md`

## Steps
1. Revert unrelated dirty log output so the worktree contains only parity work.
2. Trace the ROM wander gate predicates for `ACT_STAY_AREA`, `ACT_OUTDOORS`, and `ACT_INDOORS`.
3. Replace world-data-dependent mob-AI tests with deterministic synthetic room/area fixtures.
4. Force the wander attempt with seeded/monkeypatched RNG so the tests prove the gate itself, not probability over many ticks.
5. Re-run the focused mob-AI slice and update coverage/session docs with the new enforced status.
