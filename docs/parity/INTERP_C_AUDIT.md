# `interp.c` ROM Parity Audit

**ROM source**: `src/interp.c` (849 lines), `src/interp.h` (314 lines)
**Python counterparts**: `mud/commands/dispatcher.py`, `mud/commands/socials.py`,
`mud/commands/info.py` (`do_commands`/`do_wizhelp`), per-command modules under
`mud/commands/*.py`.
**Created**: 2026-04-27
**Status**: 🔄 Phase 3 complete (gaps identified). Phase 4 (closure) pending.
**Auditor**: rom-parity-audit skill

---

## Why this file matters

`interp.c` is ROM's command dispatcher. Every `act_*.c` audit already closed
(`act_obj.c`, `act_info.c`, `act_comm.c`, `act_move.c`, `act_enter.c`,
`mob_cmds.c`, `mob_prog.c`) assumes commands route correctly: position gates,
trust gates, social fallback, snoop forwarding, command-name disambiguation.
A gap here can silently invalidate a downstream audit's "✅ COMPLETE" claim.

---

## ROM constants (verified)

From `src/merc.h:147-167`:

| ROM macro | Numeric value |
|-----------|---------------|
| `MAX_LEVEL` | 60 |
| `LEVEL_HERO` | 51 |
| `LEVEL_IMMORTAL` (`IM`) | 52 |
| `ML` (implementor) | 60 |
| `L1` (creator) | 59 |
| `L2` (supreme) | 58 |
| `L3` (deity) | 57 |
| `L4` (god) | 56 |
| `L5` (immortal) | 55 |
| `L6` (demigod) | 54 |
| `L7` (angel) | 53 |
| `L8` (avatar) | 52 |

From `mud/models/constants.py:271-273`: same `MAX_LEVEL`, `LEVEL_HERO`,
`LEVEL_IMMORTAL`. The Python tier macros (`L1`..`L8`, `ML`) are **not**
exported, so the dispatcher hard-codes `LEVEL_IMMORTAL`/`LEVEL_HERO`/
`MAX_LEVEL - N`, which produces a systematic trust drift documented below
(see INTERP-001).

---

## Phase 1 — Function inventory

| ROM function | ROM lines | Python counterpart | Status |
|--------------|-----------|--------------------|--------|
| `cmd_table[]` (static dispatch table) | 63–381 | `COMMANDS` in `dispatcher.py:211-636` | ⚠️ Partial — many trust/position/dispatch divergences (see Phase 3) |
| `interpret(ch, argument)` | 390–559 | `process_command(char, input_str)` in `dispatcher.py:755-882` | ⚠️ Partial — missing snoop, wiznet log, empty-input semantics |
| `do_function(ch, do_fun, argument)` | 562–574 | N/A — Python passes the string directly; no string ownership concern | N/A |
| `check_social(ch, command, argument)` | 576–689 | `perform_social(char, name, arg)` in `socials.py:7-34` | ❌ Missing — stub lacks COMM_NOEMOTE, position gates, snore exception, NPC slap auto-react |
| `is_number(arg)` | 696–712 | `mud.utils.argparse.is_number` (separate audit; not exercised by dispatcher) | N/A — utility |
| `number_argument(argument, arg)` | 719–738 | `mud.utils.argparse.number_argument` | N/A — utility |
| `mult_argument(argument, arg)` | 743–762 | `mud.utils.argparse.mult_argument` | N/A — utility |
| `one_argument(argument, arg_first)` | 770–798 | `_split_command_and_args` in `dispatcher.py:679-720` (head only) + per-command `one_argument` helpers | ⚠️ Partial — uses `shlex.split` semantics for the head; differs on backslash handling |
| `do_commands(ch, argument)` | 803–825 | `do_commands` in `mud/commands/info.py` | ⚠️ Verify column format and `show` filter (Phase 4 follow-up) |
| `do_wizhelp(ch, argument)` | 827–849 | `do_wizhelp` in `mud/commands/info.py` | ⚠️ Verify column format and `level >= LEVEL_HERO` filter |

