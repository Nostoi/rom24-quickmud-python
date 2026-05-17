# update.c Parity Audit

**ROM C source**: `src/update.c`  
**Python modules**: `mud/game_loop.py`, `mud/advancement.py`  
**Audited**: 2026-05-17  
**Auditor**: OpenCode session  

---

## Scope

`src/update.c` contains eleven functions:

| ROM C function | Python equivalent | Notes |
|---|---|---|
| `advance_level()` | `advance_level()` | mud/advancement.py |
| `gain_exp()` | `gain_exp()` | mud/advancement.py |
| `hit_gain()` | `hit_gain()` | game_loop.py |
| `mana_gain()` | `mana_gain()` | game_loop.py |
| `move_gain()` | `move_gain()` | game_loop.py |
| `mobile_update()` | `mobile_update()` | mud/ai.py |
| `weather_update()` | `weather_tick()` + `time_tick()` | split — intentional divergence |
| `char_update()` | `char_update()` | game_loop.py |
| `obj_update()` | `obj_update()` | game_loop.py |
| `aggr_update()` | `aggressive_update()` | mud/ai.py |
| `update_handler()` | `game_tick()` | game_loop.py |

---

## Gap Table

| ID | Severity | ROM C location | Description | Status |
|---|---|---|---|---|
| GL-001 | N/A | — | `hit_gain` heal_rate, furniture value[3], NPC/PC branches | ✅ CORRECT |
| GL-002 | N/A | — | `move_gain` heal_rate, furniture value[3] | ✅ CORRECT |
| GL-003 | N/A | — | `game_tick` / `update_handler` ordering fixed this session | ✅ FIXED (this session) |
| GL-004 | BUG | update.c:297 | `mana_gain` uses `heal_rate` instead of `mana_rate` for room scaling | ✅ FIXED |
| GL-005 | BUG | update.c:300 | `mana_gain` furniture bonus uses `value[3]` instead of `value[4]` | ✅ FIXED |
| GL-006 | N/A | — | `update_handler` tick ordering corrected this session | ✅ FIXED (this session) |
| GL-007 | N/A | — | `run_npc_specs` moved inside PULSE_MOBILE gate this session | ✅ FIXED (this session) |
| GL-008 | N/A | — | `tail_chain` — ROM C memory chain; Python GC handles this | N/A |
| GL-009 | GAP | update.c:688-696 | NPC wanders-home: if NPC is outside its zone, 5% chance → act + extract_char | ✅ FIXED |
| GL-010 | PARTIAL | update.c:762-786 | Affect tick: consecutive same-type suppression of `msg_off` not implemented in `tick_spell_effects` | DEFERRED (see note) |
| GL-011 | GAP | update.c:794-846 | Plague tick: spread to room, drain mana/move, damage(ch,ch,dam,gsn_plague) | ✅ FIXED |
| GL-012 | GAP | update.c:848-862 | Poison tick: act shiver message + damage(ch,ch,level/10+1,gsn_poison) | ✅ FIXED |
| GL-013 | GAP | update.c:864-867 | POS_INCAP tick: 50% chance damage(ch,ch,1,TYPE_UNDEFINED) | ✅ FIXED |
| GL-014 | GAP | update.c:868-871 | POS_MORTAL tick: damage(ch,ch,1,TYPE_UNDEFINED) every tick | ✅ FIXED |
| GL-015 | BUG | update.c:741-744 | `_idle_to_limbo` sets `fighting=None` directly; ROM calls `stop_fighting(ch,TRUE)` | ✅ FIXED |
| GL-016 | N/A | — | Immortal timer/light ordering — Python equivalent is logically correct | ✅ CORRECT |
| GL-017 | PARTIAL | update.c:939-957 | `obj_update` affect wear-off: consecutive same-type suppression not implemented | DEFERRED (see note) |
| GL-018 | GAP | update.c:1017-1023 | Pit-corpse suppression: items inside a no-take pit suppress room decay message | ✅ FIXED |
| GL-019 | DIVERGENCE | update.c:530-556 | Time advancement is inside `weather_update` in ROM C; Python splits into `time_tick()` | INTENTIONAL |
| GL-020 | N/A | — | `weather_info.change` RNG expression — Python 3-call equivalent produces same distribution | ✅ CORRECT |
| GL-021 | GAP | update.c:1186 | Point pulse emits `wiznet("TICK!", NULL, NULL, WIZ_TICKS, 0, 0)` before weather/char/obj update work. | ✅ FIXED |
| GL-022 | BUG | update.c:128-139 | `gain_exp()` sent the level-up banner after `advance_level()` and skipped ROM `log_string("%s gained level %d")` entirely. | ✅ FIXED |
| GL-023 | BUG | update.c:61-139 | `advance_level()` / `gain_exp()` XP-path verification was not represented in this audit even though the ROM functions live in `update.c`. | ✅ FIXED — audit coverage now explicitly includes `mud/advancement.py`; targeted tests lock message order, log-before-wiznet ordering, and death-floor behavior. |

### Notes on DEFERRED items

- **GL-010 / GL-017** (consecutive affect suppression): ROM C suppresses `msg_off`/`msg_obj` when the
  next affect in the list has the same type and a positive duration. This prevents double-messages when
  stacked affects of the same spell wear off one at a time. `tick_spell_effects` and
  `_tick_object_affects` don't implement this. Deferring because it requires `affects` to be an ordered
  list with type tracking, which is an architectural change. No gameplay breakage — at worst players see
  an extra wear-off message.

---

## Integration Tests

See `tests/integration/test_update_c_parity.py`, `tests/test_advancement.py`, and `tests/integration/test_character_advancement.py`.

| Test | Gap(s) covered |
|---|---|
| `test_mana_gain_uses_mana_rate` | GL-004 |
| `test_mana_gain_furniture_uses_value4` | GL-005 |
| `test_idle_to_limbo_calls_stop_fighting` | GL-015 |
| `test_npc_wanders_home_out_of_zone` | GL-009 |
| `test_plague_tick_damages_and_spreads` | GL-011 |
| `test_poison_tick_deals_damage` | GL-012 |
| `test_incap_tick_damage` | GL-013 |
| `test_mortal_tick_damage` | GL-014 |
| `test_pit_corpse_suppresses_decay_message` | GL-018 |
| `test_point_pulse_emits_tick_wiznet_before_updates` | GL-021 |
| `test_gain_exp_sends_level_message_before_advance_level_gains` | GL-022 |
| `test_gain_exp_logs_level_gain_before_wiznet` | GL-022 |
| `test_xp_loss_on_death` / `test_player_kill_applies_rom_death_penalty` | GL-023 |
