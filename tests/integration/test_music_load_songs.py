"""Integration tests for MUSIC-002 — load_songs ingests area/music.txt.

ROM C: src/music.c:160-218 (`load_songs`)
Python: mud/music/__init__.py (`load_songs`, new in this commit)
"""

from __future__ import annotations

from pathlib import Path

from mud.music import (
    MAX_GLOBAL,
    MAX_SONGS,
    channel_songs,
    load_songs,
    song_table,
)


def _snapshot_music_state() -> tuple[list, list]:
    return song_table[:], channel_songs[:]


def _restore_music_state(snapshot: tuple[list, list]) -> None:
    song_table[:], channel_songs[:] = snapshot[0], snapshot[1]


def test_load_songs_populates_song_table_from_music_txt() -> None:
    # mirrors ROM src/music.c:170-217 — read group~ / name~ / lyric lines / ~ until '#'.
    snapshot = _snapshot_music_state()
    try:
        song_table[:] = [None] * len(song_table)
        channel_songs[:] = [0] * len(channel_songs)  # dirty values, must be reset.

        load_songs(Path("area/music.txt"))

        # First song in the bundled file is U2 / "Bullet the Blue Sky".
        first = song_table[0]
        assert first is not None
        assert first.group == "U2"
        assert first.name == "Bullet the Blue Sky"
        assert first.lyrics[0] == "In the howling wind comes a stinging rain"
        assert first.lines >= 1

        # Second song is Frank Zappa / "Camarillo Brillo".
        second = song_table[1]
        assert second is not None
        assert second.group == "Frank Zappa"
        assert second.name == "Camarillo Brillo"

        # Beyond the last song slot should remain None (the data file has 16 entries < MAX_SONGS).
        assert song_table[MAX_SONGS - 1] is None
    finally:
        _restore_music_state(snapshot)


def test_load_songs_resets_channel_queue() -> None:
    # mirrors ROM src/music.c:167-168 — channel_songs[0..MAX_GLOBAL] reset to -1.
    snapshot = _snapshot_music_state()
    try:
        channel_songs[:] = [99] * len(channel_songs)

        load_songs(Path("area/music.txt"))

        assert all(value == -1 for value in channel_songs)
        assert len(channel_songs) == MAX_GLOBAL + 1
    finally:
        _restore_music_state(snapshot)


def test_load_songs_handles_missing_file() -> None:
    # mirrors ROM src/music.c:170-175 — bug() and return early when the file isn't there.
    snapshot = _snapshot_music_state()
    try:
        song_table[:] = [None] * len(song_table)
        channel_songs[:] = [99] * len(channel_songs)

        load_songs(Path("area/this_file_should_never_exist.txt"))

        # Even on a missing file, ROM still resets channel_songs first.
        assert all(value == -1 for value in channel_songs)
        # No songs loaded.
        assert all(entry is None for entry in song_table)
    finally:
        _restore_music_state(snapshot)
