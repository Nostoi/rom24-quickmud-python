"""Integration tests for do_cast PK safety gates (CAST-007).

ROM parity references:
- src/magic.c:395-413 — TAR_CHAR_OFFENSIVE: is_safe + check_killer + AFF_CHARM gate
- src/magic.c:481-495 — TAR_OBJ_CHAR_OFF: is_safe_spell + check_killer + AFF_CHARM gate
- src/magic.c:514-537 — TAR_OBJ_CHAR_DEF / TAR_CHAR_DEFENSIVE: no safety gates
- src/magic.c:362-416 — overall do_cast target dispatch

Covers three PK gates missing from the Python port:
1. is_safe() / is_safe_spell() check — "Not on that target."
2. check_killer() — flag attacker PLR_KILLER for attacking innocent PCs
3. AFF_CHARM gate — "You can't do that on your own follower."
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.commands.combat import do_cast
from mud.models.character import Character
from mud.models.constants import (
    AffectFlag,
    PlayerFlag,
    Position,
    RoomFlag,
)
from mud.models.room import Room
from mud.skills.registry import load_skills, skill_registry
from mud.utils import rng_mm


@pytest.fixture(autouse=True)
def _load_skills_and_seed():
    skill_registry.skills.clear()
    skill_registry.handlers.clear()
    load_skills(Path("data/skills.json"))
    rng_mm.seed_mm(12345)
    yield
    skill_registry.skills.clear()
    skill_registry.handlers.clear()


def _make_pc(name: str = "Caster", *, level: int = 30, clan: int = 1, **overrides) -> Character:
    defaults = {
        "name": name,
        "level": level,
        "ch_class": 0,
        "is_npc": False,
        "clan": clan,
        "perm_stat": [0, 18, 0, 0, 0],
        "mana": 500,
        "position": Position.FIGHTING,
        "wait": 0,
        "skills": {"magic missile": 100},
    }
    defaults.update(overrides)
    return Character(**defaults)


def _make_room(vnum: int = 95001, *, safe: bool = False) -> Room:
    flags = int(RoomFlag.ROOM_SAFE) if safe else 0
    room = Room(
        vnum=vnum,
        name="Test Room",
        description="A test room.",
        room_flags=flags,
        sector_type=0,
    )
    return room


class TestCastOffensiveSafeRoomBlock:
    """TAR_CHAR_OFFENSIVE: is_safe(ch, victim) blocks the cast. ROM magic.c:400-404."""

    def test_cast_offensive_blocked_in_safe_room(self):
        caster = _make_pc()
        victim = Character(
            name="Victim",
            level=5,
            ch_class=0,
            is_npc=False,
            hit=100,
            max_hit=100,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        safe_room = _make_room(safe=True)
        safe_room.people = [caster, victim]
        caster.room = safe_room
        victim.room = safe_room

        result = do_cast(caster, "'magic missile' victim")
        assert "Not on that target" in result

    def test_cast_offensive_allowed_in_unsafe_room(self):
        caster = _make_pc()
        victim = Character(
            name="Victim",
            level=5,
            ch_class=0,
            is_npc=True,
            short_descr="a goblin",
            hit=500,
            max_hit=500,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        unsafe_room = _make_room(safe=False)
        unsafe_room.people = [caster, victim]
        caster.room = unsafe_room
        victim.room = unsafe_room

        result = do_cast(caster, "'magic missile' goblin")
        assert "Not on that target" not in result

    def test_cast_offensive_safe_self_not_blocked(self):
        """ROM magic.c:400 — is_safe(ch, victim) && victim != ch; self-cast is exempt."""
        caster = _make_pc(skills={"flamestrike": 100})
        unsafe_room = _make_room(safe=False)
        unsafe_room.people = [caster]
        caster.room = unsafe_room

        result = do_cast(caster, "flamestrike")
        assert "Not on that target" not in result


class TestCastOffensiveCheckKiller:
    """TAR_CHAR_OFFENSIVE: check_killer(ch, victim) flags PLR_KILLER.
    ROM magic.c:406. Only flags for PC casters attacking innocent PC victims
    who are clan members — ROM src/fight.c:1298 requires is_clan(ch)."""

    def test_cast_offensive_sets_killer_flag(self):
        caster = _make_pc(clan=1)
        victim = Character(
            name="Victim",
            level=5,
            ch_class=0,
            is_npc=False,
            hit=100,
            max_hit=100,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        unsafe_room = _make_room(safe=False)
        unsafe_room.people = [caster, victim]
        caster.room = unsafe_room
        victim.room = unsafe_room

        assert not (int(getattr(caster, "act", 0)) & int(PlayerFlag.KILLER))
        do_cast(caster, "'magic missile' Victim")
        assert int(getattr(caster, "act", 0)) & int(PlayerFlag.KILLER), (
            "check_killer should flag caster as KILLER when attacking innocent PC"
        )

    def test_cast_offensive_no_killer_for_npc_victim(self):
        caster = _make_pc(clan=1)
        victim = Character(
            name="goblin",
            level=5,
            ch_class=0,
            is_npc=True,
            short_descr="a goblin",
            hit=500,
            max_hit=500,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        unsafe_room = _make_room(safe=False)
        unsafe_room.people = [caster, victim]
        caster.room = unsafe_room
        victim.room = unsafe_room

        do_cast(caster, "'magic missile' goblin")
        assert not (int(getattr(caster, "act", 0)) & int(PlayerFlag.KILLER)), (
            "check_killer should NOT flag PC for attacking NPC"
        )

    def test_npc_caster_no_killer_flag(self):
        """ROM src/magic.c:395 — IS_NPC(ch) skips both is_safe and check_killer."""
        npc_caster = Character(
            name="angry mage",
            level=30,
            is_npc=True,
            short_descr="an angry mage",
            hit=500,
            max_hit=500,
            ch_class=0,
            position=Position.FIGHTING,
            perm_stat=[0, 18, 0, 0, 0],
            skills={"magic missile": 100},
            mana=500,
            wait=0,
        )
        victim = Character(
            name="Victim",
            level=5,
            ch_class=0,
            is_npc=False,
            hit=100,
            max_hit=100,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        unsafe_room = _make_room(safe=False)
        unsafe_room.people = [npc_caster, victim]
        npc_caster.room = unsafe_room
        victim.room = unsafe_room

        do_cast(npc_caster, "'magic missile' Victim")
        assert not (int(getattr(npc_caster, "act", 0)) & int(PlayerFlag.KILLER)), (
            "NPC casters should not be flagged KILLER"
        )

    def test_cast_offensive_no_killer_non_clan_caster(self):
        """ROM src/fight.c:1298 — is_clan(ch) check: non-clan PCs skip KILLER flag."""
        caster = _make_pc(clan=0)
        victim = Character(
            name="Victim",
            level=5,
            ch_class=0,
            is_npc=False,
            hit=100,
            max_hit=100,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        unsafe_room = _make_room(safe=False)
        unsafe_room.people = [caster, victim]
        caster.room = unsafe_room
        victim.room = unsafe_room

        do_cast(caster, "'magic missile' Victim")
        assert not (int(getattr(caster, "act", 0)) & int(PlayerFlag.KILLER)), (
            "Non-clan PC casters should not be flagged KILLER"
        )


class TestCastOffensiveCharmGate:
    """TAR_CHAR_OFFENSIVE: AFF_CHARM gate.
    ROM magic.c:408-412. The charm gate is reachable for NPC casters (which skip
    the !IS_NPC block) and for PC casters attacking an NPC (where check_killer
    returns early because resolved_victim is NPC). For a charmed PC attacking
    a non-master PC, check_killer strips the charm first (stop_follower),
    making the gate unreachable."""

    def test_charmed_npc_cannot_attack_master(self):
        npc_caster = Character(
            name="angry mage",
            level=30,
            is_npc=True,
            short_descr="an angry mage",
            hit=500,
            max_hit=500,
            ch_class=0,
            position=Position.FIGHTING,
            perm_stat=[0, 18, 0, 0, 0],
            skills={"magic missile": 100},
            mana=500,
            wait=0,
        )
        master = Character(
            name="Master",
            level=50,
            ch_class=0,
            is_npc=False,
            hit=1000,
            max_hit=1000,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        npc_caster.affected_by = int(getattr(npc_caster, "affected_by", 0)) | int(AffectFlag.CHARM)
        npc_caster.master = master
        unsafe_room = _make_room(safe=False)
        unsafe_room.people = [npc_caster, master]
        npc_caster.room = unsafe_room
        master.room = unsafe_room

        result = do_cast(npc_caster, "'magic missile' Master")
        assert "follower" in result.lower(), "Charmed NPC should be blocked from attacking their master"

    def test_charmed_npc_can_attack_non_master(self):
        npc_caster = Character(
            name="angry mage",
            level=30,
            is_npc=True,
            short_descr="an angry mage",
            hit=500,
            max_hit=500,
            ch_class=0,
            position=Position.FIGHTING,
            perm_stat=[0, 18, 0, 0, 0],
            skills={"magic missile": 100},
            mana=500,
            wait=0,
        )
        master = Character(
            name="Master",
            level=50,
            ch_class=0,
            is_npc=False,
            hit=1000,
            max_hit=1000,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        victim = Character(
            name="Bystander",
            level=5,
            ch_class=0,
            is_npc=True,
            short_descr="a bystander",
            hit=100,
            max_hit=100,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        npc_caster.affected_by = int(getattr(npc_caster, "affected_by", 0)) | int(AffectFlag.CHARM)
        npc_caster.master = master
        unsafe_room = _make_room(safe=False)
        unsafe_room.people = [npc_caster, master, victim]
        npc_caster.room = unsafe_room
        master.room = unsafe_room
        victim.room = unsafe_room

        result = do_cast(npc_caster, "'magic missile' bystander")
        assert "follower" not in result.lower()

    def test_charmed_pc_blocked_at_master_when_victim_is_npc(self):
        """ROM: check_killer returns early when resolved_victim is NPC
        (src/fight.c:1241), so charm is NOT stripped. The charm gate at
        magic.c:408-412 blocks the cast."""
        caster = _make_pc(clan=1)
        master = Character(
            name="Master",
            level=50,
            ch_class=0,
            is_npc=True,
            short_descr="the master",
            hit=1000,
            max_hit=1000,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        caster.affected_by = int(getattr(caster, "affected_by", 0)) | int(AffectFlag.CHARM)
        caster.master = master
        unsafe_room = _make_room(safe=False)
        unsafe_room.people = [caster, master]
        caster.room = unsafe_room
        master.room = unsafe_room

        result = do_cast(caster, "'magic missile' Master")
        assert "follower" in result.lower(), (
            "Charmed PC attacking NPC master: check_killer skips charm-stripping "
            "(resolved victim is NPC), so the charm gate blocks the cast"
        )

    def test_charmed_pc_charm_stripped_on_pc_victim(self):
        """When a charmed PC casts at a non-master PC, check_killer processes
        fully: resolved_victim is PC → crosses the IS_NPC gate → reaches the
        AFF_CHARM branch → stop_follower strips charm. The charm gate at
        magic.c:408 then sees IS_AFFECTED(ch, AFF_CHARM) = False."""
        caster = _make_pc(clan=1)
        other_pc = Character(
            name="Bystander",
            level=10,
            ch_class=0,
            is_npc=False,
            hit=100,
            max_hit=100,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        master = Character(
            name="MasterNPC",
            level=50,
            ch_class=0,
            is_npc=True,
            short_descr="the master",
            hit=1000,
            max_hit=1000,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        caster.affected_by = int(getattr(caster, "affected_by", 0)) | int(AffectFlag.CHARM)
        caster.master = master
        unsafe_room = _make_room(safe=False)
        unsafe_room.people = [caster, other_pc, master]
        caster.room = unsafe_room
        other_pc.room = unsafe_room
        master.room = unsafe_room

        result = do_cast(caster, "'magic missile' Bystander")
        assert "follower" not in result.lower(), (
            "Charmed PC attacking non-master PC: check_killer strips charm, so the charm gate does not fire"
        )
        assert not caster.has_affect(AffectFlag.CHARM), "check_killer should strip charm via stop_follower"


class TestCastOffensiveObjCharSafeRoomBlock:
    """TAR_OBJ_CHAR_OFF: is_safe_spell() blocks the cast on character targets.
    ROM magic.c:484-489."""

    def test_cast_curse_blocked_in_safe_room(self):
        caster = _make_pc(skills={"curse": 100})
        victim = Character(
            name="Victim",
            level=5,
            ch_class=0,
            is_npc=False,
            hit=100,
            max_hit=100,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        safe_room = _make_room(safe=True)
        safe_room.people = [caster, victim]
        caster.room = safe_room
        victim.room = safe_room

        result = do_cast(caster, "curse victim")
        assert "Not on that target" in result

    def test_cast_curse_obj_not_blocked_in_safe_room(self):
        """Object targets bypass is_safe_spell — ROM TAR_OBJ_CHAR_OFF object path
        has no safety gate. curse sword in a safe room should still work."""
        from mud.models.constants import ItemType
        from mud.models.obj import ObjIndex
        from mud.models.object import Object

        proto = ObjIndex(
            vnum=97001,
            name="sword cursedsword",
            short_descr="a cursed sword",
            item_type=int(ItemType.WEAPON),
            value=[0, 0, 0, 0, 0],
        )
        sword = Object(instance_id=None, prototype=proto)
        sword.value = list(proto.value)
        caster = _make_pc(skills={"curse": 100})
        safe_room = _make_room(safe=True)
        safe_room.people = [caster]
        safe_room.contents = [sword]
        caster.room = safe_room
        caster.inventory = [sword]
        sword.carried_by = caster

        result = do_cast(caster, "curse cursedsword")
        assert "Not on that target" not in result


class TestCastOffensiveObjCharCheckKiller:
    """TAR_OBJ_CHAR_OFF: check_killer on the character-target path.
    ROM magic.c:490."""

    def test_cast_curse_sets_killer_flag(self):
        caster = _make_pc(skills={"curse": 100}, clan=1)
        victim = Character(
            name="Victim",
            level=5,
            ch_class=0,
            is_npc=False,
            hit=100,
            max_hit=100,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        unsafe_room = _make_room(safe=False)
        unsafe_room.people = [caster, victim]
        caster.room = unsafe_room
        victim.room = unsafe_room

        do_cast(caster, "curse Victim")
        assert int(getattr(caster, "act", 0)) & int(PlayerFlag.KILLER)


class TestCastOffensiveObjCharCharmGate:
    """TAR_OBJ_CHAR_OFF: AFF_CHARM gate on character targets (NPC casters only).
    ROM magic.c:490-495. For PC casters, check_killer (line 490) strips the
    charm before the charm gate can fire — same ROM ordering as the
    TAR_CHAR_OFFENSIVE path."""

    def test_charmed_npc_curse_blocked_on_master(self):
        npc_caster = Character(
            name="angry mage",
            level=30,
            is_npc=True,
            short_descr="an angry mage",
            hit=500,
            max_hit=500,
            ch_class=0,
            position=Position.FIGHTING,
            perm_stat=[0, 18, 0, 0, 0],
            skills={"curse": 100},
            mana=500,
            wait=0,
        )
        master = Character(
            name="Master",
            level=50,
            ch_class=0,
            is_npc=False,
            hit=1000,
            max_hit=1000,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        npc_caster.affected_by = int(getattr(npc_caster, "affected_by", 0)) | int(AffectFlag.CHARM)
        npc_caster.master = master
        unsafe_room = _make_room(safe=False)
        unsafe_room.people = [npc_caster, master]
        npc_caster.room = unsafe_room
        master.room = unsafe_room

        result = do_cast(npc_caster, "curse Master")
        assert "follower" in result.lower(), "Charmed NPC should be blocked from cursing their master"


class TestCastDefensiveNoSafeRoomBlock:
    """TAR_CHAR_DEFENSIVE / TAR_OBJ_CHAR_DEF: no safety gates.
    ROM magic.c:419-442 and :514-537 have neither is_safe nor check_killer."""

    def test_cast_bless_in_safe_room_works(self):
        caster = _make_pc(skills={"bless": 100})
        victim = Character(
            name="Victim",
            level=5,
            ch_class=0,
            is_npc=False,
            hit=100,
            max_hit=100,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        safe_room = _make_room(safe=True)
        safe_room.people = [caster, victim]
        caster.room = safe_room
        victim.room = safe_room

        result = do_cast(caster, "bless victim")
        assert "Not on that target" not in result

    def test_cast_bless_no_killer_flag(self):
        caster = _make_pc(skills={"bless": 100})
        victim = Character(
            name="Victim",
            level=5,
            ch_class=0,
            is_npc=False,
            hit=100,
            max_hit=100,
            position=Position.STANDING,
            perm_stat=[0, 18, 0, 0, 0],
        )
        unsafe_room = _make_room(safe=False)
        unsafe_room.people = [caster, victim]
        caster.room = unsafe_room
        victim.room = unsafe_room

        do_cast(caster, "bless victim")
        assert not (int(getattr(caster, "act", 0)) & int(PlayerFlag.KILLER)), (
            "Defensive spells should never flag KILLER"
        )
