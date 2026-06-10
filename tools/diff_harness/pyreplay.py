"""Python-side replay driver for differential harness scenarios."""

from __future__ import annotations

from mud.commands.dispatcher import process_command
from mud.registry import room_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world
from tools.diff_harness.pysnap import _person_key, snapshot_python
from tools.diff_harness.scenario import Scenario
from tools.diff_harness.schema import StepSnap


def drive_python_replay(sc: Scenario) -> list[StepSnap]:
    """Drive the Python engine through ``sc`` and return per-step snapshots."""
    rng_mm.seed_mm(sc.seed)
    initialize_world()
    char = create_test_character(sc.char_name, sc.start_room)
    char.level = sc.char_level
    # Mirror the C shim's make_test_char defaults.
    char.max_hit = char.hit = 20
    char.max_mana = char.mana = 100
    char.max_move = char.move = 100
    char.ch_class = 0
    char.perm_stat = [13, 16, 13, 13, 13]
    char.hitroll = 0
    char.damroll = 0
    char.armor = [100, 100, 100, 100]
    # Mirror the C shim's make_test_char pcdata condition defaults
    # (diffmain.c:456-458): COND_THIRST/COND_FULL/COND_HUNGER all start at 48.
    char.condition = [0, 48, 48, 48]

    chars_by_name = {sc.char_name: char}
    rooms_by_vnum = {v: room_registry[v] for v in sc.watch_rooms}
    if char.messages:
        raise AssertionError(f"unexpected pre-command messages: {char.messages}")

    py_trace: list[StepSnap] = []
    for i, command in enumerate(sc.steps, start=1):
        response = _run_python_command(command, char, chars_by_name, sc.watch_chars)
        drained = list(char.messages)
        char.messages.clear()
        lines: list[str] = []
        for chunk in (response, *drained):
            lines.extend(chunk.split("\n"))
        py_trace.append(
            snapshot_python(
                step=i,
                command=command,
                chars_by_name=chars_by_name,
                rooms_by_vnum=rooms_by_vnum,
                output=lines,
            )
        )
    return py_trace


