from mud.combat import engine as combat_engine
from mud.commands import process_command
from mud.models.character import Character
from mud.models.constants import (
    AC_BASH,
    AC_EXOTIC,
    AC_PIERCE,
    AC_SLASH,
    AffectFlag,
    DamageType,
    ImmFlag,
    Position,
    ResFlag,
    VulnFlag,
)
from mud.world import create_test_character, initialize_world


def setup_combat() -> tuple[Character, Character]:
    initialize_world("area/area.lst")
    room_vnum = 3001
    attacker = create_test_character("Attacker", room_vnum)
    victim = create_test_character("Victim", room_vnum)
    return attacker, victim


def test_attack_damages_but_not_kill() -> None:
    attacker, victim = setup_combat()
    attacker.damroll = 3
    attacker.hitroll = 100  # guarantee hit
    victim.hit = 10
    out = process_command(attacker, "kill victim")
    # ROM unarmed damage for level 1: base 5 + damroll 3 = 8 total
    # Message includes "That really did HURT!" for significant damage
    assert out == "You hit Victim for 8 damage. That really did HURT!"
    assert victim.hit == 2  # 10 - 8 = 2
    assert attacker.position == Position.FIGHTING
    assert victim.position == Position.FIGHTING
    assert victim in attacker.room.people


def test_attack_kills_target():
    attacker, victim = setup_combat()
    attacker.damroll = 0  # Use 0 damroll so we get exactly 5 base damage
    attacker.hitroll = 100  # guarantee hit
    victim.hit = 5
    out = process_command(attacker, "kill victim")
    assert out == "You kill Victim."
    assert victim.hit == 0
    assert attacker.position == Position.STANDING
    assert victim.position == Position.DEAD
    assert victim not in attacker.room.people
    assert "Victim is DEAD!!!" in attacker.messages


def test_attack_misses_target(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = -100  # extremely low hit chance
    victim.hit = 10
    # Guarantee miss deterministically
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 100)
    out = process_command(attacker, "kill victim")
    assert out == "You miss Victim."
    assert victim.hit == 10
    assert attacker.position == Position.FIGHTING
    assert victim.position == Position.FIGHTING
    assert victim in attacker.room.people


