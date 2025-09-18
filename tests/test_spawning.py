from mud.world import initialize_world
from mud.registry import room_registry, area_registry, mob_registry, obj_registry
from mud.spawning.reset_handler import reset_tick, RESET_TICKS
from mud.models.room_json import ResetJson
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.templates import MobInstance


def test_resets_populate_world():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world('area/area.lst')
    bakery = room_registry[3001]
    assert any(getattr(m, 'name', None) for m in bakery.people)

    donation = room_registry[3054]
    assert any(getattr(o, 'short_descr', None) == 'the donation pit' for o in donation.contents)


def test_resets_repop_after_tick():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world('area/area.lst')
    bakery = room_registry[3001]
    donation = room_registry[3054]
    bakery.people.clear()
    donation.contents.clear()
    for _ in range(RESET_TICKS):
        reset_tick()
    assert any(getattr(m, 'name', None) for m in bakery.people)
    assert any(getattr(o, 'short_descr', None) == 'the donation pit' for o in donation.contents)


def test_reset_P_places_items_inside_container_in_midgaard():
    # Ensure a clean world and load Midgaard where P resets exist (desk/safe)
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world('area/area.lst')

    # Captain's Office (3142) contains a desk (3130) with a key (3123)
    office = room_registry[3142]
    desk = next((o for o in office.contents if getattr(o.prototype, 'vnum', None) == 3130), None)
    assert desk is not None
    desk_contents = [getattr(o.prototype, 'vnum', None) for o in getattr(desk, 'contained_items', [])]
    assert 3123 in desk_contents

    # Safe (3131) contains silver coins (3132)
    safe = next((o for o in office.contents if getattr(o.prototype, 'vnum', None) == 3131), None)
    assert safe is not None
    safe_contents = [getattr(o.prototype, 'vnum', None) for o in getattr(safe, 'contained_items', [])]
    assert 3132 in safe_contents


def test_p_reset_lock_state_fix_resets_container_value_field():
    # Ensure container instance's value[1] mirrors prototype after P population
    room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    initialize_world('area/area.lst')
    office = room_registry[3142]
    area = office.area; assert area is not None
    area.resets = []
    office.contents.clear()
    # Spawn desk (3130), then put key (3123) to trigger P logic
    area.resets.append(ResetJson(command='O', arg1=3130, arg3=office.vnum))
    area.resets.append(ResetJson(command='P', arg1=3123, arg2=1, arg3=3130, arg4=1))
    from mud.spawning.reset_handler import apply_resets
    apply_resets(area)
    desk = next((o for o in office.contents if getattr(o.prototype, 'vnum', None) == 3130), None)
    assert desk is not None
    # Instance value[1] equals prototype value[1]
    assert hasattr(desk, 'value')
    assert desk.value[1] == desk.prototype.value[1]


def test_reset_R_randomizes_exit_order(monkeypatch):
    # Use a deterministic RNG to force swaps
    from mud.utils import rng_mm
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world('area/area.lst')
    room = room_registry[3001]
    original = list(room.exits)
    # Ensure at least 3 slots considered
    count = min(3, len(room.exits))
    # Inject an R reset for this room into its area and apply
    area = room.area
    assert area is not None
    area.resets.append(ResetJson(command='R', arg1=room.vnum, arg2=count))

    seq = []
    def fake_number_range(a, b):
        # always pick the last index to maximize change
        seq.append((a, b))
        return b

    monkeypatch.setattr(rng_mm, 'number_range', fake_number_range)
    from mud.spawning.reset_handler import apply_resets
    apply_resets(area)
    after = room.exits
    assert after != original


