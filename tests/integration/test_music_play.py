"""Integration tests for MUSIC-001 — `do_play` song queueing.

ROM C: src/music.c:220-354 (`do_play`)
Python: mud/commands/player_info.py (`do_play`)

These tests exercise the side-effects ROM's `do_play` produces beyond the
"Coming right up." reply: queueing into `juke->value[1..4]` for local plays,
queueing into `channel_songs[1..MAX_GLOBAL]` for `play loud`, the
`"The jukebox is full up right now."` rejection when the tail slot is taken,
and the `"That song isn't available."` rejection when no song matches by
`str_prefix`.
"""

from __future__ import annotations

import pytest

from mud.commands.player_info import do_play
from mud.models.character import Character
from mud.models.constants import ItemType
from mud.models.obj import ObjectData, object_registry
from mud.models.room import Room
from mud.music import MAX_GLOBAL, Song, channel_songs, song_table


@pytest.fixture
def music_world():
    """Snapshot/restore song_table, channel_songs, and object_registry."""
    saved_songs = song_table[:]
    saved_channels = channel_songs[:]
    saved_objects = list(object_registry)

    song_table[:] = [None] * len(song_table)
    channel_songs[:] = [-1] * len(channel_songs)
    object_registry.clear()

    # mirrors ROM src/music.c song_table — entries indexed by `do_play` via str_prefix
    song_table[0] = Song(group="The Band", name="Anthem", lyrics=["Line one"])
    song_table[1] = Song(group="The Band", name="Ballad of the Blue", lyrics=["intro", "verse"])
    song_table[2] = Song(group="Other", name="Camarillo Brillo", lyrics=["la la"])

    yield

    song_table[:] = saved_songs
    channel_songs[:] = saved_channels
    object_registry[:] = saved_objects


def _build_room_with_jukebox(jukebox_values: list[int] | None = None) -> tuple[Character, ObjectData]:
    room = Room(vnum=4242, name="Music Hall")
    char = Character(name="Patron", is_npc=False)
    room.add_character(char)
    juke = ObjectData(
        item_type=int(ItemType.JUKEBOX),
        short_descr="The jukebox",
        value=list(jukebox_values) if jukebox_values is not None else [-1, -1, -1, -1, -1],
    )
    juke.in_room = room
    room.contents.append(juke)
    object_registry.append(juke)
    return char, juke


def test_do_play_queues_song_into_local_jukebox(music_world) -> None:
    # mirrors ROM src/music.c:344-352 — first free juke->value[1..4] slot gets the song id.
    char, juke = _build_room_with_jukebox()

    reply = do_play(char, "anthem")

    assert reply == "Coming right up."
    assert juke.value[1] == 0  # song index for "Anthem"
    # mirrors ROM src/music.c:348-349 — filling slot 1 also resets value[0] = -1
    assert juke.value[0] == -1


def test_do_play_loud_queues_song_globally(music_world) -> None:
    # mirrors ROM src/music.c:332-341 — loud play queues into channel_songs[1..MAX_GLOBAL].
    char, _ = _build_room_with_jukebox()

    reply = do_play(char, "loud ballad")

    assert reply == "Coming right up."
    assert channel_songs[1] == 1  # song index for "Ballad of the Blue"
    # mirrors ROM src/music.c:337-338 — filling channel slot 1 resets channel_songs[0] = -1
    assert channel_songs[0] == -1


def test_do_play_rejects_when_jukebox_queue_full(music_world) -> None:
    # mirrors ROM src/music.c:306-311 — juke->value[4] > -1 → "The jukebox is full up right now."
    char, juke = _build_room_with_jukebox(jukebox_values=[0, 0, 1, 2, 0])

    reply = do_play(char, "anthem")

    assert reply == "The jukebox is full up right now."
    # The queue must be untouched on rejection.
    assert juke.value == [0, 0, 1, 2, 0]


def test_do_play_loud_rejects_when_global_queue_full(music_world) -> None:
    # mirrors ROM src/music.c:306-311 — channel_songs[MAX_GLOBAL] > -1 means full.
    channel_songs[MAX_GLOBAL] = 0
    char, _ = _build_room_with_jukebox()

    reply = do_play(char, "loud anthem")

    assert reply == "The jukebox is full up right now."
    assert channel_songs[1] == -1  # nothing got queued at the head


def test_do_play_rejects_unknown_song(music_world) -> None:
    # mirrors ROM src/music.c:313-328 — no str_prefix match → "That song isn't available."
    char, juke = _build_room_with_jukebox()

    reply = do_play(char, "nonexistent")

    assert reply == "That song isn't available."
    assert juke.value == [-1, -1, -1, -1, -1]


def test_do_play_loud_with_empty_song_argument(music_world) -> None:
    # mirrors ROM src/music.c:300-304 — "play loud" with no song name → "Play what?"
    char, _ = _build_room_with_jukebox()

    reply = do_play(char, "loud")

    assert reply == "Play what?"


def test_do_play_matches_song_by_prefix(music_world) -> None:
    # mirrors ROM src/music.c:320 — str_prefix(argument, song_table[i].name).
    char, juke = _build_room_with_jukebox()

    reply = do_play(char, "ball")

    assert reply == "Coming right up."
    assert juke.value[1] == 1  # "Ballad of the Blue"
