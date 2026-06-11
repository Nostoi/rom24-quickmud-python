"""FIGHT-050 — is_safe missing three NPC-attacker guards.

ROM src/fight.c:1040-1094 — three guards absent from mud/combat/safety.py:is_safe:

    (1) ACT_PET (line ~1059):
        if (!IS_NPC(ch) && IS_SET(victim->act, ACT_PET))
            → act("But $N looks so cute and cuddly...", ch, NULL, victim, TO_CHAR)
            → return TRUE

    (2) AFF_CHARM non-owner (line ~1067):
        if (!IS_NPC(ch) && IS_AFFECTED(victim, AFF_CHARM) && ch != victim->master)
            → send_to_char("You don't own that monster.\n\r", ch)
            → return TRUE

    (3) Charmed NPC attacking wrong PC (lines ~1087-1093):
        if (IS_NPC(ch) && IS_AFFECTED(ch, AFF_CHARM)
                && ch->master != NULL && ch->master->fighting != victim)
            → send_to_char("Players are your friends!\n\r", ch)
            → return TRUE
"""

from __future__ import annotations

import pytest

from mud.combat.safety import is_safe
from mud.models.character import Character
from mud.models.constants import ActFlag, AffectFlag
from mud.world import create_test_character, initialize_world

_ROOM = 2300  # non-safe room in area.lst


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _make_pc(name: str) -> Character:
    ch = create_test_character(name, _ROOM)
    ch.is_npc = False
    ch.level = 20
    ch.act = 0
    ch.affected_by = 0
    ch.master = None
    ch.fighting = None
    return ch


def _make_npc(name: str) -> Character:
    ch = create_test_character(name, _ROOM)
    ch.is_npc = True
    ch.level = 20
    ch.act = int(ActFlag.IS_NPC)
    ch.affected_by = 0
    ch.master = None
    ch.fighting = None
    return ch


# ── Guard 1: ACT_PET ──────────────────────────────────────────────────────────


def test_fight050_pc_cannot_attack_pet_npc() -> None:
    # mirrors ROM src/fight.c:1059-1063 — !IS_NPC(ch) && IS_SET(victim->act, ACT_PET)
    attacker = _make_pc("Attacker")
    pet = _make_npc("Fido")
    pet.act = int(ActFlag.IS_NPC | ActFlag.PET)

    result = is_safe(attacker, pet)

    assert result is True, (
        f"is_safe should return True (safe / blocked) when PC attacks a pet NPC; got {result!r}. "
        "ROM src/fight.c:1059: IS_SET(victim->act, ACT_PET) → return TRUE"
    )


def test_fight050_npc_attacker_can_attack_pet_npc() -> None:
    # mirrors ROM src/fight.c:1059 — guard is inside !IS_NPC(ch) block;
    # NPC attackers are NOT blocked from attacking pets by this guard.
    attacker = _make_npc("Aggro")
    pet = _make_npc("Fido")
    pet.act = int(ActFlag.IS_NPC | ActFlag.PET)

    result = is_safe(attacker, pet)

    assert result is False, (
        f"is_safe should return False (not safe) for NPC attacking a pet NPC; got {result!r}. "
        "ROM src/fight.c:1059: ACT_PET guard is inside !IS_NPC(ch) — NPCs are not bound by it."
    )


# ── Guard 2: AFF_CHARM non-owner ──────────────────────────────────────────────


def test_fight050_pc_cannot_attack_charmed_npc_if_not_owner() -> None:
    # mirrors ROM src/fight.c:1067-1070 — !IS_NPC(ch) && IS_AFFECTED(victim, AFF_CHARM)
    #                                       && ch != victim->master
    attacker = _make_pc("Attacker")
    owner = _make_pc("Owner")
    charmed_mob = _make_npc("Thrall")
    charmed_mob.affected_by = int(AffectFlag.CHARM)
    charmed_mob.master = owner  # attacker is NOT the master

    result = is_safe(attacker, charmed_mob)

    assert result is True, (
        f"is_safe should block a PC from attacking a charmed NPC they don't own; got {result!r}. "
        "ROM src/fight.c:1067: IS_AFFECTED(victim, AFF_CHARM) && ch != victim->master → return TRUE"
    )


def test_fight050_owner_can_attack_own_charmed_npc() -> None:
    # mirrors ROM src/fight.c:1067 — owner IS victim->master → guard does not fire
    owner = _make_pc("Owner")
    charmed_mob = _make_npc("Thrall")
    charmed_mob.affected_by = int(AffectFlag.CHARM)
    charmed_mob.master = owner  # attacker IS the master → allowed

    result = is_safe(owner, charmed_mob)

    assert result is False, (
        f"is_safe should allow owner to attack their own charmed NPC; got {result!r}. "
        "ROM src/fight.c:1067: ch == victim->master → guard does not fire → return FALSE"
    )


# ── Guard 3: Charmed NPC attacking wrong PC ───────────────────────────────────


def test_fight050_charmed_npc_blocked_from_attacking_non_master_target() -> None:
    # mirrors ROM src/fight.c:1087-1093 — IS_NPC(ch) && IS_AFFECTED(ch, AFF_CHARM)
    #   && ch->master != NULL && ch->master->fighting != victim
    master = _make_pc("Master")
    other_pc = _make_pc("OtherPC")
    charmed_mob = _make_npc("Thrall")
    charmed_mob.affected_by = int(AffectFlag.CHARM)
    charmed_mob.master = master
    master.fighting = other_pc  # master is fighting OtherPC, not Victim

    victim = _make_pc("Victim")  # master is NOT fighting this PC

    result = is_safe(charmed_mob, victim)

    assert result is True, (
        f"is_safe should block charmed NPC from attacking a PC whose master is not fighting; "
        f"got {result!r}. "
        "ROM src/fight.c:1087-1093: IS_AFFECTED(ch, AFF_CHARM) && ch->master != NULL "
        "&& ch->master->fighting != victim → return TRUE"
    )


def test_fight050_charmed_npc_allowed_to_attack_masters_target() -> None:
    # mirrors ROM src/fight.c:1087-1093 — when master IS fighting victim, guard does NOT fire
    master = _make_pc("Master")
    victim = _make_pc("Victim")
    charmed_mob = _make_npc("Thrall")
    charmed_mob.affected_by = int(AffectFlag.CHARM)
    charmed_mob.master = master
    master.fighting = victim  # master IS fighting victim → guard does not fire

    result = is_safe(charmed_mob, victim)

    assert result is False, (
        f"is_safe should allow charmed NPC to assist master by attacking master's target; "
        f"got {result!r}. "
        "ROM src/fight.c:1087: ch->master->fighting == victim → guard does not fire → return FALSE"
    )
