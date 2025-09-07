from mud.spec_funs import get_spec_fun, register_spec_fun, spec_fun_registry, run_npc_specs
from mud.world import initialize_world, create_test_character
from mud.spawning.mob_spawner import spawn_mob
from mud.registry import mob_registry


def test_case_insensitive_lookup() -> None:
    called: list[tuple[object, ...]] = []

    def dummy(*args: object) -> None:  # placeholder spec_fun
        called.append(args)
    prev = dict(spec_fun_registry)
    try:
        register_spec_fun("Spec_Test", dummy)

        assert get_spec_fun("spec_test") is dummy
        assert get_spec_fun("SPEC_TEST") is dummy
        assert called == []
    finally:
        spec_fun_registry.clear()
        spec_fun_registry.update(prev)


def test_registry_executes_function():
    initialize_world('area/area.lst')
    # Use an existing mob prototype and give it a spec name
    proto = mob_registry.get(3000)
    assert proto is not None
    proto.spec_fun = 'Spec_Dummy'

    calls: list[object] = []

    def dummy(mob):  # spec fun signature: (mob) -> None
        calls.append(mob)

    prev = dict(spec_fun_registry)
    try:
        register_spec_fun('spec_dummy', dummy)
        # Place mob in a real room
        ch = create_test_character('Tester', 3001)
        mob = spawn_mob(3000)
        assert mob is not None
        ch.room.add_mob(mob)
        # Preconditions
        assert getattr(mob, 'prototype', None) is proto
        assert getattr(mob.prototype, 'spec_fun', None) == 'Spec_Dummy'
        assert any(getattr(e, 'prototype', None) is not None for e in ch.room.people)

        # Ensure resolver returns our dummy
        assert get_spec_fun(proto.spec_fun) is dummy
        run_npc_specs()
        assert calls and calls[0] is mob
    finally:
        spec_fun_registry.clear()
        spec_fun_registry.update(prev)


def test_mob_spec_fun_invoked():
    initialize_world('area/area.lst')
    proto = mob_registry.get(3000)
    assert proto is not None
    proto.spec_fun = 'Spec_Log'

    messages: list[str] = []

    def spec_log(mob):
        messages.append(f"tick:{getattr(mob, 'name', '?')}")

    prev = dict(spec_fun_registry)
    try:
        register_spec_fun('Spec_Log', spec_log)
        ch = create_test_character('Tester', 3001)
        mob = spawn_mob(3000)
        ch.room.add_mob(mob)
        assert getattr(mob.prototype, 'spec_fun', None) == 'Spec_Log'

        run_npc_specs()
        assert any(msg.startswith('tick:') for msg in messages)
    finally:
        spec_fun_registry.clear()
        spec_fun_registry.update(prev)
