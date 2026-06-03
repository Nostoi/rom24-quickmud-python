"""FINDING-022 — `look in <container>` contents-line indent parity with ROM.

ROM ``src/act_info.c:130-243`` ``show_list_to_char`` renders container
contents differently depending on the viewer's COMM_COMBINE flag and
whether the viewer is an NPC:

- NPC / COMM_COMBINE: each unique short_descr is printed once with a
  coalesced count.  Single items get 5-space padding (``     ``) to
  align with the ``(N)`` prefix; duplicates show ``(N)`` (right-justified
  in a 2-char field, then a trailing space).
- PC without COMM_COMBINE: items are listed one per line with **no**
  leading indent or padding at all.

The Python port had a 2-space indent (``f"  {item_name}"``) which matched
neither the no-indent PC path nor the 5-space COMBINE path.  This test
pins the correct ROM behaviour for each viewer type.
"""

from __future__ import annotations

from mud.commands.dispatcher import process_command
from mud.models.character import Character
from mud.models.constants import CommFlag, ItemType, Position
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.utils.act import show_list_to_char


def _make_pc_in_room(comm: int = 0) -> tuple[Character, Room]:
    room = Room(vnum=9501, name="test-room")
    pc = Character(name="testpc", is_npc=False, level=10, position=Position.STANDING)
    pc.comm = comm
    room.add_character(pc)
    return pc, room


def _make_npc_in_room() -> tuple[Character, Room]:
    room = Room(vnum=9502, name="test-room")
    npc = Character(name="testmob", is_npc=True, level=5, position=Position.STANDING)
    room.add_character(npc)
    return npc, room


def _make_container() -> Object:
    proto = ObjIndex(
        vnum=8600,
        name="bag",
        short_descr="a bag",
        item_type=int(ItemType.CONTAINER),
    )
    obj = Object(instance_id=0, prototype=proto)
    obj.short_descr = "a bag"
    obj.value = [0, 0, 0, 0, 0]
    return obj


def _make_item(vnum: int, name: str) -> Object:
    proto = ObjIndex(vnum=vnum, name=name, short_descr=f"a {name}")
    obj = Object(instance_id=0, prototype=proto)
    obj.short_descr = f"a {name}"
    return obj


class TestShowListToChar:
    """Direct-unit tests for show_list_to_char ROM behaviour."""

    def test_non_combine_pc_no_indent_on_contents(self):
        """FINDING-022: PC without COMM_COMBINE sees no indent on contents lines."""
        pc, _ = _make_pc_in_room(comm=0)
        sword = _make_item(8601, "sword")
        shield = _make_item(8602, "shield")

        result = show_list_to_char([sword, shield], pc, f_short=True, f_show_nothing=True)
        assert result == "a sword\na shield\n", f"non-COMBINE PC should see no leading indent, got: {result!r}"

    def test_combine_pc_5space_padding_on_singles(self):
        """COMM_COMBINE PC sees 5-space padding on single (non-duplicate) items."""
        pc, _ = _make_pc_in_room(comm=int(CommFlag.COMBINE))
        sword = _make_item(8601, "sword")
        shield = _make_item(8602, "shield")

        result = show_list_to_char([sword, shield], pc, f_short=True, f_show_nothing=True)
        assert result == "     a sword\n     a shield\n", f"COMBINE PC should see 5-space padding, got: {result!r}"

    def test_combine_pc_count_prefix_on_duplicates(self):
        """COMM_COMBINE PC sees (N) count prefix for duplicate items."""
        pc, _ = _make_pc_in_room(comm=int(CommFlag.COMBINE))
        sword1 = _make_item(8601, "sword")
        sword2 = _make_item(8601, "sword")
        sword2.short_descr = "a sword"
        shield = _make_item(8602, "shield")

        result = show_list_to_char([sword1, sword2, shield], pc, f_short=True, f_show_nothing=True)
        assert result == "( 2) a sword\n     a shield\n", (
            f"COMBINE PC should see (2) count for duplicates, got: {result!r}"
        )

    def test_npc_gets_combine_format(self):
        """NPC automatically gets COMBINE-style output (5-space + counts)."""
        npc, _ = _make_npc_in_room()
        sword = _make_item(8601, "sword")

        result = show_list_to_char([sword], npc, f_short=True, f_show_nothing=True)
        assert result == "     a sword\n", f"NPC should see 5-space padded output, got: {result!r}"

    def test_empty_container_nothing_no_combine(self):
        """Empty container: 'Nothing.' with no indent for non-COMBINE PC."""
        pc, _ = _make_pc_in_room(comm=0)
        result = show_list_to_char([], pc, f_short=True, f_show_nothing=True)
        assert result == "Nothing.\n", f"non-COMBINE PC should see plain 'Nothing.', got: {result!r}"

    def test_empty_container_nothing_with_combine(self):
        """Empty container: '     Nothing.' (5-space padded) for COMBINE/NPC."""
        npc, _ = _make_npc_in_room()
        result = show_list_to_char([], npc, f_short=True, f_show_nothing=True)
        assert result == "     Nothing.\n", f"NPC/COMBINE should see 5-space padded 'Nothing.', got: {result!r}"

    def test_empty_container_f_show_nothing_false(self):
        """Empty container with fShowNothing=FALSE produces nothing."""
        pc, _ = _make_pc_in_room(comm=0)
        result = show_list_to_char([], pc, f_short=True, f_show_nothing=False)
        assert result == "", f"fShowNothing=FALSE should produce empty string, got: {result!r}"


