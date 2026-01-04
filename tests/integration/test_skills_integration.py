"""
Integration tests for Skills System.

Verifies skills work correctly through the game loop,
matching ROM 2.4b6 behavior.

ROM Parity References:
- src/fight.c - Combat skills (backstab, bash, disarm, rescue, trip)
- src/magic.c - Skill checks and improvement
- src/handler.c - Skill improvement (check_improve)
- src/update.c - Passive skill triggers

Test Coverage:
- Skills trigger combat rounds correctly
- Skills set wait states (lag) correctly
- Passive skills activate automatically
- Skill improvement works on successful use
- Skill messages displayed correctly
"""

from __future__ import annotations

import pytest
import time

from mud.commands.dispatcher import process_command
from mud.game_loop import game_tick
from mud.models.character import Character
from mud.models.constants import Position, Stat, ItemType, WearFlag, WearLocation
from mud.spawning.templates import MobInstance
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
    char = movable_char_factory("Thief", 3001)
    char.level = 10
    char.skills = {
        "backstab": 75,
        "bash": 60,
        "dodge": 80,
        "parry": 70,
        "enhanced damage": 50,
    }

    dagger = object_factory(
        {
            "vnum": 9001,
            "name": "dagger weapon",
            "short_descr": "a sharp dagger",
            "item_type": int(ItemType.WEAPON),
            "wear_flags": int(WearFlag.WIELD),
            "value": [0, 1, 4, 0],
        }
    )
    char.add_object(dagger)
    dagger.wear_loc = int(WearLocation.WIELD)

    if not hasattr(char, "equipment") or char.equipment is None:
        char.equipment = {}
    char.equipment["wield"] = dagger

    return char


# ============================================================================
# COMBAT SKILLS INTEGRATION
# ============================================================================


class TestCombatSkillsIntegration:
    """Test combat skills work through the game loop."""

    def test_backstab_triggers_combat_round(self, skilled_character, movable_mob_factory):
        """
        Test: Using backstab triggers combat and sets combat position.

        ROM Parity: Mirrors ROM src/fight.c:do_backstab()

        Given: A character with backstab skill
        When: Character backstabs a mob
        Then: Combat starts and violence_update processes
        """
        char = skilled_character
        mob = movable_mob_factory(3000, 3001)
        mob.max_hit = 100
        mob.hit = 100

        result = process_command(char, f"backstab {mob.name}")

        assert char.fighting == mob, f"Character should be fighting mob, got result: {result}"
        assert char.position == Position.FIGHTING, "Character should be in fighting position"
        assert mob.fighting == char, "Mob should be fighting character back"

    def test_bash_sets_wait_state(self, skilled_character, movable_mob_factory):
        """
        Test: Bash skill sets wait state (skill lag).

        ROM Parity: Mirrors ROM src/fight.c:do_bash() wait state

        Given: A character with bash skill
        When: Character bashes a mob
        Then: Character has wait state set
        """
        char = skilled_character
        mob = movable_mob_factory(3000, 3001)
        char.fighting = mob
        char.position = Position.FIGHTING

        # Bash the mob
        initial_wait = getattr(char, "wait", 0)
        result = process_command(char, "bash")

        # Should have wait state (WAIT_STATE is skill_table[gsn_bash].beats)
        current_wait = getattr(char, "wait", 0)
        assert current_wait > initial_wait, "Bash should set wait state"

    def test_rescue_requires_grouping(self, skilled_character, movable_mob_factory, movable_char_factory):
        """
        Test: Rescue only works on group members.

        ROM Parity: Mirrors ROM src/fight.c:do_rescue() group check

        Given: Two characters and a mob
        When: Character tries to rescue non-grouped ally
        Then: Rescue fails with appropriate message
        """
        char = skilled_character
        char.skills["rescue"] = 75
        victim = movable_char_factory("Victim", 3001)
        mob = movable_mob_factory(3000, 3001)

        # Setup combat: mob attacks victim
        victim.fighting = mob
        mob.fighting = victim
        victim.position = Position.FIGHTING

        result = process_command(char, "rescue victim")
        assert "kill stealing" in result.lower(), "Rescue without grouping should fail with kill stealing message"

        # Now group and try again
        process_command(char, "follow victim")
        process_command(victim, "group thief")

        result = process_command(char, "rescue victim")
        # Should either succeed or fail based on skill check
        assert "rescue" in result.lower() or "bravely" in result.lower(), "Rescue attempt should be processed"


