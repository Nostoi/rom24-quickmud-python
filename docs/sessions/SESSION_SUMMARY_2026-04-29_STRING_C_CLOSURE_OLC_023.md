# Session Summary — 2026-04-29 — `string.c` ✅ 100% closure + OLC-023 real-bug fix

## Scope

Continuation of the OLC parity-closure plan path (a) from the prior `string.c`
audit + OLC-INFRA-001 / BIT cluster session. Goal: close the remaining
STRING gaps to flip `string.c` from ⚠️ Partial → ✅ AUDITED 100%, and pick up
one CRITICAL real-bug from the `olc.c` audit (OLC-023, `do_alist`) that didn't
require opening the held `olc_act.c` sibling audit. The `olc_act.c` /
`olc_save.c` / `olc_mpcode.c` / `hedit.c` audits remain on hold per user
direction; OLC-016/017/018/019 are gated on those and were not attempted.

Subagent delegation was used heavily this session: a Haiku subagent closed
STRING-003/001/002 sequentially (3 commits), a Sonnet subagent closed
STRING-005 `format_string` (1 commit), and a Sonnet subagent closed the
STRING-004 `string_add` keystone (1 commit, 24 tests). The main loop closed
OLC-023.

## Outcomes

### `string.c` file row — ✅ AUDITED 100% (was ⚠️ Partial 60% pre-session)

All 12 public helpers from `src/string.c` are now ported with integration
coverage. The file flips from ⚠️ Partial → ✅ AUDITED in
`docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`. STRING-001..012 all closed
or already closed.

### `STRING-003` — ✅ FIXED

- **Python**: `mud/utils/string_editor.py:string_replace`
- **ROM C**: `src/string.c:95-112`
- **Fix**: pure single-occurrence substring substitute. Empty `old` returns
  `orig` unchanged (ROM behavior).
- **Tests**: `tests/integration/test_string_editor_replace.py` (9 cases, green)
- **Commit**: `69faedd`

### `STRING-001` — ✅ FIXED

