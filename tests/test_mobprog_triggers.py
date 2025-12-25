from __future__ import annotations

from mud import mobprog
from mud.combat import attack_round, multi_hit
from mud.commands.combat import do_surrender
from mud.commands.communication import do_say, do_tell
from mud.game_loop import game_tick
from mud.models.character import Character, character_registry
from mud.models.constants import Direction, ItemType, OffFlag, Position
from mud.models.mob import MobProgram
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Exit, Room
from mud.world.movement import move_character


def _setup_room() -> tuple[Room, Character, Character]:
    room = Room(vnum=5000, name="Test Chamber")
    mob = Character(name="Guide", is_npc=True)
    player = Character(name="Hero", is_npc=False)
    mob.position = Position.STANDING
    mob.default_pos = Position.STANDING
    room.add_character(mob)
    room.add_character(player)
    return room, mob, player


def test_program_flow_executes_commands_and_mob_directives(monkeypatch) -> None:
    _, mob, player = _setup_room()

    program_main = MobProgram(
        trig_type=int(mobprog.Trigger.SPEECH),
        trig_phrase="hello",
        vnum=1000,
        code="""
* comment line should be ignored
if ispc $n
    say Greetings $n
    mob echo $n is welcomed.
    mob call 2001 $n
else
    say I only talk to mortals.
endif
""",
    )
    program_called = MobProgram(
        trig_type=0,
        vnum=2001,
        code="say Called for $n",
    )
    program_recursive = MobProgram(
        trig_type=0,
        vnum=3000,
        code="""
mob call 3000
say Depth reached
""",
    )

    mob.mob_programs = [program_main, program_called, program_recursive]

    executed: list[str] = []

    def fake_process_command(char: Character, command_line: str) -> str:
        executed.append(command_line)
        return ""

    monkeypatch.setattr("mud.commands.dispatcher.process_command", fake_process_command)

    results = mobprog.run_prog(
        mob,
        mobprog.Trigger.SPEECH,
        actor=player,
        phrase="hello there",
    )

    assert executed == ["say Greetings Hero", "say Called for Hero"]
    assert [(res.command, res.argument, res.mob_command) for res in results] == [
        ("say", "Greetings Hero", False),
        ("mob echo", "Hero is welcomed.", True),
        ("mob call", "2001 Hero", True),
        ("say", "Called for Hero", False),
    ]
    assert player.messages[-1] == "Hero is welcomed."

    mobprog._register_program(program_recursive)  # register for call_prog recursion
    loop_results = mobprog.call_prog(3000, mob)
    depth_messages = [res for res in loop_results if res.command == "say" and res.argument == "Depth reached"]
    assert len(depth_messages) == mobprog.MAX_CALL_LEVEL


def test_trigger_helpers_cover_act_percent_exit_greet_hpcnt(monkeypatch) -> None:
    room, mob, player = _setup_room()

    speech_prog = MobProgram(
        trig_type=int(mobprog.Trigger.SPEECH),
        trig_phrase="hail",
        vnum=4000,
        code="mob echo The guide greets $n.",
    )
    random_prog = MobProgram(
        trig_type=int(mobprog.Trigger.RANDOM),
        trig_phrase="50",
        vnum=4001,
        code="mob echo A random omen appears.",
    )
    exit_prog = MobProgram(
        trig_type=int(mobprog.Trigger.EXIT),
        trig_phrase=str(Direction.NORTH.value),
        vnum=4002,
        code="mob echo Someone leaves to the north.",
    )
    greet_prog = MobProgram(
        trig_type=int(mobprog.Trigger.GREET),
        trig_phrase="100",
        vnum=4003,
        code="mob echo Welcome to the chamber.",
    )
    hpcnt_prog = MobProgram(
        trig_type=int(mobprog.Trigger.HPCNT),
        trig_phrase="75",
        vnum=4004,
        code="mob echo The guide looks wounded.",
    )
    delay_prog = MobProgram(
        trig_type=int(mobprog.Trigger.DELAY),
        trig_phrase="100",
        vnum=4005,
        code="mob echo A delayed whisper echoes.",
    )

    mob.mob_programs = [
        speech_prog,
        random_prog,
        exit_prog,
        greet_prog,
        hpcnt_prog,
        delay_prog,
    ]

    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 10)

    player.messages.clear()
    assert mobprog.mp_act_trigger("hail friend", mob, player, trigger=mobprog.Trigger.SPEECH)
    assert player.messages.pop() == "The guide greets Hero."

    player.messages.clear()
    assert mobprog.mp_percent_trigger(mob, player, trigger=mobprog.Trigger.RANDOM)
    assert player.messages.pop() == "A random omen appears."

    player.messages.clear()
    assert mobprog.mp_exit_trigger(player, Direction.NORTH)
    assert player.messages.pop() == "Someone leaves to the north."

    player.messages.clear()
    mobprog.mp_greet_trigger(player)
    assert player.messages.pop() == "Welcome to the chamber."

    player.messages.clear()
    mob.hit = 50
    mob.max_hit = 100
    assert mobprog.mp_hprct_trigger(mob, player)
    assert player.messages.pop() == "The guide looks wounded."

    player.messages.clear()
    mob.mprog_delay = 1
    assert mobprog.mp_delay_trigger(mob)
    assert player.messages.pop() == "A delayed whisper echoes."


