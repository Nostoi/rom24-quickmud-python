from pathlib import Path

from mud.advancement import (
    BASE_XP_PER_LEVEL,
    ROM_NEWLINE,
    advance_level,
    exp_per_level,
    exp_per_level_for_creation,
    gain_exp,
)
from mud.commands.advancement import do_practice, do_train
from mud.models import Room
from mud.models.character import Character, PCData
from mud.models.constants import Position
from mud.models.classes import CLASS_TABLE
from mud.models.mob import MobIndex
from mud.models.races import list_playable_races
from mud.skills.registry import load_skills, skill_registry
from mud.spawning.templates import MobInstance
from mud.wiznet import WiznetFlag


def test_gain_exp_levels_character():
    char = Character(level=1, ch_class=0, race=0, exp=0, is_npc=False)
    base = exp_per_level(char)
    char.exp = base
    gain_exp(char, base)
    assert char.level == 2


def test_exp_per_level_applies_modifiers():
    low_points = 39
    human_low = Character(
        level=1,
        ch_class=3,
        race=0,
        exp=0,
        creation_points=low_points,
        pcdata=PCData(points=low_points),
        is_npc=False,
    )
    elf_low = Character(
        level=1,
        ch_class=3,
        race=1,
        exp=0,
        creation_points=low_points,
        pcdata=PCData(points=low_points),
        is_npc=False,
    )

    assert exp_per_level(human_low) == BASE_XP_PER_LEVEL
    assert exp_per_level(elf_low) == BASE_XP_PER_LEVEL

    base_points = 40
    human = Character(
        level=1,
        ch_class=3,
        race=0,
        exp=0,
        creation_points=base_points,
        pcdata=PCData(points=base_points),
        is_npc=False,
    )
    elf = Character(
        level=1,
        ch_class=3,
        race=1,
        exp=0,
        creation_points=base_points,
        pcdata=PCData(points=base_points),
        is_npc=False,
    )

    assert exp_per_level(elf) > exp_per_level(human)


def test_gain_exp_uses_creation_point_curve():
    low_points = 40
    high_points = 80

    low_char = Character(
        level=1,
        ch_class=0,
        race=0,
        exp=0,
        creation_points=low_points,
        pcdata=PCData(points=low_points),
        is_npc=False,
    )
    high_char = Character(
        level=1,
        ch_class=0,
        race=0,
        exp=0,
        creation_points=high_points,
        pcdata=PCData(points=high_points),
        is_npc=False,
    )

    low_base = exp_per_level(low_char)
    high_base = exp_per_level(high_char)

    assert high_base > low_base

    low_char.exp = low_base
    gain_exp(low_char, low_base)
    assert low_char.level == 2

    high_char.exp = low_base
    gain_exp(high_char, low_base)

    assert high_char.level == 1
    assert high_char.exp == max(high_base, low_base * 2)


def test_gain_exp_increases_stats_and_sessions():
    char = Character(
        level=1,
        ch_class=0,
        race=0,
        exp=0,
        max_hit=20,
        max_mana=20,
        max_move=20,
        practice=0,
        train=0,
        is_npc=False,
    )
    base = exp_per_level(char)
    char.exp = base
    gain_exp(char, base)
    assert char.level == 2
    assert char.max_hit > 20
    assert char.practice > 0
    assert char.train > 0


def test_gain_exp_honors_creation_point_floor():
    creation_points = 80
    race_meta = list_playable_races()[0]
    class_meta = CLASS_TABLE[0]
    floor = exp_per_level_for_creation(race_meta, class_meta, creation_points)
    char = Character(
        level=10,
        ch_class=0,
        race=0,
        exp=floor + 2000,
        creation_points=creation_points,
        pcdata=PCData(points=creation_points),
        is_npc=False,
    )

    gain_exp(char, -50000)

    assert char.exp == floor


def test_gain_exp_emits_levelup_messages(monkeypatch):
    captured: dict[str, object] = {}

    def fake_wiznet(message, sender, obj, flag, flag_skip, min_level):
        captured["message"] = message
        captured["sender"] = sender
        captured["flag"] = flag
        captured["min_level"] = min_level

    saved: dict[str, Character] = {}

    def fake_save(character):
        saved["char"] = character

    monkeypatch.setattr("mud.advancement.wiznet", fake_wiznet)
    monkeypatch.setattr("mud.account.account_manager.save_character", fake_save)

    base_points = 40
    char = Character(
        level=1,
        ch_class=0,
        race=0,
        exp=0,
        creation_points=base_points,
        pcdata=PCData(points=base_points),
        is_npc=False,
    )
    base = exp_per_level(char)
    char.exp = base

    gain_exp(char, base)

    assert char.level == 2
    assert "{GYou raise a level!!  {x" in char.messages
    assert captured["message"] == "$N has attained level 2!"
    assert captured["sender"] is char
    assert captured["flag"] == WiznetFlag.WIZ_LEVELS
    assert captured["min_level"] == 0
    assert saved["char"] is char


def test_advance_level_updates_permanent_stats(monkeypatch):
    now = 10_000
    monkeypatch.setattr("mud.advancement.time.time", lambda: now)

    pcdata = PCData(perm_hit=5, perm_mana=7, perm_move=9, last_level=0)
    char = Character(
        ch_class=0,
        is_npc=False,
        pcdata=pcdata,
        played=3600,
        logon=now - 1200,
        max_hit=30,
        max_mana=40,
        max_move=50,
        practice=1,
        train=0,
    )

    advance_level(char)

    assert pcdata.last_level == (3600 + 1200) // 3600
    assert pcdata.perm_hit == 5 + 8
    assert pcdata.perm_mana == 7 + 6
    assert pcdata.perm_move == 9 + 4
    assert char.max_hit == 38
    assert char.max_mana == 46
    assert char.max_move == 54
    assert char.practice == 3
    assert char.train == 1


def test_advance_level_reports_gains(monkeypatch):
    monkeypatch.setattr("mud.advancement.time.time", lambda: 5000)

    pcdata = PCData()
    char = Character(
        ch_class=1,
        is_npc=False,
        pcdata=pcdata,
    )

    advance_level(char)

    expected = f"You gain 6 hit points, 8 mana, 4 move, and 2 practices.{ROM_NEWLINE}"
    assert expected in char.messages


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


def test_practice_lists_known_skills_with_percentages():
    _load_fireball()

    room = Room(vnum=4, name="Arcane Study")
    char = Character(
        name="Apprentice",
        practice=3,
        ch_class=0,
        level=20,
        is_npc=False,
        room=room,
        skills={
            "acid blast": 60,  # gated by level; should not appear
            "armor": 55,
            "blindness": 72,
            "burning hands": 80,
            "detect magic": 40,
            "magic missile": 35,
            "colour spray": 0,
        },
    )
    room.people.append(char)

    msg = do_practice(char, "")
    expected_entries = [
        ("armor", 55),
        ("blindness", 72),
        ("burning hands", 80),
        ("detect magic", 40),
        ("magic missile", 35),
    ]
    expected_parts: list[str] = []
    col = 0
    for name, learned in expected_entries:
        expected_parts.append(f"{name:<18} {learned:3d}%  ")
        col += 1
        if col % 3 == 0:
            expected_parts.append("\n")
    if col % 3 != 0:
        expected_parts.append("\n")
    expected_parts.append("You have 3 practice sessions left.\n")

    assert msg == "".join(expected_parts)
    assert "acid blast" not in msg


def test_train_command_increases_stats():
    char = Character(practice=0, train=1)
    msg = do_train(char, "hp")
    assert char.train == 0
    assert char.max_hit > 0
    assert "train your hp" in msg
