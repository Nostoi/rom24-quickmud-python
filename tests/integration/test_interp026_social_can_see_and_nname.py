"""INTERP-026 — social target search honors can_see + N.name (via get_char_room).

ROM `do_social` (`src/interp.c:637`) resolves the social target with
`get_char_room(ch, arg)` (`src/handler.c:2194-2214`), which (a) skips occupants
the actor cannot see (`!can_see(ch, rch)`, 2207) so an unseen target yields NULL
→ "They aren't here.", and (b) honors `number_argument` `N.name` syntax
(`smile 2.guard`).

Before this fix, `perform_social` used a hand-rolled `room.people` loop with a
bare `name.lower().startswith(arg)` test — no visibility check (so
`smile <invisible>` leaked presence as "You smile at someone." instead of
"They aren't here.", the INV-027 family) and no count parsing (so `2.guard`
matched nobody). The fix migrates the victim search to the shared
`get_char_room` (now self-correct after HANDLER-001).
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


def _char(name: str, room: Room, *, npc: bool = False, short: str | None = None) -> Character:
    char = Character(
        name=name,
        short_descr=short if short is not None else f"the {name.lower()}",
        is_npc=npc,
        level=10,
        position=Position.STANDING,
        room=room,
        sex=Sex.MALE,
    )
    room.people.append(char)
    return char


def _room(vnum: int) -> Room:
    # CITY sector is never dark (room_is_dark), so can_see is gated only by the
    # invisibility check, not by global sunlight — deterministic.
    room = Room(vnum=vnum, name="Test", sector_type=int(Sector.CITY))
    room.people = []
    room.contents = []
    return room


def test_social_at_unseen_target_reports_not_here(wibble_social):
    # mirrors ROM src/handler.c:2207 — get_char_room skips !can_see targets, so
    # an invisible victim the actor can't see yields NULL → "They aren't here."
    # (no presence leak to "You wibble at someone.").
    room = _room(9601)
    alice = _char("Alice", room)
    bob = _char("Bob", room)
    bob.add_affect(AffectFlag.INVISIBLE)  # Alice has no detect-invis
    alice.messages.clear()

    result = perform_social(alice, "wibble", "bob")

    assert result == ""
    assert alice.messages == ["They aren't here."]
    assert not any("wibble" in m.lower() for m in alice.messages), alice.messages


def test_social_honors_n_dot_name_selection(wibble_social):
    # mirrors ROM src/handler.c:2201/2209 — number_argument parses "2.guard";
    # the 2nd matching occupant is the victim.
    room = _room(9602)
    alice = _char("Alice", room)
    # short_descr without "guard" so only the name field counts (avoids
    # get_char_room's name/short multi-count — tracked separately as HANDLER-002).
    guard1 = _char("Guard", room, short="a city watchman")
    guard2 = _char("Guard", room, short="a city watchman")
    for c in (guard1, guard2):
        c.messages.clear()

    result = perform_social(alice, "wibble", "2.guard")

    assert result == ""
    # The 2nd guard is the victim → receives vict_found.
    assert "Alice wibbles at you." in guard2.messages, guard2.messages
    # The 1st guard is NOT the victim → never receives vict_found.
    assert "Alice wibbles at you." not in guard1.messages, guard1.messages
