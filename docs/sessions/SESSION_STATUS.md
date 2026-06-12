# Session Status — 2026-06-12 — FIGHT-059 injury-feedback messages (2.14.6)

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: FIGHT-059 — added HURT/BLEEDING injury-feedback messages to
  `apply_damage`, mirroring ROM `src/fight.c:864-869` `default:` case. Three other
  probe candidates (stop_fighting both=False call sites, check_killer cross-file
  coherence, position-transition broadcast) verified CLEAN.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_FIGHT059_HURT_BLEEDING_MESSAGES.md](SESSION_SUMMARY_2026-06-12_FIGHT059_HURT_BLEEDING_MESSAGES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.6 |
| Tests | 5609/5609 passing, 4 skipped (2026-06-12) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-045) |

## Next Intended Task

**Cross-file invariant probes** — three fresh candidates, probe-then-scope method:

1. **`check_assist` charm-loop safety** — ROM `src/fight.c:112-170` `check_assist`
   iterates `char_list`; Python iterates `character_registry`. Verify the charm/follow
   chain guard (`fch->master == ch->fighting` at ROM `:138-144`) matches Python's
   equivalent for mobs with ACT_ASSIST.
2. **`violence_update` room-mismatch stopping rule** — ROM `src/fight.c:76-82` calls
   `stop_fighting(ch, FALSE)` when attacker and victim are in different rooms. Verify
   Python `game_loop.py:violence_tick` handles this with `both=False` and no extras.
3. **`gain_exp` level-cap guard** — ROM `src/fight.c:919-924` clamps XP so a kill can't
   push a character past `level+1`. Verify Python `gain_exp` applies the equivalent cap.

For each: read ROM C contract → read Python equivalent → write one failing test if
divergence found → close as single-gap commit or file as INV-NNN.
