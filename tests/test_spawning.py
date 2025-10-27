import pytest

import mud.spawning.reset_handler as reset_handler
import logging

from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.constants import (
    EX_CLOSED,
    EX_ISDOOR,
    EX_LOCKED,
    EX_PICKPROOF,
    ITEM_INVENTORY,
    MAX_STATS,
    ActFlag,
    AffectFlag,
    CommFlag,
    DamageType,
    Direction,
    ImmFlag,
    ItemType,
    LEVEL_HERO,
    OffFlag,
    Position,
    ExtraFlag,
    ResFlag,
    RoomFlag,
    Sex,
    Size,
    Stat,
    VulnFlag,
    convert_flags_from_letters,
)
from mud.models.mob import MobIndex, MobProgram
from mud.models.obj import ObjIndex
from mud.models.room import Exit, Room
from mud.models.room_json import ResetJson
from mud.models.shop import Shop
from mud.registry import area_registry, mob_registry, obj_registry, room_registry, shop_registry
from mud.skills.metadata import ROM_SKILL_METADATA
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.obj_spawner import spawn_object
from mud.spawning.reset_handler import RESET_TICKS, reset_tick
from mud.spawning.templates import MobInstance
from mud.utils import rng_mm
from mud.world import initialize_world
from mud.world.movement import move_character


def test_spawned_mob_copies_proto_stats():
    proto = MobIndex(
        vnum=99999,
        player_name="testmob",
        short_descr="a test mob",
        long_descr="A test mob waits here.\n",
        description="This is a parity test mob.\n",
        race="human",
        act_flags="AF",
        affected_by="CD",
        alignment=-350,
        group=7,
        level=20,
        hit_dice="4d8+30",
        mana_dice="3d5+10",
        damage_dice="2d5+6",
        damage_type="slash",
        ac_pierce=-10,
        ac_bash=-11,
        ac_slash=-12,
        ac_exotic=-13,
        offensive="AB",
        immune="C",
        resist="D",
        vuln="E",
        start_pos="sleep",
        default_pos="stand",
        sex="male",
        wealth=600,
        form="5",
        parts="7",
        size="large",
        material="bone",
        spec_fun="spec_cast_adept",
    )
    proto.hit = (4, 8, 30)
    proto.mana = (3, 5, 10)
    proto.damage = (2, 5, 6)
    proto.hitroll = 3
    proto.damroll = 4
    proto.mprog_flags = 0x04
    proto.mprogs = [MobProgram(trig_type=1, trig_phrase="hello", vnum=9000, code="say hello")]

    mob = MobInstance.from_prototype(proto)

    expected_act = convert_flags_from_letters("AF", ActFlag)
    expected_affect = convert_flags_from_letters("CD", AffectFlag)
    expected_off = convert_flags_from_letters("AB", OffFlag)
    expected_imm = convert_flags_from_letters("C", ImmFlag)
    expected_res = convert_flags_from_letters("D", ResFlag)
    expected_vuln = convert_flags_from_letters("E", VulnFlag)

    assert mob.prototype is proto
    assert mob.is_npc is True
    assert mob.act == int(expected_act)
    assert mob.has_act_flag(ActFlag.AGGRESSIVE) is True
    assert mob.affected_by == int(expected_affect)
    assert mob.has_affect(AffectFlag.DETECT_INVIS) is True
    assert mob.off_flags == int(expected_off)
    assert mob.imm_flags == int(expected_imm)
    assert mob.res_flags == int(expected_res)
    assert mob.vuln_flags == int(expected_vuln)
    assert mob.alignment == -350
    assert mob.group == 7
    assert mob.hitroll == 3
    assert mob.damroll == 6
    assert mob.damage == (2, 5, 6)
    assert mob.dam_type == int(DamageType.SLASH)
    assert mob.armor == (-10, -11, -12, -13)
    assert mob.start_pos == Position.SLEEPING
    assert mob.default_pos == Position.STANDING
    assert mob.position == Position.STANDING
    assert mob.sex == Sex.MALE
    assert mob.size == Size.LARGE
    assert mob.form == 5
    assert mob.parts == 7
    assert mob.material == "bone"
    assert mob.race == "human"
    assert mob.spec_fun == "spec_cast_adept"
    assert mob.mprog_flags == proto.mprog_flags
    assert mob.mob_programs is not proto.mprogs
    assert mob.mob_programs == proto.mprogs
    assert mob.mprog_target is None
    assert mob.mprog_delay == 0
    assert mob.max_hit >= mob.current_hp >= 0
    assert mob.move == 100
    assert mob.max_move == 100
    assert mob.max_mana == mob.mana
    assert mob.gold >= 0
    assert mob.silver >= 0
    expected_comm = CommFlag.NOSHOUT | CommFlag.NOTELL | CommFlag.NOCHANNELS
    assert mob.comm == int(expected_comm)


def test_spawned_mob_inherits_perm_stats():
    proto = MobIndex(
        vnum=88888,
        player_name="permstat",
        short_descr="a permstat mob",
        act_flags="AST",
        offensive="H",
        level=60,
        hit_dice="0d0+0",
        mana_dice="0d0+0",
        damage_dice="0d0+0",
        damage_type="slash",
        size="huge",
    )
    proto.hit = (0, 0, 0)
    proto.mana = (0, 0, 0)
    proto.damage = (0, 0, 0)

    mob = MobInstance.from_prototype(proto)

    assert mob.level == 60
    assert len(mob.perm_stat) == MAX_STATS
    expected_stats = [30, 25, 24, 30, 28]
    assert mob.perm_stat == expected_stats
    assert mob.perm_stat[Stat.STR] == 30
    assert mob.perm_stat[Stat.INT] == 25
    assert mob.perm_stat[Stat.WIS] == 24
    assert mob.perm_stat[Stat.DEX] == 30
    assert mob.perm_stat[Stat.CON] == 28


def test_spawned_mob_randomizes_sex_when_either(monkeypatch):
    proto = MobIndex(
        vnum=54321,
        player_name="randomsex",
        short_descr="a random mob",
        sex="either",
        hit_dice="0d0+0",
        mana_dice="0d0+0",
        damage_dice="0d0+0",
    )
    proto.hit = (0, 0, 0)
    proto.mana = (0, 0, 0)
    proto.damage = (0, 0, 0)

    calls: list[tuple[int, int]] = []

    def fake_number_range(low: int, high: int) -> int:
        calls.append((low, high))
        assert low == int(Sex.MALE) and high == int(Sex.FEMALE)
        return int(Sex.MALE)

    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)

    mob = MobInstance.from_prototype(proto)

    assert mob.sex == Sex.MALE
    assert calls == [(int(Sex.MALE), int(Sex.FEMALE))]


def test_spawned_mob_defaults_to_standing_when_proto_missing_positions():
    proto = MobIndex(vnum=13579, short_descr="default stance mob")
    proto.hit = (0, 0, 0)
    proto.mana = (0, 0, 0)
    proto.damage = (0, 0, 0)

    mob = MobInstance.from_prototype(proto)

    assert mob.start_pos == Position.STANDING
    assert mob.default_pos == Position.STANDING
    assert mob.position == Position.STANDING


def test_spawned_mob_without_damage_type_rolls_rom_defaults(monkeypatch):
    proto = MobIndex(
        vnum=1234,
        player_name="blank",
        short_descr="a blank mob",
        hit_dice="0d0+0",
        mana_dice="0d0+0",
        damage_dice="0d0+0",
        damage_type="",
        wealth=0,
    )
    proto.hit = (0, 0, 0)
    proto.mana = (0, 0, 0)
    proto.damage = (0, 0, 0)

    calls: list[tuple[int, int]] = []

    def fake_number_range(low: int, high: int) -> int:
        calls.append((low, high))
        assert low == 1 and high == 3
        return 2

    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)

    mob = MobInstance.from_prototype(proto)

    assert mob.dam_type == int(DamageType.BASH)
    assert calls == [(1, 3)]


