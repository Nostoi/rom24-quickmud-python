# `act_wiz.c` Audit — ROM 2.4b6 → QuickMUD-Python Parity

**Status:** ⚠️ PARTIAL — first 2026-04-28 parity pass closed 4 gameplay-visible gaps (`WIZ-001`..`004`)  
**Date:** 2026-04-28  
**ROM C:** `src/act_wiz.c` (4685 lines, immortal/admin command family)  
**Python:** `mud/wiznet.py`, `mud/commands/imm_commands.py`, `mud/commands/imm_admin.py`, `mud/commands/imm_server.py`, `mud/commands/imm_display.py`, `mud/commands/imm_punish.py`, `mud/commands/imm_load.py`, `mud/commands/imm_search.py`, `mud/commands/imm_set.py`, `mud/commands/imm_emote.py`, `mud/commands/admin_commands.py`, `mud/commands/inventory.py`, `mud/commands/remaining_rom.py`, `mud/commands/alias_cmds.py`, `mud/commands/typo_guards.py`  
**Priority:** P2 (immortal/admin command surface)

## Phase 1 — Function Inventory

| ROM C function | ROM lines | Python equivalent | Status |
|----------------|-----------|-------------------|--------|
| `do_wiznet` | `src/act_wiz.c:67-169` | `mud/wiznet.py:184` | ⚠️ PARTIAL |
| `wiznet` | `src/act_wiz.c:171-194` | `mud/wiznet.py:91` | ⚠️ PARTIAL |
| `do_guild` | `src/act_wiz.c:196-249` | `mud/commands/remaining_rom.py:267` | ⚠️ PARTIAL |
| `do_outfit` | `src/act_wiz.c:251-312` | `mud/commands/inventory.py:870` | ⚠️ PARTIAL |
| `do_nochannels` | `src/act_wiz.c:314-360` | `mud/commands/imm_punish.py:28` | ⚠️ PARTIAL |
| `do_smote` | `src/act_wiz.c:362-453` | `mud/commands/imm_emote.py:24` | ⚠️ PARTIAL |
| `do_bamfin` | `src/act_wiz.c:455-483` | `mud/commands/imm_display.py:95` (`do_poofin`) | ⚠️ PARTIAL |
| `do_bamfout` | `src/act_wiz.c:485-513` | `mud/commands/imm_display.py:127` (`do_poofout`) | ⚠️ PARTIAL |
| `do_deny` | `src/act_wiz.c:517-559` | `mud/commands/admin_commands.py:441` (`cmd_deny`) | ⚠️ PARTIAL |
| `do_disconnect` | `src/act_wiz.c:561-617` | `mud/commands/imm_punish.py:204` | ⚠️ PARTIAL |
| `do_pardon` | `src/act_wiz.c:619-672` | `mud/commands/imm_punish.py:160` | ⚠️ PARTIAL |
| `do_echo` | `src/act_wiz.c:674-695` | `mud/commands/imm_display.py:159` | ⚠️ PARTIAL |
| `do_recho` | `src/act_wiz.c:700-724` | `mud/commands/imm_display.py:184` | ⚠️ PARTIAL |
| `do_zecho` | `src/act_wiz.c:726-748` | `mud/commands/imm_display.py:210` | ⚠️ PARTIAL |
| `do_pecho` | `src/act_wiz.c:750-778` | `mud/commands/imm_display.py:243` | ⚠️ PARTIAL |
| `find_location` | `src/act_wiz.c:780-797` | `mud/commands/imm_commands.py:33` | ⚠️ PARTIAL |
| `do_transfer` | `src/act_wiz.c:799-880` | `mud/commands/imm_commands.py:218` | ⚠️ PARTIAL |
| `do_at` | `src/act_wiz.c:882-935` | `mud/commands/imm_commands.py:115` | ⚠️ PARTIAL |
| `do_goto` | `src/act_wiz.c:937-998` | `mud/commands/imm_commands.py:164` | ⚠️ PARTIAL |
| `do_violate` | `src/act_wiz.c:1000-1057` | `mud/commands/imm_server.py:156` | ⚠️ PARTIAL |
| `do_stat` | `src/act_wiz.c:1059-1120` | `mud/commands/imm_search.py:448` | ✅ AUDITED |
| `do_rstat` | `src/act_wiz.c:1122-1215` | `mud/commands/imm_search.py:495` | ✅ AUDITED |
| `do_ostat` | `src/act_wiz.c:1219-1538` | `mud/commands/imm_search.py:604` | ✅ AUDITED |
| `do_mstat` | `src/act_wiz.c:1543-1742` | `mud/commands/imm_search.py:810` | ✅ AUDITED |
| `do_rstat` | `src/act_wiz.c:1122-1217` | folded into `mud/commands/imm_search.py` helpers | ❌ MISSING |
| `do_ostat` | `src/act_wiz.c:1219-1541` | folded into `mud/commands/imm_search.py` helpers | ❌ MISSING |
| `do_mstat` | `src/act_wiz.c:1543-1744` | folded into `mud/commands/imm_search.py` helpers | ❌ MISSING |
| `do_vnum` | `src/act_wiz.c:1746-1783` | `mud/commands/imm_search.py:17` | ⚠️ PARTIAL |
| `do_mfind` | `src/act_wiz.c:1785-1834` | `mud/commands/imm_search.py:60` | ⚠️ PARTIAL |
| `do_ofind` | `src/act_wiz.c:1836-1884` | `mud/commands/imm_search.py:90` | ⚠️ PARTIAL |
| `do_owhere` | `src/act_wiz.c:1886-1948` | `mud/commands/imm_search.py:147` | ⚠️ PARTIAL |
| `do_mwhere` | `src/act_wiz.c:1950-2017` | `mud/commands/imm_search.py:206` | ⚠️ PARTIAL |
| `do_reboo` | `src/act_wiz.c:2019-2025` | `mud/commands/typo_guards.py:38` | ✅ AUDITED |
| `do_reboot` | `src/act_wiz.c:2027-2051` | `mud/commands/imm_server.py:25` | ⚠️ PARTIAL |
| `do_shutdow` | `src/act_wiz.c:2053-2057` | `mud/commands/typo_guards.py:49` | ✅ AUDITED |
| `do_shutdown` | `src/act_wiz.c:2059-2084` | `mud/commands/imm_server.py:57` | ⚠️ PARTIAL |
| `do_protect` | `src/act_wiz.c:2086-2118` | `mud/commands/imm_server.py:124` | ⚠️ PARTIAL |
| `do_snoop` | `src/act_wiz.c:2120-2200` | `mud/commands/imm_admin.py:150` | ⚠️ PARTIAL |
| `do_switch` | `src/act_wiz.c:2202-2271` | `mud/commands/imm_admin.py:200` | ⚠️ PARTIAL |
| `do_return` | `src/act_wiz.c:2273-2310` | `mud/commands/imm_admin.py:249` | ⚠️ PARTIAL |
| `do_clone` | `src/act_wiz.c:2338-2457` | `mud/commands/imm_search.py:348` | ⚠️ PARTIAL |
| `do_load` / `do_mload` / `do_oload` | `src/act_wiz.c:2459-2572` | `mud/commands/imm_load.py:17`, `mud/commands/imm_load.py:51`, `mud/commands/imm_load.py:90` | ⚠️ PARTIAL |
| `do_purge` | `src/act_wiz.c:2574-2650` | `mud/commands/imm_load.py:152` | ⚠️ PARTIAL |
| `do_advance` | `src/act_wiz.c:2652-2742` | `mud/commands/imm_admin.py:18` | ⚠️ PARTIAL |
| `do_trust` | `src/act_wiz.c:2743-2783` | `mud/commands/imm_admin.py:71` | ⚠️ PARTIAL |
| `do_restore` | `src/act_wiz.c:2785-2870` | `mud/commands/imm_load.py:218` | ⚠️ PARTIAL |
| `do_freeze` | `src/act_wiz.c:2872-2925` | `mud/commands/imm_admin.py:113` | ⚠️ PARTIAL |
| `do_log` | `src/act_wiz.c:2927-2984` | `mud/commands/admin_commands.py:341` | ✅ AUDITED |
| `do_noemote` | `src/act_wiz.c:2986-3032` | `mud/commands/imm_punish.py:61` | ⚠️ PARTIAL |
| `do_noshout` | `src/act_wiz.c:3034-3085` | `mud/commands/imm_punish.py:93` | ⚠️ PARTIAL |
| `do_notell` | `src/act_wiz.c:3087-3132` | `mud/commands/imm_punish.py:128` | ⚠️ PARTIAL |
| `do_peace` | `src/act_wiz.c:3134-3148` | `mud/commands/imm_commands.py:377` | ⚠️ PARTIAL |
| `do_wizlock` | `src/act_wiz.c:3150-3169` | `mud/commands/admin_commands.py:60` (`cmd_wizlock`) | ⚠️ PARTIAL |
| `do_newlock` | `src/act_wiz.c:3171-3189` | `mud/commands/admin_commands.py:69` (`cmd_newlock`) | ⚠️ PARTIAL |
| `do_slookup` | `src/act_wiz.c:3191-3231` | `mud/commands/imm_search.py:120` | ⚠️ PARTIAL |
| `do_set` / `do_sset` / `do_mset` / `do_string` / `do_oset` / `do_rset` | `src/act_wiz.c:3233-4138` | `mud/commands/imm_set.py` | ⚠️ PARTIAL |
| `do_sockets` | `src/act_wiz.c:4140-4181` | `mud/commands/imm_search.py:268` | ⚠️ PARTIAL |
| `do_force` | `src/act_wiz.c:4183-4322` | `mud/commands/imm_commands.py:293` | ✅ AUDITED |
| `do_invis` | `src/act_wiz.c:4329-4373` | `mud/commands/imm_display.py:17` | ⚠️ PARTIAL |
| `do_incognito` | `src/act_wiz.c:4375-4420` | `mud/commands/imm_display.py:61` | ⚠️ PARTIAL |
| `do_holylight` | `src/act_wiz.c:4422-4441` | `mud/commands/admin_commands.py:396` (`cmd_holylight`) | ⚠️ PARTIAL |
| `do_prefi` / `do_prefix` | `src/act_wiz.c:4443-4496` | `mud/commands/alias_cmds.py:120`, `mud/commands/alias_cmds.py:126` | ✅ AUDITED |
| `do_copyover` | `src/act_wiz.c:4498-4683` | `mud/commands/imm_server.py:91` | ⚠️ PARTIAL |
| `do_qmconfig` | `src/act_wiz.c:4685-4768` | `mud/commands/admin_commands.py:94` (`cmd_qmconfig`) | ⚠️ PARTIAL |

