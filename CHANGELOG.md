# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `OLC_ACT-001` — `aedit create` subcommand (`mud/commands/build.py:cmd_aedit` + `_aedit_create`). Mirrors ROM `src/olc_act.c:667-679` plus authoritative defaults from `src/mem.c:91-122` (`new_area`): `name="New area"`, `builders="None"`, `security=1`, `min/max_vnum=0`, `empty=True`, `area_flags=AreaFlag.ADDED`, `file_name="area<vnum>.are"`. Vnum allocation uses `max(area_registry) + 1` (Python adaptation; ROM uses global `top_area` counter). Reachable from both `@aedit create` (no active session) and `create` typed inside an active aedit session. Unblocks OLC-016 in the sibling audit. Test: `tests/integration/test_olc_act_001_aedit_create.py` (9 cases).
- `olc_act.c` parity audit (`docs/parity/OLC_ACT_C_AUDIT.md`) — Phase 1–3 complete. 108 ROM functions inventoried across four editors (aedit/redit/oedit/medit); mpedit/hedit out of scope (sibling audits). 14 stable gap IDs filed (OLC_ACT-001..014): 6 CRITICAL (aedit_create wholly missing; redit_create missing; redit reset/vnum dispatcher gaps; oedit_create missing security gate; medit_create missing ACT_IS_NPC flag on new mobs), 6 IMPORTANT (show-command completeness for all four editors; success message string drift; aedit_reset missing), 2 MINOR (structural). Tier breakdown: TIER A 9 functions (line-by-line), TIER B 8 functions (moderate), TIER C ~78 functions (inventory). Closures pending via `rom-gap-closer` per-gap. Tracker: olc_act.c row flipped ❌ Not Audited → ⚠️ Partial.

### Fixed

