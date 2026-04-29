# Session Summary — 2026-04-29 — `string.c` audit ✅ (12 gaps DEFERRED to OLC cluster)

## Scope

Audit of ROM `src/string.c` (692 lines, 12 public functions — the OLC string-editor
backend). Goal: replace the stale tracker entry ("⚠️ Partial 85% — `mud/utils.py`")
with an accurate inventory and gap list, so the next agent picking up the OLC
cluster has a faithful map of the work.

## Outcomes

### `string.c` file row — ✅ AUDITED (5%, was stale "85%")

- **Python primary**: `mud/utils/text.py` (`smash_tilde` only, and that one is owned
  by `merc.h` rather than `string.c` proper).
- **ROM C**: `src/string.c:38-692` (12 public functions).
- **Finding**: every function in `string.c` operates on descriptor-level OLC editor
  state (`ch->desc->pString`, `ch->desc->editor`, `ED_MPCODE`) and is reached only
  from (a) `olc_act.c` builders, (b) `string_add` itself, (c) `comm.c::game_loop_*`
  routing input when the descriptor is in EDIT/APPEND mode. With `mud/olc/` empty
  (skeleton only — `__init__.py` + `save.py`), there are no Python consumers of any
  of these helpers. The previous tracker note's "85%" claim and the `mud/utils.py`
  path were both incorrect: `mud/utils.py` does not exist (only the package
  `mud/utils/`), and within that package only `smash_tilde` is ported.
- **Decision**: all 12 helpers are filed as deferred-by-design gaps. Closing them
  in isolation would yield code with zero callers and zero integration coverage.
  They are real ROM-parity work, blocked on prerequisite OLC plumbing (descriptor
  `pString`/`editor` fields, game-loop dispatch hook, `olc_act.c` builders).

### Phase 1 inventory — 12 of 12 functions catalogued

| ROM symbol | ROM lines | Severity | Gap ID |
|------------|-----------|----------|--------|
| `string_edit` | 38-57 | IMPORTANT | STRING-001 |
| `string_append` | 66-86 | IMPORTANT | STRING-002 |
| `string_replace` | 95-112 | IMPORTANT | STRING-003 |
| `string_add` | 121-286 | CRITICAL | STRING-004 |
| `format_string` | 299-451 | IMPORTANT | STRING-005 |
| `first_arg` | 468-508 | MINOR | STRING-006 |
| `string_unpad` | 516-543 | MINOR | STRING-007 |
| `string_proper` | 551-572 | MINOR | STRING-008 |
| `string_linedel` | 574-605 | IMPORTANT | STRING-009 |
| `string_lineadd` | 607-645 | IMPORTANT | STRING-010 |
| `merc_getline` | 647-674 | MINOR | STRING-011 |
| `numlines` | 676-692 | IMPORTANT | STRING-012 |

`STRING-004` is severity-CRITICAL because `string_add` is the entire editor UX —
a partial port would silently corrupt OLC sessions; it must be ported faithfully
or not at all.

## Files Modified

- `docs/parity/STRING_C_AUDIT.md` — new file, full Phase 1–5 audit with deferred-by-design rationale.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `string.c` row flipped ⚠️ Partial 85% → ✅ Audited 5%; P3-3 narrative section rewritten to reflect the deferred-to-OLC posture.
- `CHANGELOG.md` — added `### Changed` `string.c` audit entry under `[Unreleased]`.
- `pyproject.toml` — 2.6.52 → 2.6.53 (patch bump, this audit-only commit).

## Test Status

No code changes this session. No new tests. Existing suite unchanged from the
2.6.52 baseline:

- `pytest tests/integration/` — 1455 passed / 10 skipped (last run from CONST-006 handoff).
- `ruff check .` — clean (no new files in lint-tracked paths; `docs/` is excluded).

## Next Steps

`string.c` is now ✅ Audited 5% with all 12 deferred-by-design gaps documented.
Three reasonable next-file options:

1. **`olc.c`** (P2, ❌ Not Audited 30%) — the natural next step. Closing
   STRING-001..012 happens here, plus the BIT-001..003 and CONST-007 deferrals
   that are also waiting on OLC infrastructure. This is the largest single
   remaining audit and will probably take 2–3 sessions.
2. **`board.c`** (P2, ⚠️ Partial 95%) — only 2 deferred-by-design items remain
   (BOARD-010 cosmetic, BOARD-014 architectural AFK plumbing). A short
   confirm-and-close session.
3. **`hedit.c`** (P2, ❌ Not Audited 30%) — help-system editor, smaller than
   `olc.c`, but also needs descriptor editor plumbing. Probably bundles into
   the OLC cluster regardless.

After OLC, only `string.c` deferrals close (alongside BIT-001..003, CONST-007),
and 1–2 short closure sessions remain. **6–10 sessions to 100%** across the
43-file tracker.

**Repo Hygiene flag (still standing)**: README.md lines 172 + 335 say
"13 of 43 files at 100%" — actual is 19/43 ✅ Audited (no change this session
since the row flip is a stale-fix, not a fresh audit). Per Repo Hygiene §2,
the next commit that touches README must coordinate-refresh AGENTS.md tracker
pointers + `SESSION_STATUS.md` so the three surfaces don't disagree. Treat as
a documentation-shaped task in its own commit.