@pytest.mark.parametrize("raw_value", [7, "7"])
def test_spawned_mob_translates_attack_index_damage_type(raw_value):
    proto = MobIndex(
        vnum=3333,
        player_name="indexdamage",
        short_descr="an indexed mob",
        damage_type=raw_value,
        hit_dice="0d0+0",
        mana_dice="0d0+0",
        damage_dice="0d0+0",
    )
    proto.hit = (0, 0, 0)
    proto.mana = (0, 0, 0)
    proto.damage = (0, 0, 0)

    mob = MobInstance.from_prototype(proto)

    assert mob.dam_type == int(DamageType.BASH)


def test_resets_populate_world():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world("area/area.lst")
    bakery = room_registry[3001]
    assert any(getattr(m, "name", None) for m in bakery.people)

    donation = room_registry[3054]
    assert any(getattr(o, "short_descr", None) == "the donation pit" for o in donation.contents)


def test_resets_repop_after_tick():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world("area/area.lst")
    bakery = room_registry[3001]
    donation = room_registry[3054]
    bakery.people.clear()
    donation.contents.clear()
    for _ in range(RESET_TICKS):
        reset_tick()
    assert any(getattr(m, "name", None) for m in bakery.people)
    assert any(getattr(o, "short_descr", None) == "the donation pit" for o in donation.contents)

    # Re-applying resets without clearing should not duplicate 'O' spawns.
    area = donation.area
    assert area is not None
    from mud.spawning.reset_handler import apply_resets

    apply_resets(area)
    pit_count = sum(1 for obj in donation.contents if getattr(getattr(obj, "prototype", None), "vnum", None) == 3010)
    assert pit_count == 1

    # Presence of a non-mob occupant keeps resets from respawning objects.
    dummy_player = object()
    donation.people.append(dummy_player)
    for _ in range(RESET_TICKS):
        reset_tick()
    pit_count_after_player = sum(
        1 for obj in donation.contents if getattr(getattr(obj, "prototype", None), "vnum", None) == 3010
    )
    assert pit_count_after_player == 1
    donation.people.remove(dummy_player)


def test_reset_spawn_in_dark_room_grants_infravision():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    character_registry.clear()

    area = Area(vnum=9100, name="Dark Area", min_vnum=9100, max_vnum=9101)
    room = Room(vnum=9101, name="Lightless Den", area=area)
    room.room_flags = int(RoomFlag.ROOM_DARK)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room

    proto = MobIndex(vnum=9102, short_descr="a shadow lurker")
    mob_registry[proto.vnum] = proto

    area.resets = [ResetJson(command="M", arg1=proto.vnum, arg2=1, arg3=room.vnum, arg4=1)]

    reset_handler.apply_resets(area)

    mob = next((m for m in room.people if isinstance(m, MobInstance)), None)
    assert mob is not None
    assert mob.has_affect(AffectFlag.INFRARED) is True


def test_reset_spawn_adjacent_to_pet_shop_sets_act_pet():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    character_registry.clear()

    area = Area(vnum=9200, name="Pet Plaza", min_vnum=9200, max_vnum=9201)
    storefront = Room(vnum=9200, name="Pet Shop Lobby", area=area)
    storefront.room_flags = int(RoomFlag.ROOM_PET_SHOP)
    kennel = Room(vnum=9201, name="Kennel", area=area)
    area_registry[area.vnum] = area
    room_registry[storefront.vnum] = storefront
    room_registry[kennel.vnum] = kennel

    proto = MobIndex(vnum=9202, short_descr="a cuddly companion")
    mob_registry[proto.vnum] = proto

    area.resets = [ResetJson(command="M", arg1=proto.vnum, arg2=1, arg3=kennel.vnum, arg4=1)]

    reset_handler.apply_resets(area)

    mob = next((m for m in kennel.people if isinstance(m, MobInstance)), None)
    assert mob is not None
    assert mob.has_act_flag(ActFlag.PET) is True


def test_reset_area_preserves_existing_room_state():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world("area/area.lst")

    bakery = room_registry[3001]
    donation = room_registry[3054]
    area = bakery.area
    assert area is not None and donation.area is area

    baker = next(
        (mob for mob in bakery.people if isinstance(mob, MobInstance)),
        None,
    )
    assert baker is not None
    pit = next(
        (obj for obj in donation.contents if getattr(obj, "short_descr", None) == "the donation pit"),
        None,
    )
    assert pit is not None

    extra_proto = next(
        proto
        for proto in obj_registry.values()
        if getattr(proto, "short_descr", None) not in (None, "the donation pit")
    )
    extra = spawn_object(extra_proto.vnum)
    assert extra is not None
    pit.contained_items.append(extra)

    reset_handler.reset_area(area)

    assert any(mob is baker for mob in bakery.people if isinstance(mob, MobInstance))
    assert extra in getattr(pit, "contained_items", [])


def test_door_reset_applies_closed_and_locked_state():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world("area/area.lst")

    office = room_registry[3142]
    area = office.area
    assert area is not None

    east_exit = office.exits[Direction.EAST.value]
    assert east_exit is not None

    assert east_exit.exit_info & EX_CLOSED
    assert east_exit.exit_info & EX_LOCKED

    east_exit.exit_info = 0

    from mud.spawning.reset_handler import apply_resets

    apply_resets(area)

    assert east_exit.exit_info & EX_CLOSED
    assert east_exit.exit_info & EX_LOCKED
    assert east_exit.rs_flags & EX_LOCKED


def test_door_reset_preserves_reverse_rs_flags():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()

    area = Area(vnum=999, name="Door Test")
    area_registry[area.vnum] = area

    room_a = Room(vnum=2000, name="Room A", area=area)
    room_b = Room(vnum=2001, name="Room B", area=area)
    room_registry[room_a.vnum] = room_a
    room_registry[room_b.vnum] = room_b

    forward_exit = Exit(vnum=room_b.vnum, rs_flags=EX_ISDOOR, exit_info=EX_ISDOOR)
    reverse_exit = Exit(
        vnum=room_a.vnum,
        rs_flags=EX_ISDOOR | EX_PICKPROOF,
        exit_info=EX_ISDOOR | EX_PICKPROOF,
    )
    forward_exit.to_room = room_b
    reverse_exit.to_room = room_a
    room_a.exits[Direction.EAST.value] = forward_exit
    room_b.exits[Direction.WEST.value] = reverse_exit

    area.resets = [ResetJson(command="D", arg1=room_a.vnum, arg2=Direction.EAST.value, arg3=2)]

    reset_handler.apply_resets(area)

    assert forward_exit.rs_flags & EX_LOCKED
    assert forward_exit.exit_info & EX_LOCKED
    assert reverse_exit.rs_flags & EX_PICKPROOF
    assert not (reverse_exit.rs_flags & EX_LOCKED)
    assert reverse_exit.exit_info == reverse_exit.rs_flags


def test_door_reset_does_not_promote_one_way_exit():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()

    area = Area(vnum=1000, name="Latch Test")
    area_registry[area.vnum] = area

    room_a = Room(vnum=4000, name="Door A", area=area)
    room_b = Room(vnum=4001, name="Door B", area=area)
    room_registry[room_a.vnum] = room_a
    room_registry[room_b.vnum] = room_b

    forward_exit = Exit(vnum=room_b.vnum, rs_flags=EX_ISDOOR, exit_info=EX_ISDOOR)
    reverse_exit = Exit(vnum=room_a.vnum, rs_flags=0, exit_info=0)
    forward_exit.to_room = room_b
    reverse_exit.to_room = room_a
    room_a.exits[Direction.EAST.value] = forward_exit
    room_b.exits[Direction.WEST.value] = reverse_exit

    area.resets = [ResetJson(command="D", arg1=room_a.vnum, arg2=Direction.EAST.value, arg3=2)]

    reset_handler.apply_resets(area)

    assert forward_exit.exit_info & EX_LOCKED
    assert forward_exit.exit_info & EX_CLOSED
    assert reverse_exit.exit_info == 0
    assert reverse_exit.rs_flags == 0


