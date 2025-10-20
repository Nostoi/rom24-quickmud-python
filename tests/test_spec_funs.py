from typing import Any

from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.constants import (
    GROUP_VNUM_OGRES,
    GROUP_VNUM_TROLLS,
    MOB_VNUM_PATROLMAN,
    OBJ_VNUM_WHISTLE,
    AffectFlag,
    CommFlag,
    PlayerFlag,
    Position,
    Sex,
)
from mud.models.mob import MobIndex, MobProgram
from mud.models.obj import ObjIndex
from types import SimpleNamespace

import mud.spec_funs as spec_module
from mud.models.constants import Direction, EX_CLOSED, ItemType, Position, WearFlag
from mud.models.object import Object
from mud.models.room import Exit, Room
from mud.models.room_json import ResetJson
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.templates import MobInstance
from mud.spec_funs import (
    get_spec_fun,
    register_spec_fun,
    run_npc_specs,
    spec_cast_cleric,
    spec_cast_judge,
    spec_cast_mage,
    spec_cast_undead,
    spec_fun_registry,
    spec_fido,
    spec_janitor,
    spec_poison,
    spec_mayor,
    spec_thief,
    _reset_spec_mayor_state,
)
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world, world_state
from mud.time import time_info


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


def test_spec_cast_adept_casts_support_spells(monkeypatch) -> None:
    room = Room(vnum=5000, name="Adept Hall")

    player = Character(name="Newbie", level=5)
    player.is_npc = False
    player.messages = []
    room.add_character(player)

    proto = MobIndex(vnum=5001, short_descr="a helpful adept", level=10)
    proto.spec_fun = "spec_cast_adept"
    mob_registry[proto.vnum] = proto

    adept = MobInstance.from_prototype(proto)
    adept.messages = []
    adept.position = int(Position.STANDING)
    room.add_mob(adept)

    cast_calls: list[tuple[Any, Any, str]] = []

    monkeypatch.setattr(spec_module, "_cast_spell", lambda caster, target, spell: cast_calls.append((caster, target, spell)) or True)

    bit_values = iter([0, 0])

    def fake_bits(width: int) -> int:
        try:
            return next(bit_values)
        except StopIteration:
            return 0

    monkeypatch.setattr(rng_mm, "number_bits", fake_bits)

    try:
        result = spec_module.spec_cast_adept(adept)
        assert result is True
        assert cast_calls == [(adept, player, "armor")]
        assert "a helpful adept utters the word 'abrazak'." in player.messages
    finally:
        if adept in room.people:
            room.people.remove(adept)
        room.remove_character(player)
        mob_registry.pop(proto.vnum, None)


def test_spec_cast_adept_skips_high_level_players(monkeypatch) -> None:
    room = Room(vnum=5002, name="Quiet Chapel")

    veteran = Character(name="Veteran", level=15)
    veteran.is_npc = False
    veteran.messages = []
    room.add_character(veteran)

    proto = MobIndex(vnum=5003, short_descr="a kindly adept", level=10, spec_fun="spec_cast_adept")
    mob_registry[proto.vnum] = proto

    adept = MobInstance.from_prototype(proto)
    adept.messages = []
    adept.position = int(Position.STANDING)
    room.add_mob(adept)

    cast_calls: list[tuple[Any, Any, str]] = []
    monkeypatch.setattr(spec_module, "_cast_spell", lambda caster, target, spell: cast_calls.append((caster, target, spell)))
    monkeypatch.setattr(rng_mm, "number_bits", lambda width: 0)

    try:
        result = spec_module.spec_cast_adept(adept)

        assert result is False
        assert cast_calls == []
    finally:
        if adept in room.people:
            room.people.remove(adept)
        room.remove_character(veteran)
        mob_registry.pop(proto.vnum, None)


