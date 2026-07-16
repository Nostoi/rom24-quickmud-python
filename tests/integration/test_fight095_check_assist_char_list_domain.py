"""FIGHT-095 — check_assist's inner target-selection loop walks ROM's char_list.

ROM src/fight.c:159-170 (NPC-assist reservoir):

    for (vch = ch->in_room->people; vch; vch = vch->next)

The loop SEEDS at the room people-list head (newest arrival — ROM char_to_room
head-inserts) but then follows the GLOBAL char_list link (`->next`, NOT
`->next_in_room`) — a 2.4b6 quirk. char_list is head-inserted at creation
(src/db.c:2256-2257), i.e. newest-first, so the visited domain is:

    { room head } ∪ { every char CREATED BEFORE the room head }

Two observable consequences this file locks (INV-045 nested site):

1. A same-group-as-victim char in ANOTHER room — created before the room head —
   IS visited (and can be reservoir-picked, cross-room).
2. A same-group char in the SAME room — created after the room head — is
   NEVER visited (unreachable: it sits before the room head in char_list).

Python previously iterated room.people only, diverging on both the draw count
(shared-RNG desync) and the reachable target set. The C-oracle ground truth is
the check_assist_cross_room differential golden; these tests are the
C-binary-independent lock (GROUP-006 pattern).
"""

from __future__ import annotations

import pytest

import mud.combat.assist as _assist_module
from mud.combat.assist import check_assist
from mud.models.character import Character, character_registry
from mud.models.constants import OffFlag
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world

_ROOM_A = 3001
_ROOM_B = 3008


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _make(name: str, room_vnum: int, *, npc: bool) -> Character:
    ch = create_test_character(name, room_vnum)
    ch.is_npc = npc
    ch.level = 20
    ch.act = 0
    ch.off_flags = 0
    ch.affected_by = 0
    ch.master = None
    ch.fighting = None
    ch.leader = None
    if npc:
        ch.group = 0
        ch.race = 0
    return ch


def _recording_rng(monkeypatch) -> list[tuple[int, int]]:
    recorded: list[tuple[int, int]] = []

    def mock_number_range(low: int, high: int) -> int:
        recorded.append((low, high))
        return 0  # always select — the LAST qualifying char visited wins

    monkeypatch.setattr(_assist_module, "can_see_character", lambda _o, _t: True)
    monkeypatch.setattr(rng_mm, "number_bits", lambda _: 1)  # pass the 50% gate
    monkeypatch.setattr(rng_mm, "number_range", mock_number_range)
    return recorded


def test_fight095_cross_room_group_member_is_in_the_reservoir(monkeypatch) -> None:
    """A same-group char in another room, created BEFORE the room head, draws.

    mirrors ROM src/fight.c:161 — `vch = vch->next` walks the global char_list
    from the room head, so cross-room group members are reachable.
    """
    victim = _make("Alice", _ROOM_A, npc=False)
    ally = _make("Bob", _ROOM_B, npc=False)  # OTHER room, created before the mobs
    ally.leader = victim

    attacker = _make("Troll", _ROOM_A, npc=True)
    assister = _make("Goblin", _ROOM_A, npc=True)  # newest → room-A head
    assister.off_flags = int(OffFlag.ASSIST_ALL)
    attacker.fighting = victim

    recorded = _recording_rng(monkeypatch)
    check_assist(attacker, victim)

    # Walk from Goblin (room head, newest) → Troll → Bob → Alice → older boot
    # chars. Qualifying: Bob (cross-room!) then Alice → exactly (0,0), (0,1).
    reservoir = [r for r in recorded if r[0] == 0 and r[1] <= 1][:2]
    assert (0, 0) in recorded and (0, 1) in recorded, (
        f"expected 2 reservoir draws — the cross-room ally must be visited "
        f"(ROM global char_list walk); got {recorded!r} (reservoir={reservoir!r})"
    )


def test_fight095_same_room_member_created_after_room_head_is_unreachable(monkeypatch) -> None:
    """ROM's quirk cuts BOTH ways: a same-room group member NEWER than the room
    head sits before it in char_list and is never visited.

    Construction: Troll (mob) is created FIRST (in room B), Carol (victim's
    group member, room A) is created after — then Troll moves to room A last,
    making it the room head. The walk starts at Troll's char_list position and
    proceeds to OLDER chars only: Alice qualifies, Carol never appears.
    """
    victim = _make("Alice", _ROOM_A, npc=False)

    attacker = _make("Troll2", _ROOM_B, npc=True)  # created before Carol
    assister = _make("Goblin2", _ROOM_B, npc=True)
    assister.off_flags = int(OffFlag.ASSIST_ALL)

    carol = _make("Carol", _ROOM_A, npc=False)  # created AFTER the mobs
    carol.leader = victim

    # Mobs arrive in room A LAST → they are the room heads (head-insert),
    # but their char_list position is OLDER than Carol's.
    for mob in (assister, attacker):
        mob.room.remove_character(mob)
        room_a = victim.room
        room_a.add_character(mob)

    attacker.fighting = victim

    recorded = _recording_rng(monkeypatch)
    check_assist(attacker, victim)

    # Only Alice qualifies: exactly ONE reservoir draw, (0, 0). Carol is newer
    # than the room head (attacker/assister) → unreachable in ROM's walk.
    assert (0, 1) not in recorded, (
        f"Carol (created after the room head) must be UNREACHABLE — ROM's walk "
        f"only proceeds to older chars (src/fight.c:161); got draws {recorded!r}"
    )
    assert (0, 0) in recorded, f"Alice must still draw once; got {recorded!r}"


def test_fight095_unregistered_room_head_falls_back_to_room_scope(monkeypatch) -> None:
    """Synthetic-test compatibility: if the room head is not in
    character_registry (raw-built fixtures), the loop falls back to the
    room-people domain rather than silently finding nothing."""
    victim = _make("Alice2", _ROOM_A, npc=False)
    attacker = _make("Troll3", _ROOM_A, npc=True)
    assister = _make("Goblin3", _ROOM_A, npc=True)
    assister.off_flags = int(OffFlag.ASSIST_ALL)
    attacker.fighting = victim

    # Unregister the room head (the newest arrival, Goblin3) to simulate a
    # raw-built fixture.
    head = victim.room.people[0]
    character_registry.remove(head)
    try:
        recorded = _recording_rng(monkeypatch)
        check_assist(attacker, victim)
        assert (0, 0) in recorded, f"fallback must still find the in-room victim; got {recorded!r}"
    finally:
        character_registry.append(head)