def test_door_reset_requires_door_flag(caplog):
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()

    area = Area(vnum=1001, name="Flag Test")
    area_registry[area.vnum] = area

    room_a = Room(vnum=5000, name="Room A", area=area)
    room_b = Room(vnum=5001, name="Room B", area=area)
    room_registry[room_a.vnum] = room_a
    room_registry[room_b.vnum] = room_b

    forward_exit = Exit(vnum=room_b.vnum, rs_flags=0, exit_info=0)
    reverse_exit = Exit(vnum=room_a.vnum, rs_flags=0, exit_info=0)
    forward_exit.to_room = room_b
    reverse_exit.to_room = room_a
    room_a.exits[Direction.EAST.value] = forward_exit
    room_b.exits[Direction.WEST.value] = reverse_exit

    area.resets = [ResetJson(command="D", arg1=room_a.vnum, arg2=Direction.EAST.value, arg3=2)]

    with caplog.at_level(logging.WARNING):
        reset_handler.apply_resets(area)

    assert forward_exit.exit_info == 0
    assert forward_exit.rs_flags == 0
    assert reverse_exit.exit_info == 0
    assert reverse_exit.rs_flags == 0
    assert any("non-door exit" in message for message in caplog.messages)


def test_reset_restores_base_exit_state():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world("area/area.lst")

    office = room_registry[3142]
    area = office.area
    assert area is not None

    east_exit = office.exits[Direction.EAST.value]
    assert east_exit is not None

    reverse_room = getattr(east_exit, "to_room", None)
    assert reverse_room is not None

    reverse_exit = reverse_room.exits[Direction.WEST.value]
    assert reverse_exit is not None

    east_exit.exit_info = 0
    reverse_exit.exit_info = 0

    reset_handler.apply_resets(area)

    assert east_exit.exit_info & EX_CLOSED
    assert east_exit.exit_info & EX_LOCKED
    assert reverse_exit.exit_info & EX_CLOSED
    assert reverse_exit.exit_info & EX_LOCKED


def test_reset_P_places_items_inside_container_in_midgaard():
    # Ensure a clean world and load Midgaard where P resets exist (desk/safe)
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world("area/area.lst")

    # Captain's Office (3142) contains a desk (3130) with a key (3123)
    office = room_registry[3142]
    desk = next((o for o in office.contents if getattr(o.prototype, "vnum", None) == 3130), None)
    assert desk is not None
    desk_contents = [getattr(o.prototype, "vnum", None) for o in getattr(desk, "contained_items", [])]
    assert 3123 in desk_contents

    # Safe (3131) contains silver coins (3132)
    safe = next((o for o in office.contents if getattr(o.prototype, "vnum", None) == 3131), None)
    assert safe is not None
    safe_contents = [getattr(o.prototype, "vnum", None) for o in getattr(safe, "contained_items", [])]
    assert 3132 in safe_contents


def test_p_reset_lock_state_fix_resets_container_value_field():
    # Ensure container instance's value[1] mirrors prototype after P population
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world("area/area.lst")
    office = room_registry[3142]
    area = office.area
    assert area is not None
    area.resets = []
    office.contents.clear()
    # Spawn desk (3130), then put key (3123) to trigger P logic
    area.resets.append(ResetJson(command="O", arg1=3130, arg3=office.vnum))
    area.resets.append(ResetJson(command="P", arg1=3123, arg2=1, arg3=3130, arg4=1))
    from mud.spawning.reset_handler import apply_resets

    apply_resets(area)
    desk = next((o for o in office.contents if getattr(o.prototype, "vnum", None) == 3130), None)
    assert desk is not None
    # Instance value[1] equals prototype value[1]
    assert hasattr(desk, "value")
    assert desk.value[1] == desk.prototype.value[1]


def test_reset_R_randomizes_exit_order(monkeypatch):
    # Use a deterministic RNG to force swaps
    from mud.utils import rng_mm

    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world("area/area.lst")
    room = room_registry[3001]
    original = list(room.exits)
    # Ensure at least 3 slots considered
    count = min(3, len(room.exits))
    # Inject an R reset for this room into its area and apply
    area = room.area
    assert area is not None
    area.resets.append(ResetJson(command="R", arg1=room.vnum, arg2=count))

    seq = []

    def fake_number_range(a, b):
        # always pick the last index to maximize change
        seq.append((a, b))
        return b

    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)
    from mud.spawning.reset_handler import apply_resets

    apply_resets(area)
    after = room.exits
    assert after != original


def test_reset_P_uses_last_container_instance_when_multiple():
    # Build a controlled sequence: two desks (3130) into Captain's Office (3142),
    # then put a key (3123) into each using P after each O.
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world("area/area.lst")
    office = room_registry[3142]
    area = office.area
    assert area is not None
    area.resets = []
    office.contents.clear()
    area.resets.append(ResetJson(command="O", arg1=3130, arg2=2, arg3=office.vnum))
    area.resets.append(ResetJson(command="P", arg1=3123, arg2=2, arg3=3130, arg4=1))
    area.resets.append(ResetJson(command="O", arg1=3130, arg2=2, arg3=office.vnum))
    area.resets.append(ResetJson(command="P", arg1=3123, arg2=2, arg3=3130, arg4=1))
    from mud.spawning.reset_handler import apply_resets

    apply_resets(area)
    desks = [o for o in office.contents if getattr(o.prototype, "vnum", None) == 3130]
    assert len(desks) == 2
    counts = [
        sum(
            1
            for it in getattr(d, "contained_items", [])
            if getattr(getattr(it, "prototype", None), "vnum", None) == 3123
        )
        for d in desks
    ]
    assert counts == [1, 1]


def test_reset_P_limit_enforced():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world("area/area.lst")
    office = room_registry[3142]
    area = office.area
    assert area is not None

    # Strip existing Midgaard spawns and configure a reset that requests two copies
    # of key 3123 but limits the prototype count to one (arg2 = 1).
    for room in room_registry.values():
        if room.area is area:
            room.contents.clear()
            room.people = []
    if 3123 in obj_registry:
        obj_registry[3123].count = 0
    if 3130 in obj_registry:
        obj_registry[3130].count = 0

    area.resets = [
        ResetJson(command="O", arg1=3130, arg3=office.vnum),
        ResetJson(command="P", arg1=3123, arg2=1, arg3=3130, arg4=2),
    ]

    for _ in range(RESET_TICKS):
        reset_tick()

    desk = next((o for o in office.contents if getattr(o.prototype, "vnum", None) == 3130), None)
    assert desk is not None
    key_vnums = [getattr(getattr(o, "prototype", None), "vnum", None) for o in getattr(desk, "contained_items", [])]
    assert key_vnums.count(3123) == 1
    assert obj_registry[3123].count == 1

    for _ in range(RESET_TICKS):
        reset_tick()

    desk = next((o for o in office.contents if getattr(o.prototype, "vnum", None) == 3130), None)
    assert desk is not None
    key_vnums = [getattr(getattr(o, "prototype", None), "vnum", None) for o in getattr(desk, "contained_items", [])]
    assert key_vnums.count(3123) == 1
    assert obj_registry[3123].count == 1


def test_reset_P_limit_single_apply():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world("area/area.lst")
    office = room_registry[3142]
    area = office.area
    assert area is not None
    area.resets = []
    office.contents.clear()

    area.resets.append(ResetJson(command="O", arg1=3130, arg3=office.vnum))
    area.resets.append(ResetJson(command="P", arg1=3123, arg2=1, arg3=3130, arg4=1))
    area.resets.append(ResetJson(command="P", arg1=3123, arg2=1, arg3=3130, arg4=1))
    from mud.spawning.reset_handler import apply_resets

    apply_resets(area)

    desk = next((o for o in office.contents if getattr(o.prototype, "vnum", None) == 3130), None)
    assert desk is not None
    contents = [getattr(getattr(it, "prototype", None), "vnum", None) for it in getattr(desk, "contained_items", [])]
    assert contents.count(3123) == 1
    assert getattr(obj_registry.get(3123), "count", 0) == 1


