from mud.loaders.area_loader import load_area_file
from mud.registry import area_registry, mob_registry, room_registry
from mud.spec_funs import register_spec_fun


def setup_function(_):
    mob_registry.clear()
    area_registry.clear()
    room_registry.clear()


def test_load_specials_sets_spec_fun_on_mob_prototypes():
    load_area_file("area/haon.are")
    proto = mob_registry.get(6112)
    assert proto is not None
    assert (proto.spec_fun or "").lower() == "spec_breath_gas"


def test_run_npc_specs_invokes_registered_function(monkeypatch):
    # Load area with rooms so we can place a mob
    load_area_file("area/limbo.are")
    # Manually register a dummy spec and assign to a mob prototype
    called = []

    def dummy(mob):
        called.append(getattr(mob, "name", ""))

    register_spec_fun("spec_dummy", dummy)
    # Create a mob with that spec_fun and place in a known room
    from mud.models.mob import MobIndex

    mob_registry[99999] = MobIndex(vnum=99999, short_descr="Spec Mob", level=1, spec_fun="spec_dummy")
    from mud.models.room import Room

    room = Room(vnum=42, name="Test", description="", sector_type=0)
    room_registry[42] = room
    from mud.spawning.templates import MobInstance

    m = MobInstance.from_prototype(mob_registry[99999])
    room.add_mob(m)
    from mud.spec_funs import run_npc_specs

    run_npc_specs()
    assert called, "spec fun should have been invoked"
