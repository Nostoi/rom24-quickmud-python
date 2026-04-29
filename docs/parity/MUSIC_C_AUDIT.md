# `music.c` Audit — ROM 2.4b6 → QuickMUD-Python Parity

**Status:** 🔄 IN PROGRESS — gap inventory complete; closures pending
**Date:** 2026-04-29
**ROM C:** `src/music.c` (355 lines, 3 public functions)
**Python:** `mud/music/__init__.py`, `mud/commands/player_info.py:67-144`
**Priority:** P2 (gameplay-visible jukebox + global "MUSIC:" channel)

## Phase 1 — Function Inventory

| ROM C function | ROM lines | Python equivalent | Status |
|----------------|-----------|-------------------|--------|
| `song_update` | `src/music.c:45-156` | `mud/music/__init__.py:43-126` (`song_update` + helpers) | ✅ AUDITED (minor pending: MUSIC-005, MUSIC-006) |
| `load_songs` | `src/music.c:160-218` | _none_ | ❌ MISSING (MUSIC-002) |
| `do_play` | `src/music.c:220-354` | `mud/commands/player_info.py:67-144` | ⚠️ PARTIAL — stub (MUSIC-001, MUSIC-003, MUSIC-004) |

## Phase 2 — Line-by-line Verification

### `song_update` — global channel + jukebox tick

ROM `src/music.c:55-99` (global channel):

- Lines 56-57: clamp `channel_songs[1] >= MAX_SONGS` to `-1`. ✅ Python `mud/music/__init__.py:51-52`.
- Lines 59-99: gate on `channel_songs[1] > -1`; otherwise no global broadcast. ✅ Python `:54-56`.
- Lines 61-69: when `channel_songs[0] >= MAX_LINES` or past `song.lines`, mark `[0]=-1` and shift the queue forward (`channel_songs[i] = channel_songs[i+1]`) with the tail slot cleared. ✅ Python `_advance_channel_queue` `:78-82`.
- Lines 73-86: first tick of a song prints `"Music: <group>, <name>"` and sets `channel_songs[0] = 0`; later ticks print `"Music: '<lyric>'"` and increment the line counter. ✅ Python `:68-73`.
- Lines 88-97: broadcast filter — `d->connected == CON_PLAYING && !COMM_NOMUSIC && !COMM_QUIET`, using `act_new(... POS_SLEEPING)` so even sleeping players hear the global channel. Python uses `broadcast_global(should_send=_can_hear_music)` which iterates `character_registry` and filters NOMUSIC + QUIET. **Diverges (MINOR, MUSIC-005):** Python doesn't gate on `connected == CON_PLAYING` (linkdead/menu players are counted as long as `is_npc=False`), and doesn't honor switched players (`d->original ? d->original : d->character`).

ROM `src/music.c:101-155` (jukebox tick):

- Lines 101-104: iterate `object_list`, skip non-jukeboxes or `value[1] < 0`. ✅ Python `_update_jukeboxes` `:85-95`.
- Lines 106-110: `value[1] >= MAX_SONGS` → reset to `-1`, continue. ✅ Python `:97-99`.
- Lines 114-120: room resolution — `obj->in_room` else `obj->carried_by->in_room`. ✅ Python `_resolve_room` `:136-143`.
- Lines 122-131: first tick of a song calls `act("$p starts playing %s, %s.", room->people, obj, NULL, TO_ALL)` and sets `value[0] = 0`. Python emits `"<short_descr> starts playing <group>, <name>."` via `broadcast_room`. **Diverges (MINOR, MUSIC-006):** ROM's `act()` runs `$p` substitution per-viewer and respects `can_see_obj`/short-vs-name. Python passes a single string for everyone.
- Lines 134-146: line index past end → `value[0]=-1`, scroll queue (`value[1..4]` ← `value[2..4], -1`), continue. ✅ Python `_scroll_jukebox_queue` `:129-133` (note: this leaves `value[0]=-1` so the next tick runs the "starts playing" branch for the new song, matching ROM).
- Lines 148-154: print `"$p bops: '<line>'"` via `act(... TO_ALL)` and increment. ✅ Python `:122-126` (with the same MUSIC-006 caveat re: `$p`).

### `load_songs` — `area/music.txt` ingestion

ROM `src/music.c:160-218`:

- Resets `channel_songs[0..MAX_GLOBAL]` to `-1`.
- Reads `MUSIC_FILE` (`area/music.txt`) up to `MAX_SONGS` (20).
- For each entry: read group, name, then lyric lines until `~`. `'#'` terminates the table. Excess lines past `MAX_LINES` are clamped with a `bug()` warning.

Python: **no equivalent.** `mud/music/__init__.py:38` declares `song_table: list[Song | None] = [None] * MAX_SONGS` but nothing populates it from `area/music.txt`. The repo even ships `area/music.txt` (U2 / Frank Zappa / etc.), so the data exists; only the loader is missing. Result: in the live game, `song_update` does nothing for the global channel, and `do_play` cannot resolve any song name. **MUSIC-002 (CRITICAL).**

### `do_play` — `play <song> | play loud <song> | play list [artist [<prefix>]]`

ROM `src/music.c:220-354`:

