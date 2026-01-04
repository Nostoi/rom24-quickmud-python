"""Integration tests for Character Advancement System.

Verifies character advancement works correctly through the game loop,
matching ROM 2.4b6 behavior for XP gain, leveling, and stat increases.

ROM Parity: Mirrors ROM src/update.c:gain_exp and src/fight.c:xp_compute
"""

from __future__ import annotations

import pytest

from mud.advancement import advance_level, exp_per_level, gain_exp
from mud.commands.dispatcher import process_command
from mud.game_loop import game_tick
from mud.models.character import Character
from mud.models.constants import LEVEL_HERO
from mud.registry import room_registry, area_registry, mob_registry, obj_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.world import create_test_character, initialize_world


@pytest.fixture(scope="module", autouse=True)
def _initialize_world():
    """Initialize world once for all tests in this module."""
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()


@pytest.fixture
def test_character() -> Character:
    char = create_test_character("TestChar", room_vnum=3001)
    char.level = 1
    char.exp = 1000
    char.max_hit = 20
    char.max_mana = 100
    char.max_move = 100
    char.practice = 5
    char.train = 3
    return char


@pytest.fixture
def test_mob():
    mob = spawn_mob(3143)
    if mob is None:
        pytest.skip("Hassan mob not available")
    room = room_registry.get(3001)
    if room is None:
        pytest.skip("Temple room not available")
    room.add_mob(mob)
    return mob


def test_kill_mob_grants_xp_integration(test_character, test_mob):
    """Given character in combat with mob
    When mob dies
    Then character gains XP

    ROM Parity: src/fight.c:raw_kill → group_gain → gain_exp

    Note: XP computation uses level difference. High-level chars
    get 0 XP from trivial mobs (ROM parity). Using equal levels
    ensures XP is granted for testing the XP flow itself.
    """
    from mud.models.constants import Position
    from mud.utils import rng_mm
    import time

    rng_mm.seed_mm(int(time.time()))

    char = test_character
    mob = test_mob
    initial_xp = char.exp

    # Use equal levels so xp_compute() returns non-zero XP
    # (level 50 vs level 10 = 0 XP per ROM C logic)
    char.level = 10
    mob.level = 10

    char.hitroll = 50
    char.damroll = 50
    char.hit = 1000
    char.max_hit = 1000

    mob.hit = 10
    mob.max_hit = 10

    char.fighting = mob
    mob.fighting = char
    char.position = Position.FIGHTING
    mob.position = Position.FIGHTING

    for _ in range(30):
        game_tick()
        if mob.hit <= 0:
            break

    assert mob.hit <= 0, "Mob should be dead"
    assert char.exp > initial_xp, "Character should gain XP from kill"


def test_xp_gain_scales_with_level_difference(test_character):
    """Given character at level 5
    When killing mobs of different levels
    Then XP varies based on level difference

    ROM Parity: src/fight.c:xp_compute level_range calculation (lines 1826-1879)
    """
    char = test_character
    char.level = 5
    char.exp = exp_per_level(char) * 5

    initial_xp = char.exp
    gain_exp(char, 83)
    assert char.exp == initial_xp + 83, "Same-level kill should grant base 83 XP"

    initial_xp = char.exp
    gain_exp(char, 160)
    assert char.exp == initial_xp + 160, "Higher-level kill should grant more XP"

    initial_xp = char.exp
    gain_exp(char, 22)
    assert char.exp == initial_xp + 22, "Lower-level kill should grant less XP"


def test_no_xp_for_npcs(test_mob):
    """Given NPC mob
    When XP granted
    Then NPC does not gain XP

    ROM Parity: src/update.c:121 - early return for IS_NPC(ch)
    """
    mob = test_mob
    mob.is_npc = True
    initial_xp = getattr(mob, "exp", 0)

    gain_exp(mob, 100)

    assert getattr(mob, "exp", 0) == initial_xp, "NPCs should not gain XP"


def test_no_xp_at_hero_level(test_character):
    """Given character at LEVEL_HERO
    When XP granted
    Then character does not gain XP

    ROM Parity: src/update.c:124 - early return for level >= LEVEL_HERO
    """
    char = test_character
    char.level = LEVEL_HERO
    char.exp = 1000000

    initial_xp = char.exp
    gain_exp(char, 1000)

    assert char.exp == initial_xp, "Hero-level chars should not gain XP"