def test_spec_cast_adept_requires_visibility(monkeypatch) -> None:
    room = Room(vnum=5004, name="Dim Chapel")

    hidden = Character(name="Sneaky", level=7)
    hidden.is_npc = False
    hidden.messages = []
    hidden.affected_by = int(AffectFlag.INVISIBLE)
    room.add_character(hidden)

    proto = MobIndex(vnum=5005, short_descr="a patient adept", level=10, spec_fun="spec_cast_adept")
    mob_registry[proto.vnum] = proto

    adept = MobInstance.from_prototype(proto)
    adept.messages = []
    adept.position = int(Position.STANDING)
    room.add_mob(adept)

    cast_calls: list[tuple[Any, Any, str]] = []
    monkeypatch.setattr(spec_module, "_cast_spell", lambda caster, target, spell: cast_calls.append((caster, target, spell)))

    try:
        result = spec_module.spec_cast_adept(adept)

        assert result is False
        assert cast_calls == []
    finally:
        if adept in room.people:
            room.people.remove(adept)
        room.remove_character(hidden)
        mob_registry.pop(proto.vnum, None)


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


def test_spec_janitor_collects_trash() -> None:
    room = Room(vnum=4000, name="Trash Heap")
    janitor = SimpleNamespace(
        name="Janitor",
        room=room,
        position=int(Position.STANDING),
        inventory=[],
        messages=[],
        is_npc=True,
    )
    observer = SimpleNamespace(name="Watcher", room=room, messages=[], is_npc=False)
    room.people = [janitor, observer]

    trash = SimpleNamespace(
        wear_flags=int(WearFlag.TAKE),
        cost=5,
        item_type=int(ItemType.TRASH),
        in_room=room,
        carried_by=None,
    )
    room.contents = [trash]

    assert spec_janitor(janitor) is True
    assert trash not in room.contents
    assert trash in janitor.inventory
    assert any("picks up some trash" in message for message in observer.messages)


def test_spec_fido_eats_npc_corpses() -> None:
    room = Room(vnum=4001, name="Graveyard")
    fido = SimpleNamespace(
        name="Fido",
        room=room,
        position=int(Position.STANDING),
        messages=[],
        is_npc=True,
    )
    observer = SimpleNamespace(name="Watcher", room=room, messages=[], is_npc=False)
    room.people = [fido, observer]

    loot = SimpleNamespace(
        name="tarnished ring",
        in_obj=None,
        in_room=None,
        carried_by=None,
        location=None,
    )
    npc_corpse = SimpleNamespace(
        item_type=int(ItemType.CORPSE_NPC),
        contains=[loot],
        contained_items=[loot],
        in_room=room,
        carried_by=None,
        location=room,
    )
    loot.in_obj = npc_corpse
    pc_corpse = SimpleNamespace(
        item_type=int(ItemType.CORPSE_PC),
        contains=[],
        contained_items=[],
        in_room=room,
        carried_by=None,
        location=room,
    )
    room.contents = [npc_corpse, pc_corpse]

    assert spec_fido(fido) is True
    assert npc_corpse not in room.contents
    assert pc_corpse in room.contents
    assert loot in room.contents
    assert loot.in_obj is None
    assert getattr(loot, "in_room", None) is room
    assert any("savagely devours a corpse" in message for message in observer.messages)

    observer.messages.clear()
    assert spec_fido(fido) is False
    assert pc_corpse in room.contents


def test_spec_poison_bites_current_target(monkeypatch) -> None:
    room = Room(vnum=4002, name="Serpent Pit")
    snake = SimpleNamespace(
        name="Cobra",
        room=room,
        position=int(Position.FIGHTING),
        fighting=None,
        level=20,
        messages=[],
    )
    victim = SimpleNamespace(
        name="Explorer",
        room=room,
        messages=[],
    )
    observer = SimpleNamespace(name="Watcher", room=room, messages=[], is_npc=False)
    room.people = [snake, victim, observer]
    snake.fighting = victim
    victim.fighting = snake

    rolls = iter([10, 99])
    monkeypatch.setattr(rng_mm, "number_percent", lambda: next(rolls))

    calls: list[tuple[object, object, str]] = []

    def fake_cast(caster, target, spell_name):
        calls.append((caster, target, spell_name))
        return True

    monkeypatch.setattr("mud.spec_funs._cast_spell", fake_cast)

    observer.messages.clear()
    victim.messages.clear()
    snake.messages.clear()

    assert spec_poison(snake) is True
    assert calls == [(snake, victim, "poison")]
    assert any("You bite" in msg for msg in snake.messages)
    assert any("bites you" in msg for msg in victim.messages)
    assert any("bites" in msg for msg in observer.messages)

    snake_count = len(snake.messages)
    victim_count = len(victim.messages)
    observer_count = len(observer.messages)

    assert spec_poison(snake) is False
    assert len(calls) == 1
    assert len(snake.messages) == snake_count
    assert len(victim.messages) == victim_count
    assert len(observer.messages) == observer_count


