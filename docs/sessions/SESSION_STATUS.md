# Session Status — 2026-06-20 — Differential harness: group/follow + GROUP-006

## Current State

- **Active focus**: Expanding the differential harness (`tools/diff_harness/`) —
  the only enumeration-*independent* parity oracle now that the per-file audit
  tracker is drained (`DIVERGENCE_CLASS_ROSTER.md` guardrail #3).
- **Last completed** (this session): authored the **`group_follow_cycle`**
  scenario on the zero-coverage group/follow surface. Unlike the prior session's
  clean negatives, it **surfaced a real engine divergence**:
  - **GROUP-006 / FINDING-037** — `do_group`'s roster listed members oldest-first;
    ROM walks `char_list` newest-first (head-insert). Fixed →
    `reversed(character_registry)`. This is the **first observable re-open** of
    INV-045's "lower-stakes forward walk" residual (GROUP-003 had deferred it).
  - Two harness-setup parity fixes in `pyreplay.py`: mirror `make_test_char`'s
    new-player exp init (1000 xp in the group line) + drop `__charm_mob`'s leaked
    `add_follower` message (C meta is output-silent).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-20_DIFF_HARNESS_GROUP_FOLLOW.md](SESSION_SUMMARY_2026-06-20_DIFF_HARNESS_GROUP_FOLLOW.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.202 |
| Differential scenarios | 45 / 45 converge (`KNOWN_DIVERGENCES` empty) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Differential harness widening |

## Next Intended Task

**Continue widening the differential harness.** Still grep-verified as exercised
by zero scenarios:

- **Character advancement** — `practice` / `train` / `gain` (`gain` is the
  cleanest deterministic slice: XP/level math, train/practice counters).
- **Death lifecycle** — `corpse` → auto-loot / auto-gold → `sacrifice` (the
  `mob_death_trigger` scenario fires the trigger, not the corpse/loot mechanics).

Method (reinforced this session): even a "deterministic" scenario can trip
RNG/setup asymmetries — bracket spawns with `__seed`, mirror `make_test_char`
defaults in `pyreplay.py`, keep meta-commands output-silent. A divergence is a
**FINDING** (FINDINGS.md → `/rom-gap-closer` (local) or new INV-NNN (cross-file)
→ fix Python/data, **never** overwrite the golden). Build/regen needs the shim
(`cd src && make -f Makefile.diffshim diffshim`; built). Capture per-scenario
(`--scenario <name>`), never `--all`.

Secondary / housekeeping (do NOT lead with these):
- `test_all_commands.py` `tap` alias false-positive (low).
- Cross-file INV probe / signed-math (class 7) — diminishing returns; fall back
  here only if harness work stalls.
- **Risk posture**: HIGH-blast-radius behavioral changes → file, don't fix.
  Adding harness scenarios is read-only on the engine (test data only); a small
  engine fix (like GROUP-006) is fine when impact analysis is LOW and a guard
  test locks it.
