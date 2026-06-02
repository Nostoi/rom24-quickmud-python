"""HANDLER-001 — get_char_room resolves self by name (no self-skip).

ROM `get_char_room` (`src/handler.c:2194-2214`) returns `ch` for the "self"
keyword (2203-2204) AND its `in_room->people` loop has **no self-skip** — only
`can_see`/`is_name` gates (2205-2211) — so targeting your own name finds you.
ROM's `can_see` short-circuits to TRUE for `ch == victim` (`src/handler.c`
`can_see` opens `if (ch == victim) return TRUE;`), so the self match survives
even in the dark / while blind.

Before this fix, Python's helper added `if occupant is char: continue`
(`char_find.py:51`), so `<cmd> <ownname>` could not resolve to self. The
`do_steal` caller papered over this with a substring pre-check
(`arg2_lower in own_name`) that also wrongly blocked stealing from *other*
players whose name is a substring of the thief's own name.
"""

from __future__ import annotations

import pytest

from mud.commands.thief_skills import do_steal
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, Position, Sex
from mud.registry import room_registry
from mud.world import initialize_world
from mud.world.char_find import get_char_room
from mud.world.look import look


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield


@pytest.fixture
def test_room():
    return room_registry.get(3001)


def _make_char(name: str, room) -> Character:
    char = Character(
        name=name,
        short_descr=f"{name} the tester",
        is_npc=False,
        level=10,
        position=Position.STANDING,
        room=room,
        sex=Sex.NONE,
    )
    room.add_character(char)
    character_registry.append(char)
    return char


@pytest.fixture
def alice(test_room):
    char = _make_char("Alice", test_room)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)
    if char in character_registry:
        character_registry.remove(char)


def test_get_char_room_resolves_self_by_name(alice):
    # mirrors ROM src/handler.c:2205-2211 — people loop has no self-skip, so the
    # actor's own name resolves to the actor.
    assert get_char_room(alice, "alice") is alice
    # "self" keyword still works (src/handler.c:2203-2204).
    assert get_char_room(alice, "self") is alice


def test_get_char_room_resolves_self_when_blind(alice):
    # mirrors ROM can_see (src/handler.c) — `if (ch == victim) return TRUE;` —
    # so the self match survives even when the actor cannot see anyone else.
    alice.affected_by = int(AffectFlag.BLIND)
    assert alice.has_affect(AffectFlag.BLIND)
    # A blind actor cannot see a *different* occupant...
    other = _make_char("Bob", alice.room)
    try:
        assert get_char_room(alice, "bob") is None
        # ...but still resolves their own name (can_see self-short-circuit).
        assert get_char_room(alice, "alice") is alice
    finally:
        if other in alice.room.people:
            alice.room.people.remove(other)
        if other in character_registry:
            character_registry.remove(other)


def test_look_own_name_shows_self(alice):
    # mirrors ROM do_look (src/act_info.c:1173-1177) — get_char_room returns ch
    # for the own name, then show_char_to_char_1(ch, ch) shows your own desc.
    by_self = look(alice, "self")
    by_name = look(alice, "alice")
    assert by_name == by_self
    assert "isn't here" not in by_name.lower()
    assert "don't see" not in by_name.lower()


def test_steal_other_not_blocked_by_own_name_substring(test_room):
    # Regression for the harmful do_steal pre-check (`arg2_lower in own_name`):
    # a thief named "Bobby" stealing from "Bob" must NOT be rejected as self.
    # ROM has no such pre-check; it relies on get_char_room + the victim == ch
    # guard (src/act_obj.c:2185-2189). Victim is added first so get_char_room's
    # in-room scan resolves "bob" to Bob, not the thief.
    victim = _make_char("Bob", test_room)
    thief = _make_char("Bobby", test_room)
    try:
        result = do_steal(thief, "coin bob")
        # Before the fix the pre-check returned "That's pointless." here.
        assert result != "That's pointless.\n"
    finally:
        for c in (victim, thief):
            if c in test_room.people:
                test_room.people.remove(c)
            if c in character_registry:
                character_registry.remove(c)