def _make_dragon_setup() -> tuple[Room, SimpleNamespace, SimpleNamespace]:
    room = Room(vnum=4010, name="Dragon Lair")
    dragon = SimpleNamespace(
        name="Red Dragon",
        room=room,
        position=int(Position.FIGHTING),
        fighting=None,
        level=45,
        messages=[],
    )
    knight = SimpleNamespace(
        name="Knight",
        room=room,
        position=int(Position.FIGHTING),
        fighting=dragon,
        messages=[],
    )
    dragon.fighting = knight
    room.people = [dragon, knight]
    return room, dragon, knight


def test_spec_breath_elemental_spells_target_current_enemy(monkeypatch) -> None:
    _, dragon, knight = _make_dragon_setup()

    calls: list[tuple[object, object | None, str]] = []

    def fake_cast(caster, target, spell_name):
        calls.append((caster, target, spell_name))
        return True

    monkeypatch.setattr(spec_module, "_cast_spell", fake_cast)
    monkeypatch.setattr(spec_module.rng_mm, "number_bits", lambda bits: 0)

    cases = [
        (spec_module.spec_breath_fire, "fire breath"),
        (spec_module.spec_breath_acid, "acid breath"),
        (spec_module.spec_breath_frost, "frost breath"),
        (spec_module.spec_breath_lightning, "lightning breath"),
    ]

    for func, spell in cases:
        calls.clear()
        assert func(dragon) is True
        assert calls == [(dragon, knight, spell)]


def test_spec_breath_gas_hits_room(monkeypatch) -> None:
    _, dragon, _ = _make_dragon_setup()

    calls: list[tuple[object, object | None, str]] = []

    def fake_cast(caster, target, spell_name):
        calls.append((caster, target, spell_name))
        return True

    monkeypatch.setattr(spec_module, "_cast_spell", fake_cast)

    assert spec_module.spec_breath_gas(dragon) is True
    assert calls == [(dragon, None, "gas breath")]


def test_spec_breath_any_dispatches_to_element(monkeypatch) -> None:
    _, dragon, _ = _make_dragon_setup()

    outcomes: list[str] = []

    def make_stub(name: str):
        def _stub(mob):
            assert mob is dragon
            outcomes.append(name)
            return True

        return _stub

    monkeypatch.setattr(spec_module, "spec_breath_fire", make_stub("fire"))
    monkeypatch.setattr(spec_module, "spec_breath_lightning", make_stub("lightning"))
    monkeypatch.setattr(spec_module, "spec_breath_gas", make_stub("gas"))
    monkeypatch.setattr(spec_module, "spec_breath_acid", make_stub("acid"))
    monkeypatch.setattr(spec_module, "spec_breath_frost", make_stub("frost"))

    mapping = {
        0: "fire",
        1: "lightning",
        2: "lightning",
        3: "gas",
        4: "acid",
        5: "frost",
        6: "frost",
        7: "frost",
    }

    for roll, expected in mapping.items():
        outcomes.clear()
        monkeypatch.setattr(spec_module.rng_mm, "number_bits", lambda bits, value=roll: value)
        assert spec_module.spec_breath_any(dragon) is True
        assert outcomes == [expected]


def test_spec_breath_requires_fighting_state() -> None:
    room = Room(vnum=4011, name="Lair Antechamber")
    dragon = SimpleNamespace(
        name="Drowsy Dragon",
        room=room,
        position=int(Position.SLEEPING),
        fighting=None,
    )
    room.people = [dragon]

    assert spec_module.spec_breath_fire(dragon) is False
    assert spec_module.spec_breath_any(dragon) is False


