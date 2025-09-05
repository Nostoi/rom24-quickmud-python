from mud.world import initialize_world, create_test_character
from mud.commands import process_command
from mud.models.constants import Position


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