class TestLookInContainer:
    """End-to-end tests for `look in <container>` command output."""

    def test_look_in_no_combine_pc_no_indent(self):
        """FINDING-022: PC without COMM_COMBINE sees container contents with no indent."""
        pc, room = _make_pc_in_room(comm=0)
        bag = _make_container()
        sword = _make_item(8601, "sword")
        shield = _make_item(8602, "shield")
        bag.contained_items.append(sword)
        sword.in_obj = bag
        bag.contained_items.append(shield)
        shield.in_obj = bag
        room.add_object(bag)

        result = process_command(pc, "look in bag")

        assert "A bag holds:" in result
        lines = result.split("\n")
        content_lines = [line for line in lines if line not in ("A bag holds:", "")]
        for line in content_lines:
            assert not line.startswith("  "), f"no-COMBINE PC should see no 2-space indent, got: {line!r}"
            assert not line.startswith("     "), f"no-COMBINE PC should see no 5-space padding, got: {line!r}"

    def test_look_in_combine_pc_5space_padding(self):
        """FINDING-022: PC with COMM_COMBINE sees 5-space padding."""
        pc, room = _make_pc_in_room(comm=int(CommFlag.COMBINE))
        bag = _make_container()
        sword = _make_item(8601, "sword")
        bag.contained_items.append(sword)
        sword.in_obj = bag
        room.add_object(bag)

        result = process_command(pc, "look in bag")

        assert "A bag holds:" in result
        assert "     a sword" in result, f"COMBINE PC should see 5-space padded contents, got: {result!r}"

    def test_look_in_empty_no_combine(self):
        """FINDING-022: empty container shows 'Nothing.' with no indent for non-COMBINE."""
        pc, room = _make_pc_in_room(comm=0)
        bag = _make_container()
        room.add_object(bag)

        result = process_command(pc, "look in bag")

        assert "A bag holds:" in result
        assert "Nothing." in result
        assert "     Nothing." not in result

    def test_look_in_empty_combine(self):
        """FINDING-022: empty container shows '     Nothing.' with 5-space pad for COMBINE."""
        pc, room = _make_pc_in_room(comm=int(CommFlag.COMBINE))
        bag = _make_container()
        room.add_object(bag)

        result = process_command(pc, "look in bag")

        assert "A bag holds:" in result
        assert "     Nothing." in result
