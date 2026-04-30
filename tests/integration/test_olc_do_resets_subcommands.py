"""OLC-022 — do_resets inside/room/wear-loc/random subcommands + syntax help.

ROM Reference: src/olc.c:1232-1469

Pre-fix: do_resets handled display + delete + naive mob/obj (no wear-loc, no
inside, no room, no random, no syntax block).

Post-fix: full ROM subcommand set: P/O/G/E resets via inside/room/wear-loc,
R reset via random, 6-line syntax block on unrecognized input.
"""

from __future__ import annotations

import pytest

from mud.models.constants import ItemType, WearLocation
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.room import Room
from mud.registry import mob_registry, obj_registry, room_registry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def builder_char(olc_room):
    """Character with builder privileges in olc_room."""
    from mud.models.character import Character

    char = Character()
    char.name = "Builder"
    char.level = 60
    char.trust = 60
    char.room = olc_room
    char.pcdata = type("PCData", (), {"security": 9})()

    char.is_npc = False
    return char


@pytest.fixture
def olc_area():
    from mud.models.area import Area

    area = Area(
        vnum=10,
        name="Test Area",
        file_name="test.are",
        min_vnum=9000,
        max_vnum=9099,
        security=5,
        builders="Builder",
    )
    return area


@pytest.fixture
def olc_room(olc_area):
    room = Room(vnum=9001, name="Builder Test Room")
    room.resets = []
    room.area = olc_area
    room_registry[9001] = room
    yield room
    room_registry.pop(9001, None)


@pytest.fixture
def mob_proto():
    mob = MobIndex(vnum=9010, short_descr="a test guard")
    mob_registry[9010] = mob
    yield mob
    mob_registry.pop(9010, None)


@pytest.fixture
def obj_proto_sword():
    obj = ObjIndex(vnum=9020, short_descr="a steel sword")
    obj.item_type = int(ItemType.WEAPON)
    obj_registry[9020] = obj
    yield obj
    obj_registry.pop(9020, None)


@pytest.fixture
def obj_proto_bag():
    obj = ObjIndex(vnum=9021, short_descr="a canvas bag")
    obj.item_type = int(ItemType.CONTAINER)
    obj_registry[9021] = obj
    yield obj
    obj_registry.pop(9021, None)


@pytest.fixture
def obj_proto_corpse():
    obj = ObjIndex(vnum=9022, short_descr="a NPC corpse")
    obj.item_type = int(ItemType.CORPSE_NPC)
    obj_registry[9022] = obj
    yield obj
    obj_registry.pop(9022, None)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def call_resets(builder_char, args: str) -> str:
    from mud.commands.imm_olc import do_resets

    return do_resets(builder_char, args)


# ---------------------------------------------------------------------------
# P-reset: <n> obj <vnum> inside <containerVnum> [limit] [count]
# ---------------------------------------------------------------------------


def test_do_resets_obj_inside_container_adds_p_reset(
    builder_char, olc_room, obj_proto_sword, obj_proto_bag
):
    """<n> obj <vnum> inside <containerVnum> -> P-reset with correct fields.

    mirrors ROM src/olc.c:1376-1391
    command='P', arg1=obj_vnum, arg3=container_vnum, arg2=limit(default 1), arg4=count(default 1)
    """
    out = call_resets(builder_char, "1 obj 9020 inside 9021")
    assert "Reset added." in out
    assert len(olc_room.resets) == 1
    r = olc_room.resets[0]
    assert r.command == "P"
    assert r.arg1 == 9020
    assert r.arg3 == 9021
    assert r.arg2 == 1   # default limit
    assert r.arg4 == 1   # default count


def test_do_resets_obj_inside_with_explicit_limit_count(
    builder_char, olc_room, obj_proto_sword, obj_proto_bag
):
    """<n> obj <vnum> inside <containerVnum> 3 2 -> uses explicit limit/count.

    mirrors ROM src/olc.c:1388-1390
    arg2=limit(3), arg4=count(2)
    """
    out = call_resets(builder_char, "1 obj 9020 inside 9021 3 2")
    assert "Reset added." in out
    r = olc_room.resets[0]
    assert r.arg2 == 3
    assert r.arg4 == 2


