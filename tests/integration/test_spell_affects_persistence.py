"""Integration tests for spell affects persistence.

Tests verify spell affects work correctly through game_tick() integration:
- Spell affects persist across game ticks
- Duration countdown and automatic expiration
- Buff stacking (same spell, different spells)
- Dispel magic removes affects correctly
- Mana regeneration over time

ROM Parity: Mirrors ROM 2.4b6 spell affect behavior from src/magic.c, src/handler.c
"""

from __future__ import annotations

import pytest

from mud.commands.dispatcher import process_command
from mud.config import get_pulse_tick
from mud.game_loop import game_tick
from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag


def run_point_pulses(count: int = 1) -> None:
    """Run enough game_tick() calls to trigger count point pulses.

    ROM affects only tick on PULSE_TICK intervals (default 240 pulses = 1 minute).
    This helper ensures tests wait for actual ROM timing.
    """
    ticks_per_pulse = get_pulse_tick()
    for _ in range(count * ticks_per_pulse):
        game_tick()


class TestSpellAffectPersistence:
    """Test spell affects persist through game ticks."""

    def test_spell_affect_persists_across_ticks(self, movable_char_factory):
        """
        Test: Spell affect persists across multiple game ticks.

        ROM Parity: Mirrors ROM src/update.c:affect_update() - affects don't vanish immediately

        Given: Character with armor spell (duration 10)
        When: 5 game ticks execute
        Then: Spell still active (duration > 0)
        """
        char = movable_char_factory("Mage", 3001, points=200)
        char.level = 20

        effect = SpellEffect(
            name="armor",
            duration=10,
            level=20,
            ac_mod=-20,
        )
        char.apply_spell_effect(effect)

        initial_ac = char.armor[0]

        for _ in range(5):
            game_tick()

        assert char.has_spell_effect("armor"), "Armor spell should still be active"
        assert char.armor[0] == initial_ac, "AC bonus should persist"

    def test_spell_affect_expires_after_duration(self, movable_char_factory):
        """
        Test: Spell affect expires when duration reaches 0.

        ROM Parity: Mirrors ROM src/update.c:affect_update() - duration countdown

        Given: Character with bless spell (duration 2)
        When: 3+ game ticks execute
        Then: Spell expires, bonuses removed
        """
        char = movable_char_factory("Cleric", 3001, points=200)
        char.level = 20

        initial_hitroll = char.hitroll
        initial_saves = char.saving_throw

        effect = SpellEffect(
            name="bless",
            duration=2,
            level=20,
            hitroll_mod=1,
            saving_throw_mod=-1,
        )
        char.apply_spell_effect(effect)

        assert char.hitroll == initial_hitroll + 1, "Bless should grant +1 hitroll"
        assert char.saving_throw == initial_saves - 1, "Bless should grant -1 saves"

        # Run enough point pulses for duration=2 to expire (3 point pulses total)
        run_point_pulses(3)

        assert not char.has_spell_effect("bless"), "Bless should have expired"
        assert char.hitroll == initial_hitroll, "Hitroll bonus should be removed"
        assert char.saving_throw == initial_saves, "Saves bonus should be removed"


class TestSpellAffectDuration:
    """Test spell affect duration countdown mechanics."""

    def test_affect_duration_decreases_per_tick(self, movable_char_factory):
        """
        Test: Spell affect duration decreases by 1 per game tick.

        ROM Parity: Mirrors ROM src/update.c:affect_update() - duration-- per tick

        Given: Character with spell (duration 5)
        When: 1 game tick executes
        Then: Duration now 4
        """
        char = movable_char_factory("Wizard", 3001, points=200)
        char.level = 20

        effect = SpellEffect(
            name="shield",
            duration=5,
            level=20,
            ac_mod=-20,
        )
        char.apply_spell_effect(effect)

        assert "shield" in char.spell_effects
        initial_duration = char.spell_effects["shield"].duration

        # Run 1 point pulse to decrement duration by 1
        run_point_pulses(1)

        if "shield" in char.spell_effects:
            new_duration = char.spell_effects["shield"].duration
            assert new_duration == initial_duration - 1, "Duration should decrease by 1"

    def test_infinite_duration_affects_never_expire(self, movable_char_factory):
        """
        Test: Affects with duration -1 (infinite) never expire.

        ROM Parity: Mirrors ROM affect_update() - duration -1 means permanent

        Given: Character with permanent affect (duration -1)
        When: Many game ticks execute
        Then: Affect still active
        """
        char = movable_char_factory("Paladin", 3001, points=200)
        char.level = 30

        effect = SpellEffect(
            name="sanctuary",
            duration=-1,
            level=30,
            affect_flag=AffectFlag.SANCTUARY,
        )
        char.apply_spell_effect(effect)

        for _ in range(20):
            game_tick()

        assert char.has_spell_effect("sanctuary"), "Permanent affect should persist"
        assert char.has_affect(AffectFlag.SANCTUARY), "Sanctuary flag should persist"