def test_reset_P_populates_multiple_items_up_to_limit():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()

    container_proto = ObjIndex(vnum=9105, short_descr="a sturdy crate")
    loot_proto = ObjIndex(vnum=9106, short_descr="a bundle of bolts")
    obj_registry[container_proto.vnum] = container_proto
    obj_registry[loot_proto.vnum] = loot_proto

    area = Area(vnum=9105, name="Crate Area", min_vnum=9105, max_vnum=9105)
    room = Room(vnum=9105, name="Supply Closet", area=area)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room

    area.resets = [
        ResetJson(command="O", arg1=container_proto.vnum, arg3=room.vnum),
        ResetJson(command="P", arg1=loot_proto.vnum, arg2=3, arg3=container_proto.vnum, arg4=3),
    ]

    reset_handler.apply_resets(area)

    crate = next(
        (
            obj
            for obj in room.contents
            if getattr(getattr(obj, "prototype", None), "vnum", None) == container_proto.vnum
        ),
        None,
    )
    assert crate is not None

    contents = [getattr(getattr(item, "prototype", None), "vnum", None) for item in crate.contained_items]
    assert contents.count(loot_proto.vnum) == 3
    assert getattr(obj_registry.get(loot_proto.vnum), "count", 0) == 3


def test_reset_P_fills_mob_carried_container():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()

    area = Area(vnum=9500, name="Guard Post", min_vnum=9500, max_vnum=9500)
    room = Room(vnum=9500, name="Armory", area=area)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room

    mob_proto = MobIndex(vnum=9600, short_descr="a vigilant guard", level=15, wealth=0)
    mob_proto.act_flags = int(ActFlag.IS_NPC)
    mob_registry[mob_proto.vnum] = mob_proto

    container_proto = ObjIndex(vnum=9700, short_descr="a locked coffer", item_type=int(ItemType.CONTAINER))
    obj_registry[container_proto.vnum] = container_proto
    loot_proto = ObjIndex(vnum=9701, short_descr="a stash of supplies", item_type=int(ItemType.TREASURE))
    obj_registry[loot_proto.vnum] = loot_proto

    area.resets = [
        ResetJson(command="M", arg1=mob_proto.vnum, arg2=1, arg3=room.vnum, arg4=1),
        ResetJson(command="G", arg1=container_proto.vnum, arg2=1),
        ResetJson(command="P", arg1=loot_proto.vnum, arg2=1, arg3=container_proto.vnum, arg4=1),
    ]

    reset_handler.apply_resets(area)

    mob = next((m for m in room.people if isinstance(m, MobInstance)), None)
    assert mob is not None

    container = next(
        (
            obj
            for obj in getattr(mob, "inventory", [])
            if getattr(getattr(obj, "prototype", None), "vnum", None) == container_proto.vnum
        ),
        None,
    )
    assert container is not None

    contents = [
        getattr(getattr(item, "prototype", None), "vnum", None)
        for item in getattr(container, "contained_items", [])
    ]
    assert loot_proto.vnum in contents


def test_room_reset_zeroes_object_cost():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()

    idol_proto = ObjIndex(vnum=9303, short_descr="a gilded idol", cost=750)
    obj_registry[idol_proto.vnum] = idol_proto

    area = Area(vnum=9303, name="Idol Area", min_vnum=9303, max_vnum=9303)
    room = Room(vnum=9303, name="Treasure Nook", area=area)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room

    area.resets = [ResetJson(command="O", arg1=idol_proto.vnum, arg3=room.vnum)]

    reset_handler.apply_resets(area)

    idol = next(
        (
            obj
            for obj in room.contents
            if getattr(getattr(obj, "prototype", None), "vnum", None) == idol_proto.vnum
        ),
        None,
    )
    assert idol is not None
    assert idol.cost == 0
    assert getattr(idol.prototype, "cost", None) == 750


def test_room_reset_does_not_stack_duplicate_objects():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()

    fountain_proto = ObjIndex(vnum=9310, short_descr="a marble fountain")
    obj_registry[fountain_proto.vnum] = fountain_proto

    area = Area(vnum=9310, name="Fountain Hall", min_vnum=9310, max_vnum=9310)
    room = Room(vnum=9310, name="Hall of Water", area=area)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room

    area.resets = [ResetJson(command="O", arg1=fountain_proto.vnum, arg2=10, arg3=room.vnum)]

    reset_handler.apply_resets(area)
    reset_handler.apply_resets(area)

    fountains = [
        obj
        for obj in room.contents
        if getattr(getattr(obj, "prototype", None), "vnum", None) == fountain_proto.vnum
    ]

    assert len(fountains) == 1


def test_room_reset_fuzzes_object_level(monkeypatch):
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()

    mob_proto = MobIndex(vnum=9400, short_descr="fuzzy mob", level=60)
    loot_proto = ObjIndex(vnum=9401, short_descr="fuzzy loot")
    mob_registry[mob_proto.vnum] = mob_proto
    obj_registry[loot_proto.vnum] = loot_proto

    area = Area(vnum=9400, name="Fuzzy Area", min_vnum=9400, max_vnum=9401)
    room = Room(vnum=9400, name="Fuzzy Room", area=area)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room

    area.resets = [
        ResetJson(command="M", arg1=mob_proto.vnum, arg2=1, arg3=room.vnum, arg4=1),
        ResetJson(command="O", arg1=loot_proto.vnum, arg2=1, arg3=room.vnum),
    ]

    expected_base = min(max(mob_proto.level - 2, 0), LEVEL_HERO - 1)
    fuzzy_calls: list[int] = []

    def fake_number_fuzzy(value: int) -> int:
        fuzzy_calls.append(value)
        return LEVEL_HERO + 5

    monkeypatch.setattr(rng_mm, "number_range", lambda low, high: low)
    monkeypatch.setattr(rng_mm, "number_fuzzy", fake_number_fuzzy)

    reset_handler.apply_resets(area)

    loot = next(
        (
            obj
            for obj in room.contents
            if getattr(getattr(obj, "prototype", None), "vnum", None) == loot_proto.vnum
        ),
        None,
    )

    assert loot is not None
    assert loot.level == LEVEL_HERO - 1
    assert fuzzy_calls == [expected_base]


def test_nested_reset_scales_object_level(monkeypatch):
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    shop_registry.clear()

    mob_proto = MobIndex(vnum=9450, short_descr="reset mob", level=35)
    container_proto = ObjIndex(vnum=9451, short_descr="a lacquered chest")
    loot_proto = ObjIndex(vnum=9452, short_descr="a velvet pouch")

    mob_registry[mob_proto.vnum] = mob_proto
    obj_registry[container_proto.vnum] = container_proto
    obj_registry[loot_proto.vnum] = loot_proto

    area = Area(vnum=9450, name="Chest Area", min_vnum=9450, max_vnum=9450)
    room = Room(vnum=9450, name="Treasure Vault", area=area)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room

    fuzz_inputs: list[int] = []

    def fake_number_fuzzy(value: int) -> int:
        fuzz_inputs.append(value)
        if len(fuzz_inputs) == 1:
            return value - 1
        return value + 1

    monkeypatch.setattr(reset_handler.rng_mm, "number_fuzzy", fake_number_fuzzy)

    area.resets = [
        ResetJson(command="M", arg1=mob_proto.vnum, arg2=1, arg3=room.vnum, arg4=1),
        ResetJson(command="O", arg1=container_proto.vnum, arg3=room.vnum),
        ResetJson(command="P", arg1=loot_proto.vnum, arg2=1, arg3=container_proto.vnum, arg4=1),
    ]

    reset_handler.apply_resets(area)

    chest = next(
        (
            obj
            for obj in room.contents
            if getattr(getattr(obj, "prototype", None), "vnum", None) == container_proto.vnum
        ),
        None,
    )
    assert chest is not None
    assert chest.level == 32

    assert fuzz_inputs == [33, 32]

    assert len(chest.contained_items) == 1
    nested = chest.contained_items[0]
    assert getattr(getattr(nested, "prototype", None), "vnum", None) == loot_proto.vnum
    assert nested.level == 33


