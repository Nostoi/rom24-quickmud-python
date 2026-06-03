"""FIGHT-033 — WEAPON_FROST/SHOCKING victim TO_CHAR lines drop the $p weapon name.

ROM src/fight.c:664 act("The cold touch of $p surrounds you with ice.", victim, wield, NULL, TO_CHAR)
ROM src/fight.c:675 act("You are shocked by $p.", victim, wield, NULL, TO_CHAR)

Python previously emitted:
  FROST:   "The cold touch surrounds you with ice."     — missing "$p"
  SHOCKING: "You are shocked by the weapon."             — "the weapon" instead of "$p"

Both now render the weapon's short_descr via $p.
"""

from __future__ import annotations

from unittest.mock import patch

from mud.combat.engine import process_weapon_special_attacks
from mud.models.character import character_registry
from mud.models.constants import WEAPON_FROST, WEAPON_SHOCKING
from mud.models.room import Room
from mud.registry import room_registry
from mud.world.world_state import create_test_character


class _MockWeapon:
    def __init__(self, name: str, level: int, flags: int) -> None:
        self.name = name
        self.short_descr = name
        self.level = level
        self.weapon_flags = flags


def _setup(vnum: int, weapon_flags: int):
    test_room = Room(
        vnum=vnum,
        name="Test Room",
        description="A test room.",
        room_flags=0,
        sector_type=0,
    )
    test_room.people = []
    test_room.contents = []
    room_registry[vnum] = test_room

    attacker = create_test_character("Attaq", vnum)
    attacker.level = 20
    weapon = _MockWeapon("the icy blade", level=10, flags=weapon_flags)
    attacker.wielded_weapon = weapon

    victim = create_test_character("Alice", vnum)
    victim.level = 10

    return test_room, attacker, victim


def _cleanup(vnum: int):
    room_registry.pop(vnum, None)
    character_registry.clear()


class TestFrostVictimLine:
    """FIGHT-033 — WEAPON_FROST TO_CHAR victim line includes weapon name."""

    @patch("mud.combat.engine.shock_effect")
    @patch("mud.combat.engine.cold_effect")
    @patch("mud.combat.engine.rng_mm")
    def test_frost_victim_line_includes_weapon_name(self, mock_rng, mock_cold, mock_shock):
        """ROM src/fight.c:664 — '$p' renders weapon short_descr."""
        # mirrors ROM src/fight.c:664 act("The cold touch of $p surrounds you with ice.", …, TO_CHAR)
        mock_rng.number_range.return_value = 3  # frost damage
        room, attacker, victim = _setup(5000, WEAPON_FROST)
        try:
            victim.messages = []
            process_weapon_special_attacks(attacker, victim)

            joined = "\n".join(victim.messages).lower()
            # Old Python wording missing the weapon name:
            # "The cold touch surrounds you with ice."
            # ROM: "The cold touch of {weapon_name} surrounds you with ice."
            assert "cold touch of the icy blade" in joined, (
                f"FROST victim line missing weapon name $p: {victim.messages!r}"
            )
            # Old wording must be gone
            assert "cold touch surrounds you" not in joined, (
                f"Old wording 'The cold touch surrounds you' still present: {victim.messages!r}"
            )
        finally:
            _cleanup(5000)


class TestShockingVictimLine:
    """FIGHT-033 — WEAPON_SHOCKING TO_CHAR victim line includes weapon name."""

    @patch("mud.combat.engine.shock_effect")
    @patch("mud.combat.engine.cold_effect")
    @patch("mud.combat.engine.rng_mm")
    def test_shocking_victim_line_includes_weapon_name(self, mock_rng, mock_cold, mock_shock):
        """ROM src/fight.c:675 — '$p' renders weapon short_descr."""
        # mirrors ROM src/fight.c:675 act("You are shocked by $p.", …, TO_CHAR)
        mock_rng.number_range.return_value = 3  # shock damage
        room, attacker, victim = _setup(5001, WEAPON_SHOCKING)
        try:
            victim.messages = []
            process_weapon_special_attacks(attacker, victim)

            joined = "\n".join(victim.messages).lower()
            # Old Python wording: "You are shocked by the weapon."
            # ROM: "You are shocked by {weapon_name}."
            assert "shocked by the icy blade" in joined, (
                f"SHOCKING victim line missing weapon name $p: {victim.messages!r}"
            )
            # Old wording must be gone
            assert "shocked by the weapon" not in joined, (
                f"Old wording 'You are shocked by the weapon' still present: {victim.messages!r}"
            )
        finally:
            _cleanup(5001)
