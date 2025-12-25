from mud.commands import process_command
from mud.models.constants import (
    Direction,
    EX_CLOSED,
    EX_ISDOOR,
    EX_LOCKED,
    EX_PICKPROOF,
    LEVEL_HERO,
    WearLocation,
)
from mud.models.clans import lookup_clan_id
from mud.net.session import Session
from mud.models.constants import RoomFlag, Sector
from mud.world import create_test_character, initialize_world
from mud.registry import room_registry
from mud.spawning.obj_spawner import spawn_object
from mud.spawning.mob_spawner import spawn_mob


def setup_module(module):
    initialize_world("area/area.lst")


def _attach_session(char):
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return session


def test_redit_requires_builder_security_and_marks_area():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 9
    builder.pcdata.security = 0
    session = _attach_session(builder)

    denied = process_command(builder, "@redit")
    assert "builder rights" in denied.lower()
    assert session.editor is None

    builder.pcdata.security = 9
    accepted = process_command(builder, "@redit")
    assert "room editor activated" in accepted.lower()
    assert session.editor == "redit"

    renamed = process_command(builder, 'name "New Room"')
    assert "room name set" in renamed.lower()
    assert builder.room.name == "New Room"
    assert builder.room.area.changed is True

    described = process_command(builder, 'desc "A test room"')
    assert "description updated" in described.lower()
    assert builder.room.description == "A test room"

    shown = process_command(builder, "show")
    assert "new room" in shown.lower()

    exited = process_command(builder, "done")
    assert "exiting room editor" in exited.lower()
    assert session.editor is None

    look = process_command(builder, "look")
    assert look


def test_redit_can_create_exit_and_set_flags():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    start = process_command(builder, "@redit")
    assert "room editor activated" in start.lower()

    created = process_command(builder, "@redit north create 3002")
    assert "leads to room 3002" in created.lower()

    exit_obj = builder.room.exits[Direction.NORTH.value]
    assert exit_obj is not None
    assert exit_obj.vnum == 3002
    assert builder.room.area.changed is True

    flagged = process_command(builder, "@redit north flags door closed locked")
    assert "flags set" in flagged.lower()
    assert exit_obj.exit_info == EX_ISDOOR | EX_CLOSED | EX_LOCKED

    keyed = process_command(builder, "@redit north key 1023")
    assert "key set" in keyed.lower()
    assert exit_obj.key == 1023

    described = process_command(builder, "@redit north desc A solid oak door")
    assert "description updated" in described.lower()
    assert exit_obj.description == "A solid oak door"

    summary = process_command(builder, "@redit north")
    assert "oak door" in summary.lower()
    assert "flags" in summary.lower()

    done = process_command(builder, "@redit done")
    assert "exiting" in done.lower()
    assert session.editor is None


def test_redit_ed_adds_and_updates_extra_description():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    process_command(builder, "@redit")

    added = process_command(builder, "@redit ed add plaque")
    assert "extra description 'plaque' created" in added.lower()

    updated = process_command(builder, "@redit ed desc plaque A burnished brass plaque")
    assert "updated" in updated.lower()

    extras = [extra for extra in builder.room.extra_descr if extra.keyword == "plaque"]
    assert extras
    assert extras[0].description == "A burnished brass plaque"
    assert builder.room.area.changed is True

    listing = process_command(builder, "@redit ed list")
    assert "plaque" in listing.lower()

    removed = process_command(builder, "@redit ed delete plaque")
    assert "removed" in removed.lower()
    assert not any(extra.keyword == "plaque" for extra in builder.room.extra_descr)

    process_command(builder, "@redit done")
    assert session.editor is None


def test_redit_room_flags_toggle():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    process_command(builder, "@redit")

    builder.room.area.changed = False
    builder.room.room_flags = 0

    toggle_response = process_command(builder, "@redit room safe private")
    assert "room flags toggled" in toggle_response.lower()
    flags = builder.room.room_flags
    assert flags & int(RoomFlag.ROOM_SAFE)
    assert flags & int(RoomFlag.ROOM_PRIVATE)
    assert builder.room.area.changed is True

    builder.room.area.changed = False
    second_toggle = process_command(builder, "@redit room safe")
    assert "room flags toggled" in second_toggle.lower()
    assert builder.room.room_flags & int(RoomFlag.ROOM_SAFE) == 0
    assert builder.room.room_flags & int(RoomFlag.ROOM_PRIVATE)
    assert builder.room.area.changed is True

    invalid = process_command(builder, "@redit room sparkle")
    assert "unknown room flags" in invalid.lower()

    process_command(builder, "@redit done")
    assert session.editor is None


