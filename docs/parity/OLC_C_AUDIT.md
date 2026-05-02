# `olc.c` ROM Parity Audit

- **Status**: ⚠️ Partial 58% — Phase 4 underway (2026-05-01). OLC cluster (`olc.c` + `olc_act.c` + `olc_save.c` + `olc_mpcode.c` + `hedit.c`) remains the largest remaining audit bundle, but descriptor plumbing, reset surfaces, entry commands, the unified OLC router, prompt `%o` / `%O`, and `commands` listings are now substantially closed.
- **Date**: 2026-04-29
- **Source**: `src/olc.c` (ROM 2.4b6, 1502 lines, 19 public functions + 5 dispatch tables)
- **Python primaries**:
  - `mud/commands/build.py` (per-editor session interpreters: `cmd_aedit`/`cmd_redit`/`cmd_oedit`/`cmd_medit`/`cmd_hedit` and `_interpret_*`)
  - `mud/commands/imm_olc.py` (`do_resets`, `do_alist`, `do_edit`, `do_mpedit` — stubs)
  - `mud/utils/prompt.py` (would consume `olc_ed_name`/`olc_ed_vnum` — currently emits `""` for `%o`/`%O`)
  - `mud/olc/__init__.py`, `mud/olc/save.py` (skeleton — `save_area_to_json` only)

`olc.c` is the **command-dispatch shell** of the ROM OLC subsystem. It does *not*
contain the per-field builders (those live in `olc_act.c`) or the persistence
logic (those live in `olc_save.c`). Its job is:

1. Hold the five `*edit_table[]` command tables (`aedit`/`redit`/`oedit`/`medit`/`mpedit` — `hedit_table` lives in `hedit.c`).
2. Dispatch raw input from `comm.c::game_loop` to the right per-editor interpreter via `run_olc_editor`.
3. Provide the user-facing `olc <subcmd>`, `aedit <vnum>`, `redit`, `oedit <vnum>`, `medit <vnum>` entry points.
4. Provide cluster utilities: `display_resets`, `add_reset`, `do_resets`, `do_alist`, `olc_ed_name`/`olc_ed_vnum` (for the prompt token `%o`/`%O`), `edit_done`.

The Python port *partially* covers (3) — there are session-level `cmd_aedit` / `cmd_redit` / `cmd_oedit` / `cmd_medit` / `cmd_hedit` entry points and per-editor interpreters (`_interpret_aedit` …) — but does not match ROM's behavior on (1) the `flag_value()` table-toggle prefix, (2) the `do_olc` dispatcher, (3) the unified `run_olc_editor` raw-input router, or (4) the prompt `%o/%O` tokens. (5) is mostly absent: `do_resets` and `do_alist` in `mud/commands/imm_olc.py` are stubs that only cover ~30% of the ROM cases.

---

## Prerequisite infrastructure (not in `olc.c`, but blocks closure)

Closing OLC parity gaps requires descriptor-level editor plumbing that does not yet exist in `mud/net/connection.py` or `mud/account/session.py`:

- **`pString` field** on the descriptor / session — pointer to the buffer being edited (room desc, mob desc, obj desc, ED text, mprog source, help text).
- **`editor` enum** — `ED_NONE`/`ED_AREA`/`ED_ROOM`/`ED_OBJECT`/`ED_MOBILE`/`ED_MPCODE`/`ED_HELP` (ROM `src/olc.h:57-63`). Python today uses a *string* (`session.editor in {"redit","aedit","oedit","medit","hedit"}`) + a `session.editor_state` dict — that suffices for the per-editor dispatcher but NOT for the string-editor mode (ROM uses `desc->pString != NULL` to distinguish "user is in OLC command mode" from "user is dumping raw text into a description").
- **Game-loop dispatch hook** in `mud/game_loop.py` (or wherever raw input is read post-login) that routes:
  1. If `desc->pString != NULL` → call `string_add(ch, input)` (ROM `src/string.c:121-286`, gap STRING-004).
  2. Else if `desc->editor != ED_NONE` → call `run_olc_editor(desc)` (ROM `src/olc.c:37-63`, gap OLC-001).
  3. Else → normal command interpreter.

This carve-out is **OLC-INFRA-001** (a single blocking gap, not a backlog item) and must be the first commit of the OLC closure work, before any per-command gap is touched.

---

## Phase 1 — Function inventory

