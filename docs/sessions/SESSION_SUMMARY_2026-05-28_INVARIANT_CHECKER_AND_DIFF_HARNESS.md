# Session Summary — 2026-05-28 — game_tick invariant checker (2.10.0) + differential harness v1 (branch)

## Scope

Continuation of the same day's `room_registry` isolation-leak session
(`SESSION_SUMMARY_2026-05-28_ROOM_REGISTRY_ISOLATION_LEAK.md`). The user asked
to make ROM→Python parity verification more systematic rather than
judgment-driven. We scoped two complementary capabilities (brainstormed and
spec'd both), built one outright on `master`, and built the other v1 on an
isolated branch:

1. **Always-on `game_tick` invariant checker** — built + shipped on `master`
   (2.10.0).
2. **Differential testing harness (ROM C ⇄ Python)** — built v1 on branch
   `diff-harness` (kept, not merged: v1 carries an open finding).

## Outcomes

### `game_tick` invariant checker — ✅ SHIPPED (master, 2.10.0)

- **New**: `mud/diagnostics/invariants.py` — `check_world_invariants()` walks the
  live registries after every `game_tick` during the test suite and raises
  `InvariantViolation` on a broken steady-state ROM structural invariant. v1
  asserts **FIGHTING-COHERENCE** (INV-005/006: a fighting char's target is in the
  same room and not DEAD) and **ROOM-PEOPLE-COHERENCE** (INV-010: `room.people`
  ↔ `char.room` agree both directions).
- **Wiring**: gated hook at the end of `mud/game_loop.py:game_tick`
  (`_INVARIANT_CHECK_ENABLED`, **off in production** — zero live-loop overhead);
  autouse enablement in `tests/conftest.py`; opt out per-test with
  `@pytest.mark.no_invariant_check` (registered in `pyproject.toml`).
- **Fallout (fix-fallout mode)**: surfaced exactly 3 of the 17 `game_tick`
  test files, all **artificial setups** (two use `object()` sentinel rooms;
  `test_resets::test_execution_cycle` strips mobs from `room.people` but leaves
  them registered) — marked `no_invariant_check`. **Zero real bugs**, which is
  reassuring for these two invariants.
- **Tests**: `tests/test_invariant_checker.py` (7 cases — coherent passes, each
  violation caught, marker disables). Full suite green: **4905 passed, 4
  skipped**. Commit `04e8f67d`.

### Differential testing harness v1 — ✅ BUILT (branch `diff-harness`, 2.11.0 on branch)

Golden-trace capture/replay tool: runs the Python port and the original ROM
2.4b6 C engine through identical scripted scenarios and diffs state + output.
The usual nondeterminism blocker is already solved — the C engine builds with
`-DOLD_RAND` so its Mitchell-Moore RNG matches `mud/utils/rng_mm.py`.

- **Python side** (TDD, 6 unit tests): `tools/diff_harness/{schema,compare,pysnap,scenario}.py`.
- **C side** (built by an Opus subagent; ROM `src/*.c` byte-for-byte unchanged,
  all macOS portability via compile flags + shim headers): `src/diff_shim/diffmain.c`
  + `src/Makefile.diffshim` → `src/diffshim`, which drives ROM's real `interpret()`
  from stdin and emits JSON output/snapshots. Verified by hand.
- **Capture + replay**: `tools/diff_harness/capture.py` writes committed goldens
  (`tests/data/golden/diff/`); `tests/test_differential_smoke.py` replays Python
  and diffs (pure-Python, no C build needed at test time).
- **First-run finding — FINDING-001**: room `look` renders an NPC by name
  (`Hassan`) vs ROM `long_descr` (`Hassan is here, waiting...`). Root cause
  ambiguous: `area/midgaard.are` is malformed and the C side reads a *repaired*
  overlay while Python reads the *original* (unequal inputs), plus a possible
  instance-vs-prototype `long_descr` gap (with unexplained diagnostic
  nondeterminism). Documented in `tools/diff_harness/FINDINGS.md`; gated as a
  self-clearing `xfail`. Branch full suite: **4911 passed, 4 skipped, 1 xfailed**.

Specs: `docs/superpowers/specs/2026-05-28-{game-tick-invariant-checker,differential-testing-harness}-design.md`.
Plan: `docs/superpowers/plans/2026-05-28-differential-testing-harness.md`.

## Files Modified (master)

- `mud/diagnostics/invariants.py` (new), `mud/game_loop.py` (gated hook),
  `tests/conftest.py` (autouse enablement), `tests/test_invariant_checker.py`
  (new), 3 tests marked `no_invariant_check`, `pyproject.toml` (marker + 2.10.0),
  `CHANGELOG.md`, the two design specs + the plan.

## Test Status

- Master: full suite **4905 passed, 4 skipped, 0 failed** (verified after the
  invariant checker landed).
- Branch `diff-harness`: **4911 passed, 4 skipped, 1 xfailed** (FINDING-001).

## Outstanding

- **FINDING-001 triage** (branch) — pin the `mob_registry` long_descr diagnostic
  nondeterminism, reconcile C/Python inputs (repair `area/midgaard.are` vs point
  Python at the repaired overlay), then fix the real cause; the xfail
  auto-clears. See `tools/diff_harness/FINDINGS.md`.
- **`diff-harness` branch is local-only and unmerged** — v1 with the open
  finding; merge once FINDING-001 is resolved.
- **INV-025 non-combat narration sweep** (from prior summary) — still open.

## Next Steps

1. Triage FINDING-001 in a focused session.
2. Extend the invariant checker (add INV-003/013/015) one at a time, fix-fallout.
3. Merge `diff-harness` once FINDING-001 is resolved; then a combat/RNG slice.
