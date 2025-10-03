"""ROM song_update port with global channel queue and jukebox playback."""

from __future__ import annotations

from dataclasses import dataclass

from mud.models.character import Character

from mud.models.constants import CommFlag, ItemType
from mud.models.obj import ObjectData, object_registry
from mud.models.room import Room
from mud.net.protocol import broadcast_global, broadcast_room

MAX_SONGS = 20
MAX_LINES = 100
MAX_GLOBAL = 10


@dataclass(slots=True)
class Song:
    """Runtime representation of ROM's song_data structure."""

    group: str
    name: str
    lyrics: list[str]

    def __post_init__(self) -> None:
        # Clamp lyric payloads to ROM's MAX_LINES to avoid runaway buffers.
        if len(self.lyrics) > MAX_LINES:
            del self.lyrics[MAX_LINES:]

    @property
    def lines(self) -> int:
        return min(len(self.lyrics), MAX_LINES)


# Global song table loaded from data files; None indicates unused entries.
song_table: list[Song | None] = [None] * MAX_SONGS
# channel_songs mirrors ROM channel queue: [current_line, current_song, queue...].
channel_songs: list[int] = [-1] * (MAX_GLOBAL + 1)


def song_update() -> None:
    """Advance global and jukebox music queues following ROM cadence."""

    _update_channel_music()
    _update_jukeboxes()


def _update_channel_music() -> None:
    if channel_songs[1] >= MAX_SONGS:
        channel_songs[1] = -1

    current_song_index = channel_songs[1]
    if current_song_index < 0:
        return

    song = _get_song(current_song_index)
    if song is None:
        _advance_channel_queue()
        return

    line_index = channel_songs[0]
    if line_index >= MAX_LINES or line_index >= song.lines:
        _advance_channel_queue()
        return

    if line_index < 0:
        message = f"Music: {song.group}, {song.name}"
        channel_songs[0] = 0
    else:
        message = f"Music: '{song.lyrics[line_index]}'"
        channel_songs[0] = line_index + 1

    broadcast_global(message, channel="music", should_send=_can_hear_music)


def _advance_channel_queue() -> None:
    channel_songs[0] = -1
    for idx in range(1, MAX_GLOBAL):
        channel_songs[idx] = channel_songs[idx + 1]
    channel_songs[MAX_GLOBAL] = -1


def _update_jukeboxes() -> None:
    for obj in list(object_registry):
        if obj.item_type != int(ItemType.JUKEBOX):
            continue

        values = obj.value
        if len(values) < 5:
            values.extend([-1] * (5 - len(values)))

        current_song_index = values[1]
        if current_song_index < 0:
            continue
        if current_song_index >= MAX_SONGS:
            values[1] = -1
            continue

        song = _get_song(current_song_index)
        if song is None:
            values[1] = -1
            continue

        room = _resolve_room(obj)
        if room is None:
            continue

        if values[0] < 0:
            message = (
                f"{_object_display_name(obj)} starts playing {song.group}, {song.name}."
            )
            values[0] = 0
            broadcast_room(room, message)
            continue

        if values[0] >= MAX_LINES or values[0] >= song.lines:
            values[0] = -1
            _scroll_jukebox_queue(values)
            continue

        lyric = song.lyrics[values[0]]
        values[0] += 1
        message = f"{_object_display_name(obj)} bops: '{lyric}'"
        broadcast_room(room, message)


def _scroll_jukebox_queue(values: list[int]) -> None:
    # Shift queued songs forward (value[1]..value[4]) and clear the tail slot.
    for idx in range(1, 4):
        values[idx] = values[idx + 1]
    values[4] = -1


def _resolve_room(obj: ObjectData) -> Room | None:
    room = getattr(obj, "in_room", None)
    if room is not None:
        return room
    carrier = getattr(obj, "carried_by", None)
    if carrier is None:
        return None
    return getattr(carrier, "room", None)


def _can_hear_music(character: Character) -> bool:
    if getattr(character, "is_npc", False):
        return False
    comm_bits = int(getattr(character, "comm", 0) or 0)
    flags = CommFlag(comm_bits)
    return not bool(flags & (CommFlag.NOMUSIC | CommFlag.QUIET))


def _object_display_name(obj: ObjectData) -> str:
    return obj.short_descr or obj.name or "the jukebox"


def _get_song(index: int) -> Song | None:
    if index < 0 or index >= MAX_SONGS:
        return None
    return song_table[index]