P0/P1 functions for Phase 2: `interpret`, `check_social`, `one_argument`-equivalent, the `cmd_table` data.

---

## Phase 2 — Line-by-line verification

### `interpret()` vs `process_command()`

| ROM step (interp.c:line) | Python (dispatcher.py:line) | Verdict |
|--------------------------|------------------------------|---------|
| Strip leading spaces; return on empty (401–404) | `not input_str.strip(): return "What?"` (769–770) | ❌ ROM returns silently with no message; Python returns "What?". See INTERP-007. |
| `REMOVE_BIT(ch->affected_by, AFF_HIDE)` (409) | `remover(AffectFlag.HIDE)` (772–781) | ✅ Equivalent. |
| `PLR_FREEZE` check → "You're totally frozen!" (414–418) | Lines 783–789 with `PlayerFlag.FREEZE` | ✅ Match. |
| Punctuation parsing: single non-alphanumeric char becomes the command (426–433) | `not first.isalnum(): return first, stripped[1:].lstrip()` (704–705) | ✅ Match for the head, but see INTERP-008 — Python's `COMMAND_INDEX` lacks `"."`, `","`, `"/"` aliases that ROM table provides. |
| Alphanumeric path: `one_argument` (lowercase head, lowercase first arg) (436) | `shlex.split(stripped)` (707–713), then `cmd_name.lower()` (815) | ⚠️ Backslash escapes consumed by shlex; ROM passes them through. INTERP-015. |
| Linear scan of `cmd_table` for first prefix match where `level <= trust` (442–453) | Exact `COMMAND_INDEX` lookup, then `for cmd in COMMANDS: cmd.name.startswith(name)` (662–676) | ⚠️ Python's COMMANDS list ordering controls ambiguous-prefix resolution and may diverge from ROM's `cmd_table` order — see INTERP-017. |
| `LOG_NEVER → strcpy(logline, "")` (460–461) | `if command.log_level is LogLevel.NEVER and not log_all_enabled: log_allowed = False` (829–830) | ✅ Effectively equivalent. |
| Wiznet broadcast `WIZ_SECURE` for logged commands (468–489) | Only `log_admin_command(...)` is called (838–847); no `WIZ_SECURE` broadcast | ❌ INTERP-003. |
| Snoop forward to `ch->desc->snoop_by` (491–496) | No equivalent | ❌ INTERP-002. |
| Not-found → `check_social` → IMC → "Huh?" (498–510) | `perform_social` → `try_imc_command` → "Huh?" (848–857) | ✅ Order matches; behavior differs because `perform_social` is a stub (see INTERP-018/019/020). |
| Position gate with full ROM messages (515–550) | Identical messages in `dispatcher.py:861-878` | ✅ Match. |
| Dispatch via `(*cmd_table[cmd].do_fun)(ch, argument)` (555) | `command.func(char, command_args)` (882) | ✅ Match. |
| `tail_chain()` at end (557) | None | ➖ INTERP-016, MINOR — no-op in stock ROM. |

### `check_social()` vs `perform_social()`

| ROM step (interp.c:line) | Python (socials.py:line) | Verdict |
|--------------------------|---------------------------|---------|
| Find by `str_prefix(command, social_table[cmd].name)` (584–592) | `social_registry.get(name.lower())` (8) | ⚠️ Python uses exact lookup; ROM allows prefix match. INTERP-021. |
| `COMM_NOEMOTE` → "You are anti-social!" (597–601) | None | ❌ INTERP-020. |
| Position checks: DEAD/INCAP/MORTAL/STUNNED → cannot social (605–616) | None | ❌ INTERP-018. |
| `POS_SLEEPING` blocks all socials except `snore` (618–627) | None | ❌ INTERP-019. |
| No-arg → others_no_arg + char_no_arg (632–636) | Same broadcast (32–33) | ✅ Match. |
| `get_char_room` returns NULL → "They aren't here.\n\r" (637–640) | `social.not_found` placeholder (28–30) | ⚠️ ROM has no `not_found` field — message is literal "They aren't here." See INTERP-022. |
| `victim == ch` → others_auto + char_auto (641–645) | Lines 24–26 | ✅ Match. |
| Else → others_found + char_found + vict_found (646–650) | Lines 20–23 | ✅ Match. |
| NPC slap auto-react: `number_bits(4)` 0–8 echo, 9–12 slap (652–685) | None | ❌ INTERP-023 (CRITICAL — must use `rng_mm.number_bits(4)`). |