## Phase 2 — Line-by-line Verification

### Private-room movement helpers (`find_location`, `do_at`, `do_goto`, `do_transfer`)

ROM `src/act_wiz.c:821-839,897-905,957-966`:
- Uses `is_room_owner(ch, location)` as an explicit bypass before `room_is_private(location)`.
- Treats owner-locked rooms as private, alongside `ROOM_PRIVATE` / `ROOM_SOLITARY`.
- Applies the same room-privacy gate to `transfer`, `at`, and `goto`.

Python before this pass:
- ❌ `mud/commands/imm_commands.py` used a local `_room_is_private()` that ignored `room.owner`.
- ❌ The local helper used the wrong solitary bit mask (`0x00000400` instead of ROM `ROOM_SOLITARY == 2048`).
- ❌ `do_at`, `do_goto`, and `do_transfer` had no owner-bypass logic.

Python now:
- ✅ Treats owner rooms as private.
- ✅ Uses the canonical `RoomFlag` enum values.
- ✅ Applies the ROM owner bypass before blocking private-room movement.

### `do_violate`

ROM `src/act_wiz.c:1000-1057`:
- Uses `find_location(ch, argument)`, not directional exit parsing.
- Shares `goto`-style bamf departure/arrival messaging.
- Rejects non-private targets with `"That room isn't private, use goto.\n\r"`.
- Uses the same no-argument prompt as `goto`: `"Goto where?\n\r"`.