def test_do_resets_obj_inside_corpse_npc_ok(
    builder_char, olc_room, obj_proto_sword, obj_proto_corpse
):
    """ITEM_CORPSE_NPC is a valid container (ROM accepts it alongside ITEM_CONTAINER).

    mirrors ROM src/olc.c:1381-1382
    """
    out = call_resets(builder_char, "1 obj 9020 inside 9022")
    assert "Reset added." in out
    r = olc_room.resets[0]
    assert r.command == "P"
    assert r.arg3 == 9022


def test_do_resets_obj_inside_non_container_rejected(
    builder_char, olc_room, obj_proto_sword
):
    """Non-container vnum -> 'Object 2 is not a container.\n\r'.

    mirrors ROM src/olc.c:1383-1385
    """
    out = call_resets(builder_char, "1 obj 9020 inside 9020")  # sword is not a container
    assert "Object 2 is not a container." in out
    assert len(olc_room.resets) == 0


# ---------------------------------------------------------------------------
# O-reset: <n> obj <vnum> room
# ---------------------------------------------------------------------------


def test_do_resets_obj_room_adds_o_reset(builder_char, olc_room, obj_proto_sword):
    """<n> obj <vnum> room -> O-reset with room.vnum as arg3.

    mirrors ROM src/olc.c:1397-1408
    command='O', arg1=vnum, arg2=0, arg3=room.vnum, arg4=0
    """
    out = call_resets(builder_char, "1 obj 9020 room")
    assert "Reset added." in out
    assert len(olc_room.resets) == 1
    r = olc_room.resets[0]
    assert r.command == "O"
    assert r.arg1 == 9020
    assert r.arg2 == 0
    assert r.arg3 == 9001  # olc_room.vnum
    assert r.arg4 == 0


def test_do_resets_obj_room_bad_vnum_rejected(builder_char, olc_room):
    """Bad obj vnum with 'room' subcommand -> 'Vnum doesn't exist.\n\r'.

    mirrors ROM src/olc.c:1399-1402
    """
    out = call_resets(builder_char, "1 obj 99999 room")
    assert "Vnum doesn't exist." in out
    assert len(olc_room.resets) == 0


# ---------------------------------------------------------------------------
# G/E-reset: <n> obj <vnum> <wear-loc>
# ---------------------------------------------------------------------------


def test_do_resets_obj_wear_loc_lfinger_adds_e_reset(
    builder_char, olc_room, obj_proto_sword
):
    """<n> obj <vnum> lfinger -> E-reset with arg3=FINGER_L.

    mirrors ROM src/olc.c:1409-1431
    """
    out = call_resets(builder_char, "1 obj 9020 lfinger")
    assert "Reset added." in out
    r = olc_room.resets[0]
    assert r.command == "E"
    assert r.arg1 == 9020
    assert r.arg3 == int(WearLocation.FINGER_L)


def test_do_resets_obj_wear_loc_hold_adds_e_reset(
    builder_char, olc_room, obj_proto_sword
):
    """<n> obj <vnum> hold -> E-reset with arg3=HOLD.

    mirrors ROM src/olc.c:1409-1431
    """
    out = call_resets(builder_char, "1 obj 9020 hold")
    assert "Reset added." in out
    r = olc_room.resets[0]
    assert r.command == "E"
    assert r.arg3 == int(WearLocation.HOLD)


def test_do_resets_obj_wear_loc_none_adds_g_reset(
    builder_char, olc_room, obj_proto_sword
):
    """<n> obj <vnum> none -> G-reset (WEAR_NONE means inventory).

    mirrors ROM src/olc.c:1427-1429
    """
    out = call_resets(builder_char, "1 obj 9020 none")
    assert "Reset added." in out
    r = olc_room.resets[0]
    assert r.command == "G"
    assert r.arg3 == int(WearLocation.NONE)


def test_do_resets_obj_bogus_wear_loc_rejected(builder_char, olc_room, obj_proto_sword):
    """Unrecognized wear-loc -> \"Resets: '? wear-loc'\\n\\r\".

    mirrors ROM src/olc.c:1415-1417
    """
    out = call_resets(builder_char, "1 obj 9020 bogus_loc")
    assert "Resets: '? wear-loc'" in out
    assert len(olc_room.resets) == 0


