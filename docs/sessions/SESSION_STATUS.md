# Session Status — 2026-06-08 — INV-040: affect_to_char full-apply fix (2.13.28)

## Current State

- **Active mode**: cross-file invariants / diff-harness expansion (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **INV-040 AFFECT-TO-CHAR-FULL-APPLY closed (2.13.28).** `Character.affect_to_char`
    now calls `affect_modify(True)` (ROM src/handler.c:1278) so stat mods are applied.
    `game_loop.py` plague-spread `location="str"` fixed to `location=1` (APPLY_STR).
    2 integration tests added. Budget now 25 INVs enforced.
  - **Open separate finding**: `affect_join` miss — plague re-infection stacks a second
    AffectData instead of merging (⚠️ Partial in HANDLER_C_AUDIT.md row `affect_join`).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-08_INV040_AFFECT_TO_CHAR_FULL_APPLY.md](SESSION_SUMMARY_2026-06-08_INV040_AFFECT_TO_CHAR_FULL_APPLY.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.28 |
| Tests | 5447 passing, 4 skipped |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 25 enforced (budget ~20; INV-040 added this session) |
| Diff-harness scenarios | 10 static + 16 generated-oracle tests |
| Diff-harness shop scenarios | `shop_buy_weapon`, `shop_sell_weapon`, `shop_buy_insufficient_funds` |
| Shop integration tests | 15 passing |

## Next Intended Task

**`affect_join` for plague re-infection** — implement `affect_join` in `mud/handler.py`
mirroring ROM `src/handler.c:1464-1483` (search existing same-type affect → average
level + sum duration+modifier → remove old → call affect_to_char). Update
`mud/game_loop.py:_char_update_tick_effects` plague-spread path to call `affect_join`
instead of `affect_to_char` directly. Test: carrier infects a victim who already has
plague → single merged entry (not two stacked), level averaged, duration summed.

Secondary target: **`shop_sell_keeper_broke` diff-harness scenario** — needs
`__mob_gold=0`/`__mob_silver=0` meta-commands in `diffmain.c` + `pyreplay.py`.
