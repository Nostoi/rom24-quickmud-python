from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.constants import OBJ_VNUM_WHISTLE, CommFlag, PlayerFlag, Position
from mud.models.mob import MobIndex, MobProgram
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.models.room_json import ResetJson
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.templates import MobInstance
from mud.spec_funs import (
    get_spec_fun,
    register_spec_fun,
    run_npc_specs,
    spec_cast_cleric,
    spec_cast_mage,
    spec_fun_registry,
)
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world, world_state


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
    initialize_world("area/area.lst")
    # Use an existing mob prototype and give it a spec name
    proto = mob_registry.get(3000)
    assert proto is not None
    proto.spec_fun = "Spec_Dummy"

    calls: list[object] = []

    def dummy(mob):  # spec fun signature: (mob) -> None
        calls.append(mob)

    prev = dict(spec_fun_registry)
    try:
        register_spec_fun("spec_dummy", dummy)
        # Place mob in a real room
        ch = create_test_character("Tester", 3001)
        mob = spawn_mob(3000)
        assert mob is not None
        ch.room.add_mob(mob)
        # Preconditions
        assert getattr(mob, "prototype", None) is proto
        assert getattr(mob.prototype, "spec_fun", None) == "Spec_Dummy"
        assert any(getattr(e, "prototype", None) is not None for e in ch.room.people)

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
    initialize_world("area/area.lst")
    proto = mob_registry.get(3000)
    assert proto is not None
    proto.spec_fun = "Spec_Log"

    messages: list[str] = []

    def spec_log(mob):
        messages.append(f"tick:{getattr(mob, 'name', '?')}")

    prev = dict(spec_fun_registry)
    try:
        register_spec_fun("Spec_Log", spec_log)
        ch = create_test_character("Tester", 3001)
        mob = spawn_mob(3000)
        ch.room.add_mob(mob)
        assert getattr(mob.prototype, "spec_fun", None) == "Spec_Log"

        run_npc_specs()
        assert any(msg.startswith("tick:") for msg in messages)
    finally:
        spec_fun_registry.clear()
        spec_fun_registry.update(prev)


def test_reset_spawn_triggers_spec_fun() -> None:
    from mud.spawning.reset_handler import apply_resets

    character_registry.clear()
    room_registry.clear()
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()

    area = Area(vnum=4242, name="Spec Reset Test")
    room = Room(vnum=4243, name="Spec Room", area=area)
    area.resets.append(ResetJson(command="M", arg1=7777, arg2=1, arg3=room.vnum, arg4=1))

    area_registry[area.vnum] = area
    room_registry[room.vnum] = room

    program = MobProgram(trig_type=1, trig_phrase="greet", vnum=9001, code="say hi")
    proto = MobIndex(vnum=7777, short_descr="spec sentinel", level=10)
    proto.spec_fun = "Spec_ResetEcho"
    spec_name = proto.spec_fun
    proto.mprog_flags = 0x08
    proto.mprogs = [program]
    proto.area = area
    mob_registry[proto.vnum] = proto

    calls: list[MobInstance] = []

    def reset_echo(mob: MobInstance) -> None:
        calls.append(mob)

    prev = dict(spec_fun_registry)
    try:
        register_spec_fun("Spec_ResetEcho", reset_echo)

        apply_resets(area)

        spawned = next(m for m in room.people if isinstance(m, MobInstance))
        assert spawned.prototype is proto
        assert spawned.spec_fun == spec_name
        assert spawned.mprog_flags == proto.mprog_flags
        assert spawned.mob_programs is not proto.mprogs
        assert spawned.mob_programs == proto.mprogs
        assert spawned.mprog_target is None
        assert spawned.mprog_delay == 0

        run_npc_specs()
        assert calls and calls[0] is spawned

        proto.spec_fun = None
        assert spawned.spec_fun == spec_name
        calls.clear()

        run_npc_specs()
        assert calls and calls[0] is spawned
    finally:
        spec_fun_registry.clear()
        spec_fun_registry.update(prev)