def test_spec_mayor_opens_and_closes_gate(monkeypatch) -> None:
    prev_hour = time_info.hour
    monkeypatch.setattr(spec_module, "_MAYOR_OPEN_PATH", "W1Oe3S.")
    monkeypatch.setattr(spec_module, "_MAYOR_CLOSE_PATH", "W1CE3S.")
    _reset_spec_mayor_state()

    office = Room(vnum=5000, name="Mayor's Office")
    walkway = Room(vnum=5001, name="Gate Walk")
    outside = Room(vnum=5002, name="Outer Road")

    office.people = []
    walkway.people = []
    outside.people = []

    office_to_walk = Exit(to_room=walkway)
    walk_to_office = Exit(to_room=office)
    gate_exit = Exit(to_room=outside, keyword="gate", exit_info=EX_CLOSED)
    reverse_gate = Exit(to_room=walkway, keyword="gate", exit_info=EX_CLOSED)

    office.exits[Direction.EAST.value] = office_to_walk
    walkway.exits[Direction.WEST.value] = walk_to_office
    walkway.exits[Direction.EAST.value] = gate_exit
    outside.exits[Direction.WEST.value] = reverse_gate

    clerk = SimpleNamespace(name="Clerk", room=office, messages=[], is_npc=False)
    guard = SimpleNamespace(name="Guard", room=walkway, messages=[], is_npc=False)
    office.people.append(clerk)
    walkway.people.append(guard)

    mayor = SimpleNamespace(
        name="Mayor",
        room=office,
        position=int(Position.SLEEPING),
        messages=[],
        fighting=None,
        is_npc=True,
    )
    office.people.append(mayor)

    time_info.hour = 6
    while True:
        spec_mayor(mayor)
        if not spec_module._mayor_moving and spec_module._mayor_path is None:
            break

    assert mayor.room is office
    assert mayor.position == int(Position.SLEEPING)
    assert gate_exit.exit_info & EX_CLOSED == 0
    assert reverse_gate.exit_info & EX_CLOSED == 0
    assert any("declare the city of Midgaard open" in msg for msg in guard.messages)

    guard.messages.clear()
    clerk.messages.clear()
    _reset_spec_mayor_state()
    mayor.room = office
    if mayor not in office.people:
        office.people.append(mayor)
    if mayor in walkway.people:
        walkway.people.remove(mayor)
    mayor.position = int(Position.SLEEPING)

    time_info.hour = 20
    while True:
        spec_mayor(mayor)
        if not spec_module._mayor_moving and spec_module._mayor_path is None:
            break

    assert mayor.room is office
    assert mayor.position == int(Position.SLEEPING)
    assert gate_exit.exit_info & EX_CLOSED
    assert reverse_gate.exit_info & EX_CLOSED
    assert any("declare the city of Midgaard closed" in msg for msg in guard.messages)

    _reset_spec_mayor_state()
    time_info.hour = prev_hour


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


def test_spec_executioner_yells_and_attacks_criminal(monkeypatch) -> None:
    initialize_world("area/area.lst")
    character_registry.clear()

    room = room_registry.get(3001)
    assert room is not None

    witness = create_test_character("Witness", room.vnum)
    witness.messages.clear()
    outlaw = create_test_character("Outlaw", room.vnum)
    outlaw.messages.clear()
    outlaw.act |= int(PlayerFlag.THIEF)

    proto = MobIndex(vnum=9010, short_descr="the executioner", level=50, spec_fun="spec_executioner")
    mob_registry[proto.vnum] = proto

    executioner = MobInstance.from_prototype(proto)
    executioner.spec_fun = "spec_executioner"
    executioner.messages = []
    executioner.comm = int(CommFlag.NOSHOUT)
    room.add_mob(executioner)

    attacks: list[tuple[Any, Any]] = []
    monkeypatch.setattr(spec_module, "_attack", lambda mob, victim: attacks.append((mob, victim)))

    try:
        result = spec_module.spec_executioner(executioner)

        assert result is True
        assert attacks == [(executioner, outlaw)]
        assert executioner.comm & int(CommFlag.NOSHOUT) == 0
        assert any("You yell" in msg and "THIEF" in msg for msg in executioner.messages)
        assert any("THIEF" in msg for msg in outlaw.messages)
        assert any("THIEF" in msg for msg in witness.messages)
    finally:
        if executioner in room.people:
            room.people.remove(executioner)
        mob_registry.pop(proto.vnum, None)
        room.remove_character(witness)
        room.remove_character(outlaw)
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