def test_reset_P_uses_last_container_instance_when_multiple():
    # Build a controlled sequence: two desks (3130) into Captain's Office (3142),
    # then put a key (3123) into each using P after each O.
    room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    initialize_world('area/area.lst')
    office = room_registry[3142]
    area = office.area; assert area is not None
    area.resets = []
    office.contents.clear()
    area.resets.append(ResetJson(command='O', arg1=3130, arg3=office.vnum))
    area.resets.append(ResetJson(command='P', arg1=3123, arg2=1, arg3=3130, arg4=1))
    area.resets.append(ResetJson(command='O', arg1=3130, arg3=office.vnum))
    area.resets.append(ResetJson(command='P', arg1=3123, arg2=1, arg3=3130, arg4=1))
    from mud.spawning.reset_handler import apply_resets
    apply_resets(area)
    desks = [o for o in office.contents if getattr(o.prototype, 'vnum', None) == 3130]
    assert len(desks) == 2
    counts = [sum(1 for it in getattr(d, 'contained_items', []) if getattr(getattr(it, 'prototype', None), 'vnum', None) == 3123) for d in desks]
    assert counts == [1, 1]


def test_reset_P_limit_enforced():
    room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    initialize_world('area/area.lst')
    office = room_registry[3142]
    area = office.area; assert area is not None
    area.resets = []
    office.contents.clear()

    area.resets.append(ResetJson(command='O', arg1=3130, arg3=office.vnum))
    area.resets.append(ResetJson(command='P', arg1=3123, arg2=1, arg3=3130, arg4=1))
    area.resets.append(ResetJson(command='P', arg1=3123, arg2=1, arg3=3130, arg4=1))

    from mud.spawning.reset_handler import apply_resets
    apply_resets(area)

    desk = next((o for o in office.contents if getattr(o.prototype, 'vnum', None) == 3130), None)
    assert desk is not None
    contents = [getattr(getattr(it, 'prototype', None), 'vnum', None) for it in getattr(desk, 'contained_items', [])]
    assert contents.count(3123) == 1
    assert getattr(obj_registry.get(3123), 'count', 0) == 1


def test_reset_P_skips_when_players_present():
    room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    initialize_world('area/area.lst')
    office = room_registry[3142]
    area = office.area; assert area is not None
    area.resets = []
    office.contents.clear()

    area.resets.append(ResetJson(command='O', arg1=3130, arg3=office.vnum))
    area.resets.append(ResetJson(command='P', arg1=3123, arg2=2, arg3=3130, arg4=1))

    from mud.spawning.reset_handler import apply_resets
    apply_resets(area)

    desk = next((o for o in office.contents if getattr(o.prototype, 'vnum', None) == 3130), None)
    assert desk is not None
    desk.contained_items.clear()
    key_proto = obj_registry.get(3123)
    if key_proto is not None and hasattr(key_proto, 'count'):
        key_proto.count = 0

    area.nplayer = 1
    apply_resets(area)

    assert not any(getattr(getattr(it, 'prototype', None), 'vnum', None) == 3123 for it in getattr(desk, 'contained_items', []))
    assert getattr(key_proto, 'count', 0) == 0


def test_reset_GE_limits_and_shopkeeper_inventory_flag(monkeypatch):
    room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    initialize_world('area/area.lst')
    room = room_registry[3001]
    area = room.area; assert area is not None
    # Narrow to controlled resets only
    area.resets = []
    # Spawn a shopkeeper (3000) in room 3001
    area.resets.append(ResetJson(command='M', arg1=3000, arg2=1, arg3=room.vnum, arg4=1))
    # Give two copies of lantern (3031) but limit to 1
    area.resets.append(ResetJson(command='G', arg1=3031, arg2=1))
    area.resets.append(ResetJson(command='G', arg1=3031, arg2=1))
    from mud.utils import rng_mm

    original_number_range = rng_mm.number_range

    def guard_number_range(start: int, end: int) -> int:
        if (start, end) == (0, 4):
            return 1
        return original_number_range(start, end)

    monkeypatch.setattr(rng_mm, 'number_range', guard_number_range)
    from mud.spawning.reset_handler import apply_resets
    apply_resets(area)
    keeper = next((p for p in room.people if getattr(getattr(p, 'prototype', None), 'vnum', None) == 3000), None)
    assert keeper is not None
    inv = [getattr(o.prototype, 'vnum', None) for o in getattr(keeper, 'inventory', [])]
    assert inv.count(3031) == 1
    # The inventory copy should be flagged as ITEM_INVENTORY (1<<13) on prototype
    item = next(o for o in keeper.inventory if getattr(o.prototype, 'vnum', None) == 3031)
    assert getattr(item.prototype, 'extra_flags', 0) & (1 << 13)


