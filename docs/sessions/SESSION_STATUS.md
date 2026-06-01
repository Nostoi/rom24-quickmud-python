# Session Status — 2026-06-01 — INV-025 spell-effect/healer/spec_fun ACT trigger dispatch (2.12.23)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session, 2.12.23)**:
  - **INV-025 spell-effect / healer / spec_fun ACT trigger sweep — COMPLETED**.
    - `mud/skills/handlers.py`: Added `_act_room` helper combining `broadcast_room` +
      `mp_act_trigger_room`. Converted ~50 `broadcast_room` call sites to `_act_room`,
      covering bless, blindness, cancellation wear-off, chain_lightning, change_sex,
      disarm, faerie_fire/fog, gate, holy_word, recall, teleport, word_of_recall,
      invis, mass_invis, sanctuary, shield, fly, giant_strength, weaken, frenzy,
      heat_metal, floating_disc, pick, portal, recharge, and all other spell-effect
      room broadcasts. Every `act(TO_ROOM)` in `src/magic.c` / `src/magic2.c` without
      a `MOBtrigger = FALSE` wrap now dispatches TRIG_ACT via `_act_room`.
    - `mud/skills/handlers.py:cancellation` `_broadcast_room_msg` helper now dispatches
      `mp_act_trigger_room` for all 15 wear-off messages, matching ROM `src/magic.c:1062-1196`.
    - `mud/spec_funs.py`: Modified both `_broadcast_room` and `_broadcast_room_message`
      helpers to dispatch `mp_act_trigger_room` for NPC recipients, matching ROM
      `src/comm.c:2384` which fires `mp_act_trigger` inside `act()` for every spec_fun
      utterance/taunt broadcast.
    - `mud/commands/healer.py`: Added `mp_act_trigger_room` dispatch for the healer
      utterance `broadcast_room`, matching ROM `src/healer.c:183`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_INV025_SPELL_EFFECT_ACT_TRIGGER.md](SESSION_SUMMARY_2026-06-01_INV025_SPELL_EFFECT_ACT_TRIGGER.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.23 |
| Targeted tests | `test_inv025_spell_effect_act_trigger.py`: 6 passed |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | None currently filed; INV-025 principle fully applied to handlers.py/spec_funs.py/healer.py |

## Next Intended Task

Continue the broader **INV-025** sweep for remaining non-combat ROM `act()` narrations
whose Python code still calls `broadcast_room` without `mp_act_trigger`. Remaining
surfaces (lower priority — less frequently triggered by player actions):

1. **Music broadcasts** in `mud/music/__init__.py` — ROM `src/music.c` uses `act()` for
   global/room jukebox broadcasts.
2. **Remaining `mud/commands/` command broadcasts** — `do_log`, `do_where`,
   `do_who`, `do_auto` etc. that use `act(TO_ROOM)` in ROM.