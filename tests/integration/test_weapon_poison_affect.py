"""FIGHT-016 — WEAPON_POISON applies a timed, STR-reducing poison affect.

ROM ``src/fight.c:616-624``: on a WEAPON_POISON hit where the victim fails the
poison save, ROM builds and ``affect_join``s a structured affect::

    af.where     = TO_AFFECTS;
    af.type      = gsn_poison;
    af.level     = level * 3 / 4;
    af.duration  = level / 2;
    af.location  = APPLY_STR;
    af.modifier  = -1;
    af.bitvector = AFF_POISON;
    affect_join (victim, &af);

Python previously applied only a bare ``AffectFlag.POISON`` (untimed, no STR
penalty, no ``affect_join`` merge). These tests pin the structured affect.
"""

from __future__ import annotations

from unittest.mock import patch

from mud.combat.engine import process_weapon_special_attacks
from mud.models.character import character_registry
from mud.models.constants import WEAPON_POISON, AffectFlag, Stat
from mud.models.obj import Affect
from mud.models.room import Room
from mud.registry import room_registry
from mud.world.world_state import create_test_character


class _MockWeapon:
    def __init__(self, name: str, level: int, flags: int) -> None:
        self.name = name
        self.level = level
        self.weapon_flags = flags
        self.affected: list[Affect] = []


def _envenom(level: int, duration: int) -> Affect:
    """Mirror the temporary envenom affect created by spell_poison on a weapon
    (mud/skills/handlers.py:6388-6398) — gsn_poison on wield->affected."""
    af = Affect(where=0, type=0, level=level, duration=duration, location=0, modifier=0, bitvector=int(WEAPON_POISON))
    af.spell_name = "poison"
    af.wear_off_message = "The poison on $p dries up."
    return af


def _setup(vnum: int, weapon_level: int):
    room = Room(vnum=vnum, name="Test Room", description="d", room_flags=0, sector_type=0)
    room.people = []
    room_registry[vnum] = room

    attacker = create_test_character("Attaq", vnum)
    attacker.level = 20
    weapon = _MockWeapon("the venom blade", level=weapon_level, flags=int(WEAPON_POISON))
    attacker.wielded_weapon = weapon

    victim = create_test_character("Victus", vnum)
    victim.level = 20
    attacker.fighting = victim
    return attacker, victim


@patch("mud.combat.engine.saves_spell")
def test_fight_016_weapon_poison_applies_timed_str_reducing_affect(mock_saves):
    """ROM src/fight.c:616-624 — failed save → APPLY_STR -1 affect, level*3/4, duration level/2."""
    mock_saves.return_value = False  # save fails → poison branch fires
    vnum = 2100
    try:
        attacker, victim = _setup(vnum, weapon_level=20)

        process_weapon_special_attacks(attacker, victim)

        # ROM af.bitvector = AFF_POISON
        assert victim.has_affect(AffectFlag.POISON), "AFF_POISON bitvector not set"
        # Structured, named, TIMED affect — not a bare flag
        assert victim.has_spell_effect("poison"), "poison is a bare flag, not a timed affect"
        effect = victim.spell_effects["poison"]
        # ROM af.duration = level / 2  (20 -> 10)
        assert effect.duration == 10, f"duration {effect.duration} != level//2"
        # ROM af.level = level * 3 / 4  (20 -> 15)
        assert effect.level == 15, f"level {effect.level} != level*3//4"
        # ROM af.location = APPLY_STR, af.modifier = -1
        assert effect.stat_modifiers.get(Stat.STR) == -1, "missing APPLY_STR -1 modifier"
        # the -1 STR modifier was actually applied to the character's mod_stat
        assert victim.mod_stat[int(Stat.STR)] == -1, "APPLY_STR -1 not applied to mod_stat"
    finally:
        room_registry.pop(vnum, None)
        character_registry.clear()


@patch("mud.combat.engine.saves_spell")
def test_fight_016_successful_save_applies_no_poison(mock_saves):
    """ROM src/fight.c:610 — passing the save skips the affect entirely."""
    mock_saves.return_value = True  # save succeeds → no poison
    vnum = 2101
    try:
        attacker, victim = _setup(vnum, weapon_level=20)
        process_weapon_special_attacks(attacker, victim)
        assert not victim.has_affect(AffectFlag.POISON)
        assert not victim.has_spell_effect("poison")
    finally:
        room_registry.pop(vnum, None)
        character_registry.clear()


