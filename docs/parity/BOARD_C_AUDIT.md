# `board.c` ROM Parity Audit

- **Date opened:** 2026-04-29
- **ROM source:** `src/board.c` (1199 lines, Erwin Andreasen 1995–96 note-board subsystem)
- **Python module(s):**
  - `mud/notes.py` (registry / persistence)
  - `mud/models/board.py` (`Board`, `BoardForceType`, `NoteDraft` + recipient logic)
  - `mud/models/note.py` (`Note` dataclass)
  - `mud/commands/notes.py` (`do_board`, `do_note` and helpers)
  - `mud/models/character.py` `PCData.board_name` / `last_notes` / `in_progress`
- **Status:** 🔄 IN PROGRESS — Phases 1–3 complete, gap closures in progress.

The Python implementation is structurally a port of the ROM/Erwin board system
but executes against a JSON registry instead of ROM's per-board flat files,
and exposes a request/response command vocabulary (`note post`, `note to`,
`note send`, …) instead of ROM's `CON_NOTE_*` interactive state machine. Most
gaps fall into three buckets: **the five hardcoded ROM boards are not seeded
on startup**, **post/visibility behaviors diverge from ROM** (timestamp
collisions, unread counting that ignores the recipient list, no expire/archive
sweep), and **the ROM `act()` TO_ROOM broadcasts for "starts/finishes a note"
are missing**.

---

## Phase 1 — Function Inventory

| ROM function | ROM lines | Python counterpart | Status | Notes |
|--------------|-----------|---------------------|--------|-------|
| `free_note` / `new_note` | 90–131 | implicit (Python GC + `Note` dataclass) | ✅ N/A | C allocator boilerplate. |
| `append_note` | 134–143 | `mud/notes.py:save_board` (JSON dump) | ⚠️ PARTIAL | ROM appends ROM-format text to flat file; Python writes JSON. Persistence formats diverge by design — acceptable. |
| `finish_note` | 146–186 | `mud/models/board.py:Board.post` + `mud/notes.py:save_board` | ⚠️ PARTIAL | Missing unique `date_stamp` collision logic (BOARD-004); save behavior parity. |
| `board_number` / `board_lookup` | 189–210 | `mud/notes.py:find_board` / iteration in `do_board` | ✅ AUDITED | Lookup is name-based via `storage_key`. |
| `unlink_note` | 213–227 | `del board.notes[index]` in `do_note remove` | ✅ AUDITED | |
| `find_note` | 230–244 | `mud/commands/notes.py:_find_visible_note_index` | ✅ AUDITED | Visibility-gated lookup matches ROM. |
| `save_board` / `save_notes` / `load_board` / `load_boards` | 247–405 | `mud/notes.py:save_board` / `load_boards` | ⚠️ PARTIAL | Missing expire-archive sweep on load (BOARD-008). |
| `is_note_to` | 408–440 | `mud/commands/notes.py:_is_note_visible_to` | ✅ AUDITED | Numeric trust check, immortal/imp tokens, sender, "all", explicit name all match ROM. |
| `unread_notes` | 444–460 | `mud/models/board.py:Board.unread_count` | ❌ MISSING | Python ignores `is_note_to` filter (BOARD-005). |
| `do_nwrite` | 467–559 | `mud/commands/notes.py:do_note "write"` (and `to`/`subject`/`text`/`send`) | ⚠️ PARTIAL | Vocabulary diverges (no CON state machine). Missing TO_ROOM `act("$n starts writing a note.")` (BOARD-002). |
| `do_nread` | 563–612 | `mud/commands/notes.py:_read_next_unread_note` + `note read N` | ✅ AUDITED | Number / next / next-board cascade match. |
| `do_nremove` | 615–643 | `mud/commands/notes.py:do_note "remove"` | ✅ AUDITED | Author or `MAX_LEVEL` may remove. |
| `do_nlist` | 648–687 | `mud/commands/notes.py:do_note "list"` | ✅ AUDITED | Number-arg "last N visible" filter matches. |
| `do_ncatchup` | 690–704 | `mud/commands/notes.py:do_note "catchup"` | ✅ AUDITED | Misspelling "All mesages skipped." preserved. |
| `do_note` | 707–738 | `mud/commands/notes.py:do_note` | ⚠️ PARTIAL | Adds `post`/`to`/`subject`/`text`/`send`/`expire` subcommands not in ROM; missing `do_help "note"` fallback (BOARD-013). |
| `do_board` | 743–840 | `mud/commands/notes.py:do_board` | ⚠️ PARTIAL | Listing access filter uses `can_read` instead of `unread_notes != BOARD_NOACCESS`; tied to BOARD-005. |
| `personal_message` / `make_note` | 843–886 | ❌ NONE | ❌ MISSING | No programmatic note-injection API for systems (death notifications, mail) (BOARD-018). |
| `next_board` | 889–903 | `mud/commands/notes.py:_next_readable_board` | ✅ AUDITED | |
| `handle_con_note_to/subject/expire/text/finish` | 905–1198 | replaced by `note to/subject/text/send/expire` request/response subcommands | ⚠️ PARTIAL | Missing TO_ROOM "$n finishes $s note." broadcast on post (BOARD-003). |
| ROM hardcoded `boards[MAX_BOARD]` table | 67–76 | ❌ NONE | ❌ MISSING | Five default boards (General/Ideas/Announce/Bugs/Personal) with specific levels/force-types/purge-days never seeded (BOARD-001). |

