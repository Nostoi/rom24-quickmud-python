# `olc_mpcode.c` Parity Audit

**Status**: ⚠️ IN PROGRESS — Phases 1–3 complete; Phase 4 in progress
**Date**: 2026-05-02
**Auditor**: OpenCode

---

## Phase 1 — Function Inventory

| ROM Function | ROM Lines | Python File : Line | Status |
|---|---|---|---|
| `mpedit_table[]` (dispatch table) | 22–33 | `mud/commands/build.py` — no table | ❌ MISSING |
| `mpedit()` (session interpreter) | 35–94 | `mud/commands/imm_olc.py` — stub | ⚠️ PARTIAL |
| `do_mpedit()` (entry command) | 96–151 | `mud/commands/imm_olc.py:517` | ⚠️ PARTIAL |
| `mpedit_create()` | 153–196 | none | ❌ MISSING |
| `mpedit_show()` | 198–211 | none | ❌ MISSING |
| `mpedit_code()` | 213–226 | none | ❌ MISSING |
| `mpedit_list()` | 228–272 | none | ❌ MISSING |

**Infrastructure gap**: ROM has `MPROG_CODE` — a separate model for standalone code blocks with their own vnum registry (`mprog_list`). Python has `MobProgram` (trigger list attached to mobs) but no standalone `MprogCode` class or registry. This underpins all subcommands.

---

## Phase 2 — Verification Notes

### `do_mpedit()` (src/olc_mpcode.c:96–151)

ROM behavior:
1. `one_argument` splits first token as `command`.
2. If `command` is numeric: look up by vnum in `mprog_list` (standalone code blocks). Error: `"MPEdit : That vnum does not exist.\n\r"`. If vnum has no area: `"MPEdit : VNUM no asignado a ningun area.\n\r"`. If insufficient builder security: `"MPEdit : Insuficiente seguridad para editar area.\n\r"`. On success: set `ch->desc->pEdit` + `editor = ED_MPCODE` (silent).
3. If `command == "create"`: delegate to `mpedit_create(ch, argument)`.
4. Otherwise: syntax `"Sintaxis : mpedit [vnum]\n\r" + "           mpedit create [vnum]\n\r"`.

Python `do_mpedit` stub:
- Checks `args.strip().split()[0].isdigit()` but looks up in `mob_prototypes` (WRONG — should be mprog code registry).
- Returns a fake string, never sets session.
- No `create` branch.
- No security check.

### `mpedit()` session interpreter (src/olc_mpcode.c:35–94)

ROM behavior:
1. `smash_tilde` the argument.
2. `EDIT_MPCODE` to get `pMcode`.
3. If pMcode exists: check area + IS_BUILDER; on fail → `edit_done` + `"MPEdit: Insufficient security to modify code.\n\r"`.
4. Empty command → `mpedit_show`.
5. `"done"` → `edit_done`.
6. Prefix-match against `mpedit_table`; if matched and function returns TRUE → `SET_BIT(ad->area_flags, AREA_CHANGED)`.
7. Fallback → `interpret(ch, arg)` (normal command).

Python has no `_interpret_mpedit` at all.

### `mpedit_create()` (src/olc_mpcode.c:153–196)

ROM behavior:
1. Null/bad vnum → `"Sintaxis : mpedit create [vnum]\n\r"`.
2. No area for vnum → `"MPEdit : VNUM no asignado a ningun area.\n\r"`.
3. No builder security → `"MPEdit : Insuficiente seguridad para crear MobProgs.\n\r"`.
4. vnum already exists → `"MPEdit: Code vnum already exists.\n\r"`.
5. `new_mpcode()` → set vnum, prepend to `mprog_list`, set `pEdit`/`editor = ED_MPCODE`.
6. `"MobProgram Code Created.\n\r"`.

Python: not implemented.

### `mpedit_show()` (src/olc_mpcode.c:198–211)

ROM format: `"Vnum:       [%d]\n\rCode:\n\r%s\n\r"` with `pMcode->vnum` and `pMcode->code`.

Python: not implemented.

### `mpedit_code()` (src/olc_mpcode.c:213–226)

ROM: no-arg → `string_append(ch, &pMcode->code)` returns TRUE; arg present → `"Syntax: code\n\r"` returns FALSE.

Python: not implemented.

### `mpedit_list()` (src/olc_mpcode.c:228–272)

ROM: iterates `mprog_list`; `fAll = !str_cmp(argument, "all")`; filters to current area's vnum range otherwise.
Format per entry: `"[%3d] (%c) %5d\n\r"` (count, `*`/` `/`?` access indicator, vnum).
Empty → `"MobPrograms do not exist!\n\r"` (all) or `"MobPrograms do not exist in this area.\n\r"`.
Uses `page_to_char`.

Python: not implemented.

---

## Phase 3 — Gap Table

| Gap ID | Severity | ROM Reference | Python Reference | Description | Status |
|---|---|---|---|---|---|
| MPEDIT-001 | CRITICAL | `olc_mpcode.c:35–94` | `imm_olc.py:517` | `_interpret_mpedit` session loop entirely missing; no dispatch table, no smash_tilde, no security re-check, no area-changed flag, no fallback to interpret | 🔄 OPEN |
| MPEDIT-002 | CRITICAL | `olc_mpcode.c:96–151` | `imm_olc.py:517` | `do_mpedit` looks up `mob_prototypes` instead of mprog code registry; no session open; no `create` branch; no security check; wrong error messages | 🔄 OPEN |
| MPEDIT-003 | CRITICAL | `olc_mpcode.c:153–196` | (missing) | `mpedit_create` entirely missing — no standalone `MprogCode` model, no registry, no vnum check, no area check, no builder check | 🔄 OPEN |
| MPEDIT-004 | CRITICAL | `olc_mpcode.c:198–211` | (missing) | `mpedit_show` entirely missing — exact ROM format `"Vnum:       [%d]\n\rCode:\n\r%s\n\r"` | 🔄 OPEN |
| MPEDIT-005 | CRITICAL | `olc_mpcode.c:213–226` | (missing) | `mpedit_code` entirely missing — no-arg enters string_append; arg → syntax error | 🔄 OPEN |
| MPEDIT-006 | CRITICAL | `olc_mpcode.c:228–272` | (missing) | `mpedit_list` entirely missing — `[%3d] (%c) %5d\n\r` format, all/area filter, empty fallback messages | 🔄 OPEN |
| MPEDIT-007 | IMPORTANT | `olc_mpcode.c:261–266` | (missing) | `mpedit_list` empty message: `"MobPrograms do not exist!\n\r"` vs `"MobPrograms do not exist in this area.\n\r"` based on fAll | 🔄 OPEN (part of MPEDIT-006) |

**Total: 6 independent gaps (MPEDIT-001..006); MPEDIT-007 is sub-item of MPEDIT-006.**

---

## Phase 4 — Gap Closures

*(to be filled as gaps are closed)*

---

## Phase 5 — Completion Summary

*(to be filled when all gaps are closed)*