@patch("mud.combat.engine.saves_spell")
def test_fight_017_temporary_envenom_is_the_level_source(mock_saves):
    """ROM src/fight.c:605-608 — a temporary envenom affect on the weapon
    supplies the poison level (poison->level), not wield->level."""
    mock_saves.return_value = False
    vnum = 2102
    try:
        attacker, victim = _setup(vnum, weapon_level=2)  # low weapon level
        weapon = attacker.wielded_weapon
        weapon.affected.append(_envenom(level=40, duration=5))

        process_weapon_special_attacks(attacker, victim)

        # Resulting victim affect derives from the envenom level (40), not the
        # weapon level (2): level*3//4 == 30, duration//2 == 20. Using the
        # weapon level would give level 1, duration 1.
        effect = victim.spell_effects["poison"]
        assert effect.level == 30, f"level {effect.level} — used weapon.level not poison->level"
        assert effect.duration == 20, f"duration {effect.duration} — used weapon.level not poison->level"

        # Per-hit weakening: poison->level -= 2, poison->duration -= 1.
        env = weapon.affected[0]
        assert env.level == 38, f"envenom level not weakened: {env.level}"
        assert env.duration == 4, f"envenom duration not weakened: {env.duration}"
    finally:
        room_registry.pop(vnum, None)
        character_registry.clear()


@patch("mud.combat.engine.saves_spell")
def test_fight_017_weakening_happens_even_on_successful_save(mock_saves):
    """ROM src/fight.c:627-636 — weakening sits OUTSIDE the !saves_spell block,
    so a passed save still decrements the envenom."""
    mock_saves.return_value = True  # save succeeds → no affect on victim
    vnum = 2103
    try:
        attacker, victim = _setup(vnum, weapon_level=2)
        weapon = attacker.wielded_weapon
        weapon.affected.append(_envenom(level=40, duration=5))

        process_weapon_special_attacks(attacker, victim)

        assert not victim.has_spell_effect("poison")  # save passed
        env = weapon.affected[0]
        assert env.level == 38, "weakening skipped on successful save"
        assert env.duration == 4, "weakening skipped on successful save"
    finally:
        room_registry.pop(vnum, None)
        character_registry.clear()


@patch("mud.combat.engine.saves_spell")
def test_fight_017_worn_off_message_goes_to_attacker_not_victim(mock_saves):
    """ROM src/fight.c:633-635 — act(..., ch, wield, NULL, TO_CHAR): the
    "worn off" line goes to the wielder when level hits 0."""
    mock_saves.return_value = True
    vnum = 2104
    try:
        attacker, victim = _setup(vnum, weapon_level=2)
        weapon = attacker.wielded_weapon
        weapon.affected.append(_envenom(level=2, duration=5))  # level 2 -> 0

        attacker.messages = []
        victim.messages = []
        process_weapon_special_attacks(attacker, victim)

        worn = "The poison on the venom blade has worn off."
        assert worn in attacker.messages, f"attacker missing worn-off msg: {attacker.messages}"
        assert worn not in victim.messages, "worn-off msg leaked to victim"
    finally:
        room_registry.pop(vnum, None)
        character_registry.clear()


@patch("mud.combat.engine.saves_spell")
def test_fight_017_worn_off_fires_when_duration_hits_zero(mock_saves):
    """ROM src/fight.c:633 — `level == 0 || duration == 0`: a duration-driven
    expiry also fires the worn-off message even if level is still positive."""
    mock_saves.return_value = True
    vnum = 2105
    try:
        attacker, victim = _setup(vnum, weapon_level=2)
        weapon = attacker.wielded_weapon
        weapon.affected.append(_envenom(level=10, duration=1))  # duration 1 -> 0

        attacker.messages = []
        process_weapon_special_attacks(attacker, victim)

        env = weapon.affected[0]
        assert env.level == 8, "level should still be positive"
        assert env.duration == 0, "duration should hit zero"
        worn = "The poison on the venom blade has worn off."
        assert worn in attacker.messages, "worn-off msg not fired on duration==0"
    finally:
        room_registry.pop(vnum, None)
        character_registry.clear()
