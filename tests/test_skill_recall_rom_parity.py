"""
ROM parity tests for recall skill.

Tests ROM src/act_move.c:1563-1628 (do_recall) implementation.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag, RoomFlag, ROOM_VNUM_TEMPLE
from mud.registry import room_registry
from mud.skills.handlers import recall
from mud.world import initialize_world


TEST_ROOM_VNUM = 3010
TEST_MOB_VNUM = 3000


@pytest.fixture
def recalling_char(movable_char_factory):
    """Create a character with recall skill."""
    initialize_world("area/area.lst")
    char = movable_char_factory("warrior", TEST_ROOM_VNUM)
    char.skills["recall"] = 75
    char.move = 100
    return char


def test_recall_npc_without_pet_flag_blocked(movable_mob_factory):
    """ROM L1569-1573: NPCs without ACT_PET cannot recall."""
    initialize_world("area/area.lst")
    mob = movable_mob_factory(TEST_MOB_VNUM, TEST_ROOM_VNUM)

    result = recall(mob)

    assert "only players can recall" in result.lower()


def test_recall_sends_prayer_message_to_room(recalling_char):
    """ROM L1575: act('$n prays for transportation!', ch, 0, 0, TO_ROOM)"""
    recall(recalling_char)


def test_recall_moves_to_temple(recalling_char):
    """ROM L1617-1621: char_from_room/char_to_room sequence."""
    assert recalling_char.room.vnum == TEST_ROOM_VNUM

    recall(recalling_char)

    assert recalling_char.room.vnum == ROOM_VNUM_TEMPLE


def test_recall_halves_movement_points(recalling_char):
    """ROM L1617: ch->move /= 2"""
    recalling_char.move = 100

    recall(recalling_char)

    assert recalling_char.move == 50


def test_recall_blocked_by_no_recall_flag(recalling_char):
    """ROM L1586-1591: ROOM_NO_RECALL blocks recall."""
    room = recalling_char.room
    room.room_flags = int(RoomFlag.ROOM_NO_RECALL)

    result = recall(recalling_char)

    assert "mota has forsaken you" in result.lower()
    assert recalling_char.room.vnum == TEST_ROOM_VNUM


def test_recall_blocked_by_curse_affect(recalling_char):
    """ROM L1587: IS_AFFECTED(ch, AFF_CURSE) blocks recall."""
    recalling_char.affected_by = int(AffectFlag.CURSE)

    result = recall(recalling_char)

    assert "mota has forsaken you" in result.lower()
    assert recalling_char.room.vnum == TEST_ROOM_VNUM


def test_recall_from_combat_with_low_skill_fails(recalling_char, movable_mob_factory, monkeypatch):
    """ROM L1599-1606: Skill check in combat, failure sets WAIT_STATE."""
    from mud.utils import rng_mm

    mob = movable_mob_factory(TEST_MOB_VNUM, TEST_ROOM_VNUM)
    recalling_char.fighting = mob

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 50)

    result = recall(recalling_char)

    assert "you failed" in result.lower()
    assert recalling_char.room.vnum == TEST_ROOM_VNUM
    assert recalling_char.wait == 4


def test_recall_from_combat_success_loses_exp(recalling_char, movable_mob_factory, monkeypatch):
    """ROM L1608-1612: Successful combat recall loses 25 exp (with desc) or 50 (without)."""
    from mud.utils import rng_mm

    mob = movable_mob_factory(TEST_MOB_VNUM, TEST_ROOM_VNUM)
    recalling_char.fighting = mob
    recalling_char.exp = 2000
    recalling_char.desc = "has_descriptor"

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 70)

    result = recall(recalling_char)

    assert "lose 25 exps" in result.lower()
    assert recalling_char.exp == 1975
    assert recalling_char.room.vnum == ROOM_VNUM_TEMPLE


def test_recall_from_combat_stops_fighting(recalling_char, movable_mob_factory, monkeypatch):
    """ROM L1613: stop_fighting(ch, TRUE) called on success."""
    from mud.utils import rng_mm

    mob = movable_mob_factory(TEST_MOB_VNUM, TEST_ROOM_VNUM)
    recalling_char.fighting = mob

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 70)

    recall(recalling_char)

    assert recalling_char.fighting is None


def test_recall_at_temple_does_nothing(movable_char_factory):
    """ROM L1583-1584: if (ch->in_room == location) return"""
    initialize_world("area/area.lst")
    char = movable_char_factory("warrior", ROOM_VNUM_TEMPLE)
    char.skills["recall"] = 75

    result = recall(char)

    assert result == ""
    assert char.room.vnum == ROOM_VNUM_TEMPLE


def test_recall_pet_follows_master(recalling_char, movable_mob_factory, monkeypatch):
    """ROM L1624-1625: if (ch->pet != NULL) do_recall(ch->pet, '')"""
    from mud.models.constants import ActFlag
    from mud.utils import rng_mm

    pet = movable_mob_factory(TEST_MOB_VNUM, TEST_ROOM_VNUM)
    pet.act = int(ActFlag.PET)
    recalling_char.pet = pet

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 70)

    recall(recalling_char)

    assert recalling_char.room.vnum == ROOM_VNUM_TEMPLE
    assert pet.room.vnum == ROOM_VNUM_TEMPLE


def test_recall_requires_caster():
    """Verify recall raises ValueError if caster is None."""
    with pytest.raises(ValueError, match="recall requires a caster"):
        recall(None)


def test_recall_missing_temple_shows_lost_message(recalling_char):
    """ROM L1577-1581: get_room_index(ROOM_VNUM_TEMPLE) NULL check."""
    temple_room = room_registry.get(ROOM_VNUM_TEMPLE)

    try:
        if ROOM_VNUM_TEMPLE in room_registry:
            del room_registry[ROOM_VNUM_TEMPLE]

        result = recall(recalling_char)

        assert "completely lost" in result.lower()
    finally:
        if temple_room and ROOM_VNUM_TEMPLE not in room_registry:
            room_registry[ROOM_VNUM_TEMPLE] = temple_room