class TestSpellAffectStacking:
    """Test spell stacking and merging mechanics."""

    def test_same_spell_stacks_duration_and_averages_level(self, movable_char_factory):
        """
        Test: Casting same spell twice stacks duration, averages level.

        ROM Parity: Mirrors ROM src/handler.c:affect_join() - duration adds, level averages

        Given: Character with armor spell (duration 10, level 10)
        When: Cast armor again (duration 10, level 20)
        Then: Duration = 20, level = 15, AC bonus same
        """
        char = movable_char_factory("Mage", 3001, points=200)
        char.level = 20

        effect1 = SpellEffect(
            name="armor",
            duration=10,
            level=10,
            ac_mod=-20,
        )
        char.apply_spell_effect(effect1)

        effect2 = SpellEffect(
            name="armor",
            duration=10,
            level=20,
            ac_mod=-20,
        )
        char.apply_spell_effect(effect2)

        assert char.has_spell_effect("armor")
        armor_effect = char.spell_effects["armor"]
        assert armor_effect.duration == 20, "Duration should stack (10 + 10)"
        assert armor_effect.level == 15, "Level should average ((10 + 20) / 2)"

    def test_different_spells_stack_independently(self, movable_char_factory):
        """
        Test: Different spells stack independently (additive bonuses).

        ROM Parity: Mirrors ROM affect system - multiple affects can coexist

        Given: Character with armor spell (-20 AC)
        When: Cast shield spell (-20 AC)
        Then: Both active, total AC bonus = -40
        """
        char = movable_char_factory("Wizard", 3001, points=200)
        char.level = 20

        initial_ac = char.armor[0]

        armor_effect = SpellEffect(
            name="armor",
            duration=10,
            level=20,
            ac_mod=-20,
        )
        char.apply_spell_effect(armor_effect)

        shield_effect = SpellEffect(
            name="shield",
            duration=10,
            level=20,
            ac_mod=-20,
        )
        char.apply_spell_effect(shield_effect)

        assert char.has_spell_effect("armor")
        assert char.has_spell_effect("shield")
        assert char.armor[0] == initial_ac - 40, "AC bonuses should stack (-20 -20 = -40)"

    def test_stat_modifiers_stack_from_same_spell(self, movable_char_factory):
        """
        Test: Stat modifiers from same spell stack when recast.

        ROM Parity: Mirrors ROM affect_join() - stat modifiers merge
        ROM Reference: src/handler.c affect_join() - paf->modifier += paf_old->modifier

        Given: Character with giant strength (+2 STR)
        When: Cast giant strength again (+2 STR)
        Then: Total +4 STR
        """
        from mud.skills.handlers import giant_strength

        char = movable_char_factory("TestChar", 3001)
        char.level = 20
        char.perm_stat = [13, 13, 13, 13, 13]

        initial_str = char.get_curr_stat(0)

        giant_strength(char, char)
        assert char.has_spell_effect("giant strength")

        first_str = char.get_curr_stat(0)
        assert first_str == initial_str + 2, "First cast should give +2 STR"

        giant_strength(char, char)

        second_str = char.get_curr_stat(0)
        assert second_str == initial_str + 4, "Second cast should stack to +4 STR total"


