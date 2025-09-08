from mud.world import initialize_world, create_test_character
from mud.commands import process_command
from mud.models.constants import Position, DamageType, AC_PIERCE, AC_BASH, AC_SLASH, AC_EXOTIC
from mud.combat import engine as combat_engine


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


def test_attack_misses_target():
    attacker, victim = setup_combat()
    attacker.hitroll = -100  # guarantee miss
    victim.hit = 10
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