def test_guard_attacks_flagged_criminal() -> None:
    initialize_world("area/area.lst")
    character_registry.clear()

    room = room_registry.get(3001)
    assert room is not None

    bystander = create_test_character("Bystander", room.vnum)
    bystander.messages.clear()
    criminal = create_test_character("Criminal", room.vnum)
    criminal.messages.clear()
    criminal.act |= int(PlayerFlag.KILLER)

    guard_proto = MobIndex(vnum=9000, short_descr="the city guard", level=25, alignment=1000)
    guard_proto.spec_fun = "spec_guard"
    mob_registry[guard_proto.vnum] = guard_proto

    guard = MobInstance.from_prototype(guard_proto)
    guard.spec_fun = "spec_guard"
    guard.messages = []
    room.add_mob(guard)

    try:
        rng_mm.seed_mm(4242)
        run_npc_specs()

        assert any("KILLER" in message for message in criminal.messages)
        assert guard.comm & int(CommFlag.NOSHOUT) == 0
    finally:
        if guard in room.people:
            room.people.remove(guard)
        mob_registry.pop(guard_proto.vnum, None)
        room.remove_character(bystander)
        room.remove_character(criminal)
        character_registry.clear()


def test_patrolman_blows_whistle_when_breaking_fight() -> None:
    character_registry.clear()
    area_registry.clear()
    room_registry.clear()

    area = Area(vnum=6000, name="City Watch")
    room = Room(vnum=6001, name="Main Square", area=area)
    nearby = Room(vnum=6002, name="Side Street", area=area)
    area_registry[area.vnum] = area
    room_registry[room.vnum] = room
    room_registry[nearby.vnum] = nearby

    listener = Character(name="Listener")
    listener.is_npc = False
    nearby.add_character(listener)
    listener.messages.clear()
    character_registry.append(listener)

    fighter_a = Character(name="FighterA")
    fighter_b = Character(name="FighterB")
    for fighter in (fighter_a, fighter_b):
        fighter.is_npc = False
        fighter.position = int(Position.FIGHTING)
        fighter.messages.clear()
        room.add_character(fighter)
        character_registry.append(fighter)
    fighter_a.fighting = fighter_b
    fighter_b.fighting = fighter_a

    patrol_proto = MobIndex(vnum=9001, short_descr="the patrolman", level=20)
    patrol_proto.spec_fun = "spec_patrolman"
    mob_registry[patrol_proto.vnum] = patrol_proto

    patrol = MobInstance.from_prototype(patrol_proto)
    patrol.spec_fun = "spec_patrolman"
    patrol.messages = []
    whistle_proto = ObjIndex(vnum=OBJ_VNUM_WHISTLE, short_descr="a copper whistle")
    patrol.equipment = {"neck_1": Object(instance_id=1, prototype=whistle_proto)}
    room.add_mob(patrol)

    try:
        rng_mm.seed_mm(777)
        run_npc_specs()

        assert any("blow down hard" in message for message in patrol.messages)
        joined_messages = fighter_a.messages + fighter_b.messages
        assert any("WHEEEEE" in message for message in joined_messages)
        assert any("whistling sound" in message for message in listener.messages)
    finally:
        room.people.remove(patrol)
        mob_registry.pop(patrol_proto.vnum, None)
        area_registry.pop(area.vnum, None)
        room_registry.pop(room.vnum, None)
        room_registry.pop(nearby.vnum, None)
        character_registry.clear()