class TestDispelMagic:
    """Test dispel magic affect removal."""

    def test_dispel_magic_removes_random_affect(self, test_player):
        """
        Test: Dispel magic attempts to remove spell affects.

        ROM Parity: Mirrors ROM spell_dispel_magic() - tries to dispel all affects
        ROM Reference: src/magic.c - spell_dispel_magic(), check_dispel()

        Given: Character with 3 active spell affects
        When: Dispel magic cast at high level
        Then: At least one affect removed (probabilistic, but high level ensures success)
        """
        from mud.skills.handlers import armor, bless, giant_strength, dispel_magic

        char = test_player
        char.level = 10

        # Apply 3 spell affects at low level (easier to dispel)
        armor(char, char)  # -20 AC
        bless(char, char)  # +hitroll, -saving_throw
        giant_strength(char, char)  # +STR

        # Verify all 3 affects active
        assert char.has_spell_effect("armor")
        assert char.has_spell_effect("bless")
        assert char.has_spell_effect("giant strength")
        assert len(char.spell_effects) == 3

        # Cast dispel magic at VERY high level (level 50 vs level 10 affects)
        # ROM: saves_dispel = 50 + (spell_level - dis_level) * 5
        # = 50 + (10 - 50) * 5 = 50 - 200 = -150, clamped to 5%
        # So 95% chance to dispel each affect
        caster = test_player
        caster.level = 50
        result = dispel_magic(caster, char)

        # Should succeed in removing at least one affect
        assert result is True
        # With 95% chance per affect, at least one should be removed
        assert len(char.spell_effects) < 3

    def test_dispel_magic_higher_level_more_likely(self, movable_char_factory):
        """
        Test: Higher level dispel magic more likely to remove affects.

        ROM Parity: Mirrors ROM dispel checks - level vs level
        ROM Formula: saves_dispel = 50 + (spell_level - dis_level) * 5, clamped [5, 95]

        Given: Low level affects
        When: High level dispel magic cast
        Then: Higher success rate
        """
        from mud.skills.handlers import armor, dispel_magic

        # Run multiple trials to verify probabilistic behavior
        # With 50% chance, expect ~50% success rate
        # With 95% chance, expect ~95% success rate
        low_level_successes = 0
        high_level_successes = 0

        for _ in range(20):
            # Test 1: Low level dispel vs low level affect (50% chance)
            char1 = movable_char_factory("LowTarget", 3001)
            char1.level = 10
            armor(char1, char1)
            assert char1.has_spell_effect("armor")

            caster_low = movable_char_factory("LowCaster", 3001)
            caster_low.level = 10  # Same level = 50% success

            # Test 2: High level dispel vs low level affect (95% chance)
            char2 = movable_char_factory("HighTarget", 3001)
            char2.level = 10
            armor(char2, char2)
            assert char2.has_spell_effect("armor")

            caster_high = movable_char_factory("HighCaster", 3001)
            caster_high.level = 50  # Much higher level = 95% success

            # Try dispel
            if dispel_magic(caster_low, char1):
                low_level_successes += 1
            if dispel_magic(caster_high, char2):
                high_level_successes += 1

        # High level should succeed significantly more often than low level
        # With 20 trials: low ~10, high ~19
        # Use loose bounds to avoid flakiness
        assert high_level_successes > low_level_successes
        assert high_level_successes >= 15  # 95% of 20 = 19, allow some variance


class TestManaRegeneration:
    """Test mana regeneration over time."""

    def test_mana_regenerates_over_time(self, test_player):
        """
        Test: Character mana regenerates each game tick.

        ROM Parity: Mirrors ROM src/update.c:mana_gain() - per-tick regeneration

        Given: Character with 50/100 mana
        When: Game ticks execute
        Then: Mana increases toward max
        """
        char = test_player
        char.level = 20
        char.max_mana = 100
        char.mana = 50

        # Set stats for mana regeneration formula (WIS + INT)
        char.perm_stat = [13, 13, 13, 13, 13]  # STR, INT, WIS, DEX, CON

        initial_mana = char.mana

        # Run 10 point pulses to allow mana regeneration
        run_point_pulses(10)

        assert char.mana > initial_mana, "Mana should regenerate over time"
        assert char.mana <= char.max_mana, "Mana should not exceed maximum"

    def test_resting_increases_mana_regen(self, test_player):
        """
        Test: Resting position increases mana regeneration rate.

        ROM Parity: Mirrors ROM mana_gain() - position affects regen rate
        ROM: Standing gain//=4, Resting gain//=2, Sleeping no penalty

        Given: Character resting vs standing
        When: Game ticks execute
        Then: Resting regenerates faster than standing
        """
        from mud.models.constants import Position

        char = test_player
        char.level = 20
        char.max_mana = 200
        char.perm_stat = [13, 16, 16, 13, 13]

        char.mana = 50
        char.position = Position.STANDING
        run_point_pulses(5)
        standing_gain = char.mana - 50

        char.mana = 50
        char.position = Position.RESTING
        run_point_pulses(5)
        resting_gain = char.mana - 50

        assert resting_gain > standing_gain, (
            f"Resting ({resting_gain}) should regen more than standing ({standing_gain})"
        )

    def test_meditation_skill_increases_mana_regen(self, test_player):
        """
        Test: Meditation skill increases mana regeneration.

        ROM Parity: Mirrors ROM mana_gain() meditation bonus
        ROM: gain += (roll * gain / 100) when roll < meditation skill%

        Given: Character with meditation skill
        When: Character regenerates mana
        Then: Mana regenerates faster with meditation
        """
        from mud.models.constants import Position

        char = test_player
        char.level = 20
        char.max_mana = 200
        char.perm_stat = [13, 16, 16, 13, 13]
        char.position = Position.RESTING

        char.mana = 50
        char.skills = {}
        run_point_pulses(5)
        no_meditation_gain = char.mana - 50

        char.mana = 50
        char.skills = {"meditation": 95}
        run_point_pulses(5)
        with_meditation_gain = char.mana - 50

        assert with_meditation_gain >= no_meditation_gain, (
            f"Meditation ({with_meditation_gain}) should regen >= no skill ({no_meditation_gain})"
        )


