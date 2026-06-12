"""LOOK-005 / LOOK-006 — PLR_HOLYLIGHT bypasses for blindness and darkness.

ROM gives immortals with PLR_HOLYLIGHT X-ray senses:

- ``check_blind`` (src/act_info.c:542-556) returns TRUE for a non-NPC with
  PLR_HOLYLIGHT set *before* the AFF_BLIND test, so a blind holylight
  immortal still sees.  ``do_look`` (src/act_info.c:1065) and ``do_exits``
  (src/act_info.c:1404) both gate on ``check_blind``.
- ``do_look``'s dark-room gate (src/act_info.c:1068-1069) is
  ``!IS_NPC(ch) && !IS_SET(ch->act, PLR_HOLYLIGHT) && room_is_dark(...)`` —
  a holylight character sees the full room where mortals get
  "It is pitch black ...".

The PLR_HOLYLIGHT check is guarded by ``!IS_NPC`` in ROM because ``ch->act``
is a union namespace: PLR_* bits on PCs, ACT_* bits on NPCs.
"""

from __future__ import annotations

from mud.commands.inspection import do_exits, do_look
from mud.models.character import Character
from mud.models.constants import AffectFlag, PlayerFlag, Position, RoomFlag, Sector
from mud.models.room import Room


def _lit_room() -> Room:
    room = Room(vnum=3001)
    room.name = "Midgaard Temple"
    room.description = "You are in the temple."
    room.sector_type = int(Sector.INSIDE)
    room.room_flags = 0
    room.light = 1
    room.people = []
    room.contents = []
    room.exits = [None, None, None, None, None, None]
    return room


def _dark_room() -> Room:
    room = Room(vnum=3002)
    room.name = "Dark Cave"
    room.description = "A pitch-black cave."
    room.sector_type = int(Sector.FOREST)
    room.room_flags = int(RoomFlag.ROOM_DARK)
    room.light = 0
    room.people = []
    room.contents = []
    room.exits = [None, None, None, None, None, None]
    return room


def _pc(room: Room, *, act: int = 0) -> Character:
    char = Character()
    char.name = "Watcher"
    char.level = 1
    char.trust = 0
    char.is_npc = False
    char.position = int(Position.STANDING)
    char.act = act
    char.comm = 0
    char.room = room
    room.people.append(char)
    return char


class TestCheckBlindHolylight:
    """LOOK-005 — check_blind PLR_HOLYLIGHT bypass (src/act_info.c:544-545)."""

    def test_blind_holylight_pc_can_look(self) -> None:
        # mirrors ROM src/act_info.c:544-545 — !IS_NPC && PLR_HOLYLIGHT returns
        # TRUE from check_blind before AFF_BLIND is consulted.
        room = _lit_room()
        char = _pc(room, act=int(PlayerFlag.HOLYLIGHT))
        char.add_affect(AffectFlag.BLIND)

        output = do_look(char, "")

        assert "You can't see a thing!" not in output
        assert "Midgaard Temple" in output

    def test_blind_holylight_pc_sees_exits(self) -> None:
        # mirrors ROM src/act_info.c:1404 — do_exits gates on check_blind,
        # which the PLR_HOLYLIGHT bypass satisfies even while AFF_BLIND.
        room = _lit_room()
        char = _pc(room, act=int(PlayerFlag.HOLYLIGHT))
        char.add_affect(AffectFlag.BLIND)

        output = do_exits(char, "")

        assert "You can't see a thing!" not in output
        assert output.startswith("Obvious exits")

    def test_blind_pc_without_holylight_cannot_look(self) -> None:
        # regression guard — mortals (no PLR_HOLYLIGHT) stay blocked by
        # AFF_BLIND (src/act_info.c:547-551).
        room = _lit_room()
        char = _pc(room)
        char.add_affect(AffectFlag.BLIND)

        assert do_look(char, "") == "You can't see a thing!"
        assert do_exits(char, "") == "You can't see a thing!"

    def test_blind_npc_is_not_rescued_by_plr_bit(self) -> None:
        # mirrors ROM's !IS_NPC guard — ch->act on NPCs holds ACT_* bits, so
        # the same integer value must NOT trigger the holylight bypass.
        room = _lit_room()
        char = _pc(room, act=int(PlayerFlag.HOLYLIGHT))
        char.is_npc = True
        char.add_affect(AffectFlag.BLIND)

        assert do_look(char, "") == "You can't see a thing!"
