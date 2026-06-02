# Session Status — 2026-06-01 — INV-025 command-layer PERS sweep (2.12.48)

## Current State

- **Active mode**: cross-file invariants — the **INV-025 command-layer PERS
  sweep is now CLOSED** (all confirmed `mud/commands/` baked-name
  `room.broadcast(f"{char.name} …")` sites converted to `act_to_room`).
- **Today's progression (all pushed green):**
  - 2.12.40 → 2.12.42: CAST-009 + TRAIN-005 (full suite 5242).
  - 2.12.42 → 2.12.44: MAGIC-012 (frenzy) + MAGIC-013 (cure_disease) —
    manual-room-loop `$n`/`$s` PERS + channel (full suite 5246).
  - 2.12.44 → 2.12.45: **MAGIC-014** (`ed9b35e0`) — batch closure of the ~11
    `$n`-only single-actor spell room lines → `act_to_room` (full suite 5249).
  - 2.12.45 → 2.12.46: **FIGHT-039** (`83e42d33`) — trip self-trip lines colour
    + `$n` PERS + `$s` possessive (full suite 5251).
  - 2.12.46 → 2.12.47: **FIGHT-040** (`4015cccb`) — dirt-kick already-blinded
    uses ROM gendered `$E` in ROM order; deleted Python-invented guards
    (full suite 5256).
  - 2.12.47 → 2.12.48: **INV-025 command-layer sweep** (`ad4ae4aa`) — 10
    baked-name `room.broadcast` sites in `advancement.py` (practice ×2, train
    ×3), `session.py` (recall pray/disappear/appear), `notes.py` (note
    start/finish, restored `{G..{x` colour + `$s` possessive, removed
    `_possessive` helper) → `act_to_room(room, "$n …", char, exclude=char)`,
    each verified vs its exact ROM `act()` string. New
    `test_inv025_command_layer_pers.py` (invisible→"Someone", visible→name);
    re-baselined `test_do_practice_command::test_practice_room_messages` from a
    mocked `room.broadcast` to a sighted-witness assertion. **Full suite 5259
    passed, 4 skipped.**

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_INV025_COMMAND_LAYER_PERS.md](SESSION_SUMMARY_2026-06-01_INV025_COMMAND_LAYER_PERS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.48 |
| Tests | **full suite green: 5259 passed, 4 skipped** (run `pytest -p no:xdist -o addopts="" -q`; under high load `-n auto` hangs at worker fork and `-n0` can hit a broken xdist `sessionfinish` teardown) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | **INV-025 re-probe** — `mud/combat/`, `mud/world/`, `mud/commands/communication.py` (`do_say`/`do_tell`) not yet swept for the same baked-name `room.broadcast` pattern |

## Next Intended Task

1. **Finish the INV-025 baked-name re-probe** — `mud/combat/`, `mud/world/`,
   and `mud/commands/communication.py` (`do_say`/`do_tell`) for the same
   `room.broadcast(f"…{name}…")` pattern that bypasses `act_to_room` PERS
   masking. Confirm each against its ROM `act()` string, then close as a batch.
2. Other cross-file-invariants candidate areas (position transitions, mob script
   triggers) remain once the PERS sweep is exhausted.

> **Push note:** all of today's work (through 2.12.48) is pushed to `master`.
> **Stale index:** GitNexus reindex pending (the running one predates today's
> handler/command edits) — re-run on a quiet machine.