---

## Phase 3 — Gap table

Severity legend: **CRITICAL** = visible behavior diverges (wrong gating,
wrong damage, wrong message); **IMPORTANT** = wrong broadcast, wrong wording,
or feature missing; **MINOR** = cosmetic/no-op.

| ID | Severity | ROM ref | Python ref | Description | Status |
|----|----------|---------|------------|-------------|--------|
| INTERP-001 | **CRITICAL** | `src/interp.c:289-374`, `src/merc.h:147-167` | `mud/commands/dispatcher.py:419-636` | Trust-level table mismatch: ~30 immortal commands use `LEVEL_IMMORTAL`/`LEVEL_HERO` instead of ROM's tiered `L1..L8`/`ML`. E.g. ROM `reboot`=L1 (59), Python uses `MAX_LEVEL-2`=58; ROM `ban`=L2 (58), Python uses `LEVEL_HERO`=51 (7 levels too low); ROM `trust`=`ML` (60), Python uses `MAX_LEVEL-3`=57; ROM `protect`=L1, Python uses `LEVEL_IMMORTAL`=52. Full mapping in INTERP-001 detail table below. | ✅ FIXED 2026-04-27 — all 43 drift rows corrected; goto/poofin/poofout were already at correct trust (L8=52=LEVEL_IMMORTAL). Test: `tests/integration/test_interp_trust.py::test_interp_001_command_trust_matches_rom` (50 parameters). |
| INTERP-002 | IMPORTANT | `src/interp.c:491-496` | `mud/commands/dispatcher.py:825-847` | Snoop forwarding missing — ROM emits `"% <logline>\n\r"` to `ch->desc->snoop_by`; Python's dispatcher has no snoop hook at all. | ✅ FIXED — `process_command` now appends `% <logline>` to `desc.snoop_by.character.messages` (test `tests/integration/test_interp_dispatcher.py::test_interp_002_snoop_forwards_logline_to_snooper`) |
| INTERP-003 | IMPORTANT | `src/interp.c:468-489` | `mud/commands/dispatcher.py:838-847` | Wiznet `WIZ_SECURE` broadcast missing — ROM mirrors logged commands to wiznet (with `$` and `{` doubled to defuse format strings). Python only writes the admin log file. | ✅ VERIFIED — `log_admin_command` (`mud/admin_logging/admin.py:107-114`) calls `wiznet(..., WIZ_SECURE, ...)` with `_duplicate_wiznet_chars` smashing `$`/`{`. Audit description was stale. Test `tests/integration/test_interp_dispatcher.py::test_interp_003_logged_command_mirrors_to_wiznet_secure`. |
| INTERP-004 | IMPORTANT | `src/interp.c:200` | `mud/commands/dispatcher.py:279` | `shout` requires level 3 in ROM (`POS_RESTING, 3`); Python sets no `min_trust` (defaults to 0). | 🔄 OPEN |
| INTERP-005 | IMPORTANT | `src/interp.c:247` | `mud/commands/dispatcher.py:312` | `murder` requires level 5 in ROM (`POS_FIGHTING, 5`); Python sets no `min_trust`. | 🔄 OPEN |
| INTERP-006 | IMPORTANT | `src/interp.c:93` | `mud/commands/dispatcher.py:290` | `music` minimum position is `POS_SLEEPING` in ROM; Python sets `Position.RESTING`. | 🔄 OPEN |
| INTERP-007 | IMPORTANT | `src/interp.c:401-404` | `mud/commands/dispatcher.py:769-770` | Empty-input behavior: ROM returns silently; Python returns the literal string `"What?"`. | ✅ FIXED — empty input now returns `""` (test `tests/integration/test_interp_dispatcher.py::test_interp_007_empty_input_returns_silently`) |
| INTERP-008 | IMPORTANT | `src/interp.c:184, 186, 272` | `mud/commands/dispatcher.py:284, 281, 348` | Punctuation aliases missing from `COMMAND_INDEX`: `"."` → `do_gossip`, `","` → `do_emote`, `"/"` → `do_recall`. (`"'"`, `";"`, `":"` are present.) | ✅ FIXED — aliases added to gossip/emote/recall (test `tests/integration/test_interp_dispatcher.py::test_interp_008_punctuation_aliases_route_to_rom_handlers`) |
| INTERP-009 | IMPORTANT | `src/interp.c:88` | `mud/commands/dispatcher.py:300` | `"hit"` should dispatch to `do_kill` (single canonical combat handler); Python routed to a separate `do_hit` stub. | ✅ FIXED — added `"hit"` to `do_kill` aliases; deleted `do_hit` stub from `player_info.py`. Test: `tests/integration/test_interp_dispatcher.py::test_interp_009_hit_routes_to_do_kill`. |
| INTERP-010 | IMPORTANT | `src/interp.c:226` | `mud/commands/dispatcher.py:269` | `"take"` should dispatch to `do_get`; Python routed to `do_take`. | ✅ FIXED — added `"take"` to `do_get` aliases; deleted `do_take` stub. Test: `tests/integration/test_interp_dispatcher.py::test_interp_010_take_routes_to_do_get`. |
| INTERP-011 | IMPORTANT | `src/interp.c:228-229` | `mud/commands/dispatcher.py:402` | `"junk"` and `"tap"` should dispatch to `do_sacrifice`; Python used separate `do_junk`/`do_tap` stubs. | ✅ FIXED — added `"junk"`, `"tap"` to `do_sacrifice` aliases; deleted both stubs from `remaining_rom.py`. Test: `test_interp_011_junk_tap_route_to_do_sacrifice` (2 cases). |
| INTERP-012 | IMPORTANT | `src/interp.c:263` | `mud/commands/dispatcher.py:260` | `"go"` should dispatch to `do_enter`; Python used `do_go`. | ✅ FIXED — added `"go"` to `do_enter` aliases; deleted `do_go` stub. Test: `test_interp_012_go_routes_to_do_enter`. |
| INTERP-013 | IMPORTANT | `src/interp.c:103, 215` | `mud/commands/dispatcher.py:334-335` | `"wield"` and `"hold"` should dispatch to `do_wear` (the wear command branches on item slot internally); Python has separate `do_wield`/`do_hold` functions. | ⚠️ DEFERRED — Python `do_wear` (`mud/commands/equipment.py`) is missing ROM behavior that `do_wield`/`do_hold` currently encapsulate: STR wield-weight check (`src/act_obj.c:1616-1668`, `mud/commands/equipment.py:329-340`), weapon-skill flavor message (`mud/commands/equipment.py:379-382`), two-hand vs shield conflict (`mud/commands/equipment.py:353-358`), and HOLD auto-unequip (`src/act_obj.c:1670-1678` vs Python `mud/commands/equipment.py:451-454` which rejects). Collapsing now would regress behavior. Track follow-ups in `ACT_OBJ_C_AUDIT.md` (WEAR-001/WEAR-002) — port the missing pieces into `do_wear`, then revisit this routing gap. |
| INTERP-014 | IMPORTANT | `src/interp.c:356` | `mud/commands/dispatcher.py:294` | `":"` should dispatch to `do_immtalk` (immortal channel); Python routed to `do_colon` stub that lost ROM's empty-arg NOWIZ toggle. | ✅ FIXED — added `":"` to `do_immtalk` aliases; deleted `do_colon` stub from `typo_guards.py`. Test: `test_interp_014_colon_routes_to_do_immtalk`. |
| INTERP-015 | MINOR | `src/interp.c:770-798` | `mud/commands/dispatcher.py:707-720` | `_split_command_and_args` uses `shlex.split` for the alphanumeric branch, which interprets `\` as an escape and consumes unbalanced quotes differently from ROM's byte-for-byte `one_argument`. ROM lowercases each character into the output; shlex preserves case (later coerced via `cmd_name.lower()`, so command resolution is unaffected). The user-visible difference is rare command strings that contain `\`. | 🔄 OPEN |
| INTERP-016 | MINOR | `src/interp.c:557` | (none) | `tail_chain()` is invoked after command dispatch in ROM. It's a no-op in stock ROM 2.4b6 but exists as an extension hook. Document and skip unless an extension hooks it. | 🔄 OPEN (defer) |
| INTERP-017 | **CRITICAL** | `src/interp.c:63-381, 442-453` | `mud/commands/dispatcher.py:211-636, 670-676` | Prefix-match table-order divergence: ROM's `cmd_table` is hand-ordered so common 1- and 2-letter abbreviations resolve correctly (`cmd_table` comment at line 76: "Placed here so one and two letter abbreviations work"). Python's `COMMANDS` list is grouped by feature, not by abbreviation priority. Any single-letter prefix that hits multiple commands resolves by Python list order, not ROM table order. Empirical sweep needed: enumerate every 1- and 2-letter prefix in both tables and diff the resolved command. | 🔄 OPEN |
| INTERP-018 | **CRITICAL** | `src/interp.c:603-616` | `mud/commands/socials.py:7-34` | `perform_social` does not enforce position gates (DEAD/INCAP/MORTAL/STUNNED). A dead or stunned character can currently emit any social. | ✅ FIXED 2026-04-27 — added DEAD/MORTAL/INCAP/STUNNED early-return with ROM messages. Test: `tests/integration/test_socials.py::TestSocialPositionGates`. |
| INTERP-019 | IMPORTANT | `src/interp.c:618-627` | `mud/commands/socials.py` | `POS_SLEEPING` should block all socials except `snore` ("In your dreams, or what?"). Python's `perform_social` has no sleeping check at all. | ✅ FIXED 2026-04-27 — added SLEEPING gate with snore exception. Test: `tests/integration/test_socials.py::TestSocialPositionGates::test_sleeping_character_cannot_social_except_snore` (+ snore guard). |
| INTERP-020 | IMPORTANT | `src/interp.c:597-601` | `mud/commands/socials.py` | `COMM_NOEMOTE` punishment: ROM blocks all socials with "You are anti-social!" when `IS_SET(ch->comm, COMM_NOEMOTE)`. Python omits this check entirely. | ✅ FIXED 2026-04-27 — added NOEMOTE early-return with NPC bypass. Tests: `tests/integration/test_socials.py::TestSocialPositionGates::test_noemote_player_blocked_with_anti_social_message` + `test_noemote_does_not_apply_to_npcs`. |
| INTERP-021 | IMPORTANT | `src/interp.c:584-592` | `mud/commands/socials.py:8` | Social lookup: ROM uses `str_prefix` (so `gigg` matches `giggle`); Python uses exact dict lookup via `social_registry.get(name.lower())`. | ✅ FIXED 2026-04-27 — `find_social()` in `mud/models/social.py` does load-order prefix match; dispatcher + `perform_social` both use it. Tests: `tests/integration/test_socials.py::TestSocialPrefixLookup` (3 cases). |
| INTERP-022 | MINOR | `src/interp.c:637-640` | `mud/commands/socials.py:30` | "Target not found" message: ROM hard-codes `"They aren't here.\n\r"`; Python emits a fabricated `social.not_found` field that does not exist in ROM's social table. Users may see whatever placeholder lives there. | ✅ FIXED 2026-04-27 — `perform_social` emits literal `"They aren't here."` Test: `tests/integration/test_socials.py::TestSocialNotFoundMessage::test_not_found_emits_rom_literal`. |
| INTERP-023 | **CRITICAL** | `src/interp.c:652-685` | `mud/commands/socials.py` | NPC slap auto-react missing: when a player socials at an awake non-charmed NPC with no descriptor, ROM rolls `number_bits(4)` (0–15) — values 0–8 echo the social back at the player, values 9–12 emit `"$n slaps $N."` instead. Python performs no auto-react. **Must use `mud.utils.rng_mm.number_bits(4)` per ROM Parity Rules** — `random.*` is forbidden. | ✅ FIXED 2026-04-27 — added auto-react with `rng_mm.number_bits(4)`, all four gate conditions (player actor, NPC victim, not charmed, awake, no descriptor), and 0..8/9..12/13..15 branches. Tests: `tests/integration/test_socials.py::TestSocialNpcAutoReact` (6 cases). |
| INTERP-024 | IMPORTANT | `src/interp.c:803-825, 827-849` | `mud/commands/info.py:42-54` (`_chunk_commands`) | Verify both commands iterate dispatcher table in declaration order, filter by `show` and effective trust, format as 12-char left-justified columns 6 per line, and split mortal vs immortal at `LEVEL_HERO`. | ✅ FIXED — verified iteration order (PASS), `show` filter (PASS), trust split via `min_level=LEVEL_HERO` for `do_wizhelp` and `max_level=LEVEL_HERO-1` for `do_commands` (PASS). Removed `.rstrip()` calls from `_chunk_commands` so columns preserve full 12-char padding (was compressing the trailing column on each row). Test: `tests/integration/test_interp_dispatcher.py::test_interp_024_do_commands_preserves_12char_column_padding`. |

### INTERP-001 detail — full trust drift table

This is the bulk of the work. Each row is a separate gap closure (one
ROM command = one stable trust level = one Python edit). Closing them
is mechanical but cannot be batched per the rom-gap-closer rules
(one gap, one test, one commit).

| ROM command | ROM trust (interp.c:line) | Python trust (dispatcher.py:line) | Drift |
|-------------|--------------------------|------------------------------------|-------|
| `advance` | `ML` = 60 (289) | `MAX_LEVEL - 3` = 57 (433) | −3 |
| `copyover` | `ML` = 60 (290) | `MAX_LEVEL - 2` = 58 (472) | −2 |
| `dump` | `ML` = 60 (291) | `MAX_LEVEL - 2` = 58 (475) | −2 |
| `trust` | `ML` = 60 (292) | `MAX_LEVEL - 3` = 57 (434) | −3 |
| `violate` | `ML` = 60 (293) | `LEVEL_IMMORTAL` = 52 (474) | −8 |
| `qmconfig` | `ML` = 60 (321) | `LEVEL_HERO` = 51 (583) | −9 |
| `allow` | `L2` = 58 (295) | `LEVEL_HERO` = 51 (575) | −7 |
| `ban` | `L2` = 58 (296) | `LEVEL_HERO` = 51 (566) | −7 |
| `set` | `L2` = 58 (305) | `LEVEL_IMMORTAL` = 52 (477) | −6 |
| `wizlock` | `L2` = 58 (309) | `LEVEL_HERO` = 51 (619) | −7 |
| `deny` | `L1` = 59 (297) | `LEVEL_HERO` = 51 (574) | −8 |
| `permban` | `L1` = 59 (301) | `LEVEL_HERO` = 51 (568) | −8 |
| `protect` | `L1` = 59 (302) | `LEVEL_IMMORTAL` = 52 (473) | −7 |
| `reboo` | `L1` = 59 (303) | `LEVEL_IMMORTAL` = 52 (519) | −7 |
| `reboot` | `L1` = 59 (304) | `MAX_LEVEL - 2` = 58 (470) | −1 |
| `shutdow` | `L1` = 59 (306) | `LEVEL_IMMORTAL` = 52 (520) | −7 |
| `shutdown` | `L1` = 59 (307) | `MAX_LEVEL - 2` = 58 (471) | −1 |
| `log` | `L1` = 59 (336) | `LEVEL_HERO` = 51 (578) | −8 |
| `disconnect` | `L3` = 57 (298) | `LEVEL_IMMORTAL` = 52 (457) | −5 |
| `pardon` | `L3` = 57 (319) | `LEVEL_IMMORTAL` = 52 (456) | −5 |
| `sla` | `L3` = 57 (323) | `LEVEL_IMMORTAL` = 52 (431) | −5 |
| `slay` | `L3` = 57 (324) | `LEVEL_IMMORTAL` = 52 (430) | −5 |
| `flag` | `L4` = 56 (299) | `LEVEL_IMMORTAL - 2` = 50 (508) | −6 |
| `freeze` | `L4` = 56 (300) | `LEVEL_IMMORTAL` = 52 (435) | −4 |
| `guild` | `L4` = 56 (87) | `LEVEL_IMMORTAL - 2` = 50 (507) | −6 |
| `load` | `L4` = 56 (312) | `LEVEL_IMMORTAL` = 52 (425) | −4 |
| `newlock` | `L4` = 56 (313) | `LEVEL_HERO` = 51 (620) | −5 |
| `pecho` | `L4` = 56 (318) | `LEVEL_IMMORTAL` = 52 (450) | −4 |
| `purge` | `L4` = 56 (320) | `LEVEL_IMMORTAL` = 52 (428) | −4 |
| `restore` | `L4` = 56 (322) | `LEVEL_IMMORTAL` = 52 (429) | −4 |
| `sockets` | `L4` = 56 (99) | `LEVEL_IMMORTAL` = 52 (465) | −4 |
| `vnum` | `L4` = 56 (348) | `LEVEL_IMMORTAL` = 52 (459) | −4 |
| `zecho` | `L4` = 56 (349) | `LEVEL_IMMORTAL` = 52 (449) | −4 |
| `gecho` | `L4` = 56 (331) | `LEVEL_IMMORTAL` = 52 (486) | −4 |
| `nochannels` | `L5` = 55 (314) | `LEVEL_IMMORTAL` = 52 (452) | −3 |
| `noemote` | `L5` = 55 (315) | `LEVEL_IMMORTAL` = 52 (453) | −3 |
| `noshout` | `L5` = 55 (316) | `LEVEL_IMMORTAL` = 52 (454) | −3 |
| `notell` | `L5` = 55 (317) | `LEVEL_IMMORTAL` = 52 (455) | −3 |
| `peace` | `L5` = 55 (340) | `LEVEL_IMMORTAL` = 52 (423) | −3 |
| `snoop` | `L5` = 55 (343) | `LEVEL_IMMORTAL` = 52 (436) | −3 |
| `string` | `L5` = 55 (345) | `LEVEL_IMMORTAL` = 52 (482) | −3 |
| `transfer`/`teleport` | `L5` = 55 (325–326) | `LEVEL_IMMORTAL` (52, 421) / `LEVEL_IMMORTAL - 1` (51, 515) | −3 / −4 |
| `clone` | `L5` = 55 (351) | `LEVEL_IMMORTAL` = 52 (467) | −3 |
| `at` | `L6` = 54 (78) | `LEVEL_IMMORTAL` = 52 (419) | −2 |
| `recho` (`echo`) | `L6` = 54 (341) | `LEVEL_IMMORTAL` = 52 (448) | −2 |
| `return` | `L6` = 54 (342) | `LEVEL_IMMORTAL` = 52 (438) | −2 |
| `switch` | `L6` = 54 (346) | `LEVEL_IMMORTAL` = 52 (437) | −2 |
| `force` | `L7` = 53 (311) | `LEVEL_IMMORTAL` = 52 (422) | −1 |
| `goto` | `L8` = 52 (85) | `LEVEL_IMMORTAL` = 52 (420) | 0 ✅ |
| `poofin`/`poofout` | `L8` = 52 (329–330) | `LEVEL_IMMORTAL` = 52 (443–444) | 0 ✅ |

**Net effect**: every drift is **negative** — Python grants commands at lower
levels than ROM. A LEVEL_IMMORTAL (52) character in Python can `reboot`,
`shutdown`, `purge`, `restore`, `freeze`, `slay`, `transfer`, `force`, etc.
In ROM, those require L1, L4, L7, etc. **This is a security-relevant gap**.

---

## Phase 4 — Gap closure (planning)

**Recommended order** (close highest-risk first; each via `/rom-gap-closer`):

1. **INTERP-001** — split into one closure per row in the table above (~40 commits). Each is mechanical: change `min_trust=` value to ROM's tier. Test: a character at trust = ROM_LEVEL - 1 cannot use the command; a character at trust = ROM_LEVEL can.
2. **INTERP-018** + **INTERP-019** + **INTERP-020** + **INTERP-023** — rewrite `perform_social` to add COMM_NOEMOTE, position gates, snore exception, and the NPC slap auto-react (using `rng_mm.number_bits(4)`).
3. **INTERP-002** + **INTERP-003** — wire snoop forwarding and `WIZ_SECURE` log mirror into `process_command`.
4. **INTERP-008** — register `"."`, `","`, `"/"` aliases in `COMMAND_INDEX` (single edit covers all three).
5. **INTERP-009** through **INTERP-014** — repoint each alias to ROM's canonical handler and delete the redundant Python stubs (`do_hit`, `do_take`, `do_junk`, `do_tap`, `do_go`, `do_colon`, possibly `do_wield`/`do_hold` if their bodies don't add ROM-required logic).
6. **INTERP-004** + **INTERP-005** + **INTERP-006** — set the missing `min_trust` and fix `music`'s `min_position`.
7. **INTERP-007** — change empty-input return path to silent (drop the `"What?"` literal).
8. **INTERP-017** — write a parametric test that enumerates every 1- and 2-letter prefix and asserts `resolve_command(prefix, trust=60)` matches the ROM table-order winner. Reorder `COMMANDS` (or add an explicit priority field) until it passes.
9. **INTERP-021** — rewrite `social_registry` lookup to fall back to `str_prefix` semantics.
10. **INTERP-022** — replace `social.not_found` with the literal `"They aren't here."`.
11. **INTERP-024** — verify `do_commands`/`do_wizhelp` formatting in `info.py`.
12. **INTERP-015** — replace `shlex.split` with a ROM-faithful `one_argument` port (or limit shlex use to non-backslash inputs).
13. **INTERP-016** — defer; document as "no-op in stock ROM."

### Per-rule reminders for closures (from `AGENTS.md`)

- RNG via `mud.math.rng_mm.number_*` only. INTERP-023 explicitly requires `number_bits(4)`.
- Integer math via `c_div`/`c_mod` if any closure touches arithmetic (INTERP-001 doesn't).
- Flag values via IntEnum — no hex literals (`COMM_NOEMOTE` must be `CommFlag.NOEMOTE` or equivalent).
- One gap = one failing test (`tests/integration/test_dispatcher_*.py` or `test_socials_rom_parity.py`) = one `feat(parity)`/`fix(parity)` commit.

---

## Phase 5 — Closure (pending)

Will flip `interp.c` row in `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
from `⚠️ Partial / 80%` to `✅ AUDITED` with the new percentage once all
CRITICAL and IMPORTANT gaps above are FIXED. MINOR gaps (INTERP-015,
INTERP-016, INTERP-022) may be deferred with a note in the audit doc.

CHANGELOG entries and session summary will follow per AGENTS.md Repo Hygiene.