| ROM symbol | ROM lines | Visibility | Purpose | Python counterpart | Status |
|------------|-----------|------------|---------|--------------------|--------|
| `run_olc_editor` | 37-63 | public | Raw-input router: dispatch to `aedit`/`redit`/`oedit`/`medit`/`mpedit`/`hedit` based on `desc->editor` | `mud/commands/dispatcher.py:_process_descriptor_input` + `_olc_handler_from_session` | ✅ FIXED (OLC-001) |
| `olc_ed_name` | 67-97 | public | Prompt `%o` token: `"AEdit"`/`"REdit"`/… string for current editor | `mud/utils/prompt.py:_olc_ed_name` | ✅ FIXED (OLC-002) |
| `olc_ed_vnum` | 101-144 | public | Prompt `%O` token: vnum (or keyword for `ED_HELP`) of currently-edited entity | `mud/utils/prompt.py:_olc_ed_vnum` | ✅ FIXED (OLC-003) |
| `show_olc_cmds` | 153-175 | public | Format command table as 5-column listing | `mud/commands/build.py:_show_olc_cmds` | ✅ FIXED (OLC-004) |
| `show_commands` | 184-209 | public | Dispatch `commands` to the right `show_olc_cmds` based on `desc->editor` | `mud/commands/build.py:_interpret_*edit` `commands` branches | ✅ FIXED (OLC-005) |
| `aedit_table[]` | 216-238 | data | Area-editor command table (15 entries) | `_interpret_aedit` (`build.py:1261-1376`) inlines a Python equivalent — **not** a data-driven `(name, fn)` table | ⚠️ PARTIAL (OLC-006) |
| `redit_table[]` | 242-279 | data | Room-editor command table (29 entries) | `_interpret_redit` (`build.py:961-1069`) inlines | ⚠️ PARTIAL (OLC-007) |
| `oedit_table[]` | 283-315 | data | Object-editor command table (24 entries) | `_interpret_oedit` (`build.py:1477-1613`) inlines | ⚠️ PARTIAL (OLC-008) |
| `medit_table[]` | 319-362 | data | Mobile-editor command table (38 entries) | `_interpret_medit` (`build.py:1761-1976`) inlines | ⚠️ PARTIAL (OLC-009) |
| `editor_table[]` | 646-657 | data | Top-level `olc <subcmd>` dispatch (6 entries) | — | ❌ MISSING (OLC-010) |
| `get_area_data` | 375-386 | public (file-local) | Area-by-vnum lookup helper | `mud/registry.py::area_registry.get(vnum)` covers behavior, no named helper | ✅ AUDITED — equivalent via `area_registry` |
| `edit_done` | 395-400 | public | Reset `desc->pEdit = NULL; desc->editor = 0` and return FALSE | `mud/commands/build.py:139-141` `_clear_session` (sets `session.editor = None`) — equivalent semantics, different shape | ✅ AUDITED |
| `aedit` (interpreter) | 410-469 | public | Per-input area-editor dispatcher: `flag_value(area_flags, command)` toggle, then `aedit_table` lookup, then fallback to `interpret()` | `_interpret_aedit` (`build.py:1261`) — covers table dispatch only, **no** `flag_value(area_flags, …)` toggle prefix, **no** `interpret()` fallback | ⚠️ PARTIAL (OLC-011) |
| `redit` (interpreter) | 474-527 | public | Per-input room-editor dispatcher; `interpret()` fallback | `_interpret_redit` (`build.py:961`) — table dispatch only, no `interpret()` fallback | ⚠️ PARTIAL (OLC-012) |
| `oedit` (interpreter) | 532-584 | public | Per-input object-editor dispatcher; `interpret()` fallback | `_interpret_oedit` (`build.py:1477`) — table dispatch only, no `interpret()` fallback | ⚠️ PARTIAL (OLC-013) |
| `medit` (interpreter) | 589-641 | public | Per-input mobile-editor dispatcher; `interpret()` fallback | `_interpret_medit` (`build.py:1761`) — table dispatch only, no `interpret()` fallback | ⚠️ PARTIAL (OLC-014) |
| `do_olc` | 661-690 | public | User entry point: parse `olc <subcmd>` and route via `editor_table` | — (no `do_olc` command in dispatcher; user must type `aedit`/`redit`/`oedit`/`medit` directly) | ❌ MISSING (OLC-015) |
| `do_aedit` | 695-740 | public | User entry: `aedit <vnum>` / `aedit create` → set `desc->pEdit` + `desc->editor = ED_AREA` | `cmd_aedit` + `_aedit_create` (`build.py`) — `create` keyword wired in OLC_ACT-001. | ✅ FIXED (OLC-016 via OLC_ACT-001) |
| `do_redit` | 745-821 | public | User entry: `redit reset` / `redit create <vnum>` / `redit <vnum>` / no-arg | `cmd_redit` + `_redit_create` + `_redit_vnum_teleport` + `_apply_resets_for_redit` (`build.py`) — all three subpaths wired in OLC_ACT-002/003/004. | ✅ FIXED (OLC-017 via OLC_ACT-002/003/004) |
| `do_oedit` | 826-895 | public | User entry: `oedit <vnum>` / `oedit create <vnum>` | `cmd_oedit` + `_oedit_create` (`build.py`) — `create` keyword wired with full validation chain in OLC_ACT-005. | ✅ FIXED (OLC-018 via OLC_ACT-005) |
| `do_medit` | 900-969 | public | User entry: `medit <vnum>` / `medit create <vnum>` | `cmd_medit` + `_medit_create` (`build.py`) — `create` keyword wired + `ACT_IS_NPC` flag set on new mobs (OLC_ACT-006). | ✅ FIXED (OLC-019 via OLC_ACT-006) |
| `display_resets` | 973-1183 | public | Format `pRoom->reset_first` linked list as the 8-column table (M/O/P/G/E/D/R commands + pet-shop detection on `R[%5d-1]`) | `mud/commands/imm_olc.py:_display_resets` | ✅ FIXED (OLC-020) |
| `add_reset` | 1192-1228 | public | Insert reset at 1-indexed position in `room->reset_first`/`reset_last` linked list (negative idx → tail; idx=1 → head) | `mud/commands/imm_olc.py:_add_reset` | ✅ FIXED (OLC-021) |
| `do_resets` | 1232-1469 | public | Top-level `resets` command: display, add `M`/`O`/`P` (with `inside`/`room`/wear-loc subcases), add `R`andom-exits, delete | `mud/commands/imm_olc.py:do_resets` | ✅ FIXED (OLC-022) |
| `do_alist` | 1478-1502 | public | List all areas with vnum range / filename / security / builders, header row included | `mud/commands/imm_olc.py:do_alist:121-146` — iterates `area_registry.values()`, prints `area.vnum` + `file_name`. | ✅ AUDITED (OLC-023 fixed) |

