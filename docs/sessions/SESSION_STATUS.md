# Session Status — 2026-05-31 — GL-033 mob stat floor (2.12.12)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session, 2.12.12)**:
  - **GL-033 — CLOSED**. `MobInstance.get_curr_stat` clamped raw effective
    stats to a minimum of `0`, while ROM `get_curr_stat`
    (`src/handler.c:868-874`) uses `URANGE(3, perm_stat + mod_stat, max)` for
    both PCs and NPCs. After GL-032 added NPC `mod_stat`, negative stat affects
    made the divergence reachable for live mobs; directly-constructed zero-stat
    fixtures also skewed bash/disarm/dirt-kick expectations. Raised the NPC
    floor to 3 and re-derived the affected combat chances against ROM.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-31_GL033_MOB_STAT_FLOOR.md](SESSION_SUMMARY_2026-05-31_GL033_MOB_STAT_FLOOR.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.12 |
| Targeted tests | `test_get_curr_stat_floor_three.py`: 23 passed; `test_skill_combat_rom_parity.py`: 104 passed |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 24 enforced |
| Open correctness gaps | None currently filed in `UPDATE_C_AUDIT` after GL-033 closure. |
| Active focus | cross-file invariants probe pass |

## Next Intended Task

Resume the cross-file-invariants probe pass. Remaining candidates from the prior
status:

1. **Position transitions**.
2. **Group/follower chain**.
3. **Broader INV-025 sweep** — non-combat `_push_message`/`broadcast_room`
   narration where the matching ROM site uses `act()`.

Method: probe-then-scope (read ROM C contract → read Python equivalent →
one failing test for the contract → close as a gap or file as next INV-NNN).
