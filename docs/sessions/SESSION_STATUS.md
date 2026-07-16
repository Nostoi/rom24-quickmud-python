# Session Status — 2026-07-16 — Follower-disband sweep (clean + guard) & FIGHT-095 de-risk

## Current State

- **Active focus**: **cross-file invariants / divergence-class probe** mode
  remains the parity default (per-file audit tracker at 100%, documented backlog
  drained). This continuation session ran a follower-disband sweep and drove the
  one open actionable gap (FIGHT-095) to de-risked-and-characterized.
- **This run (v2.14.317 → v2.14.319):** 1 clean probe + 1 new guard, and 1 gap
  de-risked (not closed).
  - **Follower-disband edges — CLEAN + guard.** `add_follower`/`stop_follower`/
    `die_follower` (`mud/characters/follow.py`) and their full ROM call-site set
    verified faithful vs `src/act_comm.c:1591-1680`. New behavioral guard
    `test_player_config.py::test_nofollow_detaches_existing_followers` locks the
    previously-untested `do_nofollow → die_follower` detach leg (mutation-tested).
    Commit `2bf19447`.
  - **FIGHT-095 — de-risked, still OPEN.** Retired its stated blocker: the C
    oracle is deterministic within-build (twice-capture of every RNG-adjacent
    scenario → byte-identical; the `capture --check` CHANGED is cross-build
    provenance drift, not nondeterminism). Identified its real nature: an
    unconformed **NESTED** site of INV-045 (CHAR-LIST-WALK-ORDER) — ROM
    head-inserts `char_list` (newest-first) vs Python `character_registry.append`
    (oldest-first). Fix pattern proven by GROUP-006 (`reversed(character_registry)`).
    Closure blocked only on two additive diff-harness primitives (mob off_flags +
    cross-room grouped-member placement); deliberately not started on a replay
    turn. Commit `4ba46807` (docs).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-07-16_FOLLOWER_DISBAND_SWEEP_FIGHT095_DERISK.md](SESSION_SUMMARY_2026-07-16_FOLLOWER_DISBAND_SWEEP_FIGHT095_DERISK.md)
- **Prior session (same date)** (extract-cleanup matrix sweep, INV-020/047 legs):
  [SESSION_SUMMARY_2026-07-16_EXTRACT_CLEANUP_MATRIX_DIVERGENCE_SWEEP.md](SESSION_SUMMARY_2026-07-16_EXTRACT_CLEANUP_MATRIX_DIVERGENCE_SWEEP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.319 |
| Tests | **6209 passed, 4 skipped, 0 failed** — clean parallel run (299s). (+1 vs prior 6208, the new nofollow guard.) |
| ROM C files audited | 43 / 43 |
| Push status | **Local only** — 2 commits this run (`2bf19447`, `4ba46807`) + 7 from the prior same-date run, NOT pushed (commit-local directive); operator to review + push/publish. |
| Active focus | Cross-file invariants / divergence-class probe |

## Outstanding — deferred by design

- **FIGHT-095** (OPEN) — unconformed nested INV-045 site (`check_assist` inner
  reservoir loop). Oracle-trust blocker retired; closure spec recorded. Needs two
  additive diff-harness primitives (mob off_flags directive + cross-room
  grouped-member placement) → author scenario → capture golden → port `assist.py`
  to the reversed positional-slice (GROUP-006/GL-040 pattern) → lock via replay
  test. Route: `/rom-gap-closer FIGHT-095`.
- **FIGHT-094** (OPEN) — `check_killer` placement inside `damage()` vs command layer.
- **DESC-001** (latent) — unreachable plain-replace description path.
- **OLC spell-name lookup** (`build.py:2617/2637`) — Tier-C deferred.
- **IS_BUILDER** (`look.py:261`) — TODO, area-builder subsystem not yet added.
- **Stray unused SQLite files** — `data/quickmud.db` (0 bytes), `doc/game.db`
  (stale). Confirm unused, then clean up.

## Next Intended Task

Close **FIGHT-095** as a dedicated (non-replay) effort — it now has an exact
closure spec (extend the diff-harness with the two missing primitives, then the
standard capture → port-reversed-slice → lock arc). Otherwise resume the
divergence-class sweep on un-probed surfaces, noting the split-extract/follower
vein is exhausted (further faithful-function probes expected mostly clean).