def test_do_resets_obj_prefix_wear_loc_lookup(builder_char, olc_room, obj_proto_sword):
    """Prefix match: 'lfin' resolves to lfinger -> E-reset with FINGER_L.

    mirrors ROM src/bit.c:118-119 str_prefix prefix lookup
    """
    out = call_resets(builder_char, "1 obj 9020 lfin")
    assert "Reset added." in out
    r = olc_room.resets[0]
    assert r.command == "E"
    assert r.arg3 == int(WearLocation.FINGER_L)


# ---------------------------------------------------------------------------
# R-reset: <n> random <#exits>
# ---------------------------------------------------------------------------


def test_do_resets_random_adds_r_reset(builder_char, olc_room):
    """<n> random 3 -> R-reset with arg1=room.vnum, arg2=3.

    mirrors ROM src/olc.c:1437-1451
    """
    out = call_resets(builder_char, "1 random 3")
    assert "Random exits reset added." in out
    assert len(olc_room.resets) == 1
    r = olc_room.resets[0]
    assert r.command == "R"
    assert r.arg1 == 9001  # olc_room.vnum
    assert r.arg2 == 3


def test_do_resets_random_zero_rejected(builder_char, olc_room):
    """<n> random 0 -> 'Invalid argument.\n\r' (must be 1..6).

    mirrors ROM src/olc.c:1439-1442
    """
    out = call_resets(builder_char, "1 random 0")
    assert "Invalid argument." in out
    assert len(olc_room.resets) == 0


def test_do_resets_random_seven_rejected(builder_char, olc_room):
    """<n> random 7 -> 'Invalid argument.\n\r' (must be 1..6).

    mirrors ROM src/olc.c:1439-1442
    """
    out = call_resets(builder_char, "1 random 7")
    assert "Invalid argument." in out
    assert len(olc_room.resets) == 0


def test_do_resets_random_one_allowed(builder_char, olc_room):
    """<n> random 1 -> valid (boundary).

    mirrors ROM src/olc.c:1439 atoi(arg3) < 1 || atoi(arg3) > 6
    """
    out = call_resets(builder_char, "1 random 1")
    assert "Random exits reset added." in out


def test_do_resets_random_six_allowed(builder_char, olc_room):
    """<n> random 6 -> valid (boundary).

    mirrors ROM src/olc.c:1439
    """
    out = call_resets(builder_char, "1 random 6")
    assert "Random exits reset added." in out


# ---------------------------------------------------------------------------
# M-reset: <n> mob <vnum> [max#area] [max#room]
# ---------------------------------------------------------------------------


def test_do_resets_mob_with_optional_max_args(builder_char, olc_room, mob_proto):
    """<n> mob <vnum> 5 2 -> M-reset with arg2=5 (max area), arg4=2 (max room).

    mirrors ROM src/olc.c:1357-1361
    """
    out = call_resets(builder_char, "1 mob 9010 5 2")
    assert "Reset added." in out
    r = olc_room.resets[0]
    assert r.command == "M"
    assert r.arg1 == 9010
    assert r.arg2 == 5    # max # in area
    assert r.arg3 == 9001  # room vnum
    assert r.arg4 == 2    # max # in room


def test_do_resets_mob_defaults_max_args(builder_char, olc_room, mob_proto):
    """<n> mob <vnum> with no limits -> defaults arg2=1, arg4=1.

    mirrors ROM src/olc.c:1359,1361 is_number guards with default 1
    """
    out = call_resets(builder_char, "1 mob 9010")
    assert "Reset added." in out
    r = olc_room.resets[0]
    assert r.arg2 == 1
    assert r.arg4 == 1


def test_do_resets_mob_bad_vnum_rejected(builder_char, olc_room):
    """Bad mob vnum -> 'Mob doesn't exist.\n\r'.

    mirrors ROM src/olc.c:1352-1354
    """
    out = call_resets(builder_char, "1 mob 99999")
    assert "Mob doesn't exist." in out
    assert len(olc_room.resets) == 0


# ---------------------------------------------------------------------------
# Syntax block on unrecognized numeric-arg subcommand
# ---------------------------------------------------------------------------