def test_reset_G_allows_multiple_copies_up_to_limit(monkeypatch):
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()

    area = Area(vnum=9201, name="Reset Test Area", min_vnum=9201, max_vnum=9201)
    room = Room(vnum=9201, name="Reset Room", area=area)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room

    mob_proto = MobIndex(vnum=9201, short_descr="reset mob", level=10)
    mob_registry[mob_proto.vnum] = mob_proto
    loot_proto = ObjIndex(vnum=9202, short_descr="reset loot")
    obj_registry[loot_proto.vnum] = loot_proto

    area.resets = [
        ResetJson(command="M", arg1=mob_proto.vnum, arg2=1, arg3=room.vnum, arg4=1),
        ResetJson(command="G", arg1=loot_proto.vnum, arg2=2),
        ResetJson(command="G", arg1=loot_proto.vnum, arg2=2),
    ]

    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)

    reset_handler.apply_resets(area)

    mob = next((m for m in room.people if isinstance(m, MobInstance)), None)
    assert mob is not None

    carried = [
        getattr(getattr(item, "prototype", None), "vnum", None)
        for item in getattr(mob, "inventory", [])
    ]
    assert carried.count(loot_proto.vnum) == 2
    assert getattr(obj_registry.get(loot_proto.vnum), "count", 0) == 2


def test_reset_equips_scale_with_lastmob_level(monkeypatch):
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    shop_registry.clear()

    area = Area(vnum=9300, name="Reset Scale Area", min_vnum=9300, max_vnum=9301)
    room_low = Room(vnum=9300, name="Low Mob Room", area=area)
    room_high = Room(vnum=9301, name="High Mob Room", area=area)
    area_registry[area.vnum] = area
    room_registry[room_low.vnum] = room_low
    room_registry[room_high.vnum] = room_high

    mob_low = MobIndex(vnum=9300, short_descr="a lowbie mob", level=20)
    mob_high = MobIndex(vnum=9301, short_descr="a hero mob", level=LEVEL_HERO + 5)
    mob_registry[mob_low.vnum] = mob_low
    mob_registry[mob_high.vnum] = mob_high

    loot_low = ObjIndex(vnum=9302, short_descr="a training blade")
    loot_high = ObjIndex(vnum=9303, short_descr="a hero blade")
    obj_registry[loot_low.vnum] = loot_low
    obj_registry[loot_high.vnum] = loot_high

    area.resets = [
        ResetJson(command="M", arg1=mob_low.vnum, arg2=1, arg3=room_low.vnum, arg4=1),
        ResetJson(command="G", arg1=loot_low.vnum, arg2=1),
        ResetJson(command="M", arg1=mob_high.vnum, arg2=1, arg3=room_high.vnum, arg4=1),
        ResetJson(command="E", arg1=loot_high.vnum, arg2=1, arg3=0),
    ]

    fuzzy_calls: list[int] = []
    fuzzy_returns = [12, LEVEL_HERO + 5]

    def fake_number_fuzzy(value: int) -> int:
        fuzzy_calls.append(value)
        return fuzzy_returns.pop(0)

    original_number_range = rng_mm.number_range

    def fake_number_range(low: int, high: int) -> int:
        if low == 0 and high == 4:
            return 0
        return original_number_range(low, high)

    monkeypatch.setattr(rng_mm, "number_fuzzy", fake_number_fuzzy)
    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)

    reset_handler.apply_resets(area)

    low_mob = next((m for m in room_low.people if isinstance(m, MobInstance)), None)
    assert low_mob is not None
    low_loot = next(
        (
            obj
            for obj in getattr(low_mob, "inventory", [])
            if getattr(getattr(obj, "prototype", None), "vnum", None) == loot_low.vnum
        ),
        None,
    )
    assert low_loot is not None
    assert low_loot.level == 12

    high_mob = next((m for m in room_high.people if isinstance(m, MobInstance)), None)
    assert high_mob is not None
    high_loot = next(
        (
            obj
            for obj in getattr(high_mob, "inventory", [])
            if getattr(getattr(obj, "prototype", None), "vnum", None) == loot_high.vnum
        ),
        None,
    )
    assert high_loot is not None
    assert high_loot.level == LEVEL_HERO - 1

    assert fuzzy_calls == [max(0, mob_low.level - 2), min(LEVEL_HERO - 1, max(0, mob_high.level - 2))]
    assert fuzzy_returns == []


def test_reset_equips_preserves_new_format_level(monkeypatch):
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    shop_registry.clear()

    area = Area(vnum=9400, name="New Format Area", min_vnum=9400, max_vnum=9401)
    room_mob = Room(vnum=9400, name="Equipper", area=area)
    room_shop = Room(vnum=9401, name="Shop", area=area)
    area_registry[area.vnum] = area
    room_registry[room_mob.vnum] = room_mob
    room_registry[room_shop.vnum] = room_shop

    mob_proto = MobIndex(vnum=9400, short_descr="a seasoned warrior", level=45)
    mob_registry[mob_proto.vnum] = mob_proto

    keeper_proto = MobIndex(vnum=9401, short_descr="a meticulous shopkeeper", level=30)
    keeper_proto.pShop = Shop(keeper=keeper_proto.vnum)
    mob_registry[keeper_proto.vnum] = keeper_proto
    shop_registry[keeper_proto.vnum] = keeper_proto.pShop

    old_format_proto = ObjIndex(vnum=9402, short_descr="a battered blade", item_type=int(ItemType.WEAPON))
    obj_registry[old_format_proto.vnum] = old_format_proto

    new_format_proto = ObjIndex(
        vnum=9403,
        short_descr="a gleaming relic",
        item_type=int(ItemType.WEAPON),
        level=45,
        new_format=True,
    )
    obj_registry[new_format_proto.vnum] = new_format_proto

    shop_item_proto = ObjIndex(
        vnum=9404,
        short_descr="a jewelled circlet",
        item_type=int(ItemType.TREASURE),
        level=30,
        new_format=True,
    )
    obj_registry[shop_item_proto.vnum] = shop_item_proto

    area.resets = [
        ResetJson(command="M", arg1=mob_proto.vnum, arg2=1, arg3=room_mob.vnum, arg4=1),
        ResetJson(command="G", arg1=new_format_proto.vnum, arg2=1),
        ResetJson(command="G", arg1=old_format_proto.vnum, arg2=1),
        ResetJson(command="M", arg1=keeper_proto.vnum, arg2=1, arg3=room_shop.vnum, arg4=1),
        ResetJson(command="G", arg1=shop_item_proto.vnum, arg2=1),
    ]

    fuzzy_calls: list[int] = []

    def fake_number_fuzzy(value: int) -> int:
        fuzzy_calls.append(value)
        return 18

    monkeypatch.setattr(rng_mm, "number_fuzzy", fake_number_fuzzy)
    monkeypatch.setattr(rng_mm, "number_range", lambda low, high: 0 if (low, high) == (0, 4) else low)

    reset_handler.apply_resets(area)

    mob = next((m for m in room_mob.people if isinstance(m, MobInstance)), None)
    assert mob is not None

    inventory = {
        getattr(getattr(item, "prototype", None), "vnum", None): item for item in getattr(mob, "inventory", [])
    }
    assert inventory[new_format_proto.vnum].level == new_format_proto.level
    assert inventory[old_format_proto.vnum].level == 18

    keeper = next((m for m in room_shop.people if isinstance(m, MobInstance)), None)
    assert keeper is not None
    shop_inventory = [
        item for item in getattr(keeper, "inventory", []) if getattr(getattr(item, "prototype", None), "vnum", None) == shop_item_proto.vnum
    ]
    assert shop_inventory, "shopkeeper should receive new-format stock"
    assert shop_inventory[0].level == shop_item_proto.level

    assert fuzzy_calls == [max(0, mob_proto.level - 2)]


