"""die_follower must reset the leader chain — ROM src/act_comm.c:1658-1680.

When a character dies, ROM walks ``char_list`` and for every ``fch`` whose
``leader == ch`` (the deceased), sets ``fch->leader = fch`` so the former
group members become their own independent group leaders.  Python had been
leaving those leader pointers dangling at the dead character, which breaks
``is_same_group`` (src/handler.c:2018) — it compares ``leader`` pointers, so
two unrelated survivors would still test as "same group" because both still
pointed at the same extracted corpse.

ROM ``die_follower`` also detaches ``ch`` from its own master (releasing the
master's pet pointer) and clears ``ch->leader``.  Python's variant only
handled "stop everyone following ch" and missed both self-cleanup steps.
"""

from __future__ import annotations

import pytest

from mud.characters.follow import add_follower, die_follower
from mud.commands.group_commands import is_same_group
from mud.models.character import Character, character_registry


@pytest.fixture(autouse=True)
def _isolated_registry():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def _make_char(name: str) -> Character:
    ch = Character(name=name)
    ch.is_npc = False
    ch.messages = []
    character_registry.append(ch)
    return ch


def test_die_follower_resets_leader_to_self_for_each_ex_member():
    leader = _make_char("Leader")
    member_a = _make_char("MemberA")
    member_b = _make_char("MemberB")

    member_a.leader = leader
    member_b.leader = leader
    leader.leader = leader

    assert is_same_group(member_a, member_b)

    die_follower(leader)

    assert member_a.leader is member_a, "ex-member must become own leader"
    assert member_b.leader is member_b, "ex-member must become own leader"
    assert not is_same_group(member_a, member_b), "ex-members of a dead leader's group are no longer in the same group"


def test_die_follower_detaches_ch_from_its_own_master():
    master = _make_char("Master")
    ch = _make_char("Ch")

    add_follower(ch, master)
    master.pet = ch
    assert ch.master is master

    die_follower(ch)

    assert ch.master is None, "die_follower must clear ch.master"
    assert ch.leader is None, "die_follower must clear ch.leader"
    assert master.pet is None, "die_follower must clear master.pet if it was ch"
