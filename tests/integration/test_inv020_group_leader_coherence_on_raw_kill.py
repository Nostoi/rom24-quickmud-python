"""INV-020 — GROUP-LEADER-COHERENCE-ON-RAW-KILL.

ROM ``src/fight.c:1718 raw_kill`` calls ``die_follower(ch)``
(``src/act_comm.c:1658-1680``) before any extract. ``die_follower``
walks ``char_list`` and resets every ``fch->leader == ch`` to
``fch`` so survivors don't hold a dangling pointer at the extracted
corpse — without that reset, ``src/handler.c:2018 is_same_group``
would continue to report two unrelated survivors as same-group
because both still pointed at the dead leader.

The contract spans three modules:

- ``mud/combat/death.py:raw_kill`` (the death funnel) must call
  ``die_follower(victim)`` BEFORE ``character_registry.remove(victim)``.
- ``mud/characters/follow.py:die_follower`` must walk the registry
  and reset every ``leader == ch`` to self.
- ``mud/commands/group_commands.py:is_same_group`` (or wherever
  the leader pointer is consulted) must compare leader pointers.

A direct-call test exists at
``tests/integration/test_die_follower_leader_chain.py``. This
file pins the full death-funnel chain: an NPC leader dies via the
production ``raw_kill`` path; ex-members must end up with
``leader is self`` and ``is_same_group`` must return False.
"""

from __future__ import annotations

import pytest

from mud.combat.death import raw_kill
from mud.commands.group_commands import is_same_group
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
    room_registry.pop(9430, None)


def _make_room(vnum: int = 9430) -> Room:
    room = Room(vnum=vnum, name="Death Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _make_npc(name: str, room: Room) -> Character:
    ch = Character(
        name=name,
        is_npc=True,
        level=10,
        room=room,
        position=int(Position.STANDING),
    )
    ch.messages = []
    ch.hit = 100
    ch.max_hit = 100
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def test_inv020_raw_kill_resets_followers_leader_to_self():
    """ROM src/fight.c:raw_kill → die_follower → leader-chain reset."""
    room = _make_room()
    leader = _make_npc("leader", room)
    member_a = _make_npc("membera", room)
    member_b = _make_npc("memberb", room)

    leader.leader = leader
    member_a.leader = leader
    member_b.leader = leader

    assert is_same_group(member_a, member_b), (
        "precondition: members of the same group test as same-group"
    )

    raw_kill(leader)

    # raw_kill (NPC path) removes leader from the registry.
    assert leader not in character_registry, (
        "raw_kill must extract NPC victims from character_registry"
    )

    # The load-bearing INV: followers no longer point at the extracted leader.
    assert member_a.leader is member_a, (
        f"ex-member leader pointer must be reset to self per die_follower "
        f"(ROM src/act_comm.c:1675); got {member_a.leader!r}"
    )
    assert member_b.leader is member_b, (
        f"ex-member leader pointer must be reset to self per die_follower "
        f"(ROM src/act_comm.c:1675); got {member_b.leader!r}"
    )
    assert not is_same_group(member_a, member_b), (
        "ex-members of a dead leader are no longer same-group "
        "(would falsely test True against a dangling pointer at the corpse)"
    )


def test_inv020_raw_kill_detaches_followers_master_pointer():
    """ROM src/act_comm.c:1674 — fch->master == ch ⇒ stop_follower(fch)."""
    room = _make_room()
    master = _make_npc("master", room)
    pet = _make_npc("pet", room)

    pet.master = master
    master.pet = pet

    raw_kill(master)

    assert pet.master is None, (
        "pet's master pointer must be cleared when master is raw_kill'd "
        "(ROM src/act_comm.c:1673-1675 stop_follower branch)"
    )
