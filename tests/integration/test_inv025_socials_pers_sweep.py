"""INV-025 — socials room broadcasts must use per-recipient PERS masking,
TO_NOTVICT victim-exclusion, and TRIG_ACT dispatch.

ROM ``check_social`` (``src/interp.c:634-685``) renders every social line through
``act()``:

  - ``act(others_no_arg, ch, NULL, victim, TO_ROOM)``     — to room except ch
  - ``act(others_auto,   ch, NULL, victim, TO_ROOM)``     — to room except ch
  - ``act(others_found,  ch, NULL, victim, TO_NOTVICT)``  — to room except ch AND victim
  - ``act(char_*,        ch, ..., TO_CHAR)``              — to ch
  - ``act(vict_found,    ch, NULL, victim, TO_VICT)``     — to victim

so ``$n``/``$N`` are rendered through ``PERS(ch/victim, to)`` per recipient — an
invisible actor masks to "someone" for a witness without detect-invis. The old
Python ``perform_social`` baked ``actor.name`` once via ``expand_placeholders`` +
``room.broadcast(exclude=char)``: no PERS masking, no TRIG_ACT, and — critically —
it delivered ``others_found`` to the victim too (``exclude=char`` is TO_ROOM, but
ROM uses TO_NOTVICT). This is the INV-025 socials class.
"""

from __future__ import annotations

import pytest

from mud.commands.socials import perform_social
from mud.models.character import Character
from mud.models.constants import AffectFlag, Position, Sector, Sex
from mud.models.room import Room
from mud.models.social import Social, register_social, social_registry


@pytest.fixture
def wibble_social():
    """A synthetic social with clean ``$n``/``$N``-only templates."""
    social = Social(
        name="wibble",
        char_no_arg="You wibble.",
        others_no_arg="$n wibbles.",
        char_found="You wibble at $N.",
        others_found="$n wibbles at $N.",
        vict_found="$n wibbles at you.",
        char_auto="You wibble at yourself.",
        others_auto="$n wibbles at $mself.",
    )
    register_social(social)
    yield social
    social_registry.pop("wibble", None)


def _char(name: str, room: Room, *, npc: bool = False) -> Character:
    char = Character(
        name=name,
        short_descr=f"the {name.lower()}",
        is_npc=npc,
        level=10,
        position=Position.STANDING,
        room=room,
        sex=Sex.MALE,
    )
    room.people.append(char)
    return char


def _room(vnum: int) -> Room:
    room = Room(vnum=vnum, name="Test", sector_type=int(Sector.CITY))
    room.people = []
    room.contents = []
    return room


def test_others_no_arg_masks_invisible_actor(wibble_social):
    # ROM act(others_no_arg, ch, NULL, victim, TO_ROOM) → PERS(ch, to).
    room = _room(9501)
    alice = _char("Alice", room)
    observer = _char("Observer", room)
    alice.add_affect(AffectFlag.INVISIBLE)
    observer.messages.clear()

    perform_social(alice, "wibble", "")

    assert any(m == "Someone wibbles." for m in observer.messages), observer.messages
    assert not any("Alice" in m for m in observer.messages), observer.messages


def test_targeted_social_excludes_victim_from_notvict(wibble_social):
    # ROM act(others_found, ch, NULL, victim, TO_NOTVICT) excludes the victim:
    # the victim receives ONLY vict_found, never the others_found broadcast.
    room = _room(9502)
    alice = _char("Alice", room)
    bob = _char("Bob", room)
    observer = _char("Observer", room)
    for c in (alice, bob, observer):
        c.messages.clear()

    perform_social(alice, "wibble", "bob")

    # Bob (victim) gets exactly one line: vict_found, not others_found.
    assert bob.messages == ["Alice wibbles at you."], bob.messages
    # Observer gets others_found naming both.
    assert any("Alice wibbles at Bob." == m for m in observer.messages), observer.messages
