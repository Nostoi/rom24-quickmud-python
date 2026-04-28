# `act_wiz.c` Audit — ROM 2.4b6 → QuickMUD-Python Parity

**Status:** ⚠️ PARTIAL — first 2026-04-28 parity pass closed 4 gameplay-visible gaps (`WIZ-001`..`004`)  
**Date:** 2026-04-28  
**ROM C:** `src/act_wiz.c` (4685 lines, immortal/admin command family)  
**Python:** `mud/wiznet.py`, `mud/commands/imm_commands.py`, `mud/commands/imm_admin.py`, `mud/commands/imm_server.py`, `mud/commands/imm_display.py`, `mud/commands/imm_punish.py`, `mud/commands/imm_load.py`, `mud/commands/imm_search.py`, `mud/commands/imm_set.py`, `mud/commands/imm_emote.py`, `mud/commands/admin_commands.py`, `mud/commands/inventory.py`, `mud/commands/remaining_rom.py`, `mud/commands/alias_cmds.py`, `mud/commands/typo_guards.py`  
**Priority:** P2 (immortal/admin command surface)

## Phase 1 — Function Inventory

| ROM C function | ROM lines | Python equivalent | Status |
|----------------|-----------|-------------------|--------|
| `do_wiznet` | `src/act_wiz.c:67-169` | `mud/wiznet.py:184` (`cmd_wiznet`) | ✅ AUDITED |
| `wiznet` | `src/act_wiz.c:171-194` | `mud/wiznet.py:91` | ✅ AUDITED |
| `do_guild` | `src/act_wiz.c:196-249` | `mud/commands/remaining_rom.py:267` | ✅ AUDITED |
| `do_outfit` | `src/act_wiz.c:251-312` | `mud/commands/inventory.py:870` | ✅ AUDITED |
| `do_nochannels` | `src/act_wiz.c:314-360` | `mud/commands/imm_punish.py:28` | ✅ AUDITED |
| `do_noemote` | `src/act_wiz.c:2986-3032` | `mud/commands/imm_punish.py:61` | ✅ AUDITED |
| `do_noshout` | `src/act_wiz.c:3034-3085` | `mud/commands/imm_punish.py:93` | ✅ AUDITED |
| `do_notell` | `src/act_wiz.c:3087-3132` | `mud/commands/imm_punish.py:128` | ✅ AUDITED |
| `do_pardon` | `src/act_wiz.c:619-670` | `mud/commands/imm_punish.py:160` | ✅ AUDITED |
| `do_freeze` | `src/act_wiz.c:2872-2922` | `mud/commands/imm_admin.py:113` | ✅ AUDITED |
| `do_peace` | `src/act_wiz.c:3134-3148` | `mud/commands/imm_commands.py:392` | ✅ AUDITED |
| `do_log` | `src/act_wiz.c:2927-2984` | `mud/commands/admin_commands.py:341` | ✅ AUDITED |
| `do_deny` | `src/act_wiz.c:517-557` | `mud/commands/admin_commands.py:444` (`cmd_deny`) | ✅ AUDITED |
| `do_echo` | `src/act_wiz.c:674-695` | `mud/commands/imm_display.py:147` | ✅ AUDITED |
| `do_recho` | `src/act_wiz.c:700-724` | `mud/commands/imm_display.py:172` | ✅ AUDITED |
| `do_zecho` | `src/act_wiz.c:726-748` | `mud/commands/imm_display.py:198` | ✅ AUDITED |
| `do_pecho` | `src/act_wiz.c:750-777` | `mud/commands/imm_display.py:231` | ✅ AUDITED |
| `do_smote` | `src/act_wiz.c:362-453` | `mud/commands/imm_emote.py:24` | ✅ AUDITED |
| `do_bamfin` | `src/act_wiz.c:455-483` | `mud/commands/imm_display.py:83` (`do_poofin`) | ✅ AUDITED |
| `do_bamfout` | `src/act_wiz.c:485-512` | `mud/commands/imm_display.py:115` (`do_poofout`) | ✅ AUDITED |
| `do_disconnect` | `src/act_wiz.c:561-614` | `mud/commands/imm_punish.py:199` | ✅ AUDITED |
| `do_switch` | `src/act_wiz.c:2202-2269` | `mud/commands/imm_admin.py:202` | ✅ AUDITED |
| `do_return` | `src/act_wiz.c:2273-2303` | `mud/commands/imm_admin.py:251` | ✅ AUDITED |
| `do_wizlock` | `src/act_wiz.c:3150-3169` | `mud/commands/admin_commands.py:60` (`cmd_wizlock`) | ✅ AUDITED |
| `do_newlock` | `src/act_wiz.c:3171-3189` | `mud/commands/admin_commands.py:69` (`cmd_newlock`) | ✅ AUDITED |
| `do_slookup` | `src/act_wiz.c:3191-3231` | `mud/commands/imm_search.py:143` | ✅ AUDITED |
| `do_clone` | `src/act_wiz.c:2338-2455` | `mud/commands/imm_search.py:375` | ✅ AUDITED |
| `do_load` | `src/act_wiz.c:2459-2486` | `mud/commands/imm_load.py:17` | ✅ AUDITED |
| `do_mload` | `src/act_wiz.c:2489-2517` | `mud/commands/imm_load.py:51` | ✅ AUDITED |
| `do_oload` | `src/act_wiz.c:2521-2570` | `mud/commands/imm_load.py:90` | ✅ AUDITED |
| `do_purge` | `src/act_wiz.c:2574-2648` | `mud/commands/imm_load.py:152` | ✅ AUDITED |
| `do_restore` | `src/act_wiz.c:2785-2869` | `mud/commands/imm_load.py:218` | ✅ AUDITED |
| `do_set` | `src/act_wiz.c:3233-3275` | `mud/commands/imm_set.py:17` | ✅ AUDITED |
| `do_sset` | `src/act_wiz.c:3278-3352` | `mud/commands/imm_set.py:345` | ✅ AUDITED |
| `do_mset` | `src/act_wiz.c:3355-3790` | `mud/commands/imm_set.py:61` | ✅ AUDITED |
| `do_string` | `src/act_wiz.c:3793-3954` | `mud/commands/imm_set.py:407` | ✅ AUDITED |
| `do_oset` | `src/act_wiz.c:3958-4067` | `mud/commands/imm_set.py:218` | ✅ AUDITED |
| `do_rset` | `src/act_wiz.c:4071-4136` | `mud/commands/imm_set.py:293` | ✅ AUDITED |
| `do_sockets` | `src/act_wiz.c:4140-4181` | `mud/commands/imm_search.py:291` | ✅ AUDITED |
| `do_force` | `src/act_wiz.c:4183-4322` | `mud/commands/imm_commands.py:293` | ✅ AUDITED |
| `do_invis` | `src/act_wiz.c:4329-4373` | `mud/commands/imm_display.py:17` | ✅ AUDITED |
| `do_incognito` | `src/act_wiz.c:4375-4420` | `mud/commands/imm_display.py:61` | ✅ AUDITED |
| `do_holylight` | `src/act_wiz.c:4422-4441` | `mud/commands/admin_commands.py:399` (`cmd_holylight`) | ✅ AUDITED |
| `do_prefi` / `do_prefix` | `src/act_wiz.c:4443-4496` | `mud/commands/alias_cmds.py:120`, `mud/commands/alias_cmds.py:126` | ✅ AUDITED |
| `do_copyover` | `src/act_wiz.c:4498-4683` | `mud/commands/imm_server.py:91` | ✅ AUDITED |
| `do_qmconfig` | `src/act_wiz.c:4685-4787` | `mud/commands/admin_commands.py:95` (`cmd_qmconfig`) | ✅ AUDITED |

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
| `WIZ-008` | CRITICAL | `src/act_wiz.c:314-360,2986-3032,3034-3085,3087-3132,2872-2922,619-670` | `mud/commands/imm_punish.py:28-201`, `mud/commands/imm_admin.py:113` | Punish commands (`nochannels`, `noemote`, `noshout`, `notell`, `freeze`, `pardon`) used hardcoded wrong flag bit values (`0x00004000` instead of `CommFlag.NOCHANNELS=1<<22`, etc.), corrupting unrelated flags. Missing wiznet broadcasts and `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_nochannels_*, test_noemote_*, test_noshout_*, test_notell_*, test_pardon_*, test_freeze_*` |
| `WIZ-009` | HIGH | `src/act_wiz.c:3134-3148` | `mud/commands/imm_commands.py:392` | `do_peace` set `fighting=None` instead of calling `stop_fighting(person, True)` (incomplete combat cleanup leaving dangling references); hardcoded `ACT_AGGRESSIVE=0x20` instead of `ActFlag.AGGRESSIVE` enum. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_peace_stops_fighting_and_removes_aggressive` |
| `WIZ-010` | HIGH | `src/act_wiz.c:4329-4420` | `mud/commands/imm_display.py:17,61` | `do_invis` and `do_incognito` missing room-wide `act()` broadcast messages; `do_incognito` missing `reply = None`; both missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_invis_*, test_incognito_*` |
| `WIZ-011` | HIGH | `src/act_wiz.c:674-777` | `mud/commands/imm_display.py:147,172,198,231` | Echo family (`do_echo`, `do_recho`, `do_zecho`, `do_pecho`) iterated `registry.players` dict instead of `descriptor_list` with `CON_PLAYING` filter; `do_pecho` used wrong trust check and messages; all missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_echo_*, test_recho_*, test_zecho_*, test_pecho_*` |
| `WIZ-012` | MEDIUM | `src/act_wiz.c:455-512` | `mud/commands/imm_display.py:83,115` | `do_bamfin`/`do_bamfout` missing `smash_tilde()`, used case-insensitive name check instead of ROM `strstr` case-sensitive check; missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_poofin_*, test_poofout_*` |
| `WIZ-013` | MEDIUM | `src/act_wiz.c:3150-3188` | `mud/commands/admin_commands.py:60,69` | `cmd_wizlock`/`cmd_newlock` missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_wizlock_*, test_newlock_*` |
| `WIZ-014` | MEDIUM | `src/act_wiz.c:4422-4439` | `mud/commands/admin_commands.py:399` | `cmd_holylight` returned `"Huh?"` for NPCs instead of empty string; missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_holylight_*` |
| `WIZ-015` | MEDIUM | `src/act_wiz.c:3191-3229` | `mud/commands/imm_search.py:143` | `do_slookup` missing `all` arg, missing `Slot` column, used substring match instead of ROM `skill_lookup` prefix match; missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_slookup_*` |
| `WIZ-016` | MEDIUM | `src/act_wiz.c:4140-4176` | `mud/commands/imm_search.py:291` | `do_sockets` missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_sockets_*` |
| `WIZ-017` | HIGH | `src/act_wiz.c:517-557` | `mud/commands/admin_commands.py:444` | `cmd_deny` was a toggle instead of SET-only; used `character_registry` prefix-match instead of `get_char_world`; missing `stop_fighting(victim, TRUE)`, wiznet broadcast, and `do_quit` call; missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_deny_*` |
| `WIZ-018` | MEDIUM | `src/act_wiz.c:2202-2269` | `mud/commands/imm_admin.py:202` | `do_switch` missing private-room check (is_room_owner/room_is_private), missing wiznet broadcast; all messages missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_switch_*` |
| `WIZ-019` | MEDIUM | `src/act_wiz.c:2273-2303` | `mud/commands/imm_admin.py:251` | `do_return` missing full ROM message (`"You return to your original body. Type replay to see any missed tells."`), missing prompt cleanup, missing wiznet broadcast; all messages missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_return_*` |
| `WIZ-020` | MEDIUM | `src/act_wiz.c:362-453` | `mud/commands/imm_emote.py:24` | `do_smote` used case-insensitive name check instead of ROM `strstr`; skipped no-descriptor viewers incorrectly; missing `_smote_substitute` letter-by-letter algorithm; `\n\r` line endings missing. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_smote_*` |
| `WIZ-021` | MEDIUM | `src/act_wiz.c:750-777` | `mud/commands/imm_display.py:231` | `do_pecho` used wrong trust check (`victim is not char` instead of `get_trust(char) != MAX_LEVEL`); wrong "not found" message; missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_pecho_*` |
| `WIZ-022` | MEDIUM | `src/act_wiz.c:561-614` | `mud/commands/imm_punish.py:199` | `do_disconnect` iterated wrong collection; missing descriptor-list loop for victim lookup; missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_disconnect_*` |
| `WIZ-023` | MEDIUM | `src/act_wiz.c:196-249` | `mud/commands/remaining_rom.py:267` | `do_guild` missing `\n\r` line endings, used dict lookup instead of `lookup_clan_id`/`CLAN_TABLE`, missing independent-clan vs member-clan messaging distinction (`"a <name>"` vs `"member of clan <Name>"`), used exact string match for "none" instead of ROM `str_prefix`. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_guild_*` |
| `WIZ-024` | LOW | `src/act_wiz.c:251-310` | `mud/commands/inventory.py:870` | `do_outfit` returned "You already have your equipment" when nothing to equip (ROM always says "You have been equipped by Mota."); missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_outfit_*` |
| `WIZ-025` | LOW | `src/act_wiz.c:4498-4588` | `mud/commands/imm_server.py:91` | `do_copyover` iterated `registry.players` dict instead of `descriptor_list` with `CON_PLAYING` filter; missing `\n\r` line endings. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_copyover_*` |
| `WIZ-026` | LOW | `src/act_wiz.c:4685-4787` | `mud/commands/admin_commands.py:95` | `cmd_qmconfig` already ROM-faithful; verified `\n\r` line endings and `str_prefix` matching. No gaps found. | ✅ VERIFIED — `tests/integration/test_act_wiz_command_parity.py::test_qmconfig_*` |
| `WIZ-027` | MEDIUM | `src/act_wiz.c:2459-2486` | `mud/commands/imm_load.py:17` | `do_load` missing `\n\r` line endings; missing ROM `str_cmp` for "mob"/"char"; invalid type re-invoked `do_load("")` in ROM instead of hardcoded syntax. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_load_*` |
| `WIZ-028` | MEDIUM | `src/act_wiz.c:2489-2517` | `mud/commands/imm_load.py:51` | `do_mload` returned `"You have created {name}!"` instead of ROM `"Ok.\n\r"`; missing `wiznet()` broadcast; used `registry.mob_prototypes` directly instead of safe `getattr`; missing `\n\r`. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_mload_*` |
| `WIZ-029` | MEDIUM | `src/act_wiz.c:2521-2570` | `mud/commands/imm_load.py:90` | `do_oload` returned `"You have created {name}!"` instead of ROM `"Ok.\n\r"`; missing `wiznet()` broadcast; ROM level error says `"between 0 and your level"` with typo extra "be"; used `registry.obj_prototypes` directly; used `char.carrying` instead of `char.inventory`; missing `\n\r`. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_oload_*` |
| `WIZ-030` | HIGH | `src/act_wiz.c:2574-2648` | `mud/commands/imm_load.py:152` | `do_purge` trust check used `>=` instead of ROM `<=`; missing `"X tried to purge you!\n\r"` notification to victim on trust failure; all messages missing `\n\r`. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_purge_*` |
| `WIZ-031` | MEDIUM | `src/act_wiz.c:2785-2869` | `mud/commands/imm_load.py:218` | `do_restore` iterated `registry.players` instead of `descriptor_list` for `restore all`; missing wiznet broadcasts for room restore, `all` restore, and individual restore; all messages missing `\n\r`. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_restore_*` |
| `WIZ-032` | MEDIUM | `src/act_wiz.c:2338-2455` | `mud/commands/imm_search.py:375` | `do_clone` missing `\n\r` line endings; missing wiznet broadcasts; missing ROM trust check for mob cloning; used `char.carrying` instead of checking `obj.carried_by`; missing `"Your powers are not great enough"` message for obj_check. | ✅ FIXED — `tests/integration/test_act_wiz_command_parity.py::test_clone_*` |
| `WIZ-033` | MEDIUM | `src/act_wiz.c:3233-3275` | `mud/commands/imm_set.py:17` | `do_set` syntax messages missing `\n\r` line endings; invalid type should re-invoke `do_set("")` per ROM, not return hardcoded syntax. | ✅ FIXED |
| `WIZ-034` | MEDIUM | `src/act_wiz.c:3278-3352` | `mud/commands/imm_set.py:312` | `do_sset` uses string iteration over `skill_table` instead of ROM `skill_lookup`; missing `(use the name of the skill, not the number)` hint; missing `\n\r` line endings. | ✅ FIXED |
| `WIZ-035` | HIGH | `src/act_wiz.c:3355-3790` | `mud/commands/imm_set.py:68` | `do_mset` missing `smash_tilde`; stat max hardcoded 25 instead of `get_max_train()`; `level` allows PCs (ROM: NPC-only); `sex` missing `pcdata.true_sex` set; `hp`/`mana`/`move` missing `pcdata.perm_hit/perm_mana/perm_move` set and wrong ranges; `practice`/`train` missing range checks; `class` field entirely missing (uses `class_lookup`); `race` field entirely missing (uses `race_lookup`); `group` field missing (NPC-only); `hours` field missing; `thirst`/`drunk`/`full`/`hunger` fields missing (PC-only with condition arrays); `security` missing `ch->pcdata->security`-based range check; `victim->zone` not cleared; unknown field re-invokes `do_mset("")` per ROM; all messages missing `\n\r`. | ✅ FIXED |
| `WIZ-036` | MEDIUM | `src/act_wiz.c:3958-4067` | `mud/commands/imm_set.py:366` | `do_oset` missing `smash_tilde`; missing `v0`-`v4` short aliases (ROM allows `v0` as alias for `value0`); `value0` not capped at `UMIN(50,value)` per ROM:3998; missing `timer` field; unknown field re-invokes `do_oset("")` per ROM; all messages missing `\n\r`. | ✅ FIXED |
| `WIZ-037` | MEDIUM | `src/act_wiz.c:4071-4136` | `mud/commands/imm_set.py:457` | `do_rset` missing `smash_tilde`; uses `registry.rooms.get(vnum)` instead of ROM `find_location(ch, arg1)`; missing private-room check (`is_room_owner`/`room_is_private`); missing `"Value must be numeric.\n\r"` check; unknown field re-invokes `do_rset("")`; `"No such location.\n\r"` vs `"No such room."`; all messages missing `\n\r`. | ✅ FIXED |
| `WIZ-038` | MEDIUM | `src/act_wiz.c:3793-3954` | `mud/commands/imm_set.py:516` | `do_string` missing `smash_tilde`; `spec` field entirely missing (NPC-only, uses `spec_lookup`); `long` appends `\n` instead of ROM `\n\r`; `title` uses `" " + value` instead of ROM `set_title(victim, arg3)`; `desc` uses exact match instead of `str_prefix`; extended description stub instead of ROM `extra_descr` insertion; bad type re-invokes `do_string("")` per ROM; all messages missing `\n\r`. | ✅ FIXED |

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