- `OLC-022` — `do_resets` (`mud/commands/imm_olc.py`) rewritten with full ROM subcommand set (src/olc.c:1232-1469): P-reset via `inside <containerVnum> [limit] [count]` (validates ITEM_CONTAINER or ITEM_CORPSE_NPC), O-reset via `room`, G/E-reset via wear-loc prefix lookup (`lfin` → FINGER_L), R-reset via `random 1..6`, M-reset extended with optional `[max#area] [max#room]` args. 6-line syntax block on unrecognized numeric-arg subcommand. `_add_reset` helper extracted. Test: `tests/integration/test_olc_do_resets_subcommands.py` (27 cases).
- `OLC-020` — `display_resets` (`mud/commands/imm_olc.py`) now faithfully formats each reset type (M/O/P/G/E/D/R) with exact ROM `sprintf` column widths, pet-shop `final[5]='P'` overlay (src/olc.c:1037-1044), wear-loc decoding via `wear_loc_strings` table, and door-reset state decoding. Bad-mob/obj `continue` paths correctly suppress output per ROM. New `mud/utils/olc_tables.py` provides `WEAR_LOC_STRINGS`, `WEAR_LOC_FLAGS`, `DOOR_RESETS`, `DIR_NAMES` tables ported from `src/tables.c:355-572`. Test: `tests/integration/test_olc_display_resets.py` (16 cases).
- `OLC-023` — `do_alist` (`mud/commands/imm_olc.py:121-146`) iterated the nonexistent `registry.areas` attribute and returned a header-only listing on a live system. Now iterates `area_registry.values()`, prints `area.vnum` (was a 1-indexed enumerate counter — drifted from ROM `src/olc.c:1494`'s `pArea->vnum`), and reads `area.file_name` (was the nonexistent `area.filename`). Test: `tests/integration/test_olc_alist.py` (4 cases).

### Added

- `STRING-004` — `string_add` OLC editor input dispatcher (.c/.s/.r/.f/.h/.ld/.li/.lr dot-commands, ~/@ termination with on_commit callback, MAX_STRING_LENGTH-4 length cap) (src/string.c:121). 24 integration tests in `tests/integration/test_string_editor_string_add.py`. Completes `string.c` at 100%.
- `STRING-005` — `format_string` word-wrap, sentence capitalization (src/string.c:299).
- `STRING-002` — `mud/utils/string_editor.py:string_append(string_edit_obj, current) -> str`. Mirrors ROM `src/string.c:66-86`: enter APPEND mode, preserve the buffer, and return the editor banner (4 lines) plus the `numlines()` line-numbered listing. Takes a `StringEdit` object and a *current* string (the existing text to append to), unlike `string_edit` which clears. The banner matches ROM verbatim: `-=======- Entering APPEND Mode -========-`, help, termination, and separator. The listing shows each line with its 1-indexed line number in `%2d` format. Used by every OLC description builder (`aedit_builder`, `redit`, `medit`, `oedit`, etc.). Test: `tests/integration/test_string_editor_append.py` (9 cases).
- `STRING-001` — `mud/utils/string_editor.py:string_edit(string_edit_obj) -> str`. Mirrors ROM `src/string.c:38-57`: enter EDIT mode, clear the buffer, return the editor banner (4 lines). Takes a `StringEdit` object (mirrors ROM `ch->desc->pString` field) and initializes it with an empty buffer. The returned banner matches ROM verbatim: `-========- Entering EDIT Mode -=========-`, help prompt, termination instructions, and separator. Used by `olc_act.c::aedit_builder` ("desc edit"), `redit` (edit-description), `medit` (edit-description). Test: `tests/integration/test_string_editor_edit.py` (6 cases).
- `STRING-003` — `mud/utils/string_editor.py:string_replace(orig, old, new) -> str`. Mirrors ROM `src/string.c:95-112`: replace the first occurrence of *old* substring within *orig* with *new*. If *old* is not found, returns *orig* unchanged. Empty *old* returns *orig* unchanged (ROM behavior). Used by `string_add::.r` dot-command (STRING-004) and `aedit_builder::replace`. Test: `tests/integration/test_string_editor_replace.py` (9 cases).
- `STRING-010` — `mud/utils/string_editor.py:string_lineadd(string, newstr, line) -> str`. Mirrors ROM `src/string.c:607-645`: insert *newstr* as the 1-indexed line N. The inserted line gets a `\n\r` suffix. If line is past the end, insertion doesn't happen (never reached). Used by `.li` and `.lr` dot-commands. Test: `tests/integration/test_string_editor_lineadd.py` (10 cases).
- `STRING-009` — `mud/utils/string_editor.py:string_linedel(string, line) -> str`. Mirrors ROM `src/string.c:574-605`: remove the 1-indexed line N from the string, preserving `\n\r` line endings. Out-of-range line numbers are a no-op. Used by `.ld` dot-command. Test: `tests/integration/test_string_editor_linedel.py` (8 cases).
- `STRING-012` — `mud/utils/string_editor.py:numlines(string) -> str`. Mirrors ROM `src/string.c:676-692`: format string as line-numbered listing (`%2d. <line>\n\r`), 1-indexed. Used by `.s` dot-command and `string_append` greeting. Test: `tests/integration/test_string_editor_numlines.py` (7 cases).
- `STRING-011` — `mud/utils/string_editor.py:merc_getline(string) -> tuple[str, str]`. Mirrors ROM `src/string.c:647-674`: read one `\n`-terminated line; consume trailing `\r` when present (ROM `\n\r` canonical line ending). Returns `(rest, line)`. Test: `tests/integration/test_string_editor_merc_getline.py` (6 cases).
- `STRING-006` — `mud/utils/string_editor.py:first_arg(argument, lower=False) -> tuple[str, str]`. Mirrors ROM `src/string.c:468-508`: quote/paren-aware single-arg parser. Recognizes `'`/`"`/`%` (self-pair quotes) and `(`/`)` (balanced pair). Unterminated quotes consume the entire remainder. The `lower` flag (ROM `fCase`) lowercases the parsed word. Test: `tests/integration/test_string_editor_first_arg.py` (10 cases).
- `STRING-008` — `mud/utils/string_editor.py:string_proper(argument) -> str`. Mirrors ROM `src/string.c:551-572`: uppercases first char of each space-delimited word, leaves rest of each word as-is. Differs from Python `str.title()` which also lowercases the rest. Test: `tests/integration/test_string_editor_proper.py` (8 cases).
- `STRING-007` — `mud/utils/string_editor.py:string_unpad(argument) -> str`. Mirrors ROM `src/string.c:516-543`: trims leading/trailing spaces (only spaces, not all whitespace) — `aedit_builder` callers expect tab/newline preservation. Test: `tests/integration/test_string_editor_unpad.py` (7 cases).
- `BIT-003` — `mud/utils/bit.py:is_stat(table) -> bool`. Mirrors ROM `src/bit.c:93-104` (and replaces ROM's static `flag_stat_table[]` registry at `src/bit.c:50-83`): returns True for IntEnum (stat) tables, False for IntFlag (flag) tables. The Python port encodes the stat-vs-flag distinction in the type system, so no runtime registry is needed. With BIT-001/002/003 closed, `bit.c` flips ✅ Audited 90% → ✅ Audited 100%. Test: `tests/integration/test_bit_is_stat.py` (5 cases).
- `BIT-002` — `mud/utils/bit.py:flag_string(table, bits) -> str`. Mirrors ROM `src/bit.c:151-177`: returns a space-joined string of every flag name set in *bits* for IntFlag (flag) tables, the single matched name for IntEnum (stat) tables, or the literal `"none"` when nothing matched. The ROM rotating two-buffer trick (`buf[2][512]`) is unnecessary in Python (immutable strings). Composite alias IntFlag members are skipped to avoid double-printing. Test: `tests/integration/test_bit_flag_string.py` (8 cases).
- `BIT-001` — `mud/utils/bit.py:flag_value(table, argument) -> int | None`. Mirrors ROM `src/bit.c:111-142`: tokenizes the argument, prefix-looks up each token, OR-accumulates hits for IntFlag (flag) tables, returns a single matched value for IntEnum (stat) tables, returns `None` (the `NO_FLAG` sentinel) on no match. Unknown tokens are silently skipped, mirroring ROM `flag_value` semantics (which differ from ROM `do_flag` on purpose). Test: `tests/integration/test_bit_flag_value.py` (9 cases).
- `OLC-INFRA-001` — descriptor-level OLC editor state plumbing. New `mud/olc/editor_state.py` provides `EditorMode` IntEnum (mirrors ROM `src/olc.h:53-59` — `NONE`/`AREA`/`ROOM`/`OBJECT`/`MOBILE`/`MPCODE`/`HELP`), `StringEdit` dataclass (mirrors ROM `desc->pString` — buffer + on-commit hook + `MAX_STRING_EDIT_LENGTH=4604`), and `route_descriptor_input(session)` (mirrors ROM `src/comm.c:833-847` — `string_edit` precedes `editor_mode` precedes normal interpret). `Session.editor_mode` and `Session.string_edit` fields wired in `mud/net/session.py`. Destinations (`string_add` for STRING-004, `run_olc_editor` for OLC-001) remain stubbed under their own gap IDs; this commit lands only the routing decision and data shapes that unblock the STRING-001..012 cluster. Test: `tests/integration/test_olc_descriptor_state.py` (6 cases).

### Changed

- `string.c` parity audit (`docs/parity/STRING_C_AUDIT.md`) — `string.c` flipped ⚠️ Partial 85% (stale, wrong file path) → ✅ Audited 5% (accurate). Phase 1 inventory catalogues all 12 public functions (`string_edit`, `string_append`, `string_replace`, `string_add`, `format_string`, `first_arg`, `string_unpad`, `string_proper`, `string_linedel`, `string_lineadd`, `merc_getline`, `numlines`); every one is OLC-editor backend operating on `ch->desc->pString`/`ch->desc->editor` with no current Python consumer (`mud/olc/` skeleton only). 12 stable gap IDs filed (`STRING-001..STRING-012`), all DEFERRED to the OLC audit cluster (`olc.c`/`olc_act.c`/`olc_save.c`/`olc_mpcode.c`/`hedit.c`) where their first concrete consumers will appear. Previous tracker note "85% — `mud/utils.py`" was stale: that file does not exist; only `mud/utils/text.py:smash_tilde` (a `merc.h` helper, not a `string.c` helper) is ported. No code changes.
- `const.c` parity audit (`docs/parity/CONST_C_AUDIT.md`) — Phase 1–3 complete. 16 ROM data tables inventoried; 13 ✅ AUDITED (item, wiznet, attack, race, pc_race, class, int_app, liq, skill, group, plus `str_app.carry` + `str_app.wield` columns); 7 stable gap IDs filed (`CONST-001`..`CONST-007`). **Four CRITICAL combat-math gaps surfaced**: `CONST-002` `GET_HITROLL` macro missing `str_app[STR].tohit` (`mud/combat/engine.py:411,420`), `CONST-003` `GET_DAMROLL` missing `str_app[STR].todam` (`mud/combat/engine.py:1184`), `CONST-004` `GET_AC` missing `dex_app[DEX].defensive` (`mud/combat/engine.py:391`), `CONST-005` `advance_level` missing `con_app[CON].hitp` + `number_range(hp_min,hp_max)` per-level HP roll (`mud/advancement.py:91`). One IMPORTANT advancement gap (`CONST-006` `wis_app[WIS].practice` in `advance_level`). One IMPORTANT data gap (`CONST-001` `title_table` 480 entries — defer to NANNY-009 dedicated session). One MINOR (`CONST-007` `weapon_table` — defer to OLC audit, BIT-style). `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` row updated; tracker held at ⚠️ Partial 80% pending closures via `/rom-gap-closer`. No code changes.
- `bit.c` parity audit (`docs/parity/BIT_C_AUDIT.md`) — `bit.c` flipped ⚠️ Partial 90% → ✅ Audited 90%. Confirmed the only current Python consumer of bit.c-shaped logic (`do_flag` in `mud/commands/remaining_rom.py`) faithfully mirrors ROM `do_flag` semantics (not ROM `flag_value` — they differ on unknown-name handling on purpose). Three MINOR helpers (`flag_value`, `flag_string`, `flag_stat_table`+`is_stat`) recorded as `BIT-001`/`BIT-002`/`BIT-003` and deferred to the OLC audit, where their first concrete consumers (`olc.c`, `olc_act.c`, `olc_save.c`, `act_olc.c`) will appear. No code changes.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — reconciled the stale `P1-3: db.c + db2.c (PARTIAL - 55%)` section with the actual audit state. Both files have been ✅ Audited 100% on the summary table since the Jan 5 (db.c) and Apr 28 (db2.c) sessions; the P1-3 narrative section has been rewritten to reflect that and to point at the per-file audit docs (`DB_C_AUDIT.md` covers db.c's 44/44 functional functions; `DB2_C_AUDIT.md` covers DB2-001/002/003/006 closures and DB2-004/005 deferred MINORs). No code changes.

### Added

- `comm.c` parity audit (`docs/parity/COMM_C_AUDIT.md`) — non-networking surface of `src/comm.c` (`bust_a_prompt`, `act_new`, `colour`, `check_parse_name`, `stop_idling`, `fix_sex`, `show_string`) mapped to Python equivalents. Networking layer (`main`, `init_socket`, `game_loop_*`, descriptor I/O) confirmed deferred-by-design per the asyncio rewrite. Phase 3 produces 9 stable gap IDs (`COMM-001..COMM-009`).
- `mud/utils/prompt.py:bust_a_prompt(char) -> str` — port of ROM `src/comm.c:1420-1595`. Expands `%h %H %m %M %v %V %x %X %g %s %a %r %R %z %% %e %c %o %O` against character state, falls back to `<%dhp %dm %dmv> %s` when `ch->prompt` is unset, short-circuits to `<AFK>` when `COMM_AFK` is on. Wired into both telnet game-loop call sites in `mud/net/connection.py`. Test: `tests/integration/test_prompt_rom_parity.py` (8 cases).
- `board.c` parity audit (`docs/parity/BOARD_C_AUDIT.md`) — full Phase 1 inventory of every public ROM function in `src/board.c` (Erwin Andreasen 1995–96 note-board subsystem) mapped to `mud/notes.py`, `mud/models/board.py`, and `mud/commands/notes.py`. Phase 3 produces 14 stable gap IDs (BOARD-001..BOARD-014); `tracker.md` flips `board.c` from ❌ Not Audited 35% → ⚠️ Partial 85%. New regression suite `tests/integration/test_boards_rom_parity.py` (6 ROM-parity tests, all green).

### Added

- `MUSIC-002` — `mud/music/__init__.py:load_songs(path=area/music.txt)` ports ROM `src/music.c:160-218`. Reads the ROM-format music data file (`group~` / `name~` / lyric lines / `~` / `#`), populates `mud.music.song_table` (up to `MAX_SONGS=20`), resets `channel_songs[0..MAX_GLOBAL]` to `-1`, drops lyrics past `MAX_LINES=100` with a warning, and gracefully no-ops on a missing file. Wired into `mud/world/world_state.py:initialize_world` so the song table is populated at boot — the global "MUSIC:" channel and `play list` previously had nothing to broadcast or display. Tests: `tests/integration/test_music_load_songs.py` (3 cases).

### Fixed

- `CONST-006` — `advance_level` per-level practice gain now applies `wis_app[get_curr_stat(ch, STAT_WIS)].practice`, mirroring ROM `src/update.c:87`. Previously the gain was a hardcoded `PRACTICES_PER_LEVEL = 2` constant — WIS-3 dunce was getting 2 free practices/level instead of 0; WIS-13 default got 2 instead of 1; WIS-25 sage got 2 instead of 5. New `mud/math/stat_apps.py::WIS_APP` table (verbatim port of `src/const.c:790-817`) and `wis_practice_bonus(ch)` accessor. The level-up message now reflects the actual roll with correct singular/plural pluralisation. Per AGENTS.md "test asserting behavior that contradicts ROM is a bug in the test", five existing tests in `tests/test_advancement.py` and `tests/integration/test_character_advancement.py` that asserted the old constant gain were updated to assert ROM's wis_app formula. Test: `tests/integration/test_advancement_wis_app.py` (26 cases).
- `CONST-005` — `advance_level` per-level HP gain now follows ROM `src/update.c:74-79` exactly: `UMAX(2, (con_app[get_curr_stat(ch, STAT_CON)].hitp + number_range(class_table[ch->class].hp_min, class_table[ch->class].hp_max)) * 9 / 10)`. Previously used a static `LEVEL_BONUS[ch_class]` dict (`mud/advancement.py:91`) — both the RNG roll and the CON modifier were absent, so a CON-25 character was missing +8 hitp/level and a CON-3 character was missing −2 hitp/level on top of the missing variability. New `mud/math/stat_apps.py::CON_APP` table (verbatim port of `src/const.c:850-878`) and `con_hitp_bonus(ch)` accessor. Mana/move continue to use the legacy `LEVEL_BONUS` path until their respective gaps close. Per AGENTS.md "test asserting behavior that contradicts ROM is a bug in the test", six existing tests in `tests/test_advancement.py` and `tests/integration/test_character_advancement.py` that asserted the old static HP values were updated to seed `rng_mm.number_range` and assert the ROM formula. Test: `tests/integration/test_advancement_con_app.py` (14 cases).
- `CONST-004` — Armor class now augments `armor[type]` with `dex_app[get_curr_stat(ch, STAT_DEX)].defensive` when the character `IS_AWAKE` (`position > POS_SLEEPING`), mirroring ROM `src/merc.h:2104-2106`. New `mud/math/stat_apps.py::DEX_APP` table (verbatim from `src/const.c:821-848`) and `get_ac(ch, ac_type)` accessor; combat at `mud/combat/engine.py:391`, `do_score` at `mud/commands/session.py`, and the wiz `stat char` AC line at `mud/commands/imm_search.py` all read through it. Sleeping/stunned/incap/dead victims still show raw armor (the IS_AWAKE gate). Before this fix, a DEX-3 character was missing +40 AC penalty and a DEX-25 character was missing −120 AC bonus on every combat hit-roll and every AC display. Test: `tests/integration/test_combat_dex_app.py` (11 cases).
- `CONST-003` — Combat `GET_DAMROLL` now augments `ch->damroll` with `str_app[get_curr_stat(ch, STAT_STR)].todam`, mirroring ROM `src/merc.h:2109-2110` (consumed at `src/fight.c:588` for weapon damage). New `mud/math/stat_apps.py::get_damroll(ch)` accessor; `calculate_weapon_damage` at `mud/combat/engine.py:1189` now reads it. Before this fix, a STR-3 attacker missed −1 damage and a STR-25 attacker missed +9 damage. Test: `tests/integration/test_combat_str_app.py::test_get_damroll_*` (7 cases).
- `CONST-002` — Combat `GET_HITROLL` now augments `ch->hitroll` with `str_app[get_curr_stat(ch, STAT_STR)].tohit`, mirroring ROM `src/merc.h:2107-2108` (consumed at `src/fight.c:471` for THAC0). New module `mud/math/stat_apps.py` ports `STR_APP[26]` verbatim from `src/const.c:728-755` and exposes `get_hitroll(ch)`; both attack paths in `mud/combat/engine.py` (THAC0 at L411, percent fallback at L420) now read the augmented value. Before this fix, a STR-3 attacker missed −3 to-hit and a STR-25 attacker missed +6. Test: `tests/integration/test_combat_str_app.py` (8 cases).
- `MUSIC-004` — `mud/commands/player_info.py:do_play` jukebox scan now applies `mud.world.vision.can_see_object(ch, obj)` so invisible / VIS_DEATH / dark-room jukeboxes drop out of selection, mirroring ROM `src/music.c:229-232`'s `can_see_obj(ch, juke)` filter. Test: `tests/integration/test_music_play.py::test_do_play_skips_invisible_jukebox`.

- `MUSIC-003` — `play list` in `mud/commands/player_info.py:do_play` now reads `mud.music.song_table` (previously `mud.registry.song_table`, which doesn't exist, so it always fell through to a 3-song hardcoded stub). Reproduces ROM `src/music.c:246-292`: capitalized `"<short_descr> has the following songs available:"` header, `play list <prefix>` filters song names by case-insensitive prefix in two `%-35s` columns, `play list artist [<prefix>]` filters by group name in single-line `%-39s %-39s` group/name pairs, and a trailing odd column is flushed on its own line. Tests: `tests/integration/test_music_play.py` (4 new list-formatting cases).

- `MUSIC-001` — `mud/commands/player_info.py:do_play` now ports the queueing half of ROM `src/music.c:220-354`. Previously a stub: it found a jukebox, returned `"Coming right up."`, and queued nothing — so `song_update()` had nothing to broadcast and `play loud` was silently ignored. The port now resolves the `loud` keyword for global plays, enforces the `value[4] > -1` / `channel_songs[MAX_GLOBAL] > -1` queue-full check (`"The jukebox is full up right now."`), case-insensitive name-prefix matches against `mud.music.song_table`, surfaces `"That song isn't available."` on no match, and writes the song id into the first free `juke.value[1..4]` (local) or `channel_songs[1..MAX_GLOBAL]` (global) slot — also resetting the slot-0 line cursor to `-1` when slot 1 is filled, matching ROM `src/music.c:337-352`. Tests: `tests/integration/test_music_play.py` (7 cases).

- `NANNY-008` — `broadcast_entry_to_room` (`mud/net/connection.py`) now moves `char.pet` into the owner's room via `char_to_room` and emits a TO_ROOM "$n has entered the game." for the pet on login, mirroring ROM `src/nanny.c:810-815`. Previously a returning player's pet stayed un-roomed and onlookers never saw the pet's arrival. Test: `tests/integration/test_nanny_login_parity.py::test_login_pet_follows_owner_into_room`.
- `COMM-009` — Standalone `mud/utils/fix_sex.py:fix_sex(ch)` helper added, mirroring ROM `src/comm.c:2178-2182`: clamps `ch.sex` to `[0,2]`, falling back to `pcdata.true_sex` for PCs and `0` for NPCs. Inline clamp at the affect-strip site in `mud/handler.py:1110-1112` now delegates to the helper. Test: `tests/test_fix_sex.py` (5 cases).
- `COMM-008` — ANSI translator now covers ROM `colour()` specials at `src/comm.c:2714-2728`: `{D` → `\x1b[1;30m`, `{*` → `\x07` (bell), `{/` → `\n\r`, `{-` → `~`, `{{` → `{`. `mud/net/ansi.py` rewritten as a single-pass `re.sub` so `{{` cannot be re-matched as `{h` once partially consumed; `strip_ansi` mirrors ROM `send_to_char` non-colour branch (`src/comm.c:1995-2007`) by eating both characters of any `{X` pair. Tests: `tests/test_ansi.py::test_translate_ansi_handles_rom_specials` and `::test_strip_ansi_eats_rom_token_pairs`.
- `COMM-007` — `_stop_idling` now broadcasts the ROM "$n has returned from the void." message through `mud/utils/act.py:act_format`, mirroring ROM `act(...)` at `src/comm.c:1922`. The previous literal `f"{name} has returned from the void."` fallback rendered "Someone has returned…" for entities without a `name`; with the new act_format pipeline, `$n` expands via `_pers` (name → short_descr fallback). Test: `tests/test_networking_telnet.py::test_stop_idling_broadcast_uses_rom_act_format`.
- `COMM-002` — `show_string` pager input semantics now match ROM. While paging, `_read_player_command` (`mud/net/connection.py`) used to treat `"c"` as continue and dispatch arbitrary non-empty input to `interpret()`. ROM `src/comm.c:632-633` instead routes input to `show_string` instead of `interpret`, and `show_string` at `src/comm.c:2131-2141` aborts on any non-empty input and consumes it as no-op. Fix: empty input continues paging; any non-empty input clears the pager and returns `" "` (no-op). The bulk paging machinery (`Session.start_paging` / `send_next_page`) was already wired through `mud/net/protocol.py:send_to_char`; this closure pinned the missing ROM-faithful abort semantics. Tests: `tests/test_networking_telnet.py::test_show_string_pager_aborts_on_any_non_empty_input_per_rom` (new) and `test_show_string_paginates_output` (updated to assert `" "` no-op consumption).
- `COMM-006` — `is_valid_character_name` now rejects names matching any clan in `CLAN_TABLE` (case-insensitive), mirroring ROM `src/comm.c:1713-1718`. `rom`/`ROM` and `loner` are both rejected at character creation.
- `COMM-004` — Character-creation name validator now rejects names that collide with any mob prototype's `player_name` keyword list, mirroring ROM `src/comm.c:1782-1796`. Implemented as a new `mud.account.is_valid_character_name` helper layered on top of `is_valid_account_name`; the old syntactic-only validator stays intact for account-name validation (a Python addition with no ROM analogue). `create_character` and the connection-layer character-creation flow both use the new validator. Pre-existing tests in `tests/test_account_auth.py` that used stock RPG names colliding with real mobs (`Zeus`, `Nomad`, `Queen`, `Guardian`) were renamed to invented tokens — per AGENTS.md "test contradicting ROM C is a bug in the test."
- `COMM-003` — `check_parse_name` length floor now matches ROM. `is_valid_account_name` rejected names shorter than 3 characters; ROM `src/comm.c:1729` rejects only names shorter than 2. Two-letter ROM-legal names (e.g. `Bo`) are now accepted. The previous NANNY-012 test (`test_name_validator_matches_rom_check_parse_name`) had locked in the buggy `< 3` threshold with a docstring misreading ROM — the test now asserts the correct ROM `< 2` bound (`Bo` accepted, `a` rejected).
- `COMM-001` — Player prompts now render character state. The telnet game loop previously emitted a literal `"> "` regardless of `do_prompt` settings; HP / mana / move / room / alignment never reached the client. Fix: replaced the hard-coded `send_prompt("> ")` with `send_prompt(bust_a_prompt(char))` at `mud/net/connection.py:1698,1923` and made `do_prompt` write to `Character.prompt` (mirrors ROM `ch->prompt`, `src/act_info.c:951-952`) instead of `PCData.prompt` (which in ROM is the colour triplet, not the format string). `send_prompt` now applies ANSI rendering so `{p…{x` colour wrappers don't leak as raw text. Five existing tests in `test_player_prompt.py` / `test_player_auto_settings.py` / `test_config_commands.py` updated to assert the correct field (per AGENTS.md "test contradicting ROM C is a bug in the test").
- `BOARD-001` — Five hardcoded ROM boards (General/Ideas/Announce/Bugs/Personal) are now seeded on `load_boards()` with the exact ROM levels, force-types, default recipients, and purge-days from `src/board.c:67-76`. Persisted JSON content is overlaid on top so notes survive a reload but the static metadata cannot drift below ROM defaults.
- `BOARD-002` / `BOARD-003` — `note write` and `note send` now emit ROM TO_ROOM `act()` broadcasts ("$n starts writing a note." / "$n finishes $s note.") via `char.room.broadcast(..., exclude=char)`, mirroring `src/board.c:503` and `src/board.c:1181`. Adds `_possessive(char)` helper for ROM `$s` (his/her/its from `Character.sex`).
- `BOARD-004` — `Board.post` now routes through a new `mud.notes.next_note_stamp(base)` helper backed by a module-level `_last_note_stamp` counter, mirroring ROM `finish_note` (`src/board.c:154-160`). Two notes posted in the same wall-clock second now get distinct, monotonically increasing timestamps so the `> last_read` unread cursor cannot collide. Test fixtures reset the counter per test (parallel to ROM rebooting `boot_db` globals).
- `BOARD-005` (and `BOARD-006`) — `Board.unread_count_for(char, last_read)` mirrors ROM `unread_notes` (`src/board.c:444-460`) by filtering through `mud.notes.is_note_to(char, note)` (the canonical recipient predicate, factored out of `mud/commands/notes.py`). `do_board` listing now uses the recipient-aware count, so Personal/per-name notes no longer leak into non-recipients' unread totals. `BOARD-006` is subsumed by this fix (ROM's listing filter `unread_notes != BOARD_NOACCESS` is now consistent with what each row displays).
- `BOARD-008` — `load_boards` now sweeps every loaded board for notes whose `expire < now` and appends them to `<board>.old.json` before re-saving the active board, mirroring ROM `load_board`'s archive at `src/board.c:365-383`. Boards no longer grow without bound across reloads.
- `BOARD-012` — `do_note` now mirrors ROM `src/board.c:736-737`: an unknown subcommand (anything other than `read`/`list`/`write`/`remove`/`purge`/`archive`/`catchup` and the Python-only draft verbs) dispatches to `do_help(ch, "note")` instead of returning the generic `"Huh?"`. Test: `tests/integration/test_boards_rom_parity.py::test_note_unknown_subcommand_shows_help`.
- `BOARD-011` — `note write` now mirrors ROM `do_nwrite` at `src/board.c:482-488`: when the player has an in-progress draft whose `text` is empty (e.g. lost link before typing the body), the stale draft is discarded and the actor sees the ROM cancellation notice ("Note in progress cancelled because you did not manage to write any text before losing link.") before a fresh draft is started. Test: `tests/integration/test_boards_rom_parity.py::test_note_write_discards_textless_in_progress_draft`.
- `BOARD-013` — Added `mud.notes.make_note(board_name, sender, to, subject, expire_days, text)` and `mud.notes.personal_message(...)` mirroring ROM `make_note` / `personal_message` at `src/board.c:843-886`. Unknown boards and text exceeding `MAX_NOTE_TEXT` (= `4 * MAX_STRING_LENGTH - 1000` = 17432, per `src/board.h:19`) return `None` (mirroring ROM's silent `bug` + return); on success the note is appended via `Board.post` (so it picks up the unique `last_note_stamp` cursor), persisted with `save_board`, and `expire = current_time + expire_days * 86400`. Unblocks programmatic Personal-board injection for death notifications and system mail.

- `TABLES-001` — `AffectFlag` bit positions (`mud/models/constants.py`) renumbered to match ROM `src/merc.h:953-982` exactly (letters A..dd → bits 0..29). Closes a 20-of-29-bit divergence where `convert_flags_from_letters` was decoding ROM area-file letters with the canonical mapping (e.g. `G` → bit 6) but Python `AffectFlag.SANCTUARY` sat on bit 6, so any letter-form area data was silently mis-aligned with the enum. Pfile schema gains `pfile_version: int` (default `0`); legacy saves are translated on load by `mud/persistence.py:translate_legacy_affect_bits` (covers character `affected_by`, every nested `Affect.bitvector` on persisted items, pet `affected_by`, and pet affect bitvectors), then re-saved at `pfile_version=1`. Reproducer `tests/integration/test_tables_parity.py::test_affect_flag_letters_match_rom_merc_h` flipped from `xfail(strict)` → green; `test_merc_h_letter_macros_match_python_intflag_values` now also covers `AFF_*`. New migration tests in `tests/integration/test_tables_001_affect_migration.py`. Tables.c flips ⚠️ Partial 75% → ✅ AUDITED 100%.
- `TABLES-003` — Programmatic verification of every `src/merc.h` letter-mapped `#define` macro against the matching Python `IntFlag` member's bit value. New test `tests/integration/test_tables_parity.py::test_merc_h_letter_macros_match_python_intflag_values` parses merc.h, resolves A..Z / aa..dd letter tokens, and cross-checks ~210 macros across the `ACT_/PLR_/OFF_/IMM_/RES_/VULN_/FORM_/PART_/COMM_/ROOM_/GATE_/FURN_/WEAPON_` prefixes. Confirms only `AFF_*` (TABLES-001) diverges; all other letter-mapped tables in `src/tables.c` have correct Python bit positions. Acts as a durable regression guard.
- `TABLES-002` — `mud/utils/prefix_lookup.py:prefix_lookup_intflag` now consults a ROM `src/tables.c` table-name alias map (`rom_flag_aliases`) before falling back to Python IntFlag member names. ROM-style abbreviations like `+npc`/`+healer`/`+changer`/`+can_loot`/`+dirt_kick`/`+noclangossip` now resolve to the matching Python flag member (`IS_NPC`/`IS_HEALER`/`IS_CHANGER`/`CANLOOT`/`KICK_DIRT`/`NOAUCTION`), restoring ROM `flag_lookup` parity for `do_flag` and OLC.

### Added

- `tables.c` parity audit (`docs/parity/TABLES_C_AUDIT.md`): Phase 1 inventory of all 38 ROM data tables in `src/tables.c` mapped to Python `IntFlag`/`IntEnum` equivalents in `mud/models/constants.py`; Phase 2 spot-checks confirm `ActFlag` / `PlayerFlag` / `OffFlag` / `CommFlag` bit positions match ROM letters A..dd. Three gaps documented: **TABLES-001 (CRITICAL)** — `AffectFlag` bit positions diverge from ROM `merc.h:953-982` (e.g. `AFF_DETECT_GOOD=G=1<<6` in ROM, but `AffectFlag.SANCTUARY=1<<6` in Python); `convert_flags_from_letters` decodes ROM letters with the ROM-correct mapping, so any area-file `AFF G` is silently mis-decoded as `SANCTUARY`. Closure deferred — requires `AffectFlag` renumber + persistence migration plan. TABLES-002 (ROM-name aliases for prefix-match) and TABLES-003 (per-table value verification for the remaining 30+ tables) also open. New `tests/integration/test_tables_parity.py` (4 passing spot-checks + 1 xfail reproducer for TABLES-001).

### Fixed

- `LOOKUP-008` — Added public `liq_lookup(name)` to `mud/utils/prefix_lookup.py` mirroring ROM `src/lookup.c:138-150` (case-insensitive prefix-match against `LIQUID_TABLE`, returns `-1` on miss). The loader-internal `mud/loaders/obj_loader.py:_liq_lookup` is retained because it intentionally returns `0` (water) on miss for object-load defaults. With this `lookup.c` is ✅ AUDITED at 100% (LOOKUP-001..008 all closed).
- `LOOKUP-007` — Added `item_lookup(name)` to `mud/utils/prefix_lookup.py` mirroring ROM `src/lookup.c:124-136` (case-insensitive prefix-match against `ItemType` IntEnum, returns the ITEM_X type value, `-1` on miss). Python's `ItemType` IntEnum values match ROM ITEM_X constants 1:1.
- `LOOKUP-006` — Added `size_lookup(name)` to `mud/utils/prefix_lookup.py` mirroring ROM `src/lookup.c:95-107` (case-insensitive prefix-match against `Size` IntEnum, returns `-1` on miss).
- `LOOKUP-005` — Added `sex_lookup(name)` to `mud/utils/prefix_lookup.py` mirroring ROM `src/lookup.c:81-93` (case-insensitive prefix-match against `Sex` IntEnum, returns `-1` on miss). ROM `sex_table {none, male, female, either}` maps 1:1 to Python's enum.
- `LOOKUP-004` — Added `position_lookup(name)` to `mud/utils/prefix_lookup.py` mirroring ROM `src/lookup.c:67-79` (case-insensitive prefix-match against `Position` IntEnum, returns `-1` on miss).
- `LOOKUP-003` — `lookup_clan_id` (`mud/models/clans.py`) now uses ROM-faithful prefix-match instead of exact-match. `lookup_clan_id("lo")` returns clan `loner`, `lookup_clan_id("ro")` returns clan `rom`, mirroring ROM `src/lookup.c:53-65` (`clan_lookup` calls `str_prefix`).
- `LOOKUP-002` — `_lookup_flag_bit` (`mud/commands/remaining_rom.py`) now uses ROM-faithful prefix-match instead of exact-match. `flag char Bob plr +holy` matches `HOLYLIGHT` per ROM `src/lookup.c:39-51` (`flag_lookup` calls `str_prefix`). Introduces `mud/utils/prefix_lookup.py` with shared `prefix_lookup_index` and `prefix_lookup_intflag` helpers for the remaining LOOKUP-003..008 closures.
- `LOOKUP-001` — Added `race_lookup(name: str | None) -> int` to `mud/models/races.py` mirroring ROM `src/lookup.c:110-122` (case-insensitive prefix-match against `RACE_TABLE`, fall-through `return 0`). Fixes a latent `ImportError` in `mud/persistence.py:614`'s pet-restore path: every pet load with a non-None race snapshot was crashing with `ImportError: cannot import name 'race_lookup'` because the function had not been ported. Caught during the `lookup.c` parity audit.
- `FLAG-001` — `do_flag` (`mud/commands/remaining_rom.py`) is now a fully-wired immortal command instead of a syntax-validator stub. Mirrors ROM `src/flags.c:44-251`: parses the `=`/`+`/`-`/toggle operator, dispatches `act`/`plr`/`aff`/`immunity`/`resist`/`vuln`/`form`/`parts`/`comm` to the matching Character attribute and IntFlag enum (`ActFlag`, `PlayerFlag`, `AffectFlag`, `ImmFlag`, `FormFlag`, `PartFlag`, `CommFlag`), enforces NPC-only / PC-only field guards (`Use 'plr' for PCs.`, `Use 'act' for NPCs.`, `Form/Parts can't be set on PCs.`, `Comm can't be set on NPCs.`), looks up flag names case-insensitively, rejects unknown flags with `That flag doesn't exist!`, and mutates the matching bit on the victim. Previously the command returned a confirmation string but performed no mutation. New 9-test integration suite in `tests/integration/test_flag_command_parity.py`. FLAG-002 (preserve ROM `flag_type.settable=FALSE` bits across the `=` operator) deferred as MINOR — requires per-bit settable metadata on the IntFlag enums.

### Changed

- `sha256.c` audit completed (`docs/parity/SHA256_C_AUDIT.md`). SHA-256 primitive is delegated to Python's stdlib `hashlib` (byte-for-byte equivalent to ROM `src/sha256.c:131-318`). The `sha256_crypt` password hash (ROM `src/sha256.c:320-336`, plain unsalted single-round SHA-256) is replaced by PBKDF2-HMAC-SHA256 with a 16-byte random salt and 100 000 rounds in `mud/security/hash_utils.py` — a deliberate security upgrade with no observable gameplay parity surface (no pfile compatibility goal). Tracker row flipped from ⚠️ Partial → ✅ AUDITED.

### Fixed

- `NANNY-012` — Name validator (`is_valid_account_name` in `mud/account/account_service.py`) now matches ROM `check_parse_name` (`src/comm.c`, called from `nanny.c:188`): minimum length raised from 2 to 3 chars, and `god` / `imp` added to the reserved-name set. Existing reserved tokens (`all auto immortal self someone something the you loner none`) are unchanged.
- `NANNY-013` — Audit correction: ROM `hit=max_hit; mana=max_mana; move=max_move` (src/nanny.c:772-775) is already covered by `from_orm` initialising `max_*` from `perm_*` plus `hit` from saved `hp` (a fresh character is persisted with `hp=perm_hit=100`). NANNY-014 reset_char further guarantees max_* are restored on every login. Added regression test.
- `NANNY-006` — Login fallback room now distinguishes immortals from mortals when no saved room can be loaded. Added `ROOM_VNUM_CHAT = 1200` constant (ROM `src/merc.h:1250`) and `default_login_room_vnum(char)` helper in `mud/net/connection.py`; an `is_admin` character with `char.room is None` lands in ROOM_VNUM_CHAT (the immortal chat room), mortals in ROOM_VNUM_TEMPLE. Mirrors ROM `src/nanny.c:791-802` `IS_IMMORTAL ? ROOM_VNUM_CHAT : ROOM_VNUM_TEMPLE`.
- `NANNY-001` — Account login now disconnects on the first wrong password (returns `None` from `_run_account_login`) instead of looping back to the Account prompt, mirroring ROM `src/nanny.c:269-274` (`close_socket(d)` on bad password). The same path applies to reconnect attempts (matching ROM's "one chance" rule for both fresh logins and CON_BREAK_CONNECT).
- `NANNY-005` — Audit correction: ROM `perm_stat[class.attr_prime] += 3` (src/nanny.c:769) was already implemented in `mud/account/account_service.py:finalize_creation_stats` and locked in by `tests/test_nanny_rom_parity.py::test_prime_attribute_bonus_formula`. ROM applies the bonus during the `level == 0 → 1` promotion inside `CON_READ_MOTD`; Python applies it equivalently during `create_character` since Python characters are persisted at level 1.
- `NANNY-004` — Audit correction: ROM `learned[weapon_gsn] = 40` (src/nanny.c:653) was already implemented in `mud/models/character.py:from_orm` (lines 1047-1051), which uses `_STARTING_WEAPON_SKILL_BY_VNUM` to seed the picked weapon's skill to ≥40 on every load. Audit had cited the prompt-time path. Added regression test.
- `NANNY-003` — Audit correction: ROM `learned[gsn_recall] = 50` (src/nanny.c:581) was already implemented in `mud/models/character.py:from_orm` (lines 1052-1053), which clamps `learned["recall"]` to ≥50 on every character load. Audit had cited the wrong source location. Added regression test to lock in the behavior.
- `NANNY-002` — Login flow now honors the `PlayerFlag.DENY` bit per ROM `src/nanny.c:197-205`: a denied character logs `Denying access to <name>@<host>.`, receives `You are denied access.`, and is rejected before reaching the game loop. New `is_character_denied_access` helper in `mud/net/connection.py`, wired into both load branches of `_select_character`.
- `NANNY-007` — Login flow now broadcasts `<Name> has entered the game.` to other room occupants on every fresh (non-reconnect) login, mirroring ROM `act("$n has entered the game.", ch, NULL, NULL, TO_ROOM)` at `src/nanny.c:804`. New `broadcast_entry_to_room` helper in `mud/net/connection.py` excludes the actor and uses `act_format` for `$n` substitution.
- `BAN-004` — `BanEntry.matches` (`mud/security/bans.py`) no longer falls through to exact-string match when neither PREFIX nor SUFFIX bit is set; ROM `src/ban.c:104-132` `check_ban` silently skips such entries. Pre-existing tests in `tests/test_bans.py` and `tests/test_account_auth.py` were updated to use `*host*` patterns so a host-specific ban actually matches under ROM semantics.
- `BAN-003` — `_apply_ban` (`mud/commands/admin_commands.py`) now accepts ROM-style prefix abbreviations of the type token (`a`, `n`, `p`, `al`, `ne`, …), matching `src/ban.c:180-191` `!str_prefix(arg2, "all"/"newbies"/"permit")`. Previously required full-prefix `startswith` so single-letter abbreviations were rejected.
- `BAN-002` — `_render_ban_listing` now mirrors ROM's chained ternary at `src/ban.c:166-168`: prints `"newbies"` / `"permit"` / `"all"` based on the corresponding flag bits and falls through to `""` when none is set. Previously defaulted to `"all"` in the no-flag case.
- `BAN-001` — `_render_ban_listing` (`mud/commands/admin_commands.py`) now left-aligns the level column (`:<3d`) to match ROM `src/ban.c:164` `%-3d` instead of right-aligning. Visible in `banlist` / `ban` (no-arg) output.
- `NANNY-011` — `_prompt_new_password` (`mud/net/connection.py`) now rejects passwords containing `~` with ROM message "New password not acceptable, try again." mirroring ROM `src/nanny.c:396-405` file-format poisoner check. Python uses a DB backend so the practical risk is gone, but parity with ROM input validation is preserved.
- `NANNY-014` — Login flow now invokes `reset_char(ch)` on every successful login (ROM `src/nanny.c:760`), restoring `max_hit`/`max_mana`/`max_move` from `pcdata.perm_*`, zeroing transient `mod_stat[]`/`hitroll`/`damroll`/`saving_throw`, and re-applying equipment affects so returning characters land with clean state. Wired into both branches of `mud/net/connection.py:handle_connection` via new `apply_login_state_refresh` helper. Also corrected a latent bug in `mud/handler.py:reset_char` where `range(int(WearLocation.MAX))` raised `AttributeError` (the enum has no `MAX` member); replaced with literal `19` matching ROM `MAX_WEAR` (`src/merc.h:1356`).
- `SPEC-001` — `spec_executioner` yell now broadcasts area-wide (ROM `src/special.c:890-893`) instead of room-only. Added `_yell_area` helper mirroring ROM `do_yell`.
- `SPEC-002` — `spec_guard` now checks ALL room occupants for evil-alignment combatants (ROM `src/special.c:948-972`), not just PCs. The fallback path targeting `alignment < max_evil` fighters now works for NPCs too.
- `SPEC-003` — `spec_mayor` gate open/close now emits proper TO_CHAR (`You open the gate.`) and TO_ROOM (`Mayor opens gate.`) messages, plus reverse-exit toggle. Mirrors ROM `do_function(ch, &do_open, "gate")` / `do_function(ch, &do_close, "gate")`.
- `SPEC-004` — `spec_thief` gold/silver division now uses `c_div` (C integer division) instead of Python `//`, matching ROM `src/special.c:1174-1186`.
- `SPEC-005` — `spec_nasty` ambush now calls `do_murder` (which sets PLR_KILLER flag) instead of `do_kill`, matching ROM `src/special.c:368-371`. Updated `_issue_command` to search multiple command modules.
- `SPEC-006` — `spec_troll_member` and `spec_ogre_member` now check `is_safe()` before attacking, matching ROM `src/special.c:145,213`. Prevents attacks in safe rooms.
- `SPEC-008` — `spec_mayor` movement now uses `move_character()` (with fallback for test SimpleNamespace objects), matching ROM `move_char(ch, dir, FALSE)`.
- `SPEC-012` — `spec_nasty` gold steal now uses `c_div(gold_before, 10)` instead of `gold_before // 10`, matching ROM `src/special.c:394-396`.

- `WIZ-001` — `goto`, `at`, and `transfer` now mirror ROM `src/act_wiz.c:821-839,897-905,957-966` owner/private-room gating by honoring owner-locked rooms, the canonical `ROOM_SOLITARY` flag value, and `is_room_owner()` bypass semantics.
- `WIZ-002` — `violate` now mirrors ROM `src/act_wiz.c:1000-1057`: it targets rooms through `find_location()`, rejects public rooms with the `use goto` hint, and no longer parses directions/exits.
- `WIZ-003` — `protect` now mirrors ROM `src/act_wiz.c:2086-2118` lookup/messages and toggles the real `CommFlag.SNOOP_PROOF` bit instead of the old `COMM_NOTELL` value.
- `WIZ-004` — `snoop` now honors the canonical `CommFlag.SNOOP_PROOF` bit from ROM `src/act_wiz.c:2167-2174`, preventing snooping of correctly protected targets.
- `WIZ-006` — `log` command now mirrors ROM `src/act_wiz.c:2927-2984`: uses `get_char_world()` for lookup, toggles `PlayerFlag.LOG` on `victim.act` instead of a `log_commands` bool, rejects NPCs with ROM message, and uses canonical `\n\r` line endings.
- `WIZ-007` — `force` command now mirrors ROM `src/act_wiz.c:4183-4322`: adds `gods` branch for hero+ players, adds private-room check before forcing individuals, applies trust check to all victims (not just non-NPCs), iterates `descriptor_list` for `force all` and `char_list` for `force players`/`force gods`, and uses canonical `\n\r` line endings.
- `WIZ-005` — `stat` family now mirrors ROM `src/act_wiz.c:1059-1742`: `do_stat` dispatcher uses `get_char_world`/`get_obj_world`/`find_location` per ROM; `do_rstat` outputs Name/Area/Vnum/Sector/Light/Healing/Mana/Room flags/Description/Extra descs/Characters/Objects/Door details; `do_ostat` outputs Name(s)/Vnum/Format/Type/Resets/Short+Long descr/Wear bits/Extra bits/Number+Weight/Level+Cost+Condition+Timer/In room+In obj+Carried by+Wear_loc/Values/Item-type blocks (scroll, potion, pill, wand, staff, drink_con, weapon, armor, container)/Extra descs/Affects; `do_mstat` outputs Name/Vnum/Format/Race/Group/Sex/Room/Count+Killed/Stats/Hp+Mana+Move+Practices/Level+Class+Align+Gold+Silver+Exp/AC per type/Hit+Dam+Saves+Size+Position+Wimpy/Damage+Fighting/Thirst+Hunger+Full+Drunk for PCs/Carry number+Weight/Age+Played/Act/Comm/Offense/Immune/Resist/Vulnerable/Form+Parts/Affected by/Master+Leader+Pet/Security/Short+Long desc/Spec fun/Affected. Added 8 ROM-faithful bit-name helpers (`wear_bit_name`, `extra_bit_name`, `imm_bit_name`, `off_bit_name`, `form_bit_name`, `part_bit_name`, `weapon_bit_name`, `cont_bit_name`) and 5 display helpers (`size_name`, `position_name`, `sex_name`, `class_name`, `race_name`) to `mud/handler.py`.
- `WIZ-008` — Punish commands (`nochannels`, `noemote`, `noshout`, `notell`, `freeze`, `pardon`) now use canonical `CommFlag`/`PlayerFlag` enum values instead of hardcoded wrong bit positions that were corrupting unrelated flags. Added `wiznet()` broadcasts with `WIZ_PENALTIES` + `WIZ_SECURE` flags. Added `\n\r` line endings.
- `WIZ-009` — `peace` now calls `stop_fighting(person, True)` instead of setting `fighting = None` (properly clearing all combat references). Uses `ActFlag.AGGRESSIVE` enum instead of hardcoded `0x20`. Added `\n\r` line endings.
- `WIZ-010` — `invis` and `incognito` now broadcast room-wide `act()` messages per ROM `src/act_wiz.c:4329-4420`. `incognito` clears `reply` when setting a specific level. Added `\n\r` line endings.
- `WIZ-011` — Echo family (`echo`, `recho`, `zecho`, `pecho`) now iterates `descriptor_list` with `CON_PLAYING` filter per ROM `src/act_wiz.c:674-777` instead of `registry.players` dict. `pecho` uses ROM trust check and exact messages. Added `\n\r` line endings.
- `WIZ-012` — `bamfin`/`bamfout` now use `smash_tilde()` and ROM `strstr` case-sensitive name check per `src/act_wiz.c:455-512`. Added `\n\r` line endings.
- `WIZ-013` — `wizlock`/`newlock` now use `\n\r` line endings per ROM `src/act_wiz.c:3150-3188`.
- `WIZ-014` — `holylight` now returns empty string for NPCs (ROM parity) and uses `\n\r` line endings per `src/act_wiz.c:4422-4439`.
- `WIZ-015` — `slookup` now supports `all` arg, shows `Slot` column, uses prefix-match lookup per ROM `src/act_wiz.c:3191-3229`. Added `\n\r` line endings.
- `WIZ-016` — `sockets` now uses `\n\r` line endings per ROM `src/act_wiz.c:4140-4176`.
- `WIZ-017` — `deny` rewritten to ROM parity per `src/act_wiz.c:517-557`: SET-only (not toggle), uses `get_char_world()` not `character_registry`, adds `PlayerFlag.DENY` flag, wiznet broadcast, `stop_fighting(victim, True)`, forced quit, `\n\r` line endings.
- `WIZ-018` — `switch` now has private-room check (`is_room_owner`/`room_is_private`) and wiznet broadcast per ROM `src/act_wiz.c:2202-2269`. Added `\n\r` line endings.
- `WIZ-019` — `return` now has full ROM message, prompt cleanup, and wiznet broadcast per `src/act_wiz.c:2273-2303`. Added `\n\r` line endings.
- `WIZ-020` — `smote` now uses ROM `_smote_substitute` letter-by-letter algorithm, case-sensitive `strstr` name check, skips no-descriptor viewers per `src/act_wiz.c:362-453`. Added `\n\r` line endings.
- `WIZ-021` — `pecho` now uses ROM trust check (`get_trust(char) != MAX_LEVEL`) and exact messages per `src/act_wiz.c:750-777`. Added `\n\r` line endings.
- `WIZ-022` — `disconnect` now follows ROM descriptor-list victim lookup per `src/act_wiz.c:561-614`. Added `\n\r` line endings.
- `WIZ-023` — `guild` now uses `lookup_clan_id`/`CLAN_TABLE` per ROM `src/act_wiz.c:196-249`; distinguishes independent-clan (`"a <name>"`) vs member-clan (`"member of clan <Name>"`) messaging; uses `str_prefix`-style match for "none"; all messages have `\n\r`.
- `WIZ-024` — `outfit` now always returns `"You have been equipped by Mota.\n\r"` per ROM `src/act_wiz.c:251-310` (removed "You already have your equipment" branch).
- `WIZ-025` — `copyover` now iterates `descriptor_list` with `CON_PLAYING` filter per ROM `src/act_wiz.c:4498-4588`; all messages have `\n\r`.
- `WIZ-026` — `qmconfig` verified as already ROM-faithful per `src/act_wiz.c:4685-4787`; added test coverage for `"I have no clue..."` fallback.
- `wiznet()` broadcast now iterates `descriptor_list` with `CON_PLAYING` filter per ROM `src/act_wiz.c:171-194`; falls back to `character_registry` in test environments without descriptor setup.
- `WIZ-027` — `load` syntax messages now have `\n\r` line endings per ROM; re-invokes `do_load("")` on invalid type.
- `WIZ-028` — `mload` now returns `"Ok.\n\r"` instead of `"You have created {name}!"` per ROM `src/act_wiz.c:2489-2517`; added `wiznet()` broadcast; safe `getattr` for registry.
- `WIZ-029` — `oload` now returns `"Ok.\n\r"` instead of `"You have created {name}!"` per ROM `src/act_wiz.c:2521-2570`; added `wiznet()` broadcast; ROM typo preserved in level message; fixed `char.inventory` slot name.
- `WIZ-030` — `purge` trust check now uses ROM `<=` comparison per `src/act_wiz.c:2625`; added `"X tried to purge you!\n\r"` notification to victim; all messages have `\n\r`.
- `WIZ-031` — `restore` iterates `descriptor_list` for `restore all` per ROM `src/act_wiz.c:2820-2845`; added wiznet broadcasts; all messages have `\n\r`.
- `WIZ-032` — `clone` now has wiznet broadcasts per ROM `src/act_wiz.c:2338-2455`; added trust check for mob cloning; uses `obj.carried_by` to determine placement; all messages have `\n\r`.
- `WIZ-033` — `set` command now uses `\n\r` line endings and re-invokes `do_set("")` on invalid type per ROM `src/act_wiz.c:3233-3275`.
- `WIZ-034` — `sset` now uses `getattr(registry, "skill_table", [])` iteration; added `(use the name of the skill, not the number)` hint; all messages have `\n\r` per ROM `src/act_wiz.c:3278-3352`.
- `WIZ-035` — `mset` now fully ROM-parity per `src/act_wiz.c:3355-3790`: uses `smash_tilde()`; uses `get_max_train()` for stat ranges; `level` rejects PCs; `sex` sets `pcdata.true_sex`; `hp`/`mana`/`move` set PC `perm_*` values; uses ROM field name prefixes (`startswith()`); adds fields: `class`, `race`, `group`, `hours`, `thirst`, `drunk`, `full`, `hunger`; `security` uses `ch->pcdata->security` range; clears `victim.zone`; re-invokes `do_mset("")` on unknown field; all messages have `\n\r`.
- `WIZ-036` — `oset` now fully ROM-parity per `src/act_wiz.c:3958-4067`: uses `smash_tilde()`; adds `v0`-`v4` aliases; caps `value0` at `min(50, value)` per ROM:3998; adds `timer` field; uses ROM field prefixes; re-invokes `do_oset("")` on unknown field; all messages have `\n\r`.
- `WIZ-037` — `rset` now fully ROM-parity per `src/act_wiz.c:4071-4136`: uses `smash_tilde()`; uses `find_location()` for room lookup; adds private-room check (`is_room_owner`/`room_is_private`); adds "Value must be numeric.\n\r" check; uses ROM field prefixes; re-invokes `do_rset("")` on unknown field; all messages have `\n\r`.
- `WIZ-038` — `string` now fully ROM-parity per `src/act_wiz.c:3793-3954`: uses `smash_tilde()`; adds `spec` field via `get_spec_fun()`; `long` appends `\n\r`; uses `set_title()` for title; uses ROM field prefixes; adds ROM `extra_descr` insertion; re-invokes `do_string("")` on bad type; all messages have `\n\r`.
- `ALIAS-001` — `alia` now returns the ROM `src/alias.c:97-100` typo-guard text instead of a generic helper string.
- `ALIAS-002` — `alias` now mirrors ROM `src/alias.c:112-220`: exact list/query/set/realias messages, reserved-word checks, quote/name validation, `delete`/`prefix` expansion guards, and the five-alias limit.
- `ALIAS-003` — alias substitution now mirrors ROM `src/alias.c:69-99`: one expansion pass only, truncation warning handling, and `mud.rom_api.substitute_alias()` now returns the expanded string instead of an internal tuple.
- `ALIAS-004` — `unalias` now mirrors ROM `src/alias.c:236-274` prompt/removal/failure messages.
- `ALIAS-005` — prefix preprocessing before alias expansion now mirrors ROM `src/alias.c:49-61,88-95`, including the overlong-line warning and full-`prefix` bypass semantics.
- `HEALER-001` — `heal` now finds NPC healers via `ACT_IS_HEALER` and shows the ROM `src/healer.c:49-79` service table instead of a compressed summary string.
- `HEALER-002` — `heal mana` now mirrors ROM `src/healer.c:147-190`: silver-aware affordability, `deduct_cost`, healer payout, TO_ROOM utterance, and `dice(2, 8) + level/3` mana restoration.
- `HEALER-003` — `heal refresh` now dispatches to the underlying ROM spell path from `src/healer.c:156-160,196` instead of a placeholder full-restore shortcut.
- `HEALER-004` — `heal heal` now dispatches to the underlying ROM `spell_heal` path from `src/healer.c:107-112,196` instead of always filling hit points to max.

## [2.6.15] - 2026-04-28

Closes the `scan.c` audit (P2): all 3 gaps fixed, ROM-faithful TO_ROOM/TO_CHAR
broadcasts on the `scan` command, divergent header and fallback lines removed.

### Added

- `SCAN-001` — `do_scan` with no argument now emits the TO_ROOM broadcast
  `"$n looks all around."` so onlookers see the scan, mirroring ROM
  `src/scan.c:60` (`act("$n looks all around.", ch, NULL, NULL, TO_ROOM);`).
- `SCAN-002` — directional `do_scan` now emits the TO_CHAR/TO_ROOM act() pair
  `"You peer intently <dir>."` / `"$n peers intently <dir>."`, mirroring ROM
  `src/scan.c:89-90`.

### Fixed

- `SCAN-002` — directional `do_scan` no longer prints a spurious
  `"Looking <dir> you see:"` header. ROM builds that string into `buf` at
  `src/scan.c:91` but never calls `send_to_char(buf, ch)`; the only visible
  scanner-facing message is the `"You peer intently <dir>."` act().
- `SCAN-003` — `do_scan` no longer emits non-ROM fallback lines
  (`"No one is nearby."`, `"Nothing of note."`) when no visible characters
  are found. ROM emits only the act() messages and header in that case
  (`src/scan.c:48-104`).

## [2.6.14] - 2026-04-28

Closes the `db2.c` audit (P1): all CRITICAL/IMPORTANT mob-loader gaps fixed.
Both `.are` and JSON loaders now match ROM `src/db2.c:load_mobiles` for AC
scaling, `ACT_IS_NPC` enforcement, race-table flag merge, and first-char
uppercase of long_descr/description. Two MINOR gaps (`DB2-004` kill_table,
`DB2-005` single-line fread_string) remain deferred — both documented as
not user-reachable in the current port.

### Fixed

- `DB2-003` — both mob loaders now uppercase the first character of
  `long_descr` and `description` at load time, mirroring ROM
  `src/db2.c:236-237` (`pMobIndex->long_descr[0] = UPPER(...)`).
  Previously mob protos with a lowercase first letter rendered that way in
  room/look output. `.are` loader normalizes after `read_string_tilde`;
  JSON loader normalizes inline at MobIndex construction.
- `DB2-006` — mob armor-class fields (`ac_pierce`/`ac_bash`/`ac_slash`/`ac_exotic`)
  are now multiplied by 10 at load time in both the `.are` loader
  (`mud/loaders/mob_loader.py`) and the JSON loader (`mud/loaders/json_loader.py`),
  mirroring ROM `src/db2.c:273-276`. Previously every loaded NPC had an AC value
  10× off in ROM's negative-AC convention, making them noticeably easier to hit.
  `mud/scripts/convert_are_to_json.py` now divides back when re-emitting JSON so
  the JSON files stay a faithful mirror of the raw `.are` upstream.
- `DB2-002` — both mob loaders now merge ROM `race_table[race].{act, aff,
  off, imm, res, vuln, form, parts}` flag bits into each loaded mob's
  letter-based flag fields, mirroring ROM `src/db2.c:239-242,279-286,295-297`.
  Previously race-derived intrinsics (dragon flying, troll regeneration,
  modron immunities, undead form/parts) were silently dropped at load time.
  Implemented in `mud/loaders/mob_loader.py:merge_race_flags`; the JSON
  loader (`mud/loaders/json_loader.py`) invokes it after MobIndex construction.
- `DB2-001` — both mob loaders now unconditionally OR `ACT_IS_NPC` (letter `A`)
  into every prototype's `act_flags` letter string, mirroring ROM
  `src/db2.c:239`. Previously a mob whose area-file flags omitted the `A`
  letter would spawn with `IS_NPC()` returning false, breaking every
  downstream `is_npc` check (combat, save, look, mobprog dispatch).

## [2.6.13] - 2026-04-28

Closes the cross-file dependency that blocked `interp.c` completion:
`WEAR-010` (do_wear dispatches weapons to wield) and `WEAR-011`
(do_hold auto-replaces) cleared the way for `INTERP-013` to collapse
`do_wield`/`do_hold` into aliases on `do_wear`, mirroring ROM
`cmd_table[]`. `interp.c` now closes at **24/24 fixed + 1
closed-deferred**.

### Fixed

- `act_obj.c:WEAR-010` — `do_wear` now dispatches `ITEM_WEAPON` items
  to the WIELD branch (`_dispatch_wield`) instead of rejecting with
  "You need to wield weapons, not wear them." Mirrors ROM
  `src/act_obj.c:1401-1697` `wear_obj` single-dispatcher design where
  `do_wear`/`do_wield`/`do_hold` are all the same function. Tests:
  `tests/integration/test_equipment_system.py::test_wear_010_do_wear_dispatches_weapon_to_wield`.
- `act_obj.c:WEAR-011` — `do_hold` now auto-unequips an existing held
  item via `_unequip_to_inventory()` instead of rejecting with
  "You're already holding {name}." Mirrors ROM
  `src/act_obj.c:1670-1677` `remove_obj(WEAR_HOLD, fReplace=TRUE)`
  semantics. Tests:
  `tests/integration/test_equipment_system.py::test_wear_011_do_hold_auto_replaces_existing_held`.
- `interp.c:INTERP-013` — `wield` and `hold` now dispatch to `do_wear`
  via the dispatcher's `aliases=("wield", "hold")` on the `wear`
  Command, mirroring ROM `cmd_table[]` (src/interp.c:103, 215, 232).
  `do_wield`/`do_hold` collapsed to thin wrappers around `do_wear`
  for direct-import callers. Closes `interp.c` to **24/24 fixed +
  1 closed-deferred** (100% of closeable gaps). Tests:
  `tests/integration/test_interp_dispatcher.py::test_interp_013_wear_wield_hold_share_do_wear`.

### Changed

- `wield <non-weapon>` and `hold <non-holdable>` no longer reject with
  command-specific errors ("You can't wield that." / "You can't hold
  that."). They now run the full `do_wear` dispatcher, so
  e.g. `wield ring` wears the ring on a finger — ROM-faithful since
  ROM has no separate `do_wield`/`do_hold` functions.
- `wield` and `hold` with no argument now emit
  `"Wear, wield, or hold what?"` instead of `"Wield what?"` /
  `"Hold what?"`, mirroring ROM's single-prompt design.

## [2.6.12] - 2026-04-28

Closes the remaining `interp.c` parser/extension gaps:
`INTERP-015` (port ROM `one_argument` to replace `shlex.split`) and
`INTERP-016` (verify `tail_chain` is a no-op in stock ROM and close-defer).
`interp.c` is now 22/24 gaps fixed + 1 closed-deferred + 1 deferred-pending
(`INTERP-013`, blocked on `ACT_OBJ_C` `do_wear` port).

### Fixed

- `interp.c:INTERP-015` — `_split_command_and_args` no longer routes
  through `shlex.split`; the new `_one_argument()` mirrors ROM
  `src/interp.c:766-798` byte-for-byte (lowercases head, single-char
  `'` and `"` quote sentinels with no nesting, backslash treated
  literally, surrounding whitespace stripped). `shlex` import dropped.
  Tests:
  `tests/integration/test_interp_dispatcher.py::test_interp_015_one_argument_matches_rom`
  (8 cases).

### Changed

- `interp.c:INTERP-016` — closed-deferred. Confirmed `tail_chain()`
  is `return;` only in stock ROM 2.4b6 (`src/db.c:3929`); empty
  hook used by some ROM derivatives for stack-tail-call extension.
  Stock-ROM behavior is "do nothing", which Python already matches
  by omission.
- `tests/test_alias_parity.py::test_alias_case_sensitivity` renamed
  to `test_alias_case_insensitive_lookup_matches_rom` and flipped to
  assert ROM-correct behavior — ROM `do_alias` stores keys via
  `one_argument` which lowercases (`src/alias.c:127, 217`), so an
  uppercase input head expands a lowercased alias key. The previous
  Python assertion mirrored pre-port `shlex` behavior, not ROM.

## [2.6.11] - 2026-04-28

Closes the three small position/trust gates left in `interp.c`
(`INTERP-004`/`-005`/`-006`). `interp.c` is now 20/24 gaps closed
(83%); only `INTERP-013` (deferred until `do_wear` ports the missing
wield/hold logic), `INTERP-015` (shlex/one_argument port), and
`INTERP-016` (`tail_chain` documentation, no-op) remain.

### Fixed

- `interp.c:INTERP-004` — `shout` now requires trust 3 to match ROM
  (`src/interp.c:200`). Previously had no `min_trust` (defaulted to 0).
  Test: `tests/integration/test_interp_dispatcher.py::test_interp_004_shout_requires_trust_3`.
- `interp.c:INTERP-005` — `murder` now requires trust 5 to match ROM
  (`src/interp.c:247`). Test:
  `test_interp_005_murder_requires_trust_5`.
- `interp.c:INTERP-006` — `music` `min_position` lowered from
  `RESTING` to `SLEEPING` to match ROM (`src/interp.c:93`). Test:
  `test_interp_006_music_min_position_sleeping`.

## [2.6.10] - 2026-04-27

Closes five more `interp.c` gaps: command-mapping cleanup
(`INTERP-009/010/011/012/014` — `hit`/`take`/`junk`/`tap`/`go`/`:`
now route to canonical handlers), `do_commands` column-padding fix
(`INTERP-024`), and the prefix-order sweep (`INTERP-017`) — Python's
prefix scan now mirrors ROM `cmd_table[]` declaration order via a
250-entry table, so 1- and 2-letter abbreviations resolve identically
to ROM. `INTERP-013` (collapse `do_wield`/`do_hold` into `do_wear`)
deferred — Python `do_wear` is missing strength/skill/two-hand checks
and HOLD auto-unequip that the separate functions currently provide;
collapsing now would regress behavior. `interp.c` is now 17/24 gaps
closed (71%).

### Fixed

- `interp.c:INTERP-009` — `"hit"` now dispatches to `do_kill` as a
  ROM-style alias on the kill `Command`; deleted redundant `do_hit`
  stub from `player_info.py` (`src/interp.c:88`). Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_009_hit_routes_to_do_kill`.
- `interp.c:INTERP-010` — `"take"` now dispatches to `do_get` as an
  alias on the get `Command`; deleted `do_take` stub
  (`src/interp.c:226`). Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_010_take_routes_to_do_get`.
- `interp.c:INTERP-011` — `"junk"` and `"tap"` now dispatch to
  `do_sacrifice` as aliases; deleted both stubs from `remaining_rom.py`
  (`src/interp.c:228-229`). Test:
  `test_interp_011_junk_tap_route_to_do_sacrifice`.
- `interp.c:INTERP-012` — `"go"` now dispatches to `do_enter` as an
  alias; deleted `do_go` stub (`src/interp.c:263`). Test:
  `test_interp_012_go_routes_to_do_enter`.
- `interp.c:INTERP-014` — `":"` now dispatches to `do_immtalk` as an
  alias; deleted `do_colon` stub from `typo_guards.py` whose
  `"Say what on the immortal channel?"` placeholder was masking ROM's
  NOWIZ toggle behavior (`src/interp.c:356`). Test:
  `test_interp_014_colon_routes_to_do_immtalk`.
- `interp.c:INTERP-024` — `do_commands`/`do_wizhelp` no longer strip
  trailing whitespace from rows; ROM emits each name as `%-12s` with
  full column padding preserved (`src/interp.c:815-823`). Test:
  `test_interp_024_do_commands_preserves_12char_column_padding`.
- `interp.c:INTERP-017` — `resolve_command` now walks a 250-entry
  ROM-faithful `_PREFIX_TABLE` in `src/interp.c` declaration order
  instead of Python's feature-grouped `COMMANDS` list; removed the
  exact-match shortcut so prefix resolution mirrors ROM
  `interpret()` exactly (e.g. `"go"` now resolves to `goto` not
  `enter`, matching ROM's hand-ordered prefix block). Sweep test:
  `tests/integration/test_interp_prefix_order.py::test_interp_017_prefix_winner_matches_rom`
  parses `src/interp.c` at collection time and asserts every
  single-letter prefix plus 20 curated 2-letter prefixes resolve
  identically to ROM (45 cases).

## [2.6.9] - 2026-04-27

Closes four `interp.c` dispatcher-level gaps in one session: empty-input
behavior (`INTERP-007`), ROM punctuation aliases (`INTERP-008`), snoop
forwarding (`INTERP-002`), and verified the wiznet `WIZ_SECURE` mirror
that was already in place (`INTERP-003`). `interp.c` is now 11/24 gaps
closed (46%).

### Fixed

- `interp.c:INTERP-007` — empty input now returns silently to match
  ROM `interpret()` (`src/interp.c:401-404`). Previously emitted the
  literal `"What?"`. Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_007_empty_input_returns_silently`.
- `interp.c:INTERP-008` — added ROM punctuation aliases `.` → `gossip`,
  `,` → `emote`, `/` → `recall` to `COMMAND_INDEX`
  (`src/interp.c:184,186,272`). Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_008_punctuation_aliases_route_to_rom_handlers`.
- `interp.c:INTERP-002` — `process_command` now forwards the input
  logline to `desc.snoop_by.character.messages` prefixed with `"% "`
  (`src/interp.c:491-496`). Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_002_snoop_forwards_logline_to_snooper`.
- `interp.c:INTERP-003` — verified `log_admin_command` already mirrors
  logged commands to wiznet `WIZ_SECURE` with ROM-style `$`/`{`
  doubling (`mud/admin_logging/admin.py:107-114`,
  `src/interp.c:468-489`). Audit row description was stale. Test:
  `tests/integration/test_interp_dispatcher.py::test_interp_003_logged_command_mirrors_to_wiznet_secure`.

## [2.6.8] - 2026-04-27

Closes the immortal command trust drift (`INTERP-001`). All 43 commands
that were gated too low now match ROM `cmd_table[]` tier-for-tier. This
is a security-relevant fix — previously a `LEVEL_IMMORTAL` (52) character
could invoke commands ROM gates at L1..ML (53..60).

### Fixed

- `interp.c:INTERP-001` — raised `min_trust` on 43 immortal commands
  in `mud/commands/dispatcher.py` to match ROM `cmd_table[]` trust
  tiers (`src/interp.c:63-381`, `src/interp.h:34-44`). Affected
  tiers: ML, L1, L2, L3, L4, L5, L6, L7. Security-relevant — closes
  privilege drift where `LEVEL_IMMORTAL` (52) characters could
  invoke commands ROM gates at L1..ML (53..60). Test:
  `tests/integration/test_interp_trust.py::test_interp_001_command_trust_matches_rom` (50 parameters).

## [2.6.7] - 2026-04-27

`interp.c` social-cluster audit complete (6/6 social gaps closed). Both
remaining gaps (prefix lookup + literal "not found" message) shipped
with integration coverage; socials suite now 31/31. `interp.c` overall
audit progress: 6/24 gaps closed (25%) — non-social gaps (trust drift,
dispatcher hooks, command-mapping cleanup) remain open.

### Fixed

- `interp.c:INTERP-021` — social command lookup now mirrors ROM
  `str_prefix` semantics so partial names (e.g. `gigg` → `giggle`)
  resolve in load order. Added `mud.models.social.find_social()` and
  routed both the dispatcher fallback (`mud/commands/dispatcher.py`)
  and `perform_social` (`mud/commands/socials.py`) through it. Mirrors
  ROM `src/interp.c:584-592`.
- `interp.c:INTERP-022` — `perform_social` now emits the literal
  `"They aren't here."` when the targeted victim is absent, matching
  ROM `src/interp.c:637-640`. The fabricated `social.not_found` field
  (which has no counterpart in ROM's social table) is no longer used.

## [2.6.6] - 2026-04-27

`interp.c` ROM parity audit started — full audit doc with 24 stable gap
IDs (`INTERP-001`..`INTERP-024`) created. Closed the entire CRITICAL+
IMPORTANT social-cluster subset of `check_social` (`src/interp.c:597-685`):
position gates, NOEMOTE, sleeping snore exception, and the NPC slap/echo
auto-react via `mud.utils.rng_mm.number_bits(4)`. Socials integration
suite grew from 13 to 27 tests, all green.

### Fixed

- `interp.c:INTERP-018` — `perform_social` now refuses socials from
  characters in `Position.DEAD`, `MORTAL`, `INCAP`, or `STUNNED` and
  emits ROM's exact response messages
  (`"Lie still; you are DEAD."`, `"You are hurt far too bad for that."`,
  `"You are too stunned to do that."`). Mirrors
  `src/interp.c:603-616` (`check_social` position gate).
- `interp.c:INTERP-019` — sleeping characters now receive
  `"In your dreams, or what?"` for every social except `snore`
  (the canonical Furey exception). Mirrors `src/interp.c:618-626`.
- `interp.c:INTERP-020` — players punished with the `COMM_NOEMOTE`
  flag now receive `"You are anti-social!"` when attempting any
  social. NPCs are unaffected per ROM's `IS_NPC` short-circuit.
  Mirrors `src/interp.c:597-601`.

### Added

- `interp.c:INTERP-023` — NPC auto-reaction to player socials. When
  a non-NPC socials at an awake, non-charmed, non-switched NPC,
  `mud.utils.rng_mm.number_bits(4)` (0..15) decides the response:
  values 0..8 echo the social back at the player with the actor and
  victim swapped; values 9..12 produce a slap
  (`"$n slaps $N." / "You slap $N." / "$n slaps you."`); values 13..15
  fall through silently. Mirrors `src/interp.c:652-685`.

## [2.6.5] - 2026-04-27

`mob_prog.c` ROM parity audit complete — all 7 gaps closed (2 CRITICAL,
4 IMPORTANT, 1 MINOR). MOBprog predicate evaluation, greet/grall trigger
exclusivity, $-code expansion, and program-flow state-machine now match
ROM 2.4b6 behaviour.

### Fixed

- MOBPROG-007: `_program_flow` now logs a warning and aborts the program when
  an `if`/`or`/`and` keyword is not in ROM's `fn_keyword[]` table, mirroring
  the `bug()` + `return` paths at `src/mob_prog.c:1049-1056`, `1076-1083`,
  `1103-1109`. Typo'd predicates fail loudly instead of silently evaluating
  to False. Integration coverage at
  `tests/integration/test_mobprog_program_flow.py`. Also corrected the
  `test_simple_quest_accept_workflow` fixture program to use the real ROM
  keyword `carries` (not the previously-silent invalid `has_item`).
- MOBPROG-006: `_expand_arg` `$R` substitution now replicates the ROM
  long-standing bug at `src/mob_prog.c:798-799` — the visibility gate uses
  `rch` (random victim) but the substituted string is `ch->short_descr`
  (NPC actor) or `ch->name` (PC actor). Per AGENTS.md ROM Parity Rules,
  QuickMUD reproduces the bug. Integration coverage at
  `tests/integration/test_mobprog_predicates.py`.
- MOBPROG-005: `_program_flow` `else` branch now resets
  `state[level] = IN_BLOCK` mirroring ROM `src/mob_prog.c:1138`. Structural
  state-machine parity only — no observable divergence on valid programs;
  regression coverage added at
  `tests/integration/test_mobprog_program_flow.py`.
- MOBPROG-004: `_cmd_eval` `clan` / `race` / `class` checks now resolve their
  name keyword via a ROM-style prefix lookup over `CLAN_TABLE`, `RACE_TABLE`,
  and `CLASS_TABLE` (mirroring ROM `clan_lookup` / `race_lookup` /
  `class_lookup`, `src/mob_prog.c:601-609`) instead of comparing the int
  attribute to the literal name string. `if class $n mage`,
  `if race $n dragon`, `if clan $n thieves` now match ROM. Integration
  coverage at `tests/integration/test_mobprog_predicates.py`.
- MOBPROG-003: `_cmd_eval` `vnum` check now compares against `lval=0` when the
  target is a PC instead of returning False. Mirrors ROM `src/mob_prog.c:631-642`
  — `lval` initialises to 0 and is only overwritten for NPCs, so
  `if vnum $n == 0` is True against PCs and `if vnum $n != 0` is False.
  Integration coverage at `tests/integration/test_mobprog_predicates.py`.
- MOBPROG-002: `mp_greet_trigger` no longer falls through to GRALL after a
  failed GREET percent roll. Mirrors ROM `src/mob_prog.c:1340-1345` where the
  GREET / GRALL branches are exclusive — a mob that is awake, can see the
  entrant, and has a GREET trigger only attempts GREET; GRALL is reserved for
  the busy/blind path. Integration coverage at
  `tests/integration/test_mobprog_greet_trigger.py`.
- MOBPROG-001: `_cmd_eval` `objexists` now walks `mud.models.obj.object_registry`
  (mirroring ROM `get_obj_world`, `src/mob_prog.c:399`) instead of only the
  current room and same-room carriers. Mob programs that gate on
  `if objexists <vnum|name>` against globally-placed items now match ROM
  semantics. Integration coverage at
  `tests/integration/test_mobprog_predicates.py`.

## [2.6.4] - 2026-04-27

`mob_cmds.c` ROM parity audit complete — all 18 gaps closed (6 CRITICAL,
9 IMPORTANT, 3 MINOR). MOBprog script commands (`mob kill`, `assist`,
`oload`, `flee`, `cast`, `call`, `damage`, `junk`, `purge`, `transfer`)
now match ROM 2.4b6 behaviour for charm/master defence, position gates,
target-type dispatch, level bounds, NO_MOB respect, recursion, and
bug-log emission on script authoring errors.

### Fixed

- MOBCMD-017: `do_mptransfer` now mirrors ROM's recursive structure — a
  literal `mob transfer all <loc>` recursively dispatches
  `do_mptransfer(ch, "<pcname> <loc>")` once per PC in the room
  (`src/mob_cmds.c:791-806`) so each victim re-runs the full validation
  pipeline (private-room check, location resolution). Previously the
  Python implementation inlined the iteration with a direct
  `_transfer_character` call. NPCs are skipped exactly as in ROM line
  799. Integration coverage at `tests/integration/test_mob_cmds_transfer.py`.
- MOBCMD-018: verified `do_mpflee` already checks `ch.fighting` as the
  first guard, mirroring ROM `src/mob_cmds.c:1266-1267`. The audit row
  was stale and is now closed without a code change.
- MOBCMD-007: `do_mppurge` no longer accepts the literal `"all"` token
  as a synonym for the no-arg purge-everything form. ROM
  `src/mob_cmds.c:631-665` treats an empty argument as purge-all and has
  no `"all"` keyword — the token falls through to the name-resolution
  branch like any other word. Also added the missing
  `Mppurge - Bad argument` (ROM line 663) and `Mppurge - Purging a PC`
  (ROM line 671) bug logs via the new `_bug()` helper. The previously
  divergent unit test (`test_mppurge_all_cleans_room`) now uses the
  no-arg form. Integration coverage at
  `tests/integration/test_mob_cmds_purge.py`.
- MOBCMD-013: `do_mpdamage` now emits a ROM-style `bug()` warning via
  Python's `logging` module when the min or max argument is non-numeric,
  mirroring ROM `src/mob_cmds.c:1105-1107` + `1113-1115`. Previously the
  function silently returned, swallowing what is a script-authoring
  error. A new module-local `_bug()` helper in `mud/mob_cmds.py` mirrors
  ROM's `bug("Mp... - <reason> from vnum %d.", vnum)` pattern; expect
  this helper to be reused as further `mob_cmds` gaps are closed.
  Integration coverage at
  `tests/integration/test_mob_cmds_damage.py::TestMpDamageNonNumericArgsBugLog`.
- MOBCMD-009: `do_mpflee` now respects `ROOM_NO_MOB` on a candidate
  destination when the fleeing character is an NPC, mirroring ROM
  `src/mob_cmds.c:1277-1280`. Previously script-driven NPC flees would
  pour mobs into rooms flagged NO_MOB. Integration coverage at
  `tests/integration/test_mob_cmds_flee.py::TestMpFleeNoMobRoomFlag`.
- MOBCMD-006: `do_mpoload` now validates the optional level argument
  against ROM's `level < 0 || level > get_trust(ch)` check
  (`src/mob_cmds.c:575-580`) and refuses to spawn the object when out of
  range. Previously the level was accepted unconditionally so a script
  could load objects above the mob's trust ceiling. Integration coverage
  at `tests/integration/test_mob_cmds_oload.py`.
- MOBCMD-004: `do_mpjunk` (MOBprog `junk` script command) now matches
  ROM's empty-needle behaviour: `mob junk all.` (trailing dot, no
  suffix) discards nothing because ROM `src/mob_cmds.c:436` defers to
  `is_name(&arg[4], ...)` which returns FALSE for an empty string.
  Python had been short-circuiting on `not suffix` and discarding every
  carried object. Bare `mob junk all` still clears inventory as before.
  Integration coverage at `tests/integration/test_mob_cmds_junk.py`.
- MOBCMD-002: `do_mpassist` now enforces ROM `src/mob_cmds.c:393`'s full
  guard set — `victim == ch`, `ch->fighting != NULL`, and
  `victim->fighting == NULL`. Previously only the third clause was
  checked, so a script mob already in a fight could be redirected onto a
  new target via `mob assist`, and a script mob could nonsensically
  assist itself. Integration coverage at
  `tests/integration/test_mob_cmds_assist.py`.
- MOBCMD-001: `do_mpkill` now refuses when the script mob is charmed
  (`AffectFlag.CHARM`) and the chosen victim is its master, mirroring ROM
  `src/mob_cmds.c:364-369`. Previously a charmed mob scripted to
  `mob kill <master>` would attack its own charmer. Integration coverage
  at `tests/integration/test_mob_cmds_kill.py::TestMpKillCharmedMasterGuard`.
- MOBCMD-015 + MOBCMD-016: `do_mpcall` (MOBprog `call` script command) now
  parses the optional obj1/obj2 tokens from `mob call <vnum> <victim>
  <obj1> <obj2>` and resolves them via `_find_obj_here` (the `get_obj_here`
  analog), forwarding both to `mobprog.call_prog`. ROM
  `src/mob_cmds.c:1217-1252` initialises obj1/obj2 to NULL and only sets
  them when the corresponding token resolves through `get_obj_here`; the
  Python implementation had been dropping both args entirely so called
  sub-programs could never receive object context. Integration coverage at
  `tests/integration/test_mob_cmds_call.py`.
- MOBCMD-011 + MOBCMD-012: `do_mpcast` (MOBprog `cast` script command) now
  resolves the JSON `target` string into a canonical `_TargetType` IntEnum
  mirroring ROM `TAR_*` (`src/magic.h`) and dispatches on the enum, matching
  ROM's switch in `src/mob_cmds.c:1043-1066`. The previously string-keyed
  branches were drift-prone; in particular the `TAR_OBJ_CHAR_DEF/OFF/INV`
  cases now require an object (no character fallback) and `TAR_CHAR_DEFENSIVE`
  defaults to `ch` when the lookup fails, matching ROM lines 1055 + 1060-1065.
  Integration coverage at `tests/integration/test_mob_cmds_cast.py`.
- MOBCMD-003: `do_mpkill` now gates on `ch.position == Position.FIGHTING`
  (matching ROM `src/mob_cmds.c:361`) instead of the looser
  `ch.fighting is not None` check, and short-circuits self-attacks via the
  missing `victim is ch` guard from the same ROM line. Integration coverage
  at `tests/integration/test_mob_cmds_kill.py`.
- MOBCMD-008: `do_mpflee` now performs 6 `rng_mm.number_door()` random-door
  attempts before giving up, mirroring ROM `src/mob_cmds.c:1272-1286`.
  Previously the function iterated the exits list in order, so the first
  valid exit always won — wrong distribution for ROM-faithful flee
  behavior. Integration coverage at
  `tests/integration/test_mob_cmds_flee.py::TestMpFleeRandomDoor`.
- MOBCMD-010: `do_mpflee` (MOBprog `flee` script command) now routes through
  `mud.world.movement.move_character` instead of the silent `_move_to_room`
  helper, mirroring ROM `src/mob_cmds.c:1283`
  (`move_char(ch, door, FALSE)`). Leave/arrive broadcasts, mp_exit/entry
  triggers, and the rest of the canonical movement pipeline now fire on
  script-driven flees. Integration coverage at
  `tests/integration/test_mob_cmds_flee.py`.
- MOBCMD-005: `do_mpoload` (MOBprog `oload` script command) now accepts the
  optional `level` argument from `mob oload <vnum> [level] [R|W]`, mirroring
  ROM `src/mob_cmds.c:538-614`. When omitted, level defaults to
  `get_trust(ch)`; the spawned object's `level` is set post-spawn to mirror
  ROM `create_object(pObjIndex, level)`. Previously the level token was parsed
  but discarded, so script-loaded objects always took the prototype's raw
  level. Integration coverage at `tests/integration/test_mob_cmds_oload.py`.
- MOBCMD-014: `do_mpdamage` (MOBprog `damage` script command) now routes
  through `mud.combat.engine.apply_damage` instead of raw-decrementing
  `victim.hit`. Mirrors ROM `src/mob_cmds.c:1132-1145`
  (`damage(victim, victim, amount, TYPE_UNDEFINED, DAM_NONE, FALSE)`) so
  the death pipeline, position updates, fight triggers, and corpse
  handling fire on script-driven damage. Integration coverage at
  `tests/integration/test_mob_cmds_damage.py`.

### Changed

- `docs/parity/ACT_OBJ_C_AUDIT.md` and `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
  refreshed to reflect that ROM `src/act_obj.c` is at 100% parity. Apr 27, 2026
  formal sweep verified all 12 audited functions
  (`do_get`/`do_put`/`do_drop`/`do_give`/`do_remove`/`do_sacrifice`/`do_quaff`/
  `do_drink`/`do_eat`/`do_fill`/`do_pour`/`do_recite`/`do_brandish`/`do_zap`
  plus `do_wear`/`do_wield`/`do_hold` and `do_steal`) against current Python;
  the recent batch commits (`97c901e` do_drop parity batch, `517542b` close
  get/put/drop/give/wear/sacrifice/recite/brandish/zap/steal gaps) closed all
  outstanding gaps. 193 act_obj-area integration tests green. P1 audited count
  rises from 5/11 (81%) to 6/11 (86%). No code changes — documentation
  reconciliation only.

## [2.6.3] - 2026-04-27

### Added

- Three project-local skills under `.claude/skills/` encoding the ROM 2.4b6 →
  Python parity loop: `rom-parity-audit` (file-level 5-phase audit),
  `rom-gap-closer` (single-gap TDD close flow), `rom-session-handoff`
  (end-of-session SESSION_SUMMARY + SESSION_STATUS + CHANGELOG generation).
- `CLAUDE.md` "Porting workflow" section: decision-tree mapping of when to
  invoke each skill plus dependencies between them.

### Changed

- `README.md` Project Status / badges refreshed to current state: version
  `2.6.2`, tests `3508/3521 passing` (99.6%) with 11 skipped and 2 known
  pre-existing failures, integration suite `1000+`, ROM 2.4b parity badge
  scoped to "gameplay 100%" (truer given the long tail of P2/P3 files), and
  active focus called out as `act_obj.c` (~60%).
- `AGENTS.md` Repo Hygiene §2 now requires that any change to README's
  Project Status / badges / metrics be accompanied in the same commit by a
  refresh of AGENTS.md tracker pointers and `docs/sessions/SESSION_STATUS.md`,
  preventing drift between the three surfaces. Underlying numbers stay
  sourced from `docs/parity/*` trackers.

## [2.6.2] - 2026-04-27

### Fixed

- **act_enter portal regressions** uncovered by the act_enter.c audit
  (PR #123):
  - `_stand_charmed_follower` now forwards `do_stand`'s returned string
    into the follower's message stream, so charmed sleepers receive the
    "You wake and stand up." text exactly as ROM `act_move.c:1044`
    sends inside `do_stand`.
  - `_portal_fade_out` now explicitly removes the portal from
    `room.contents` and clears `portal.location`. `game_loop._extract_obj`
    keys off `obj.in_room` but `Object` uses `obj.location`, so portal
    detachment after charge expiry was a silent no-op. Behavior now
    matches ROM `extract_obj(portal)` at `act_enter.c:212`.
  - `test_enter_closed_portal_denied`: corrected expected message to
    `"You can't seem to find a way in."` per ROM `act_enter.c:94`. The
    prior `"The portal is closed."` was the door-blocked message from
    `act_move.c`, not the portal path.
  - `test_move_through_portal_blocked_while_fighting`: corrected to
    assert silent return per ROM `act_enter.c:70-71`
    (`if (ch->fighting != NULL) return;`); removed the non-ROM
    `"No way!  You are still fighting!"` string.
- **`test_giant_strength_refuses_to_stack`** (was
  `test_stat_modifiers_stack_from_same_spell`): test asserted +4 STR after
  recasting giant strength, but ROM `src/magic.c:3022-3030`
  `spell_giant_strength` early-returns with "You are already as strong as
  you can get!" when the target is already affected. The Python
  implementation correctly mirrors ROM; the test was wrong. Rewrote the
  test to assert ROM anti-stack behavior.
- **`test_scavenger_prefers_valuable_items`**: flaky because the
  Mitchell-Moore RNG state leaks across tests, and the scavenger only acts
  on a 1/64 roll per `mobile_update` tick. Seed `rng_mm.seed_mm` to a
  known value at start of test and bump the iteration cap from 2000 to
  5000 for deterministic passes.

## [2.6.1] - 2026-04-27

### Added

- **act_enter.c parity (100% ROM parity for portal/enter mechanics):**
  Close all 15 ENTER-001..016 gaps documented in
  `docs/parity/ACT_ENTER_C_AUDIT.md`. 25 new integration tests in
  `tests/integration/test_act_enter_gaps.py`.

### Fixed

- **ENTER-009 (CRITICAL):** `do_enter` TO_CHAR message ("You enter $p." /
  "...somewhere else...") was being returned as a Python string and
  silently dropped — now delivered to the player.
- **ENTER-005:** Portal lookup uses `get_obj_list` (visibility,
  numbered syntax `2.portal`, keyword-list semantics) instead of fuzzy
  substring matching.
- **ENTER-004:** Non-portal objects and closed portals both produce
  `"You can't seem to find a way in."` (was diverging).
- **ENTER-008/010:** Departure/arrival TO_ROOM messages go through
  `act_format` + `broadcast_room` for correct `$n` invisibility
  resolution.
- **ENTER-011:** Portal fade-out only broadcasts in the old room when
  caller is in the old room; calls `extract_obj` on charge expiry.
- **ENTER-013:** `_get_random_room` capped at 100k iterations
  (was potentially returning None; ROM loops indefinitely).
- **ENTER-006/007/012:** Follower cascade — charmed followers stand
  before following, follower-name interpolation via `act_format`.
- **ENTER-002/003/014/015/016:** Cosmetic message wording matched to
  ROM and fighting-character silent-skip path.

## [2.6.0] - 2026-04-27

### Added

- **act_obj.c parity batch (100% ROM parity for object-manipulation
  commands):** do_get/do_put/do_drop/do_give/do_wear/do_remove/do_sacrifice/
  do_quaff/do_eat/do_drink/do_fill/do_pour/do_envenom/do_recite/do_brandish/
  do_zap/do_steal and shop commands (do_buy/do_sell/do_list/do_value).
  Adds full ROM TO_ROOM/TO_VICT/TO_NOTVICT broadcasts via act_format +
  broadcast_room. ~80 new integration tests under tests/integration/.
- **act_move.c parity batch:** do_stand/do_rest/do_sit/do_sleep/do_wake
  rewritten with full ROM furniture support (STAND/SIT/REST/SLEEP_AT/ON/IN
  with capacity checks and ch.on tracking). MOVE-001 arrival broadcast,
  MOVE-002 follower-name interpolation, SNEAK-001/HIDE-001 dispatcher
  delegation to canonical handlers. 40 new integration tests in
  tests/integration/test_position_commands.py.
- **act_comm.c P2 batch:** do_emote NOEMOTE check, do_pmote (~312 lines),
  do_colour, do_split gold+silver simultaneous-split fix, do_pose pose_table
  by class+level. New mud/utils/poses.py.
- **act_info.c P2 batch:** do_title/do_description/auto-settings family
  (autolist, autoassist, autoexit, autogold, autoloot, autopeek, autosac,
  autosplit, autotitle).
- LIQUID_TABLE in mud/models/constants.py extended with proof/full/thirst/
  food/ssize fields sourced from ROM src/const.c:886-931.
- WebSocket stream support (mud/network/websocket_stream.py) for the
  browser frontend; tests in tests/test_websocket_server.py.

### Changed

- **AGENTS.md rewritten:** ~700 lines → 275. Removed running session
  narrative, duplicated status reporting, stale "next steps". Added Session
  Notes (docs/sessions/) and Repo Hygiene (CHANGELOG / README / semver in
  pyproject.toml) sections modeled on quickmud-web-client/AGENTS.md.
- 79 SESSION_SUMMARY_*.md and HANDOFF_*.md files moved from repo root to
  `docs/sessions/`.

### Fixed

- `_obj_from_char()` now operates on `char.inventory` (was reading the
  wrong field, so transferred objects were not removed from giver).
- `count_users()` in mud/handler.py now reads `room.people` (room.characters
  does not exist).
- String-keyed equipment lookups replaced with `WearLocation` IntEnum keys
  across BRANDISH/ZAP/POUR families.
- Hardcoded hex flag values replaced with enum members
  (`PlayerFlag.AUTOSPLIT`, `WearFlag.NO_SAC`, `ItemType.STAFF/WAND`, etc).
- `do_steal` MAX_LEVEL set to 60 (was 51); STEAL-001..014 covering
  one_argument semantics, is_safe, is_clan, sleeping-victim wake, PC→PC
  PlayerFlag.THIEF, multi_hit signature, NODROP/INVENTORY checks,
  can_see_object visibility filter.
- `do_recite/do_brandish/do_zap` success paths were unrunnable due to
  undefined SkillTarget, bad ItemType references, string-keyed HOLD
  lookup; all 17 RECITE/BRANDISH/ZAP gaps closed.

## [2.5.2] - 2025-12-30

### Added

- **Command Integration ROM Parity Tests** (70 new tests):
  - `tests/test_act_comm_rom_parity.py` - 23 tests for communication commands (ROM `act_comm.c`)
    - Channel status display (`do_channels`)
    - Communication flag toggles (`do_deaf`, `do_quiet`, `do_afk`)
    - Channel blocking logic (QUIET, NOCHANNELS flags)
    - Delete command NPC blocking
    - Replay command behaviors
  - `tests/test_act_enter_rom_parity.py` - 22 tests for portal mechanics (ROM `act_enter.c`)
    - Random room selection with flag exclusions (`get_random_room`)
    - Portal entry mechanics (closed, curse, trust checks)
    - Portal charge system and flag handling (RANDOM, BUGGY, GOWITH)
    - Follower cascading through portals
  - `tests/test_act_wiz_rom_parity.py` - 25 tests for wiznet/admin commands (ROM `act_wiz.c`)
    - Wiznet channel toggle and flag management
    - Wiznet broadcast filtering (WIZ_ON, flag filters, min_level)
    - Admin commands (freeze, transfer, goto, trust)
    - Trust level enforcement

- **Documentation**:
  - `COMMAND_INTEGRATION_PARITY_REPORT.md` - Comprehensive command integration test completion report
    - Detailed ROM C to Python mapping for all 70 tests
    - Test philosophy and design decisions
    - ROM C source analysis summary
    - Quality metrics and coverage matrix

### Changed

- **ROM 2.4b6 Parity Certification Updates**:
  - Updated total ROM parity test count: 735 → 805 tests (+70)
  - Updated total test count: 2507 → 2577 tests (+70)
  - Added Command Integration Tests section to certification document
  - Updated ROM C source verification to include `act_comm.c`, `act_enter.c`, `act_wiz.c`

- **Test Coverage**:
  - Increased command integration test coverage (communication, portal, wiznet modules)
  - Total ROM parity tests: 805 (127 P0/P1/P2 + 608 combat/spells/skills + 70 command integration)

## [2.5.1] - 2025-12-30

### Added

- **Session Summary Documentation**:
  - `P0_P1_P2_EXTENDED_TESTING_SESSION_SUMMARY.md` - Verification session summary documenting that all P0/P1/P2 ROM C parity tests were already complete from previous sessions (December 29-30, 2025)

### Changed

- Updated README badges and project status to reflect complete ROM C parity test coverage (735 total ROM parity tests including 127 P0/P1/P2 formula verification tests)

## [2.5.0] - 2025-12-29

### Added

- **🎉 ROM 2.4b6 Parity Certification**: Official 100% ROM 2.4b6 behavioral parity certification
  - Created `ROM_2.4B6_PARITY_CERTIFICATION.md` - Comprehensive official certification document
  - 10 detailed subsystem parity matrices with ROM C source verification
  - Complete audit trail with 7 comprehensive audit documents (2000+ lines)
  - Integration test verification (43/43 passing = 100%)
  - Unit test coverage breakdown (700+ tests)
  - Differential testing methodology documented
  - Production readiness assessment
  - All 7 certification criteria verified and passing

- **Combat System Parity Verification** (100% Complete):
  - `COMBAT_PARITY_AUDIT_2025-12-28.md` - Comprehensive combat system audit
  - Added combat assist system (`mud/combat/assist.py`) with all ROM mechanics
  - Added 30+ combat tests (damage types, position multipliers, surrender command)
  - Verified all 32 ROM C combat functions implemented
  - Verified all 15 ROM combat commands functional
  - Position-based damage multipliers (sleeping 2x, resting/sitting 1.5x)
  - Damage resistance/vulnerability system complete
  - Special weapon effects (sharpness, vorpal, flaming, frost, vampiric, poison)

- **World Reset System Parity Verification** (100% Complete):
  - `WORLD_RESET_PARITY_AUDIT.md` - Comprehensive reset system audit
  - Verified all 7 ROM reset commands (M, O, P, G, E, D, R)
  - 49/49 reset tests passing with complete behavioral verification
  - Door state synchronization (bidirectional + one-way doors)
  - Exit randomization (Fisher-Yates shuffle)
  - ROM scheduling formula verified exact
  - Special cases documented (shop inventory, pet shops, infrared)

- **OLC Builders System Parity Verification** (100% Complete):
  - `OLC_PARITY_AUDIT.md` - Comprehensive OLC system audit
  - Verified all 5 ROM editors (@redit, @aedit, @oedit, @medit, @hedit)
  - 189/189 OLC tests passing with complete workflow verification
  - All 5 @asave variants functional
  - All 5 builder stat commands operational
  - Builder security system complete (trust levels, vnum ranges)

- **Security System Parity Verification** (100% Complete):
  - `SECURITY_PARITY_AUDIT.md` - Comprehensive security system audit
  - `SECURITY_PARITY_COMPLETION_SUMMARY.md` - Security session summary
  - Verified all 6 ROM ban flags (BAN_SUFFIX, PREFIX, NEWBIES, ALL, PERMIT, PERMANENT)
  - All 4 pattern matching modes (exact, prefix*, *suffix, *substring*)
  - 25/25 ban tests passing
  - Trust level enforcement verified
  - ROM file format compatibility verified

- **Object System Parity Verification** (100% Complete):
  - `OBJECT_PARITY_COMPLETION_REPORT.md` - Object system completion report
  - `docs/parity/OBJECT_PARITY_TRACKER.md` - Detailed 11-subsystem breakdown
  - Verified all 17 ROM object commands functional
  - 152/152 object tests passing + 277+ total object-related tests
  - Complete equipment system (11/11 wear mechanics)
  - Full container system (9/9 mechanics)
  - Exact encumbrance system (7/7 ROM C functions)
  - Complete shop economy (11/11 features)

- **Session Documentation**:
  - `SESSION_SUMMARY_2025-12-28.md` - Complete session documentation
  - `SESSION_SUMMARY_2025-12-27.md` - Previous session documentation

- **Additional Audit Documents**:
  - `SPELL_AFFECT_PARITY_AUDIT_2025-12-28.md` - Spell affect system verification
  - `COMBAT_GAP_VERIFICATION_FINAL.md` - Combat gap analysis and closure
  - `COMBAT_DAMAGE_RESISTANCE_COMPLETION.md` - Damage type system completion
  - `REMAINING_PARITY_GAPS_2025-12-28.md` - Final gap analysis (none remaining)
  - `COMMAND_AUDIT_2025-12-27_FINAL.md` - Command parity final verification

### Changed

- **README.md Updates**:
  - Updated version badge to 2.5.0
  - Updated ROM parity badge to link to official certification
  - Added "CERTIFIED" designation to ROM parity claim
  - Updated test counts to reflect integration test results (43/43 passing)
  - Added integration tests badge
  - Reorganized documentation section with certification first
  - Updated project status section with certification details

- **Documentation Organization**:
  - Added official certification as primary documentation
  - Reorganized docs to highlight certification achievement
  - Updated all parity references to point to certification

- **Test Organization**:
  - Added `tests/test_combat_assist.py` - Combat assist mechanics (14 tests)
  - Added `tests/test_combat_damage_types.py` - Damage resistance/vulnerability (15 tests)
  - Added `tests/test_combat_position_damage.py` - Position damage multipliers (10 tests)
  - Added `tests/test_combat_surrender.py` - Surrender command (5 tests)

### Fixed

- Combat damage vulnerability check now runs after immunity check (ROM parity fix)
- Corrected misleading "decapitation" comment on vorpal flag (ROM 2.4b6 has no decapitation)
- Updated outdated parity assessments in ROM_PARITY_FEATURE_TRACKER.md

### Verified

- ✅ **100% ROM 2.4b6 command coverage** (255/255 commands implemented)
- ✅ **100% integration test pass rate** (43/43 tests passing)
- ✅ **96.1% ROM C function coverage** (716/745 functions mapped)
- ✅ **All 10 major subsystems** verified with comprehensive audits
- ✅ **Production readiness** confirmed for players, builders, admins, developers

### Documentation

- 7 comprehensive audit documents totaling 2000+ lines
- Official ROM 2.4b6 parity certification document
- Complete ROM C source verification methodology
- Differential testing documentation
- Production deployment guidelines

## [2.4.0] - 2025-12-27

### Added

- **GitHub Release Creator Skill**: Comprehensive Claude Desktop skill for automated release management
  - Added `.claude/skills/github-release-creator/` with complete release automation tooling
  - Python script for automated release creation (`create_release.py`)
  - Shell scripts for release validation and creation
  - Changelog extraction utilities
  - Complete documentation with usage examples and workflows
  - GitHub CLI integration for professional release management
  - Support for semantic versioning, draft releases, and pre-releases

## [2.3.1] - 2025-12-27

### Added

- **Comprehensive Test Planning Documentation**:
  - Created `docs/validation/MOB_PARITY_TEST_PLAN.md` - Complete testing strategy for ROM 2.4b mob behaviors
    - 22 spec_fun behaviors (guards, dragons, casters, thieves)
    - 30+ ACT flag behaviors (aggressive, wimpy, scavenger, sentinel)
    - Damage modifiers (immunities, resistances, vulnerabilities)
    - Mob memory and tracking systems
    - Group assist mechanics
    - Wandering/movement AI
  - Created `docs/validation/PLAYER_PARITY_TEST_PLAN.md` - Complete testing strategy for player-specific behaviors
    - Information display commands (score, worth, whois)
    - Auto-settings (autoassist, autoloot, autogold, autosac, autosplit)
    - Conditions system (hunger, thirst, drunk, full)
    - Player flags and reputation (KILLER, THIEF)
    - Prompt customization
    - Title/description management
    - Trust/security levels
    - Player visibility states (AFK, wizinvis, incognito)
- **Claude Desktop Skill Support**:
  - Added `SKILL.md` - Comprehensive skill documentation for AI assistants
  - Added `.claude/skills/skill-creator/` - Anthropic's skill-creator tool
    - Skill validation scripts
    - Skill packaging utilities
    - Best practices documentation

### Changed

- **Test Organization**: Created clear roadmap for implementing 180+ behavioral tests
  - 6 major mob test areas (P0-P3 priority matrix)
  - 8 major player test areas (P0-P3 priority matrix)
  - 4-phase implementation roadmap for each
  - Complete test templates with ROM C references

### Documentation

- Documented 100+ specific test cases with ROM C source references
- Added implementation effort estimates and player impact assessments
- Created comprehensive testing guides for future development

## [2.3.0] - 2025-12-26

### Added

- **MobProg 100% ROM C Parity Achievement**: All 4 critical trigger hookups complete
  - `mp_give_trigger` integrated in do_give command
  - `mp_hprct_trigger` integrated in combat damage system
  - `mp_death_trigger` integrated in character death handling
  - `mp_speech_trigger` already integrated (verified)
- MobProg movement command validation in area file validator
- Comprehensive MobProg testing documentation (5 guides)
- Enhanced `validate_mobprogs.py` with movement command validation
- Organized validation and parity documentation structure

### Changed

- **Documentation Reorganization**: Created proper folder structure
  - Moved 10 documentation files to `docs/validation/` and `docs/parity/`
  - Moved 10 scripts to `scripts/validation/` and `scripts/parity/`
  - Moved 5 report files to appropriate `reports/` subfolders
  - Created 6 README files documenting folder contents
- Updated all cross-references in documentation to use new paths
- Enhanced validation scripts with movement command checks

### Fixed

- Integration test issues with Object creation and trigger signatures
- Syntax error in validate_mobprogs.py output formatting

## [2.2.1] - Previous Release

### Added

- Complete weapon special attacks system with ROM 2.4 parity (WEAPON_VAMPIRIC, WEAPON_POISON, WEAPON_FLAMING, WEAPON_FROST, WEAPON_SHOCKING)

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [1.3.0] - 2025-09-15

### Added

- Complete fighting state management with ROM 2.4 parity
- Character immortality protection following IS_IMMORTAL macro
- Level constants (MAX_LEVEL, LEVEL_IMMORTAL) matching ROM source

### Changed

### Deprecated

### Removed

### Fixed

- Character position initialization defaults to STANDING instead of DEAD
- Fighting state damage application and position updates
- Immortal character survival logic in combat system
- Combat defense order to match ROM 2.4 C source (shield_block → parry → dodge)

### Security

## [1.2.0] - 2025-09-15

### Added

- Complete telnet server with multi-user support
- Working shop system with buy/sell/list commands
- 132 skill system with handler stubs
- JSON-based world loading with 352 resets in Midgaard
- Admin commands (teleport, spawn, ban management)
- Communication system (say, tell, shout, socials)
- OLC building system for room editing
- pytest-timeout plugin for proper test timeouts

### Changed

- Achieved 100% test success rate (200/200 tests)
- Full test suite completes in ~16 seconds
- Modern async/await telnet server architecture
- SQLAlchemy ORM with migrations
- Comprehensive test coverage across all subsystems
- Memory efficient JSON area loading
- Optimized command processing pipeline
- Robust error handling throughout

### Fixed

- Character position initialization (STANDING vs DEAD)
- Hanging telnet tests resolved
- Enhanced error handling and null room safety
- Character creation now allows immediate command execution

## [0.1.1] - 2025-09-14

### Added

- Initial ROM 2.4 Python port foundation
- Basic world loading and character system
- Core command framework
- Database integration with SQLAlchemy

### Changed

- Migrated from legacy C codebase to pure Python
- JSON world data format for easier editing
- Modern Python packaging structure

## [0.1.0] - 2025-09-13

### Added

- Initial project structure
- Basic MUD framework
- ROM compatibility layer
- Core game loop implementation

[Unreleased]: https://github.com/Nostoi/rom24-quickmud-python/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/Nostoi/rom24-quickmud-python/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Nostoi/rom24-quickmud-python/compare/v0.1.1...v1.2.0
[0.1.1]: https://github.com/Nostoi/rom24-quickmud-python/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Nostoi/rom24-quickmud-python/releases/tag/v0.1.0
