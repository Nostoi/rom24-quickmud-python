# `olc.c` ROM Parity Audit

- **Status**: ⚠️ Partial 30% — Phase 1–3 inventory + gap list filed (2026-04-29). Phase 4 closures pending user scope confirmation. OLC cluster (`olc.c` + `olc_act.c` + `olc_save.c` + `olc_mpcode.c` + `hedit.c`) is the largest single remaining audit and bundles 16 cross-cluster deferrals (STRING-001..012, BIT-001..003, CONST-007).
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
| `run_olc_editor` | 37-63 | public | Raw-input router: dispatch to `aedit`/`redit`/`oedit`/`medit`/`mpedit`/`hedit` based on `desc->editor` | — (per-editor `handle_*_command` exists, no unified router) | ❌ MISSING (OLC-001) |
| `olc_ed_name` | 67-97 | public | Prompt `%o` token: `"AEdit"`/`"REdit"`/… string for current editor | `mud/utils/prompt.py:158-160` returns `""` (stub) | ❌ MISSING (OLC-002) |
| `olc_ed_vnum` | 101-144 | public | Prompt `%O` token: vnum (or keyword for `ED_HELP`) of currently-edited entity | `mud/utils/prompt.py:158-160` returns `""` (stub) | ❌ MISSING (OLC-003) |
| `show_olc_cmds` | 153-175 | public | Format command table as 5-column listing | — | ❌ MISSING (OLC-004) |
| `show_commands` | 184-209 | public | Dispatch `commands` to the right `show_olc_cmds` based on `desc->editor` | — | ❌ MISSING (OLC-005) |
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
| `do_aedit` | 695-740 | public | User entry: `aedit <vnum>` / `aedit create` → set `desc->pEdit` + `desc->editor = ED_AREA` | `cmd_aedit` (`build.py:1226-1255`) — covers numeric/non-numeric, but **no `create` subcommand**, no security level=9 gate, no `IS_BUILDER` re-check | ⚠️ PARTIAL (OLC-016) |
| `do_redit` | 745-821 | public | User entry: `redit reset` / `redit create <vnum>` / `redit <vnum>` / no-arg | `cmd_redit` (`build.py:1071-1103`) — covers no-arg path, **no `reset` / `create` / `<vnum>` subpaths**, no `char_from_room`+`char_to_room` teleport on vnum match | ⚠️ PARTIAL (OLC-017) |
| `do_oedit` | 826-895 | public | User entry: `oedit <vnum>` / `oedit create <vnum>` | `cmd_oedit` (`build.py:1430-1471`) — covers numeric path, **no `create` subcommand**, no `get_vnum_area` security check on create | ⚠️ PARTIAL (OLC-018) |
| `do_medit` | 900-969 | public | User entry: `medit <vnum>` / `medit create <vnum>` | `cmd_medit` (`build.py:1714-1755`) — covers numeric path, **no `create` subcommand**, no `get_vnum_area` security check | ⚠️ PARTIAL (OLC-019) |
| `display_resets` | 973-1183 | public | Format `pRoom->reset_first` linked list as the 8-column table (M/O/P/G/E/D/R commands + pet-shop detection on `R[%5d-1]`) | `mud/commands/imm_olc.py:do_resets:39-53` — emits a 1-line per reset listing only; **no** M/O/P/G/E/D/R per-command formatting, **no** pet-shop check, **no** wear-loc decoding via `flag_string(wear_loc_strings, …)`, **no** door-direction labels | ⚠️ PARTIAL (OLC-020) |
| `add_reset` | 1192-1228 | public | Insert reset at 1-indexed position in `room->reset_first`/`reset_last` linked list (negative idx → tail; idx=1 → head) | `mud/commands/imm_olc.py:88,109` uses `list.insert(idx-1, ...)` — partial semantics, no `reset_last` tracking (Python uses Python `list`, no doubly-linked structure to maintain) | ⚠️ PARTIAL (OLC-021) |
| `do_resets` | 1232-1469 | public | Top-level `resets` command: display, add `M`/`O`/`P` (with `inside`/`room`/wear-loc subcases), add `R`andom-exits, delete | `mud/commands/imm_olc.py:do_resets:17-118` — covers display + delete + simple `mob`/`obj` add only; **no** `inside <vnum>` container reset (`P` command), **no** wear-loc gate (`G`/`E` distinction), **no** `random` subcommand (`R`), **no** syntax help on bad input | ⚠️ PARTIAL (OLC-022) |
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

