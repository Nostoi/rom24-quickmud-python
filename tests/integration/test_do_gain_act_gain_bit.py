"""Regression for PARALLEL-003a: do_gain read the wrong ACT_GAIN bit.

`mud/commands/remaining_rom.py:211` in `do_gain` declared inline:
- `ACT_GAIN = 0x00100000` (bit 20)

Canonical: `ActFlag.GAIN = 1<<27 = 0x8000000` (ROM letter `bb` per
`src/merc.h`). Mirrored at `mud/models/constants.py:436`.

Pre-fix: an NPC carrying the canonical `ActFlag.GAIN` (the ROM "trainer"
mob act bit) was not recognized as a trainer — `do_gain` returned
"You can't do that here." even when a real trainer stood in the room.
Conversely, a mob with bit 20 set (unrelated ROM macro) was spuriously
treated as a trainer.

ROM C: `src/skills.c do_gain` (lines 44+) scans the room for a mob
with `IS_SET(mob->act, ACT_GAIN)`.
"""

from __future__ import annotations

import pytest

from mud.advancement import exp_per_level
from mud.commands.remaining_rom import do_gain
from mud.models.character import Character, PCData
from mud.models.constants import ActFlag
from mud.models.room import Room
from mud.registry import room_registry


def _place_trainer(room: Room) -> Character:
    trainer = Character(name="trainer", level=50, is_npc=True, room=room)
    trainer.act = int(ActFlag.GAIN)
    trainer.short_descr = "the master trainer"
    room.people.append(trainer)
    return trainer


@pytest.fixture
def gain_room():
    room = Room(
        vnum=10010,
        name="Trainer Hall",
        description="A trainer hall.",
        room_flags=0,
        sector_type=0,
    )
    room.people = []
    room_registry[10010] = room
    yield room
    room_registry.pop(10010, None)


@pytest.fixture
def learner(gain_room):
    char = Character(name="Learner", level=10, is_npc=False, room=gain_room)
    gain_room.people.append(char)
    return char


def test_trainer_with_canonical_act_gain_is_found(learner: Character, gain_room: Room) -> None:
    """NPC with canonical ActFlag.GAIN should be recognized as a trainer."""
    trainer = Character(name="trainer", level=50, is_npc=True, room=gain_room)
    trainer.act = int(ActFlag.GAIN)  # canonical 1<<27
    trainer.short_descr = "the master trainer"
    gain_room.people.append(trainer)

    result = do_gain(learner, "")

    # Trainer found → returns the trainer's "Pardon me?" line, NOT "You can't do that here."
    assert "can't do that here" not in result.lower()
    assert "pardon me" in result.lower() or "trainer" in result.lower()


def test_no_trainer_returns_cant_do_that(learner: Character, gain_room: Room) -> None:
    """With no ActFlag.GAIN mob in the room, do_gain rejects."""
    bystander = Character(name="bystander", level=10, is_npc=True, room=gain_room)
    bystander.act = 0
    gain_room.people.append(bystander)

    result = do_gain(learner, "")

    assert "can't do that here" in result.lower()


def test_gain_points_spends_two_trains_to_lower_points_and_recalcs_exp(learner: Character, gain_room: Room) -> None:
    """GAIN-002 — mirrors ROM `src/skills.c:149-172`.

    `gain points` trades 2 `train` to **lower** creation `points` by 1 (which
    lowers `exp_per_level`, making leveling easier) and recomputes
    `exp = exp_per_level(ch, points) * level`. Python had it backwards: it
    *raised* points by 1, skipped the `points <= 40` gate, and never recalculated
    exp.
    """

    _place_trainer(gain_room)
    learner.pcdata = PCData()
    learner.pcdata.points = 50
    learner.train = 5
    learner.exp = 0

    result = do_gain(learner, "points")

    # ROM: points decremented, 2 trains spent.
    assert learner.pcdata.points == 49
    assert learner.train == 3
    # ROM: exp = exp_per_level(ch, points) * level, computed with the NEW points.
    assert learner.exp == exp_per_level(learner) * learner.level
    assert "feel more at ease with your skills" in result
    assert "gain a creation point" not in result


def test_gain_points_refuses_when_points_at_or_below_40(learner: Character, gain_room: Room) -> None:
    """GAIN-002 — mirrors ROM `src/skills.c:158-163`.

    ROM refuses `gain points` when `points <= 40` ("There would be no point in
    that.") with no state change. Python omitted this gate entirely.
    """

    _place_trainer(gain_room)
    learner.pcdata = PCData()
    learner.pcdata.points = 40
    learner.train = 5

    result = do_gain(learner, "points")

    assert "no point in that" in result.lower()
    assert learner.pcdata.points == 40  # unchanged
    assert learner.train == 5  # unchanged