def test_do_resets_unknown_subcommand_emits_syntax_block(builder_char, olc_room):
    """<n> garbage -> 6-line syntax block.

    mirrors ROM src/olc.c:1452-1465
    """
    out = call_resets(builder_char, "1 garbage")
    assert "Syntax: RESET <number> OBJ <vnum> <wear_loc>" in out
    assert "RESET <number> OBJ <vnum> inside <vnum> [limit] [count]" in out
    assert "RESET <number> OBJ <vnum> room" in out
    assert "RESET <number> MOB <vnum> [max #x area] [max #x room]" in out
    assert "RESET <number> DELETE" in out
    assert "RESET <number> RANDOM [#x exits]" in out


# ---------------------------------------------------------------------------
# Delete (existing behavior preserved)
# ---------------------------------------------------------------------------


def test_do_resets_delete_existing(builder_char, olc_room, obj_proto_sword):
    """<n> delete removes the reset at position n.

    mirrors ROM src/olc.c:1287-1334
    """
    # First add a reset
    call_resets(builder_char, "1 obj 9020 room")
    assert len(olc_room.resets) == 1
    out = call_resets(builder_char, "1 delete")
    assert "Reset deleted." in out
    assert len(olc_room.resets) == 0


# ---------------------------------------------------------------------------
# olc_tables.py helper unit tests (infrastructure — in same file for locality)
# ---------------------------------------------------------------------------


def test_wear_loc_string_for_known_values():
    """WEAR_LOC_STRINGS covers all WearLocation entries.

    mirrors ROM src/tables.c:525-547
    """
    from mud.utils.olc_tables import wear_loc_string_for

    assert wear_loc_string_for(int(WearLocation.NONE)) == "in the inventory"
    assert wear_loc_string_for(int(WearLocation.FINGER_L)) == "on the left finger"
    assert wear_loc_string_for(int(WearLocation.HOLD)) == "held in the hands"
    assert wear_loc_string_for(int(WearLocation.FLOAT)) == "floating nearby"


def test_wear_loc_string_for_miss_returns_none():
    """Unknown value -> 'none' (ROM flag_string miss sentinel).

    mirrors ROM src/bit.c flag_string miss path
    """
    from mud.utils.olc_tables import wear_loc_string_for

    assert wear_loc_string_for(999) == "none"


def test_wear_loc_flag_lookup_exact():
    """Exact key lookup returns the correct value.

    mirrors ROM src/tables.c:550-572
    """
    from mud.utils.olc_tables import wear_loc_flag_lookup

    assert wear_loc_flag_lookup("none") == int(WearLocation.NONE)
    assert wear_loc_flag_lookup("lfinger") == int(WearLocation.FINGER_L)
    assert wear_loc_flag_lookup("rfinger") == int(WearLocation.FINGER_R)
    assert wear_loc_flag_lookup("hold") == int(WearLocation.HOLD)
    assert wear_loc_flag_lookup("floating") == int(WearLocation.FLOAT)


def test_wear_loc_flag_lookup_prefix():
    """Prefix lookup: 'lfin' resolves to 'lfinger' -> FINGER_L.

    mirrors ROM src/bit.c:118-119 str_prefix match
    """
    from mud.utils.olc_tables import wear_loc_flag_lookup

    assert wear_loc_flag_lookup("lfin") == int(WearLocation.FINGER_L)
    assert wear_loc_flag_lookup("hol") == int(WearLocation.HOLD)
    assert wear_loc_flag_lookup("float") == int(WearLocation.FLOAT)


def test_wear_loc_flag_lookup_miss_returns_none():
    """Completely unrecognized name -> None (ROM NO_FLAG sentinel).

    mirrors ROM src/bit.c flag_value NO_FLAG return
    """
    from mud.utils.olc_tables import wear_loc_flag_lookup

    assert wear_loc_flag_lookup("bogus_xyz") is None


def test_door_reset_string_for():
    """DOOR_RESETS covers all three ROM states.

    mirrors ROM src/tables.c:355-360
    """
    from mud.utils.olc_tables import door_reset_string_for

    assert door_reset_string_for(0) == "open and unlocked"
    assert door_reset_string_for(1) == "closed and unlocked"
    assert door_reset_string_for(2) == "closed and locked"
    assert door_reset_string_for(99) == "none"