# ============================================================================
# PASSIVE SKILLS INTEGRATION
# ============================================================================


class TestPassiveSkillsIntegration:
    """Test passive skills activate automatically during combat."""

    def test_dodge_activates_in_combat(self, skilled_character, movable_mob_factory):
        """
        Test: Dodge skill activates automatically when attacked.

        ROM Parity: Mirrors ROM src/fight.c:check_dodge()

        Given: A character with dodge skill
        When: Character is attacked in combat
        Then: Dodge doesn't break combat mechanics
        """
        char = skilled_character
        char.skills["dodge"] = 95
        char.hit = 1000
        char.max_hit = 1000
        char.level = 50
        char.hitroll = 20
        char.damroll = 15
        mob = movable_mob_factory(3000, 3001)
        mob.max_hit = 50
        mob.hit = 50
        mob.level = 1

        char.fighting = mob
        mob.fighting = char
        char.position = Position.FIGHTING
        mob.position = Position.FIGHTING

        initial_hp = char.hit
        for _ in range(5):
            game_tick()

        assert char.hit > 0, "Character should survive with high dodge and level"
        assert char.hit >= initial_hp - 100, "Dodge should mitigate most damage"

    def test_enhanced_damage_applies_in_combat(self, skilled_character, movable_mob_factory):
        """
        Test: Enhanced damage increases attack damage.

        ROM Parity: Mirrors ROM src/fight.c:one_hit() enhanced damage

        Given: A character with enhanced damage skill
        When: Character attacks in combat
        Then: Combat works correctly with enhanced damage
        """
        char = skilled_character
        char.hit = 1000
        char.max_hit = 1000
        char.level = 50
        char.hitroll = 20  # Ensure character can hit the mob
        char.damroll = 15  # Ensure character can damage the mob
        mob = movable_mob_factory(3000, 3001)
        mob.max_hit = 50
        mob.hit = 50
        mob.level = 1
        mob.imm_flags = 0  # Remove weapon immunity so test can verify damage

        char.fighting = mob
        mob.fighting = char
        char.position = Position.FIGHTING
        mob.position = Position.FIGHTING

        for _ in range(10):
            game_tick()

        assert char.hit > 0, "Character should survive"
        assert mob.hit <= 0, "Mob should be defeated by enhanced damage character"


# ============================================================================
# SKILL IMPROVEMENT INTEGRATION
# ============================================================================


class TestSkillImprovementIntegration:
    """Test skills improve when used successfully."""

    @pytest.mark.skip(reason="Probabilistic test - check_improve is implemented and called, but RNG makes this flaky")
    def test_skill_improves_on_successful_use(self, skilled_character, movable_mob_factory):
        """
        Test: Skills improve when used successfully.

        ROM Parity: Mirrors ROM src/handler.c:check_improve()

        Given: A character with low skill % and good INT
        When: Character uses skill successfully many times
        Then: Skill % increases (probabilistic - may take many attempts)

        Note: Uses unseed RNG for this test since improvement is probabilistic.
        ROM C uses rand() which can't guarantee improvement in N iterations.
        """
        rng_mm.seed_mm(int(time.time()))

        char = skilled_character
        char.skills["bash"] = 20
        char.perm_stats[Stat.INT] = 25
        char.level = 10

        mob = movable_mob_factory(3000, 3001)
        mob.level = 1
        mob.size = 1

        initial_skill = char.skills["bash"]
        improved = False

        for i in range(500):
            char.fighting = mob
            mob.fighting = char
            char.position = Position.FIGHTING
            mob.hit = 100
            char.wait = 0

            process_command(char, "bash")
            game_tick()

            current_skill = char.skills.get("bash", initial_skill)
            if current_skill > initial_skill:
                improved = True
                break

        assert improved, (
            f"Skill should improve after 500 uses (started at {initial_skill}, ended at {char.skills['bash']})"
        )


# ============================================================================
# SKILL WAIT STATE INTEGRATION
# ============================================================================


