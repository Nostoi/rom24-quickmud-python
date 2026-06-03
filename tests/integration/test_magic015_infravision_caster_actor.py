"""MAGIC-015 — infravision room line uses the CASTER as the ``$n`` actor.

ROM ``spell_infravision`` (src/magic.c:3598) emits
``act("$n's eyes glow red.", ch, NULL, NULL, TO_ROOM)`` — the actor is ``ch``
(the caster), and ``TO_ROOM`` excludes only ``ch``. So on a cross-cast
(``caster != victim``, valid for ``TAR_CHAR_DEFENSIVE``) the whole room —
including the victim — sees the *caster's* name where the Python port
previously rendered the *victim's* (it passed ``target`` as the actor and
``exclude=target``). Self-cast (``caster == victim``) is identical either way.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Sector
from mud.models.room import Room
from mud.skills.handlers import infravision


def _lit_room() -> Room:
    room = Room(
        vnum=42715,
        name="Infravision Lab",
        description="A well-lit room.",
        room_flags=0,
        sector_type=int(Sector.INSIDE),
    )
    room.people = []
    return room


def _pc(name: str, room: Room) -> Character:
    char = Character(name=name, level=30, room=room, is_npc=False)
    room.people.append(char)
    return char


def test_cross_cast_room_line_shows_caster_name() -> None:
    room = _lit_room()
    caster = _pc("Castor", room)
    victim = _pc("Vimes", room)
    onlooker = _pc("Bystan", room)

    assert infravision(caster, victim) is True

    onlooker_msgs = [str(m) for m in onlooker.messages]
    # ROM: the room sees the CASTER's name, not the victim's.
    assert any("Castor's eyes glow red" in m for m in onlooker_msgs), onlooker_msgs
    assert not any("Vimes's eyes glow red" in m for m in onlooker_msgs), onlooker_msgs

    # The victim receives the personal line...
    victim_msgs = [str(m) for m in victim.messages]
    assert any("Your eyes glow red." in m for m in victim_msgs), victim_msgs
    # ...and, because TO_ROOM excludes only the caster, the victim also sees the
    # caster's room line (ROM includes the victim in the broadcast).
    assert any("Castor's eyes glow red" in m for m in victim_msgs), victim_msgs


def test_self_cast_room_line_shows_caster_name() -> None:
    room = _lit_room()
    caster = _pc("Castor", room)
    onlooker = _pc("Bystan", room)

    assert infravision(caster) is True

    onlooker_msgs = [str(m) for m in onlooker.messages]
    assert any("Castor's eyes glow red" in m for m in onlooker_msgs), onlooker_msgs
