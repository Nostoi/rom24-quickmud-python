# `fight.c` ROM Parity Audit

- **Status**: ⚠️ Audited 95% — combat-control regressions closed; 2026-05-23 PERS sweep opened FIGHT-004..008 on the position-change broadcast surface (`_position_change_message`); 2026-05-28 ARITH-004 reclass surfaced the WEAPON_POISON affect divergence (FIGHT-016 ✅ + FIGHT-017 ✅, both fixed); 2026-05-28 INV-025 act()-dispatch sweep surfaced the combat dam_message TRIG_ACT gap (FIGHT-018 ✅ fixed).
- **Date**: 2026-05-15 (FIGHT-001..003); 2026-05-23 (FIGHT-004..008 opened); 2026-05-28 (FIGHT-016/017 opened); 2026-05-28 (FIGHT-018 opened+closed)
- **Source**: `src/fight.c` (ROM 2.4b6)
- **Python primaries**:
  - `mud/combat/engine.py`
  - `mud/combat/safety.py`
  - `mud/commands/combat.py`
  - `mud/game_loop.py`

This audit doc was opened to track the combat-path regressions surfaced during the 2026-05-02 death/combat triage. The original two regressions are closed, and a May 15, 2026 ROM-source-first combat→XP sweep closed one more real death-branch gap. `fight.c` remains at 95% in the top-level tracker only because the file still has historical broader-sweep debt, not because a current named implementation gap is open.

## Phase 1 — Function inventory

| ROM function | ROM lines | Python counterpart | Status | Notes |
|--------------|-----------|--------------------|--------|-------|
| `multi_hit` | `src/fight.c:187-247` | `mud/combat/engine.py:312` | ✅ AUDITED | `do_kill()` now enters combat through `multi_hit()` as ROM does. |
| `damage` | `src/fight.c:688-1016` | `mud/combat/engine.py:498` | ✅ AUDITED | `apply_damage()` now re-runs `is_safe()` at entry, matching ROM `damage()`. |
| `is_safe` | `src/fight.c:1018-1124` | `mud/combat/safety.py:14` | ✅ AUDITED | Port exists and the combat damage path now consistently uses it at the ROM-critical entry point. |
| `is_safe_spell` | `src/fight.c:1126-1221` | `mud/combat/safety.py:75` | ✅ AUDITED | Present; separate from the open melee-damage gap. |
| `do_kill` | `src/fight.c:2758-2819` | `mud/commands/combat.py:94` | ✅ AUDITED | Command now routes through `multi_hit()` instead of a single `attack_round()`. |

## Phase 2 — Verification highlights

### `do_kill` — ROM `src/fight.c:2815-2817`

ROM explicitly enters combat through the full multi-attack entrypoint:

```c
WAIT_STATE (ch, 1 * PULSE_VIOLENCE);
check_killer (ch, victim);
multi_hit (ch, victim, TYPE_UNDEFINED);
```

Python `mud/commands/combat.py:123-125` currently does:

```python
skill_registry._apply_wait_state(char, get_pulse_violence())
check_killer(char, victim)
return attack_round(char, victim)
```

That drops the entire ROM `multi_hit()` chain (`src/fight.c:209-244`): first swing, haste extra swing, second-attack skill roll, third-attack skill roll, and the post-first-hit `check_assist()` path already mirrored by `mud/combat/engine.py:338-341`.

### `damage` entry gate — ROM `src/fight.c:725-733`

ROM re-checks attack safety inside `damage()` itself:

```c
if (victim != ch)
{
    if (is_safe (ch, victim))
        return FALSE;
    check_killer (ch, victim);
```

Python `mud/combat/engine.py:528-620` has no corresponding `is_safe()` call at function entry. That means once combat is underway, subsequent `attack_round()` / `multi_hit()` passes keep landing even if one combatant is moved into a safe room. This is a direct behavioral divergence from ROM and from the already-ported `mud/combat/safety.py:is_safe`.

### Special-attack call chains

ROM applies the same safety contract by routing attack variants through `damage()` (`one_hit`, skills, weapon procs, mobprog damage paths). Python likewise funnels the core physical path through `mud/combat/engine.py:488` `apply_damage(...)`, and weapon special procs call `apply_damage(...)` at `mud/combat/engine.py:1502`, `mud/combat/engine.py:1522`, `mud/combat/engine.py:1532`, and `mud/combat/engine.py:1546`. Because the entry gate is missing there, every caller inherits the bug until `apply_damage()` is fixed.