def test_reset_equips_limit_overflow_probability(monkeypatch):
    original_number_range = rng_mm.number_range

    monkeypatch.setattr(rng_mm, "number_fuzzy", lambda value: value)

    def build_world():
        room_registry.clear()
        area_registry.clear()
        mob_registry.clear()
        obj_registry.clear()
        shop_registry.clear()
        character_registry.clear()

        area = Area(vnum=9450, name="Overflow Area", min_vnum=9450, max_vnum=9451)
        room = Room(vnum=9450, name="Overflow Room", area=area)
        area_registry[area.vnum] = area
        room_registry[room.vnum] = room

        mob_proto = MobIndex(vnum=9450, short_descr="an overflow mob", level=30)
        mob_registry[mob_proto.vnum] = mob_proto

        obj_proto = ObjIndex(vnum=9451, short_descr="an overflow trinket")
        obj_registry[obj_proto.vnum] = obj_proto

        area.resets = [
            ResetJson(command="M", arg1=mob_proto.vnum, arg2=1, arg3=room.vnum, arg4=1),
            ResetJson(command="G", arg1=obj_proto.vnum, arg2=1),
        ]

        existing_obj = spawn_object(obj_proto.vnum)
        room.add_object(existing_obj)

        return area, room, obj_proto.vnum

    def run_with_roll(roll_value: int) -> list:
        area, room, obj_vnum = build_world()

        def fake_number_range(low: int, high: int) -> int:
            if low == 0 and high == 4:
                return roll_value
            return original_number_range(low, high)

        monkeypatch.setattr(rng_mm, "number_range", fake_number_range)
        reset_handler.apply_resets(area)
        monkeypatch.setattr(rng_mm, "number_range", original_number_range)

        mob = next((m for m in room.people if isinstance(m, MobInstance)), None)
        assert mob is not None
        return [
            obj
            for obj in getattr(mob, "inventory", [])
            if getattr(getattr(obj, "prototype", None), "vnum", None) == obj_vnum
        ]

    denied_inventory = run_with_roll(roll_value=3)
    assert denied_inventory == []

    overflow_inventory = run_with_roll(roll_value=0)
    assert len(overflow_inventory) == 1


def test_reset_generates_overflow_item_for_existing_inventory(monkeypatch):
    original_number_range = rng_mm.number_range

    monkeypatch.setattr(rng_mm, "number_fuzzy", lambda value: value)

    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    shop_registry.clear()
    character_registry.clear()

    area = Area(vnum=3200, name="Overflow Inventory Area", min_vnum=3200, max_vnum=3200)
    room = Room(vnum=3200, name="Overflow Inventory Room", area=area)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room

    mob_proto = MobIndex(vnum=3201, short_descr="an overflow mob", level=30)
    mob_registry[mob_proto.vnum] = mob_proto

    obj_proto = ObjIndex(vnum=3202, short_descr="an overflow trinket")
    obj_registry[obj_proto.vnum] = obj_proto

    area.resets = [
        ResetJson(command="M", arg1=mob_proto.vnum, arg2=1, arg3=room.vnum, arg4=1),
        ResetJson(command="G", arg1=obj_proto.vnum, arg2=1),
        ResetJson(command="G", arg1=obj_proto.vnum, arg2=1),
    ]

    def fake_number_range(low: int, high: int) -> int:
        if low == 0 and high == 4:
            return 0
        return original_number_range(low, high)

    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)
    reset_handler.apply_resets(area)

    mob = next((m for m in room.people if isinstance(m, MobInstance)), None)
    assert mob is not None

    overflow_inventory = [
        obj
        for obj in getattr(mob, "inventory", [])
        if getattr(getattr(obj, "prototype", None), "vnum", None) == obj_proto.vnum
    ]

    assert len(overflow_inventory) == 2


def test_reset_P_skips_when_players_present():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    character_registry.clear()
    initialize_world("area/area.lst")
    office = room_registry[3142]
    area = office.area
    assert area is not None
    area.resets = []
    office.contents.clear()

    area.resets.append(ResetJson(command="O", arg1=3130, arg3=office.vnum))
    area.resets.append(ResetJson(command="P", arg1=3123, arg2=2, arg3=3130, arg4=1))

    from mud.spawning.reset_handler import apply_resets

    apply_resets(area)

    desk = next((o for o in office.contents if getattr(o.prototype, "vnum", None) == 3130), None)
    assert desk is not None
    desk.contained_items.clear()
    key_proto = obj_registry.get(3123)
    if key_proto is not None and hasattr(key_proto, "count"):
        key_proto.count = 0

    area.nplayer = 1
    apply_resets(area)

    assert not any(
        getattr(getattr(it, "prototype", None), "vnum", None) == 3123 for it in getattr(desk, "contained_items", [])
    )
    assert getattr(key_proto, "count", 0) == 0


def test_reset_respects_player_held_limit(monkeypatch):
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    character_registry.clear()

    limited_proto = ObjIndex(vnum=9100, short_descr="a limited relic")
    obj_registry[limited_proto.vnum] = limited_proto

    mob_proto = MobIndex(vnum=9200, short_descr="reset mob", level=10)
    mob_registry[mob_proto.vnum] = mob_proto

    area = Area(vnum=9100, name="Test Area", min_vnum=9100, max_vnum=9100)
    room = Room(vnum=9100, name="Treasure Room", area=area)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room
    area.resets = [
        ResetJson(command="M", arg1=mob_proto.vnum, arg2=1, arg3=room.vnum, arg4=1),
        ResetJson(command="G", arg1=limited_proto.vnum, arg2=1),
    ]

    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)

    reset_handler.apply_resets(area)

    mob = next((m for m in room.people if isinstance(m, MobInstance)), None)
    assert mob is not None
    treasure = next(
        (
            obj
            for obj in getattr(mob, "inventory", [])
            if getattr(getattr(obj, "prototype", None), "vnum", None) == limited_proto.vnum
        ),
        None,
    )
    assert treasure is not None
    assert getattr(limited_proto, "count", 0) == 1

    mob.inventory.remove(treasure)
    player = Character(name="Holder", is_npc=False)
    character_registry.append(player)
    player.add_object(treasure)
    player.room = room
    room.people.append(player)

    room.people = [p for p in room.people if not isinstance(p, MobInstance)]
    proto = mob_registry.get(mob_proto.vnum)
    if proto is not None and hasattr(proto, "count"):
        proto.count = 0

    reset_handler.apply_resets(area)

    new_mob = next((m for m in room.people if isinstance(m, MobInstance)), None)
    assert new_mob is not None
    assert not any(
        getattr(getattr(obj, "prototype", None), "vnum", None) == limited_proto.vnum
        for obj in getattr(new_mob, "inventory", [])
    )
    assert getattr(limited_proto, "count", 0) == 1


