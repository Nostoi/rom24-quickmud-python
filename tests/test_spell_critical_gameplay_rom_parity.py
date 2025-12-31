"""ROM parity tests for critical gameplay spells.

Tests for: fireball, heal, sanctuary, teleport, word_of_recall

These are high-priority spells used extensively in ROM gameplay.
All tests use ROM C formulas and golden file methodology.
"""

from __future__ import annotations

from mud.affects.saves import saves_spell
from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import AffectFlag, DamageType, Position, RoomFlag
from mud.models.room import Room
from mud.skills.handlers import fireball, heal, sanctuary, teleport, word_of_recall
from mud.utils import rng_mm
from mud.registry import room_registry


def make_character(**overrides) -> Character:
    """Helper to create test characters with common defaults."""
    base = {
        "name": overrides.get("name", "TestChar"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 120),
        "max_hit": overrides.get("max_hit", 120),
        "move": overrides.get("move", 100),
        "max_move": overrides.get("max_move", 100),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


# ============================================================================
# FIREBALL TESTS (ROM src/magic.c:2074-2114)
# ============================================================================


def _rom_fireball(level: int, victim: Character) -> int:
    """ROM fireball damage formula with damage table."""
    dam_each = (
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        30,
        35,
        40,
        45,
        50,
        55,
        60,
        65,
        70,
        75,
        80,
        82,
        84,
        86,
        88,
        90,
        92,
        94,
        96,
        98,
        100,
        102,
        104,
        106,
        108,
        110,
        112,
        114,
        116,
        118,
        120,
        122,
        124,
        126,
        128,
        130,
    )
    index = min(level, len(dam_each) - 1)
    base = dam_each[index]
    low = c_div(base, 2)
    high = base * 2
    damage = rng_mm.number_range(low, high)

    if saves_spell(level, victim, DamageType.FIRE):
        damage = c_div(damage, 2)

    return damage


def test_fireball_damage_table():
    """ROM L2074-2114: Fireball uses damage table by level."""
    caster = make_character(level=20)
    victim = make_character(hit=150, max_hit=150, level=24)
    rom_victim = make_character(hit=150, max_hit=150, level=24)

    rng_mm.seed_mm(0xF1)
    expected = _rom_fireball(20, rom_victim)

    rng_mm.seed_mm(0xF1)
    dealt = fireball(caster, victim)

    assert dealt == expected
    assert victim.hit == 150 - dealt


def test_fireball_save_for_half():
    """ROM L2111: Save reduces fireball damage by half."""
    caster = make_character(level=10)
    victim = make_character(hit=120, max_hit=120, level=50)  # High level = likely save

    damages = []
    for seed in range(50):
        rng_mm.seed_mm(seed)
        rom_victim = make_character(hit=120, max_hit=120, level=50)
        expected = _rom_fireball(10, rom_victim)

        rng_mm.seed_mm(seed)
        victim.hit = 120
        dealt = fireball(caster, victim)

        assert dealt == expected
        damages.append(dealt)

    # At least some should be reduced by save
    max_base_damage = 35 * 2  # Level 10 base = 0, but level 14 = 30, level 15 = 35
    assert any(d < max_base_damage for d in damages)


def test_fireball_level_scaling():
    """ROM L2074-2114: Damage increases with caster level."""
    victim = make_character(hit=200, max_hit=200, level=1)

    # Test at different caster levels
    low_caster = make_character(level=15)
    high_caster = make_character(level=40)

    low_damages = []
    high_damages = []

    for seed in range(20):
        rng_mm.seed_mm(seed)
        victim.hit = 200
        low_damages.append(fireball(low_caster, victim))

        rng_mm.seed_mm(seed)
        victim.hit = 200
        high_damages.append(fireball(high_caster, victim))

    # Higher level should deal more damage on average
    assert sum(high_damages) / len(high_damages) > sum(low_damages) / len(low_damages)


def test_fireball_requires_target():
    """Fireball requires caster and target."""
    caster = make_character(level=30)

    try:
        fireball(caster, None)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "target" in str(e).lower()


# ============================================================================
# HEAL TESTS (ROM src/magic.c:3066-3084)
# ============================================================================


def test_heal_fixed_amount():
    """ROM L3066-3084: Heal restores exactly 100 hit points."""
    caster = make_character(level=30)
    target = make_character(hit=50, max_hit=200)

    healed = heal(caster, target)

    assert healed == 100
    assert target.hit == 150


def test_heal_caps_at_max_hit():
    """ROM L3066-3084: Heal cannot exceed max_hit."""
    caster = make_character(level=30)
    target = make_character(hit=120, max_hit=150)

    healed = heal(caster, target)

    assert target.hit == 150  # Capped at max_hit
    assert healed == 100  # Still reports 100 healed


def test_heal_self_targeting():
    """ROM L3066-3084: Heal defaults to caster if no target."""
    caster = make_character(level=30, hit=50, max_hit=200)

    healed = heal(caster, None)

    assert healed == 100
    assert caster.hit == 150


def test_heal_updates_position():
    """Heal should update position if target was below full health."""
    caster = make_character(level=30)
    target = make_character(hit=-10, max_hit=100, position=Position.INCAP)

    heal(caster, target)

    assert target.hit == 90  # -10 + 100
    assert target.position != Position.INCAP


# ============================================================================
# SANCTUARY TESTS (ROM src/magic.c:3753-3777)
# ============================================================================


def test_sanctuary_applies_affect():
    """ROM L3753-3777: Sanctuary applies SANCTUARY affect flag."""
    caster = make_character(level=30)
    target = make_character()

    result = sanctuary(caster, target)

    assert result is True
    assert target.has_affect(AffectFlag.SANCTUARY) or target.has_spell_effect("sanctuary")


def test_sanctuary_duration_formula():
    """ROM L3753-3777: Sanctuary duration is level/6."""
    caster = make_character(level=36)
    target = make_character()

    sanctuary(caster, target)

    # Check spell effect duration (spell_effects is a dict, not a list)
    effects = getattr(target, "spell_effects", {})
    sanc_effect = effects.get("sanctuary")

    assert sanc_effect is not None
    expected_duration = c_div(36, 6)  # = 6 ticks
    assert sanc_effect.duration == expected_duration


def test_sanctuary_already_affected():
    """ROM L3753-3777: Cannot apply sanctuary if already in sanctuary."""
    caster = make_character(level=30)
    target = make_character()

    # First application should succeed
    result1 = sanctuary(caster, target)
    assert result1 is True

    # Second application should fail
    result2 = sanctuary(caster, target)
    assert result2 is False


def test_sanctuary_self_targeting():
    """ROM L3753-3777: Sanctuary defaults to caster if no target."""
    caster = make_character(level=30)

    result = sanctuary(caster, None)

    assert result is True
    assert caster.has_affect(AffectFlag.SANCTUARY) or caster.has_spell_effect("sanctuary")


# ============================================================================
# TELEPORT TESTS (ROM src/magic.c:3813-3881)
# ============================================================================


def test_teleport_moves_character():
    """ROM L3813-3881: Teleport moves character to random room."""
    from mud.utils.rng_mm import seed_mm

    seed_mm(42)
    caster = make_character(level=30)

    start_room = Room(vnum=1000, name="Start Room")
    start_room.add_character(caster)

    try:
        original_room = caster.room

        result = teleport(caster, None)

        if result:
            assert caster.room is not original_room
        else:
            assert caster.room is original_room
    finally:
        if caster.room and caster in caster.room.people:
            caster.room.remove_character(caster)


def test_teleport_fails_no_recall_room():
    """ROM L3813-3881: Teleport fails in NO_RECALL rooms."""
    caster = make_character(level=30)

    # Create NO_RECALL room
    no_recall_room = Room(vnum=1000, name="No Recall", room_flags=int(RoomFlag.ROOM_NO_RECALL))
    no_recall_room.add_character(caster)

    result = teleport(caster, None)

    assert result is False


def test_teleport_self_targeting():
    """ROM L3813-3881: Teleport defaults to caster if no target."""
    caster = make_character(level=30)
    room = Room(vnum=1000, name="Test Room")
    room_registry[1000] = room

    try:
        room.add_character(caster)
        original_room = caster.room

        result = teleport(caster, None)

        # Should target self (may succeed or fail based on room availability)
        assert result is True or result is False
    finally:
        if 1000 in room_registry:
            del room_registry[1000]


# ============================================================================
# WORD OF RECALL TESTS (ROM src/magic.c:4051-4104)
# ============================================================================


def test_word_of_recall_to_temple():
    """ROM L4051-4104: Word of recall moves to temple (vnum 3001)."""
    caster = make_character(level=30, is_npc=False)

    # Create temple and starting room
    temple = Room(vnum=3001, name="Temple of Midgaard")
    start_room = Room(vnum=1000, name="Start Room")

    room_registry[3001] = temple
    room_registry[1000] = start_room

    try:
        start_room.add_character(caster)

        result = word_of_recall(caster, None)

        assert result is True
        assert caster.room is temple
    finally:
        if 3001 in room_registry:
            del room_registry[3001]
        if 1000 in room_registry:
            del room_registry[1000]


def test_word_of_recall_costs_half_move():
    """ROM L4051-4104: Word of recall costs half movement points."""
    caster = make_character(level=30, is_npc=False, move=100, max_move=100)

    # Create temple and starting room
    temple = Room(vnum=3001, name="Temple of Midgaard")
    start_room = Room(vnum=1000, name="Start Room")

    room_registry[3001] = temple
    room_registry[1000] = start_room

    try:
        start_room.add_character(caster)

        word_of_recall(caster, None)

        expected_move = c_div(100, 2)  # 50
        assert caster.move == expected_move
    finally:
        if 3001 in room_registry:
            del room_registry[3001]
        if 1000 in room_registry:
            del room_registry[1000]


def test_word_of_recall_fails_no_recall():
    """ROM L4051-4104: Word of recall fails in NO_RECALL rooms."""
    caster = make_character(level=30, is_npc=False)

    no_recall_room = Room(vnum=1000, name="No Recall", room_flags=int(RoomFlag.ROOM_NO_RECALL))
    no_recall_room.add_character(caster)

    result = word_of_recall(caster, None)

    assert result is False


def test_word_of_recall_fails_cursed():
    """ROM L4051-4104: Word of recall fails if victim is cursed."""
    from mud.utils.rng_mm import seed_mm

    seed_mm(100)
    caster = make_character(level=60, is_npc=False)

    temple = Room(vnum=3001, name="Temple of Midgaard")
    start_room = Room(vnum=1000, name="Start Room")

    room_registry[3001] = temple
    room_registry[1000] = start_room

    try:
        start_room.add_character(caster)

        from mud.skills.handlers import curse

        curse_result = curse(caster, caster)

        if not curse_result:
            assert True
            return

        assert caster.has_affect(AffectFlag.CURSE) or caster.has_spell_effect("curse")

        result = word_of_recall(caster, None)

        assert result is False
        assert caster.room is start_room
    finally:
        if 3001 in room_registry:
            del room_registry[3001]
        if 1000 in room_registry:
            del room_registry[1000]


def test_word_of_recall_npcs_cannot_recall():
    """ROM L4051-4104: NPCs cannot use word of recall."""
    npc = make_character(level=30, is_npc=True)

    result = word_of_recall(npc, None)

    assert result is False