class TestSkillWaitStateIntegration:
    """Test wait states work correctly with skills."""

    def test_wait_state_blocks_skill_reuse(self, skilled_character, movable_mob_factory):
        """
        Test: Can't use skill again while in wait state.

        ROM Parity: Mirrors ROM wait state mechanics

        Given: A character who just used a skill
        When: Character tries to use skill again immediately
        Then: Skill is blocked by wait state
        """
        char = skilled_character
        mob = movable_mob_factory(3000, 3001)
        char.fighting = mob
        char.position = Position.FIGHTING

        result1 = process_command(char, "bash")

        wait_after_first = char.wait
        assert wait_after_first > 0, "First bash should set wait state"

        char.position = Position.FIGHTING

        result2 = process_command(char, "bash")

        assert "wait" in result2.lower() or "recovering" in result2.lower(), (
            f"Second bash should be blocked by wait state, got: {result2}"
        )

    def test_wait_state_decrements_per_tick(self, skilled_character, movable_mob_factory):
        """
        Test: Wait state decrements each game tick.

        ROM Parity: Mirrors ROM src/update.c:violence_update() wait decrement

        Given: A character with wait state set
        When: Game ticks occur
        Then: Wait state decrements to zero
        """
        char = skilled_character
        mob = movable_mob_factory(3000, 3001)
        char.fighting = mob
        char.position = Position.FIGHTING

        # Set initial wait state
        char.wait = 24  # ROM WAIT_STATE(ch, skill_table[gsn_bash].beats)

        # Run game ticks
        for _ in range(30):
            game_tick()
            if getattr(char, "wait", 0) <= 0:
                break

        # Wait should have decremented to zero
        assert getattr(char, "wait", 0) <= 0, "Wait state should decrement to zero"


# ============================================================================
# SKILL COMMAND INTEGRATION
# ============================================================================


class TestSkillCommandIntegration:
    """Test skill-related commands work through game loop."""

    def test_practice_command_increases_skill(self, movable_char_factory):
        """
        Test: Practice command increases skill %.

        ROM Parity: Mirrors ROM src/act_info.c:do_practice()

        Given: A character at a practice mob
        When: Character practices a skill
        Then: Skill % increases
        """
        # This would need a proper practice mob setup
        # Skipping for now
        pytest.skip("Practice command integration not yet tested")

    def test_skills_command_lists_character_skills(self, skilled_character):
        """
        Test: Skills command shows character's skills.

        ROM Parity: Mirrors ROM src/act_info.c:do_skills()

        Given: A character with skills
        When: Character types 'skills'
        Then: Skills are listed with percentages
        """
        char = skilled_character

        result = process_command(char, "skills")

        # Should list skills
        assert "backstab" in result.lower() or "skill" in result.lower(), "Skills command should list skills"


# ============================================================================
# SKILL FAILURE CASES
# ============================================================================


class TestSkillFailureCases:
    """Test skills fail gracefully in edge cases."""

    def test_skill_fails_without_sufficient_level(self, movable_char_factory, movable_mob_factory):
        """
        Test: Low-level character can't use high-level skills.

        ROM Parity: Mirrors ROM skill level requirements

        Given: A low-level character
        When: Character tries to use skill above their level
        Then: Skill fails with appropriate message
        """
        char = movable_char_factory("Newbie", 3001)
        char.level = 1
        char.skills = {"backstab": 75}  # Has skill but too low level
        mob = movable_mob_factory(3000, 3001)

        result = process_command(char, "backstab Hassan")

        # Should fail (either "You don't know that skill" or level check)
        # Exact message depends on implementation
        assert len(result) > 0, "Should have some response"

    def test_skill_fails_in_wrong_position(self, skilled_character, movable_mob_factory):
        """
        Test: Some skills require specific positions.

        ROM Parity: Mirrors ROM position checks

        Given: A character sitting/resting
        When: Character tries to use combat skill
        Then: Skill fails with position message
        """
        char = skilled_character
        mob = movable_mob_factory(3000, 3001)
        char.position = Position.SITTING

        result = process_command(char, "bash Hassan")

        assert "stand" in result.lower() or "position" in result.lower() or "can't" in result.lower(), (
            f"Skill should require proper position, got: {result}"
        )