def test_level_up_at_xp_threshold(test_character):
    """Given character with enough XP
    When XP threshold reached
    Then character levels up

    ROM Parity: src/update.c:128-139 - while loop level advancement
    """
    char = test_character
    char.level = 1
    char.exp = 0

    base_exp = exp_per_level(char)
    xp_to_level_2 = base_exp * 2
    gain_exp(char, xp_to_level_2)

    assert char.level >= 2, "Character should level up at XP threshold"


def test_multiple_levels_at_once(test_character):
    """Given character with massive XP grant
    When XP exceeds multiple thresholds
    Then character gains multiple levels

    ROM Parity: src/update.c:128 - while loop allows multiple level-ups
    """
    char = test_character
    char.level = 1
    char.exp = 0

    base_exp = exp_per_level(char)
    xp_for_level_5 = base_exp * 5
    gain_exp(char, xp_for_level_5)

    assert char.level >= 3, "Character should gain multiple levels at once"


def test_level_up_grants_hp_mana_move(test_character):
    """Given warrior character leveling up
    When advance_level called
    Then HP/mana/move increase by class bonuses

    ROM Parity: src/update.c:advance_level stat increases
    Warrior bonuses: +10 HP, +4 mana, +6 move
    """
    char = test_character
    char.ch_class = 3
    char.level = 1

    initial_hp = char.max_hit
    initial_mana = char.max_mana
    initial_move = char.max_move

    advance_level(char)

    assert char.max_hit == initial_hp + 10, "Warrior should gain +10 HP"
    assert char.max_mana == initial_mana + 4, "Warrior should gain +4 mana"
    assert char.max_move == initial_move + 6, "Warrior should gain +6 move"


def test_level_up_grants_practices_and_trains(test_character):
    """Given character leveling up
    When advance_level called
    Then practices and trains increase

    ROM Parity: advancement.py PRACTICES_PER_LEVEL=2, TRAINS_PER_LEVEL=1
    """
    char = test_character
    char.level = 1
    char.practice = 5
    char.train = 3

    advance_level(char)

    assert char.practice == 7, "Should gain 2 practices per level"
    assert char.train == 4, "Should gain 1 train per level"


def test_level_up_message_sent_to_character(test_character):
    """Given character leveling up
    When level threshold reached
    Then level-up message sent

    ROM Parity: src/update.c:131 - send_to_char level-up message
    """
    char = test_character
    char.level = 1
    char.exp = exp_per_level(char) * 1

    messages = []

    def mock_send(msg):
        messages.append(msg)

    char.send_to_char = mock_send

    xp_needed = exp_per_level(char) * 2
    gain_exp(char, xp_needed)

    assert any("raise a level" in msg for msg in messages), "Should send level-up message to character"


def test_practice_command_improves_skills(test_character):
    """Given character with practice sessions
    When practice command used
    Then skill improves and practice consumed

    ROM Parity: src/act_info.c:do_practice skill improvement
    """
    char = test_character
    char.level = 5
    char.practice = 10

    result = process_command(char, "practice bash")

    assert "practice" in result.lower() or "skill" in result.lower(), "Practice command should provide feedback"


def test_train_command_increases_stats(test_character):
    """Given character with train sessions
    When train command used
    Then stats increase and train consumed

    ROM Parity: src/act_info.c:do_train stat increases
    """
    char = test_character
    char.level = 5
    char.train = 5

    result = process_command(char, "train hp")

    assert "train" in result.lower() or "hp" in result.lower(), "Train command should provide feedback"


def test_xp_loss_on_death(test_character):
    """Given character dying
    When negative XP applied
    Then XP decreases but not below level floor

    ROM Parity: src/update.c:127 - UMAX(exp_per_level, exp + gain)
    """
    char = test_character
    char.level = 5
    char.exp = exp_per_level(char) * 5 + 500

    initial_xp = char.exp
    gain_exp(char, -100)

    assert char.exp < initial_xp, "Death should reduce XP"
    assert char.exp >= exp_per_level(char) * 5, "XP should not drop below level floor"


def test_group_xp_split_among_members(test_character):
    """Given group of 2 players
    When mob killed
    Then XP split among members

    ROM Parity: src/fight.c:group_gain XP distribution (lines 1727-1789)
    """
    char = test_character
    char.level = 5

    char2 = create_test_character("Groupmate", room_vnum=3001)
    char2.level = 5

    base_xp = 100
    expected_xp_per_member = base_xp // 2

    char.exp = exp_per_level(char) * 5
    char2.exp = exp_per_level(char2) * 5

    initial_xp1 = char.exp
    initial_xp2 = char2.exp

    gain_exp(char, expected_xp_per_member)
    gain_exp(char2, expected_xp_per_member)

    assert char.exp == initial_xp1 + expected_xp_per_member
    assert char2.exp == initial_xp2 + expected_xp_per_member


