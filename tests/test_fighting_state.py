"""Tests for fighting state management in combat system.

Tests set_fighting, stop_fighting, update_pos, and position messaging following
ROM 2.4 C src/fight.c logic.
"""

from mud.combat.engine import apply_damage, is_awake, set_fighting, stop_fighting, update_pos
from mud.models.character import Character
from mud.models.constants import Position
from mud.utils import rng_mm


def test_set_fighting_basic():
    """Test set_fighting sets fighting state and position."""
    rng_mm.seed_mm(12345)

    attacker = Character(name="Attacker", level=20, hit=100, max_hit=100)
    victim = Character(name="Victim", level=18, hit=80, max_hit=80)

    attacker.fighting = None
    attacker.position = Position.STANDING

    set_fighting(attacker, victim)

    assert attacker.fighting == victim
    assert attacker.position == Position.FIGHTING


def test_set_fighting_already_fighting():
    """Test set_fighting handles already fighting gracefully."""
    rng_mm.seed_mm(12345)

    attacker = Character(name="Attacker", level=20, hit=100, max_hit=100)
    victim1 = Character(name="Victim1", level=18, hit=80, max_hit=80)
    victim2 = Character(name="Victim2", level=18, hit=80, max_hit=80)

    attacker.fighting = victim1
    attacker.position = Position.FIGHTING

    # Should not change fighting target if already fighting
    set_fighting(attacker, victim2)

    assert attacker.fighting == victim1  # Unchanged
    assert attacker.position == Position.FIGHTING


def test_stop_fighting():
    """Test stop_fighting clears fighting state and sets position."""
    rng_mm.seed_mm(12345)

    attacker = Character(name="Attacker", level=20, hit=100, max_hit=100)
    victim = Character(name="Victim", level=18, hit=80, max_hit=80)

    attacker.fighting = victim
    attacker.position = Position.FIGHTING

    stop_fighting(attacker, both=False)

    assert attacker.fighting is None
    assert attacker.position == Position.STANDING


def test_update_pos_healthy():
    """Test update_pos with healthy character."""
    victim = Character(name="Victim", level=18, hit=80, max_hit=80)
    victim.position = Position.STUNNED

    update_pos(victim)

    assert victim.position == Position.STANDING


def test_update_pos_npc_death():
    """Test update_pos with NPC at 0 or negative hit points."""
    victim = Character(name="NpcVictim", level=5, hit=-1, max_hit=50)
    victim.is_npc = True

    update_pos(victim)

    assert victim.position == Position.DEAD


def test_update_pos_pc_mortal():
    """Test update_pos with PC at mortal wound level."""
    victim = Character(name="PcVictim", level=10, hit=-8, max_hit=100)
    victim.is_npc = False

    update_pos(victim)

    assert victim.position == Position.MORTAL


def test_update_pos_pc_incap():
    """Test update_pos with PC at incapacitated level."""
    victim = Character(name="PcVictim", level=10, hit=-4, max_hit=100)
    victim.is_npc = False

    update_pos(victim)

    assert victim.position == Position.INCAP


def test_update_pos_pc_stunned():
    """Test update_pos with PC at stunned level."""
    victim = Character(name="PcVictim", level=10, hit=-1, max_hit=100)
    victim.is_npc = False

    update_pos(victim)

    assert victim.position == Position.STUNNED


def test_update_pos_pc_death():
    """Test update_pos with PC at death level."""
    victim = Character(name="PcVictim", level=10, hit=-12, max_hit=100)
    victim.is_npc = False

    update_pos(victim)

    assert victim.position == Position.DEAD


def test_is_awake():
    """Test is_awake position checks."""
    char = Character(name="Test", level=10, hit=50, max_hit=50)

    char.position = Position.DEAD
    assert not is_awake(char)

    char.position = Position.MORTAL
    assert not is_awake(char)

    char.position = Position.INCAP
    assert not is_awake(char)

    char.position = Position.STUNNED
    assert not is_awake(char)

    char.position = Position.SLEEPING
    assert not is_awake(char)

    char.position = Position.RESTING
    assert is_awake(char)

    char.position = Position.SITTING
    assert is_awake(char)

    char.position = Position.FIGHTING
    assert is_awake(char)

    char.position = Position.STANDING
    assert is_awake(char)


def test_apply_damage_sets_fighting():
    """Test apply_damage sets fighting state properly."""
    rng_mm.seed_mm(12345)

    attacker = Character(name="Attacker", level=20, hit=100, max_hit=100)
    victim = Character(name="Victim", level=18, hit=80, max_hit=80)

    # Start not fighting
    attacker.fighting = None
    victim.fighting = None
    attacker.position = Position.STANDING
    victim.position = Position.STANDING

    apply_damage(attacker, victim, 10)

    # Both should be fighting now
    assert attacker.fighting == victim
    assert victim.fighting == attacker
    assert attacker.position == Position.FIGHTING
    assert victim.position == Position.FIGHTING
    assert victim.hit == 70


def test_apply_damage_death():
    """Test apply_damage handles death correctly."""
    rng_mm.seed_mm(12345)

    attacker = Character(name="Attacker", level=20, hit=100, max_hit=100)
    victim = Character(name="Victim", level=5, hit=10, max_hit=50)
    victim.is_npc = True

    result = apply_damage(attacker, victim, 15)

    # Victim should be dead, fighting cleared
    assert victim.position == Position.DEAD
    assert victim.hit == -5
    assert attacker.fighting is None
    assert victim.fighting is None
    assert attacker.position == Position.STANDING
    assert "kill" in result.lower()


def test_apply_damage_unconscious_stops_fighting():
    """Test unconscious victim stops fighting."""
    rng_mm.seed_mm(12345)

    attacker = Character(name="Attacker", level=20, hit=100, max_hit=100)
    victim = Character(name="Victim", level=10, hit=15, max_hit=100)
    victim.is_npc = False

    # Set up fighting
    set_fighting(attacker, victim)
    set_fighting(victim, attacker)

    # Damage enough to stun (15 - 17 = -2, which is > -3, so STUNNED)
    apply_damage(attacker, victim, 17)

    # Victim should be stunned and not fighting
    assert victim.position == Position.STUNNED
    assert victim.fighting is None  # Stopped fighting due to unconsciousness


def test_apply_damage_immortal_survives():
    """Test immortal character can't be killed."""
    rng_mm.seed_mm(12345)

    attacker = Character(name="Attacker", level=20, hit=100, max_hit=100)
    victim = Character(name="Immortal", level=110, hit=10, max_hit=100)
    victim.is_npc = False  # PC immortal

    apply_damage(attacker, victim, 50)

    # Immortal should survive with 1 hit
    assert victim.hit == 1
    assert victim.position != Position.DEAD


def test_apply_damage_already_dead():
    """Test apply_damage handles already dead victim."""
    rng_mm.seed_mm(12345)

    attacker = Character(name="Attacker", level=20, hit=100, max_hit=100)
    victim = Character(name="DeadVictim", level=5, hit=0, max_hit=50)
    victim.position = Position.DEAD

    result = apply_damage(attacker, victim, 10)

    assert result == "Already dead."
    assert victim.hit == 0  # No additional damage