---

## Phase 2 — Verification highlights

### Hardcoded board table (`boards[MAX_BOARD]`, ROM 67–76)

ROM ships exactly five boards with these properties:

| short_name | description                       | read | write | default | force_type   | purge_days |
|------------|-----------------------------------|-----:|------:|---------|--------------|-----------:|
| General    | General discussion                | 0    | 2     | all     | DEF_INCLUDE  | 21         |
| Ideas      | Suggestion for improvement        | 0    | 2     | all     | DEF_NORMAL   | 60         |
| Announce   | Announcements from Immortals      | 0    | L_IMM | all     | DEF_NORMAL   | 60         |
| Bugs       | Typos, bugs, errors               | 0    | 1     | imm     | DEF_NORMAL   | 60         |
| Personal   | Personal messages                 | 0    | 1     | all     | DEF_EXCLUDE  | 28         |

These are referenced by every other function (`do_board` enumeration, default
recipient handling on `do_nwrite`, `personal_message` posting to "Personal",
etc.). Python's `mud/notes.py` lazily creates whatever board name happens to
be requested with all-zero defaults; on a fresh install nothing exists until
something writes JSON to `data/boards/`. Result: a brand-new player typing
`board` sees an empty list and `boards[i]` integer-indexing semantics from
`do_board <N>` cannot be replicated.

### `finish_note` unique date_stamp (ROM 154–160)

```c
if (last_note_stamp >= current_time)
    note->date_stamp = ++last_note_stamp;
else
{
    note->date_stamp = current_time;
    last_note_stamp = current_time;
}
```

Two notes posted in the same second get distinct, monotonically increasing
stamps. `Board.post` in `mud/models/board.py:102` uses `time.time()` directly
and stores the float — two rapid posts collide on integer-second granularity
in the JSON serializer (`Note.to_json` keeps the float, but the `last_note`
timestamp comparison done in `_read_next_unread_note` and `unread_count`
treats `>` strictly, so a note whose stamp equals `last_read` is silently
skipped on the next `note` invocation).

### `unread_notes` recipient filter (ROM 444–460)

```c
for (note = board->note_first; note; note = note->next)
    if (is_note_to(ch, note) && ((long)last_read < (long)note->date_stamp))
        count++;
```

Python `Board.unread_count` (`mud/models/board.py:121`) iterates all notes
ignoring `to_list`. For the Personal board this leaks unread counts to
non-recipients; for boards with arbitrary `to_list` filtering (per-name or
per-trust-level) it overcounts.

### Expire / archive sweep on load (ROM 365–383)

`load_board` drops notes whose `expire < current_time`, appends them to
`<board>.old`, and marks the board changed. `mud/notes.py:load_boards` keeps
expired notes forever; the JSON file grows without bound and stale entries
remain visible.

### Missing TO_ROOM broadcasts (ROM 503, 1181)

```c
act ("{G$n starts writing a note.{x", ch, NULL, NULL, TO_ROOM);
…
act ("{G$n finishes $s note.{x", ch, NULL, NULL, TO_ROOM);
```

`note write` and `note send` in `mud/commands/notes.py` return only the actor
text. Bystanders in the room never see either message.

### `personal_message` API (ROM 843–846)

```c
void personal_message (const char *sender, const char *to,
                       const char *subject, const int expire_days,
                       const char *text)
{
    make_note ("Personal", sender, to, subject, expire_days, text);
}
```

ROM exposes this so other subsystems (death notifications, system mail) can
post Personal-board notes programmatically. Python has no equivalent. The
`mud/commands/communication.py:_queue_personal_message` is a different
mechanism (in-memory tells) that does not interact with the boards subsystem.

---

## Phase 3 — Gap Table