Python before this pass:
- ❌ Parsed directions/exits instead of locations.
- ❌ Could not target a private room by vnum or character name.
- ❌ Used non-ROM prompt and failure strings.

Python now:
- ✅ Resolves the target through `find_location()`.
- ✅ Rejects public rooms with the ROM `use goto` hint.
- ✅ Uses the ROM no-argument prompt and room move flow.

### `do_protect`

ROM `src/act_wiz.c:2086-2118`:
- Prompts `"Protect whom from snooping?\n\r"`.
- On lookup failure prints `"You can't find them.\n\r"`.
- Toggles `COMM_SNOOP_PROOF` on any found victim (no NPC exclusion).
- Sends victim `"You are now immune to snooping.\n\r"` / `"Your snoop-proofing was just removed.\n\r"`.
- Sends the immortal `"$N is now snoop-proof."` / `"$N is no longer snoop-proof."`.

Python before this pass:
- ❌ Used `"They aren't here."` on lookup failure.
- ❌ Rejected NPCs even though ROM does not.
- ❌ Used the wrong flag bit (`0x00020000`, actually `COMM_NOTELL`).
- ❌ Used non-ROM actor/victim strings.

Python now:
- ✅ Uses `CommFlag.SNOOP_PROOF`.
- ✅ Uses ROM-visible actor/victim strings.
- ✅ Allows NPC targets.