### Reverse-direction missing infrastructure

| Symbol | Why missing matters | Gap ID |
|--------|---------------------|--------|
| `desc->pString` field | Required by `string_add` raw-input dispatch (STRING-001..012) and by `redit_desc`/`medit_desc`/`oedit_long`/`oedit_short`/`medit_long`/MPCODE editor entry points in `olc_act.c`. | OLC-INFRA-001 |
| `desc->editor` integer enum | Currently a string `session.editor`; ROM's `run_olc_editor` switch and `olc_ed_name/_vnum` consume the integer. | OLC-INFRA-001 |
| Game-loop string-editor hook | Without it, no `string_add` call is ever issued; STRING-001..012 are uncloseable. | OLC-INFRA-001 |
| `flag_value(table, argument)` standalone helper | Required by `aedit` flag-toggle prefix, `do_resets` wear-loc gate, every `oedit_extra`/`oedit_wear`/`medit_act`/`medit_affect`/etc. builder in `olc_act.c`. | BIT-001 (already filed) |
| `flag_string(table, bits)` decoder | Required by `display_resets` (wear-loc + door-reset decode) and every `*_show` builder in `olc_act.c`. | BIT-002 (already filed) |
| `weapon_table` data port | Required by `oedit` weapon-class display. | CONST-007 (already filed) |

---

## Phase 2 — Verification (load-bearing functions)

### `run_olc_editor` (ROM 37-63) — OLC-001

Sole caller in ROM is `comm.c::game_loop_unix` / `game_loop_mac`, gated on `desc->pString == NULL && desc->editor != ED_NONE`. Behavior is a 6-way switch on `desc->editor` to call one of `aedit`/`redit`/`oedit`/`medit`/`mpedit`/`hedit` with `d->incomm` (the raw input line).

Python today routes input differently: `mud/commands/dispatcher.py` reads the input, looks up `Command` by name, and calls `Command.handler(char, args)`. There is no per-descriptor "we are in OLC mode, route everything to the editor interpreter" branch. Each per-editor `handle_*_command` (`handle_redit_command`, `handle_aedit_command`, …) exists but is never invoked from the game loop — it is only called from `cmd_redit`/`cmd_aedit`/etc. (which are in turn invoked as normal commands). So the user's experience is: type `@redit` (toggle session.editor), then EVERY subsequent input goes through the *normal* command dispatcher, which special-cases `session.editor == "redit"` to route to `_interpret_redit`. Functionally close to ROM but not identical: ROM's `aedit` falls back to `interpret(ch, arg)` for unknown commands, and Python does too via the normal dispatcher path — but the *order* is reversed. ROM tries the editor table FIRST and falls through to the interpreter; Python always goes through the interpreter and special-cases the editor command set. Not a behavioral gap if the per-editor command names don't collide with normal commands; they sometimes do (e.g. `look`/`l`, `show`/`s`).