Confirmed gap. Not CRITICAL because the partial workaround works for documented OLC users; IMPORTANT because the behavior diverges on edge cases.

### `olc_ed_name` / `olc_ed_vnum` (ROM 67-144) — OLC-002, OLC-003

Sole consumer in ROM: prompt rendering in `comm.c:make_prompt` for the `%o` and `%O` tokens. Python `mud/utils/prompt.py:155-160` emits `""` and leaves a TODO comment. Closing this requires: (a) reading `session.editor` (string) → produce `"AEdit"`/`"REdit"`/etc., (b) reading `session.editor_state["area"|"room"|"obj_proto"|"mob_proto"|"help_entry"]` → produce vnum (or `keyword` for help). Behavior is purely cosmetic, MINOR severity.

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
| `OLC-001` | IMPORTANT | `src/olc.c:37-63` | (no equivalent router) | `run_olc_editor(desc)` not ported. Python routes editor input through the normal command dispatcher with `session.editor` special-cases, instead of branching at game-loop level. Edge cases collide on common command names (`look`, `show`, `l`). | 🔄 OPEN |
| `OLC-002` | MINOR | `src/olc.c:67-97` | `mud/utils/prompt.py:158-160` | `olc_ed_name(ch)` not ported; prompt token `%o` always renders `""`. | 🔄 OPEN |
| `OLC-003` | MINOR | `src/olc.c:101-144` | `mud/utils/prompt.py:158-160` | `olc_ed_vnum(ch)` not ported; prompt token `%O` always renders `""`. | 🔄 OPEN |
| `OLC-004` | MINOR | `src/olc.c:153-175` | (no equivalent) | `show_olc_cmds` 5-column command-table formatter not ported. Required by `commands` subcommand in every editor. | 🔄 OPEN |
| `OLC-005` | MINOR | `src/olc.c:184-209` | (no equivalent) | `show_commands` editor-aware dispatcher to `show_olc_cmds` not ported. | 🔄 OPEN |
| `OLC-006` | IMPORTANT | `src/olc.c:216-238` | `mud/commands/build.py:1261-1376` | `aedit_table[]` (15 entries) not ported as a data-driven `(name, fn)` table. Python inlines the dispatch in `_interpret_aedit`. Closing means extracting a tuple/list and the builders themselves, in tandem with `olc_act.c` audit. | 🔄 OPEN |
| `OLC-007` | IMPORTANT | `src/olc.c:242-279` | `mud/commands/build.py:961-1069` | `redit_table[]` (29 entries) not ported as a data table; many entries (`mreset`, `oreset`, `mlist`, `rlist`, `olist`, `mshow`, `oshow`, `heal`, `mana`, `clan`, `format`) have no Python implementation at all. | 🔄 OPEN |
| `OLC-008` | IMPORTANT | `src/olc.c:283-315` | `mud/commands/build.py:1477-1613` | `oedit_table[]` (24 entries) not ported as a data table; missing entries: `addaffect`, `addapply`, `delaffect`, `v0..v4`, `extra`, `wear`, `material`, `level`, `condition`. | 🔄 OPEN |
| `OLC-009` | IMPORTANT | `src/olc.c:319-362` | `mud/commands/build.py:1761-1976` | `medit_table[]` (38 entries) not ported as a data table; missing entries include `affect`, `armor`, `form`, `part`, `imm`, `res`, `vuln`, `material`, `off`, `size`, `hitdice`, `manadice`, `damdice`, `position`, `wealth`, `hitroll`, `damtype`, `group`, `addmprog`, `delmprog`. | 🔄 OPEN |
| `OLC-010` | MINOR | `src/olc.c:646-657` | (no equivalent) | `editor_table[]` 6-entry top-level dispatch not ported. | 🔄 OPEN |
| `OLC-011` | IMPORTANT | `src/olc.c:410-469` | `mud/commands/build.py:1261` | `aedit` interpreter missing the `flag_value(area_flags, command)` toggle prefix — builder cannot toggle area flags by typing the flag name. Also missing `interpret()` fallback to normal command tree. | 🔄 OPEN |
| `OLC-012` | MINOR | `src/olc.c:474-527` | `mud/commands/build.py:961` | `redit` interpreter missing explicit fallback to `interpret()` for unknown commands. (Python dispatcher route makes this functionally close.) | 🔄 OPEN |
| `OLC-013` | MINOR | `src/olc.c:532-584` | `mud/commands/build.py:1477` | `oedit` interpreter missing explicit fallback to `interpret()`. | 🔄 OPEN |
| `OLC-014` | MINOR | `src/olc.c:589-641` | `mud/commands/build.py:1761` | `medit` interpreter missing explicit fallback to `interpret()`. | 🔄 OPEN |
| `OLC-015` | MINOR | `src/olc.c:661-690` | (no equivalent) | `do_olc` top-level user command not ported. Users cannot type `olc room`/`olc area`/etc. (must type the editor name directly). | 🔄 OPEN |
| `OLC-016` | CRITICAL | `src/olc.c:695-740` | `mud/commands/build.py:1226-1255` | `do_aedit` missing `create` subcommand (security≥9 gate + `aedit_create` call). No way to create new areas through OLC. | 🔄 OPEN |
| `OLC-017` | CRITICAL | `src/olc.c:745-821` | `mud/commands/build.py:1071-1103` | `do_redit` missing `reset` (call `reset_room`), `create <vnum>` (call `redit_create`+teleport), and `<vnum>` jump+teleport subcommands. No way to create new rooms or jump-edit a remote room through OLC. | 🔄 OPEN |
| `OLC-018` | CRITICAL | `src/olc.c:826-895` | `mud/commands/build.py:1430-1471` | `do_oedit` missing `create <vnum>` subcommand + `get_vnum_area` security gate. No way to create new objects through OLC. | 🔄 OPEN |
| `OLC-019` | CRITICAL | `src/olc.c:900-969` | `mud/commands/build.py:1714-1755` | `do_medit` missing `create <vnum>` subcommand + `get_vnum_area` security gate. No way to create new mobiles through OLC. | 🔄 OPEN |
| `OLC-020` | IMPORTANT | `src/olc.c:973-1183` | `mud/commands/imm_olc.py:39-53` | `display_resets` not faithfully ported. Missing per-command (M/O/P/G/E/D/R) formatting, pet-shop overlay, wear-loc/door-reset flag-string decoding. Builder UX significantly degraded. Depends on BIT-002 (`flag_string`). | 🔄 OPEN |
| `OLC-021` | MINOR | `src/olc.c:1192-1228` | `mud/commands/imm_olc.py:88,109` | `add_reset` linked-list semantics differ from Python `list.insert`. Edge cases on negative/zero indices diverge. | 🔄 OPEN |
| `OLC-022` | IMPORTANT | `src/olc.c:1232-1469` | `mud/commands/imm_olc.py:17-118` | `do_resets` missing `inside <vnum>` (P-reset), `wear-loc` decode (G/E split), `random <#exits>` (R-reset), and the 6-line syntax help. Depends on BIT-001 (`flag_value`). | 🔄 OPEN |
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
10. **OLC-001 / OLC-002 / OLC-003 / OLC-004 / OLC-005 / OLC-010 / OLC-012 / OLC-013 / OLC-014 / OLC-015** — MINOR cosmetic/structural gaps. Batch as a single "OLC structural alignment" commit set.

