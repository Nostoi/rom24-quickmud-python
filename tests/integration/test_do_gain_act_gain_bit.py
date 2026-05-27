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

from mud.commands.remaining_rom import do_gain
from mud.models.character import Character
from mud.models.constants import ActFlag
from mud.models.room import Room
from mud.registry import room_registry


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


def test_mob_with_old_wrong_bit_is_not_a_trainer(learner: Character, gain_room: Room) -> None:
    """A mob with only the pre-fix wrong bit (0x00100000, bit 20) is NOT a trainer."""
    not_trainer = Character(name="impostor", level=10, is_npc=True, room=gain_room)
    not_trainer.act = 0x00100000  # the old wrong hex
    gain_room.people.append(not_trainer)

    result = do_gain(learner, "")

    assert "can't do that here" in result.lower()