def test_defense_order_and_early_out(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit roll passes
    attacker.damroll = 3

    calls: list[str] = []

    def parry(a, v):
        calls.append("parry")
        return False

    def dodge(a, v):
        calls.append("dodge")
        return True  # early-out here

    def shield(a, v):
        calls.append("shield")
        return False

    monkeypatch.setattr(combat_engine, "check_parry", parry)
    monkeypatch.setattr(combat_engine, "check_dodge", dodge)
    monkeypatch.setattr(combat_engine, "check_shield_block", shield)

    out = process_command(attacker, "kill victim")
    assert out == "Victim dodges your attack."
    # ROM defense order: shield_block → parry → dodge (dodge early-exits, so shield not reached after)
    assert calls == ["shield", "parry", "dodge"]


def test_multi_hit_single_attack():
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit
    attacker.damroll = 1
    victim.hit = 10

    # No extra attack skills - should only get one attack
    results = combat_engine.multi_hit(attacker, victim)
    assert len(results) == 1
    # ROM damage: base 5 + damroll 1 = 6 total
    assert "You hit Victim for" in results[0] and "damage." in results[0]
    assert victim.hit == 4  # 10 - 6 = 4


def test_multi_hit_with_haste():
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit
    attacker.damroll = 1
    victim.hit = 20  # Increase HP to survive two attacks

    # Add haste affect
    attacker.add_affect(AffectFlag.HASTE)

    results = combat_engine.multi_hit(attacker, victim)
    assert len(results) == 2  # Normal + haste attack
    # With weapon damage calculation, damage will be higher than just damroll
    assert all("You hit Victim for" in r and "damage." in r for r in results)
    assert victim.hit == 8  # 20 - (6 + 6) = 8


def test_multi_hit_second_attack():
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit
    attacker.damroll = 1
    attacker.second_attack_skill = 100  # 50% chance (100/2)
    victim.hit = 20  # Increase HP to survive multiple attacks

    # Initialize fighting state
    combat_engine.set_fighting(attacker, victim)

    # Mock to force successful second attack
    from mud.utils import rng_mm

    original_number_percent = rng_mm.number_percent

    def mock_number_percent():
        return 1  # Always return 1, which is < 50

    rng_mm.number_percent = mock_number_percent

    try:
        results = combat_engine.multi_hit(attacker, victim)
        assert len(results) == 2  # First + second attack
        assert attacker.fighting == victim
        assert victim.fighting == attacker
        # ROM damage: 2 hits × 6 damage = 12 total, so 20 - 12 = 8
        assert victim.hit == 8
    finally:
        # Restore original function
        rng_mm.number_percent = original_number_percent


def test_multi_hit_third_attack():
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit
    attacker.damroll = 1
    attacker.second_attack_skill = 100  # Always succeeds (50% chance)
    attacker.third_attack_skill = 100  # Always succeeds (25% chance)
    victim.hit = 20

    # Set up a monkey patch to force successful rolls
    from mud.utils import rng_mm

    original_number_percent = rng_mm.number_percent

    def mock_number_percent():
        return 1  # Always return 1, which is < any positive chance

    rng_mm.number_percent = mock_number_percent

    try:
        results = combat_engine.multi_hit(attacker, victim)
        assert len(results) == 3  # First + second + third attack
        assert attacker.fighting == victim
    finally:
        # Restore original function
        rng_mm.number_percent = original_number_percent


def test_multi_hit_with_slow():
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit
    attacker.damroll = 1
    attacker.second_attack_skill = 100  # Normally would always succeed
    attacker.third_attack_skill = 100  # Normally would always succeed
    victim.hit = 10

    # Add slow affect
    attacker.add_affect(AffectFlag.SLOW)

    results = combat_engine.multi_hit(attacker, victim)
    # Slow reduces second attack chance and prevents third attack entirely
    assert len(results) >= 1  # Always get first attack
    # Second attack chance halved, third attack prevented


def test_multi_hit_victim_dies_early():
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit
    attacker.damroll = 5
    attacker.second_attack_skill = 100  # Would normally get second attack
    victim.hit = 3  # Dies on first hit

    results = combat_engine.multi_hit(attacker, victim)
    assert len(results) == 1
    assert results[0] == "You kill Victim."
    assert attacker.fighting is None  # Fighting cleared on death
    assert victim.fighting is None


def test_ac_mapping_and_sign_semantics():
    # Mapping: NONE/unarmed→BASH, BASH→BASH, PIERCE→PIERCE, SLASH→SLASH, FIRE→EXOTIC
    assert combat_engine.ac_index_for_dam_type(DamageType.NONE) == AC_BASH
    assert combat_engine.ac_index_for_dam_type(DamageType.BASH) == AC_BASH
    assert combat_engine.ac_index_for_dam_type(DamageType.PIERCE) == AC_PIERCE
    assert combat_engine.ac_index_for_dam_type(DamageType.SLASH) == AC_SLASH
    assert combat_engine.ac_index_for_dam_type(DamageType.FIRE) == AC_EXOTIC

    # AC is better when more negative
    assert combat_engine.is_better_ac(-10, -5)
    assert combat_engine.is_better_ac(-1, 5)
    assert not combat_engine.is_better_ac(5, 0)


def test_ac_influences_hit_chance(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = 10
    attacker.damroll = 3
    attacker.dam_type = int(DamageType.BASH)

    # Fix roll to 60 for deterministic checks
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 60)

    # No armor: base to_hit = 50 + 10 = 60 → hit on 60
    victim.armor = [0, 0, 0, 0]
    victim.hit = 10
    out = process_command(attacker, "kill victim")
    # ROM damage: base 5 + damroll 3 = 8 total
    assert out == "You hit Victim for 8 damage. That really did HURT!"

    # Strong negative AC on BASH index lowers to_hit: victim.armor[AC_BASH] = -22 → +(-22//2) = -11 → 49 → miss
    victim.hit = 50
    victim.armor[AC_BASH] = -22
    out = process_command(attacker, "kill victim")
    assert out == "You miss Victim."

    # Positive AC raises to_hit: +20 → +(20//2)=+10 → 70 → hit
    victim.hit = 50
    victim.armor[AC_BASH] = 20
    out = process_command(attacker, "kill victim")
    assert out.startswith("You hit")


def test_visibility_and_position_modifiers(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = 10
    attacker.damroll = 3
    attacker.dam_type = int(DamageType.BASH)
    victim.armor = [0, 0, 0, 0]
    victim.hit = 50

    # At roll 60, baseline to_hit=60 → hit; invisible should make it miss
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 60)
    out = process_command(attacker, "kill victim")
    assert out.startswith("You hit")
    victim.hit = 50
    victim.add_affect(AffectFlag.INVISIBLE)
    out = process_command(attacker, "kill victim")
    assert out == "You miss Victim."

    # Positional: roll 62; sleeping target grants +10 effective AC mods (+4 +6)
    victim.hit = 50
    victim.remove_affect(AffectFlag.INVISIBLE)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 62)
    victim.position = Position.SLEEPING
    out = process_command(attacker, "kill victim")
    assert out.startswith("You hit")


def test_riv_scaling_applies_before_side_effects(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = 100
    attacker.damroll = 0  # Set to 0 to make calculation more predictable
    attacker.dam_type = int(DamageType.BASH)
    victim.hit = 50

    captured: list[int] = []

    def on_hit(a, v, d):
        captured.append(d)

    monkeypatch.setattr(combat_engine, "on_hit_effects", on_hit)

    # With damroll=0, we get base unarmed damage + 0 damroll bonus
    # Then RIV resistance should reduce it by 1/3
    victim.res_flags = int(ResFlag.BASH)
    out = process_command(attacker, "kill victim")

    # The exact damage will depend on RNG, but it should be RIV-scaled
    assert "You hit Victim for" in out and "damage." in out

    # More importantly, check that on_hit_effects received the scaled damage
    assert len(captured) == 1
    assert captured[0] > 0  # Should have some damage after RIV scaling
    # ROM calculation: base 5, resistance: 5 - 5//3 = 5 - 1 = 4
    assert captured[-1] == 4

    # Vulnerable: dam += dam/2 → 5 + 2 = 7
    victim.hit = 50
    victim.res_flags = 0
    victim.vuln_flags = int(VulnFlag.BASH)
    out = process_command(attacker, "kill victim")
    assert out == "You hit Victim for 7 damage. That really did HURT!"
    assert captured[-1] == 7

    # Immune: dam = 0
    victim.hit = 50
    victim.vuln_flags = 0
    victim.imm_flags = int(ImmFlag.BASH)
    out = process_command(attacker, "kill victim")
    assert out == "Your attack has no effect."
    assert captured[-1] == 0
