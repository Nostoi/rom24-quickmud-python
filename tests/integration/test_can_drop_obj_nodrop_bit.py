"""Regression for PARALLEL-005: _can_drop_obj read the wrong bit.

`mud/commands/obj_manipulation.py:_can_drop_obj` aliased
`ITEM_NODROP = 0x0010` (bit 4 — `ExtraFlag.EVIL`) instead of
`ExtraFlag.NODROP` (ROM `H = 1<<7 = 0x80`). The function is the gate
for `do_drop`, `do_put`, `do_give`, and `inventory.py:do_drop_all`,
so pre-fix:

- Items flagged `ExtraFlag.NODROP` (cursed gear) could be dropped freely.
- Items flagged `ExtraFlag.EVIL` (a different bit) were spuriously
  blocked from being dropped by a NODROP-shaped error.

ROM C: `src/merc.h:1111` `#define ITEM_NODROP (H)` where `H = 1<<7`.
"""

from __future__ import annotations

import pytest

from mud.commands.obj_manipulation import _can_drop_obj
from mud.models.character import Character
from mud.models.constants import ExtraFlag


class _Obj:
    def __init__(self, extra_flags: int) -> None:
        self.extra_flags = extra_flags


@pytest.fixture
def player() -> Character:
    return Character(name="NoDropTester", level=10, is_npc=False)


def test_nodrop_item_cannot_be_dropped(player: Character) -> None:
    obj = _Obj(int(ExtraFlag.NODROP))
    assert _can_drop_obj(player, obj) is False


def test_evil_item_can_be_dropped(player: Character) -> None:
    # EVIL = bit 4 = the bit the pre-fix code was wrongly reading.
    obj = _Obj(int(ExtraFlag.EVIL))
    assert _can_drop_obj(player, obj) is True


def test_unflagged_item_can_be_dropped(player: Character) -> None:
    assert _can_drop_obj(player, _Obj(0)) is True