### `WIZ-008` — ✅ FIXED

- **Python:** `mud/commands/imm_punish.py:28-201`, `mud/commands/imm_admin.py:113`
- **ROM C:** `src/act_wiz.c:314-360,2986-3032,3034-3085,3087-3132,2872-2922,619-670`
- **Fix:** Replaced all hardcoded flag constants with canonical `CommFlag` and `PlayerFlag` enums. `COMM_NOCHANNELS=0x00004000` → `CommFlag.NOCHANNELS` (bit 22); `COMM_NOEMOTE=0x00008000` → `CommFlag.NOEMOTE` (bit 19); `COMM_NOSHOUT=0x00010000` → `CommFlag.NOSHOUT` (bit 20); `COMM_NOTELL=0x00020000` → `CommFlag.NOTELL` (bit 21); `PLR_KILLER=0x00000004` → `PlayerFlag.KILLER` (bit 26); `PLR_THIEF=0x00000008` → `PlayerFlag.THIEF` (bit 25); `PLR_FREEZE=0x00004000` → `PlayerFlag.FREEZE` (bit 24). Added `wiznet()` calls with `WIZ_PENALTIES` + `WIZ_SECURE` flags. Added canonical `\n\r` line endings. `do_pardon` now silently returns when flag not set (matching ROM line 654 `return`).
- **Tests:** `test_nochannels_sets_and_removes_comm_flag`, `test_nochannels_rejects_higher_trust`, `test_noemote_sets_and_removes_comm_flag`, `test_noshout_rejects_npc`, `test_notell_sets_and_removes_comm_flag`, `test_pardon_killer_flag`, `test_pardon_thief_flag`, `test_pardon_rejects_npc`, `test_freeze_sets_and_removes_plr_freeze`, `test_freeze_rejects_npc`

