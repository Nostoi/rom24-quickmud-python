"""FIGHT-098 — mob_hit's OFF_AREA_ATTACK sweep walks ROM's char_list.

ROM src/fight.c:262-270 (area attack):

    for (vch = ch->in_room->people; vch != NULL; vch = vch_next)
    {
        vch_next = vch->next;
        if ((vch != victim && vch->fighting == ch))
            one_hit (ch, vch, dt);
    }

The loop SEEDS at the room people-list head (newest arrival — ROM char_to_room
head-inserts) but follows the GLOBAL char_list link (`vch->next`, NOT
`->next_in_room`) — the same 2.4b6 quirk as check_assist's reservoir
(FIGHT-095). char_list is head-inserted at creation (src/db.c:2256-2257,
newest-first), so the visited domain is:

    { room head } ∪ { every char CREATED BEFORE the room head }

Two observable consequences this file locks (INV-045 nested site):

1. A char fighting the mob from ANOTHER room — created before the room head —
   IS visited (the swing then whiffs in one_hit's cross-room guard, FIGHT-097;
   the fled-but-still-fighting edge).
2. A char fighting the mob in the SAME room — created after the room head — is
   NEVER swung at (unreachable: it sits before the room head in char_list).

Python previously iterated room.people only, diverging on the swung-at set
(and hence draw counts/damage). C-binary-independent lock, GROUP-006 pattern.
"""

from __future__ import annotations

import pytest

import mud.combat.engine as _engine_module
from mud.combat.engine import mob_hit
from mud.models.character import Character, character_registry
from mud.models.constants import OffFlag
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
    return ch


def _recording_attack_round(monkeypatch) -> list[Character]:
    """Record every attack_round target; mob_hit resolves it as a module global."""

    targets: list[Character] = []

    def mock_attack_round(attacker: Character, victim: Character, dt=None) -> str:
        targets.append(victim)
        return ""

    monkeypatch.setattr(_engine_module, "attack_round", mock_attack_round)
    return targets


def test_fight098_same_room_char_newer_than_room_head_is_not_swung_at(monkeypatch) -> None:
    """A same-room char fighting the mob but created AFTER the room head is
    unreachable — ROM's walk only proceeds to OLDER chars (src/fight.c:266).

    Construction: Troll (the area-attacker) is created BEFORE Nate, then moves
    into room A LAST → Troll is the room head, but Nate is newer in char_list.
    """
    victim = _make("Alice", _ROOM_A, npc=False)

    attacker = _make("Troll", _ROOM_B, npc=True)  # created before Nate
    attacker.off_flags = int(OffFlag.AREA_ATTACK)

    nate = _make("Nate", _ROOM_A, npc=False)  # created AFTER the mob
    nate.fighting = attacker

    # Troll arrives in room A LAST → room head (head-insert), but its
    # char_list position is OLDER than Nate's.
    attacker.room.remove_character(attacker)
    victim.room.add_character(attacker)
    attacker.fighting = victim

    targets = _recording_attack_round(monkeypatch)
    mob_hit(attacker, victim)

    assert nate not in targets, (
        "Nate (created after the room head) must be UNREACHABLE — ROM's area "
        f"sweep walks char_list to older chars only (src/fight.c:264-269); got {targets!r}"
    )
    assert victim in targets, "the main victim must still take the opening one_hit"


def test_fight098_cross_room_char_fighting_the_mob_is_visited(monkeypatch) -> None:
    """A char in ANOTHER room whose fighting still points at the mob — created
    before the room head — IS visited (fled-but-still-fighting edge). The real
    one_hit then whiffs cross-room (FIGHT-097); the domain must include it.

    mirrors ROM src/fight.c:264-267 — `vch_next = vch->next` walks the global
    char_list from the room head, crossing room boundaries.
    """
    victim = _make("Alice2", _ROOM_A, npc=False)
    bob = _make("Bob", _ROOM_B, npc=False)  # OTHER room, created before the mob

    attacker = _make("Troll2", _ROOM_A, npc=True)  # newest → room-A head
    attacker.off_flags = int(OffFlag.AREA_ATTACK)
    bob.fighting = attacker
    attacker.fighting = victim

    targets = _recording_attack_round(monkeypatch)
    mob_hit(attacker, victim)

    assert bob in targets, (
        "Bob (cross-room, fighting the mob, older than the room head) must be "
        f"visited by the area sweep (ROM global char_list walk); got {targets!r}"
    )


def test_fight098_unregistered_room_head_falls_back_to_room_scope(monkeypatch) -> None:
    """Synthetic-test compatibility: if the room head is not in
    character_registry (raw-built fixtures), the sweep falls back to the
    room-people domain rather than silently swinging at nobody."""
    victim = _make("Alice3", _ROOM_A, npc=False)
    attacker = _make("Troll3", _ROOM_A, npc=True)
    attacker.off_flags = int(OffFlag.AREA_ATTACK)
    helper = _make("Helper", _ROOM_A, npc=False)
    helper.fighting = attacker
    attacker.fighting = victim

    # Unregister the room head (the newest arrival, Helper) to simulate a
    # raw-built fixture.
    head = victim.room.people[0]
    character_registry.remove(head)
    try:
        targets = _recording_attack_round(monkeypatch)
        mob_hit(attacker, victim)
        assert helper in targets, f"fallback must still sweep the in-room fighter; got {targets!r}"
    finally:
        character_registry.append(head)
