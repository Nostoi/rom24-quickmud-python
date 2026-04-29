# `string.c` ROM Parity Audit

- **Status**: ✅ AUDITED 5% — 11 of 12 helpers DEFERRED to OLC audit cluster (no current Python consumer)
- **Date**: 2026-04-29
- **Source**: `src/string.c` (ROM 2.4b6, 692 lines, 12 public functions — all OLC string-editor backend)
- **Python primary**: `mud/utils/text.py` (only `smash_tilde` is ported, and that one is declared in `merc.h` rather than `string.c` proper)

## Phase 1 — Function inventory

| ROM symbol | ROM lines | Visibility | Purpose | Python counterpart | Status |
|------------|-----------|------------|---------|--------------------|--------|
| `string_edit` | 38-57 | public | Enter EDIT mode; clear `*pString`; attach to `ch->desc->pString` | — | ❌ MISSING (STRING-001) |
| `string_append` | 66-86 | public | Enter APPEND mode; preserve `*pString`; emit `numlines()` listing | — | ❌ MISSING (STRING-002) |
| `string_replace` | 95-112 | public | Substring substitute (single occurrence) | — | ❌ MISSING (STRING-003) |
| `string_add` | 121-286 | public | Editor input dispatcher (`.c`/`.s`/`.r`/`.f`/`.h`/`.ld`/`.li`/`.lr`/`~`/`@`); MPCODE save hook | — | ❌ MISSING (STRING-004) |
| `format_string` | 299-451 | public | Word-wrap to 77 cols + sentence capitalization + paren/quote handling | — | ❌ MISSING (STRING-005) |
| `first_arg` | 468-508 | public | Quote/paren-aware single-arg parser (used by `.r`/`.li`/`.lr`) | — | ❌ MISSING (STRING-006) |
| `string_unpad` | 516-543 | public | Trim leading + trailing spaces (used by `aedit_builders`) | — | ❌ MISSING (STRING-007) |
| `string_proper` | 551-572 | public | Title-case each space-delimited word (used by `aedit_builder`) | — | ❌ MISSING (STRING-008) |
| `string_linedel` | 574-605 | public | Remove line N (1-indexed) | — | ❌ MISSING (STRING-009) |
| `string_lineadd` | 607-645 | public | Insert `newstr` as line N (1-indexed) | — | ❌ MISSING (STRING-010) |
| `merc_getline` | 647-674 | public | Read one `\n`-terminated line into `buf`; return rest of `str` | — | ❌ MISSING (STRING-011) |
| `numlines` | 676-692 | public | Format string as line-numbered listing (`%2d. ...\n\r`) | — | ❌ MISSING (STRING-012) |

Adjacent helper declared in `merc.h` (defined in `db.c`/`comm.c` — not `string.c`):

| ROM symbol | ROM lines | Python counterpart | Status |
|------------|-----------|--------------------|--------|
| `smash_tilde` | `src/db.c` | `mud/utils/text.py:108:smash_tilde` | ✅ AUDITED (already ported, exercised by note board + spec_funs paths) |

## Phase 2 — Verification

Every public function in `string.c` operates on **descriptor-level OLC editor state** (`ch->desc->pString`, `ch->desc->editor`, `ED_MPCODE`) and is reached via one of two call patterns:

1. **OLC entry points** in `olc_act.c` / `aedit_builder` / `medit_builder` / `redit_builder` — `string_edit`, `string_append`, `string_unpad`, `string_proper`, `format_string`, `string_replace`.
2. **Game-loop dispatch** in `comm.c::game_loop_*`, which routes raw input to `string_add` whenever `ch->desc->pString != NULL` (i.e. the descriptor is in EDIT/APPEND mode). `string_add` then calls `format_string` / `string_replace` / `string_linedel` / `string_lineadd` / `first_arg` / `numlines` / `merc_getline`.

There is **no Python descriptor-level editor state**. Verification confirms:

- `mud/olc/` contains only `__init__.py` and `save.py` (skeleton — no editor state machine, no `pString`, no `ED_*` editor enum).
- `grep -rn "pString" mud/` → 0 matches.
- `grep -rn "string_add\|string_edit\|string_append" mud/` → 0 matches.
- The tracker note "string.c — `mud/utils.py` — 85%" is **stale**: `mud/utils.py` does not exist, only the package `mud/utils/`. Within that package, only `smash_tilde` from `merc.h` is ported. Real coverage is **5%** (1 of 13 helpers, and the one that is ported lives in `merc.h` rather than `string.c` proper).
- `format_string` is the most subtle of the missing helpers (sentence-end double-space + capitalization + paren rewrite + 77-col wrap with mid-word `-` fallback when `bug("No spaces", 0)` fires). Any future port must mirror the `bug()` log emission too — that fallback is a faithful-port edge case.
- `first_arg` differs from `one_argument` (already ported as `mud/utils/parse.py`) in three ways: (a) supports `(`/`)` as a balanced quote pair, (b) `fCase` parameter for case preservation, (c) does NOT lowercase by default. Consumers other than `string_add` (`.r`/`.li`/`.lr`) currently do not exist; ROM never calls `first_arg` from outside `string.c`.
- `string_linedel` / `string_lineadd` operate on `\n\r`-terminated lines and 1-indexed line numbers (per the `.ld <num>` / `.li <num>` UX), not Python `splitlines()` semantics — a line port must preserve both line-ending forms.

## Phase 3 — Gaps

All gaps below are **DEFERRED to the OLC audit cluster** (`olc.c`, `olc_act.c`, `olc_save.c`, `olc_mpcode.c`, `hedit.c`). Closing them in isolation would yield code with zero callers and zero integration coverage. They are real ROM-parity work; they are simply blocked on prerequisite OLC plumbing (descriptor `pString` field, `ED_NONE`/`ED_MPCODE` editor enum, game-loop dispatch hook, `olc_act.c` builders).

