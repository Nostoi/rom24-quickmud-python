# Session Status — 2026-05-31 — DB-001 / INV-032 room-flags fix

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session)**:
  - **DB-001 / INV-032 (2.11.61)** — room flags now survive the
    `.are`→JSON→runtime pipeline (were dropped game-wide). `room_loader.py`
    read `int(tokens[0])` (discarded area-number) instead of letter-decoding
    `tokens[1]`, so every room loaded `room_flags=0` and the converter baked
    zeros into all 52 JSONs. Fixed via new `_parse_room_flag_field` helper +
    `assert len(tokens)==3`; all 52 JSONs regenerated (verified flags-only:
    2064 flag-line changes, zero non-flag changes). School "Darkened Room"
    (3720, `ADR`) is now dark at runtime. INV-032 → ✅ ENFORCED. Side-note
    resolved: exit/door flags are NOT lost (`_locks_to_exit_bits` already
    mirrors `src/db.c:1218-1238`). See `fix(parity): db.c:DB-001` commit.
- **Prior session (2.11.60)** — in-game bug detour: NANNY-015, TRAIN-002,
  CAST-008, TRAIN-003 (see
  [SESSION_SUMMARY_2026-05-31_INGAME_BUGS_TRAIN_CAST.md](SESSION_SUMMARY_2026-05-31_INGAME_BUGS_TRAIN_CAST.md)).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.61 |
| Tests | 5102 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 24 enforced — all rows enforced (tracker is source of truth; INV-032 flipped this session) |
| Open correctness gaps | none |
| Active focus | cross-file invariants probe pass |

## Next Intended Task

No open correctness gaps. Resume the **cross-file invariants probe pass**
(per-file audit tracker is exhausted — this is the active mode):

1. **TRAIN-004 candidate** — file/close the `get_max_train` hardcoded-22
   divergence in `ACT_MOVE_C_AUDIT.md` (carried over, not yet filed).
2. Resume the INV-025 act-dispatch slices: `do_close` / `do_lock` /
   `do_unlock` / `do_pick` `TRIG_ACT` dispatch (same pattern as the
   `do_open` follow-up already closed).
3. Other probe candidates (AGENTS.md): affect ticks, position transitions,
   mob script triggers, group/follower chain.

Method: probe-then-scope (read ROM C contract → read Python equivalent →
one failing test for the contract → close as a gap or file as next INV-NNN).
