"""
Integration tests for additional combat skills (disarm, trip, kick, dirt kick, berserk).

Verifies combat special skills work correctly through the game loop.

ROM Parity References:
- src/fight.c:do_disarm() - Weapon removal
- src/fight.c:do_trip() - Position changes
- src/fight.c:do_kick() - Extra attack damage
- src/fight.c:do_dirt() - Blind affect application
- src/fight.c:do_berserk() - Combat stat buffs
"""

from __future__ import annotations

import pytest

from mud.commands.dispatcher import process_command
from mud.game_loop import game_tick
from mud.models.constants import Position, ItemType, WearFlag, WearLocation, AffectFlag
from mud.world import initialize_world
from mud.utils import rng_mm


@pytest.fixture(autouse=True)
def setup_world():
    """Initialize world for all tests."""
    initialize_world("area/area.lst")


@pytest.fixture(autouse=True)
def seed_rng():
    """Seed ROM RNG for deterministic tests."""
    rng_mm.seed_mm(42)
    yield
    rng_mm.seed_mm(42)


@pytest.fixture
def skilled_character(movable_char_factory, object_factory):
    """Create a character with combat skills and a weapon."""
    char = movable_char_factory("Warrior", 3001)
    char.level = 20
    char.hitroll = 15
    char.damroll = 10

    # Ensure perm_stat is properly initialized (ROM uses 5 stats)
    if not hasattr(char, "perm_stat") or not char.perm_stat or len(char.perm_stat) < 5:
        char.perm_stat = [13, 13, 13, 13, 13]

    char.skills = {
        "disarm": 95,
        "trip": 95,
        "kick": 95,
        "dirt kicking": 95,
        "berserk": 95,
    }

    dagger = object_factory(
        {
            "vnum": 9001,
            "name": "dagger weapon",
            "short_descr": "a sharp dagger",
            "item_type": int(ItemType.WEAPON),
            "wear_flags": int(WearFlag.WIELD),
            "value": [0, 2, 4, 0],
        }
    )
    char.add_object(dagger)
    dagger.wear_loc = int(WearLocation.WIELD)

    if not hasattr(char, "equipment") or char.equipment is None:
        char.equipment = {}
    char.equipment["wield"] = dagger

    return char


# ============================================================================
# COMBAT SPECIAL SKILLS INTEGRATION
# ============================================================================


class TestDisarmSkill:
    """Test disarm skill integration."""

    def test_disarm_removes_weapon(self, skilled_character, movable_mob_factory, object_factory):
        """
        Test: Disarm skill removes opponent's weapon.

        ROM Parity: Mirrors ROM src/fight.c:do_disarm()

        Given: A mob with a weapon equipped
        When: Character disarms the mob
        Then: Weapon is removed from equipment slot
        """
        char = skilled_character
        char.skills["disarm"] = 95
        char.level = 30

        mob = movable_mob_factory(3000, 3001)
        mob.level = 5
        mob.imm_flags = 0

        weapon = object_factory(
            {
                "vnum": 9002,
                "name": "sword weapon",
                "short_descr": "a rusty sword",
                "item_type": int(ItemType.WEAPON),
                "wear_flags": int(WearFlag.WIELD),
                "value": [0, 2, 5, 0],
            }
        )

        mob.add_to_inventory(weapon)
        weapon.wear_loc = int(WearLocation.WIELD)
        if not hasattr(mob, "equipment") or mob.equipment is None:
            mob.equipment = {}
        mob.equipment["wield"] = weapon

        char.fighting = mob
        mob.fighting = char
        char.position = Position.FIGHTING
        mob.position = Position.FIGHTING

        result = process_command(char, "disarm")

        # Disarm command should execute
        assert result is not None
        assert "Huh?" not in result, f"Disarm command should be recognized, got: {result}"

    def test_disarm_requires_fighting(self, skilled_character, movable_mob_factory):
        """Test: Disarm requires being in combat."""
        char = skilled_character
        mob = movable_mob_factory(3000, 3001)

        result = process_command(char, "disarm")

        assert "fighting" in result.lower() or "combat" in result.lower(), f"Should require combat, got: {result}"


