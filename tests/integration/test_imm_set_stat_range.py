"""TRAIN-004 / SET-002 — `set char <name> <stat> <value>` clamps to the
victim's race/class-specific `get_max_train`, not a broken fallback.

ROM Reference:
- src/act_wiz.c:3400-3496 (do_mset stat fields gate on get_max_train)
- src/handler.c:876 (get_max_train — race max + prime-class bonus)

The pre-existing `mud.handler.get_max_train` compared the int `ch.race`
index against PC-race *names* (and read a non-existent `class_num`), so it
fell through to a hardcoded fallback for every real character — capping
every stat at that fallback regardless of race. A dwarf's STR max is 20.
"""

from __future__ import annotations

import pytest

from mud.commands.imm_set import do_mset
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import STAT_STR
from mud.models.races import race_lookup
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture
def setter_and_dwarf():
    # INV-046: do_mset resolves its victim via the real get_char_world
    # (src/handler.c:2222-2243), which walks character_registry and skips
    # roomless chars — so both chars live in a registered room, not in the
    # retired phantom `registry.char_list`.
    room = Room(vnum=98765, name="Set Room", description="Set Room")
    room_registry[room.vnum] = room

    setter = Character(name="Imm", level=60, trust=60, is_npc=False)
    setter.pcdata = PCData()

    dwarf = Character(name="Gimli", level=10, is_npc=False)
    dwarf.pcdata = PCData()
    dwarf.race = race_lookup("dwarf")  # dwarf max_stats = (20, 16, 19, 14, 21)
    dwarf.ch_class = 0  # mage — STR is non-prime, so its cap is the raw race max
    dwarf.perm_stat = [13, 13, 13, 13, 13]

    for ch in (setter, dwarf):
        room.add_character(ch)
        character_registry.append(ch)
    try:
        yield setter, dwarf
    finally:
        for ch in (setter, dwarf):
            if ch in room.people:
                room.people.remove(ch)
            if ch in character_registry:
                character_registry.remove(ch)
        room_registry.pop(room.vnum, None)


def test_set_stat_uses_race_max_not_fallback(setter_and_dwarf):
    """A dwarf's STR may be set up to 20 (its race max), not capped lower.

    mirrors ROM src/act_wiz.c:3400 — `value > get_max_train(victim, STAT_STR)`
    rejects only values above the dwarf's true max of 20.
    """
    setter, dwarf = setter_and_dwarf

    # 20 is exactly the dwarf STR max — must be accepted (ROM returns no error).
    result = do_mset(setter, "Gimli str 20")
    assert result == "", f"setting dwarf STR to its race max 20 must succeed, got {result!r}"
    assert dwarf.perm_stat[STAT_STR] == 20

    # 21 exceeds the dwarf STR max — must be rejected with the 3..max range.
    rejected = do_mset(setter, "Gimli str 21")
    assert "3 to 20" in rejected, f"out-of-range STR must report 3 to 20, got {rejected!r}"
    assert dwarf.perm_stat[STAT_STR] == 20, "rejected set must not mutate the stat"
