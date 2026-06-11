# Session Status — 2026-06-11 — FIGHT-055 xp_compute alignment gaps closed

## Current State

- **Active audit**: Cross-file invariants pass (all per-file P0/P1/P2 rows at 100%)
- **Last completed**: FIGHT-055 (`mud/groups/xp.py:xp_compute` — (A) removed early return
  `if base_exp <= 0: return 0` so alignment always mutates, including the UMAX(1,change)
  minimum-1 shift for zero-base-exp kills; (B) replaced pre-mutation `gch_alignment` snapshot
  with `post_alignment = gch.alignment` in the XP multiplier, matching ROM `fight.c:1916+`
  which reads the field post-mutation)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-11_FIGHT055_XP_COMPUTE_ALIGNMENT.md](SESSION_SUMMARY_2026-06-11_FIGHT055_XP_COMPUTE_ALIGNMENT.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.1 |
| Tests | 5597/5601 passing, 4 skipped (full suite run 2026-06-11) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants (next free ID: INV-044) |

## Next Intended Task

INV-044 slot is free. The three probes from the previous STATUS are now closed
(check_assist ordering — no gap; do_rescue stop-fighting args — no gap; violence_update
position guard — no gap). FIGHT-055 filed and closed. Suggested next probes:

1. **`group_gain` NPC-level-contribution floor** — ROM `src/fight.c:1751`
   `total_levels += gch->level / 2` for NPCs (integer division; a level-1 NPC contributes 0).
   Python `mud/groups/xp.py:group_gain` uses `level // 2` which matches for non-negative, but
   confirm the `total_levels <= 0` fallback and the NPC-in-group edge case.

2. **`apply_damage` death-message broadcast** — ROM `src/fight.c:505-560` logs kills differently
   for NPC vs PC, and broadcasts "is DEAD!!" to room. Verify Python `mud/combat/engine.py:apply_damage`
   death-message broadcast matches ROM.

3. **`damage` zero-dam WEAPON_NONE path** — ROM `src/fight.c:375` — when `dam_type == WEAPON_NONE`
   and `dam == 0`, ROM still calls `update_pos`. Verify Python `apply_damage` handles the
   zero-damage weapon-hit edge case identically.