def test_event_hooks_fire_rom_triggers(monkeypatch) -> None:
    character_registry.clear()

    events: list[str] = []

    def record(event: str) -> None:
        events.append(event)

    monkeypatch.setattr(mobprog, "mp_exit_trigger", lambda ch, direction: (record("exit"), False)[1])

    def fake_greet(ch: Character) -> None:
        record("greet")

    monkeypatch.setattr(mobprog, "mp_greet_trigger", fake_greet)

    def fake_percent(
        mob: Character,
        actor: Character | None = None,
        arg1: object | None = None,
        arg2: object | None = None,
        trigger: mobprog.Trigger = mobprog.Trigger.RANDOM,
    ) -> bool:
        trig = mobprog.Trigger(trigger)
        if trig == mobprog.Trigger.ENTRY:
            record("percent-entry")
        return False

    monkeypatch.setattr(mobprog, "mp_percent_trigger", fake_percent)
    monkeypatch.setattr(mobprog, "mp_speech_trigger", lambda argument, mob, ch: record(f"speech:{mob.name}"))
    monkeypatch.setattr(mobprog, "mp_fight_trigger", lambda mob, ch: (record("fight"), False)[1])
    monkeypatch.setattr(mobprog, "mp_hprct_trigger", lambda mob, ch: (record("hpcnt"), False)[1])
    monkeypatch.setattr(mobprog, "mp_kill_trigger", lambda mob, ch: (record("kill"), False)[1])
    monkeypatch.setattr(mobprog, "mp_death_trigger", lambda mob, ch: (record("death"), False)[1])

    def fake_delay(mob: Character) -> bool:
        if int(getattr(mob, "mprog_delay", 0)) > 0:
            record("delay")
            mob.mprog_delay = 0
            return True
        return False

    monkeypatch.setattr(mobprog, "mp_delay_trigger", fake_delay)
    monkeypatch.setattr(mobprog, "mp_random_trigger", lambda mob: (record("random"), False)[1])
    monkeypatch.setattr(mobprog, "mp_surr_trigger", lambda mob, ch: (record("surrender"), False)[1])

    start = Room(vnum=6000, name="Start")
    target = Room(vnum=6001, name="Target")
    start.exits[Direction.NORTH.value] = Exit(to_room=target, keyword="archway")
    target.exits[Direction.SOUTH.value] = Exit(to_room=start, keyword="archway")

    guard = Character(name="Guard", is_npc=True, position=Position.STANDING)
    guard.default_pos = Position.STANDING
    greeter = Character(name="Greeter", is_npc=True, position=Position.STANDING)
    greeter.default_pos = Position.STANDING
    player = Character(name="Hero", is_npc=False, position=Position.STANDING)
    player.default_pos = Position.STANDING
    player.move = 100
    player.max_move = 100

    start.add_character(guard)
    start.add_character(player)
    target.add_character(greeter)

    character_registry.extend([player, guard, greeter])

    assert move_character(player, "north") == "You walk north to Target."
    assert move_character(guard, "north") == "You walk north to Target."

    do_say(player, "hello there")
    do_tell(player, f"{guard.name} secret news")

    guard.fighting = player
    player.fighting = guard
    multi_hit(guard, player)

    victim = Character(name="Target", is_npc=True, position=Position.STANDING, hit=5, max_hit=5)
    victim.default_pos = Position.STANDING
    target.add_character(victim)
    character_registry.append(victim)

    monkeypatch.setattr(
        "mud.combat.engine.calculate_weapon_damage",
        lambda attacker, victim, dam_type, **kwargs: 10,
    )
    player.hitroll = 100
    attack_round(player, victim)

    player.fighting = guard
    guard.fighting = player
    do_surrender(player, "")

    delay_npc = Character(name="Delayed", is_npc=True, position=Position.STANDING, mprog_delay=1)
    delay_npc.default_pos = Position.STANDING
    random_npc = Character(name="Wanderer", is_npc=True, position=Position.STANDING)
    random_npc.default_pos = Position.STANDING
    target.add_character(delay_npc)
    target.add_character(random_npc)
    character_registry.extend([delay_npc, random_npc])

    monkeypatch.setattr("mud.game_loop.reset_tick", lambda: None)
    monkeypatch.setattr("mud.game_loop.run_npc_specs", lambda: None)
    game_tick()

    for required in [
        "exit",
        "greet",
        "percent-entry",
        f"speech:{guard.name}",
        "fight",
        "hpcnt",
        "kill",
        "death",
        "surrender",
        "delay",
        "random",
    ]:
        assert required in events

    character_registry.clear()


