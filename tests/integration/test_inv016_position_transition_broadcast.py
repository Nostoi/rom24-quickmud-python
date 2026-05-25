"""INV-016 BCAST-ON-POSITION-TRANSITION — known gap, documenting test.

ROM ``src/fight.c:damage`` is the canonical damage funnel: it
applies the hp delta, calls ``update_pos`` (handler.c:1380), and
then ``act()``-broadcasts the position-change line to the room
(``src/fight.c:837-861``) — "X is mortally wounded", "X is
incapacitated", "X is stunned", "X is DEAD!!". Every damage path
in ROM — combat hits, spells, breath weapons, traps — funnels
through ``damage()``, so the broadcast is the natural consequence
of any hp drop that crosses a threshold.

The Python port has two damage code-paths:

1. ``mud/combat/engine.py:apply_damage`` (the proper funnel) calls
   ``_position_change_message`` after ``update_pos``, which
   broadcasts the room line via ``_broadcast_pos_change`` —
   matches ROM exactly.
2. ``mud/skills/handlers.py`` damage spells (acid_blast,
   acid_breath, fire_breath, lightning_bolt, magic_missile,
   harm, etc., ~18 sites) do ``target.hit -= damage`` then call
   ``update_pos(target)`` directly — they bypass ``apply_damage``,
   so the position-transition broadcast NEVER fires for spell
   damage. ROM does broadcast in this case (its spells go through
   ``damage()``).

Filed as INV-016. Status ❌ BROKEN. This test documents the
contract so we don't forget it; closing it is a separate cluster
because ~18 spell sites need rerouting.

The test below is **expected to fail** (``pytest.mark.xfail``
strict=True) — when INV-016 is closed, the xfail flips and we
remove the marker.
"""

from __future__ import annotations

import pytest

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


@pytest.mark.xfail(
    reason=(
        "INV-016 BCAST-ON-POSITION-TRANSITION — known gap. "
        "Skill damage paths in mud/skills/handlers.py bypass "
        "apply_damage and call update_pos directly, so the "
        "'X is incapacitated' / 'X is mortally wounded' / "
        "'X is DEAD!!' room broadcast (src/fight.c:837-861) "
        "never fires for spell-induced position transitions. "
        "Closing this is a separate cluster (~18 spell sites + "
        "harm, breath weapons, traps). Flip xfail → pass when "
        "the routing fix lands."
    ),
    strict=True,
)
def test_spell_damage_broadcasts_incap_transition_to_room() -> None:
    """When a damage spell pushes a victim across the INCAP
    threshold, the room must hear 'X is incapacitated and will
    slowly die, if not aided.' per ROM ``src/fight.c:845-846``.
    """

    from mud.skills.handlers import acid_blast

    caster, target, observer, _room = _build_room_with_caster_target_observer()

    damage = acid_blast(caster, target)
    assert damage > 0, "acid_blast must do non-trivial damage"
    assert target.hit <= -3, "target hp should have crossed the INCAP threshold"
    assert target.position == Position.INCAP, (
        "update_pos should have set INCAP per src/fight.c:1403-1404"
    )

    observer_msgs = " ".join(getattr(observer, "messages", []))
    assert "incapacitated and will slowly die" in observer_msgs, (
        "ROM src/fight.c:845-846 act('$n is incapacitated and will "
        "slowly die, if not aided.', victim, NULL, NULL, TO_ROOM) — "
        "spell damage must produce the same room broadcast as "
        "physical damage through apply_damage."
    )