- **Python**: `mud/utils/string_editor.py:string_edit`
- **ROM C**: `src/string.c:38-57`
- **Fix**: descriptor-state setter — clears the `StringEdit` buffer, returns
  the 4-line ROM editor banner verbatim. Caller wires the `on_commit` callback
  (Python adaptation of ROM's `pString` pointer-to-pointer pattern).
- **Tests**: `tests/integration/test_string_editor_edit.py` (6 cases, green)
- **Commit**: `bc9350c`

### `STRING-002` — ✅ FIXED

- **Python**: `mud/utils/string_editor.py:string_append`
- **ROM C**: `src/string.c:66-86`
- **Fix**: descriptor-state setter — preserves the existing buffer, returns
  banner + `numlines()` listing of current contents.
- **Tests**: `tests/integration/test_string_editor_append.py` (9 cases, green)
- **Commit**: `6619be6`

### `OLC-023` — ✅ FIXED (real bug)

- **Python**: `mud/commands/imm_olc.py:do_alist`
- **ROM C**: `src/olc.c:1478-1502`
- **Fix**: `do_alist` was iterating `getattr(registry, "areas", [])` — an
  attribute that does not exist on `mud.registry`. On a live system the
  command returned only the header row. Fixed to iterate
  `area_registry.values()`. Two additional drifts corrected: first column now
  prints `area.vnum` (was a 1-indexed `enumerate` counter — ROM emits
  `pArea->vnum` per `src/olc.c:1494`), and the filename column now reads the
  real attribute `area.file_name` (was the nonexistent `area.filename`).
- **Tests**: `tests/integration/test_olc_alist.py` (4 cases, green)
- **Commit**: `b1efdf5`

### `STRING-005` — ✅ FIXED (Sonnet subagent)

- **Python**: `mud/utils/string_editor.py:format_string`
- **ROM C**: `src/string.c:299-451`
- **Fix**: two-phase ROM-faithful port — Phase 1 normalizes whitespace,
  emits sentence-end double-space after `.`/`?`/`!`, consumes quote-after-punct,
  rebalances parens, applies capitalize-after-sentence flag. Phase 2 word-wraps
  at 77 cols with the ROM quirk that the *first* wrap scans back from col 73
  (not 76, per ROM line 418 `(xbuf[0] ? 76 : 73)`). Mid-word `-\n\r` fallback
  emits `logging.warning("format_string: no spaces")` (mirrors ROM's
  `bug("No spaces", 0)`).
- **Tests**: `tests/integration/test_string_editor_format_string.py` (16 cases,
  green incl caplog assertion for the long-word fallback)
- **Commit**: `c47bfd4`

### `STRING-004` — ✅ FIXED (Sonnet subagent, the keystone)

- **Python**: `mud/utils/string_editor.py:string_add`
- **ROM C**: `src/string.c:121-286`
- **Fix**: 115-line per-line input dispatcher — the entire OLC editor UX.
  Implements `.c` (clear), `.s` (show via `numlines`), `.r 'old' 'new'` (uses
  `first_arg` twice + `string_replace`), `.f` (`format_string`), `.h` (help),
  `.ld <num>` (`string_linedel`), `.li <num> <text>` / `.lr <num> <text>`
  (`string_lineadd` / linedel+lineadd). `~` and `@` terminators call
  `session.string_edit.on_commit(buffer)` and clear `session.string_edit`.
  Length cap at `string_edit.max_length` (= MAX_STRING_LENGTH − 4 = 4604).
  All input lines pass through `smash_tilde`.
- **ROM-C ambiguities resolved** (preserved verbatim by the subagent):
  - Return strings locked to ROM verbatim (e.g. `"String cleared.\n\r"`,
    `'usage:  .r "old string" "new string"\n\r'`, `"SEdit:  Invalid dot
    command.\n\r"` — two spaces after colon).
  - **`~` terminator deviation cited in code**: ROM `src/string.c:128` smashes
    tildes *before* the terminator check at line 230, making `~` dead code at
    runtime. The Python port intentionally reverses the order (terminator
    check first) so both `~` and `@` work as the `.h` help text documents.
  - `.r` validates only `arg2` per ROM line 159; empty `arg3` (delete `arg2`
    from buffer) is valid.
  - `.li`/`.lr` use the raw remainder after `arg2` (multi-word text preserved),
    not a further `first_arg` parse.
  - Length cap is `len(buf) + len(line) >= max_length` (no `+2`); overflow
    forces `session.string_edit = None` without calling `on_commit`
    (mirrors ROM line 271).
- **Tests**: `tests/integration/test_string_editor_string_add.py` (24 cases, green)
- **Commit**: `f220398`

## Files Modified

- `mud/utils/string_editor.py` — `string_replace`, `string_edit`,
  `string_append`, `format_string`, `string_add` added (joining the 7
  helpers landed earlier in the day)
- `mud/commands/imm_olc.py` — `do_alist` real-bug fix
- `tests/integration/test_string_editor_replace.py` — new (STRING-003)
- `tests/integration/test_string_editor_edit.py` — new (STRING-001)
- `tests/integration/test_string_editor_append.py` — new (STRING-002)
- `tests/integration/test_string_editor_format_string.py` — new (STRING-005)
- `tests/integration/test_string_editor_string_add.py` — new (STRING-004)
- `tests/integration/test_olc_alist.py` — new (OLC-023)
- `docs/parity/STRING_C_AUDIT.md` — flipped to ✅ AUDITED 100%; rows
  STRING-001/002/003/004/005 ❌→✅
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `string.c` row flipped
  to ✅ AUDITED 100%
- `docs/parity/OLC_C_AUDIT.md` — OLC-023 row ⚠️ BROKEN → ✅ AUDITED
- `CHANGELOG.md` — STRING-001/002/003/004/005 + OLC-023 entries under
  `[Unreleased]`
- `pyproject.toml` — 2.6.64 → 2.6.71 (7 patch bumps; one per gap)

## Test Status

- `pytest tests/integration/test_string_editor_*.py tests/integration/test_bit_*.py
  tests/integration/test_olc_*.py` → **216 / 216 passing** (~0.74s)
- Full suite not re-run this session (large; subagent-by-subagent runs all
  green for area + STRING + OLC scopes)
- `ruff check` clean for new files (pre-existing whitespace issues elsewhere
  in `mud/commands/imm_olc.py` left untouched per scope)

## Commits this session

| SHA | Gap | Severity |
|-----|-----|----------|
| `69faedd` | STRING-003 `string_replace` | MINOR |
| `bc9350c` | STRING-001 `string_edit` | IMPORTANT |
| `6619be6` | STRING-002 `string_append` | IMPORTANT |
| `b1efdf5` | OLC-023 `do_alist` real-bug | CRITICAL |
| `c47bfd4` | STRING-005 `format_string` | IMPORTANT |
| `f220398` | STRING-004 `string_add` (keystone) | CRITICAL |

## Next Steps

The `string.c` cluster is fully closed. Carried-forward work for the next
session, in priority order:

1. **OLC sibling audits (currently held)** — closing the remaining
   `olc.c` CRITICAL gaps requires opening one or more sibling audits:
   - `OLC-016` (cmd_aedit `create`), `OLC-017` (cmd_redit `reset`/`create`/
     `<vnum>` teleport), `OLC-018` (cmd_oedit `create`), `OLC-019`
     (cmd_medit `create`) all gated on `aedit_create`/`redit_create`/
     `oedit_create`/`medit_create` builders living in `src/olc_act.c`.
     Lifting the hold means starting `/rom-parity-audit olc_act.c` next.
2. **OLC-020** (display_resets — depends on BIT-002 already closed),
   **OLC-022** (do_resets `inside`/`wear-loc`/`R-reset` subcommands —
   depends on BIT-001 already closed) — both *unblocked* now and could be
   closed without opening sibling audits. Smaller scope than 016-019.
3. **README/AGENTS/SESSION_STATUS coordinated refresh** — outstanding from
   prior session: README still says "13 of 43 files at 100%"; actual is
   now 21/43 with `string.c` flipping this session. Per AGENTS.md Repo
   Hygiene, this is a single coordinated commit, NOT bundled with parity
   work.