## Phase 3 — Gaps

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `FIGHT-001` | CRITICAL | `src/fight.c:2815-2817`, `src/fight.c:209-244` | `mud/commands/combat.py:123-128`, `mud/combat/engine.py:312-388` | `do_kill()` calls a single `attack_round()` instead of ROM `multi_hit(ch, victim, TYPE_UNDEFINED)`, so `kill` starts combat with one swing instead of the full ROM multi-attack sequence. | ✅ FIXED — `do_kill()` now routes through `multi_hit()` and preserves the first combat message as the command return. Regression test: `tests/integration/test_fight_c_do_kill_parity.py::test_do_kill_uses_rom_multi_hit_sequence`. Commit SHA recorded in session report for this one-gap commit. |
| `FIGHT-002` | CRITICAL | `src/fight.c:725-733`, plus all attack variants that rely on `damage()` | `mud/combat/engine.py:503-535` (`apply_damage`) and downstream callers such as `mud/combat/engine.py:1508`, `mud/combat/engine.py:1528`, `mud/combat/engine.py:1538`, `mud/combat/engine.py:1552` | The ROM `damage()` function early-exits through `is_safe(ch, victim)` before any fighting-state or HP mutation. Python never re-checks `is_safe()` inside the damage path, so combat continues after safe-room transitions. | ✅ FIXED — `apply_damage()` now re-checks `is_safe()` at entry, which also covers weapon special attacks and skill handlers because they already funnel through `apply_damage()`. Regression test: `tests/integration/test_fight_c_safe_room_damage_gate.py::test_attack_round_does_no_damage_after_fight_moves_into_safe_room`. Commit SHA recorded in session report for this one-gap commit. |
| `FIGHT-003` | CRITICAL | `src/fight.c:887-893` | `mud/combat/engine.py:_handle_death` | ROM applies the player death XP penalty inside the combat death branch after `group_gain()` and before `raw_kill()`. Python was killing the player without applying that penalty. | ✅ FIXED — `_handle_death()` now applies `gain_exp(victim, (2 * (exp_per_level * level - exp) / 3) + 50)` before `raw_kill()`, matching ROM control flow. Regression test: `tests/integration/test_character_advancement.py::test_player_kill_applies_rom_death_penalty`. |
| `FIGHT-004` | IMPORTANT | `src/fight.c:837-838` | `mud/combat/engine.py:704-709` | POS_MORTAL TO_ROOM `act("$n is mortally wounded, and will die soon, if not aided.", victim, NULL, NULL, TO_ROOM)`. Python uses `_broadcast_room(room, f"{victim.name} is mortally wounded...", exclude=victim)` — a single fixed string keyed on `victim.name`. ROM's act() macro substitutes `$n` per-listener through `PERS(victim, looker)`, so an invisible victim renders as `"someone"` to room observers without `DETECT_INVIS`. Python leaks the victim's name to every recipient regardless of `can_see`. Same PERS gap pattern as SAY-002/EMOTE-001/TELL-003/SHOUT-003/YELL-001. | ✅ FIXED (2.8.55) — `_broadcast_pos_change` helper renders `pers(victim, listener)` per-recipient. Test: `tests/integration/test_invisibility_combat.py::TestPositionChangeBroadcastPers::test_fight_004_pos_mortal_broadcast_uses_pers_for_invisible_victim`. |
| `FIGHT-005` | IMPORTANT | `src/fight.c:845-846` | `mud/combat/engine.py:712-717` | POS_INCAP TO_ROOM `act("$n is incapacitated and will slowly die, if not aided.", victim, NULL, NULL, TO_ROOM)`. Same PERS gap as FIGHT-004 — `victim.name` baked into a fixed broadcast string instead of per-listener PERS render. | ✅ FIXED (2.8.56) — INCAP branch now uses `_broadcast_pos_change`. Test: `tests/integration/test_invisibility_combat.py::TestPositionChangeBroadcastPers::test_fight_005_pos_incap_broadcast_uses_pers_for_invisible_victim`. |
| `FIGHT-006` | IMPORTANT | `src/fight.c:853-854` | `mud/combat/engine.py:720-725` | POS_STUNNED TO_ROOM `act("$n is stunned, but will probably recover.", victim, NULL, NULL, TO_ROOM)`. Same PERS gap as FIGHT-004. | ✅ FIXED (2.8.57) — STUNNED branch now uses `_broadcast_pos_change`. Test: `tests/integration/test_invisibility_combat.py::TestPositionChangeBroadcastPers::test_fight_006_pos_stunned_broadcast_uses_pers_for_invisible_victim`. |
| `FIGHT-007` | CRITICAL | `src/fight.c:860` | `mud/combat/engine.py:729` | POS_DEAD TO_ROOM `act("{R$n is DEAD!!{x", victim, 0, 0, TO_ROOM)`. Three divergences: (a) same PERS gap as FIGHT-004 (`victim.name` baked into fixed broadcast); (b) missing `{R...{x` red colour wrapping; (c) wording typo — Python emits `"is DEAD!!!"` (3 exclamation marks) where ROM is `"is DEAD!!"` (2). | ✅ FIXED (2.8.58) — DEAD branch uses `_broadcast_pos_change` with `{{R{name} is DEAD!!{{x` template. Legacy `tests/test_combat.py` assertion updated to ROM-exact form. Test: `tests/integration/test_invisibility_combat.py::TestPositionChangeBroadcastPers::test_fight_007_pos_dead_broadcast_uses_pers_and_red_colour_and_two_bangs`. |
| `FIGHT-008` | IMPORTANT | `src/fight.c:861` | `mud/combat/engine.py:730` | POS_DEAD TO_CHAR self-message: ROM `send_to_char("{RYou have been KILLED!!{x\n\r\n\r", victim)`. Python returns `"You have been KILLED!!"` from `_position_change_message`. Two divergences: (a) missing `{R...{x` red colour wrapping; (b) missing the trailing blank-line newline ROM appends after the death notice. | ✅ FIXED (2.8.59) — return now `"{RYou have been KILLED!!{x\n"`. Python's `mud/net/protocol.py:send_to_char` auto-appends one `\r\n`, so the embedded `\n` plus the auto-append produces the same visual blank-line spacing ROM gets from its two `\n\r` pairs. Test: `tests/integration/test_invisibility_combat.py::TestPositionChangeBroadcastPers::test_fight_008_pos_dead_self_message_wraps_red_and_appends_blank_line`. |
| `FIGHT-009` | IMPORTANT | `src/fight.c:614-615` | `mud/combat/engine.py:1496-1500` | WEAPON_POISON TO_ROOM `act("$n is poisoned by the venom on $p.", victim, wield, NULL, TO_ROOM)`. Python emits `_broadcast_room(room, f"{victim.name} is poisoned by the venom on {weapon_name}.", exclude=victim)` — single fixed string keyed on `victim.name`. Same PERS gap as FIGHT-004 — invisible victim leaks identity to room observers without `DETECT_INVIS`. Wording matches ROM (`$n is poisoned by the venom on $p`). | ✅ FIXED (2.8.61) — poison broadcast routed through `_broadcast_pos_change` (extended to accept `**extra` for `$p` weapon name). Test: `tests/integration/test_weapon_proc_pers.py::TestWeaponProcBroadcastPers::test_fight_009_poison_broadcast_uses_pers_for_invisible_victim`. |
| `FIGHT-010` | IMPORTANT | `src/fight.c:643` | `mud/combat/engine.py:1510` | WEAPON_VAMPIRIC TO_ROOM `act("$p draws life from $n.", victim, wield, NULL, TO_ROOM)`. Python: `_broadcast_room(room, f"{weapon_name} draws life from {victim.name}.", exclude=victim)`. PERS gap on `$n` (victim). Wording matches ROM. | ✅ FIXED (2.8.62) — vampiric broadcast routed through `_broadcast_pos_change`. Test: `tests/integration/test_weapon_proc_pers.py::TestWeaponProcBroadcastPers::test_fight_010_vampiric_broadcast_uses_pers_for_invisible_victim`. |
| `FIGHT-011` | IMPORTANT | `src/fight.c:654` | `mud/combat/engine.py:1531` | WEAPON_FLAMING TO_ROOM `act("$n is burned by $p.", victim, wield, NULL, TO_ROOM)`. Python: `_broadcast_room(room, f"{victim.name} is burned by {weapon_name}.", exclude=victim)`. PERS gap on `$n`. Wording matches ROM. | ✅ FIXED (2.8.63) — flaming broadcast routed through `_broadcast_pos_change`. Test: `tests/integration/test_weapon_proc_pers.py::TestWeaponProcBroadcastPers::test_fight_011_flaming_broadcast_uses_pers_for_invisible_victim`. |
| `FIGHT-012` | IMPORTANT | `src/fight.c:663` | `mud/combat/engine.py:1541` | WEAPON_FROST TO_ROOM `act("$p freezes $n.", victim, wield, NULL, TO_ROOM)`. Two divergences: (a) PERS gap on `$n`; (b) wording — ROM is `"$p freezes $n."` (e.g. `"the sword freezes Alice."`) but Python emits `f"{victim.name} is frozen by {weapon_name}."` (`"Alice is frozen by the sword."`). | ✅ FIXED (2.8.64) — frost broadcast routed through `_broadcast_pos_change` with ROM-true wording `"{weapon} freezes {name}."`. Test: `tests/integration/test_weapon_proc_pers.py::TestWeaponProcBroadcastPers::test_fight_012_frost_broadcast_uses_pers_and_rom_wording`. |
| `FIGHT-013` | IMPORTANT | `src/fight.c:673-674` | `mud/combat/engine.py:1551-1555` | WEAPON_SHOCKING TO_ROOM `act("$n is struck by lightning from $p.", victim, wield, NULL, TO_ROOM)`. Python: `_broadcast_room(room, f"{victim.name} is struck by lightning from {weapon_name}.", exclude=victim)`. PERS gap on `$n`. Wording matches ROM. | ✅ FIXED (2.8.65) — shocking broadcast routed through `_broadcast_pos_change`. Test: `tests/integration/test_weapon_proc_pers.py::TestWeaponProcBroadcastPers::test_fight_013_shocking_broadcast_uses_pers_for_invisible_victim`. Closes the FIGHT-009..013 weapon-proc sweep. |
| `FIGHT-014` | IMPORTANT | `src/fight.c:961-970` (AUTOSAC dispatch → `do_function(ch, &do_sacrifice, "corpse")`); broadcast text at `src/act_obj.c:1856` (`act("$n sacrifices $p to Mota.", ch, obj, NULL, TO_ROOM)`) | `mud/combat/engine.py:_auto_sacrifice` | AUTOSAC TO_ROOM broadcast pre-renders `$n` from `attacker.name` via `expand_placeholders(...)` baked into a single `_broadcast_room` string, leaking the attacker's identity to room observers even when the attacker is invisible. **Note**: Python's `_auto_sacrifice` re-implements sacrifice logic inline rather than dispatching to `do_sacrifice` like ROM does at `src/fight.c:970`; that structural divergence is tracked separately (FIGHT-015 reserved). This gap addresses only the PERS leak. | ✅ FIXED (2.8.66) — `_auto_sacrifice` broadcast routed through `_broadcast_pos_change(attacker, "{name} sacrifices {corpse} to Mota.", corpse=corpse_name)`. Orphan `SimpleNamespace` import removed as a side effect. Test: `tests/integration/test_auto_sacrifice_pers.py::test_fight_014_auto_sacrifice_broadcast_uses_pers_for_invisible_attacker`. |
| `DAMMSG-001` | CRITICAL | `src/fight.c:2222` (`act(buf1, ch, NULL, victim, TO_NOTVICT)`) | `mud/combat/messages.py:dam_message`, `mud/combat/engine.py:_broadcast_damage_messages` | `dam_message` builds `room_msg` as a pre-rendered string baked with `attacker.name`/`victim.name`, then `engine.py` ships it via `_broadcast_room` once. ROM's `act(..., TO_NOTVICT)` evaluates `PERS(ch, looker)` AND `PERS(victim, looker)` per recipient — both names render independently for each observer. Python leaks both attacker and victim identities to every room observer regardless of `can_see`. Highest-volume PERS leak in combat (fires on every melee swing / spell hit). | ✅ FIXED (2.8.67) — `dam_message` now returns `{attacker}`/`{victim}` templates; `_broadcast_damage_messages` PERS-renders per recipient via `render_for` for TO_NOTVICT iteration over `room.people`. Test: `tests/integration/test_dam_message_pers.py::TestDamMessagePers::test_dammsg_001_to_notvict_renders_attacker_and_victim_per_observer`. |
| `DAMMSG-002` | IMPORTANT | `src/fight.c:2224` (`act(buf3, ch, NULL, victim, TO_VICT)`) | `mud/combat/messages.py:dam_message`, `mud/combat/engine.py:_broadcast_damage_messages` | `dam_message`'s `victim_msg` bakes `attacker.name` for `$n` substitution. ROM's `act(..., TO_VICT)` evaluates `PERS(ch, victim)` so an invisible attacker (no `DETECT_INVIS` on victim) renders as `"someone"` — Python instead leaks the attacker's real name. | ✅ FIXED (2.8.67) — TO_VICT render path uses `render_for(template, attacker, victim, observer=victim)`. Test: `tests/integration/test_dam_message_pers.py::TestDamMessagePers::test_dammsg_002_to_vict_renders_attacker_per_victim`. |
| `DAMMSG-003` | IMPORTANT | `src/fight.c:2223` (`act(buf2, ch, NULL, victim, TO_CHAR)`) | `mud/combat/messages.py:dam_message`, `mud/combat/engine.py:_broadcast_damage_messages` | `dam_message`'s `attacker_msg` bakes `victim.name` for `$N` substitution. ROM's `act(..., TO_CHAR)` evaluates `PERS(victim, ch)` — an invisible victim without `can_see` from attacker (rare but real, e.g. blind attacker) should render as `"someone"`. Python leaks the victim's name. | ✅ FIXED (2.8.67) — TO_CHAR render path uses `render_for(template, attacker, victim, observer=attacker)`; `damage()` return value also rendered for the attacker's view so test/scripted callers see PERS-correct strings. Test: `tests/integration/test_dam_message_pers.py::TestDamMessagePers::test_dammsg_003_to_char_renders_victim_per_attacker`. |
| `FIGHT-016` | IMPORTANT | `src/fight.c:616-624` | `mud/combat/engine.py:1561-1579` (`process_weapon_special_attacks`, WEAPON_POISON branch) | On a WEAPON_POISON hit where the victim fails the save, ROM builds and `affect_join`s a structured poison affect: `af.level = level*3/4`, `af.duration = level/2`, `af.location = APPLY_STR`, `af.modifier = -1`, `af.bitvector = AFF_POISON` (`level = wield->level` for a permanently-poisoned weapon). Python instead calls only `victim.add_affect(AffectFlag.POISON)` — a bare, untimed flag with **no duration** (never wears off), **no STR penalty**, and no `affect_join` merge semantics. So weapon poison in Python is a permanent flag with no stat effect, where ROM is a timed `level/2`-tick STR-reducing affect. Surfaced 2026-05-28 during ARITH-004 reclassification. Reference implementation: `spell_poison` at `mud/skills/handlers.py:6438-6447` already builds a `SpellEffect` + `victim.apply_spell_effect()` (the Python `affect_join` port at `mud/models/character.py:673`); the weapon proc differs only in params (STR -1 not -2, `level*3/4` level, `level/2` duration). | ✅ FIXED (2.9.88) — WEAPON_POISON branch now builds `SpellEffect(name="poison", level=c_div(level*3,4), duration=c_div(level,2), stat_modifiers={Stat.STR:-1}, affect_flag=AffectFlag.POISON, wear_off_message="You feel less sick.")` and calls `victim.apply_spell_effect(...)` (the `affect_join` port), replacing the bare `add_affect(AffectFlag.POISON)`. Test: `tests/integration/test_weapon_poison_affect.py::test_fight_016_weapon_poison_applies_timed_str_reducing_affect` (+ successful-save no-op case). |
| `FIGHT-017` | MINOR | `src/fight.c:605-608, 627-636` | `mud/combat/engine.py:1561` (`process_weapon_special_attacks`, WEAPON_POISON branch) | ROM derives the poison `level` from a **temporary** envenom affect if present — `affect_find(wield->affected, gsn_poison)` → use `poison->level`, else `wield->level` — and after applying the venom, **weakens a temporary poison per hit**: `poison->level = UMAX(0, poison->level - 2)`, `poison->duration = UMAX(0, poison->duration - 1)`, emitting `"The poison on $p has worn off."` to the wielder when either hits 0. Python's weapon-proc branch ignores the weapon's `affected` list entirely (always uses the weapon level) and never weakens an envenom (the `spell_poison`-object path at `handlers.py:6388` adds a `WeaponFlag.POISON` affect with `spell_name == "poison"` that never decays via combat). Depends on FIGHT-016 (shares the `level` variable). Filed 2026-05-28. | ✅ FIXED (2.9.89) — WEAPON_POISON branch now scans `wield.affected` for the temporary envenom affect (`spell_name == "poison"`, set by `spell_poison` on an object at `handlers.py:6397`); when present, `level = poison_af.level` (raw, no floor) instead of `wield.level`, and after the save block the envenom is weakened per hit (`level = max(0, level-2)`, `duration = max(0, duration-1)`) with `"The poison on {weapon} has worn off."` pushed to the **attacker** (TO_CHAR) when either hits 0. Permanent WEAPON_POISON weapons (no envenom affect) are unaffected. Test: `tests/integration/test_weapon_poison_affect.py::test_fight_017_*` (4 cases: level source, weakening-on-save, attacker-not-victim message, duration-zero trigger). |

