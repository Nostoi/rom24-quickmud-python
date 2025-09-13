from mud.spec_funs import get_spec_fun, register_spec_fun, spec_fun_registry, run_npc_specs
from mud.world import initialize_world, create_test_character
from mud.spawning.mob_spawner import spawn_mob
from mud.registry import mob_registry
from mud.utils import rng_mm


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


def test_spec_cast_adept_rng():
    """RNG sequence parity anchor for spec_cast_adept using Mitchell–Moore.

    Seeds the MM generator and verifies the first several number_percent
    outputs match known-good values derived from ROM semantics. Also asserts
    that spec_cast_adept returns True/False in lockstep with a <=25 threshold
    over that sequence, proving it uses rng_mm.number_percent().
    """
    from mud.spec_funs import spec_cast_adept

    rng_mm.seed_mm(12345)
    expected = [24, 97, 90, 83, 45, 44, 43, 87, 2, 89]
    produced = [rng_mm.number_percent() for _ in range(len(expected))]
    assert produced == expected

    # Re-seed and check spec behavior corresponds to the same sequence
    rng_mm.seed_mm(12345)
    outcomes = [spec_cast_adept(object()) for _ in range(len(expected))]
    assert outcomes == [v <= 25 for v in expected]


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
