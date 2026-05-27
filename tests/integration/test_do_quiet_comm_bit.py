"""Regression for PARALLEL-003b: do_quiet read the wrong COMM_QUIET bit.

`mud/commands/remaining_rom.py:105` declared module-local:
- `COMM_QUIET = 0x00000004` (bit 2)

Canonical: `CommFlag.QUIET = 1<<0 = 0x1` (ROM letter `A` per
`src/merc.h`). Mirrored at `mud/models/constants.py:467`.

Pre-fix: `do_quiet` toggled bit 2 of `char.comm` rather than bit 0.
If the player already had the canonical `CommFlag.QUIET` set (e.g.
loaded from a save), `do_quiet` saw bit 2 == 0 and turned ON bit 2
(saying "From now on...") instead of OFF bit 0 ("Quiet mode removed.").
Net effect: the toggle disagreed with everything else that reads
the canonical CommFlag.QUIET bit.

ROM C: `src/act_comm.c do_quiet` toggles `ch->comm ^ COMM_QUIET`.
"""

from __future__ import annotations

import pytest

from mud.commands.remaining_rom import do_quiet
from mud.models.character import Character
from mud.models.constants import CommFlag
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture
def quiet_room():
    room = Room(
        vnum=10011,
        name="Quiet Test Room",
        description="A test room.",
        room_flags=0,
        sector_type=0,
    )
    room.people = []
    room_registry[10011] = room
    yield room
    room_registry.pop(10011, None)


@pytest.fixture
def player(quiet_room):
    char = Character(name="Speaker", level=10, is_npc=False, room=quiet_room)
    quiet_room.people.append(char)
    return char


def test_quiet_toggle_off_when_canonical_bit_set(player: Character) -> None:
    """If CommFlag.QUIET is already set, do_quiet should clear it."""
    player.comm = int(CommFlag.QUIET)

    result = do_quiet(player, "")

    assert result == "Quiet mode removed."
    assert player.comm & int(CommFlag.QUIET) == 0


def test_quiet_toggle_on_when_canonical_bit_unset(player: Character) -> None:
    """If CommFlag.QUIET is unset, do_quiet should set the canonical bit."""
    player.comm = 0

    result = do_quiet(player, "")

    assert "from now on" in result.lower()
    assert player.comm & int(CommFlag.QUIET) != 0


def test_quiet_does_not_touch_old_wrong_bit(player: Character) -> None:
    """The pre-fix wrong bit 0x4 must no longer be the bit do_quiet toggles."""
    player.comm = 0

    do_quiet(player, "")

    # Should set CommFlag.QUIET (bit 0), NOT bit 2 (the old wrong hex 0x4).
    assert player.comm == int(CommFlag.QUIET)
    assert player.comm & 0x4 == 0
