from mud.advancement import exp_per_level, gain_exp
from mud.models.character import Character

def test_gain_exp_levels_character():
    char = Character(level=1, ch_class=0, race=0, exp=0)
    base = exp_per_level(char)
    char.exp = base
    gain_exp(char, base)
    assert char.level == 2

def test_exp_per_level_applies_modifiers():
    human = Character(level=1, ch_class=3, race=0, exp=0)
    elf = Character(level=1, ch_class=3, race=1, exp=0)
    assert exp_per_level(elf) > exp_per_level(human)
