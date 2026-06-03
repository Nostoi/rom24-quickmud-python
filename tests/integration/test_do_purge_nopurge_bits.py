"""Regression for PARALLEL-006: do_purge read the wrong bits.

`mud/commands/imm_load.py:176-177` in `do_purge` declared inline:
- `ACT_NOPURGE = 0x00002000` (canonical: `ActFlag.NOPURGE = 1<<21 = 0x200000`)
- `ITEM_NOPURGE = 0x00000040` (canonical: `ExtraFlag.NOPURGE = 1<<14 = 0x4000`)

The immortal `purge` command checked unrelated bits, so pre-fix:

- NPCs flagged `ActFlag.NOPURGE` (protected) were purged anyway.
- Objects flagged `ExtraFlag.NOPURGE` (protected) were purged anyway.
- NPCs/objects with unrelated bits matching the wrong hex values
  were spuriously protected from purge.

ROM C: `src/merc.h` defines both as letter macros, mirrored by
`mud/models/constants.py` ActFlag.NOPURGE and ExtraFlag.NOPURGE.
"""

from __future__ import annotations

import pytest

from mud.commands.imm_load import do_purge
from mud.models.character import Character
from mud.models.constants import ActFlag, ExtraFlag
from mud.models.room import Room
from mud.registry import room_registry


class _SimpleObj:
    """Minimal object stub for testing."""

    def __init__(self, vnum: int, extra_flags: int) -> None:
        self.vnum = vnum
        self.extra_flags = extra_flags
        self.in_room = None


@pytest.fixture
def purge_room():
    """Create a test room for purge operations."""
    room = Room(
        vnum=10000, name="Purge Test Room", description="A room for testing purge.", room_flags=0, sector_type=0
    )
    room.people = []
    room.contents = []
    room_registry[10000] = room
    yield room
    room_registry.pop(10000, None)


@pytest.fixture
def immortal(purge_room):
    """Create an immortal in the test room."""
    char = Character(name="TestImmortal", level=50, is_npc=False, room=purge_room)
    purge_room.people.append(char)
    return char


def test_nopurge_npc_is_not_purged(immortal: Character, purge_room: Room) -> None:
    """NPC with ActFlag.NOPURGE set should survive purge."""
    mob = Character(name="protected_mob", level=10, is_npc=True, room=purge_room)
    mob.act = int(ActFlag.NOPURGE)
    purge_room.people.append(mob)

    # Call do_purge with no args (purges room)
    result = do_purge(immortal, "")

    # NPC with NOPURGE should still be in the room
    assert mob in purge_room.people
    assert "Ok." in result


def test_nopurge_object_is_not_purged(immortal: Character, purge_room: Room) -> None:
    """Object with ExtraFlag.NOPURGE set should survive purge."""
    obj = _SimpleObj(vnum=5000, extra_flags=int(ExtraFlag.NOPURGE))
    obj.in_room = purge_room
    purge_room.contents.append(obj)

    # Call do_purge with no args (purges room)
    result = do_purge(immortal, "")

    # Object with NOPURGE should still be in the room
    assert obj in purge_room.contents
    assert "Ok." in result


def test_npc_without_nopurge_is_purged(immortal: Character, purge_room: Room) -> None:
    """NPC without NOPURGE should be purged."""
    mob = Character(name="purgeable_mob", level=10, is_npc=True, room=purge_room)
    mob.act = 0  # No flags
    purge_room.people.append(mob)

    # Call do_purge with no args (purges room)
    result = do_purge(immortal, "")

    # NPC without NOPURGE should be removed
    assert mob not in purge_room.people
    assert "Ok." in result


def test_object_without_nopurge_is_purged(immortal: Character, purge_room: Room) -> None:
    """Object without NOPURGE should be purged."""
    obj = _SimpleObj(vnum=5001, extra_flags=0)
    obj.in_room = purge_room
    purge_room.contents.append(obj)

    # Call do_purge with no args (purges room)
    result = do_purge(immortal, "")

    # Object without NOPURGE should be removed
    assert obj not in purge_room.contents
    assert "Ok." in result
