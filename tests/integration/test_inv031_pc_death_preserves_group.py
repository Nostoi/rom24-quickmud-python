"""INV-031 — PC-DEATH-PRESERVES-GROUP.

ROM ``src/fight.c:1694-1722 raw_kill`` calls
``extract_char(victim, IS_NPC(victim))`` — ``fPull=TRUE`` for NPCs,
``fPull=FALSE`` for PCs.  ``src/handler.c:2120-2122`` gates
``die_follower(ch)`` behind ``if (fPull)`` — so a PC death does NOT
dissolve group or follower relationships.  The PC's ``leader`` and
``master`` pointers survive, and other characters following the dead
PC keep their pointers.

This contract spans two modules:

- ``mud/combat/death.py:raw_kill`` must NOT call ``die_follower``
  for PC victims — matching ROM ``extract_char(ch, FALSE)``.
- ``mud/characters/follow.py:die_follower`` is still called for NPC
  victims (via ``extract_char(ch, TRUE)`` semantics), covered by
  INV-020.

A dead PC who returns to the group's room should still test as
same-group without re-following.
"""

from __future__ import annotations

import pytest

from mud.characters import is_same_group
from mud.combat.death import raw_kill
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _isolated_registry():
    char_snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(char_snapshot)
    room_registry.pop(9431, None)
    room_registry.pop(9432, None)


def _make_room(vnum: int) -> Room:
    room = Room(vnum=vnum, name="Test Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _make_pc(name: str, room: Room, level: int = 10) -> Character:
    ch = Character(
        name=name,
        is_npc=False,
        level=level,
        room=room,
        position=int(Position.STANDING),
    )
    ch.messages = []
    ch.hit = 100
    ch.max_hit = 100
    ch.mana = 100
    ch.move = 100
    ch.armor = [100, 100, 100, 100]
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def _make_npc(name: str, room: Room, level: int = 10) -> Character:
    ch = Character(
        name=name,
        is_npc=True,
        level=level,
        room=room,
        position=int(Position.STANDING),
    )
    ch.messages = []
    ch.hit = 100
    ch.max_hit = 100
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def test_pc_death_preserves_leader_pointer():
    """ROM extract_char(victim, FALSE) does NOT call die_follower."""
    room = _make_room(9431)
    leader = _make_pc("leader", room)
    member = _make_pc("member", room)

    member.leader = leader
    leader.leader = leader

    assert is_same_group(member, leader), "precondition: same group"
    assert member.leader is leader, "precondition: member follows leader"

    raw_kill(leader)

    assert leader.leader is leader, (
        "dead PC leader pointer must survive — ROM extract_char(ch, FALSE) does not call die_follower"
    )
    assert member.leader is leader, (
        "group member's leader pointer must not be reset on PC death — "
        "ROM die_follower is gated behind fPull=TRUE (NPCs only)"
    )
    assert is_same_group(member, leader), "dead PC is still same-group — leader pointer preserved per ROM"


def test_pc_death_preserves_follower_master_pointer():
    """A PC following another PC keeps master after the master dies."""
    room = _make_room(9431)
    master = _make_pc("master", room)
    follower = _make_pc("follower", room)

    follower.master = master
    follower.leader = master
    master.leader = master

    raw_kill(master)

    assert follower.master is master, (
        "follower's master pointer must survive PC death — ROM does not "
        "call die_follower for PCs (extract_char ch, FALSE)"
    )
    assert follower.leader is master, "follower's leader pointer must survive PC death"


def test_npc_death_still_calls_die_follower():
    """NPC death must still dissolve group — INV-020 contract unchanged."""
    room = _make_room(9431)
    npc_leader = _make_npc("npc_leader", room)
    member = _make_pc("member", room)

    npc_leader.leader = npc_leader
    member.leader = npc_leader

    raw_kill(npc_leader)

    assert member.leader is member, (
        "NPC death must reset followers' leader per die_follower — ROM extract_char(ch, TRUE) calls die_follower"
    )


def test_pc_group_survives_leader_death():
    """Two group members are still same-group after PC leader dies."""
    room = _make_room(9431)
    leader = _make_pc("leader", room)
    member_a = _make_pc("member_a", room)
    member_b = _make_pc("member_b", room)

    leader.leader = leader
    member_a.leader = leader
    member_b.leader = leader

    assert is_same_group(member_a, member_b), "precondition: same group"

    raw_kill(leader)

    assert is_same_group(member_a, member_b), (
        "group members must still be same-group after PC leader death — ROM does not dissolve group on PC death"
    )
