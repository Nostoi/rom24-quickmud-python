"""FIGHT-014 — `_auto_sacrifice` TO_ROOM broadcast PERS parity.

ROM `src/fight.c:961-970` dispatches AUTOSAC to `do_sacrifice`,
which emits `act("$n sacrifices $p to Mota.", ch, obj, NULL, TO_ROOM)`
at `src/act_obj.c:1856`. The act() macro substitutes `$n` per-listener
through `PERS(attacker, looker)`, so an invisible attacker renders
as "someone" to room observers without `DETECT_INVIS`.

Python's `_auto_sacrifice` previously pre-rendered the broadcast
via `expand_placeholders(...)` baked into a single `_broadcast_room`
string keyed on `attacker.name`, leaking the attacker's identity.
"""

from __future__ import annotations

from mud.combat.engine import _auto_sacrifice
from mud.models.character import character_registry
from mud.models.constants import AffectFlag, ItemType, PlayerFlag, WearFlag
from mud.models.room import Room
from mud.registry import room_registry
from mud.world.world_state import create_test_character


class _MockCorpse:
    """Minimal corpse stand-in satisfying _auto_sacrifice's checks."""

    def __init__(self, name: str, *, room) -> None:
        self.short_descr = name
        self.name = name
        self.item_type = int(ItemType.CORPSE_NPC)
        self.wear_flags = int(WearFlag.TAKE)
        self.level = 5
        self.contained_items: list = []
        self.location = room
        self.prototype = None


def test_fight_014_auto_sacrifice_broadcast_uses_pers_for_invisible_attacker():
    """FIGHT-014 — AUTOSAC TO_ROOM `$n` routes through PERS.

    ROM C: src/act_obj.c:1856 (dispatched from src/fight.c:970)
        act ("$n sacrifices $p to Mota.", ch, obj, NULL, TO_ROOM);
    """
    test_room = Room(vnum=2100, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
    test_room.people = []
    test_room.contents = []
    room_registry[2100] = test_room

    try:
        attacker = create_test_character("Aliceee", 2100)
        attacker.level = 10
        attacker.act = (getattr(attacker, "act", 0) or 0) | int(PlayerFlag.AUTOSAC)
        attacker.add_affect(AffectFlag.INVISIBLE)

        observer = create_test_character("Bobbb", 2100)
        observer.level = 10
        # No DETECT_INVIS — must not see Aliceee.
        observer.messages = []

        corpse = _MockCorpse("the corpse of an orc", room=test_room)
        _auto_sacrifice(attacker, corpse)

        joined = "\n".join(observer.messages).lower()
        assert "sacrifices" in joined, (
            f"AUTOSAC broadcast not delivered: {observer.messages!r}"
        )
        assert "someone sacrifices the corpse of an orc to mota." in joined, (
            f"PERS render missing for invisible attacker: {observer.messages!r}"
        )
        assert "aliceee" not in joined, (
            f"invisible attacker name leaked: {observer.messages!r}"
        )

    finally:
        room_registry.pop(2100, None)
        character_registry.clear()