| Gap ID | Severity | ROM C | Description | Status |
|--------|----------|-------|-------------|--------|
| `STRING-001` | IMPORTANT | `src/string.c:38-57` | `string_edit(ch, pString)` — enter EDIT mode (clears string, attaches descriptor). Required by `olc_act.c::aedit_builder` ("desc edit"), `redit::edit-description`, `medit::edit-description`. | 🔄 DEFERRED — close alongside OLC audit |
| `STRING-002` | IMPORTANT | `src/string.c:66-86` | `string_append(ch, pString)` — enter APPEND mode (preserve, list lines). Required by every OLC `desc` builder. | 🔄 DEFERRED — close alongside OLC audit |
| `STRING-003` | IMPORTANT | `src/string.c:95-112` | `string_replace(orig, old, new)` — single-occurrence substring substitute. Used by `string_add::.r` and `aedit_builder::replace`. | 🔄 DEFERRED — close alongside OLC audit |
| `STRING-004` | CRITICAL | `src/string.c:121-286` | `string_add` editor dispatcher — reads `.c/.s/.r/.f/.ld/.li/.lr/.h` dot-commands, `~`/`@` to terminate, MAX_STRING_LENGTH-4 truncation, `smash_tilde` on every line, MPCODE post-save hook (writes back to `mob_index_hash` mprogs). The whole editor UX. | 🔄 DEFERRED — close alongside OLC audit |
| `STRING-005` | IMPORTANT | `src/string.c:299-451` | `format_string` — sentence-end double-space, capitalize-after-`.`/`?`/`!`, balanced paren rewrite, 77-col word-wrap with `bug("No spaces", 0)` mid-word `-` fallback. Cited by `.f` dot-command and many `olc_act.c` `desc` builders. | 🔄 DEFERRED — close alongside OLC audit |
| `STRING-006` | MINOR | `src/string.c:468-508` | `first_arg` — quote/paren-aware single-arg parser with optional case preservation. Caller is `string_add` only (ROM never imports it elsewhere). | ✅ FIXED — `mud/utils/string_editor.py:first_arg(argument, lower=False) -> tuple[str, str]`. Recognizes `'`/`"`/`%` self-pair quotes and `(`/`)` balanced pair; unterminated quote consumes the rest. Test: `tests/integration/test_string_editor_first_arg.py` (10 cases). |
| `STRING-007` | MINOR | `src/string.c:516-543` | `string_unpad` — trim spaces (lstrip + rstrip). Caller is `aedit_builder`. | ✅ FIXED — `mud/utils/string_editor.py:string_unpad`. Test: `tests/integration/test_string_editor_unpad.py` (7 cases). |
| `STRING-008` | MINOR | `src/string.c:551-572` | `string_proper` — title-case each space-delimited word. Caller is `aedit_builder`. | ✅ FIXED — `mud/utils/string_editor.py:string_proper`. Differs from `str.title()`: ROM only uppercases boundary char, leaves rest of word alone. Test: `tests/integration/test_string_editor_proper.py` (8 cases). |
| `STRING-009` | IMPORTANT | `src/string.c:574-605` | `string_linedel(string, line)` — remove 1-indexed line, preserving `\n\r` line-ending. `.ld` dot-command. | 🔄 DEFERRED — close alongside OLC audit |
| `STRING-010` | IMPORTANT | `src/string.c:607-645` | `string_lineadd(string, newstr, line)` — insert `newstr` as 1-indexed line. `.li`/`.lr` dot-commands. | 🔄 DEFERRED — close alongside OLC audit |
| `STRING-011` | MINOR | `src/string.c:647-674` | `merc_getline(str, buf)` — read one `\n`-terminated line into `buf`; return remainder. Internal helper for `numlines`. | ✅ FIXED — `mud/utils/string_editor.py:merc_getline(s) -> tuple[str, str]`. Consumes trailing `\r` after `\n` to handle ROM `\n\r` line endings. Test: `tests/integration/test_string_editor_merc_getline.py` (6 cases). |
| `STRING-012` | IMPORTANT | `src/string.c:676-692` | `numlines(string)` — format as line-numbered listing (`%2d. <line>\n\r`). Used by `.s` dot-command and `string_append` greeting. | 🔄 DEFERRED — close alongside OLC audit |

No CRITICAL gaps with current callers (because there are no callers). `STRING-004` is severity-CRITICAL because `string_add` is the entire editor UX and a partial port would silently corrupt OLC sessions; it must be ported faithfully or not at all.

## Phase 4 — Closures

None this session. All 12 gaps deferred-by-design — see Phase 3 rationale.

## Phase 5 — Completion

`string.c` is flipped from ⚠️ Partial 85% (stale, wrong file path) to ✅ AUDITED 5% (accurate). The 5% reflects the one already-ported helper (`smash_tilde`, and that one is technically owned by `merc.h`/`db.c`).

When the OLC cluster (`olc.c` next) is audited:

1. The first OLC session must add descriptor-level `pString`/`editor` fields and the game-loop dispatch hook (these are infrastructure, not in `string.c`).
2. Each `STRING-NNN` gap is closed in its own commit per `rom-gap-closer` discipline, with integration tests that drive the editor end-to-end through the descriptor state machine.
3. After STRING-001..012 close, this audit row flips to ✅ AUDITED 100% in a final closure commit.

Until then, the row stays ✅ AUDITED 5% — every helper is **inventoried and ROM-cited**, and the deferred-by-design rationale is on the record.