def test_spec_cast_cleric_casts_expected_spells() -> None:
    initialize_world("area/area.lst")
    character_registry.clear()

    room = room_registry.get(3001)
    assert room is not None
    target = create_test_character("Target", room.vnum)
    target.messages.clear()

    cleric_proto = MobIndex(vnum=9100, short_descr="cleric", level=20)
    cleric_proto.spec_fun = "spec_cast_cleric"
    mob_registry[cleric_proto.vnum] = cleric_proto
    cleric = MobInstance.from_prototype(cleric_proto)
    cleric.spec_fun = "spec_cast_cleric"
    cleric.position = int(Position.FIGHTING)
    cleric.fighting = target
    cleric.messages = []
    room.add_mob(cleric)
    target.fighting = cleric

    cleric_spells = [
        "blindness",
        "cause serious",
        "earthquake",
        "cause critical",
        "dispel evil",
        "curse",
        "change sex",
        "flamestrike",
        "harm",
        "plague",
        "dispel magic",
    ]
    registry = world_state.skill_registry
    assert registry is not None
    original_handlers: dict[str, object] = {}

    def _stub(name: str):
        def caster(_caster, _target=None, *_, **__):
            recorded.append(name)
            return True

        return caster

    recorded: list[str] = []
    for spell in cleric_spells:
        key = spell
        original_handlers[key] = registry.handlers.get(key)
        registry.handlers[key] = _stub(key)

    def predict(level: int, seed: int) -> str:
        rng_mm.seed_mm(seed)
        rng_mm.number_bits(2)  # victim selection roll
        table = {
            0: (0, "blindness"),
            1: (3, "cause serious"),
            2: (7, "earthquake"),
            3: (9, "cause critical"),
            4: (10, "dispel evil"),
            5: (12, "curse"),
            6: (12, "change sex"),
            7: (13, "flamestrike"),
            8: (15, "harm"),
            9: (15, "harm"),
            10: (15, "harm"),
            11: (15, "plague"),
        }
        default = (16, "dispel magic")
        while True:
            roll = rng_mm.number_bits(4)
            min_level, spell = table.get(roll, default)
            if level >= min_level:
                return spell

    try:
        for level, seed in ((20, 1337), (3, 4241)):
            cleric.level = level
            recorded.clear()
            target.hit = target.max_hit = 200
            cleric.fighting = target
            target.fighting = cleric
            expected = predict(level, seed)
            rng_mm.seed_mm(seed)
            assert spec_cast_cleric(cleric) is True
            assert recorded
            assert recorded[0].lower() == expected
    finally:
        for spell, handler in original_handlers.items():
            if handler is None:
                registry.handlers.pop(spell, None)
            else:
                registry.handlers[spell] = handler
        mob_registry.pop(cleric_proto.vnum, None)
        room.people.remove(cleric)
        room.remove_character(target)
        character_registry.clear()


def test_spec_cast_mage_uses_rom_spell_table() -> None:
    initialize_world("area/area.lst")
    character_registry.clear()

    room = room_registry.get(3001)
    assert room is not None
    target = create_test_character("MageTarget", room.vnum)
    target.messages.clear()

    mage_proto = MobIndex(vnum=9101, short_descr="mage", level=20)
    mage_proto.spec_fun = "spec_cast_mage"
    mob_registry[mage_proto.vnum] = mage_proto
    mage = MobInstance.from_prototype(mage_proto)
    mage.spec_fun = "spec_cast_mage"
    mage.position = int(Position.FIGHTING)
    mage.fighting = target
    mage.messages = []
    room.add_mob(mage)
    target.fighting = mage

    registry = world_state.skill_registry
    assert registry is not None
    mage_spells = [
        "blindness",
        "chill touch",
        "weaken",
        "teleport",
        "colour spray",
        "change sex",
        "energy drain",
        "fireball",
        "plague",
        "acid blast",
    ]
    original_handlers: dict[str, object] = {}
    recorded: list[str] = []

    def _mage_stub(name: str):
        def caster(_caster, _target=None, *_, **__):
            recorded.append(name)
            return True

        return caster

    for spell in mage_spells:
        key = spell
        original_handlers[key] = registry.handlers.get(key)
        registry.handlers[key] = _mage_stub(key)

    def predict(level: int, seed: int) -> str:
        rng_mm.seed_mm(seed)
        rng_mm.number_bits(2)
        table = {
            0: (0, "blindness"),
            1: (3, "chill touch"),
            2: (7, "weaken"),
            3: (8, "teleport"),
            4: (11, "colour spray"),
            5: (12, "change sex"),
            6: (13, "energy drain"),
            7: (15, "fireball"),
            8: (15, "fireball"),
            9: (15, "fireball"),
            10: (20, "plague"),
        }
        default = (20, "acid blast")
        while True:
            roll = rng_mm.number_bits(4)
            min_level, spell = table.get(roll, default)
            if level >= min_level:
                return spell

    try:
        for level, seed in ((20, 99), (8, 2024)):
            mage.level = level
            recorded.clear()
            target.hit = target.max_hit = 200
            mage.fighting = target
            target.fighting = mage
            expected = predict(level, seed)
            rng_mm.seed_mm(seed)
            assert spec_cast_mage(mage) is True
            assert recorded
            assert recorded[0].lower() == expected
    finally:
        for spell, handler in original_handlers.items():
            if handler is None:
                registry.handlers.pop(spell, None)
            else:
                registry.handlers[spell] = handler
        mob_registry.pop(mage_proto.vnum, None)
        room.people.remove(mage)
        room.remove_character(target)
        character_registry.clear()
