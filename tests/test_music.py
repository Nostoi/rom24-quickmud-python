from __future__ import annotations

from mud.models.character import Character, character_registry
from mud.models.constants import CommFlag, ItemType
from mud.models.obj import ObjectData, object_registry
from mud.models.room import Room
from mud.music import Song, channel_songs, song_table, song_update


def test_song_update_broadcasts_global() -> None:
    original_characters = list(character_registry)
    original_songs = song_table[:]
    original_channels = channel_songs[:]
    try:
        character_registry.clear()
        song_table[:] = [None] * len(song_table)
        channel_songs[:] = [-1] * len(channel_songs)

        player = Character(name="Player", is_npc=False, comm=0)
        silent = Character(name="Silent", is_npc=False, comm=int(CommFlag.NOMUSIC))
        quiet = Character(name="Quiet", is_npc=False, comm=int(CommFlag.QUIET))
        mob = Character(name="Mob", is_npc=True)

        for character in (player, silent, quiet, mob):
            character.messages.clear()
            character_registry.append(character)

        song_table[0] = Song(group="The Band", name="Anthem", lyrics=["Line one", "Line two"])
        channel_songs[0] = -1
        channel_songs[1] = 0
        for idx in range(2, len(channel_songs)):
            channel_songs[idx] = -1

        song_update()
        assert player.messages[-1] == "Music: The Band, Anthem"
        assert silent.messages == []
        assert quiet.messages == []
        assert mob.messages == []

        song_update()
        assert player.messages[-1] == "Music: 'Line one'"
        assert len(player.messages) == 2
    finally:
        character_registry[:] = original_characters
        song_table[:] = original_songs
        channel_songs[:] = original_channels


def test_jukebox_cycles_queue() -> None:
    original_characters = list(character_registry)
    original_objects = list(object_registry)
    original_songs = song_table[:]
    original_channels = channel_songs[:]
    try:
        character_registry.clear()
        object_registry.clear()
        song_table[:] = [None] * len(song_table)
        channel_songs[:] = [-1] * len(channel_songs)

        room = Room(vnum=42, name="Music Hall")
        listener = Character(name="Listener", is_npc=False)
        listener.messages.clear()
        room.add_character(listener)
        character_registry.append(listener)

        jukebox = ObjectData(
            item_type=int(ItemType.JUKEBOX),
            short_descr="The jukebox",
            value=[-1, 0, 1, -1, -1],
        )
        jukebox.in_room = room
        room.contents.append(jukebox)
        object_registry.append(jukebox)

        song_table[0] = Song(group="Band", name="Song A", lyrics=["first line"])
        song_table[1] = Song(group="Band", name="Song B", lyrics=["intro", "verse"])

        song_update()
        assert listener.messages[-1] == "The jukebox starts playing Band, Song A."

        song_update()
        assert listener.messages[-1] == "The jukebox bops: 'first line'"

        song_update()
        assert jukebox.value[1] == 1

        song_update()
        assert listener.messages[-1] == "The jukebox starts playing Band, Song B."
    finally:
        character_registry[:] = original_characters
        object_registry[:] = original_objects
        song_table[:] = original_songs
        channel_songs[:] = original_channels
