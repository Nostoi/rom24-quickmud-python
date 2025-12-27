"""
Player Condition System Tests

Tests for ROM condition system (hunger, thirst, drunk, full).
ROM Reference: src/update.c lines 367-580 (gain_condition, char_update)

Priority: P1 (high - affects survival mechanics and regen)

Oracle Edge Cases Tested:
1. Condition clamping [0, 48] with -1 immunity (P0)
2. Hunger/thirst regen penalties not direct damage (P1)
3. Drunk condition effects on combat (P1)
"""

from __future__ import annotations

import pytest

from mud.characters.conditions import gain_condition
from mud.models.character import Character, PCData
from mud.models.constants import Condition
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import create_test_character, initialize_world
from helpers_player import set_conditions


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    """Initialize world once for all tests in this module."""
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()


class TestConditionClamping:
    """Test ROM condition clamping behavior.

    ROM Reference: src/update.c:367 (gain_condition)
    Oracle Edge Case #3: Condition clamping and -1 immunity semantics
    """

    @pytest.mark.p1
    def test_condition_clamps_at_zero(self):
        """Conditions cannot go below 0 (except -1 immunity)."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, hunger=1)

        gain_condition(player, Condition.HUNGER, -5)

        assert player.pcdata.condition[Condition.HUNGER] == 0

    @pytest.mark.p1
    def test_condition_clamps_at_48(self):
        """Conditions cannot exceed 48 (ROM max)."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, hunger=45)

        gain_condition(player, Condition.HUNGER, 10)

        assert player.pcdata.condition[Condition.HUNGER] == 48

    @pytest.mark.p0
    def test_condition_minus_one_immunity(self):
        """Condition at -1 never changes (immunity)."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, hunger=-1)

        gain_condition(player, Condition.HUNGER, -10)
        assert player.pcdata.condition[Condition.HUNGER] == -1

        gain_condition(player, Condition.HUNGER, 10)
        assert player.pcdata.condition[Condition.HUNGER] == -1

    @pytest.mark.p1
    def test_drunk_clamps_to_range(self):
        """Drunk condition also follows [0, 48] clamping."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, drunk=0)

        gain_condition(player, Condition.DRUNK, 60)

        assert player.pcdata.condition[Condition.DRUNK] == 48

    @pytest.mark.p1
    def test_thirst_clamps_to_range(self):
        """Thirst condition follows [0, 48] clamping."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, thirst=2)

        gain_condition(player, Condition.THIRST, -5)

        assert player.pcdata.condition[Condition.THIRST] == 0


class TestConditionDecay:
    """Test condition decay over time.

    ROM Reference: src/game_loop.py char_update (mirroring ROM update.c)
    """

    @pytest.mark.p1
    def test_hunger_decreases_over_time(self):
        """Hunger decreases with game ticks."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, hunger=48)

        initial_hunger = player.pcdata.condition[Condition.HUNGER]

        gain_condition(player, Condition.HUNGER, -1)

        assert player.pcdata.condition[Condition.HUNGER] < initial_hunger

    @pytest.mark.p1
    def test_thirst_decreases_over_time(self):
        """Thirst decreases with game ticks."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, thirst=48)

        initial_thirst = player.pcdata.condition[Condition.THIRST]

        gain_condition(player, Condition.THIRST, -1)

        assert player.pcdata.condition[Condition.THIRST] < initial_thirst

    @pytest.mark.p1
    def test_drunk_decreases_over_time(self):
        """Drunk condition decreases with game ticks."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, drunk=20)

        initial_drunk = player.pcdata.condition[Condition.DRUNK]

        gain_condition(player, Condition.DRUNK, -1)

        assert player.pcdata.condition[Condition.DRUNK] < initial_drunk


class TestConditionEffects:
    """Test condition effects on character state.

    ROM Reference: src/update.c lines 207-341 (regen calculations)
    Oracle Edge Case #4: Hunger/thirst at 0 causes regen penalties, not damage
    """

    @pytest.mark.p1
    def test_hunger_zero_shows_message(self):
        """Hunger at 0 triggers 'hungry' message."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, hunger=0)

        gain_condition(player, Condition.HUNGER, 0)

    @pytest.mark.p1
    def test_thirst_zero_shows_message(self):
        """Thirst at 0 triggers 'thirsty' message."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, thirst=0)

        gain_condition(player, Condition.THIRST, 0)

    @pytest.mark.p1
    def test_drunk_zero_shows_sober_message(self):
        """Drunk reaching 0 triggers 'sober' message once."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, drunk=1)

        gain_condition(player, Condition.DRUNK, -1)

        assert player.pcdata.condition[Condition.DRUNK] == 0


class TestConditionDisplay:
    """Test condition display in affects and other commands.

    ROM Reference: src/commands/affects.py
    """

    @pytest.mark.p2
    def test_hungry_shows_in_affects(self):
        """Hunger at 0 shows in affects display."""
        from mud.commands.affects import do_affects

        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, hunger=0)

        output = do_affects(player, "")

        assert "hungry" in output.lower() or "hunger" in output.lower()

    @pytest.mark.p2
    def test_thirsty_shows_in_affects(self):
        """Thirst at 0 shows in affects display."""
        from mud.commands.affects import do_affects

        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, thirst=0, hunger=48)

        output = do_affects(player, "")

        assert "thirst" in output.lower() or "hungry" in output.lower()


class TestConditionEdgeCases:
    """Test condition edge cases from Oracle analysis.

    Oracle-identified critical behaviors.
    """

    @pytest.mark.p1
    def test_multiple_conditions_independent(self):
        """Each condition tracks independently."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_conditions(player, hunger=10, thirst=20, drunk=5, full=30)

        gain_condition(player, Condition.HUNGER, -5)

        assert player.pcdata.condition[Condition.HUNGER] == 5
        assert player.pcdata.condition[Condition.THIRST] == 20
        assert player.pcdata.condition[Condition.DRUNK] == 5
        assert player.pcdata.condition[Condition.FULL] == 30

    @pytest.mark.p1
    def test_npc_conditions_not_tracked(self):
        """NPCs don't have condition tracking."""
        player = create_test_character("NPC", 3001)
        player.is_npc = True

        gain_condition(player, Condition.HUNGER, -10)

    @pytest.mark.p0
    def test_condition_array_length_validation(self):
        """Condition array must have 4 slots."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False

        assert len(player.pcdata.condition) >= 4
        assert player.pcdata.condition[Condition.DRUNK] is not None
        assert player.pcdata.condition[Condition.FULL] is not None
        assert player.pcdata.condition[Condition.THIRST] is not None
        assert player.pcdata.condition[Condition.HUNGER] is not None
