# Session Summary — 2026-04-29 — `board.c` final pass (BOARD-011 / 012 / 013 closed)

## Scope

Continuation of the same-day `board.c` audit. The Phase 1–4 session
([SESSION_SUMMARY_2026-04-29_BOARD_C_AUDIT_PHASES_1-4.md](SESSION_SUMMARY_2026-04-29_BOARD_C_AUDIT_PHASES_1-4.md))
closed 6 of 14 gaps and left BOARD-010..014 deferred. This session closes
the three deferred gaps that did not require new architectural plumbing
(BOARD-013, BOARD-011, BOARD-012) and re-classifies the remaining two
(BOARD-010 cosmetic, BOARD-014 architectural) as **deferred-by-design**.
`board.c` advances ⚠️ Partial 85% → ⚠️ Partial 95%.

## Outcomes

### `BOARD-013` — ✅ FIXED (CRITICAL)

- **Python**: `mud/notes.py` — new `make_note(...)` and `personal_message(...)`
- **ROM C**: `src/board.c:843-886`
- **Fix**: Added programmatic posting API mirroring ROM `make_note` /
  `personal_message`. Unknown boards and text exceeding `MAX_NOTE_TEXT`
  (= `4 * MAX_STRING_LENGTH - 1000` = 17432, per `src/board.h:19`) return
  `None`; on success the note is appended via `Board.post` (so it picks up
  the `last_note_stamp` cursor), persisted with `save_board`, and
  `expire = current_time + expire_days * 86400`. Unblocks programmatic
  Personal-board injection (death notifications, system mail).
- **Tests**: `tests/integration/test_boards_rom_parity.py::test_personal_message_posts_to_personal_board`,
  `::test_make_note_returns_none_for_unknown_board`,
  `::test_make_note_rejects_text_exceeding_max_note_text`
- **Commit**: `152c8ce`

### `BOARD-011` — ✅ FIXED (IMPORTANT)

- **Python**: `mud/commands/notes.py:327-357` (`do_note` `write` branch)
- **ROM C**: `src/board.c:482-488` (`do_nwrite` cancellation block)
- **Fix**: When the player has an in-progress draft whose `text` is empty
  (lost link before typing the body), the stale draft is discarded and the
  actor sees the ROM cancellation notice ("Note in progress cancelled
  because you did not manage to write any text before losing link.")
  before a fresh draft is started.
- **Tests**: `::test_note_write_discards_textless_in_progress_draft`
- **Commit**: `0fded45`

### `BOARD-012` — ✅ FIXED (IMPORTANT)

- **Python**: `mud/commands/notes.py:469-479` (`do_note` fallthrough)
- **ROM C**: `src/board.c:707-737` (`do_note` dispatch tail)
- **Fix**: Unknown subcommands now dispatch to `do_help(ch, "note")`
  instead of returning the generic dispatcher `"Huh?"`. Vocabulary
  divergence on accepted draft verbs (`post`/`to`/`subject`/`text`/`send`/
  `expire`) remains intentional — the Python client has no telnet
  `CON_NOTE_*` state machine — and is documented in
  `BOARD_C_AUDIT.md`.
- **Tests**: `::test_note_unknown_subcommand_shows_help`
- **Commit**: `9fe74b8`

## Deferred-by-design (not gaps)

| ID | Disposition | Reason |
|----|-------------|--------|
| BOARD-010 | 🔄 DEFERRED (cosmetic) | ROM `note read again` is a no-op (empty `if` body at `src/board.c:569-572`); Python returns "Read which note?". Cosmetic edge case. |
| BOARD-014 | 🔄 DEFERRED (architectural) | ROM AFK-flags the player while writing a note (`src/board.c:49,1175-1182`); the Python port has no AFK plumbing. Out of scope for this audit; reopen alongside the AFK system. |

Both rows in `BOARD_C_AUDIT.md` already document the rationale; tracker
row updated to call them out as deferred-by-design rather than open work.

## Files Modified

- `mud/commands/notes.py` — BOARD-011 cancellation branch + BOARD-012
  `do_help` fallthrough.
- `mud/notes.py` — BOARD-013 `make_note` / `personal_message` API.
- `tests/integration/test_boards_rom_parity.py` — added 5 tests
  (BOARD-013 ×3, BOARD-011 ×1, BOARD-012 ×1). Now 11 tests, all green.
- `docs/parity/BOARD_C_AUDIT.md` — flipped rows: BOARD-011, BOARD-012,
  BOARD-013 → ✅ FIXED.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `board.c` row
  85% → 95% with deferred-by-design framing on BOARD-010/014.
- `CHANGELOG.md` — added `Fixed` entries for BOARD-011/012/013.
- `pyproject.toml` — `2.6.35` → `2.6.36` (patch — parity gap closures).

## Test Status

- `pytest tests/integration/test_boards_rom_parity.py` — 11/11 passing.
- `pytest tests/test_boards.py` — 20/20 passing.
- All 31 board-touching tests green.
- Pre-existing `~30 failures` baseline (`test_olc_save`, `test_building`,
  `test_commands`, `test_logging_admin`, `test_mobprog_triggers`)
  untouched by this session.

## Next Steps

`board.c` is effectively closed (95%; remaining 5% is intentionally
deferred). Pick a new tracker target:

1. **`comm.c`** (P3 ❌ Not Audited 50%) — networking arch already
   diverges, but command-side comm parity may have closable gaps.
2. **OLC cluster** (`olc.c` / `olc_act.c` / `olc_save.c` /
   `olc_mpcode.c` / `hedit.c`) — `tests/test_olc_save.py` already has
   ~13 pre-existing failures; treat as baseline before starting.
3. **Deferred NANNY trio** (NANNY-008/009/010) — architectural-scope
   login/state-machine work.

Recommended start: `/rom-parity-audit comm.c` (smallest scope of the
three, P3 priority makes it a low-risk warm-up after the multi-pass
`board.c` audit).
