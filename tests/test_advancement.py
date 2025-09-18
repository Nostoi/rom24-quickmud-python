from pathlib import Path

from mud.advancement import exp_per_level, gain_exp
from mud.commands.advancement import do_practice, do_train
from mud.models import Room
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.mob import MobIndex
from mud.skills.registry import load_skills, skill_registry
from mud.spawning.templates import MobInstance

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


def _load_fireball() -> None:
    skill_registry.skills.clear()
    skill_registry.handlers.clear()
    load_skills(Path("data/skills.json"))


def _make_trainer() -> MobInstance:
    trainer_proto = MobIndex(vnum=1000, act_flags="K")
    trainer = MobInstance.from_prototype(trainer_proto)
    trainer.position = Position.STANDING
    return trainer


def test_practice_requires_trainer_and_caps():
    _load_fireball()
    skill = skill_registry.get("fireball")
    skill.rating[0] = 4

    room = Room(vnum=1, name="Practice Room")
    char = Character(
        name="Learner",
        practice=2,
        ch_class=0,
        is_npc=False,
        room=room,
        perm_stat=[13, 25, 13, 13, 13],
        mod_stat=[0, 0, 0, 0, 0],
        skills={"fireball": 74},
    )
    room.people.append(char)

    msg = do_practice(char, "fireball")
    assert msg == "You can't do that here."
    assert char.practice == 2

    trainer = _make_trainer()
    trainer.position = Position.SLEEPING
    room.people.append(trainer)
    msg = do_practice(char, "fireball")
    assert msg == "You can't do that here."
    assert char.practice == 2

    trainer.position = Position.STANDING
    msg = do_practice(char, "fireball")
    assert msg == "You are now learned at fireball."
    assert char.practice == 1
    assert char.skills["fireball"] == char.skill_adept_cap()


def test_practice_applies_int_based_gain():
    _load_fireball()
    skill = skill_registry.get("fireball")
    skill.rating[0] = 4

    room = Room(vnum=2, name="Practice Hall")
    char = Character(
        name="Scholar",
        practice=1,
        ch_class=0,
        is_npc=False,
        room=room,
        perm_stat=[13, 18, 13, 13, 13],
        mod_stat=[0, 0, 0, 0, 0],
        skills={"fireball": 1},
    )
    room.people.extend([char, _make_trainer()])

    learn_rate = char.get_int_learn_rate()
    msg = do_practice(char, "fireball")
    assert msg == "You practice fireball."
    expected = min(char.skill_adept_cap(), 1 + max(1, learn_rate // 4))
    assert char.skills["fireball"] == expected
    assert char.practice == 0


def test_practice_rejects_unknown_skill():
    _load_fireball()
    skill = skill_registry.get("fireball")
    skill.rating[0] = 4

    room = Room(vnum=3, name="Hallway")
    char = Character(
        name="Newbie",
        practice=1,
        ch_class=0,
        is_npc=False,
        room=room,
        perm_stat=[13, 13, 13, 13, 13],
        mod_stat=[0, 0, 0, 0, 0],
        skills={},
    )
    room.people.extend([char, _make_trainer()])

    msg = do_practice(char, "fireball")
    assert msg == "You can't practice that."
    assert char.practice == 1
    assert "fireball" not in char.skills


def test_train_command_increases_stats():
    char = Character(practice=0, train=1)
    msg = do_train(char, "hp")
    assert char.train == 0
    assert char.max_hit > 0
    assert "train your hp" in msg
