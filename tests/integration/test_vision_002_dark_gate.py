"""VISION-002 — dark-gate same-room divergence in ``can_see_character``.

ROM ``can_see`` (``src/handler.c:2638``) masks on ``room_is_dark(ch->in_room)``
**unconditionally** — no same-room guard.  A character standing in a dark room
cannot see anyone, regardless of where the target is.  Python's dark gate
(``mud/world/vision.py``) had an extra ``observer_room is target_room``
conjunction that let an observer see cross-room targets from a dark room,
diverging from ROM.

This test module locks the fix: the dark check must fire based on the
**observer's** room alone, matching ROM.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, RoomFlag, Sector
from mud.models.room import Room
from mud.world.vision import can_see_character


def _dark_room() -> Room:
    room = Room(
        vnum=42001,
        name="Dark Cave",
        description="A pitch-black cave.",
        room_flags=int(RoomFlag.ROOM_DARK),
        sector_type=int(Sector.CITY),
    )
    room.people = []
    room.contents = []
    return room


def _lit_room() -> Room:
    room = Room(
        vnum=42002,
        name="Lit Square",
        description="A well-lit square.",
        room_flags=0,
        sector_type=int(Sector.INSIDE),
    )
    room.people = []
    room.contents = []
    return room


class TestDarkGateVision:
    """ROM handler.c:2638 — room_is_dark(ch->in_room) is unconditional."""

    def test_dark_room_cannot_see_same_room_target(self) -> None:
        # mirrors ROM src/handler.c:2638-2639 — observer in dark room, target
        # in the same dark room, no infrared ⇒ cannot see.
        dark = _dark_room()
        observer = Character(name="Watcher", level=10, room=dark, is_npc=False)
        target = Character(name="Target", level=10, room=dark, is_npc=False)

        assert can_see_character(observer, target) is False

    def test_dark_room_cannot_see_lit_room_target(self) -> None:
        # mirrors ROM src/handler.c:2638 — the dark gate fires regardless of
        # whether observer and target share a room.  An observer in a dark room
        # cannot see a target standing in a lit room either.
        dark = _dark_room()
        lit = _lit_room()
        observer = Character(name="Watcher", level=10, room=dark, is_npc=False)
        target = Character(name="Target", level=10, room=lit, is_npc=False)

        assert can_see_character(observer, target) is False

    def test_dark_room_with_infrared_sees_same_room(self) -> None:
        # mirrors ROM src/handler.c:2638-2639 — AFF_INFRARED bypasses dark.
        dark = _dark_room()
        observer = Character(name="Watcher", level=10, room=dark, is_npc=False)
        observer.add_affect(AffectFlag.INFRARED)
        target = Character(name="Target", level=10, room=dark, is_npc=False)

        assert can_see_character(observer, target) is True

    def test_dark_room_with_infrared_sees_lit_room_target(self) -> None:
        # mirrors ROM src/handler.c:2638-2639 — AFF_INFRARED bypasses the dark
        # gate entirely, so the observer can see targets in other lit rooms.
        dark = _dark_room()
        lit = _lit_room()
        observer = Character(name="Watcher", level=10, room=dark, is_npc=False)
        observer.add_affect(AffectFlag.INFRARED)
        target = Character(name="Target", level=10, room=lit, is_npc=False)

        assert can_see_character(observer, target) is True

    def test_lit_room_sees_dark_room_target(self) -> None:
        # mirrors ROM — the dark check is on the *observer's* room.  An
        # observer in a lit room can see a target in a dark room.
        dark = _dark_room()
        lit = _lit_room()
        observer = Character(name="Watcher", level=10, room=lit, is_npc=False)
        target = Character(name="Target", level=10, room=dark, is_npc=False)

        assert can_see_character(observer, target) is True