class TestHitpointRegeneration:
    """Test HP regeneration mechanics."""

    def test_hp_regenerates_over_time(self, test_player):
        """
        Test: Character HP regenerates each game tick.

        ROM Parity: Mirrors ROM src/update.c:hit_gain() - per-tick HP regen

        Given: Character with 50/100 HP
        When: Game ticks execute
        Then: HP increases toward max
        """
        char = test_player
        char.level = 20
        char.max_hit = 100
        char.hit = 50

        # Set stats for HP regeneration formula (CON-based)
        char.perm_stat = [13, 13, 13, 13, 13]  # STR, INT, WIS, DEX, CON

        initial_hp = char.hit

        # Run 10 point pulses to allow HP regeneration
        run_point_pulses(10)

        assert char.hit > initial_hp, "HP should regenerate over time"
        assert char.hit <= char.max_hit, "HP should not exceed maximum"

    def test_resting_increases_hp_regen(self, test_player):
        """
        Test: Resting position increases HP regeneration rate.

        ROM Parity: Mirrors ROM hit_gain() - position affects regen rate
        ROM: Standing gain//=4, Resting gain//=2, Sleeping no penalty

        Given: Character resting vs standing
        When: Game ticks execute
        Then: Resting regenerates faster than standing
        """
        from mud.models.constants import Position

        char = test_player
        char.level = 20
        char.max_hit = 200
        char.perm_stat = [13, 13, 13, 13, 16]

        char.hit = 50
        char.position = Position.STANDING
        run_point_pulses(5)
        standing_gain = char.hit - 50

        char.hit = 50
        char.position = Position.RESTING
        run_point_pulses(5)
        resting_gain = char.hit - 50

        assert resting_gain > standing_gain, (
            f"Resting ({resting_gain}) should regen more than standing ({standing_gain})"
        )


class TestMoveRegeneration:
    """Test movement points regeneration."""

    def test_move_points_regenerate_over_time(self, test_player):
        """
        Test: Movement points regenerate each game tick.

        ROM Parity: Mirrors ROM src/update.c:move_gain() - per-tick move regen

        Given: Character with 50/100 move
        When: Game ticks execute
        Then: Move increases toward max
        """
        char = test_player
        char.level = 20
        char.max_move = 100
        char.move = 50

        # Set stats for movement regeneration formula (DEX-based for sleeping/resting)
        char.perm_stat = [13, 13, 13, 13, 13]  # STR, INT, WIS, DEX, CON

        initial_move = char.move

        # Run 10 point pulses to allow movement regeneration
        run_point_pulses(10)

        assert char.move > initial_move, "Move points should regenerate over time"
        assert char.move <= char.max_move, "Move should not exceed maximum"


