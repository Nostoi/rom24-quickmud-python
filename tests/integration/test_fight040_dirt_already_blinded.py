"""FIGHT-040 — dirt-kick already-blinded check: ROM `$E` message, no invented guard.

ROM `do_dirt` (`src/fight.c:2521-2524`) has exactly ONE already-affected check —
`if (IS_AFFECTED(victim, AFF_BLIND)) act("$E's already been blinded.", ch, NULL,
victim, TO_CHAR)` — and it runs *before* the `victim == ch` "Very funny." check
(`:2528`). `$E` is the victim's gendered subject pronoun (He/She/It), capitalized
at sentence start.

The Python `dirt_kicking` handler had three divergences:
  1. the AFF_BLIND message baked the victim name ("{name} is already blinded.")
     instead of ROM's gendered `act("$E's already been blinded.")`;
  2. it added an INVENTED second guard — `if victim.has_spell_effect("dirt
     kicking"): "{name} already has dirt in their eyes."` — that has no ROM
     equivalent (and is dead code: the dirt-kick effect sets AFF_BLIND, so the
     AFF_BLIND check above already catches a re-kick);
  3. it checked `victim == ch` ("Very funny.") *before* the AFF_BLIND check.

ROM C: src/fight.c:2521-2528 (do_dirt already-blinded / self checks).
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag, Sex
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _room(vnum: int = 3077) -> Room:
    room = Room(vnum=vnum, name="Pit")
    room.people = []
    return room


@pytest.mark.parametrize(
    "sex,pronoun",
    [(int(Sex.MALE), "He"), (int(Sex.FEMALE), "She"), (int(Sex.NONE), "It")],
)
def test_dirt_already_blinded_uses_gendered_pronoun(sex: int, pronoun: str) -> None:
    caster = Character(name="Kicker", level=20, is_npc=False)
    victim = Character(name="Mark", level=18, is_npc=False, sex=sex)
    room = _room()
    for ch in (caster, victim):
        room.add_character(ch)
    victim.add_affect(AffectFlag.BLIND)
    caster.messages.clear()

    skill_handlers.dirt_kicking(caster, victim)

    # ROM `$E's already been blinded.` — gendered subject pronoun, not the name.
    assert caster.messages[-1] == f"{pronoun}'s already been blinded.", caster.messages


def test_dirt_rekick_hits_aff_blind_branch_after_guard_removed() -> None:
    """A victim carrying the dirt-kick effect (which sets AFF_BLIND) must still be
    rejected via the AFF_BLIND check, proving the deleted invented "dirt kicking"
    guard's behavior survives its removal."""
    from mud.models.character import SpellEffect

    caster = Character(name="Kicker", level=50, is_npc=False)
    victim = Character(name="Mark", level=5, is_npc=False, sex=int(Sex.MALE))
    room = _room()
    for ch in (caster, victim):
        room.add_character(ch)

    # Mirror a landed dirt-kick: the effect sets AFF_BLIND (handlers.py:3289).
    victim.apply_spell_effect(
        SpellEffect(name="dirt kicking", duration=0, level=50, affect_flag=AffectFlag.BLIND)
    )
    assert victim.has_affect(AffectFlag.BLIND)

    caster.messages.clear()
    skill_handlers.dirt_kicking(caster, victim)
    # Re-kick hits the AFF_BLIND branch → gendered "He's already been blinded."
    assert caster.messages[-1] == "He's already been blinded.", caster.messages


def test_dirt_blind_self_target_matches_rom_order() -> None:
    """ROM checks AFF_BLIND before `victim == ch`, so a blind caster targeting
    themselves gets the already-blinded line, not "Very funny."."""
    caster = Character(name="Kicker", level=20, is_npc=False, sex=int(Sex.MALE))
    room = _room()
    room.add_character(caster)
    caster.add_affect(AffectFlag.BLIND)
    caster.messages.clear()

    skill_handlers.dirt_kicking(caster, caster)
    assert caster.messages[-1] == "He's already been blinded.", caster.messages