def test_redit_sector_updates_type():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    process_command(builder, "@redit")

    builder.room.area.changed = False
    builder.room.sector_type = int(Sector.INSIDE)

    response = process_command(builder, "@redit sector city")
    assert "sector type set" in response.lower()
    assert builder.room.sector_type == int(Sector.CITY)
    assert builder.room.area.changed is True

    builder.room.area.changed = False
    error = process_command(builder, "@redit sector spaceport")
    assert "unknown sector type" in error.lower()
    assert builder.room.area.changed is False

    process_command(builder, "@redit done")
    assert session.editor is None


def test_redit_owner_sets_and_clears_name():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    process_command(builder, "@redit")

    builder.room.area.changed = False
    owner_response = process_command(builder, "@redit owner Clan Rom")
    assert "owner set" in owner_response.lower()
    assert builder.room.owner == "Clan Rom"
    assert builder.room.area.changed is True

    builder.room.area.changed = False
    clear_response = process_command(builder, "@redit owner none")
    assert "owner set" in clear_response.lower()
    assert builder.room.owner == ""
    assert builder.room.area.changed is True

    process_command(builder, "@redit done")
    assert session.editor is None


def test_redit_format_rewraps_description():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    process_command(builder, "@redit")

    raw_description = '   this is   a test.  line two!  "quoted" yes?  ok) done.'
    expected = 'This is a test.  Line two!  "quoted" yes?  Ok) done.\n'

    builder.room.description = raw_description
    builder.room.area.changed = False

    response = process_command(builder, "@redit format")

    assert "string formatted" in response.lower()
    assert builder.room.description == expected
    assert builder.room.area.changed is True

    process_command(builder, "@redit done")
    assert session.editor is None


def test_redit_sets_heal_and_mana_rates():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    process_command(builder, "@redit")

    builder.room.area.changed = False
    heal_response = process_command(builder, "@redit heal 150")
    assert "heal rate set" in heal_response.lower()
    assert builder.room.heal_rate == 150
    assert builder.room.area.changed is True

    builder.room.area.changed = False
    mana_response = process_command(builder, "@redit mana 85")
    assert "mana rate set" in mana_response.lower()
    assert builder.room.mana_rate == 85
    assert builder.room.area.changed is True

    done = process_command(builder, "@redit done")
    assert "exiting" in done.lower()
    assert session.editor is None


def test_redit_sets_clan():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    process_command(builder, "@redit")

    builder.room.area.changed = False
    clan_response = process_command(builder, "@redit clan rom")
    assert "room clan set" in clan_response.lower()
    expected = lookup_clan_id("rom")
    assert builder.room.clan == expected
    assert builder.room.area.changed is True

    builder.room.area.changed = False
    reset_response = process_command(builder, "@redit clan none")
    assert "room clan set" in reset_response.lower()
    assert builder.room.clan == 0
    assert builder.room.area.changed is True

    process_command(builder, "@redit done")
    assert session.editor is None