def test_reset_does_not_refill_player_container():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    character_registry.clear()

    container_proto = ObjIndex(vnum=9101, short_descr="a traveling chest")
    loot_proto = ObjIndex(vnum=9102, short_descr="a rare gem")
    obj_registry[container_proto.vnum] = container_proto
    obj_registry[loot_proto.vnum] = loot_proto

    area = Area(vnum=9101, name="Container Area", min_vnum=9101, max_vnum=9101)
    room = Room(vnum=9101, name="Vault", area=area)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room
    area.resets = [
        ResetJson(command="O", arg1=container_proto.vnum, arg2=1, arg3=room.vnum),
        ResetJson(command="P", arg1=loot_proto.vnum, arg2=1, arg3=container_proto.vnum, arg4=1),
    ]

    reset_handler.apply_resets(area)

    chest = next(
        (
            obj
            for obj in room.contents
            if getattr(getattr(obj, "prototype", None), "vnum", None) == container_proto.vnum
        ),
        None,
    )
    assert chest is not None
    assert any(
        getattr(getattr(item, "prototype", None), "vnum", None) == loot_proto.vnum
        for item in getattr(chest, "contained_items", [])
    )

    player = Character(name="Collector", is_npc=False)
    character_registry.append(player)
    room.add_character(player)

    loot = chest.contained_items.pop()
    player.add_object(loot)
    room.contents.remove(chest)
    chest.location = None
    player.add_object(chest)

    room.remove_character(player)
    assert area.nplayer == 0

    reset_handler.apply_resets(area)

    assert getattr(chest, "contained_items", []) == []
    assert getattr(loot_proto, "count", 0) == 1


def test_shopkeeper_inventory_ignores_limit(monkeypatch):
    from mud.spawning.reset_handler import apply_resets
    from mud.utils import rng_mm

    def setup_shop_area():
        room_registry.clear()
        area_registry.clear()
        mob_registry.clear()
        obj_registry.clear()
        initialize_world("area/area.lst")
        room = room_registry[3001]
        area = room.area
        assert area is not None
        area.resets = []
        for candidate in room_registry.values():
            if candidate.area is area:
                candidate.people = [p for p in candidate.people if not isinstance(p, MobInstance)]
        room.contents.clear()
        area.resets.append(ResetJson(command="M", arg1=3000, arg2=1, arg3=room.vnum, arg4=1))
        area.resets.append(ResetJson(command="G", arg1=3031, arg2=1))
        area.resets.append(ResetJson(command="G", arg1=3031, arg2=1))
        return area, room

    area, room = setup_shop_area()
    lantern_proto = obj_registry.get(3031)
    assert lantern_proto is not None
    original_proto_flags = int(getattr(lantern_proto, "extra_flags", 0) or 0)
    existing = spawn_object(3031)
    assert existing is not None
    room.contents.append(existing)
    monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)
    apply_resets(area)
    keeper = next((p for p in room.people if getattr(getattr(p, "prototype", None), "vnum", None) == 3000), None)
    assert keeper is not None
    inv = [getattr(o.prototype, "vnum", None) for o in getattr(keeper, "inventory", [])]
    assert inv.count(3031) >= 1
    item = next(o for o in keeper.inventory if getattr(o.prototype, "vnum", None) == 3031)
    assert getattr(item, "extra_flags", 0) & int(ITEM_INVENTORY)
    assert int(getattr(item.prototype, "extra_flags", 0) or 0) == original_proto_flags
    assert getattr(lantern_proto, "count", 0) >= 2

    # A second reset should keep restocking even though the keeper already holds a copy.
    apply_resets(area)
    inv = [getattr(o.prototype, "vnum", None) for o in getattr(keeper, "inventory", [])]
    assert inv.count(3031) >= 2


def test_reset_shopkeeper_inventory_does_not_mutate_prototype():
    from mud.spawning.reset_handler import apply_resets

    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    shop_registry.clear()
    character_registry.clear()

    area = Area(vnum=9100, name="Shop Sanity", min_vnum=9100, max_vnum=9100)
    area_registry[area.vnum] = area
    room = Room(vnum=9100, name="Shop Room", area=area)
    room_registry[room.vnum] = room

    trinket_proto = ObjIndex(vnum=9101, short_descr="a shop trinket", level=1, extra_flags=0)
    obj_registry[trinket_proto.vnum] = trinket_proto

    keeper_proto = MobIndex(vnum=9102, short_descr="a diligent shopkeeper", level=30, act_flags=int(ActFlag.IS_NPC))
    keeper_proto.hit = (0, 0, 0)
    keeper_proto.mana = (0, 0, 0)
    keeper_proto.damage = (0, 0, 0)
    keeper_proto.pShop = Shop(keeper=keeper_proto.vnum)
    mob_registry[keeper_proto.vnum] = keeper_proto
    shop_registry[keeper_proto.vnum] = keeper_proto.pShop

    guard_proto = MobIndex(vnum=9103, short_descr="a city guard", level=20, act_flags=int(ActFlag.IS_NPC))
    guard_proto.hit = (0, 0, 0)
    guard_proto.mana = (0, 0, 0)
    guard_proto.damage = (0, 0, 0)
    mob_registry[guard_proto.vnum] = guard_proto

    area.resets = [
        ResetJson(command="M", arg1=keeper_proto.vnum, arg2=1, arg3=room.vnum, arg4=1),
        ResetJson(command="G", arg1=trinket_proto.vnum, arg2=1),
        ResetJson(command="M", arg1=guard_proto.vnum, arg2=1, arg3=room.vnum, arg4=2),
        ResetJson(command="G", arg1=trinket_proto.vnum, arg2=1),
    ]

    apply_resets(area)

    keeper = next(
        (p for p in room.people if isinstance(p, MobInstance) and getattr(getattr(p, "prototype", None), "vnum", None) == keeper_proto.vnum),
        None,
    )
    guard = next(
        (p for p in room.people if isinstance(p, MobInstance) and getattr(getattr(p, "prototype", None), "vnum", None) == guard_proto.vnum),
        None,
    )

    assert keeper is not None and guard is not None

    keeper_item = next(o for o in keeper.inventory if getattr(getattr(o, "prototype", None), "vnum", None) == trinket_proto.vnum)
    guard_item = next(o for o in guard.inventory if getattr(getattr(o, "prototype", None), "vnum", None) == trinket_proto.vnum)

    proto_flags = int(getattr(trinket_proto, "extra_flags", 0) or 0)
    assert keeper_item.extra_flags & int(ITEM_INVENTORY)
    assert not (guard_item.extra_flags & int(ITEM_INVENTORY))
    assert int(getattr(keeper_item.prototype, "extra_flags", 0) or 0) == proto_flags
    assert int(getattr(guard_item.prototype, "extra_flags", 0) or 0) == proto_flags


def test_spawn_object_preserves_extra_flags_from_letters():
    obj_registry.clear()

    proto = ObjIndex(vnum=9205, short_descr="a glowing relic", extra_flags="AG")
    obj_registry[proto.vnum] = proto

    inst = spawn_object(proto.vnum)

    assert inst is not None
    expected_flags = int(convert_flags_from_letters("AG", ExtraFlag))
    assert inst.extra_flags == expected_flags
    assert getattr(proto, "extra_flags") == "AG"


