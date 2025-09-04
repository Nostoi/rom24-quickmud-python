from mud.world import initialize_world, create_test_character
from mud.commands import process_command


def setup_combat():
    initialize_world('area/area.lst')
    room_vnum = 3001
    attacker = create_test_character('Attacker', room_vnum)
    victim = create_test_character('Victim', room_vnum)
    return attacker, victim


def test_attack_damages_but_not_kill():
    attacker, victim = setup_combat()
    attacker.damroll = 3
    victim.hit = 10
    out = process_command(attacker, 'kill victim')
    assert out == 'You hit Victim for 3 damage.'
    assert victim.hit == 7
    assert victim in attacker.room.people


def test_attack_kills_target():
    attacker, victim = setup_combat()
    attacker.damroll = 5
    victim.hit = 5
    out = process_command(attacker, 'kill victim')
    assert out == 'You kill Victim.'
    assert victim.hit == 0
    assert victim not in attacker.room.people
    assert 'Victim is DEAD!!!' in attacker.messages