def test_spec_cast_undead_uses_rom_spell_table() -> None:
    initialize_world("area/area.lst")
    character_registry.clear()

    room = room_registry.get(3001)
    assert room is not None
    target = create_test_character("UndeadTarget", room.vnum)
    target.messages.clear()

    undead_proto = MobIndex(vnum=9102, short_descr="undead", level=25)
    undead_proto.spec_fun = "spec_cast_undead"
    mob_registry[undead_proto.vnum] = undead_proto
    undead = MobInstance.from_prototype(undead_proto)
    undead.spec_fun = "spec_cast_undead"
    undead.position = int(Position.FIGHTING)
    undead.fighting = target
    undead.messages = []
    room.add_mob(undead)
    target.fighting = undead

    registry = world_state.skill_registry
    assert registry is not None

    undead_spells = [
        "curse",
        "weaken",
        "chill touch",
        "blindness",
        "poison",
        "energy drain",
        "harm",
        "teleport",
        "plague",
    ]
    original_handlers: dict[str, object] = {}
    recorded: list[str] = []

    def _undead_stub(name: str):
        def caster(_caster, _target=None, *_, **__):
            recorded.append(name)
            return True

        return caster

    for spell in undead_spells:
        key = spell
        original_handlers[key] = registry.handlers.get(key)
        registry.handlers[key] = _undead_stub(key)

    def predict(level: int, seed: int) -> str:
        rng_mm.seed_mm(seed)
        rng_mm.number_bits(2)
        table = {
            0: (0, "curse"),
            1: (3, "weaken"),
            2: (6, "chill touch"),
            3: (9, "blindness"),
            4: (12, "poison"),
            5: (15, "energy drain"),
            6: (18, "harm"),
            7: (21, "teleport"),
            8: (20, "plague"),
        }
        default = (18, "harm")
        while True:
            roll = rng_mm.number_bits(4)
            min_level, spell = table.get(roll, default)
            if level >= min_level:
                return spell

    try:
        for level, seed in ((25, 1777), (12, 3001)):
            undead.level = level
            recorded.clear()
            target.hit = target.max_hit = 200
            undead.fighting = target
            target.fighting = undead
            expected = predict(level, seed)
            rng_mm.seed_mm(seed)
            assert spec_cast_undead(undead) is True
            assert recorded
            assert recorded[0].lower() == expected
    finally:
        for spell, handler in original_handlers.items():
            if handler is None:
                registry.handlers.pop(spell, None)
            else:
                registry.handlers[spell] = handler
        mob_registry.pop(undead_proto.vnum, None)
        room.people.remove(undead)
        room.remove_character(target)
        character_registry.clear()


def test_spec_cast_judge_casts_high_explosive() -> None:
    initialize_world("area/area.lst")
    character_registry.clear()

    room = room_registry.get(3001)
    assert room is not None
    target = create_test_character("JudgeTarget", room.vnum)
    target.messages.clear()

    judge_proto = MobIndex(vnum=9103, short_descr="judge", level=25)
    judge_proto.spec_fun = "spec_cast_judge"
    mob_registry[judge_proto.vnum] = judge_proto
    judge = MobInstance.from_prototype(judge_proto)
    judge.spec_fun = "spec_cast_judge"
    judge.position = int(Position.FIGHTING)
    judge.fighting = target
    judge.messages = []
    room.add_mob(judge)
    target.fighting = judge

    registry = world_state.skill_registry
    assert registry is not None
    original = registry.handlers.get("high explosive")
    recorded: list[str] = []

    def _judge_stub(_caster, _target=None, *_, **__):
        recorded.append("high explosive")
        return True

    registry.handlers["high explosive"] = _judge_stub

    try:
        rng_mm.seed_mm(4242)
        assert spec_cast_judge(judge) is True
        assert recorded == ["high explosive"]
    finally:
        if original is None:
            registry.handlers.pop("high explosive", None)
        else:
            registry.handlers["high explosive"] = original
        mob_registry.pop(judge_proto.vnum, None)
        room.people.remove(judge)
        room.remove_character(target)
        character_registry.clear()