`olc_act.c` (5007 lines, ~80 builder functions) and `olc_save.c` (1136 lines, ROM `.are` text-format writer) are intentionally *out of scope* for this audit — they are sibling audits in the OLC cluster and will be filed after the user confirms scope. `olc_mpcode.c` (272 lines) and `hedit.c` (462 lines) are smaller and may bundle into the final closure session.

---

## Phase 4 — Closures

None this session. Closure work paused awaiting user confirmation on:

- Whether to start with `OLC-INFRA-001` + the BIT/STRING bundle (the architecturally-correct path, ~1 large session) **or** start with the user-facing `OLC-016..019` CRITICAL gaps (more visible progress, but blocked on the create-area/room/mob/obj builders in `olc_act.c`, which forces an immediate sibling audit).
- Whether `olc_act.c` / `olc_save.c` / `olc_mpcode.c` / `hedit.c` audits are expected in-scope for this session or filed for later.

---

## Phase 5 — Completion

`olc.c` flips ⚠️ Partial 30% → ⚠️ Partial 30% (audit doc filed, gap IDs stable, no closures yet). Next status flip when OLC-INFRA-001 + the first round of CRITICAL gaps close — at minimum OLC-016/017/018/019/023 must close before the row can credibly read ⚠️ Partial >30%.