def _run_python_command(command: str, char, chars_by_name: dict[str, object], watch_chars: list[str]) -> str:
    if command.startswith("__seed="):
        rng_mm.seed_mm(int(command[len("__seed=") :]))
        return ""
    if command.startswith("__hour="):
        from mud.time import time_info

        time_info.hour = int(command[len("__hour=") :])
        return ""
    if command.startswith("__gold="):
        char.gold = int(command[len("__gold=") :])
        return ""
    if command.startswith("__silver="):
        char.silver = int(command[len("__silver=") :])
        return ""
    if command.startswith("__mana="):
        val = int(command[len("__mana=") :])
        char.mana = val
        char.max_mana = max(int(getattr(char, "max_mana", 0) or 0), val)
        return ""
    if command.startswith("__level="):
        char.level = int(command[len("__level=") :])
        return ""
    if command.startswith("__goto="):
        destination = room_registry[int(command[len("__goto=") :])]
        if getattr(char, "room", None) is not None:
            char.room.remove_character(char)
        destination.add_character(char)
        return ""
    if command.startswith("__mob_gold="):
        from mud.spawning.templates import MobInstance

        val = int(command[len("__mob_gold=") :])
        mob = next((p for p in char.room.people if isinstance(p, MobInstance)), None)
        if mob is not None:
            mob.gold = val
        return ""
    if command.startswith("__mob_silver="):
        from mud.spawning.templates import MobInstance

        val = int(command[len("__mob_silver=") :])
        mob = next((p for p in char.room.people if isinstance(p, MobInstance)), None)
        if mob is not None:
            mob.silver = val
        return ""
    if command.startswith("__cond_full="):
        from mud.models.constants import Condition

        char.condition[int(Condition.FULL)] = int(command[len("__cond_full=") :])
        return ""
    if command.startswith("__cond_thirst="):
        from mud.models.constants import Condition

        char.condition[int(Condition.THIRST)] = int(command[len("__cond_thirst=") :])
        return ""
    if command.startswith("__learn="):
        from mud.skills import skill_registry

        spell_name = command[len("__learn=") :].strip()
        resolved = skill_registry.find_spell(char, spell_name)
        if resolved is None:
            raise AssertionError(f"__learn: unknown skill {spell_name!r}")
        if char.skills is None:
            char.skills = {}
        char.skills[resolved.name] = 100
        return ""
    if command.startswith("__mload="):
        mob = spawn_mob(int(command[len("__mload=") :]))
        if mob is None:
            raise AssertionError(f"spawn_mob failed for {command!r}")
        char.room.add_character(mob)
        # Only snapshot the spawned mob if the scenario declares it in
        # watch.chars — mirroring the C shim, which resolves snapshot keys
        # strictly from the declared watch set (diffmain.c:resolve_watched_char).
        # Auto-adding every mload'd mob diverged from C for give/transfer targets
        # that aren't being observed (e.g. the money_drop_get_give "wizard").
        key = _person_key(mob)
        if key in watch_chars:
            chars_by_name[key] = mob
        return ""
    if command.startswith("__mob_hold="):
        from mud.models.constants import WearLocation
        from mud.spawning.obj_spawner import spawn_object
        from mud.spawning.templates import MobInstance

        obj = spawn_object(int(command[len("__mob_hold=") :]))
        if obj is None:
            raise AssertionError(f"spawn_object failed for {command!r}")
        obj.value = list(obj.value)
        obj.value[1] = 0
        mob = next((p for p in char.room.people if isinstance(p, MobInstance)), None)
        if mob is None:
            raise AssertionError("no NPC in room for __mob_hold")
        mob.add_to_inventory(obj)
        obj.wear_loc = int(WearLocation.HOLD)
        if not hasattr(mob, "equipment") or mob.equipment is None:
            mob.equipment = {}
        mob.equipment[int(WearLocation.HOLD)] = obj
        key = _person_key(mob)
        if key in watch_chars:
            chars_by_name[key] = mob
        return ""
    if command.startswith("__mob_carry="):
        from mud.spawning.obj_spawner import spawn_object
        from mud.spawning.templates import MobInstance

        obj = spawn_object(int(command[len("__mob_carry=") :]))
        if obj is None:
            raise AssertionError(f"spawn_object failed for {command!r}")
        mob = next((p for p in char.room.people if isinstance(p, MobInstance)), None)
        if mob is None:
            raise AssertionError("no NPC in room for __mob_carry")
        mob.add_to_inventory(obj)
        key = _person_key(mob)
        if key in watch_chars:
            chars_by_name[key] = mob
        return ""
    if command.startswith("__mob_prog="):
        from mud.mobprog import Trigger
        from mud.models.mob import MobProgram
        from mud.spawning.templates import MobInstance

        rest = command[len("__mob_prog=") :]
        trig_name, trig_phrase, code = rest.split(":", 2)
        mob = next((p for p in char.room.people if isinstance(p, MobInstance)), None)
        if mob is None:
            raise AssertionError("no NPC in room for __mob_prog")
        trig_type = getattr(Trigger, trig_name.upper(), None)
        if trig_type is None:
            raise AssertionError(f"unknown trigger type {trig_name!r} in __mob_prog")
        prog = MobProgram(trig_type=int(trig_type), trig_phrase=trig_phrase, code=code)
        if not isinstance(getattr(mob, "mob_programs", None), list):
            mob.mob_programs = []
        # mirroring ROM C: prog->next = mob->pIndexData->mprogs (prepend = LIFO)
        mob.mob_programs.insert(0, prog)
        return ""
    if command.startswith("__oload="):
        from mud.spawning.obj_spawner import spawn_object

        obj = spawn_object(int(command[len("__oload=") :]))
        if obj is None:
            raise AssertionError(f"spawn_object failed for {command!r}")
        char.room.add_object(obj)
        return ""
    if command.startswith("__tick"):
        from mud.game_loop import violence_tick

        violence_tick(do_combat=True)
        return ""
    if command.startswith("__char_update"):
        from mud.game_loop import char_update

        char_update()
        return ""
    if command.startswith("__set_affect_duration="):
        dur = int(command[len("__set_affect_duration=") :])
        for aff in getattr(char, "affected", []) or []:
            aff.duration = dur
        return ""
    if command.startswith("__charm_mob="):
        # Charm the first NPC in the room with a fixed duration, bypassing the
        # spell cast path and immunity checks.  Mirrors the C-shim __charm_mob
        # handler in diffmain.c (ROM src/magic.c:1347-1390 spell_charm_person).
        from mud.characters.follow import add_follower
        from mud.models.character import SpellEffect
        from mud.models.constants import AffectFlag
        from mud.spawning.templates import MobInstance

        dur = int(command[len("__charm_mob=") :])
        mob = next((p for p in char.room.people if isinstance(p, MobInstance)), None)
        if mob is None:
            raise AssertionError("no NPC in room for __charm_mob")
        add_follower(mob, char)
        mob.leader = char  # mirroring ROM src/magic.c:1381 victim->leader = ch
        effect = SpellEffect(
            name="charm person",
            duration=dur,
            level=char.level,
            affect_flag=AffectFlag.CHARM,
            wear_off_message="You feel more self-confident.",
        )
        mob.apply_spell_effect(effect)
        key = _person_key(mob)
        if key in watch_chars:
            chars_by_name[key] = mob
        return ""
    if command.startswith("__mob_position="):
        from mud.models.constants import Position
        from mud.spawning.templates import MobInstance

        new_pos = int(command[len("__mob_position=") :])
        mob = next((p for p in char.room.people if isinstance(p, MobInstance)), None)
        if mob is None:
            raise AssertionError("no NPC in room for __mob_position")
        mob.position = Position(new_pos)
        return ""
    if command.startswith("__mob_hp="):
        from mud.spawning.templates import MobInstance

        val = int(command[len("__mob_hp=") :])
        mob = next((p for p in char.room.people if isinstance(p, MobInstance)), None)
        if mob is None:
            raise AssertionError("no NPC in room for __mob_hp")
        mob.hit = val
        return ""

    if command.startswith("__instant_kill"):
        # Deliver a killing blow through the full Python death path (apply_damage at
        # dam = mob.hit + 1) so TRIG_DEATH, XP, corpse, and raw_kill all fire.
        # dt=1000 (TYPE_HIT) mirrors the C shim which calls damage(..., TYPE_HIT, DAM_BASH, TRUE),
        # ensuring parry/dodge/shield checks run in the same order as C's damage().
        # Mirrors the C-shim __instant_kill handler in diffmain.c.
        from mud.combat.engine import apply_damage
        from mud.models.constants import DamageType
        from mud.spawning.templates import MobInstance

        mob = next((p for p in char.room.people if isinstance(p, MobInstance)), None)
        if mob is None:
            raise AssertionError("no NPC in room for __instant_kill")
        apply_damage(char, mob, mob.hit + 1, int(DamageType.BASH), dt=1000)  # type: ignore[arg-type]
        return ""

    if command.startswith("__mobile_update"):
        # Run one mobile_update() pulse — triggers TRIG_RANDOM and TRIG_DELAY.
        # Mirrors the C shim __mobile_update handler in diffmain.c.
        # ROM src/update.c:408 mobile_update().
        from mud.ai import mobile_update

        mobile_update()
        return ""

    if command.startswith("__mob_delay="):
        # Set the first NPC in the room's mprog_delay countdown to N.
        # Mirrors the C shim __mob_delay handler in diffmain.c.
        # ROM src/mob_prog.c:mp_delay_trigger.
        from mud.spawning.templates import MobInstance

        val = int(command[len("__mob_delay=") :])
        mob = next((p for p in char.room.people if isinstance(p, MobInstance)), None)
        if mob is None:
            raise AssertionError("no NPC in room for __mob_delay")
        mob.mprog_delay = val
        return ""

    # Mirror the C shim's direct interpret() path, which bypasses comm.c's wait
    # gate. FINDING-014 documents the architectural divergence.
    char.wait = 0
    return process_command(char, command) or ""