- Lines 227: `one_argument(argument, arg)` — split first token, leave the rest in `str`.
- Lines 229-232: scan `ch->in_room->contents` for the first `ITEM_JUKEBOX` that `can_see_obj(ch, juke)` returns true for.
- Lines 234-244: empty argument → `"Play what?\n\r"`; no jukebox → `"You see nothing to play.\n\r"`.
- Lines 246-292: `play list [artist [<prefix>]]` — print available songs in two columns by song name (35-wide), or one row per artist when `artist` keyword is supplied. `str_prefix(argument, song_table[i].group/name)` is the filter. The header is `capitalize("<juke->short_descr> has the following songs available:\n\r")`.
- Lines 294-298: `loud` keyword sets `global = TRUE` and consumes one more token.
- Lines 300-304: empty after stripping `loud` → `"Play what?\n\r"`.
- Lines 306-311: queue-full check — global queue full when `channel_songs[MAX_GLOBAL] > -1`; jukebox full when `juke->value[4] > -1` → `"The jukebox is full up right now.\n\r"`.
- Lines 313-328: scan `song_table` for the first entry whose name has `argument` as a `str_prefix`. Empty slot or end of table → `"That song isn't available.\n\r"`.
- Lines 330-353: emit `"Coming right up.\n\r"`, then place the song id in the first free queue slot. For the global queue, slots are `channel_songs[1..MAX_GLOBAL]`; when slot 1 is filled, also reset `channel_songs[0] = -1` so the next tick prints the announcement. For jukeboxes, slots are `value[1..4]` with the same `value[0] = -1` reset when slot 1 is filled.

Python `mud/commands/player_info.py:67-144`:

- ✅ Empty arg → `"Play what?"`.
- ✅ No room or no jukebox → `"You see nothing to play."`.
- ❌ Does **not** check `can_see_obj` (MUSIC-004).
- ⚠️ `play list` reads from `mud.registry.song_table` (which doesn't exist on `mud.registry` — this is dead code that always falls through to the hardcoded three-song stub) instead of `mud.music.song_table`. Missing: `list artist`, `str_prefix` filter, header capitalization, empty-line column flushing. **MUSIC-003.**
- ❌ `play loud` is not parsed; `global = TRUE` queueing is unimplemented.
- ❌ Queue-full check missing.
- ❌ Song lookup uses no song table at all — the function just returns `"Coming right up."` without queueing anything onto `juke.value[1..4]` or `channel_songs[1..MAX_GLOBAL]`. `song_update` therefore never has a song to play. **MUSIC-001 (CRITICAL).**
- ❌ `"That song isn't available."` rejection path missing.

## Phase 3 — Gaps

| Gap ID | Severity | ROM ref | Python ref | Description | Status |
|--------|----------|---------|------------|-------------|--------|
| MUSIC-001 | CRITICAL | `src/music.c:294-353` | `mud/commands/player_info.py:139-144` | `do_play` is a stub: doesn't resolve `play loud`, doesn't check queue-full, doesn't match song by `str_prefix`, doesn't write into `juke.value[1..4]` / `channel_songs[1..MAX_GLOBAL]`, and doesn't emit `"That song isn't available."`. End result: no jukebox or global music ever queues. | ✅ FIXED — `do_play` now resolves `loud`, enforces tail-slot queue-full check, matches by case-insensitive name prefix against `mud.music.song_table`, queues into `juke.value[1..4]` / `channel_songs[1..MAX_GLOBAL]` with the slot-1 `[0]=-1` reset, and surfaces `"That song isn't available."` on no match. Tested by `tests/integration/test_music_play.py`. |
| MUSIC-002 | CRITICAL | `src/music.c:160-218` | `mud/music/__init__.py:load_songs` | No `load_songs` equivalent — `mud/music/song_table` is never populated from `area/music.txt`. The global "MUSIC:" channel and `play list` have nothing to play. | ✅ FIXED — `mud/music/__init__.py:load_songs(path)` ports the ROM parser (group~ / name~ / lyrics / `~` / `#`), resets `channel_songs[0..MAX_GLOBAL]` to `-1`, drops lyrics past `MAX_LINES` with a warning, and is invoked from `mud/world/world_state.py:initialize_world` so `area/music.txt` is loaded at boot. Tested by `tests/integration/test_music_load_songs.py`. |
| MUSIC-003 | IMPORTANT | `src/music.c:246-292` | `mud/commands/player_info.py:108-137` | `play list` pulls from a non-existent `mud.registry.song_table`, falls back to a 3-song hardcoded stub, and is missing the `list artist` mode, `str_prefix` filter, and ROM column/header formatting (`capitalize`, two-column `%-35s`, single-column `%-39s %-39s` for artist mode). | 🔄 OPEN |
| MUSIC-004 | MINOR | `src/music.c:229-232` | `mud/commands/player_info.py:91-100` | Jukebox lookup doesn't filter by `can_see_obj(ch, juke)`; invisible/dark jukeboxes are still pickable. | 🔄 OPEN |
| MUSIC-005 | MINOR | `src/music.c:88-97` | `mud/music/__init__.py:75, 146-151` | Global broadcast doesn't gate on `connected == CON_PLAYING` and doesn't honor switched-puppet `d->original`. Linkdead/menu PCs receive music; switched immortals would receive on the puppet body, not their original. | 🔄 OPEN |
| MUSIC-006 | MINOR | `src/music.c:122-154` | `mud/music/__init__.py:111-126` | Jukebox `act(... TO_ALL)` runs ROM's `$p` substitution per-viewer with `can_see_obj`. Python broadcasts a single pre-formatted string, so blind/dark viewers see the jukebox's short descr regardless of visibility. | 🔄 OPEN |

## Phase 4 — Gap Closures

_(One subsection per gap as it lands; each closure cites the integration test name and the `feat(parity)` / `fix(parity)` commit.)_

## Phase 5 — Completion Summary

_(Filled when all CRITICAL/IMPORTANT gaps are ✅ FIXED, tracker flipped, CHANGELOG and session summary written.)_