Closed 2026-05-01. `process_command()` now mirrors the ROM descriptor decision tree by calling `route_descriptor_input()` first, routing `session.string_edit` to `string_add()`, and routing OLC descriptors through `_process_descriptor_input()` / `_olc_handler_from_session()` before normal command interpretation. The Python port keeps the pragmatic wrapper fallback for still-open OLC-012/013/014 paths: if an editor handler reports an unknown editor command, control falls through to the normal interpreter, preserving pre-existing user-facing behavior while the per-editor fallback gaps remain tracked separately.

### `olc_ed_name` / `olc_ed_vnum` (ROM 67-144) — OLC-002, OLC-003

Closed 2026-05-01. `mud/utils/prompt.py` now mirrors ROM `olc_ed_name()` / `olc_ed_vnum()` by reading `char.desc.editor_mode` first, tolerating the legacy `session.editor` string as a fallback, and rendering `%o` / `%O` through `_olc_ed_name()` / `_olc_ed_vnum()`. The Python port follows ROM's room special-case (`ED_ROOM` uses `ch->in_room`) and maps editor targets through the existing OLC session state: `area`, `obj_proto`, `mob_proto`, `help`. Help prompts render the Python help entry's keyword list as the ROM-equivalent keyword string. Locked by `tests/integration/test_prompt_rom_parity.py`.

### `do_olc` / `editor_table[]` (ROM 646-690) — OLC-010, OLC-015

ROM exposes `olc <area|room|object|mobile|mpcode|hedit>` as a single user-facing command that routes to the relevant `do_*edit`. Python registers `aedit`/`redit`/`oedit`/`medit`/`hedit`/`mpedit` *individually* in `dispatcher.py:474-492`. The user-facing surface is functionally the same (a builder can type either `olc room` or `redit` in ROM; only `redit` works in Python). MINOR — ROM users transferring habits may try `olc room` and fail.

### `aedit` interpreter (ROM 410-469) — OLC-011

ROM signature: `void aedit(CHAR_DATA *ch, char *argument)`. Behavior:

1. `EDIT_AREA(ch, pArea)` — fetch from `desc->pEdit`.
2. `smash_tilde(argument)`.
3. `one_argument(argument, command)` — peel first token.
4. `IS_BUILDER` security check.
5. `if !str_cmp(command, "done")` → `edit_done`, return.
6. **`if (value = flag_value(area_flags, command)) != NO_FLAG` → `TOGGLE_BIT(pArea->area_flags, value)`, send "Flag toggled.\n\r", return.** This is the load-bearing divergence. ROM lets the builder toggle area flags by typing `nochannels` / `noteleport` / etc. directly without a subcommand, because the table-toggle prefix is checked before the named commands. Python `_interpret_aedit` has no equivalent path.
7. Iterate `aedit_table` with `str_prefix` matching, dispatch.
8. Fall through to `interpret(ch, arg)` for unknown commands.

Python `_interpret_aedit`:
- Checks `done` (✅).
- No `flag_value(area_flags, …)` toggle prefix (❌).
- Iterates a Python equivalent of the command table (✅).
- No fallback to normal command interpreter (✅ in practice — the dispatcher does this implicitly).

Same shape applies to `redit`/`oedit`/`medit` (OLC-012/013/014). Only `aedit` has the flag-toggle prefix; the other three only need the dispatcher table + interpreter fallback alignment.

### `do_aedit` / `do_redit` / `do_oedit` / `do_medit` (ROM 695-969) — OLC-016/017/018/019

These are the **entry points** the user types from the normal command interpreter to *enter* an editor. They differ from the per-input interpreters above. ROM behavior:

- `do_aedit`: `aedit <vnum>` (numeric → switch to that area), `aedit create` (security≥9, call `aedit_create`), default → switch to current room's area.
- `do_redit`: `redit reset` (call `reset_room`), `redit create <vnum>` (call `redit_create`, then teleport via `char_from_room`/`char_to_room`), `redit <vnum>` (jump + teleport), default → edit current room.
- `do_oedit`: `oedit <vnum>` (jump), `oedit create <vnum>` (security via `get_vnum_area`).
- `do_medit`: `medit <vnum>` (jump), `medit create <vnum>` (security via `get_vnum_area`).

Python `cmd_aedit` / `cmd_redit` / `cmd_oedit` / `cmd_medit` cover only the simplest path (no-arg or numeric-vnum). All four are missing the `create` subcommand and (for `redit`) the `reset` subcommand and the teleport-on-jump behavior. **CRITICAL functionally** — without `create`, no new areas/rooms/mobs/objects can be made through OLC at all.

### `display_resets` (ROM 973-1183) — OLC-020

