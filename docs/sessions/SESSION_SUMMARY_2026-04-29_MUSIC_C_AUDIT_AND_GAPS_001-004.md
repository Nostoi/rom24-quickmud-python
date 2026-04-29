# Session Summary — 2026-04-29 — `music.c` audit + MUSIC-001..004 closures

## Scope

Picked up the next ⚠️ Partial row from `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` (`music.c`, P2, 60%). No prior per-file audit doc existed. Ran the full 5-phase `rom-parity-audit` flow: produced `docs/parity/MUSIC_C_AUDIT.md` with 6 stable gap IDs (`MUSIC-001..MUSIC-006`), then closed all CRITICAL+IMPORTANT gaps (4 of 6) one-test-one-commit. Both remaining MINOR cosmetics deferred with documented rationale and revisit triggers.

## Outcomes

### `MUSIC-001` — ✅ FIXED — `do_play` queues songs into juke and channel_songs

- **Python**: `mud/commands/player_info.py:do_play`
- **ROM C**: `src/music.c:220-354`
- **Gap**: `do_play` was a stub: returned `"Coming right up."` without queueing onto `juke.value[1..4]` or `channel_songs[1..MAX_GLOBAL]`, didn't parse `loud`, didn't enforce queue-full, didn't match by name prefix, never emitted `"That song isn't available."`.
- **Fix**: Ported the queueing half — `loud` keyword resolves global vs. local play; tail-slot queue-full check (`channel_songs[MAX_GLOBAL] > -1` / `juke.value[4] > -1`) → `"The jukebox is full up right now."`; case-insensitive name-prefix match against `mud.music.song_table`; `"That song isn't available."` on miss; first-free-slot insert with `value[0]=-1` reset when slot 1 fills (mirrors `src/music.c:337-352`).
- **Tests**: 7 cases in `tests/integration/test_music_play.py` (`test_do_play_queues_song_into_local_jukebox`, `test_do_play_loud_queues_song_globally`, `test_do_play_rejects_when_jukebox_queue_full`, `test_do_play_loud_rejects_when_global_queue_full`, `test_do_play_rejects_unknown_song`, `test_do_play_loud_with_empty_song_argument`, `test_do_play_matches_song_by_prefix`) — all passing.

### `MUSIC-002` — ✅ FIXED — `load_songs` ports `area/music.txt` parser and wires into boot

- **Python**: `mud/music/__init__.py:load_songs(path=area/music.txt)` + `mud/world/world_state.py:initialize_world`
- **ROM C**: `src/music.c:160-218`
- **Gap**: No `load_songs` equivalent — `mud/music/song_table` was `[None] * MAX_SONGS` at startup forever, so the global "MUSIC:" channel had nothing to broadcast and `play list` had nothing to display.
- **Fix**: Implemented a line-oriented ROM-format parser (`group~` / `name~` / lyric lines / sentinel `~` / `#` table terminator), resets `channel_songs[0..MAX_GLOBAL]` to `-1` first, drops lyrics past `MAX_LINES=100` with a warning, gracefully no-ops on a missing file. Invoked from `initialize_world` alongside `load_helps` and `load_boards`.
- **Tests**: 3 cases in `tests/integration/test_music_load_songs.py` (`test_load_songs_populates_song_table_from_music_txt`, `test_load_songs_resets_channel_queue`, `test_load_songs_handles_missing_file`) — all passing.

### `MUSIC-003` — ✅ FIXED — `play list` reads real song_table with ROM formatting

- **Python**: `mud/commands/player_info.py:do_play` (list branch)
- **ROM C**: `src/music.c:246-292`
- **Gap**: `play list` pulled from a non-existent `mud.registry.song_table` and always fell through to a 3-song hardcoded stub. No `list artist` mode, no `str_prefix` filter, no ROM formatting.
- **Fix**: Reads `mud.music.song_table`. Capitalizes the header `"<short_descr> has the following songs available:"`. Two-column `%-35s` name listing with optional case-insensitive name prefix filter; `list artist [<prefix>]` switches to single-line `%-39s %-39s` group/name pairs filtered by group prefix. Trailing odd column flushes on its own line.
- **Tests**: 4 new list-formatting cases in `tests/integration/test_music_play.py` (`test_do_play_list_uses_real_song_table_with_two_column_format`, `test_do_play_list_filters_by_name_prefix`, `test_do_play_list_artist_mode_pairs_group_and_name`, `test_do_play_list_artist_mode_filters_by_group_prefix`) — all passing.