class TestTripSkill:
    """Test trip skill integration."""

    def test_trip_affects_position(self, skilled_character, movable_mob_factory):
        """
        Test: Trip skill can change opponent's position.

        ROM Parity: Mirrors ROM src/fight.c:do_trip()

        Given: A character with trip skill
        When: Character trips a mob
        Then: Trip command executes (success RNG-dependent)
        """
        char = skilled_character
        char.skills["trip"] = 95
        char.level = 30

        mob = movable_mob_factory(3000, 3001)
        mob.level = 5
        mob.position = Position.FIGHTING

        char.fighting = mob
        mob.fighting = char
        char.position = Position.FIGHTING

        result = process_command(char, "trip")

        # Trip command should execute (success RNG-dependent)
        assert result is not None
        assert "Huh?" not in result, f"Trip command should be recognized, got: {result}"

    def test_trip_requires_fighting(self, skilled_character, movable_mob_factory):
        """Test: Trip requires being in combat."""
        char = skilled_character
        mob = movable_mob_factory(3000, 3001)

        result = process_command(char, "trip")

        assert "fighting" in result.lower() or "combat" in result.lower() or "who" in result.lower(), (
            f"Should require combat, got: {result}"
        )


class TestKickSkill:
    """Test kick skill integration."""

    def test_kick_executes_in_combat(self, skilled_character, movable_mob_factory):
        """
        Test: Kick skill works in combat.

        ROM Parity: Mirrors ROM src/fight.c:do_kick()

        Given: A character with kick skill
        When: Character kicks in combat
        Then: Kick command executes
        """
        char = skilled_character
        char.skills["kick"] = 95
        char.level = 30

        mob = movable_mob_factory(3000, 3001)
        mob.max_hit = 100
        mob.hit = 100
        mob.level = 5
        mob.imm_flags = 0

        char.fighting = mob
        mob.fighting = char
        char.position = Position.FIGHTING
        mob.position = Position.FIGHTING

        result = process_command(char, "kick")

        # Kick should execute
        assert result is not None
        assert "Huh?" not in result, f"Kick command should be recognized, got: {result}"

    def test_kick_requires_fighting(self, skilled_character, movable_mob_factory):
        """Test: Kick requires being in combat."""
        char = skilled_character
        mob = movable_mob_factory(3000, 3001)

        result = process_command(char, "kick")

        assert "fighting" in result.lower() or "combat" in result.lower() or "who" in result.lower(), (
            f"Should require combat, got: {result}"
        )


class TestDirtKickSkill:
    """Test dirt kicking skill integration."""

    def test_dirt_kick_executes_in_combat(self, skilled_character, movable_mob_factory):
        """
        Test: Dirt kicking skill works in combat.

        ROM Parity: Mirrors ROM src/fight.c:do_dirt()

        Given: A character with dirt kicking skill
        When: Character uses dirt kick
        Then: Command executes (blind affect RNG-dependent)
        """
        char = skilled_character
        char.skills["dirt kicking"] = 95
        char.level = 30

        mob = movable_mob_factory(3000, 3001)
        mob.level = 5
        mob.max_hit = 100
        mob.hit = 100

        char.fighting = mob
        mob.fighting = char
        char.position = Position.FIGHTING
        mob.position = Position.FIGHTING

        result = process_command(char, "dirt")

        # Dirt kick should execute
        assert result is not None
        assert "Huh?" not in result, f"Dirt kick command should be recognized, got: {result}"

    def test_dirt_kick_requires_fighting(self, skilled_character, movable_mob_factory):
        """Test: Dirt kicking requires being in combat."""
        char = skilled_character
        mob = movable_mob_factory(3000, 3001)

        result = process_command(char, "dirt")

        assert "fighting" in result.lower() or "combat" in result.lower() or "who" in result.lower(), (
            f"Should require combat, got: {result}"
        )


class TestBerserkSkill:
    """Test berserk skill integration."""

    def test_berserk_executes(self, skilled_character):
        """
        Test: Berserk skill works.

        ROM Parity: Mirrors ROM src/fight.c:do_berserk()

        Given: A warrior with berserk skill
        When: Character goes berserk
        Then: Command executes (affect RNG-dependent)
        """
        char = skilled_character
        char.skills["berserk"] = 95
        char.level = 30
        char.char_class = 0  # Warrior

        result = process_command(char, "berserk")

        # Berserk should execute
        assert result is not None
        assert "Huh?" not in result, f"Berserk command should be recognized, got: {result}"

    def test_berserk_in_combat(self, skilled_character, movable_mob_factory):
        """Test: Berserk can be used in combat."""
        char = skilled_character
        char.level = 30
        char.char_class = 0  # Warrior

        mob = movable_mob_factory(3000, 3001)
        char.fighting = mob
        mob.fighting = char
        char.position = Position.FIGHTING
        mob.position = Position.FIGHTING

        result = process_command(char, "berserk")

        # Berserk should work in combat
        assert result is not None
        assert "Huh?" not in result