def test_cmd_eval_conditionals(monkeypatch) -> None:
    room, mob, player = _setup_room()
    player.is_npc = False
    player.alignment = 400
    player.sex = 2

    sword_proto = ObjIndex(
        vnum=2000,
        name="steel sword",
        short_descr="a steel sword",
        item_type=int(ItemType.WEAPON),
    )
    sword = Object(instance_id=1, prototype=sword_proto)
    player.add_object(sword)

    helm_proto = ObjIndex(
        vnum=2001,
        name="iron helm",
        short_descr="an iron helm",
        item_type=int(ItemType.ARMOR),
    )
    helm = Object(instance_id=2, prototype=helm_proto)
    player.equip_object(helm, "head")

    blade_proto = ObjIndex(
        vnum=2002,
        name="gleaming blade",
        short_descr="a gleaming blade",
        item_type=int(ItemType.WEAPON),
    )
    blade = Object(instance_id=3, prototype=blade_proto)
    player.equip_object(blade, "wield")

    program = MobProgram(
        trig_type=int(mobprog.Trigger.SPEECH),
        trig_phrase="parity",
        vnum=9000,
        code="""
if isnpc $n
    mob echo Should not see this.
endif
if exists $n
    mob echo $n exists.
endif
if exists $q
    mob echo Target stored.
endif
if isgood $n
    mob echo $n passes goodness.
endif
if isvisible $n
    mob echo $n is visible.
endif
if carries $n 2000
    mob echo $n carries vnum.
endif
if wears $n helm
    mob echo $n wears helm.
endif
if has $n weapon
    mob echo $n has weapon.
endif
if uses $n weapon
    mob echo $n uses weapon.
endif
if off $i berserk
    mob echo Berserk stance ready.
endif
""",
    )

    mob.mob_programs = [program]
    mob.off_flags = int(OffFlag.BERSERK)

    monkeypatch.setattr("mud.commands.dispatcher.process_command", lambda *_: "")

    results = mobprog.run_prog(
        mob,
        mobprog.Trigger.SPEECH,
        actor=player,
        phrase="parity check",
    )

    echo_arguments = [res.argument for res in results if res.command == "mob echo"]

    assert echo_arguments == [
        "Hero exists.",
        "Target stored.",
        "Hero passes goodness.",
        "Hero is visible.",
        "Hero carries vnum.",
        "Hero wears helm.",
        "Hero has weapon.",
        "Hero uses weapon.",
        "Berserk stance ready.",
    ]


def test_expand_arg_supports_rom_tokens(monkeypatch) -> None:
    room, mob, player = _setup_room()
    player.sex = 2
    mob.sex = 1

    bystander = Character(name="Scout", is_npc=False)
    bystander.sex = 1
    room.add_character(bystander)

    mob.mprog_target = player

    monkeypatch.setattr(mobprog, "_get_random_char", lambda _: bystander)

    program = MobProgram(
        trig_type=int(mobprog.Trigger.SPEECH),
        trig_phrase="tokens",
        vnum=9100,
        code="mob echo $Q/$J/$K/$L/$X/$Y/$Z",
    )

    mob.mob_programs = [program]

    results = mobprog.run_prog(
        mob,
        mobprog.Trigger.SPEECH,
        actor=player,
        phrase="tokens now",
    )

    echo_arguments = [res.argument for res in results if res.command == "mob echo"]

    assert echo_arguments == ["Hero/he/him/his/she/her/her"]


def test_trigger_phrases_match_case(monkeypatch) -> None:
    _, mob, player = _setup_room()
    mobprog._PROGRAM_REGISTRY.clear()

    program = MobProgram(
        trig_type=int(mobprog.Trigger.SPEECH),
        trig_phrase="Hello",
        vnum=9200,
        code="say Hello $n",
    )
    mob.mob_programs = [program]

    calls: list[tuple[int, str]] = []

    def fake_program_flow(
        pvnum: int,
        code: str,
        context: mobprog.ProgramContext,
        mob_arg: Character,
        ch_arg: object | None,
        arg1: object | None,
        arg2: object | None,
        rch_arg: object | None,
    ) -> None:
        calls.append((pvnum, code))

    monkeypatch.setattr(mobprog, "_program_flow", fake_program_flow)

    fired = mobprog.mp_act_trigger("Hello there", mob, player, trigger=mobprog.Trigger.SPEECH)
    assert fired
    assert calls == [(program.vnum, program.code)]

    calls.clear()
    fired = mobprog.mp_act_trigger("hello there", mob, player, trigger=mobprog.Trigger.SPEECH)
    assert not fired
    assert calls == []

    calls.clear()
    pc_program = MobProgram(
        trig_type=int(mobprog.Trigger.SPEECH),
        trig_phrase="Hello",
        vnum=9201,
        code="say Should not run",
    )
    player.mob_programs = [pc_program]

    fired = mobprog.mp_act_trigger("Hello there", player, mob, trigger=mobprog.Trigger.SPEECH)
    assert not fired
    assert calls == []

    mobprog._PROGRAM_REGISTRY.clear()
