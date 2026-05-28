"""INV-028 LIGHT-SLOT-KEY-COHERENCE enforcement.

ROM equips a worn light (`item_type == ITEM_LIGHT`) into the single `WEAR_LIGHT`
slot (`src/act_obj.c:1415-1422` wear_obj — item-type dispatch happens BEFORE any
wear-flag branch), and reads it from that same slot for room-light accounting
(`src/handler.c:1504-1573` char_from/to_room) and per-tick burnout decay
(`src/update.c:721-730`). `do_wear` / `do_hold` / `do_wield` all route through
wear_obj, so `hold torch` lands in WEAR_LIGHT too.

Python contract (INV-028): a worn light lives under `int(WearLocation.LIGHT)`,
and all three consumers agree on that key:
  - `do_wear` (writer) equips an ITEM_LIGHT into `WearLocation.LIGHT`.
  - `Room._has_lit_light_source` (reader) counts it for room.light.
  - `mud/game_loop.py:_find_equipped_light` (reader) finds it for burnout decay.

Pre-fix the slot was keyed three inconsistent ways (do_wear -> HOLD, room.py ->
str "0", game_loop.py -> "light"/int-LIGHT), so PC lights never burned out and
PC-held lights were mis-counted vs ROM. See
docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md INV-028.
"""

from __future__ import annotations

import pytest

from mud.commands.equipment import do_wear
from mud.game_loop import _decay_worn_light
from mud.models.constants import ItemType, WearFlag, WearLocation
from mud.models.room import Room
from mud.world import create_test_character


@pytest.fixture
def lit_torch(object_factory):
    torch = object_factory(
        {
            "vnum": 28000,
            "name": "torch",
            "short_descr": "a burning torch",
            "description": "A torch burns here.",
            "item_type": int(ItemType.LIGHT),
            "wear_flags": int(WearFlag.TAKE | WearFlag.HOLD),
            "value": [0, 0, 100, 0, 0],  # value[2] = light duration
        }
    )
    torch.value = [0, 0, 100, 0, 0]  # object_factory doesn't sync value from proto (AGENTS.md)
    return torch


def _make_char(room: Room):
    char = create_test_character("Lighter", room_vnum=room.vnum)
    char.is_npc = False
    char.equipment = {}
    char.room = room
    return char


def test_do_wear_routes_light_to_light_slot_by_key(lit_torch):
    """ROM src/act_obj.c:1415-1421 — ITEM_LIGHT -> equip_char(ch, obj, WEAR_LIGHT)."""
    room = Room(vnum=28001, name="Test Room", description="d", light=0)
    char = _make_char(room)
    char.inventory.append(lit_torch)

    result = do_wear(char, "torch")

    # Pin the KEY (the coherence axis), not just membership.
    assert int(WearLocation.LIGHT) in char.equipment
    assert char.equipment[int(WearLocation.LIGHT)] is lit_torch
    assert int(WearLocation.HOLD) not in char.equipment
    assert "light" in result.lower() and "hold" in result.lower()


def test_room_light_tracks_worn_light_in_light_slot(lit_torch):
    """ROM src/handler.c:1571-1573 / 1504-1507 — room light follows WEAR_LIGHT."""
    room = Room(vnum=28002, name="Test Room", description="d", light=0)
    char = _make_char(room)
    char.equipment[int(WearLocation.LIGHT)] = lit_torch

    room.add_character(char)
    assert room.light == 1

    room.remove_character(char)
    assert room.light == 0


def test_worn_light_burnout_decrements_room_light_and_destroys(lit_torch):
    """ROM src/update.c:721-730 — burnout drops --room->light and extract_obj()s."""
    room = Room(vnum=28003, name="Test Room", description="d", light=0)
    char = _make_char(room)
    lit_torch.value = [0, 0, 1, 0, 0]  # one tick from burnout
    char.equipment[int(WearLocation.LIGHT)] = lit_torch
    room.add_character(char)
    assert room.light == 1  # lit light counted on entry

    _decay_worn_light(char)

    # torch burned out: room light decremented and the light removed from the slot
    assert room.light == 0
    assert int(WearLocation.LIGHT) not in char.equipment
