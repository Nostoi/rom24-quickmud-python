from mud.registry import room_registry
from mud.spec_funs import get_spec_fun, register_spec_fun, run_npc_specs


def test_get_spec_fun_case_insensitive_and_unknown_returns_none():
    f = get_spec_fun("SPEC_CAST_ADEPT")
    assert callable(f)
    assert get_spec_fun("__nope__") is None


def test_run_npc_specs_ignores_errors(monkeypatch):
    # Arrange a room with a mob whose spec fun raises
    from mud.models.mob import MobIndex
    from mud.models.room import Room
    from mud.spawning.templates import MobInstance

    def boom(_):
        raise RuntimeError("kaboom")

    register_spec_fun("spec_boom", boom)
    proto = MobIndex(vnum=55555, short_descr="Boomer", level=1, spec_fun="spec_boom")
    m = MobInstance.from_prototype(proto)
    room = Room(vnum=1, name="r", description="", sector_type=0)
    room_registry[1] = room
    room.add_mob(m)

    # Should not raise despite spec throwing
    run_npc_specs()