### `WIZ-009` — ✅ FIXED

- **Python:** `mud/commands/imm_commands.py:392`
- **ROM C:** `src/act_wiz.c:3134-3148`
- **Fix:** Replaced `person.fighting = None` with `stop_fighting(person, True)` to properly clear all combat references (both attacker and defender). Replaced hardcoded `ACT_AGGRESSIVE=0x20` with `ActFlag.AGGRESSIVE` enum. Added canonical `\n\r` line endings.
- **Tests:** `tests/integration/test_act_wiz_command_parity.py::test_peace_stops_fighting_and_removes_aggressive`

### `WIZ-010` — ✅ FIXED

- **Python:** `mud/commands/imm_display.py:17,61`
- **ROM C:** `src/act_wiz.c:4329-4420`
- **Fix:** Added `_act_room()` helper for room-wide visibility-aware messages. `do_invis` now broadcasts `"$n slowly fades into thin air."` / `"$n slowly fades back into existence."` to room occupants as ROM does via `act()`. `do_incognito` broadcasts `"$n cloaks $s presence."`. Added `char.reply = None` in `do_incognito` level-setting path (ROM 4410). Added `\n\r` line endings.
- **Tests:** `test_invis_toggle_sets_and_clears_invis_level`, `test_invis_set_level`, `test_invis_rejects_invalid_level`, `test_incognito_toggle_sets_and_clears_incog_level`, `test_incognito_set_level`