def test_redit_show_lists_rom_metadata():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    process_command(builder, "@redit")

    room = builder.room
    original_name = room.name
    original_description = room.description
    original_flags = room.room_flags
    original_sector = room.sector_type
    original_heal = room.heal_rate
    original_mana = room.mana_rate
    original_clan = room.clan
    original_owner = room.owner
    original_extras = list(room.extra_descr)
    original_area_changed = room.area.changed

    process_command(builder, 'name "Hall of Heroes"')
    process_command(builder, 'desc "A vaulted hall lined with statues."')
    process_command(builder, "sector city")
    process_command(builder, "heal 120")
    process_command(builder, "mana 80")
    process_command(builder, "clan rom")
    process_command(builder, "owner Builder")
    process_command(builder, "ed add plaque")

    obj = spawn_object(3005)
    room.add_object(obj)
    expected_obj_word = ((obj.name or obj.short_descr or "").split() or ["none"])[0].lower()

    new_vnum = 3398
    process_command(builder, f"east dig {new_vnum}")
    process_command(builder, "east key 1023")
    process_command(builder, "east flags door closed locked")
    east_exit = room.exits[Direction.EAST.value]
    east_exit.exit_info |= EX_PICKPROOF
    east_exit.keyword = "iron gate"
    east_exit.description = "A sturdy gate bars the passage."

    room.room_flags = original_flags | int(RoomFlag.ROOM_SAFE) | int(RoomFlag.ROOM_LAW)

    summary = process_command(builder, "show")
    summary_lower = summary.lower()
    room_flags_line = next(line for line in summary.splitlines() if line.startswith("Room flags:"))
    characters_line = next(line for line in summary.splitlines() if line.startswith("Characters:"))

    assert "Description:\nA vaulted hall lined with statues." in summary
    assert "Name:       [Hall of Heroes]" in summary
    area_vnum = getattr(room.area, "vnum", 0)
    assert f"Area:       [{area_vnum:5}]" in summary
    assert "Sector:     [city]" in summary
    assert "safe" in room_flags_line and "law" in room_flags_line
    assert "Health rec: [120]" in summary
    assert "Mana rec  : [80]" in summary
    assert "Clan      : [" in summary and "rom" in summary
    assert "Owner     : [Builder]" in summary
    assert "Desc Kwds:  [plaque]" in summary
    assert "builder" in characters_line.lower()
    assert f"objects:    [{expected_obj_word}" in summary_lower
    assert "-East  to" in summary and "Exit flags: [door closed locked PICKPROOF]" in summary
    assert "Kwds: [iron gate]" in summary
    assert "A sturdy gate bars the passage." in summary

    process_command(builder, "east delete")
    room_registry.pop(new_vnum, None)
    if obj in room.contents:
        room.contents.remove(obj)
    if hasattr(obj, "location") and getattr(obj, "location", None) is room:
        obj.location = None

    room.name = original_name
    room.description = original_description
    room.room_flags = original_flags
    room.sector_type = original_sector
    room.heal_rate = original_heal
    room.mana_rate = original_mana
    room.clan = original_clan
    room.owner = original_owner
    room.extra_descr = original_extras
    room.area.changed = original_area_changed

    process_command(builder, "@redit done")
    assert session.editor is None


def test_redit_link_creates_bidirectional_exit():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    target_room = room_registry[3002]
    target_room.area.security = 1
    session = _attach_session(builder)

    start = process_command(builder, "@redit")
    assert "room editor activated" in start.lower()

    link_response = process_command(builder, "@redit north link 3002")
    assert "two-way link" in link_response.lower()

    exit_obj = builder.room.exits[Direction.NORTH.value]
    assert exit_obj is not None
    assert exit_obj.vnum == 3002

    reverse_exit = target_room.exits[Direction.SOUTH.value]
    assert reverse_exit is not None
    assert reverse_exit.vnum == builder.room.vnum

    flag_response = process_command(builder, "@redit north flags door closed locked")
    assert "flags set" in flag_response.lower()
    assert exit_obj.exit_info == EX_ISDOOR | EX_CLOSED | EX_LOCKED
    assert reverse_exit.exit_info == exit_obj.exit_info

    clear_response = process_command(builder, "@redit north flags none")
    assert "flags cleared" in clear_response.lower()
    assert exit_obj.exit_info == 0
    assert reverse_exit.exit_info == 0

    delete_response = process_command(builder, "@redit north delete")
    assert "removed" in delete_response.lower()
    assert builder.room.exits[Direction.NORTH.value] is None
    assert target_room.exits[Direction.SOUTH.value] is None

    dig_response = process_command(builder, "@redit north dig 3399")
    assert "room 3399 created" in dig_response.lower()

    new_exit = builder.room.exits[Direction.NORTH.value]
    assert new_exit is not None and new_exit.vnum == 3399

    new_room = room_registry[3399]
    reverse_new = new_room.exits[Direction.SOUTH.value]
    assert reverse_new is not None and reverse_new.vnum == builder.room.vnum

    cleanup_delete = process_command(builder, "@redit north delete")
    assert "removed" in cleanup_delete.lower()
    room_registry.pop(3399, None)

    done = process_command(builder, "@redit done")
    assert "exiting" in done.lower()
    assert session.editor is None


