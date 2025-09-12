from mud.world import initialize_world, create_test_character
from mud.commands import process_command
from mud.models.constants import DamageType


def setup_function(_):
    initialize_world('area/area.lst')


def _setup_pair():
    attacker = create_test_character('Attacker', 3001)
    victim = create_test_character('Victim', 3001)
    attacker.hitroll = 100
    attacker.damroll = 3
    attacker.dam_type = int(DamageType.BASH)
    victim.armor = [0, 0, 0, 0]
    victim.hit = 50
    return attacker, victim


def test_shield_block_triggers_before_parry_and_dodge(monkeypatch):
    from mud.utils import rng_mm
    attacker, victim = _setup_pair()
    victim.shield_block_chance = 100
    victim.parry_chance = 100
    victim.dodge_chance = 100
    # Ensure percent roll always hits the threshold
    monkeypatch.setattr(rng_mm, 'number_percent', lambda: 1)
    out = process_command(attacker, 'kill victim')
    assert out == 'Victim blocks your attack with a shield.'


def test_parry_triggers_when_no_shield(monkeypatch):
    from mud.utils import rng_mm
    attacker, victim = _setup_pair()
    victim.parry_chance = 100
    monkeypatch.setattr(rng_mm, 'number_percent', lambda: 1)
    out = process_command(attacker, 'kill victim')
    assert out == 'Victim parries your attack.'


def test_dodge_triggers_when_no_shield_or_parry(monkeypatch):
    from mud.utils import rng_mm
    attacker, victim = _setup_pair()
    victim.dodge_chance = 100
    monkeypatch.setattr(rng_mm, 'number_percent', lambda: 1)
    out = process_command(attacker, 'kill victim')
    assert out == 'Victim dodges your attack.'