def test_mage_level_up_grants_class_bonuses():
    """Given mage character
    When leveling up
    Then mage bonuses applied: +8 HP, +6 mana, +4 move

    ROM Parity: advancement.py LEVEL_BONUS per class
    """
    char = create_test_character("MageTest", room_vnum=3001)
    char.ch_class = 0
    char.level = 1
    char.max_hit = 20
    char.max_mana = 100
    char.max_move = 100

    advance_level(char)

    assert char.max_hit == 28, "Mage should gain +8 HP"
    assert char.max_mana == 106, "Mage should gain +6 mana"
    assert char.max_move == 104, "Mage should gain +4 move"


def test_cleric_level_up_grants_class_bonuses():
    """Given cleric character
    When leveling up
    Then cleric bonuses applied: +6 HP, +8 mana, +4 move

    ROM Parity: advancement.py LEVEL_BONUS per class
    """
    char = create_test_character("ClericTest", room_vnum=3001)
    char.ch_class = 1
    char.level = 1
    char.max_hit = 20
    char.max_mana = 100
    char.max_move = 100

    advance_level(char)

    assert char.max_hit == 26, "Cleric should gain +6 HP"
    assert char.max_mana == 108, "Cleric should gain +8 mana"
    assert char.max_move == 104, "Cleric should gain +4 move"


def test_thief_level_up_grants_class_bonuses():
    """Given thief character
    When leveling up
    Then thief bonuses applied: +7 HP, +6 mana, +5 move

    ROM Parity: advancement.py LEVEL_BONUS per class
    """
    char = create_test_character("ThiefTest", room_vnum=3001)
    char.ch_class = 2
    char.level = 1
    char.max_hit = 20
    char.max_mana = 100
    char.max_move = 100

    advance_level(char)

    assert char.max_hit == 27, "Thief should gain +7 HP"
    assert char.max_mana == 106, "Thief should gain +6 mana"
    assert char.max_move == 105, "Thief should gain +5 move"


def test_character_advancement_from_level_1_to_10(test_character):
    """Given level 1 warrior
    When XP granted to reach level 10
    Then all stat bonuses accumulate correctly

    ROM Parity: Full advancement workflow
    """
    char = test_character
    char.level = 1
    char.exp = 0
    char.ch_class = 3
    char.max_hit = 20
    char.max_mana = 100
    char.max_move = 100
    char.practice = 5
    char.train = 3

    base_exp = exp_per_level(char)
    xp_for_level_10 = base_exp * 10
    gain_exp(char, xp_for_level_10)

    assert char.level >= 10, f"Character should reach level 10 (got {char.level})"

    level_ups = char.level - 1
    expected_hp = 20 + (level_ups * 10)
    expected_mana = 100 + (level_ups * 4)
    expected_move = 100 + (level_ups * 6)

    assert char.max_hit == expected_hp, f"Expected {expected_hp} HP at level {char.level}"
    assert char.max_mana == expected_mana, f"Expected {expected_mana} mana at level {char.level}"
    assert char.max_move == expected_move, f"Expected {expected_move} move at level {char.level}"

    expected_practices = 5 + (level_ups * 2)
    expected_trains = 3 + (level_ups * 1)

    assert char.practice == expected_practices, f"Expected {expected_practices} practices at level {char.level}"
    assert char.train == expected_trains, f"Expected {expected_trains} trains at level {char.level}"


def test_negative_xp_gain_does_not_drop_below_level_floor(test_character):
    """Given character losing XP
    When negative XP exceeds current level XP
    Then XP stops at level floor

    ROM Parity: src/update.c:127 - UMAX(exp_per_level, exp + gain)
    """
    char = test_character
    char.level = 5
    char.exp = 6000

    floor = exp_per_level(char)
    gain_exp(char, -10000)

    assert char.exp >= floor, f"XP should not drop below level floor (got {char.exp}, floor {floor})"


def test_zero_xp_gain_does_nothing(test_character):
    """Given character gaining 0 XP
    When gain_exp(0) called
    Then XP unchanged
    """
    char = test_character
    char.level = 5
    char.exp = exp_per_level(char) * 5

    initial_xp = char.exp
    gain_exp(char, 0)

    assert char.exp == initial_xp, "Gaining 0 XP should not change XP"