| `FIGHT-018` | IMPORTANT | `src/fight.c:2215-2226` (`dam_message`) | `mud/combat/engine.py:_broadcast_damage_messages` | ROM `dam_message` emits the combat hit line TO_ROOM (self-inflicted, `ch == victim`) or TO_NOTVICT (normal) via `act()` with no `MOBtrigger = FALSE` wrap. Per `src/comm.c:2384`, every NPC recipient in the room then fires `mp_act_trigger(buf, to, ch, ..., TRIG_ACT)`, so mob ACT-progs respond to combat happening around them. Python's `_broadcast_damage_messages` PERS-renders the per-recipient combat text (DAMMSG-001/002/003) but never dispatched TRIG_ACT, so every combat-watching mobprog silently no-opped — same class of gap as the INV-025 act()-dispatch sweep (do_emote / position-transition / give / wear / get / drop / sacrifice). | ✅ FIXED (2.9.90) — after the TO_NOTVICT room loop, `_broadcast_damage_messages` now renders the room template canonically (real attacker/victim names, matching the `_broadcast_pos_change` pattern) and calls `mp_act_trigger_room(canonical, room, attacker, exclude=victim)`. `exclude=victim` reproduces TO_NOTVICT's actor+victim exclusion; the self-inflicted case (`attacker is victim`) collapses to TO_ROOM's single-actor exclusion. Test: `tests/integration/test_fight_018_dam_message_act_trigger_dispatch.py` (fires on a listening third-party NPC; excludes attacker and victim). |

