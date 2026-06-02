"""INTERP-025 — self-targeted socials reach the char_auto/others_auto branch.

ROM `do_social` (`src/interp.c:637`) resolves the target via
`get_char_room(ch, arg)` (`src/handler.c:2194-2214`), which (a) returns `ch`
directly when `arg == "self"` and (b) iterates `in_room->people` **without
skipping ch**, so socialing your own name finds you too. Either path yields
`victim == ch`, routing to `others_auto`/`char_auto` (`src/interp.c:641-645`).

Before this fix, Python's hand-rolled victim search in `perform_social` did
`if person is char: continue` and had no `"self"` keyword, so both `smile self`
and `smile <ownname>` fell through to "They aren't here." and the
`char_auto`/`others_auto` branch was dead code.
"""

from __future__ import annotations

import pytest

from mud.commands.socials import perform_social
from mud.models.character import Character, character_registry
from mud.models.constants import Position, Sex
from mud.registry import room_registry
from mud.world import initialize_world


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield


@pytest.fixture
def test_room():
    return room_registry.get(3001)


@pytest.fixture
def alice(test_room):
    char = Character(
        name="Alice",
        short_descr="Alice the tester",
        is_npc=False,
        level=10,
        position=Position.STANDING,
        room=test_room,
        sex=Sex.FEMALE,
    )
    test_room.add_character(char)
    character_registry.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)
    if char in character_registry:
        character_registry.remove(char)


@pytest.fixture
def observer(test_room):
    char = Character(
        name="Bob",
        short_descr="Bob the listener",
        is_npc=False,
        level=10,
        position=Position.STANDING,
        room=test_room,
        sex=Sex.MALE,
    )
    test_room.add_character(char)
    character_registry.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)
    if char in character_registry:
        character_registry.remove(char)


def test_smile_self_keyword_reaches_char_auto(alice, observer):
    # mirrors ROM src/handler.c:2203-2204 — get_char_room returns ch for "self";
    # src/interp.c:643-644 — victim == ch routes to char_auto/others_auto.
    alice.messages.clear()
    observer.messages.clear()

    result = perform_social(alice, "smile", "self")

    assert result == ""
    assert alice.messages == ["You smile at yourself."]
    # others_auto goes to the room (TO_ROOM); $n→Alice, $mself→herself.
    assert observer.messages == ["Alice smiles at herself."]


def test_smile_own_name_reaches_char_auto(alice, observer):
    # mirrors ROM src/handler.c:2205-2211 — get_char_room's people loop does NOT
    # skip ch, so matching your own name also yields victim == ch.
    alice.messages.clear()
    observer.messages.clear()

    result = perform_social(alice, "smile", "alice")

    assert result == ""
    assert alice.messages == ["You smile at yourself."]
    assert observer.messages == ["Alice smiles at herself."]
