from mud.world import initialize_world
from mud.registry import room_registry, area_registry, mob_registry, obj_registry
from mud.spawning.reset_handler import reset_tick, RESET_TICKS
from mud.models.room_json import ResetJson
from mud.spawning.mob_spawner import spawn_mob


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
    area.resets.append(ResetJson(command='O', arg2=3130, arg4=office.vnum))
    area.resets.append(ResetJson(command='P', arg2=3123, arg3=1, arg4=3130))
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
    area.resets.append(ResetJson(command='O', arg2=3130, arg4=office.vnum))
    area.resets.append(ResetJson(command='P', arg2=3123, arg3=1, arg4=3130))
    area.resets.append(ResetJson(command='O', arg2=3130, arg4=office.vnum))
    area.resets.append(ResetJson(command='P', arg2=3123, arg3=1, arg4=3130))
    from mud.spawning.reset_handler import apply_resets
    apply_resets(area)
    desks = [o for o in office.contents if getattr(o.prototype, 'vnum', None) == 3130]
    assert len(desks) == 2
    counts = [sum(1 for it in getattr(d, 'contained_items', []) if getattr(getattr(it, 'prototype', None), 'vnum', None) == 3123) for d in desks]
    assert counts == [1, 1]


def test_reset_GE_limits_and_shopkeeper_inventory_flag():
    room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    initialize_world('area/area.lst')
    room = room_registry[3001]
    area = room.area; assert area is not None
    # Narrow to controlled resets only
    area.resets = []
    # Spawn a shopkeeper (3000) in room 3001
    area.resets.append(ResetJson(command='M', arg2=3000, arg4=room.vnum))
    # Give two copies of lantern (3031) but limit to 1
    area.resets.append(ResetJson(command='G', arg2=3031, arg3=1))
    area.resets.append(ResetJson(command='G', arg2=3031, arg3=1))
    from mud.spawning.reset_handler import apply_resets
    apply_resets(area)
    keeper = next((p for p in room.people if getattr(getattr(p, 'prototype', None), 'vnum', None) == 3000), None)
    assert keeper is not None
    inv = [getattr(o.prototype, 'vnum', None) for o in getattr(keeper, 'inventory', [])]
    assert inv.count(3031) == 1
    # The inventory copy should be flagged as ITEM_INVENTORY (1<<13) on prototype
    item = next(o for o in keeper.inventory if getattr(o.prototype, 'vnum', None) == 3031)
    assert getattr(item.prototype, 'extra_flags', 0) & (1 << 13)
