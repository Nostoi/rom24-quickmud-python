"""HANDLER-002 — get_char_room counts each occupant at most once (N.name).

ROM `get_char_room` (`src/handler.c:2205-2211`) gates each occupant with a
SINGLE boolean test — `if (!can_see (ch, rch) || !is_name (arg, rch->name))
continue; if (++count == number) return rch;` — so `count` advances **once per
occupant**.

Python's helper historically split the match across two blocks that each ran
`count += 1`: a name/short_descr block and a separate keyword-list block. An
occupant matching BOTH advanced `count` twice, so `2.<name>` could resolve to
the FIRST occupant (count hit 2 on occupant #1) instead of the second.

This is a **latent** double-count, not a live ROM divergence: real Characters
keep their keyword list in `.name` (see the JSON loader — keywords populate
`ObjIndex.name`/mob name, and `Character` is never given a `.keywords`
attribute), so the keyword block is empty for every real occupant and the bug
never fires in production. The test below forces the multi-field match by
setting `.keywords` directly — exercising the defensive invariant that an
occupant counts once even if both match-sources are ever populated.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.registry import room_registry
from mud.world import initialize_world
from mud.world.char_find import get_char_room


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield


@pytest.fixture
def test_room():
    return room_registry.get(3001)


def _make_guard(room, tag: str) -> Character:
    # Distinct short_descr per guard so the two dataclass instances are not
    # equal (room.add_character dedupes via __eq__); both still match "guard".
    guard = Character(
        name="guard",
        short_descr=f"a {tag} guard",
        is_npc=True,
        level=10,
        position=Position.STANDING,
        room=room,
    )
    # Force the historically-double-counted path: a keyword list that ALSO
    # matches the search term, in addition to the name/short_descr match.
    guard.keywords = "guard soldier"  # type: ignore[attr-defined]
    room.add_character(guard)
    character_registry.append(guard)
    return guard


def test_2name_selects_second_occupant_not_first(test_room):
    # mirrors ROM src/handler.c:2205-2211 — count advances once per occupant, so
    # "2.guard" must return the SECOND guard. The pre-fix double-count returned
    # the first (count reached 2 on occupant #1).
    g1 = _make_guard(test_room, "city")
    g2 = _make_guard(test_room, "temple")
    try:
        assert get_char_room(g1, "2.guard") is g2
        # "1.guard" still resolves to the first.
        assert get_char_room(g1, "1.guard") is g1
        # bare "guard" resolves to the first (number defaults to 1).
        assert get_char_room(g1, "guard") is g1
    finally:
        for c in (g1, g2):
            if c in test_room.people:
                test_room.people.remove(c)
            if c in character_registry:
                character_registry.remove(c)