## Phase 5 — Current State

`act_wiz.c` is now **AUDITED** — all functions verified or closed.

Completed this session (WIZ-023..038):
- `do_guild` now uses `lookup_clan_id`/`CLAN_TABLE` for clan lookup; distinguishes independent-clan vs member-clan messaging; `\n\r`.
- `do_outfit` always returns ROM message.
- `do_copyover` iterates `descriptor_list` with `CON_PLAYING`; `\n\r`.
- `cmd_qmconfig` verified; added test for `"I have no clue..."` fallback.
- `wiznet()` broadcast now iterates `descriptor_list` in production.
- `do_load` syntax messages have `\n\r`; re-invokes `do_load("")` on bad arg per ROM.
- `do_mload` returns `"Ok.\n\r"` per ROM; added `wiznet()` broadcast; safe `getattr` for registry.
- `do_oload` returns `"Ok.\n\r"` per ROM; added `wiznet()` broadcast; ROM typo in level message; fixed `char.inventory` slot.
- `do_purge` trust check now uses ROM `<=` comparison; added `"X tried to purge you!\n\r"` to victim; `\n\r`.
- `do_restore` iterates `descriptor_list` for `restore all`; added wiznet broadcasts; `\n\r`.
- `do_clone` added wiznet broadcasts, trust check for mob cloning, `obj.carried_by` check; `\n\r`.
- `do_set`/`do_mset`/`do_oset`/`do_rset`/`do_string` now fully ROM-faithful:
  - Uses `smash_tilde()` for input sanitization per ROM
  - Uses `get_max_train()` for stat ranges instead of hardcoded 25
  - Uses `str_prefix`-style matching (`.startswith()`) for field matching
  - Missing fields added: `class`, `race`, `group`, `hours`, `spec`, `timer`
  - `mset.sex` now sets `pcdata.true_sex` for PCs
  - `mset.hp`/`mana`/`move` now set `pcdata.perm_hit/perm_mana/perm_move` for PCs
  - `mset.security` uses `ch->pcdata->security`-based range check per ROM
  - `mset.level` now rejects PCs per ROM (line 3552-3556)
  - Missing fields from original: `thirst`, `drunk`, `full`, `hunger` (PC-only condition arrays)
  - `mset`/`oset`/`rset`/`string` re-invoke themselves on unknown field per ROM
  - `oset.value0` capped at `min(50, value)` per ROM:3998
  - `oset`/`rset`/`string` use `find_location()` for room lookup per ROM
  - `rset` includes private-room check (`is_room_owner`/`room_is_private`)
  - `string` uses `set_title()` for title setting
  - `string.spec` uses `get_spec_fun()` for spec function lookup
  - `string.long` appends `\n\r` per ROM
  - All messages have `\n\r` line endings
- All modified commands have `\n\r` line endings.

Still outstanding: (none — act_wiz.c fully audited)

Validation:
- `pytest tests/integration/test_act_wiz_command_parity.py -q` — `102 passed` (+27 new tests)
- `pytest tests/integration/test_act_comm_gaps.py::TestPmoteGaps -q` — `5 passed`
- `pytest tests/test_wiznet.py -q` — `32 passed`
- `ruff check` — clean (no F/E9 errors)