def test_spec_thief_steals_from_sleeping_player(monkeypatch) -> None:
    character_registry.clear()

    room = Room(vnum=7200, name="Thieves' Den")
    sleeper = Character(name="Sleeper", level=25)
    sleeper.is_npc = False
    sleeper.position = int(Position.SLEEPING)
    sleeper.gold = 1000
    sleeper.silver = 2000
    sleeper.messages = []
    room.add_character(sleeper)

    thief_proto = MobIndex(vnum=7201, short_descr="a nimble cutpurse", level=12)
    thief_proto.spec_fun = "spec_thief"
    mob_registry[thief_proto.vnum] = thief_proto

    thief = MobInstance.from_prototype(thief_proto)
    thief.spec_fun = "spec_thief"
    thief.position = int(Position.STANDING)
    thief.gold = 10
    thief.silver = 5
    thief.messages = []
    room.add_mob(thief)

    rolls = iter([15, 3])

    monkeypatch.setattr(rng_mm, "number_bits", lambda _: 0)

    def fake_number_range(start: int, end: int) -> int:
        try:
            return next(rolls)
        except StopIteration:
            return end

    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)

    try:
        result = spec_thief(thief)
        assert result is True
        assert thief.gold == 10 + 60
        assert thief.silver == 5 + 60
        assert sleeper.gold == 1000 - 60
        assert sleeper.silver == 2000 - 60
        assert sleeper.messages == []
    finally:
        room.people.remove(thief)
        room.remove_character(sleeper)
        mob_registry.pop(thief_proto.vnum, None)
        character_registry.clear()


def test_spec_thief_fails_against_awake_player(monkeypatch) -> None:
    character_registry.clear()

    room = Room(vnum=7300, name="Market Square")
    victim = Character(name="Watcher", level=20)
    victim.is_npc = False
    victim.position = int(Position.STANDING)
    victim.gold = 500
    victim.silver = 800
    victim.messages = []
    victim.sex = int(Sex.MALE)
    room.add_character(victim)

    observer = Character(name="Bystander", level=10)
    observer.is_npc = False
    observer.position = int(Position.STANDING)
    observer.messages = []
    room.add_character(observer)

    thief_proto = MobIndex(vnum=7301, short_descr="a lurking thief", level=14)
    thief_proto.spec_fun = "spec_thief"
    mob_registry[thief_proto.vnum] = thief_proto

    thief = MobInstance.from_prototype(thief_proto)
    thief.spec_fun = "spec_thief"
    thief.position = int(Position.STANDING)
    thief.gold = 40
    thief.silver = 75
    thief.messages = []
    room.add_mob(thief)

    monkeypatch.setattr(rng_mm, "number_bits", lambda _: 0)
    rolls = iter([0])

    def fake_number_range(start: int, end: int) -> int:
        try:
            return next(rolls)
        except StopIteration:
            return end

    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)

    try:
        result = spec_thief(thief)
        assert result is True
        assert thief.gold == 40
        assert thief.silver == 75
        assert victim.gold == 500
        assert victim.silver == 800
        assert victim.messages == ["You discover a lurking thief's hands in your wallet!"]
        assert observer.messages == [
            "Watcher discovers a lurking thief's hands in his wallet!"
        ]
    finally:
        room.people.remove(thief)
        room.remove_character(victim)
        room.remove_character(observer)
        mob_registry.pop(thief_proto.vnum, None)
        character_registry.clear()


def test_spec_nasty_ambushes_stronger_players(monkeypatch) -> None:
    character_registry.clear()

    room = Room(vnum=7400, name="Shadowy Alley")

    bystander = Character(name="Bystander", level=5)
    bystander.is_npc = False
    bystander.messages = []
    room.add_character(bystander)

    target = Character(name="Champion", level=16)
    target.is_npc = False
    target.messages = []
    room.add_character(target)

    proto = MobIndex(vnum=7401, short_descr="a nasty assassin", level=8)
    proto.spec_fun = "spec_nasty"
    mob_registry[proto.vnum] = proto

    assassin = MobInstance.from_prototype(proto)
    assassin.spec_fun = "spec_nasty"
    assassin.position = int(Position.STANDING)
    assassin.messages = []
    room.add_mob(assassin)

    calls: list[tuple[object, object]] = []
    def fake_issue(mob, command, argument):
        calls.append((command, argument))
        if command == "do_kill":
            mob.fighting = target
            target.fighting = mob
        return ""

    monkeypatch.setattr(spec_module, "_issue_command", fake_issue)

    try:
        result = spec_module.spec_nasty(assassin)
        assert result is True
        assert calls == [("do_backstab", "Champion"), ("do_kill", "Champion")]
    finally:
        room.people.remove(assassin)
        room.remove_character(target)
        room.remove_character(bystander)
        mob_registry.pop(proto.vnum, None)
        character_registry.clear()