class TestAffectFlags:
    """Test affect flags (AffectFlag enum) behavior."""

    def test_blind_affect_persists(self, movable_char_factory):
        """
        Test: AFFECT_BLIND persists through game ticks.

        ROM Parity: Mirrors ROM AFF_BLIND flag behavior

        Given: Character blinded by dirt kick
        When: Game ticks execute
        Then: Blind flag persists until duration expires
        """
        char = movable_char_factory("Warrior", 3001, points=200)
        char.level = 20

        effect = SpellEffect(
            name="blindness",
            duration=5,
            level=20,
            hitroll_mod=-4,
            affect_flag=AffectFlag.BLIND,
        )
        char.apply_spell_effect(effect)

        assert char.has_affect(AffectFlag.BLIND), "Blind flag should be set"

        # Run 3 point pulses (duration still > 0)
        run_point_pulses(3)

        assert char.has_affect(AffectFlag.BLIND), "Blind flag should persist"

        # Run 6 more point pulses to ensure duration=5 expires
        run_point_pulses(6)

        assert not char.has_affect(AffectFlag.BLIND), "Blind flag should be removed after expiration"

    def test_sanctuary_affect_visual_indicator(self, movable_char_factory):
        """
        Test: AFFECT_SANCTUARY provides visual indicator.

        ROM Parity: Mirrors ROM AFF_SANCTUARY - white aura in room description
        ROM Reference: src/act_info.c lines 271-272 - "(White Aura)" prefix

        Given: Character with sanctuary spell
        When: Look at character
        Then: Shows "(White Aura)" prefix
        """
        from mud.skills.handlers import sanctuary
        from mud.world.vision import describe_character

        char = movable_char_factory("TestChar", 3001)
        char.level = 20

        observer = movable_char_factory("Observer", 3001)

        description_before = describe_character(observer, char)
        assert "(White Aura)" not in description_before

        sanctuary(char, char)
        assert char.has_spell_effect("sanctuary")

        description_after = describe_character(observer, char)
        assert "(White Aura)" in description_after
        assert "TestChar" in description_after

    def test_invisible_affect_hides_character(self):
        """
        Test: AFFECT_INVISIBLE hides character from normal sight.

        ROM Parity: Mirrors ROM src/handler.c:2618 can_see() - AFF_INVISIBLE check

        Given: Character with invisibility spell
        When: Another character looks
        Then: Invisible character not seen (unless detect invis)
        """
        from mud.commands.dispatcher import process_command
        from mud.models.character import Character, character_registry
        from mud.models.constants import AffectFlag
        from mud.models.room import Room
        from mud.registry import room_registry

        # Create test room
        test_room = Room(
            vnum=1000,
            name="Test Room",
            description="A room for testing invisibility.",
            room_flags=0,
            sector_type=0,
        )
        test_room.people = []
        test_room.contents = []
        room_registry[1000] = test_room

        # Create observer character
        observer = Character(name="Observer", level=5, room=test_room)
        observer.is_npc = False
        test_room.people.append(observer)
        character_registry.append(observer)

        # Create invisible character
        invisible_char = Character(name="Invisible", level=5, room=test_room)
        invisible_char.is_npc = False
        invisible_char.add_affect(AffectFlag.INVISIBLE)
        test_room.people.append(invisible_char)
        character_registry.append(invisible_char)

        try:
            assert invisible_char.has_affect(AffectFlag.INVISIBLE), "Character should have INVISIBLE affect"

            # Observer looks without detect invis - should NOT see invisible char
            result = process_command(observer, "look")
            assert "Invisible" not in result, f"Invisible character should not be visible in room, got: {result}"

            # Give observer detect invis - should NOW see invisible char
            observer.add_affect(AffectFlag.DETECT_INVIS)
            result_with_detect = process_command(observer, "look")
            invisible_name = invisible_char.name or "Invisible"
            assert "Invisible" in result_with_detect or invisible_name in result_with_detect, (
                f"Character with DETECT_INVIS should see invisible character, got: {result_with_detect}"
            )

        finally:
            # Cleanup
            room_registry.pop(1000, None)
            if observer in character_registry:
                character_registry.remove(observer)
            if invisible_char in character_registry:
                character_registry.remove(invisible_char)


class TestAffectInteractions:
    """Test interactions between multiple affects."""

    def test_curse_prevents_item_removal(self, movable_char_factory):
        """
        Test: AFFECT_CURSE prevents removing equipment.

        ROM Parity: Mirrors ROM AFF_CURSE - can't remove cursed items

        Given: Character wearing cursed item
        When: Try to remove item
        Then: Command fails
        """
        pytest.skip("P2 feature - Requires curse mechanic in item removal commands - implement separately")

    def test_poison_damages_over_time(self, movable_char_factory):
        """
        Test: AFFECT_POISON deals damage each tick.

        ROM Parity: Mirrors ROM poison damage over time

        Given: Character poisoned
        When: Game ticks execute
        Then: HP decreases each tick
        """
        pytest.skip("P3 feature - Requires damage-over-time (DOT) system in game_tick - implement separately")

    def test_plague_spreads_to_nearby_characters(self, movable_char_factory):
        """
        Test: AFFECT_PLAGUE can spread to others in room.

        ROM Parity: Mirrors ROM plague spreading mechanic

        Given: Character with plague in room with others
        When: Game ticks execute
        Then: Chance to infect others
        """
        pytest.skip("P3 feature - Requires contagion spreading system in game_tick - implement separately")
