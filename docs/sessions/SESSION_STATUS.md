# Session Status — 2026-06-01 — MAGIC-014 single-actor PERS sweep (2.12.45)

## Current State

- **Active mode**: cross-file invariants — the **INV-025 manual-room-loop PERS
  sweep is now DRAINED for magic** (`$n`-only single-actor spell room lines).
- **Today's progression (all pushed green):**
  - 2.12.40 → 2.12.42: CAST-009 + TRAIN-005 (full suite 5242).
  - 2.12.42 → 2.12.44: MAGIC-012 (frenzy) + MAGIC-013 (cure_disease) —
    manual-room-loop `$n`/`$s` PERS + channel (full suite 5246).
  - 2.12.44 → 2.12.45: **MAGIC-014** (`ed9b35e0`) — batch closure of the ~11
    `$n`-only single-actor spell room lines (haste, slow ×2 legs,
    giant_strength, stone_skin, pass_door, sleep, weaken, earthquake,
    create_rose) → `act_to_room`; fixed the visible-NPC "Someone" bug
    (`if name else "Someone"` ternaries) + invisible-actor leaks. Full suite
    **5249 passed, 4 skipped** (no-xdist reliable mode).
  - Probed group/follower + affect-tick engine — both **faithful**.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_MAGIC014_SINGLE_ACTOR_PERS_SWEEP.md](SESSION_SUMMARY_2026-06-01_MAGIC014_SINGLE_ACTOR_PERS_SWEEP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.45 |
| Tests | **full suite green: 5249 passed, 4 skipped** (run `pytest -p no:xdist -o addopts="" -q`; under high load `-n auto` hangs at worker fork and `-n0` can hit a broken xdist `sessionfinish` teardown) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | **FIGHT-039** (trip self-trip colour/`$s`/`$n` — filed open); dirt-kicking "their" caster line needs ROM verification (MAGIC-013 note) |

## Next Intended Task

1. **FIGHT-039** — `trip` self-trip room line (`handlers.py:~7981`, ROM
   `src/fight.c:2701` `act("{5$n trips over $s own feet!{x", …, TO_ROOM)`):
   convert to `act_to_room` with colour + `$s` possessive + `$n` masking
   preserved. Model on FIGHT-036/037 (dirt-kick). One failing-first commit.
2. **Verify the dirt-kicking already-affected caster line**
   (`handlers.py:~3200`, `"{name} already has dirt in their eyes."`) — no ROM
   equivalent found in `src/`; confirm Python-invented before touching.
3. **Re-probe for remaining baked-name room broadcasts outside handlers.py** —
   the INV-025 sweep covered `_act_room` sites + handlers.py manual loops; check
   `mud/commands/`, `mud/combat/`, `mud/spec_funs.py` for `room.broadcast(f"…{name}…")`
   patterns that bypass `act_to_room` PERS masking.
4. Other cross-file-invariants candidate areas (position transitions, mob script
   triggers) remain once the PERS sweep is exhausted.

> **Push note:** all of today's work (through 2.12.45) is pushed to `master`.
> **Stale index:** GitNexus reindex pending (the running one predates the
> MAGIC-012/013/014 handler edits) — re-run on a quiet machine.
