"""MAGIC-011 — poison food/drink caster leg is capitalized for every recipient.

ROM ``spell_poison`` food/drink branch emits
``act("$p is infused with poisonous vapors.", ch, obj, NULL, TO_ALL)``
(``src/magic.c:3946``).  ``act_new`` capitalizes ``buf[0]`` (or ``buf[2]`` behind
a ``{`` colour kludge) for **every** recipient inside the per-recipient loop
(``src/comm.c:2376-2379``) — including ``ch``.  So the caster sees
``"Loaf of bread is infused with poisonous vapors."`` with a capital ``L``.

The Python port's food caster leg emitted the short_descr verbatim
(``"loaf of bread is infused…"``) with no ``capitalize_act_line``, even though
the **weapon** caster leg right above it (``:3981``) *is* capped — the tell-tale
asymmetry of a missed site under the closed ACT-CAP-002 invariant.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ItemType, Sector
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _lit_room() -> Room:
    room = Room(
        vnum=42831,
        name="Poison Caps Lab",
        description="A well-lit room for poison-food capitalization tests.",
        room_flags=0,
        sector_type=int(Sector.INSIDE),
    )
    room.people = []
    room.contents = []
    return room


def _pc(name: str, room: Room, *, level: int = 28) -> Character:
    char = Character(name=name, level=level, room=room, is_npc=False)
    room.people.append(char)
    char.messages = []
    return char


def _food(short_descr: str = "loaf of bread") -> Object:
    proto = ObjIndex(
        vnum=4400,
        short_descr=short_descr,
        item_type=int(ItemType.FOOD),
        value=[0, 0, 0, 0, 0],
    )
    return Object(instance_id=4400, prototype=proto, value=list(proto.value), extra_flags=0)


class TestPoisonFoodCasterCaps:
    """The poison food/drink caster leg must capitalize the first letter,
    matching ROM ``act(TO_ALL)`` (ACT-CAP-002) and the sibling weapon leg."""

    def test_food_caster_leg_is_capitalized(self) -> None:
        # mirrors ROM src/magic.c:3946 + src/comm.c:2376-2379 — TO_ALL caps for ch
        room = _lit_room()
        caster = _pc("Herbalist", room)
        food = _food()

        assert skill_handlers.poison(caster, food) is True
        assert caster.messages[-1] == "Loaf of bread is infused with poisonous vapors."

    def test_food_caster_and_witness_both_capitalized(self) -> None:
        # TO_ALL — the room (witness) leg was already capped via act_to_room;
        # the caster leg must now match (ACT-CAP-002 covers every recipient).
        room = _lit_room()
        caster = _pc("Herbalist", room)
        witness = _pc("Watcher", room, level=20)
        food = _food()

        assert skill_handlers.poison(caster, food) is True
        assert caster.messages[-1] == "Loaf of bread is infused with poisonous vapors."
        assert witness.messages[-1] == "Loaf of bread is infused with poisonous vapors."
