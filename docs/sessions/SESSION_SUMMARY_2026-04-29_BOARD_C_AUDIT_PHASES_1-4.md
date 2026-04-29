# Session Summary — 2026-04-29 — `board.c` audit (Phases 1–4, 6 gaps closed)

## Scope

ROM `src/board.c` (Erwin Andreasen 1995–96 note-board subsystem, 1199 lines)
went from ❌ Not Audited 35% to ⚠️ Partial 85%. The audit doc with 14 stable
gap IDs lives at `docs/parity/BOARD_C_AUDIT.md`. Six gaps closed (one TDD
commit per gap); five deferred (minor / architectural); one confirmed not a
gap; one subsumed transitively.

## Closed gaps

| ID | Severity | Commit | What changed |
|----|---------|--------|--------------|
| BOARD-001 | CRITICAL | 7256e3d | Seed five hardcoded ROM boards (General/Ideas/Announce/Bugs/Personal) on `load_boards()` with their `src/board.c:67-76` levels / force-types / default recipients / purge-days. Persisted JSON content overlays the seed without lowering the ROM static metadata. |
| BOARD-002 | IMPORTANT | ae2a75c | `note write` emits `act("$n starts writing a note.", TO_ROOM)` (`src/board.c:503`) via `char.room.broadcast(... exclude=char)`. |
| BOARD-003 | IMPORTANT | ae2a75c | `note send` emits `act("$n finishes $s note.", TO_ROOM)` (`src/board.c:1181`); adds `_possessive(char)` for ROM `$s` (his/her/its). |
| BOARD-004 | CRITICAL | e5bb5a2 | `Board.post` routes through `mud.notes.next_note_stamp(base)` + module-level `_last_note_stamp` (`src/board.c:81,154-160`); two same-second posts now get distinct monotonically increasing stamps so the `> last_read` unread cursor cannot collide. |
| BOARD-005 (and BOARD-006) | CRITICAL / IMPORTANT | 4d63623 | Adds canonical `mud.notes.is_note_to(char, note)` (ROM `is_note_to` at `src/board.c:408-440`) and `Board.unread_count_for(char, last_read)` (ROM `unread_notes` at `src/board.c:444-460`). `do_board` listing uses the recipient-aware count, transitively closing BOARD-006. |
| BOARD-008 | CRITICAL | df056ac | `load_boards` sweeps every loaded board for notes whose `expire < now`, appends them to `<board>.old.json`, and re-saves the active board (`src/board.c:365-383`). Boards no longer grow without bound. |

## Deferred / no-gap

| ID | Disposition | Reason |
|----|-------------|--------|
| BOARD-009 | ✅ NO GAP | Numeric `to_list` "trust ≥ N" check in Python already matches ROM; no fix needed. |
| BOARD-010 | 🔄 DEFERRED (cosmetic) | ROM `note read again` is a no-op (empty `if` body at `src/board.c:569-572`); Python returns "Read which note?". Cosmetic. |
| BOARD-011 | 🔄 DEFERRED | ROM discards an in-progress draft whose text is NULL ("cancelled because you did not manage to write any text"); Python silently reuses any draft. Edge case under request/response model. |
| BOARD-012 | 🔄 DEFERRED | `do_note` does not call `do_help "note"` for unknown subcommands and accepts non-ROM verbs (`post`/`to`/`subject`/`text`/`send`/`expire`). Vocabulary divergence is intentional (no telnet `CON_NOTE_*` state machine). |
| BOARD-013 | 🔄 DEFERRED | `personal_message` / `make_note` programmatic posting API not exposed; subsystems cannot inject Personal-board notes. Architectural — needs a new caller path. |
| BOARD-014 | 🔄 DEFERRED | ROM AFK-flags the player while writing a note; no Python AFK plumbing in place. Architectural — out of scope for this audit. |

## Files touched

- `docs/parity/BOARD_C_AUDIT.md` (new — full audit doc)
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` (board.c row flipped)
- `mud/notes.py` — seed table, `next_note_stamp`, `is_note_to`, expire/archive sweep
- `mud/models/board.py` — unique-stamp routing, `unread_count_for`
- `mud/commands/notes.py` — TO_ROOM broadcasts, `is_note_to` delegation, recipient-aware listing
- `tests/integration/test_boards_rom_parity.py` (new — 6 ROM-parity tests)
- `tests/test_boards.py` — three pre-existing tests adjusted to not contradict ROM (General is `DEF_INCLUDE("all")` so private-recipient tests need a NORMAL override; the `initialize_world_loads_boards_from_disk` test now passes `purge_days=21` to match ROM so the new archive sweep doesn't drop its synthetic note)
- `CHANGELOG.md` — `board.c` `Added` + `Fixed` blocks
- `pyproject.toml` — `2.6.34` → `2.6.35`

## Pre-existing test baseline

The pre-existing `~50 failures` baseline (`test_olc_save`, `test_building`,
`test_commands`, `test_logging_admin`) was untouched. All 26 board-touching
tests (`tests/test_boards.py` 20 + `tests/integration/test_boards_rom_parity.py`
6) green.

## Next intended task

Either:

1. **Pick up the remaining `board.c` deferred items** if note posting needs
   programmatic injection — start with **BOARD-013** (`personal_message` /
   `make_note` API) since it unblocks death-notification / system-mail
   features.
2. **Move on** to another tracker target. Top P2 candidates:
   - `comm.c` (P3 ❌ Not Audited 50%) — networking arch is already different,
     but command-side comm parity may have gaps.
   - **OLC cluster** (`olc.c` / `olc_act.c` / `olc_save.c` / `olc_mpcode.c` /
     `hedit.c`) — note `tests/test_olc_save.py` already has 13 pre-existing
     failures.
   - **Deferred NANNY trio** (NANNY-008/009/010) — architectural-scope.
