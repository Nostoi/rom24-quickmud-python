from mud.world import initialize_world, create_test_character
from mud.commands import process_command
from mud.models.constants import (
    Position,
    DamageType,
    AC_PIERCE,
    AC_BASH,
    AC_SLASH,
    AC_EXOTIC,
    ResFlag,
    ImmFlag,
    VulnFlag,
)
from mud.combat import engine as combat_engine
from mud.models.constants import AffectFlag


def setup_combat():
    initialize_world('area/area.lst')
    room_vnum = 3001
    attacker = create_test_character('Attacker', room_vnum)
    victim = create_test_character('Victim', room_vnum)
    return attacker, victim


def test_attack_damages_but_not_kill():
    attacker, victim = setup_combat()
    attacker.damroll = 3
    attacker.hitroll = 100  # guarantee hit
    victim.hit = 10
    out = process_command(attacker, 'kill victim')
    assert out == 'You hit Victim for 3 damage.'
    assert victim.hit == 7
    assert attacker.position == Position.FIGHTING
    assert victim.position == Position.FIGHTING
    assert victim in attacker.room.people


def test_attack_kills_target():
    attacker, victim = setup_combat()
    attacker.damroll = 5
    attacker.hitroll = 100  # guarantee hit
    victim.hit = 5
    out = process_command(attacker, 'kill victim')
    assert out == 'You kill Victim.'
    assert victim.hit == 0
    assert attacker.position == Position.STANDING
    assert victim.position == Position.DEAD
    assert victim not in attacker.room.people
    assert 'Victim is DEAD!!!' in attacker.messages


def test_attack_misses_target(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = -100  # extremely low hit chance
    victim.hit = 10
    # Guarantee miss deterministically
    monkeypatch.setattr('mud.utils.rng_mm.number_percent', lambda: 100)
    out = process_command(attacker, 'kill victim')
    assert out == 'You miss Victim.'
    assert victim.hit == 10
    assert attacker.position == Position.FIGHTING
    assert victim.position == Position.FIGHTING
    assert victim in attacker.room.people


def test_defense_order_and_early_out(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit roll passes
    attacker.damroll = 3

    calls: list[str] = []

    def shield(a, v):
        calls.append("shield")
        return False

    def parry(a, v):
        calls.append("parry")
        return True  # early-out here

    def dodge(a, v):  # pragma: no cover - should not be called
        calls.append("dodge")
        return False

    monkeypatch.setattr(combat_engine, "check_shield_block", shield)
    monkeypatch.setattr(combat_engine, "check_parry", parry)
    monkeypatch.setattr(combat_engine, "check_dodge", dodge)

    out = process_command(attacker, 'kill victim')
    assert out == 'Victim parries your attack.'
    assert calls == ["shield", "parry"]  # dodge not reached


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
    monkeypatch.setattr('mud.utils.rng_mm.number_percent', lambda: 60)

    # No armor: base to_hit = 50 + 10 = 60 → hit on 60
    victim.armor = [0, 0, 0, 0]
    victim.hit = 10
    out = process_command(attacker, 'kill victim')
    assert out == 'You hit Victim for 3 damage.'

    # Strong negative AC on BASH index lowers to_hit: victim.armor[AC_BASH] = -22 → +(-22//2) = -11 → 49 → miss
    victim.hit = 50
    victim.armor[AC_BASH] = -22
    out = process_command(attacker, 'kill victim')
    assert out == 'You miss Victim.'

    # Positive AC raises to_hit: +20 → +(20//2)=+10 → 70 → hit
    victim.hit = 50
    victim.armor[AC_BASH] = 20
    out = process_command(attacker, 'kill victim')
    assert out.startswith('You hit')


def test_visibility_and_position_modifiers(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = 10
    attacker.damroll = 3
    attacker.dam_type = int(DamageType.BASH)
    victim.armor = [0, 0, 0, 0]
    victim.hit = 50

    # At roll 60, baseline to_hit=60 → hit; invisible should make it miss
    monkeypatch.setattr('mud.utils.rng_mm.number_percent', lambda: 60)
    out = process_command(attacker, 'kill victim')
    assert out.startswith('You hit')
    victim.hit = 50
    victim.add_affect(AffectFlag.INVISIBLE)
    out = process_command(attacker, 'kill victim')
    assert out == 'You miss Victim.'

    # Positional: roll 62; sleeping target grants +10 effective AC mods (+4 +6)
    victim.hit = 50
    victim.remove_affect(AffectFlag.INVISIBLE)
    monkeypatch.setattr('mud.utils.rng_mm.number_percent', lambda: 62)
    victim.position = Position.SLEEPING
    out = process_command(attacker, 'kill victim')
    assert out.startswith('You hit')


def test_riv_scaling_applies_before_side_effects(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = 100
    attacker.damroll = 9
    attacker.dam_type = int(DamageType.BASH)
    victim.hit = 50

    captured: list[int] = []

    def on_hit(a, v, d):
        captured.append(d)

    monkeypatch.setattr(combat_engine, "on_hit_effects", on_hit)

    # Resistant: dam -= dam/3 → 9 - 3 = 6
    victim.res_flags = int(ResFlag.BASH)
    out = process_command(attacker, 'kill victim')
    assert out == 'You hit Victim for 6 damage.'
    assert captured[-1] == 6

    # Vulnerable: dam += dam/2 → 9 + 4 = 13
    victim.hit = 50
    victim.res_flags = 0
    victim.vuln_flags = int(VulnFlag.BASH)
    out = process_command(attacker, 'kill victim')
    assert out == 'You hit Victim for 13 damage.'
    assert captured[-1] == 13

    # Immune: dam = 0
    victim.hit = 50
    victim.vuln_flags = 0
    victim.imm_flags = int(ImmFlag.BASH)
    out = process_command(attacker, 'kill victim')
    assert out == 'You hit Victim for 0 damage.'
    assert captured[-1] == 0
