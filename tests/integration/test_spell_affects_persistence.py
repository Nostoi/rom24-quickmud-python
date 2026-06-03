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
from mud.models.character import AffectData, SpellEffect, character_registry
from mud.models.constants import AffectFlag, ExtraFlag, ItemType, WearFlag, WearLocation
from mud.models.room import Room
from mud.registry import room_registry
from mud.utils import rng_mm


@pytest.fixture(autouse=True)
def _isolate_spell_affect_tests():
    """Clear leaked character/world state between spell-affect integration tests."""
    import mud.game_loop as gl
    from mud.config import get_pulse_area, get_pulse_mobile, get_pulse_music, get_pulse_tick, get_pulse_violence

    def _clear_registry() -> None:
        for char in list(character_registry):
            room = getattr(char, "room", None)
            if room is not None and hasattr(room, "people") and char in room.people:
                room.people.remove(char)
        character_registry.clear()

    def _reset_counters() -> None:
        gl._pulse_counter = 0
        gl._point_counter = get_pulse_tick()
        gl._area_counter = get_pulse_area()
        gl._music_counter = get_pulse_music()
        gl._mobile_counter = get_pulse_mobile()
        gl._violence_counter = get_pulse_violence()

    _clear_registry()
    _reset_counters()
    yield
    _clear_registry()
    _reset_counters()


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

    def test_real_spell_affect_persists_until_point_pulse(self, movable_char_factory):
        """
        Test: Real spell affects do not decay before ROM's point-pulse boundary.

        ROM Parity: Mirrors ROM src/update.c:1190 and src/update.c:765-768 —
        affect decay only happens inside char_update(), which runs on PULSE_TICK.

        Given: giant strength active on a character
        When: game_tick() runs for fewer than PULSE_TICK pulses
        Then: duration and level remain unchanged
        """
        from mud.skills.handlers import giant_strength

        char = movable_char_factory("Warrior", 3001, points=200)
        char.level = 20
        char.perm_stat = [13, 13, 13, 13, 13]

        assert giant_strength(char, char) is True
        effect = char.spell_effects["giant strength"]
        initial_duration = effect.duration
        initial_level = effect.level

        for _ in range(get_pulse_tick() - 1):
            game_tick()

        effect_after = char.spell_effects["giant strength"]
        assert effect_after.duration == initial_duration
        assert effect_after.level == initial_level

    def test_real_spell_affect_level_can_fade_on_point_pulse(self, movable_char_factory, monkeypatch):
        """
        Test: Spell affect level can fade by 1 on a point pulse.

        ROM Parity: Mirrors ROM src/update.c:765-768 — after duration--,
        `number_range(0, 4) == 0` causes `paf->level--`.

        Given: giant strength active at level 20
        When: the first ROM fade roll returns 0 on the point pulse
        Then: the affect duration drops by 1 and affect level drops by 1
        """
        from mud.skills.handlers import giant_strength

        char = movable_char_factory("Champion", 3001, points=200)
        char.level = 20
        char.perm_stat = [13, 13, 13, 13, 13]

        assert giant_strength(char, char) is True

        original_number_range = rng_mm.number_range
        fade_roll_used = False

        def _force_first_fade_roll(from_val: int, to_val: int) -> int:
            nonlocal fade_roll_used
            if not fade_roll_used and from_val == 0 and to_val == 4:
                fade_roll_used = True
                return 0
            return original_number_range(from_val, to_val)

        monkeypatch.setattr(rng_mm, "number_range", _force_first_fade_roll)

        run_point_pulses(1)

        effect = char.spell_effects["giant strength"]
        assert effect.duration == 19
        assert effect.level == 19

        giant_strength_affects = [affect for affect in char.affected if affect.type == "giant strength"]
        assert len(giant_strength_affects) == 1
        assert giant_strength_affects[0].duration == 19
        assert giant_strength_affects[0].level == 19

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

    def test_multi_entry_spell_wears_off_once_through_game_tick(self, movable_char_factory):
        """
        Test: Multi-entry spell emits one wear-off message and removes all entries.

        ROM Parity: Mirrors ROM src/update.c:773-784 — when consecutive
        AFFECT_DATA nodes share the same spell type, only the final expired node
        emits `msg_off` before all matching entries are removed.

        Given: frenzy active on a character
        When: point pulses advance until the spell expires
        Then: all frenzy affects are removed and exactly one wear-off message is sent
        """
        from mud.skills.handlers import frenzy

        char = movable_char_factory("Templar", 3001, points=200)
        char.level = 12
        char.alignment = 0

        initial_hitroll = char.hitroll
        initial_damroll = char.damroll
        initial_armor = list(char.armor)

        assert frenzy(char, char) is True
        assert len([affect for affect in char.affected if affect.type == "frenzy"]) == 3

        char.messages.clear()

        run_point_pulses(5)

        assert not char.has_spell_effect("frenzy")
        assert [affect for affect in char.affected if affect.type == "frenzy"] == []
        assert char.hitroll == initial_hitroll
        assert char.damroll == initial_damroll
        assert char.armor == initial_armor
        wear_off_messages = [message for message in char.messages if message == "Your rage ebbs.\n\r"]
        assert wear_off_messages == ["Your rage ebbs.\n\r"]

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

    def test_giant_strength_refuses_to_stack(self, movable_char_factory):
        """
        Test: spell_giant_strength refuses to stack on the same target.

        ROM Parity: src/magic.c:3022-3030 spell_giant_strength() returns early
        with "You are already as strong as you can get!" when the target is
        already affected. It does NOT call affect_join — unlike most other
        buff spells, giant strength explicitly anti-stacks.

        Given: Character cast giant strength (level 20 → +2 STR)
        When: Cast giant strength again on same target
        Then: Second cast fails; STR remains at initial+2 (not +4).
        """
        from mud.skills.handlers import giant_strength

        char = movable_char_factory("TestChar", 3001)
        char.level = 20
        char.perm_stat = [13, 13, 13, 13, 13]

        initial_str = char.get_curr_stat(0)

        assert giant_strength(char, char) is True
        assert char.has_spell_effect("giant strength")

        first_str = char.get_curr_stat(0)
        assert first_str == initial_str + 2, "First cast should give +2 STR"

        # Second cast must fail (ROM anti-stack) and STR must not change.
        assert giant_strength(char, char) is False, "Second cast must refuse to stack"
        second_str = char.get_curr_stat(0)
        assert second_str == initial_str + 2, "STR must not change on refused recast"


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
        from mud.skills.handlers import armor, bless, dispel_magic, giant_strength

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

    def test_curse_prevents_item_removal(self, movable_char_factory, object_factory):
        """
        Test: AFFECT_CURSE prevents removing equipment.

        ROM Parity: Mirrors ROM AFF_CURSE - can't remove cursed items

        Given: Character wearing cursed item
        When: Try to remove item
        Then: Command fails
        """
        char = movable_char_factory("Cursed", 3001, points=200)
        cursed_ring = object_factory(
            {
                "vnum": 9010,
                "name": "cursed ring",
                "short_descr": "a cursed ring",
                "item_type": int(ItemType.ARMOR),
                "wear_flags": int(WearFlag.TAKE) | int(WearFlag.WEAR_FINGER),
                "extra_flags": int(ExtraFlag.NOREMOVE),
                "value": [1, 0, 0, 0],
            }
        )
        char.add_object(cursed_ring)

        wear_result = process_command(char, "wear ring")
        assert "wear" in wear_result.lower()
        assert cursed_ring.wear_loc in {int(WearLocation.FINGER_L), int(WearLocation.FINGER_R)}

        result = process_command(char, "remove ring")
        assert result == "You can't remove a cursed ring."
        assert cursed_ring.wear_loc in {int(WearLocation.FINGER_L), int(WearLocation.FINGER_R)}
        assert cursed_ring in char.equipment.values()

    def test_poison_damages_over_time(self, movable_char_factory):
        """
        Test: AFFECT_POISON deals damage each tick.

        ROM Parity: Mirrors ROM poison damage over time

        Given: Character poisoned
        When: Game ticks execute
        Then: HP decreases each tick
        """
        char = movable_char_factory("Poisoned", 3001, points=200)
        char.hit = 80
        char.max_hit = 100
        char.desc = object()
        char.affect_to_char(
            AffectData(
                type="poison",
                level=20,
                duration=5,
                location="none",
                modifier=0,
                bitvector=int(AffectFlag.POISON),
            )
        )

        before = char.hit
        run_point_pulses(1)

        assert char.hit < before
        assert any("shiver and suffer" in message.lower() for message in getattr(char, "messages", []))

    def test_plague_spreads_to_nearby_characters(self, movable_char_factory, monkeypatch: pytest.MonkeyPatch):
        """
        Test: AFFECT_PLAGUE can spread to others in room.

        ROM Parity: Mirrors ROM plague spreading mechanic

        Given: Character with plague in room with others
        When: Game ticks execute
        Then: Chance to infect others
        """
        from mud import game_loop as gl

        room_vnum = 91000
        room_registry[room_vnum] = Room(vnum=room_vnum, name="Isolation Room", description="A sealed test room")

        try:
            victim = movable_char_factory("Patient", room_vnum, points=200)
            victim.level = 20
            victim.mana = 100
            victim.move = 100
            victim.desc = object()
            bystander = movable_char_factory("Bystander", room_vnum, points=200)
            bystander.level = 10
            bystander.desc = object()

            victim.affect_to_char(
                AffectData(
                    type="plague",
                    level=12,
                    duration=5,
                    location="str",
                    modifier=-5,
                    bitvector=int(AffectFlag.PLAGUE),
                )
            )

            monkeypatch.setattr(gl.rng_mm, "number_bits", lambda _bits: 0)
            monkeypatch.setattr(gl.rng_mm, "number_range", lambda _low, high: high)

            from mud.affects import saves as saves_module

            monkeypatch.setattr(saves_module, "saves_spell", lambda *_args, **_kwargs: False)

            run_point_pulses(1)

            assert bystander.has_affect(AffectFlag.PLAGUE)
            assert any("feel hot and feverish" in message.lower() for message in getattr(bystander, "messages", []))
        finally:
            room_registry.pop(room_vnum, None)


