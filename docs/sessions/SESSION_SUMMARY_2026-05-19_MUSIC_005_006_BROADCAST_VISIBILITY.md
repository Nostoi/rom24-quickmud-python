# Session Summary — 2026-05-19 — `MUSIC-005` / `MUSIC-006` broadcast visibility parity

## What landed

Closed the last two `music.c` parity gaps.

- `MUSIC-005`: global channel music now mirrors ROM `src/music.c:88-97` by iterating the lightweight ROM-style `descriptor_list`, requiring `CON_PLAYING`, checking `COMM_NOMUSIC` / `COMM_QUIET` on `descriptor.original` when switched, and delivering the line through the active descriptor character.
- `MUSIC-006`: jukebox room output now mirrors ROM `src/music.c:122-154` by resolving `$p` per viewer. Recipients who cannot see the jukebox now get the ROM-style `something` fallback instead of the jukebox short description.

## Files changed

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/music/__init__.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/utils/act.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_music_play.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/MUSIC_C_AUDIT.md`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_STATUS.md`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/CHANGELOG.md`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/pyproject.toml`

## Tests

- `./venv/bin/python -m pytest -q tests/integration/test_music_play.py -k 'global_music_respects_playing_descriptors or jukebox_visibility_uses_per_viewer_object_rendering'` → `2 passed`
- `./venv/bin/python -m pytest -q tests/integration/test_music_play.py tests/integration/test_music_load_songs.py tests/test_music.py` → `19 passed`
- `./venv/bin/ruff check mud/music/__init__.py mud/utils/act.py tests/integration/test_music_play.py tests/test_music.py` → clean
- `./venv/bin/python -m pytest -q --maxfail=1` → `4555 passed, 4 skipped`

## Result

- `music.c` now records **100%** closure in the canonical parity tracker.
- Remaining work is no longer in the `music.c` surface; the next target should come from the remaining deferred/user-visible parity slices after full-suite recertification.