ROM walks `pRoom->reset_first` linked list and emits one of seven per-reset formats (M / O / P / G / E / D / R). Each format uses `flag_string(wear_loc_strings | door_resets, arg)` to decode bit-fields, plus a `pet-shop` peek (overwrites column-5 with `'P'` if `room.vnum-1` has `ROOM_PET_SHOP`).

Python `do_resets` display block (`imm_olc.py:39-53`) emits `[NN] X arg1 arg2 arg3` with no per-command formatting, no flag decoding, no pet-shop detection. IMPORTANT — visible UX gap.

### `do_resets` (ROM 1232-1469) — OLC-022

ROM supports:
- No-arg → `display_resets`.
- `<num> delete` → unlink reset at index from doubly-linked list.
- `<num> mob <vnum> [max#area] [max#room]` → emit `M` reset.
- `<num> obj <vnum> inside <containerVnum> [limit] [count]` → emit `P` reset.
- `<num> obj <vnum> room` → emit `O` reset.
- `<num> obj <vnum> <wear-loc>` → emit `G` (if WEAR_NONE) or `E` reset.
- `<num> random <#exits>` → emit `R` reset (1≤n≤6).
- Bad input → 6-line syntax block.

Python covers display + delete + naive `mob`/`obj` (no wear-loc, no `inside`, no `room`, no `random`, no syntax block). IMPORTANT.

### `do_alist` (ROM 1478-1502) — OLC-023

ROM iterates `area_first` linked list and emits `[Num] [Name] (lvnum-uvnum) [Filename] Sec [Builders]`. Python `do_alist` iterates `getattr(registry, "areas", [])` — `mud/registry.py` exports `area_registry` (a dict), not `areas` (a list). The `getattr(..., [])` default kicks in and the function emits header + zero rows on a live system. **BROKEN, not just partial.**

### `add_reset` (ROM 1192-1228) — OLC-021

ROM uses a doubly-linked list (`reset_first`/`reset_last` on `ROOM_INDEX_DATA`); inserts at 1-indexed position with negative-or-zero idx → tail, idx=1 → head. Python uses a Python `list` and `list.insert(idx-1, …)`. The semantics differ on idx≤0 (Python: clamps to 0 = head; ROM: walks to tail). MINOR — but a parity gap.

---