def test_reset_G_reroll_allows_extra_copy(monkeypatch):
    room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    initialize_world('area/area.lst')
    room = room_registry[3001]
    area = room.area; assert area is not None
    area.resets = []
    area.resets.append(ResetJson(command='M', arg1=3000, arg2=1, arg3=room.vnum, arg4=1))
    area.resets.append(ResetJson(command='G', arg1=3031, arg2=1))
    area.resets.append(ResetJson(command='G', arg1=3031, arg2=1))
    from mud.utils import rng_mm

    original_number_range = rng_mm.number_range
    reroll_calls: list[tuple[int, int]] = []

    def reroll_number_range(start: int, end: int) -> int:
        if (start, end) == (0, 4):
            reroll_calls.append((start, end))
            return 0
        return original_number_range(start, end)

    monkeypatch.setattr(rng_mm, 'number_range', reroll_number_range)
    from mud.spawning.reset_handler import apply_resets

    apply_resets(area)
    assert reroll_calls == [(0, 4)]
    keeper = next((p for p in room.people if getattr(getattr(p, 'prototype', None), 'vnum', None) == 3000), None)
    assert keeper is not None
    inv = [getattr(o.prototype, 'vnum', None) for o in getattr(keeper, 'inventory', [])]
    assert inv.count(3031) == 2


def test_reset_mob_limits():
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    initialize_world('area/area.lst')

    wizard_room = room_registry[3033]
    area = wizard_room.area
    assert area is not None
    area.resets = []
    wizard_room.people = [p for p in wizard_room.people if not isinstance(p, MobInstance)]

    # Pre-spawn a wizard so the global limit prevents another copy.
    existing_wizard = spawn_mob(3000)
    assert existing_wizard is not None
    wizard_room.add_mob(existing_wizard)

    area.resets.append(ResetJson(command='M', arg1=3000, arg2=1, arg3=wizard_room.vnum, arg4=1))
    from mud.spawning.reset_handler import apply_resets
    apply_resets(area)

    wizard_vnums = [
        getattr(getattr(mob, 'prototype', None), 'vnum', None)
        for mob in wizard_room.people
        if isinstance(mob, MobInstance)
    ]
    assert wizard_vnums.count(3000) == 1

    # Clear mobs in the room and validate per-room limits when multiple resets exist.
    wizard_room.people = [p for p in wizard_room.people if not isinstance(p, MobInstance)]
    area.resets = [
        ResetJson(command='M', arg1=3003, arg2=5, arg3=wizard_room.vnum, arg4=1),
        ResetJson(command='M', arg1=3003, arg2=5, arg3=wizard_room.vnum, arg4=1),
    ]
    apply_resets(area)

    janitor_vnums = [
        getattr(getattr(mob, 'prototype', None), 'vnum', None)
        for mob in wizard_room.people
        if isinstance(mob, MobInstance)
    ]
    assert janitor_vnums.count(3003) == 1


def test_resets_room_duplication_and_player_presence():
    room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    initialize_world('area/area.lst')
    office = room_registry[3142]
    area = office.area; assert area is not None
    area.resets = []
    office.contents.clear()

    area.resets.append(ResetJson(command='O', arg1=3130, arg3=office.vnum))

    from mud.spawning.reset_handler import apply_resets
    apply_resets(area)

    def desk_count() -> int:
        return sum(1 for o in office.contents if getattr(getattr(o, 'prototype', None), 'vnum', None) == 3130)

    assert desk_count() == 1

    apply_resets(area)
    assert desk_count() == 1

    desk = next((o for o in office.contents if getattr(o.prototype, 'vnum', None) == 3130), None)
    assert desk is not None
    office.contents.remove(desk)
    if hasattr(desk.prototype, 'count'):
        desk.prototype.count = max(0, desk.prototype.count - 1)

    area.nplayer = 1
    apply_resets(area)
    assert desk_count() == 0

    area.nplayer = 0
    apply_resets(area)
    assert desk_count() == 1
