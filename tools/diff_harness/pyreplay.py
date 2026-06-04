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

    # Mirror the C shim's direct interpret() path, which bypasses comm.c's wait
    # gate. FINDING-014 documents the architectural divergence.
    char.wait = 0
    return process_command(char, command) or ""
