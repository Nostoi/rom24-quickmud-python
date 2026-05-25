"""INV-016 BCAST-ON-POSITION-TRANSITION — enforcement test.

ROM ``src/fight.c:damage`` is the canonical damage funnel: it
applies the hp delta, calls ``update_pos`` (handler.c:1380), and
then ``act()``-broadcasts the position-change line to the room
(``src/fight.c:837-861``) — "X is mortally wounded", "X is
incapacitated", "X is stunned", "X is DEAD!!". Every damage path
in ROM funnels through ``damage()``, so the broadcast is the
natural consequence of any hp drop that crosses a threshold.

Python's damage spells in ``mud/skills/handlers.py`` bypass
``apply_damage`` (they do ``target.hit -= damage`` then
``update_pos(target)`` directly). The enforcement point is
``mud.combat.engine.apply_position_change`` — every spell site
that drops hp must call it after ``update_pos`` so the room
broadcast + to-self line fire exactly as for physical damage.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room


def _build_room_with_caster_target_observer() -> tuple[Character, Character, Character, Room]:
    room = Room(vnum=99916, name="probe room")

    caster = Character(name="caster-pc", is_npc=False)
    caster.level = 30
    caster.position = Position.STANDING
    caster.hit = 100
    caster.max_hit = 100

    target = Character(name="target-pc", is_npc=False)
    target.level = 30
    target.position = Position.STANDING
    target.hit = 1  # one INCAP-tier hit will push to -3 or worse
    target.max_hit = 100

    observer = Character(name="observer-pc", is_npc=False)
    observer.level = 30
    observer.position = Position.STANDING
    observer.hit = 100
    observer.max_hit = 100

    for ch in (caster, target, observer):
        room.add_character(ch)

    observer.messages = []
    return caster, target, observer, room


def test_spell_damage_broadcasts_death_transition_to_room() -> None:
    """When a damage spell pushes a victim past the DEAD
    threshold, the room must hear 'X is DEAD!!' per ROM
    ``src/fight.c:860``.
    """

    from mud.skills.handlers import acid_blast

    caster, target, observer, _room = _build_room_with_caster_target_observer()

    damage = acid_blast(caster, target)
    assert damage > 0, "acid_blast must do non-trivial damage"
    assert target.hit <= -11, "target hp should have crossed the DEAD threshold"
    assert target.position == Position.DEAD, (
        "update_pos should have set DEAD per src/fight.c:1399-1402"
    )

    observer_msgs = " ".join(getattr(observer, "messages", []))
    assert "is DEAD!!" in observer_msgs, (
        "ROM src/fight.c:860 act('{R$n is DEAD!!{x', victim, 0, 0, "
        "TO_ROOM) — spell damage must produce the same room "
        "broadcast as physical damage through apply_damage."
    )