| ID | Severity | ROM ref | Python ref | Description | Status |
|----|----------|---------|------------|-------------|--------|
| BOARD-001 | CRITICAL | `src/board.c:67-76` | `mud/notes.py:23` (no seed) | The five ROM default boards (General/Ideas/Announce/Bugs/Personal) are not seeded with their ROM levels/force-types/purge-days at startup. | ✅ FIXED |
| BOARD-002 | IMPORTANT | `src/board.c:503` | `mud/commands/notes.py:341-355` | Starting a note does not emit `act("$n starts writing a note.", TO_ROOM)`. | ✅ FIXED |
| BOARD-003 | IMPORTANT | `src/board.c:1181` | `mud/commands/notes.py:388-418` | Posting a note does not emit `act("$n finishes $s note.", TO_ROOM)`. | ✅ FIXED |
| BOARD-004 | CRITICAL | `src/board.c:154-160` | `mud/models/board.py:102-114` | `Board.post` uses `time.time()` directly; lacks ROM `last_note_stamp` collision logic — same-second posts share a stamp and silently break the `> last_read` unread cursor. | ✅ FIXED |
| BOARD-005 | CRITICAL | `src/board.c:444-460` | `mud/models/board.py:121-125` | `Board.unread_count` does not filter notes by recipient (`is_note_to`); leaks Personal/per-name notes into non-recipients' unread counts. | ✅ FIXED |
| BOARD-006 | IMPORTANT | `src/board.c:758-769,793-798,828-832` | `mud/commands/notes.py:190-237` | `do_board` enumeration uses `can_read(trust)` instead of ROM's `unread_notes != BOARD_NOACCESS`; resolved transitively once BOARD-005 lands but the listing also needs to call the recipient-aware unread helper. | ✅ FIXED (subsumed by BOARD-005) |
| BOARD-007 | MINOR | `src/board.c:790-812` | `mud/commands/notes.py:225-231` | `do_board <N>` numbers boards by accessible position, matching ROM once BOARD-006 is closed; no separate fix needed. | 🔄 OPEN (subsumed) |
| BOARD-008 | CRITICAL | `src/board.c:365-383` | `mud/notes.py:23-32` | `load_boards` does not drop notes whose `expire < now` nor archive them to `<board>.old`. | ✅ FIXED |
| BOARD-009 | MINOR | `src/board.c:436-437` | `mud/commands/notes.py:101-104` | ROM allows `to_list` to be a number meaning "trust ≥ that number"; Python checks the entire `to` field is digits. ROM is identical (`is_number(note->to_list) && get_trust(ch) >= atoi(note->to_list)`); no gap. | ✅ NO GAP |
| BOARD-010 | MINOR | `src/board.c:569-572` | `mud/commands/notes.py:327-339` | `note read again` in ROM is a no-op (empty `if` body); Python returns "Read which note?". Cosmetic, deferred. | 🔄 DEFERRED (cosmetic) |
| BOARD-011 | IMPORTANT | `src/board.c:482-488` | `mud/commands/notes.py:162-177` | ROM `do_nwrite` discards an `in_progress` draft whose `text` is NULL ("cancelled because you did not manage to write any text before losing link"); Python silently reuses any draft. | 🔄 DEFERRED |
| BOARD-012 | IMPORTANT | `src/board.c:707-737` | `mud/commands/notes.py:240-469` | `do_note` does not call `do_help "note"` for unknown subcommands and accepts non-ROM verbs (`post`, `to`, `subject`, `text`, `send`, `expire`). Vocabulary divergence is intentional (no telnet state machine), but the unknown-verb branch should mirror ROM `do_help`. | 🔄 DEFERRED |
| BOARD-013 | CRITICAL | `src/board.c:843-886` | `mud/notes.py:make_note` / `personal_message` | `personal_message` / `make_note` programmatic posting API not exposed; subsystems cannot inject Personal-board notes. | ✅ FIXED |
| BOARD-014 | MINOR | `src/board.c:49,1175-1182` | none | ROM AFK-flags the player while writing a note; no Python AFK plumbing in place. Architectural — deferred. | 🔄 DEFERRED |

This session targets **BOARD-001 / BOARD-002 / BOARD-003 / BOARD-004 /
BOARD-005 / BOARD-008** (the four CRITICALs plus the two TO_ROOM IMPORTANTs).
BOARD-006 collapses into BOARD-005 once the unread helper is recipient-aware.
BOARD-010 / BOARD-011 / BOARD-012 / BOARD-013 / BOARD-014 are documented and
left for a follow-up session — none change visible counts/contents on a fresh
install, only edge cases or out-of-scope architectural plumbing.

---

## Phase 4 — Gap Closures

(Filled in as gaps close; one row per gap with test name and commit hash.)

| ID | Test | Commit | Status |
|----|------|--------|--------|
| BOARD-001 | `tests/integration/test_boards_rom_parity.py::test_rom_default_boards_seeded_on_load` | (this commit) | ✅ |
| BOARD-002 | `tests/integration/test_boards_rom_parity.py::test_note_write_broadcasts_to_room` | (this commit) | ✅ |
| BOARD-003 | `tests/integration/test_boards_rom_parity.py::test_note_send_broadcasts_to_room` | (this commit) | ✅ |
| BOARD-004 | `tests/integration/test_boards_rom_parity.py::test_post_assigns_unique_timestamp_when_called_in_same_second` | (this commit) | ✅ |
| BOARD-005 | `tests/integration/test_boards_rom_parity.py::test_unread_count_skips_notes_not_addressed_to_reader` | (this commit) | ✅ |
| BOARD-008 | `tests/integration/test_boards_rom_parity.py::test_load_boards_archives_expired_notes` | (this commit) | ✅ |
| BOARD-013 | `tests/integration/test_boards_rom_parity.py::test_personal_message_posts_to_personal_board` (+ unknown-board / oversized-text) | (pending commit) | ✅ |

---

## Phase 5 — Closure

Pending. Will be filled at session handoff.
