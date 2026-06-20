# Session Status — 2026-06-20 — Differential harness widening (containers · cast-position · doors)

## Current State

- **Active focus**: Expanding the differential harness (`tools/diff_harness/`) —
  the only enumeration-*independent* parity oracle now that the per-file audit
  tracker is drained and cross-INV / per-file passes are enumeration-dependent
  (`DIVERGENCE_CLASS_ROSTER.md` guardrail #3).
- **Last completed** (3 new scenarios this session, all converge against the
  ROM 2.4b6 C oracle — three clean negatives, no engine divergence):
  - **`container_put_get`** — `put`/get-from-container/`look in`/re-nest cycle
    (bag 3032 + sword 3021), LIFO carry-list order observed through transitions.
  - **`cast_position_gate`** — **differentially locks this session-cluster's
    CAST-013 fix**: `cast armor` (`POS_STANDING`) rejected at FIGHTING(7),
    accepted at STANDING(8). The reject leg is the exact regression a flat
    `POS_FIGHTING` gate could not produce.
  - **`door_lock_cycle`** — full keyed-door lifecycle 3110→3142 (key 3120):
    open-while-locked reject → unlock → open → traverse → close → lock; confirms
    Python applies the closed+locked D-reset identically to ROM `reset_room`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-20_DIFF_HARNESS_CONTAINER_CAST_DOOR.md](SESSION_SUMMARY_2026-06-20_DIFF_HARNESS_CONTAINER_CAST_DOOR.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.201 |
| Tests | 71 passed (differential slice: smoke + unit); full suite 6002+ as of v2.14.200 |
| Differential scenarios | 44 / 44 converge (`KNOWN_DIVERGENCES` empty) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Differential harness widening |

## Clean negatives this session (verified parity, no gap)

- Container put/get-from/look-in/nest cycle — converges.
- Cast position gate (per-spell `minimum_position`, CAST-013) — converges.
- Keyed-door open/unlock/close/lock cycle — converges.

## Next Intended Task

**Continue widening the differential harness.** Still grep-verified as exercised
by zero scenarios:

- **Character advancement** — `practice` / `train` / `gain`.
- **Death lifecycle** — `corpse` → auto-loot / auto-gold → `sacrifice` (the
  `mob_death_trigger` scenario fires the trigger, not the corpse/loot mechanics).
- **Group / follow** — `follow` / `group`.

These mix RNG (practice/train rolls, combat-to-death), so they need careful
`__seed` bracketing (the `shop_buy_weapon.json` / `affect_armor.json` technique).
**Author the deterministic slice first** (`gain` XP/level math, `sacrifice`
mechanics, `group`/`follow` membership) before the RNG legs. Build/regen needs
the C shim: `cd src && make -f Makefile.diffshim diffshim` (already built this
session); capture **per-scenario** (`--scenario <name>`), never `--all` (avoids
provenance churn on the other goldens). A divergence is a **FINDING** —
triage → `FINDINGS.md` → `/rom-gap-closer` (local) or new INV-NNN (cross-file) →
fix Python/data, **never** overwrite the golden.

Secondary / housekeeping (do NOT lead with these):
- `test_all_commands.py` `tap` alias false-positive (resolves to `sacrifice`;
  harness artifact, low — make the probe alias-aware if revisited).
- Cross-file INV probe / signed-math (class 7) — valid but diminishing returns;
  fall back here only if the harness work stalls.
- **Risk posture**: HIGH-blast-radius behavioral logic changes → file, don't fix.
  Adding harness scenarios is strictly read-only on the engine (test data only).
