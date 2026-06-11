"""FIGHT-051 — _murder_safety_check missing victim-NPC ACT_PET and AFF_CHARM non-owner guards.

ROM src/fight.c:2861 — do_murder calls is_safe(ch, victim) first. is_safe runs the
victim-NPC PC-attacker sub-block (src/fight.c:1056-1071):

    (1) if (IS_SET(victim->act, ACT_PET)):
            act("But $N looks so cute and cuddly...", ch, NULL, victim, TO_CHAR)
            return TRUE  → do_murder returns without attacking

    (2) if (IS_AFFECTED(victim, AFF_CHARM) && ch != victim->master):
            send_to_char("You don't own that monster.\n\r", ch)
            return TRUE  → do_murder returns without attacking

Python do_murder bypasses is_safe and calls _murder_safety_check directly.
_murder_safety_check has the charm-master guard for the ATTACKER but neither
victim-side guard above.
"""

from __future__ import annotations

import pytest

from mud.commands.murder import _murder_safety_check
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
    ch.clan = 1
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


def test_fight051_murder_blocked_on_pet_npc() -> None:
    # mirrors ROM src/fight.c:2861 is_safe call → src/fight.c:1059
    # is_safe returns TRUE for ACT_PET; do_murder returns without attacking
    char = _make_pc("Attacker")
    pet = _make_npc("Fido")
    pet.act = int(ActFlag.IS_NPC | ActFlag.PET)

    result = _murder_safety_check(char, pet)

    assert result is not None, (
        "_murder_safety_check should block murder of a pet NPC; got None (allowed). "
        "ROM src/fight.c:2861 calls is_safe which returns TRUE for ACT_PET victims."
    )
    assert "cute and cuddly" in result.lower(), (
        f"Expected pet message; got {result!r}. "
        "ROM src/fight.c:1059: IS_SET(victim->act, ACT_PET) → 'But $N looks so cute and cuddly...'"
    )


def test_fight051_murder_allowed_on_plain_npc() -> None:
    # baseline: non-pet, non-charmed NPC can be murdered (no safety block)
    char = _make_pc("Attacker")
    mob = _make_npc("Goblin")

    result = _murder_safety_check(char, mob)

    assert result is None, f"_murder_safety_check should not block murder of an ordinary NPC; got {result!r}."


# ── Guard 2: AFF_CHARM non-owner ──────────────────────────────────────────────


def test_fight051_murder_blocked_on_charmed_npc_not_owned() -> None:
    # mirrors ROM src/fight.c:2861 is_safe call → src/fight.c:1067
    # is_safe returns TRUE when victim is charmed and ch != victim->master
    char = _make_pc("Attacker")
    owner = _make_pc("Owner")
    charmed_mob = _make_npc("Thrall")
    charmed_mob.affected_by = int(AffectFlag.CHARM)
    charmed_mob.master = owner  # char is NOT the master

    result = _murder_safety_check(char, charmed_mob)

    assert result is not None, (
        "_murder_safety_check should block murder of a charmed NPC the attacker doesn't own; "
        "got None (allowed). "
        "ROM src/fight.c:1067: IS_AFFECTED(victim, AFF_CHARM) && ch != victim->master → return TRUE"
    )
    assert "don't own" in result.lower(), (
        f"Expected ownership message; got {result!r}. "
        "ROM src/fight.c:1067: → send_to_char('You don\\'t own that monster.')"
    )


def test_fight051_murder_allowed_on_own_charmed_npc() -> None:
    # mirrors ROM src/fight.c:1067 — owner IS victim->master → guard does not fire
    owner = _make_pc("Owner")
    charmed_mob = _make_npc("Thrall")
    charmed_mob.affected_by = int(AffectFlag.CHARM)
    charmed_mob.master = owner  # owner IS the master → allowed

    result = _murder_safety_check(owner, charmed_mob)

    assert result is None, (
        f"_murder_safety_check should allow owner to murder their own charmed NPC; got {result!r}. "
        "ROM src/fight.c:1067: ch == victim->master → guard does not fire."
    )