def test_redit_mreset_adds_reset_and_spawns_mob():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    process_command(builder, "@redit")

    room = builder.room
    room.resets.clear()
    room.area.changed = False

    response = process_command(builder, "@redit mreset 3002 2 3")
    assert "added to resets" in response.lower()
    assert room.area.changed is True

    spawned = [
        mob
        for mob in room.people
        if getattr(mob, "prototype", None) is not None and getattr(mob.prototype, "vnum", None) == 3002
    ]
    assert spawned, "expected spawned mob in room"

    reset = room.resets[-1]
    assert reset.command == "M"
    assert reset.arg1 == 3002
    assert reset.arg2 == 2
    assert reset.arg3 == room.vnum
    assert reset.arg4 == 3

    for mob in spawned:
        if mob in room.people:
            room.people.remove(mob)

    done = process_command(builder, "@redit done")
    assert "exiting" in done.lower()
    assert session.editor is None


def test_redit_oreset_adds_room_and_container_resets():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    process_command(builder, "@redit")

    room = builder.room
    room.resets.clear()
    room.contents.clear()
    room.area.changed = False

    room_response = process_command(builder, "@redit oreset 3005")
    assert "room resets" in room_response.lower()
    assert room.area.changed is True

    placed = [obj for obj in room.contents if getattr(getattr(obj, "prototype", None), "vnum", None) == 3005]
    assert placed, "expected object spawned into room"

    room_reset = room.resets[-1]
    assert room_reset.command == "O"
    assert room_reset.arg1 == 3005
    assert room_reset.arg3 == room.vnum

    container = spawn_object(3010)
    room.add_object(container)
    room.area.changed = False

    container_response = process_command(builder, "@redit oreset 3001 pit")
    assert "inside" in container_response.lower()
    assert room.area.changed is True

    assert any(
        getattr(getattr(obj, "prototype", None), "vnum", None) == 3001
        for obj in getattr(container, "contained_items", [])
    )

    container_reset = room.resets[-1]
    assert container_reset.command == "P"
    assert container_reset.arg1 == 3001
    assert container_reset.arg3 == getattr(container.prototype, "vnum", 0)
    assert container_reset.arg4 == 1

    done = process_command(builder, "@redit done")
    assert "exiting" in done.lower()
    assert session.editor is None


def test_redit_oreset_equips_mob_and_records_reset():
    builder = create_test_character("Builder", 3001)
    builder.level = LEVEL_HERO
    builder.is_admin = True
    builder.room.area.security = 1
    builder.pcdata.security = 1
    session = _attach_session(builder)

    process_command(builder, "@redit")

    room = builder.room
    room.resets.clear()
    room.area.changed = False

    mob = spawn_mob(3001)
    room.add_mob(mob)

    equip_response = process_command(builder, "@redit oreset 3005 baker wielded")
    assert "wield" in equip_response.lower()
    assert room.area.changed is True

    reset = room.resets[-1]
    assert reset.command == "E"
    assert reset.arg1 == 3005
    assert reset.arg2 == int(WearLocation.WIELD)
    assert reset.arg3 == int(WearLocation.WIELD)

    inventory = [
        obj for obj in getattr(mob, "inventory", []) if getattr(getattr(obj, "prototype", None), "vnum", None) == 3005
    ]
    assert inventory, "expected object in mob inventory"
    equipped = inventory[0]
    assert getattr(equipped, "wear_loc", None) == int(WearLocation.WIELD)
    assert getattr(mob, "equipment", {}).get(int(WearLocation.WIELD)) is equipped

    if mob in room.people:
        room.people.remove(mob)

    done = process_command(builder, "@redit done")
    assert "exiting" in done.lower()
    assert session.editor is None
