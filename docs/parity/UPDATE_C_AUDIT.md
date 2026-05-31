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
| GL-010 | BUG | update.c:762-786 | `tick_spell_effects` removed merged `spell_effects` entries even when a later same-type `AffectData` remained active, and did not honor ROM same-type wear-off suppression semantics. | ✅ FIXED |
| GL-011 | GAP | update.c:794-846 | Plague tick: spread to room, drain mana/move, damage(ch,ch,dam,gsn_plague) | ✅ FIXED |
| GL-012 | GAP | update.c:848-862 | Poison tick: act shiver message + damage(ch,ch,level/10+1,gsn_poison) | ✅ FIXED |
| GL-013 | GAP | update.c:864-867 | POS_INCAP tick: 50% chance damage(ch,ch,1,TYPE_UNDEFINED) | ✅ FIXED |
| GL-014 | GAP | update.c:868-871 | POS_MORTAL tick: damage(ch,ch,1,TYPE_UNDEFINED) every tick | ✅ FIXED |
| GL-015 | BUG | update.c:741-744 | `_idle_to_limbo` sets `fighting=None` directly; ROM calls `stop_fighting(ch,TRUE)` | ✅ FIXED |
| GL-016 | N/A | — | Immortal timer/light ordering — Python equivalent is logically correct | ✅ CORRECT |
| GL-017 | BUG | update.c:939-957 | `_tick_object_affects` broadcast duplicate wear-off messages for consecutive zero-duration same-type affects instead of matching ROM’s one-message suppression rule. | ✅ FIXED |
| GL-018 | GAP | update.c:1017-1023 | Pit-corpse suppression: items inside a no-take pit suppress room decay message | ✅ FIXED |
| GL-019 | DIVERGENCE | update.c:530-556 | Time advancement is inside `weather_update` in ROM C; Python splits into `time_tick()` | INTENTIONAL |
| GL-020 | N/A | — | `weather_info.change` RNG expression — Python 3-call equivalent produces same distribution | ✅ CORRECT |
| GL-021 | GAP | update.c:1186 | Point pulse emits `wiznet("TICK!", NULL, NULL, WIZ_TICKS, 0, 0)` before weather/char/obj update work. | ✅ FIXED |
| GL-022 | BUG | update.c:128-139 | `gain_exp()` sent the level-up banner after `advance_level()` and skipped ROM `log_string("%s gained level %d")` entirely. | ✅ FIXED |
| GL-023 | BUG | update.c:61-139 | `advance_level()` / `gain_exp()` XP-path verification was not represented in this audit even though the ROM functions live in `update.c`. | ✅ FIXED — audit coverage now explicitly includes `mud/advancement.py`; targeted tests lock message order, log-before-wiznet ordering, and death-floor behavior. |
| GL-024 | BUG | update.c:818-819 | Plague tick: ROM does `if (af->level == 1) continue;` — a level-1 plague affect skips the entire spread + mana/move drain + `damage()` block that tick. Python `mud/game_loop.py:_char_update_tick_effects` gated only the *spread* on `if af_level > 1:`; the drain and `damage()` still ran when `af_level == 1`. **FIX (2.9.80):** moved the drain + `damage()` block inside the `if af_level > 1:` guard so a level-1 plague prints the writhe messages then goes dormant (no spread, drain, or damage), mirroring ROM's `continue`. Test: `tests/integration/test_gl_024_level1_plague_dormant.py`. | ✅ FIXED |
| GL-025 | BUG | update.c:721-862 | `char_update` operation order: ROM processes PC worn-light decay, idle timer handling, and condition decay before affect expiry and plague/poison/incap/mortal damage. Python ran affect expiry and damage first, so a lethal poison/plague tick could move equipment into the corpse before a one-tick light burned out, skipping `--room->light`, burnout messages, and `extract_obj`. **FIX (2.11.57):** moved the PC light/timer/condition block before `tick_spell_effects()` and `_char_update_tick_effects()` while preserving affect ticks for connected PCs and immortals. Test: `tests/test_game_loop.py::test_char_update_decays_light_before_lethal_poison_tick`. | ✅ FIXED |
| GL-026 | BUG (RNG parity) | update.c:765-768 | Affect-tick level-fade RNG-consumption order. ROM `if (number_range(0,4) == 0 && paf->level > 0) paf->level--;` — C `&&` is left-to-right short-circuit and `number_range` advances MM state as a side effect, so the roll is consumed **unconditionally for every `duration>0` affect**, regardless of level; `level>0` is only tested afterwards. Python `mud/affects/engine.py:tick_spell_effects` had the operands **swapped** (`if level > 0 and number_range(0,4) == 0`), skipping the roll whenever `level == 0` — and level reaches 0 naturally via the fade mechanic on long-lived affects. Each skipped roll desynced the global RNG stream for every downstream consumer in the same tick (the immediately-following plague/poison `damage()` in `_char_update_tick_effects`) and beyond. **FIX (2.12.6):** reorder to roll first (`fades = number_range(0,4) == 0; if fades and level > 0: …`), mirroring ROM's left-operand-first evaluation. Narrow contract locked: K affects with `duration>0` consume exactly K rolls in list order, independent of level. Test: `tests/integration/test_gl026_affect_tick_rng_consumption.py` (4: level-0 + multi red-first, level>0 + permanent controls). | ✅ FIXED |
| GL-028 | BUG (crash / tick-abort) | update.c:762-786 | **An expiring spell effect on a mob crashed the whole game tick.** The dict-only fallback of `tick_spell_effects` (`mud/affects/engine.py`) calls `character.remove_spell_effect(name)` on expiry, but **`MobInstance` had no `remove_spell_effect`** — so the moment any mob's spell effect expired, `tick_spell_effects` raised `AttributeError`. Reachable via the normal cast path: ~40 spell handlers call `target.apply_spell_effect(effect)`, and for a mob that resolves to `MobInstance.apply_spell_effect` (writes `spell_effects`, no `affected` mirror) → the mob ticks through the fallback. **Severity confirmed empirically on the real `char_update` path** (`tests/integration/test_gl028_mob_spell_effect_tick.py`): neither the per-character loop body nor the `char_update()` call in `game_tick` is wrapped in try/except, so the exception **propagates out of the entire tick** — every character after the mob in `character_registry` is skipped that tick, along with `obj_update`/`pump_idle`/`aggressive_update`. **FIX (2.12.7):** added `MobInstance.remove_spell_effect` (`mud/spawning/templates.py`), symmetric to `MobInstance.apply_spell_effect` — unwinds exactly hitroll/damroll/affect_flag (the mob model never applies ac/saving/stat/sex mods). Test: `tests/integration/test_gl028_mob_spell_effect_tick.py` (real cast → tick-to-expiry, no exception escapes, effect removed). Surfaced 2026-05-31 while scoping GL-027. | ✅ FIXED |
| GL-027 | BUG (RNG parity + timing) | update.c:762-768 | The **dict-only fallback** of `tick_spell_effects` (`mud/affects/engine.py`) is a divergent re-implementation of ROM's affect loop, reached by `MobInstance` NPCs (no `affected` list — see GL-028). Two remaining divergences vs ROM / the main `affected`-list path: **(1) RNG desync** — it decrements `spell_effects` durations but calls `number_range` **zero times** and never fades level, so ROM rolls one `number_range(0,4)` per `duration>0` mob affect while Python rolls none (the GL-026 contract, total desync for mobs). **(2) off-by-one expiry** — it expires a `duration==1` affect on the *same* tick (`1→0→remove`), whereas ROM and the main path decrement-and-stay, expiring only when `duration==0` is hit on a *later* tick. Fix direction (decide before patching fallback internals — option b makes a/timing fixes throwaway): (a) make the fallback faithfully mirror ROM's per-affect loop (roll + fade + decrement-and-stay), or (b) give `MobInstance` a real `affected` list + sync so mobs collapse onto the main GL-026 path and the fallback can be retired. The GL-028 crash blocked exercising this; now unblocked. Surfaced 2026-05-31 alongside GL-026. | ⚠️ OPEN |

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
| `test_char_update_keeps_spell_effect_when_same_type_affect_remains` | GL-010 |
| `test_obj_update_suppresses_duplicate_same_type_wear_off_messages` | GL-017 |
| `test_point_pulse_emits_tick_wiznet_before_updates` | GL-021 |
| `test_gain_exp_sends_level_message_before_advance_level_gains` | GL-022 |
| `test_gain_exp_logs_level_gain_before_wiznet` | GL-022 |
| `test_xp_loss_on_death` / `test_player_kill_applies_rom_death_penalty` | GL-023 |
| `test_char_update_decays_light_before_lethal_poison_tick` | GL-025 |
| `test_gl026_affect_tick_rng_consumption.py` (4 tests) | GL-026 |
| `test_gl028_mob_spell_effect_tick.py` | GL-028 |
