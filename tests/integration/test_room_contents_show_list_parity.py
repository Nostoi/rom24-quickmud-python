"""Room-contents look() path through show_list_to_char — ROM parity.

ROM src/act_info.c:1106 calls
    show_list_to_char(ch->in_room->contents, ch, FALSE, FALSE)
for the room-contents display. This means:
- f_short=FALSE: objects listed by their ground description (obj->description)
- f_show_nothing=FALSE: no "Nothing." line when no visible objects
- can_see_obj visibility filter applies
- COMBINE/NPC viewers get duplicate-coalesced output with (N) counts or 5-space pad
- Non-COMBINE PC viewers get plain one-per-line, no indent
- Aura prefixes (Invis, Red Aura, Glowing, Humming, etc.) prepend visible objects
"""

from __future__ import annotations

from mud.commands.inspection import do_look
from mud.models.character import Character
from mud.models.constants import (
    AffectFlag,
    ExtraFlag,
    ItemType,
    Position,
    RoomFlag,
    Sector,
    WearLocation,
)
from mud.models.room import Room


def _basic_room() -> Room:
    room = Room(vnum=3001)
    room.name = "Test Room"
    room.description = "A plain room."
    room.sector_type = int(Sector.INSIDE)
    room.room_flags = 0
    room.light = 1
    room.people = []
    room.contents = []
    room.exits = [None, None, None, None, None, None]
    return room


def _basic_char(**overrides) -> Character:
    char = Character()
    char.name = "Tester"
    char.level = 1
    char.trust = 0
    char.is_npc = False
    char.position = int(Position.STANDING)
    char.act = 0
    char.comm = 0
    char.affected_by = 0
    for k, v in overrides.items():
        setattr(char, k, v)
    return char


class Obj:
    """Duck-typed object for show_list_to_char / can_see_object."""

    def __init__(self, **kw):
        self.name = kw.get("name", "sword")
        self.short_descr = kw.get("short_descr", "a sword")
        self.description = kw.get("description", "A sword lies here.")
        self.item_type = kw.get("item_type", int(ItemType.WEAPON))
        self.wear_loc = kw.get("wear_loc", int(WearLocation.NONE))
        self.extra_flags = kw.get("extra_flags", 0)
        self.value = kw.get("value", [0, 0, 0, 0, 0])
        self.in_room = kw.get("in_room", None)


class TestRoomContentsShowListParity:
    """Room look uses show_list_to_char(f_short=False, f_show_nothing=False)."""

    def test_ground_objects_shown_by_description(self):
        """ROM: f_short=False -> obj->description, not short_descr."""
        room = _basic_room()
        obj = Obj(description="A wooden sword lies here.", short_descr="a sword", in_room=room)
        room.contents = [obj]
        char = _basic_char(room=room)
        room.people = [char]

        out = do_look(char, "")

        assert "A wooden sword lies here." in out
        assert "a sword" not in out

    def test_invisible_object_hidden_from_non_detect(self):
        """ROM: can_see_obj(ch, obj) hides ITEM_INVIS without DETECT_INVIS."""
        room = _basic_room()
        obj = Obj(description="An invisible sword lies here.", extra_flags=int(ExtraFlag.INVIS), in_room=room)
        room.contents = [obj]
        char = _basic_char(room=room)
        room.people = [char]

        out = do_look(char, "")

        assert "An invisible sword lies here." not in out

    def test_invisible_object_visible_with_detect_invis(self):
        """ROM: DETECT_INVIS reveals ITEM_INVIS, prefixed with (Invis)."""
        room = _basic_room()
        obj = Obj(description="A sword lies here.", extra_flags=int(ExtraFlag.INVIS), in_room=room)
        room.contents = [obj]
        char = _basic_char(affected_by=int(AffectFlag.DETECT_INVIS), room=room)
        room.people = [char]

        out = do_look(char, "")

        assert "(Invis) A sword lies here." in out

    def test_empty_room_shows_no_nothing_line(self):
        """ROM: f_show_nothing=FALSE -> no 'Nothing.' when room has no visible objects."""
        room = _basic_room()
        char = _basic_char(room=room)
        room.people = [char]

        out = do_look(char, "")

        assert "Nothing." not in out

    def test_glowing_object_gets_prefix(self):
        """ROM: format_obj_to_char prepends '(Glowing) ' for ITEM_GLOW."""
        room = _basic_room()
        obj = Obj(description="A glowing sword lies here.", extra_flags=int(ExtraFlag.GLOW), in_room=room)
        room.contents = [obj]
        char = _basic_char(room=room)
        room.people = [char]

        out = do_look(char, "")

        assert "(Glowing) A glowing sword lies here." in out

    def test_object_with_no_description_hidden(self):
        """ROM: format_obj_to_char(f_short=False) returns '' when description is empty."""
        room = _basic_room()
        obj = Obj(description=None, in_room=room)
        room.contents = [obj]
        char = _basic_char(room=room)
        room.people = [char]

        out = do_look(char, "")

        for line in out.split("\n"):
            if line.strip() and line.strip() not in ("Test Room", "A plain room."):
                assert not line.strip().startswith("None"), f"Unexpected line: '{line}'"

    def test_combine_viewer_sees_count_prefix(self):
        """ROM: NPC/COMBINE sees coalesced duplicates with (N) count."""
        room = _basic_room()
        sword1 = Obj(description="A sword lies here.", short_descr="a sword", in_room=room)
        sword2 = Obj(description="A sword lies here.", short_descr="a sword", in_room=room)
        room.contents = [sword1, sword2]

        npc = _basic_char(is_npc=True, comm=0, room=room)
        room.people = [npc]

        out = do_look(npc, "")

        assert "( 2)" in out

    def test_combine_viewer_sees_5space_for_singles(self):
        """ROM: NPC/COMBINE sees '     ' (5-space pad) for unique items."""
        room = _basic_room()
        obj = Obj(description="A sword lies here.", in_room=room)
        room.contents = [obj]

        npc = _basic_char(is_npc=True, room=room)
        room.people = [npc]

        out = do_look(npc, "")
        for line in out.split("\n"):
            if "A sword lies here." in line:
                assert line.startswith("     "), f"Expected 5-space pad, got: '{line}'"
                break
        else:
            assert False, "Expected sword description in output"

    def test_non_combine_pc_no_indent(self):
        """ROM: non-COMBINE PC sees room objects with no padding/indent."""
        room = _basic_room()
        obj = Obj(description="A sword lies here.", in_room=room)
        room.contents = [obj]
        char = _basic_char(room=room)
        room.people = [char]

        out = do_look(char, "")
        for line in out.split("\n"):
            if "A sword lies here." in line:
                assert line == "A sword lies here.", f"Expected no indent, got: '{line}'"
                break
        else:
            assert False, "Expected sword description in output"

    def test_dark_room_hides_objects(self):
        """ROM: dark rooms skip show_list_to_char entirely."""
        room = _basic_room()
        room.light = 0
        room.room_flags = int(RoomFlag.ROOM_DARK)
        obj = Obj(description="A sword lies here.", in_room=room)
        room.contents = [obj]
        char = _basic_char(affected_by=int(AffectFlag.INFRARED), room=room)
        room.people = [char]

        out = do_look(char, "")

        assert "A sword lies here." not in out
        assert "It is pitch black" in out