## Phase 3 — Gaps

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `OLC-INFRA-001` | CRITICAL | `src/olc.h:57-63`, `src/comm.c:833-847` | `mud/olc/editor_state.py` (new), `mud/net/session.py:32-39` | Descriptor-level editor plumbing missing: `pString` buffer pointer, integer `editor` enum (`ED_NONE`/`ED_AREA`/…/`ED_HELP`), and the game-loop dispatch hook that routes raw input to `string_add` when `pString != NULL`. Blocks STRING-001..012 closure entirely; also blocks any OLC builder that opens a string editor (`redit desc`, `medit desc`, etc.). | ✅ FIXED — `EditorMode` IntEnum (mirrors `src/olc.h:53-59`), `StringEdit` dataclass (mirrors `desc->pString`), `route_descriptor_input()` (mirrors `src/comm.c:833-847`) added; `Session.editor_mode` + `Session.string_edit` fields wired. Test: `tests/integration/test_olc_descriptor_state.py`. Destinations (`string_add` / `run_olc_editor`) remain deferred to STRING-004 / OLC-001. |
| `OLC-001` | IMPORTANT | `src/olc.c:37-63` | `mud/commands/dispatcher.py:_process_descriptor_input`, `_olc_handler_from_session`, `process_command`; `mud/commands/build.py:_ensure_session_*`; `mud/olc/editor_state.py:route_descriptor_input` | `process_command()` now branches on descriptor route before normal interpretation, sends `STRING_EDIT` descriptors to `string_add()`, routes OLC descriptors by `EditorMode`, and preserves normal-command fallback when a still-partial OLC interpreter reports an unknown editor command. The companion parser fix to `_split_command_and_args()` now treats `@redit`/`@aedit`/etc. as full command tokens instead of the one-character `@` alias, restoring the OLC entry path used by existing tests and builders. | ✅ FIXED — tests: `tests/integration/test_olc_001_run_olc_editor.py` (4 cases), `tests/test_building.py` (14-pass OLC smoke slice) |
| `OLC-002` | MINOR | `src/olc.c:67-97` | `mud/utils/prompt.py:_olc_ed_name`, `mud/utils/prompt.py:bust_a_prompt` | Closed: `%o` now renders ROM editor labels (`AEdit`, `REdit`, `OEdit`, `MEdit`, `MPEdit`, `HEdit`) from descriptor OLC state, with a fallback to the legacy `session.editor` string where needed. | ✅ FIXED — tests in `tests/integration/test_prompt_rom_parity.py` |
| `OLC-003` | MINOR | `src/olc.c:101-144` | `mud/utils/prompt.py:_olc_ed_vnum`, `mud/utils/prompt.py:bust_a_prompt` | Closed: `%O` now renders ROM editor targets from descriptor OLC state (`area.vnum`, `room.vnum`, `obj_proto.vnum`, `mob_proto.vnum`, help keywords). `ED_ROOM` follows ROM by using the live room vnum from `ch->in_room`. | ✅ FIXED — tests in `tests/integration/test_prompt_rom_parity.py` |
| `OLC-004` | MINOR | `src/olc.c:153-175` | `mud/commands/build.py:_show_olc_cmds` | Closed: OLC command tables now format as ROM's five 15-character columns, including final newline handling. | ✅ FIXED — tests in `tests/integration/test_olc_commands_listing.py` |
| `OLC-005` | MINOR | `src/olc.c:184-209` | `mud/commands/build.py:_interpret_aedit`, `_interpret_redit`, `_interpret_oedit`, `_interpret_medit`, `_interpret_hedit` | Closed: active editors now route `commands` to the correct ROM command-name table for area, room, object, mobile, and help editors. | ✅ FIXED — tests in `tests/integration/test_olc_commands_listing.py` |
| `OLC-006` | IMPORTANT | `src/olc.c:216-238` | `mud/commands/build.py:1261-1376` | `aedit_table[]` (15 entries) not ported as a data-driven `(name, fn)` table. Python inlines the dispatch in `_interpret_aedit`. Closing means extracting a tuple/list and the builders themselves, in tandem with `olc_act.c` audit. | 🔄 OPEN |
| `OLC-007` | IMPORTANT | `src/olc.c:242-279` | `mud/commands/build.py:_interpret_redit` | `rlist`, `mlist`, `olist`, `mshow`, `oshow` added; helper functions `_redit_rlist/mlist/olist/mshow/oshow` port ROM `src/olc_act.c:329-570`. All other `redit_table[]` entries (`mreset`, `oreset`, `format`, `heal`, `mana`, `clan`, `owner`, `room`, `sector`, directions) were already implemented. Data-driven table refactor deferred. | ✅ FIXED |
| `OLC-008` | IMPORTANT | `src/olc.c:283-315` | `mud/commands/build.py:1477-1613` | `oedit_table[]` (24 entries) not ported as a data table; missing entries: `addaffect`, `addapply`, `delaffect`, `v0..v4`, `extra`, `wear`, `material`, `level`, `condition`. | 🔄 OPEN |
| `OLC-009` | IMPORTANT | `src/olc.c:319-362` | `mud/commands/build.py:1761-1976` | `medit_table[]` (38 entries) not ported as a data table; missing entries include `affect`, `armor`, `form`, `part`, `imm`, `res`, `vuln`, `material`, `off`, `size`, `hitdice`, `manadice`, `damdice`, `position`, `wealth`, `hitroll`, `damtype`, `group`, `addmprog`, `delmprog`. | 🔄 OPEN |
| `OLC-010` | MINOR | `src/olc.c:646-657` | `mud/commands/imm_olc.py:do_edit` | `editor_table[]` 6-entry top-level dispatch ported as `_EDITOR_TABLE` list inside `do_edit`. | ✅ FIXED (OLC-015) |
| `OLC-011` | IMPORTANT | `src/olc.c:410-469` | `mud/commands/build.py:_interpret_aedit` | `aedit` interpreter now checks `flag_value(AreaFlag, command)` before table dispatch; matching flag name toggles the bit on `area_flags` and returns `"Flag toggled."` — mirrors ROM `src/olc.c:443-449`. | ✅ FIXED |
| `OLC-012` | MINOR | `src/olc.c:474-527` | `mud/commands/build.py:961` | `redit` interpreter missing explicit fallback to `interpret()` for unknown commands. (Python dispatcher route makes this functionally close.) | 🔄 OPEN |
| `OLC-013` | MINOR | `src/olc.c:532-584` | `mud/commands/build.py:1477` | `oedit` interpreter missing explicit fallback to `interpret()`. | 🔄 OPEN |
| `OLC-014` | MINOR | `src/olc.c:589-641` | `mud/commands/build.py:1761` | `medit` interpreter missing explicit fallback to `interpret()`. | 🔄 OPEN |
| `OLC-015` | MINOR | `src/olc.c:661-690` | `mud/commands/imm_olc.py:do_edit` | `do_olc` ported: NPC guard, prefix matching via `_EDITOR_TABLE`, remainder args forwarded, help text on no-arg/unknown subcmd. Registered as both `olc` and `edit` in dispatcher. | ✅ FIXED |
| `OLC-016` | CRITICAL | `src/olc.c:695-740` | `mud/commands/build.py:cmd_aedit` + `_aedit_create` | Closed by OLC_ACT-001 closure — `aedit create` wired; new area gets ROM `new_area()` defaults from `src/mem.c:91-122`; `AreaFlag.ADDED` set; descriptor edit pointer wired. | ✅ FIXED |
| `OLC-017` | CRITICAL | `src/olc.c:745-821` | `mud/commands/build.py:cmd_redit` + `_redit_create` + `_redit_vnum_teleport` + `_apply_resets_for_redit` | Closed by OLC_ACT-002/003/004 closure — `create <vnum>` (full ROM defaults + builder relocate), `reset` (security + apply_resets + "Room reset.\n\r"), and `<vnum>` silent teleport (reuses `_char_from_room`/`_char_to_room`) all wired. | ✅ FIXED |
| `OLC-018` | CRITICAL | `src/olc.c:826-895` | `mud/commands/build.py:cmd_oedit` + `_oedit_create` | Closed by OLC_ACT-005 closure — `oedit create <vnum>` wired with full ROM validation chain (vnum, area, IS_BUILDER, exists); `new_obj_index` defaults applied; auto-create-on-unknown-vnum bug removed. | ✅ FIXED |
| `OLC-019` | CRITICAL | `src/olc.c:900-969` | `mud/commands/build.py:cmd_medit` + `_medit_create` | Closed by OLC_ACT-006 closure — `medit create <vnum>` wired with full ROM validation chain; **`ActFlag.IS_NPC` now set on new mobs** (audit's flagged CRITICAL divergence); `new_mob_index` defaults applied. | ✅ FIXED |
| `OLC-020` | IMPORTANT | `src/olc.c:973-1183` | `mud/commands/imm_olc.py:_display_resets` | `display_resets` not faithfully ported. Missing per-command (M/O/P/G/E/D/R) formatting, pet-shop overlay, wear-loc/door-reset flag-string decoding. Builder UX significantly degraded. | ✅ FIXED — `_display_resets(room)` helper added; exact ROM sprintf formats, pet-shop final[5]='P' overlay, wear-loc/door-reset decoding via `mud/utils/olc_tables.py`. Bad-mob/obj 'continue' paths replicated (no emission per ROM). Test: `tests/integration/test_olc_display_resets.py` (16 cases). |
| `OLC-021` | MINOR | `src/olc.c:1192-1228` | `mud/commands/imm_olc.py:_add_reset` | Closed-by-verification: `_add_reset()` already matched ROM `add_reset` semantics under Python list storage. Locked cases: index `1` inserts at head, index `2` inserts after head, non-positive indices append to tail, and oversize positive indices also append to tail when the walk falls off the end. No runtime code change was required; the gap was stale audit debt. | ✅ FIXED — tests in `tests/integration/test_olc_do_resets_subcommands.py` |
| `OLC-022` | IMPORTANT | `src/olc.c:1232-1469` | `mud/commands/imm_olc.py:do_resets` | `do_resets` missing `inside <vnum>` (P-reset), `wear-loc` decode (G/E split), `random <#exits>` (R-reset), and the 6-line syntax help. | ✅ FIXED — `do_resets` rewritten with full ROM subcommand set: P-reset (`inside <vnum> [limit] [count]`), O-reset (`room`), G/E-reset (wear-loc prefix lookup), R-reset (`random 1..6`), M-reset extended with `[max#area] [max#room]` defaults, syntax block on unrecognized input. `_add_reset` helper added. Test: `tests/integration/test_olc_do_resets_subcommands.py` (27 cases). |
| `OLC-023` | CRITICAL | `src/olc.c:1478-1502` | `mud/commands/imm_olc.py:121-146` | `do_alist` iterates the wrong attribute (`registry.areas` does not exist; should be `registry.area_registry.values()`). Returns header-only output on a live system. **Real bug.** | ✅ FIXED — `do_alist` iterates `area_registry.values()`, prints `area.vnum` (was 1-indexed counter), uses `file_name` (was nonexistent `filename`). Test: `tests/integration/test_olc_alist.py` (4 cases). |

### Cross-cluster deferrals that close in this cluster

The OLC audit also unblocks 16 already-filed gaps from sibling audits:

- `STRING-001` … `STRING-012` (`docs/parity/STRING_C_AUDIT.md`) — all 12 string-editor helpers; closure depends on OLC-INFRA-001 + STRING-001..012 themselves.
- `BIT-001`, `BIT-002`, `BIT-003` (`docs/parity/BIT_C_AUDIT.md`) — `flag_value`, `flag_string`, `is_stat`/`flag_stat_table`; closure unblocks OLC-011, OLC-020, OLC-022 and every `olc_act.c` builder.
- `CONST-007` (`docs/parity/CONST_C_AUDIT.md`) — `weapon_table` data port; closure unblocks `oedit` weapon-class display.

### Recommended close order (proposed; awaits user confirmation per skill Phase 4 gate)

1. **OLC-INFRA-001** — descriptor `pString`/`editor` plumbing + game-loop string-editor hook. Single PR; no per-command tests yet.
2. **BIT-001 / BIT-002 / BIT-003** — `flag_value` / `flag_string` / `is_stat` helpers. One commit per gap. These have zero current callers, so tests must be infrastructure-level (call helper directly with synthetic IntFlag tables).
3. **STRING-001 .. STRING-012** — string editor helpers, one per commit. STRING-004 (`string_add`) is the keystone; STRING-005 (`format_string`) is the second-most subtle.
4. **OLC-023** — `do_alist` real bug fix. Single small commit.
5. **OLC-016 / OLC-017 / OLC-018 / OLC-019** — `do_*edit create` subcommands. Four commits. These are the user-facing CRITICAL gaps.
6. **OLC-006 / OLC-007 / OLC-008 / OLC-009** — port the four `*edit_table[]`s as data tables. Each becomes a `(name, handler)` tuple consumed by a generic `_dispatch_olc_table` helper. Each commit also pulls in the missing builders from `olc_act.c` (which is its own audit; this OLC audit ends at the dispatch boundary).
7. **OLC-011** — `aedit` flag-toggle prefix. Depends on BIT-001.
8. **OLC-020 / OLC-022** — `display_resets` + `do_resets` faithful ports. Depend on BIT-001/002.
9. **OLC-021** — `add_reset` linked-list edge cases.
10. **OLC-001 / OLC-010 / OLC-012 / OLC-013 / OLC-014 / OLC-015** — MINOR cosmetic/structural gaps. Batch as a single "OLC structural alignment" commit set.

`olc_act.c` (5007 lines, ~80 builder functions) and `olc_save.c` (1136 lines, ROM `.are` text-format writer) are intentionally *out of scope* for this audit — they are sibling audits in the OLC cluster and will be filed after the user confirms scope. `olc_mpcode.c` (272 lines) and `hedit.c` (462 lines) are smaller and may bundle into the final closure session.

---

## Phase 4 — Closures

Closed across the current OLC pass:

- `OLC-INFRA-001` — descriptor `editor_mode` / `string_edit` plumbing plus `route_descriptor_input()`.
- `OLC-016`..`OLC-019` — `aedit`/`redit`/`oedit`/`medit` entry surfaces.
- `OLC-020`, `OLC-022`, `OLC-023` — reset display/subcommands and `alist`.
- `OLC-001` — unified descriptor router in `process_command()`, including `string_add` precedence and OLC-first dispatch.
- `OLC-002`, `OLC-003` — prompt `%o` / `%O` via `olc_ed_name()` / `olc_ed_vnum()` parity in `mud/utils/prompt.py`.
- `OLC-004`, `OLC-005` — ROM five-column OLC command listings for `commands` in area, room, object, mobile, and help editors.

Current session details (`OLC-001`):

- `mud/commands/dispatcher.py` now routes descriptors via `route_descriptor_input()` before the normal interpreter, mirroring ROM `src/comm.c:833-847`.
- `mud/commands/build.py` now keeps `session.editor_mode` synchronized with the legacy string `session.editor`, so descriptor routing and prompt-token work can share one authoritative OLC mode.
- `_split_command_and_args()` now preserves `@redit` / `@aedit` / `@oedit` / `@medit` / `@hedit` / `@asave` as full command tokens instead of collapsing them to the single-character `@` alias.
- Tests added/updated: `tests/integration/test_olc_001_run_olc_editor.py` and `tests/test_building.py`.

Current session details (`OLC-004` / `OLC-005`):

- `mud/commands/build.py` now carries ROM command-name tables for `aedit`, `redit`, `oedit`, `medit`, `mpedit`, and `hedit`.
- `_show_olc_cmds()` mirrors ROM `src/olc.c:153-175` fixed-width formatting.
- Active `aedit`/`redit`/`oedit`/`medit`/`hedit` sessions now handle `commands` instead of falling through to unknown editor command output.
- Tests added: `tests/integration/test_olc_commands_listing.py`.

---

## Phase 5 — Completion

`olc.c` remains ⚠️ Partial, but the audit is now past the "inventory only" stage. The remaining meaningful open set is:

- `OLC-010` / `OLC-015` — top-level `olc` shell (`editor_table[]` + `do_olc`)
- `OLC-006`..`OLC-009` / `OLC-011` — data-driven editor tables and the `aedit` flag-toggle prefix
- `OLC-012` / `OLC-013` / `OLC-014` — explicit per-editor `interpret()` fallback