def test_spec_nasty_steals_gold_and_alerts_room(monkeypatch) -> None:
    character_registry.clear()

    room = Room(vnum=7500, name="Dark Courtyard")

    victim = Character(name="Hero", level=20)
    victim.is_npc = False
    victim.gold = 1000
    victim.messages = []
    room.add_character(victim)

    observer = Character(name="Watcher", level=18)
    observer.is_npc = False
    observer.messages = []
    room.add_character(observer)

    proto = MobIndex(vnum=7501, short_descr="a nasty assassin", level=15)
    proto.spec_fun = "spec_nasty"
    mob_registry[proto.vnum] = proto

    assassin = MobInstance.from_prototype(proto)
    assassin.spec_fun = "spec_nasty"
    assassin.position = int(Position.FIGHTING)
    assassin.gold = 50
    assassin.messages = []
    assassin.fighting = victim
    room.add_mob(assassin)

    victim.fighting = assassin

    monkeypatch.setattr(rng_mm, "number_bits", lambda _: 0)

    try:
        result = spec_module.spec_nasty(assassin)
        assert result is True
        assert victim.gold == 900
        assert assassin.gold == 150
        assert victim.messages == [
            "a nasty assassin rips apart your coin purse, spilling your gold!",
        ]
        assert assassin.messages == [
            "You slash apart Hero's coin purse and gather his gold.",
        ]
        assert observer.messages == ["Hero's coin purse is ripped apart!"]
    finally:
        room.people.remove(assassin)
        room.remove_character(victim)
        room.remove_character(observer)
        mob_registry.pop(proto.vnum, None)
        character_registry.clear()


def test_spec_nasty_flees_when_cornered(monkeypatch) -> None:
    character_registry.clear()

    room = Room(vnum=7600, name="Grimy Street")

    victim = Character(name="Guardian", level=18)
    victim.is_npc = False
    victim.messages = []
    room.add_character(victim)

    proto = MobIndex(vnum=7601, short_descr="a nasty assassin", level=14)
    proto.spec_fun = "spec_nasty"
    mob_registry[proto.vnum] = proto

    assassin = MobInstance.from_prototype(proto)
    assassin.spec_fun = "spec_nasty"
    assassin.position = int(Position.FIGHTING)
    assassin.messages = []
    assassin.fighting = victim
    assassin.hit = 100
    assassin.max_hit = 100
    room.add_mob(assassin)

    victim.fighting = assassin
    victim.hit = 120
    victim.max_hit = 120

    character_registry.append(victim)
    character_registry.append(assassin)

    safe_room = Room(vnum=7601, name="Escape Tunnel")
    room.exits[int(Direction.EAST)] = Exit(to_room=safe_room)

    def fake_bits(width: int) -> int:
        return 1 if width == 2 else 1

    monkeypatch.setattr(rng_mm, "number_bits", fake_bits)

    try:
        result = spec_module.spec_nasty(assassin)
        assert result is True
        assert assassin.fighting is None
        assert victim.fighting is None
        assert int(assassin.position) == int(Position.STANDING)
        assert assassin.room is safe_room
        assert victim.room is room
        assert "a nasty assassin has fled!" in victim.messages
    finally:
        if assassin in room.people:
            room.people.remove(assassin)
        if assassin in safe_room.people:
            safe_room.people.remove(assassin)
        room.remove_character(victim)
        mob_registry.pop(proto.vnum, None)
        character_registry.clear()


