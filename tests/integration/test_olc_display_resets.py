"""OLC-020 — display_resets per-command formatting + pet-shop + flag decoding.

ROM Reference: src/olc.c:973-1183

Pre-fix: do_resets display block (imm_olc.py:39-53) emitted "[NN] X arg1 arg2
arg3" with no per-command formatting, no flag decoding, no pet-shop detection.

Post-fix: _display_resets(room) produces the two-line column header and a
faithfully-formatted line for each reset command (M/O/P/G/E/D/R).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mud.models.constants import ItemType, RoomFlag, WearLocation
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.room import Room
from mud.registry import mob_registry, obj_registry, room_registry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_room():
    """A room used as the reset target (arg3 for M, O; arg1 for D/R)."""
    room = Room(vnum=5000, name="Test Chamber")
    room.resets = []
    room_registry[5000] = room
    yield room
    room_registry.pop(5000, None)


@pytest.fixture
def mob_proto():
    mob = MobIndex(vnum=3001, short_descr="a test guard")
    mob_registry[3001] = mob
    yield mob
    mob_registry.pop(3001, None)


@pytest.fixture
def mob_proto_shopkeeper():
    """Mob that has a pShop — triggers the shopkeeper branch (G/E)."""
    mob = MobIndex(vnum=3002, short_descr="the shopkeeper")
    mob.pShop = object()  # truthy sentinel
    mob_registry[3002] = mob
    yield mob
    mob_registry.pop(3002, None)


@pytest.fixture
def obj_proto_sword():
    obj = ObjIndex(vnum=4001, short_descr="a steel sword")
    obj.item_type = int(ItemType.WEAPON)
    obj_registry[4001] = obj
    yield obj
    obj_registry.pop(4001, None)


@pytest.fixture
def obj_proto_bag():
    obj = ObjIndex(vnum=4002, short_descr="a canvas bag")
    obj.item_type = int(ItemType.CONTAINER)
    obj_registry[4002] = obj
    yield obj
    obj_registry.pop(4002, None)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def make_reset(command: str, arg1: int = 0, arg2: int = 0, arg3: int = 0, arg4: int = 0):
    return SimpleNamespace(command=command, arg1=arg1, arg2=arg2, arg3=arg3, arg4=arg4)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_display_resets_header_lines(base_room):
    """Column header is always emitted (two lines, exact ROM strings).

    mirrors ROM src/olc.c:985-989
    """
    from mud.commands.imm_olc import _display_resets

    out = _display_resets(base_room)
    assert " No.  Loads    Description       Location         Vnum   Mx Mn Description" in out
    assert "==== ======== ============= =================== ======== ===== ===========" in out


def test_display_resets_empty_room(base_room):
    """Empty reset list: header is emitted, no per-reset lines after it."""
    from mud.commands.imm_olc import _display_resets

    out = _display_resets(base_room)
    lines = [ln for ln in out.split("\n") if ln.strip()]
    # Only the two header lines, nothing else
    assert len(lines) == 2


def test_display_resets_m_reset(base_room, mob_proto):
    """M reset: mob vnum, short_descr, room vnum, mx/mn, room name.

    mirrors ROM src/olc.c:1027-1031
    Format: "[%2d] M[%5d] %-13.13s in room             R[%5d] %2d-%2d %-15.15s\n\r"
    """
    from mud.commands.imm_olc import _display_resets

    base_room.resets = [make_reset("M", arg1=3001, arg2=5, arg3=5000, arg4=2)]
    out = _display_resets(base_room)

    assert "M[ 3001]" in out
    assert "a test guard " in out or "a test guard" in out
    assert "in room" in out
    assert "R[ 5000]" in out
    assert " 5- 2" in out
    assert "Test Chamber" in out


def test_display_resets_m_reset_pet_shop_overlay(base_room, mob_proto):
    """Pet-shop: when room.vnum-1 has ROOM_PET_SHOP, index 5 of the line becomes 'P'.

    mirrors ROM src/olc.c:1037-1044
    """
    from mud.commands.imm_olc import _display_resets

    # Room at vnum 4999 = base_room.vnum - 1; set ROOM_PET_SHOP on it
    pet_room = Room(vnum=4999, name="Pet Shop Stall")
    pet_room.room_flags = int(RoomFlag.ROOM_PET_SHOP)
    room_registry[4999] = pet_room

    try:
        base_room.resets = [make_reset("M", arg1=3001, arg2=1, arg3=5000, arg4=1)]
        out = _display_resets(base_room)
        # The M-reset line (after the two header lines)
        reset_lines = [ln for ln in out.split("\n") if "3001" in ln]
        assert len(reset_lines) == 1
        line = reset_lines[0]
        # Character at index 5 must be 'P', not 'M'
        # line starts with "[ 1] " (5 chars), then comes the command char
        assert line[5] == "P", f"Expected 'P' at index 5, got {line[5]!r} in: {line!r}"
    finally:
        room_registry.pop(4999, None)


def test_display_resets_m_reset_no_pet_shop(base_room, mob_proto):
    """Without pet-shop neighbor, the M character stays 'M' at index 5."""
    from mud.commands.imm_olc import _display_resets

    base_room.resets = [make_reset("M", arg1=3001, arg2=1, arg3=5000, arg4=1)]
    out = _display_resets(base_room)
    reset_lines = [ln for ln in out.split("\n") if "3001" in ln]
    assert len(reset_lines) == 1
    assert reset_lines[0][5] == "M"


def test_display_resets_o_reset(base_room, obj_proto_sword):
    """O reset: object in room.

    mirrors ROM src/olc.c:1067-1071
    """
    from mud.commands.imm_olc import _display_resets

    base_room.resets = [make_reset("O", arg1=4001, arg2=0, arg3=5000, arg4=0)]
    out = _display_resets(base_room)

    assert "O[ 4001]" in out
    assert "a steel sword" in out
    assert "in room" in out
    assert "R[ 5000]" in out


def test_display_resets_p_reset(base_room, obj_proto_sword, obj_proto_bag):
    """P reset: object inside a container object.

    mirrors ROM src/olc.c:1094-1101
    Format: "O[%5d] %-13.13s inside              O[%5d] %2d-%2d %-15.15s\n\r"
    """
    from mud.commands.imm_olc import _display_resets

    # arg1=sword (the put item), arg3=bag (the container), arg2/arg4=limits
    base_room.resets = [make_reset("P", arg1=4001, arg2=3, arg3=4002, arg4=1)]
    out = _display_resets(base_room)

    assert "O[ 4001]" in out
    assert "inside" in out
    assert "O[ 4002]" in out
    assert "a canvas bag" in out


def test_display_resets_g_reset_after_m(base_room, mob_proto, obj_proto_sword):
    """G reset (give to inventory): uses 'in the inventory' wear-loc string.

    mirrors ROM src/olc.c:1134-1141 — G branch uses flag_string(wear_loc_strings, WEAR_NONE)
    """
    from mud.commands.imm_olc import _display_resets

    base_room.resets = [
        make_reset("M", arg1=3001, arg2=1, arg3=5000, arg4=1),
        make_reset("G", arg1=4001, arg2=0, arg3=int(WearLocation.NONE), arg4=0),
    ]
    out = _display_resets(base_room)

    assert "in the inventory" in out
    assert "M[ 3001]" in out


def test_display_resets_e_reset_after_m(base_room, mob_proto, obj_proto_sword):
    """E reset (equip): decodes arg3 into wear-loc display string.

    mirrors ROM src/olc.c:1134-1141 — E branch uses flag_string(wear_loc_strings, pReset->arg3)
    """
    from mud.commands.imm_olc import _display_resets

    base_room.resets = [
        make_reset("M", arg1=3001, arg2=1, arg3=5000, arg4=1),
        make_reset("E", arg1=4001, arg2=0, arg3=int(WearLocation.FINGER_L), arg4=0),
    ]
    out = _display_resets(base_room)

    assert "on the left finger" in out


def test_display_resets_ge_shopkeeper_branch(base_room, mob_proto_shopkeeper, obj_proto_sword):
    """G/E after mob with pShop: uses shopkeeper format with S[vnum].

    mirrors ROM src/olc.c:1125-1131
    Format: "O[%5d] %-13.13s in the inventory of S[%5d]       %-15.15s\n\r"
    """
    from mud.commands.imm_olc import _display_resets

    base_room.resets = [
        make_reset("M", arg1=3002, arg2=1, arg3=5000, arg4=1),
        make_reset("G", arg1=4001, arg2=0, arg3=int(WearLocation.NONE), arg4=0),
    ]
    out = _display_resets(base_room)

    assert "in the inventory of" in out
    assert "S[ 3002]" in out


def test_display_resets_d_reset(base_room):
    """D reset: door direction capitalized + door-reset state string.

    mirrors ROM src/olc.c:1152-1159
    Format: "R[%5d] %s door of %-19.19s reset to %s\n\r"
    capitalize(dir_name[arg2]) for direction; flag_string(door_resets, arg3) for state.
    """
    from mud.commands.imm_olc import _display_resets

    # arg1=room vnum, arg2=direction (0=north), arg3=door state (1=closed/unlocked)
    base_room.resets = [make_reset("D", arg1=5000, arg2=0, arg3=1)]
    out = _display_resets(base_room)

    assert "R[ 5000]" in out
    assert "North" in out
    assert "door of" in out
    assert "closed and unlocked" in out


def test_display_resets_d_reset_south_locked(base_room):
    """D reset south direction, locked state.

    mirrors ROM src/olc.c:1155 — dir_name[2] = "south", capitalize -> "South"
    door state 2 -> "closed and locked"
    """
    from mud.commands.imm_olc import _display_resets

    base_room.resets = [make_reset("D", arg1=5000, arg2=2, arg3=2)]
    out = _display_resets(base_room)

    assert "South" in out
    assert "closed and locked" in out


def test_display_resets_r_reset(base_room):
    """R reset: randomize exits format.

    mirrors ROM src/olc.c:1173-1175
    Format: "R[%5d] Exits are randomized in %s\n\r"
    """
    from mud.commands.imm_olc import _display_resets

    base_room.resets = [make_reset("R", arg1=5000, arg2=3)]
    out = _display_resets(base_room)

    assert "R[ 5000]" in out
    assert "Exits are randomized in" in out
    assert "Test Chamber" in out


def test_display_resets_bad_mob_not_displayed(base_room):
    """Bad mob vnum: ROM does strcat then 'continue' which skips send_to_char.

    ROM src/olc.c:1011-1016 — the 'continue' jumps to next loop iteration
    BEFORE send_to_char(final, ch) at line 1179, so the error text is never
    sent.  We replicate that by NOT emitting the bad-mob error line.
    """
    from mud.commands.imm_olc import _display_resets

    # Use a vnum that definitely doesn't exist in mob_registry
    base_room.resets = [make_reset("M", arg1=99999, arg2=1, arg3=5000, arg4=1)]
    out = _display_resets(base_room)
    # Only the two header lines — the bad reset produces no output
    content_lines = [ln for ln in out.split("\n") if ln.strip() and "====" not in ln and "No." not in ln]
    assert content_lines == [], f"Expected no reset output for bad mob, got: {content_lines}"


def test_display_resets_ge_no_previous_mob_emits_error(base_room, obj_proto_sword):
    """G/E with no preceding M reset: emits 'Give/Equip Object - No Previous Mobile'.

    mirrors ROM src/olc.c:1118-1123 — this is a 'break' not 'continue', so
    send_to_char IS called.
    """
    from mud.commands.imm_olc import _display_resets

    base_room.resets = [
        make_reset("G", arg1=4001, arg2=0, arg3=int(WearLocation.NONE), arg4=0),
    ]
    out = _display_resets(base_room)
    assert "No Previous Mobile" in out


def test_display_resets_multiple_resets_numbered(base_room, mob_proto, obj_proto_sword):
    """Multiple resets are numbered sequentially."""
    from mud.commands.imm_olc import _display_resets

    base_room.resets = [
        make_reset("M", arg1=3001, arg2=1, arg3=5000, arg4=1),
        make_reset("G", arg1=4001, arg2=0, arg3=int(WearLocation.NONE), arg4=0),
    ]
    out = _display_resets(base_room)
    assert "[ 1]" in out
    assert "[ 2]" in out