class TestSpellPassDoorIntegration:
    """Runtime-path coverage for spell_pass_door (ROM src/magic.c:3864)."""

    def test_pass_door_persists_and_wears_off_through_point_pulses(self, movable_char_factory):
        """
        ROM Parity: src/magic.c:3864 (spell_pass_door) + src/update.c:765-784 (affect_update).

        Given: pass door cast on a character (duration = number_fuzzy(level/4))
        When: enough point pulses elapse to drain the duration
        Then: AffectFlag.PASS_DOOR clears and the ROM wear-off message fires once.
        """
        from mud.skills.handlers import pass_door

        rng_mm.seed_mm(42)

        char = movable_char_factory("Translucent", 3001, points=200)
        char.level = 40

        assert pass_door(char, char) is True
        assert char.has_affect(AffectFlag.PASS_DOOR)
        assert char.has_spell_effect("pass door")

        effect = char.spell_effects["pass door"]
        initial_duration = effect.duration
        assert initial_duration > 0

        char.messages.clear()

        run_point_pulses(initial_duration + 1)

        assert not char.has_spell_effect("pass door")
        assert not char.has_affect(AffectFlag.PASS_DOOR)
        assert [affect for affect in char.affected if affect.type == "pass door"] == []
        wear_off_messages = [message for message in char.messages if "You feel solid again." in message]
        assert wear_off_messages == ["You feel solid again.\n\r"]

    def test_pass_door_duplicate_cast_during_active_affect_is_rejected(self, movable_char_factory):
        """
        ROM Parity: src/magic.c:3869-3877 — re-casting on an already-affected target
        sends the "already out of phase" message and applies no new affect.
        """
        from mud.skills.handlers import pass_door

        rng_mm.seed_mm(42)

        char = movable_char_factory("Phaser", 3001, points=200)
        char.level = 40

        assert pass_door(char, char) is True
        effect = char.spell_effects["pass door"]
        original_duration = effect.duration

        char.messages.clear()
        assert pass_door(char, char) is False

        assert char.spell_effects["pass door"].duration == original_duration
        assert any("already out of phase" in message.lower() for message in char.messages)