def _make_learner_mage(learner: Character) -> None:
    # The skill registry loads from data/skills.json (the server does this at
    # startup); the static group table is always available. Load skills
    # idempotently so the skill branch / spell gate resolve in-test.
    from pathlib import Path

    from mud.skills.registry import load_skills, skill_registry

    if not skill_registry.skills:
        load_skills(Path("data/skills.json"))

    learner.ch_class = 0  # mage
    learner.pcdata = PCData()
    learner.pcdata.group_known = ()
    learner.pcdata.learned = {}


def test_gain_group_learns_group_and_component_skills_and_deducts_train(learner: Character, gain_room: Room) -> None:
    """GAIN-001 — mirrors ROM `src/skills.c:174-206` + `gn_add` (993-1004).

    Gaining a group marks it known, recursively grants its component skills
    (`gn_add` → `group_add`), and deducts `train` by the per-class rating.
    """
    _place_trainer(gain_room)
    _make_learner_mage(learner)
    learner.train = 10

    # "beguiling": class-0 cost 4, component skills calm / charm person / sleep.
    result = do_gain(learner, "beguiling")

    assert "trains you in the art of beguiling" in result
    assert "beguiling" in learner.pcdata.group_known
    assert learner.pcdata.learned.get("calm") == 1
    assert learner.pcdata.learned.get("charm person") == 1
    assert learner.pcdata.learned.get("sleep") == 1
    assert learner.train == 6  # 10 - 4


def test_gain_skill_learns_skill_and_deducts_train(learner: Character, gain_room: Room) -> None:
    """GAIN-001 — mirrors ROM `src/skills.c:208-244` (skill branch)."""
    _place_trainer(gain_room)
    _make_learner_mage(learner)
    learner.train = 5

    result = do_gain(learner, "dagger")  # class-0 rate 2, type skill (non-spell)

    assert "trains you in the art of dagger" in result
    assert learner.pcdata.learned.get("dagger") == 1
    assert learner.train == 3


def test_gain_spell_directly_is_refused_must_learn_full_group(learner: Character, gain_room: Room) -> None:
    """GAIN-001 — mirrors ROM `src/skills.c:211-216`.

    A skill whose `spell_fun != spell_null` (Python `Skill.type == "spell"`)
    cannot be gained directly — only via its group.
    """
    _place_trainer(gain_room)
    _make_learner_mage(learner)
    learner.train = 50

    result = do_gain(learner, "sleep")  # a spell

    assert "must learn the full group" in result.lower()
    assert learner.pcdata.learned.get("sleep", 0) == 0
    assert learner.train == 50


def test_gain_group_refused_when_insufficient_train(learner: Character, gain_room: Room) -> None:
    """GAIN-001 — mirrors ROM `src/skills.c:193-198`."""
    _place_trainer(gain_room)
    _make_learner_mage(learner)
    learner.train = 2  # beguiling costs 4

    result = do_gain(learner, "beguiling")

    assert "not yet ready for that group" in result.lower()
    assert "beguiling" not in learner.pcdata.group_known
    assert learner.train == 2


def test_gain_already_known_group_refused(learner: Character, gain_room: Room) -> None:
    """GAIN-001 — mirrors ROM `src/skills.c:179-184`."""
    _place_trainer(gain_room)
    _make_learner_mage(learner)
    learner.pcdata.group_known = ("beguiling",)
    learner.train = 10

    result = do_gain(learner, "beguiling")

    assert "already know that group" in result.lower()
    assert learner.train == 10


def test_gain_list_shows_gainable_groups_and_nonspell_skills(learner: Character, gain_room: Room) -> None:
    """GAIN-003 — mirrors ROM `src/skills.c:74-131`.

    `gain list` shows, in two sections, every group / non-spell skill the player
    does NOT know whose per-class rating is > 0, with its cost.
    """
    _place_trainer(gain_room)
    _make_learner_mage(learner)

    result = do_gain(learner, "list")

    assert "group" in result and "skill" in result and "cost" in result
    # a gainable mage group + its cost
    assert "beguiling" in result
    assert "4" in result
    # a gainable non-spell skill
    assert "dagger" in result
    # spells are NOT listed in the skill section (they are gained via groups)
    assert "sleep" not in result


def test_gain_list_excludes_known_groups(learner: Character, gain_room: Room) -> None:
    """GAIN-003 — ROM lists only groups the player does NOT already know
    (`!ch->pcdata->group_known[gn]`, `src/skills.c:89`)."""
    _place_trainer(gain_room)
    _make_learner_mage(learner)
    learner.pcdata.group_known = ("beguiling",)

    result = do_gain(learner, "list")

    assert "beguiling" not in result
    # another gainable group still shows
    assert "maladictions" in result


def test_mob_with_old_wrong_bit_is_not_a_trainer(learner: Character, gain_room: Room) -> None:
    """A mob with only the pre-fix wrong bit (0x00100000, bit 20) is NOT a trainer."""
    not_trainer = Character(name="impostor", level=10, is_npc=True, room=gain_room)
    not_trainer.act = 0x00100000  # the old wrong hex
    gain_room.people.append(not_trainer)

    result = do_gain(learner, "")

    assert "can't do that here" in result.lower()