### `MUSIC-004` — ✅ FIXED — `do_play` filters jukebox lookup with `can_see_obj`

- **Python**: `mud/commands/player_info.py:do_play` (jukebox scan)
- **ROM C**: `src/music.c:229-232`
- **Gap**: Jukebox scan didn't apply `can_see_obj(ch, juke)`; INVIS / VIS_DEATH / dark-room jukeboxes were still pickable.
- **Fix**: Added `mud.world.vision.can_see_object(ch, obj)` to the loop predicate.
- **Tests**: `tests/integration/test_music_play.py::test_do_play_skips_invisible_jukebox` — passing.

### `MUSIC-005` / `MUSIC-006` — ⚠️ DEFERRED MINOR (documented)

- **MUSIC-005** (`src/music.c:88-97`): global broadcast doesn't gate on `connected == CON_PLAYING` and doesn't honor switched-puppet `d->original`. Needs descriptor-state plumbing through `mud.net.protocol.broadcast_global` (current `should_send` callback only sees the `Character`). No gameplay impact: linkdead PCs aren't actively playing, and the project doesn't implement the ROM `switch` immortal command.
- **MUSIC-006** (`src/music.c:122-154`): jukebox `act(... TO_ALL)` runs ROM's `$p` substitution per-viewer. Python broadcasts a single pre-formatted string. Needs routing through `mud.utils.act:act_format` with per-viewer `$p` resolution that honors `can_see_object`. Cosmetic only.

## Files Modified

- `mud/commands/player_info.py` — `do_play` rewritten: queueing logic, list formatting, can_see_obj filter.
- `mud/music/__init__.py` — added `load_songs(path)` + `_read_tilde_field` helper + `DEFAULT_MUSIC_FILE`.
- `mud/world/world_state.py` — wires `load_songs()` into `initialize_world` boot path.
- `tests/integration/test_music_play.py` — new file, 12 cases covering MUSIC-001/003/004.
- `tests/integration/test_music_load_songs.py` — new file, 3 cases covering MUSIC-002.
- `docs/parity/MUSIC_C_AUDIT.md` — new audit doc; rows MUSIC-001..004 ✅ FIXED, MUSIC-005/006 ⚠️ DEFERRED, Phase 5 closure summary written.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `music.c` row flipped ⚠️ Partial 60% → ✅ Audited 95%.
- `CHANGELOG.md` — `[Unreleased]` Added entries for MUSIC-002/003 and Fixed entries for MUSIC-001/004.
- `pyproject.toml` — 2.6.44 → 2.6.45 (patch bump on session push).

## Test Status

- `tests/integration/test_music_play.py` — 12/12 passing.
- `tests/integration/test_music_load_songs.py` — 3/3 passing.
- `tests/test_music.py` — 2/2 passing (existing song_update tests).
- `tests/integration/test_do_examine_command.py` — 11/11 passing (verifies the `examine jukebox` → `do_play("list")` integration path is intact under the rewrite).
- Full integration suite: 1383/1394 passing, 10 skipped, 1 pre-existing intermittent flake (`test_kill_mob_grants_xp_integration` — confirmed flaky on master before this session, unrelated to music work).
- `ruff check` clean for all touched files.

## Next Steps

`music.c` is closed at the AUDITED level for this session. Next ⚠️ Partial candidates from the tracker (in tracker order):

1. **`const.c`** (P3, 80%) — closest to done; `mud/models/constants.py`. NANNY-009 (488-entry `title_table` port from `src/const.c:421-721`) is the largest single chunk; could be its own dedicated session per `SESSION_STATUS.md`'s prior recommendation.
2. **`bit.c`** (P3, 90%) — minor parity audit; `mud/utils.py`.
3. **OLC cluster** (`olc.c`, `olc_act.c`, `olc_save.c`, `olc_mpcode.c`, `hedit.c`) — largest remaining P2 cluster, all ❌ Not Audited at 20-30%.

If the deferred MINORs `MUSIC-005`/`MUSIC-006` need closure, both depend on broader infrastructure work (descriptor-state in broadcast helpers, per-viewer `act_format` for object substitution) and should land alongside that infrastructure rather than as standalone music fixes.