def test_reset_shopkeeper_potion_levels_use_skill_metadata():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    shop_registry.clear()
    character_registry.clear()

    area = Area(vnum=9200, name="Shop Test", min_vnum=9200, max_vnum=9200)
    room = Room(vnum=9201, name="Potion Counter", area=area)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room

    keeper_proto = MobIndex(vnum=9202, short_descr="the meticulous vendor", level=30)
    mob_registry[keeper_proto.vnum] = keeper_proto
    shop_registry[keeper_proto.vnum] = Shop(keeper=keeper_proto.vnum)

    heal_metadata = ROM_SKILL_METADATA["heal"]
    heal_slot = int(heal_metadata["slot"])
    potion_proto = ObjIndex(
        vnum=9203,
        short_descr="a vial of radiant liquid",
        item_type="potion",
        value=[0, heal_slot, 0, 0, 0],
    )
    obj_registry[potion_proto.vnum] = potion_proto

    area.resets = [
        ResetJson(command="M", arg1=keeper_proto.vnum, arg2=1, arg3=room.vnum, arg4=1),
        ResetJson(command="G", arg1=potion_proto.vnum, arg2=1),
    ]

    reset_handler.apply_resets(area)

    keeper = next((mob for mob in room.people if isinstance(mob, MobInstance)), None)
    assert keeper is not None

    potion = next(
        (
            obj
            for obj in getattr(keeper, "inventory", [])
            if getattr(getattr(obj, "prototype", None), "vnum", None) == potion_proto.vnum
        ),
        None,
    )
    assert potion is not None

    olevel = 53
    for level in heal_metadata["levels"]:
        olevel = min(olevel, int(level))
    expected_level = max(0, (olevel * 3 // 4) - 2)

    assert potion.level == expected_level


def test_equipment_reset_skips_after_failed_room_reset():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    character_registry.clear()

    area = Area(vnum=9400, name="Last Flag Test", min_vnum=9400, max_vnum=9400)
    room = Room(vnum=9401, name="Crowded Hall", area=area)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room

    mob_proto = MobIndex(vnum=9402, short_descr="the hall guard", level=20)
    mob_registry[mob_proto.vnum] = mob_proto

    ground_proto = ObjIndex(vnum=9403, short_descr="a banner stand")
    obj_registry[ground_proto.vnum] = ground_proto

    sword_proto = ObjIndex(vnum=9404, short_descr="a parade blade", item_type="weapon")
    obj_registry[sword_proto.vnum] = sword_proto

    area.resets = [
        ResetJson(command="M", arg1=mob_proto.vnum, arg2=1, arg3=room.vnum, arg4=1),
        ResetJson(command="O", arg1=ground_proto.vnum, arg2=1, arg3=room.vnum),
        ResetJson(command="G", arg1=sword_proto.vnum, arg2=1),
    ]

    area.nplayer = 1

    reset_handler.apply_resets(area)

    guard = next((mob for mob in room.people if isinstance(mob, MobInstance)), None)
    assert guard is not None

    equipped = [
        obj
        for obj in getattr(guard, "inventory", [])
        if getattr(getattr(obj, "prototype", None), "vnum", None) == sword_proto.vnum
    ]

    assert not equipped


def test_reset_tick_announces_wiznet(monkeypatch):
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    character_registry.clear()

    area = Area(vnum=9300, name="Silver Falls")
    area_registry[area.vnum] = area
    area.age = 2
    area.nplayer = 0
    area.empty = False

    calls: list[tuple[str, object]] = []

    def fake_reset(target: Area) -> None:
        target.age = 0

    monkeypatch.setattr(reset_handler, "reset_area", fake_reset)
    monkeypatch.setattr(reset_handler.rng_mm, "number_range", lambda a, b: 1)

    from mud.wiznet import WiznetFlag

    def capture(message: str, flag: object, *_, **__) -> None:
        calls.append((message, flag))

    monkeypatch.setattr("mud.wiznet.wiznet", capture)

    reset_tick()

    assert calls == [("Silver Falls has just been reset.", WiznetFlag.WIZ_RESETS)]


def test_reset_mob_limits():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world("area/area.lst")

    wizard_room = room_registry[3033]
    area = wizard_room.area
    assert area is not None
    area.resets = []
    wizard_room.people = [p for p in wizard_room.people if not isinstance(p, MobInstance)]

    # Pre-spawn a wizard so the global limit prevents another copy.
    existing_wizard = spawn_mob(3000)
    assert existing_wizard is not None
    wizard_room.add_mob(existing_wizard)

    area.resets.append(ResetJson(command="M", arg1=3000, arg2=1, arg3=wizard_room.vnum, arg4=1))
    from mud.spawning.reset_handler import apply_resets

    apply_resets(area)

    wizard_vnums = [
        getattr(getattr(mob, "prototype", None), "vnum", None)
        for mob in wizard_room.people
        if isinstance(mob, MobInstance)
    ]
    assert wizard_vnums.count(3000) == 1

    # Clear mobs in the room and validate per-room limits when multiple resets exist.
    wizard_room.people = [p for p in wizard_room.people if not isinstance(p, MobInstance)]
    area.resets = [
        ResetJson(command="M", arg1=3003, arg2=5, arg3=wizard_room.vnum, arg4=1),
        ResetJson(command="M", arg1=3003, arg2=5, arg3=wizard_room.vnum, arg4=1),
    ]
    apply_resets(area)

    janitor_vnums = [
        getattr(getattr(mob, "prototype", None), "vnum", None)
        for mob in wizard_room.people
        if isinstance(mob, MobInstance)
    ]
    assert janitor_vnums.count(3003) == 1


def test_resets_room_duplication_and_player_presence():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world("area/area.lst")
    office = room_registry[3142]
    area = office.area
    assert area is not None
    area.resets = []
    office.contents.clear()

    area.resets.append(ResetJson(command="O", arg1=3130, arg3=office.vnum))

    from mud.spawning.reset_handler import apply_resets

    apply_resets(area)

    def desk_count() -> int:
        return sum(1 for o in office.contents if getattr(getattr(o, "prototype", None), "vnum", None) == 3130)

    assert desk_count() == 1

    apply_resets(area)
    assert desk_count() == 1

    desk = next((o for o in office.contents if getattr(o.prototype, "vnum", None) == 3130), None)
    assert desk is not None
    office.contents.remove(desk)
    if hasattr(desk.prototype, "count"):
        desk.prototype.count = max(0, desk.prototype.count - 1)

    area.nplayer = 1
    apply_resets(area)
    assert desk_count() == 0

    area.nplayer = 0
    apply_resets(area)
    assert desk_count() == 1


def test_area_player_counts_follow_char_moves():
    room_registry.clear()
    area_registry.clear()

    area = Area(vnum=9000, name="Test Area", min_vnum=9000, max_vnum=9001)
    area.empty = True
    area.age = 5
    area_registry[area.vnum] = area

    start = Room(vnum=9000, name="Start Room", area=area)
    target = Room(vnum=9001, name="Target Room", area=area)
    start.exits[Direction.NORTH.value] = Exit(to_room=target)
    target.exits[Direction.SOUTH.value] = Exit(to_room=start)
    room_registry[start.vnum] = start
    room_registry[target.vnum] = target

    player = Character(name="Traveler", is_npc=False, move=100)
    start.add_character(player)

    assert area.nplayer == 1
    assert area.empty is False
    assert area.age == 0

    response = move_character(player, "north")
    assert response == "You walk north to Target Room."
    assert player.room is target
    assert area.nplayer == 1
    assert area.empty is False

    target.remove_character(player)
    assert area.nplayer == 0
    assert area.empty is False


def test_area_reset_schedule_matches_rom(monkeypatch):
    area_registry.clear()
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()

    test_area = Area(vnum=9999, name="Test Area")
    area_registry[test_area.vnum] = test_area

    reset_calls: list[Area] = []

    def fake_reset(target: Area) -> None:
        reset_calls.append(target)

    monkeypatch.setattr(reset_handler, "reset_area", fake_reset)
    monkeypatch.setattr(reset_handler.rng_mm, "number_range", lambda a, b: 2)

    test_area.age = 0
    test_area.nplayer = 0
    test_area.empty = False

    reset_calls.clear()
    reset_tick()
    assert reset_calls == []
    reset_tick()
    assert reset_calls == []
    reset_tick()
    assert reset_calls == [test_area]
    assert test_area.age == 2
    assert test_area.empty is True

    reset_calls.clear()
    test_area.age = 30
    test_area.nplayer = 0
    test_area.empty = True
    reset_tick()
    assert reset_calls == [test_area]
    assert test_area.age == 2
    assert test_area.empty is True

    reset_calls.clear()
    test_area.age = 14
    test_area.nplayer = 1
    test_area.empty = False
    reset_tick()
    assert reset_calls == [test_area]
    assert test_area.age == 2
    assert test_area.empty is False

    area_registry.pop(test_area.vnum, None)