def test_spec_troll_member_attacks_ogres(monkeypatch) -> None:
    character_registry.clear()

    room = Room(vnum=7700, name="Clan Square")

    ogre_proto = MobIndex(vnum=7701, short_descr="a hulking ogre", level=12)
    ogre_proto.group = GROUP_VNUM_OGRES
    mob_registry[ogre_proto.vnum] = ogre_proto
    ogre = MobInstance.from_prototype(ogre_proto)
    ogre.messages = []
    room.add_mob(ogre)

    observer = Character(name="Onlooker", level=20)
    observer.is_npc = False
    observer.messages = []
    room.add_character(observer)

    troll_proto = MobIndex(vnum=7702, short_descr="a nasty troll", level=14)
    troll_proto.spec_fun = "spec_troll_member"
    mob_registry[troll_proto.vnum] = troll_proto
    troll = MobInstance.from_prototype(troll_proto)
    troll.spec_fun = "spec_troll_member"
    troll.position = int(Position.STANDING)
    troll.messages = []
    room.add_mob(troll)

    calls: list[tuple[object, object]] = []
    monkeypatch.setattr(spec_module, "_attack", lambda mob, vic: calls.append((mob, vic)))

    rolls = iter([0, 2])

    def fake_number_range(start: int, end: int) -> int:
        try:
            return next(rolls)
        except StopIteration:
            return start

    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)

    try:
        result = spec_module.spec_troll_member(troll)
        assert result is True
        assert calls == [(troll, ogre)]
        expected = "a nasty troll says 'What's slimy Ogre trash like you doing around here?'"
        assert ogre.messages == [expected]
        assert observer.messages == [expected]
    finally:
        room.people.remove(troll)
        room.people.remove(ogre)
        room.remove_character(observer)
        mob_registry.pop(troll_proto.vnum, None)
        mob_registry.pop(ogre_proto.vnum, None)
        character_registry.clear()


def test_spec_ogre_member_attacks_trolls(monkeypatch) -> None:
    character_registry.clear()

    room = Room(vnum=7800, name="Rival Alley")

    troll_proto = MobIndex(vnum=7801, short_descr="a fierce troll", level=13)
    troll_proto.group = GROUP_VNUM_TROLLS
    mob_registry[troll_proto.vnum] = troll_proto
    troll = MobInstance.from_prototype(troll_proto)
    troll.messages = []
    room.add_mob(troll)

    ogre_proto = MobIndex(vnum=7802, short_descr="a snarling ogre", level=15)
    ogre_proto.spec_fun = "spec_ogre_member"
    mob_registry[ogre_proto.vnum] = ogre_proto
    ogre = MobInstance.from_prototype(ogre_proto)
    ogre.spec_fun = "spec_ogre_member"
    ogre.position = int(Position.STANDING)
    ogre.messages = []
    room.add_mob(ogre)

    observer = Character(name="Citizen", level=18)
    observer.is_npc = False
    observer.messages = []
    room.add_character(observer)

    calls: list[tuple[object, object]] = []
    monkeypatch.setattr(spec_module, "_attack", lambda mob, vic: calls.append((mob, vic)))

    rolls = iter([0, 3])

    def fake_number_range(start: int, end: int) -> int:
        try:
            return next(rolls)
        except StopIteration:
            return start

    monkeypatch.setattr(rng_mm, "number_range", fake_number_range)

    try:
        result = spec_module.spec_ogre_member(ogre)
        assert result is True
        assert calls == [(ogre, troll)]
        expected = "a snarling ogre cracks his knuckles and says 'Do ya feel lucky?'"
        assert troll.messages == [expected]
        assert observer.messages == [expected]
    finally:
        room.people.remove(ogre)
        room.people.remove(troll)
        room.remove_character(observer)
        mob_registry.pop(ogre_proto.vnum, None)
        mob_registry.pop(troll_proto.vnum, None)
        character_registry.clear()


def test_spec_troll_member_backs_off_when_patrol_present(monkeypatch) -> None:
    character_registry.clear()

    room = Room(vnum=7900, name="Guarded Street")

    patrol_proto = MobIndex(vnum=MOB_VNUM_PATROLMAN, short_descr="a city patrol", level=20)
    mob_registry[patrol_proto.vnum] = patrol_proto
    patrol = MobInstance.from_prototype(patrol_proto)
    room.add_mob(patrol)

    troll_proto = MobIndex(vnum=7901, short_descr="a nasty troll", level=14)
    troll_proto.spec_fun = "spec_troll_member"
    mob_registry[troll_proto.vnum] = troll_proto
    troll = MobInstance.from_prototype(troll_proto)
    troll.spec_fun = "spec_troll_member"
    troll.position = int(Position.STANDING)
    troll.messages = []
    room.add_mob(troll)

    calls: list[tuple[object, object]] = []
    monkeypatch.setattr(spec_module, "_attack", lambda mob, vic: calls.append((mob, vic)))

    try:
        result = spec_module.spec_troll_member(troll)
        assert result is False
        assert calls == []
    finally:
        room.people.remove(troll)
        room.people.remove(patrol)
        mob_registry.pop(troll_proto.vnum, None)
        mob_registry.pop(patrol_proto.vnum, None)
        character_registry.clear()
