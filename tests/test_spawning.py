from mud.world import initialize_world
from mud.registry import room_registry, area_registry, mob_registry, obj_registry
from mud.spawning.reset_handler import reset_tick, RESET_TICKS


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
    from mud.models.room_json import ResetJson
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