### `do_snoop`

ROM `src/act_wiz.c:2167-2174`:
- Rejects victims protected by `COMM_SNOOP_PROOF`.

Python before this pass:
- ❌ Checked the wrong bit (`0x00020000`), so a correctly-set `CommFlag.SNOOP_PROOF` would not block snooping.

Python now:
- ✅ Checks the canonical `CommFlag.SNOOP_PROOF` value.

## Phase 3 — Gaps

| ID | Severity | ROM C ref | Python ref | Description | Status |
|----|----------|-----------|------------|-------------|--------|
| `WIZ-001` | CRITICAL | `src/act_wiz.c:821-839,897-905,957-966` | `mud/commands/imm_commands.py:115`, `mud/commands/imm_commands.py:164`, `mud/commands/imm_commands.py:218`, `mud/commands/imm_commands.py:407`, `mud/commands/imm_commands.py:428` | Private-room movement ignored `room.owner`, used the wrong `ROOM_SOLITARY` value, and lacked ROM `is_room_owner()` bypass handling. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_goto_denies_non_owner_into_owned_private_room` |
| `WIZ-002` | IMPORTANT | `src/act_wiz.c:1000-1057` | `mud/commands/imm_server.py:156` | `do_violate` parsed directions instead of `find_location()` targets and missed the ROM private-room gating/message path. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_violate_uses_room_lookup_and_rejects_non_private_rooms` |
| `WIZ-003` | CRITICAL | `src/act_wiz.c:2086-2118` | `mud/commands/imm_server.py:124` | `do_protect` used the wrong bitmask, blocked NPCs incorrectly, and used non-ROM lookup and snoop-proof messages. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_protect_sets_rom_snoop_proof_flag_and_message` |
| `WIZ-004` | CRITICAL | `src/act_wiz.c:2167-2174` | `mud/commands/imm_admin.py:150` | `do_snoop` checked the wrong bitmask, so canonical `CommFlag.SNOOP_PROOF` did not actually block snooping. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_snoop_honors_comm_snoop_proof_enum` |
| `WIZ-005` | CRITICAL | `src/act_wiz.c:1059-1742` | `mud/commands/imm_search.py:448` | `do_stat` dispatch auto-detection used room-local lookups instead of world lookups; `do_rstat`/`do_ostat`/`do_mstat` were simplified stubs with no ROM output format parity, missing private-room checks, description output, exit details, affects, bit-name rendering, item-type-specific stat blocks, and `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_stat_*`, `test_rstat_*`, `test_ostat_*`, `test_mstat_*` |
| `WIZ-006` | IMPORTANT | `src/act_wiz.c:2927-2984` | `mud/commands/admin_commands.py:341` | `do_log` used `character_registry` prefix match instead of `get_char_world`, toggled a `log_commands` bool instead of `PlayerFlag.LOG` on `act`, and omitted ROM `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_log_*` |
| `WIZ-007` | IMPORTANT | `src/act_wiz.c:4183-4322` | `mud/commands/imm_commands.py:293` | `do_force` was missing `gods` branch, private-room check, canonical trust check for all victims, and ROM `\n\r` line endings; bulk branches iterated wrong collections. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_force_*` |

## Phase 4 — Closures

### `WIZ-001` — ✅ FIXED

- **Python:** `mud/commands/imm_commands.py:115`, `mud/commands/imm_commands.py:164`, `mud/commands/imm_commands.py:218`, `mud/commands/imm_commands.py:407`, `mud/commands/imm_commands.py:428`
- **ROM C:** `src/act_wiz.c:821-839,897-905,957-966`
- **Fix:** Restored owner-aware private-room gating and canonical `RoomFlag` usage for `at`, `goto`, and `transfer`.
- **Tests:** `tests/integration/test_act_wiz_command_parity.py::test_goto_denies_non_owner_into_owned_private_room`

### `WIZ-002` — ✅ FIXED

- **Python:** `mud/commands/imm_server.py:156`
- **ROM C:** `src/act_wiz.c:1000-1057`
- **Fix:** Reworked `do_violate` to use `find_location()`, ROM prompt strings, ROM public-room rejection, and a `goto`-style move flow.
- **Tests:** `tests/integration/test_act_wiz_command_parity.py::test_violate_uses_room_lookup_and_rejects_non_private_rooms`

### `WIZ-003` — ✅ FIXED

- **Python:** `mud/commands/imm_server.py:124`
- **ROM C:** `src/act_wiz.c:2086-2118`
- **Fix:** Restored ROM `protect` lookup/messages and switched to `CommFlag.SNOOP_PROOF`.
- **Tests:** `tests/integration/test_act_wiz_command_parity.py::test_protect_sets_rom_snoop_proof_flag_and_message`

### `WIZ-004` — ✅ FIXED

- **Python:** `mud/commands/imm_admin.py:150`
- **ROM C:** `src/act_wiz.c:2167-2174`
- **Fix:** Restored ROM snoop-proof blocking by checking `CommFlag.SNOOP_PROOF` instead of the old `NOTELL` bit.
- **Tests:** `tests/integration/test_act_wiz_command_parity.py::test_snoop_honors_comm_snoop_proof_enum`

### `WIZ-006` — ✅ FIXED

- **Python:** `mud/commands/admin_commands.py:341`
- **ROM C:** `src/act_wiz.c:2927-2984`
- **Fix:** Replaced `character_registry` prefix-match lookup with `get_char_world()`; replaced `log_commands` bool toggle with canonical `PlayerFlag.LOG` bit toggle on `victim.act`; added ROM `\n\r` line endings to all messages.
- **Tests:** `tests/integration/test_act_wiz_command_parity.py::test_log_toggles_plr_log_on_act_not_bool_field`, `test_log_rejects_npc`, `test_log_all_toggles_global_flag`, `test_log_empty_arg_and_not_found`

### `WIZ-005` — ✅ FIXED

- **Python:** `mud/commands/imm_search.py:448` (do_stat, do_rstat, do_ostat, do_mstat)
- **ROM C:** `src/act_wiz.c:1059-1742`
- **Fix:** Rewrote `do_stat` dispatcher to use `get_char_world`/`get_obj_world`/`find_location` for ROM-faithful auto-detection (not room-local lookups); added ROM syntax message for empty args; added `char`/`mob` keyword routing to `do_mstat`. Rewrote `do_rstat` with ROM area name, vnum, sector, light, healing, mana, room flags, description, extra descriptions, character list, object list, and door details. Rewrote `do_ostat` with ROM name(s), vnum/format/type/resets, short/long description, wear bits, extra bits, number/weight, level/cost/condition/timer, in_room/in_obj/carried_by/wear_loc, values, item-type-specific blocks (scroll/potion/pill, wand/staff, drink_con, weapon, armor, container), extra descriptions, and affect listing with bitvector where/types. Rewrote `do_mstat` with ROM name, vnum/format/race/group/sex/room, NPC count/killed, stats (perm+cur), hp/mana/move/practices, level/class/align/gold/silver/exp, AC per type, hit/dam/saves/size/position/wimpy, NPC damage/message, fighting, thirst/hunger/full/drunk for PCs, carry number/weight, age/played/last_level/timer for PCs, act bits, comm bits, offense bits, immune/resist/vulnerable, form/parts, affected_by, master/leader/pet, security for PCs, short/long description, spec_fun, and affected list. Added 8 ROM-faithful bit-name helpers to `mud/handler.py`: `wear_bit_name`, `extra_bit_name`, `imm_bit_name`, `off_bit_name`, `form_bit_name`, `part_bit_name`, `weapon_bit_name`, `cont_bit_name`, plus `size_name`, `position_name`, `sex_name`, `class_name`, `race_name` helpers. All outputs use canonical `\n\r` line endings.
- **Tests:** `test_stat_shows_syntax_when_no_args`, `test_stat_room_dispatches_to_rstat`, `test_stat_mob_dispatches_to_mstat`, `test_stat_nothing_found`, `test_rstat_shows_room_info`, `test_rstat_private_room_blocks_non_owner`, `test_ostat_shows_object_info`, `test_ostat_empty_arg`, `test_mstat_shows_character_info`, `test_mstat_empty_arg`

### `WIZ-007` — ✅ FIXED

- **Python:** `mud/commands/imm_commands.py:293`
- **ROM C:** `src/act_wiz.c:4183-4322`
- **Fix:** Added `gods` branch (force immortals ≥ LEVEL_HERO); added private-room check using `_is_room_owner` / `_room_is_private`; changed trust check to apply to all victims (not just non-NPCs); added `MAX_LEVEL - 3` threshold for forcing PCs; iterated `descriptor_list` for `force all` and `char_list` for `force players`/`force gods` per ROM semantics; added canonical `\n\r` line endings; added `mob` prefix check (`startswith("mob")`) per ROM `!str_prefix(arg2, "mob")`.
- **Tests:** `tests/integration/test_act_wiz_command_parity.py::test_force_rejects_delete_and_mob_prefix`, `test_force_empty_arg`, `test_force_self_returns_aye_aye`, `test_force_gods_branch_rejects_low_trust`, `test_force_private_room_blocks_non_owner`, `test_force_single_target_trust_check`, `test_force_returns_ok_after_single_force`

## Phase 5 — Current State

`act_wiz.c` remains **PARTIAL** after this pass.

Completed this session:
- `do_stat` dispatcher now uses world-scope lookups and ROM-faithful routing.
- `do_rstat` / `do_ostat` / `do_mstat` rewritten with full ROM C output parity.
- 8 bit-name helpers added to `mud/handler.py` (wear, extra, imm, off, form, part, weapon, cont).
- 5 display helpers added (size_name, position_name, sex_name, class_name, race_name).

Still outstanding:
- Remaining echo family, punishment, load/clone, and server-control audits.

Validation:
- `pytest tests/integration/test_act_wiz_command_parity.py -q` — `25 passed`
- `ruff check mud/commands/imm_search.py mud/commands/admin_commands.py mud/commands/imm_commands.py` — clean
