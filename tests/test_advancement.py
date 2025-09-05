from pathlib import Path

from mud.advancement import exp_per_level, gain_exp
from mud.commands.advancement import do_practice, do_train
from mud.models.character import Character
from mud.skills.registry import load_skills, skill_registry

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


def test_gain_exp_increases_stats_and_sessions():
    char = Character(level=1, ch_class=0, race=0, exp=0,
                     max_hit=20, max_mana=20, max_move=20,
                     practice=0, train=0)
    base = exp_per_level(char)
    char.exp = base
    gain_exp(char, base)
    assert char.level == 2
    assert char.max_hit > 20
    assert char.practice > 0
    assert char.train > 0


def test_practice_and_train_commands():
    skill_registry.skills.clear()
    load_skills(Path("data/skills.json"))
    char = Character(practice=1, train=1)
    msg = do_practice(char, "fireball")
    assert char.practice == 0
    assert char.skills["fireball"] == 25
    assert "practice fireball" in msg
    msg = do_train(char, "hp")
    assert char.train == 0
    assert char.max_hit > 0
    assert "train your hp" in msg