## Phase 4 — Closures

1. `FIGHT-001` — ✅ closed with `tests/integration/test_fight_c_do_kill_parity.py`.
2. `FIGHT-002` — ✅ closed with `tests/integration/test_fight_c_safe_room_damage_gate.py`.
3. `FIGHT-003` — ✅ closed with `tests/integration/test_character_advancement.py::test_player_kill_applies_rom_death_penalty`.

## Phase 5 — Completion summary

`fight.c`'s combat-control regressions (FIGHT-001/002/003) are closed.
The 2026-05-23 PERS sweep opened five new gaps on the
position-change broadcast surface (`_position_change_message`):
FIGHT-004..008. All five are the same pattern the channel-message
arc just normalized (`pers()` helper from `mud/world/vision.py`),
plus colour-wrap and wording corrections on the POS_DEAD case.

**Out of scope for this sub-sweep, deferred to a follow-up cluster
(reserve FIGHT-009..013 for them):** weapon-proc broadcasts at
`mud/combat/engine.py:1496` (poison), `:1510` (vampiric), `:1531`
(flaming), `:1541` (frost), `:1551` (shocking) all have analogous
PERS gaps and some have wording divergences vs ROM
`src/fight.c:614-675` (e.g. ROM `"$p freezes $n."` rendered by
Python as `"X is frozen by Y."`). Same fix pattern, different
session.

Recent verification locked by
`tests/integration/test_fight_c_do_kill_parity.py`,
`tests/integration/test_fight_c_safe_room_damage_gate.py`, and
`tests/integration/test_character_advancement.py::test_player_kill_applies_rom_death_penalty`.
