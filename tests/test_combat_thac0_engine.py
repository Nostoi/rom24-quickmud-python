from mud.world import initialize_world, create_test_character
from mud.commands import process_command
from mud.combat import engine as combat_engine
from mud.models.constants import DamageType


def setup_thac0_env():
    initialize_world('area/area.lst')
    atk = create_test_character('Atk', 3001)
    vic = create_test_character('Vic', 3001)
    vic.armor = [0, 0, 0, 0]
    atk.dam_type = int(DamageType.BASH)
    atk.damroll = 3
    return atk, vic


def test_thac0_path_hit_and_miss(monkeypatch):
    # Enable THAC0 feature flag (patch engine's imported flag)
    monkeypatch.setattr('mud.combat.engine.COMBAT_USE_THAC0', True)

    # Deterministic dicerolls
    monkeypatch.setattr('mud.utils.rng_mm.number_bits', lambda bits: 10)

    # Strong attacker (warrior32) should hit with diceroll 10
    atk, vic = setup_thac0_env()
    atk.ch_class = 3  # warrior
    atk.level = 32
    atk.hitroll = 0
    vic.hit = 10
    out = process_command(atk, 'kill vic')
    assert out.startswith('You hit')

    # Weak attacker (mage0) should miss with same diceroll
    atk, vic = setup_thac0_env()
    atk.ch_class = 0  # mage
    atk.level = 0
    atk.hitroll = 0
    vic.hit = 10
    out = process_command(atk, 'kill vic')
    assert out == 'You miss Vic.'

    # Natural 0 always misses
    monkeypatch.setattr('mud.utils.rng_mm.number_bits', lambda bits: 0)
    atk, vic = setup_thac0_env()
    atk.ch_class = 3
    atk.level = 32
    vic.hit = 10
    out = process_command(atk, 'kill vic')
    assert out == 'You miss Vic.'
