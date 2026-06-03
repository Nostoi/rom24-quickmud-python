"""Differential smoke test: drive the Python engine through each captured
scenario and assert its per-step state+output matches the committed C golden."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mud.commands.dispatcher import process_command
from mud.registry import room_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world
from tools.diff_harness.compare import diff_traces
from tools.diff_harness.pysnap import _person_key, snapshot_python
from tools.diff_harness.scenario import load_scenario
from tools.diff_harness.schema import step_from_dict

REPO = Path(__file__).resolve().parents[1]
SCEN_DIR = REPO / "tools" / "diff_harness" / "scenarios"
GOLDEN_DIR = REPO / "tests" / "data" / "golden" / "diff"

# Scenarios with a documented, not-yet-resolved divergence. Maps scenario name →
# reason. When a divergence is actually fixed the diff goes clean, no xfail
# fires, the test passes, and the entry should be removed (self-cleaning).
# See tools/diff_harness/FINDINGS.md.
KNOWN_DIVERGENCES: dict[str, str] = {
    # Empty — all four scenarios converge end-to-end: movement_get_drop,
    # combat_melee_rounds, spell_combat, affect_armor.
    # spell_combat surfaced FINDING-012 (saving_throw crash) + FINDING-013 (spurious
    # "You cast" line), both fixed on master (v2.11.18/.19). The step-6 wait-state
    # gap (FINDING-014) is an architectural divergence (sync pulse-loop vs async),
    # NOT a parity bug — the replay now drives ordinary commands below the wait gate
    # (char.wait = 0), mirroring the C shim's direct interpret(). See FINDINGS.md.
    # affect_armor surfaced FINDING-015 (MAGIC-002): the Python armor handler was
    # silent on success while ROM spell_armor sends "You feel someone protecting
    # you."; fixed on master (v2.11.20), so the diff is clean and the entry cleared.
    # When a divergence is resolved the diff goes clean, the xfail flips to XPASS,
    # and its entry should be removed here (self-cleaning).
}


def _scenarios():
    return sorted(SCEN_DIR.glob("*.json"))


@pytest.mark.parametrize("scen_path", _scenarios(), ids=lambda p: p.stem)
def test_python_matches_c_golden(scen_path):
    sc = load_scenario(scen_path)
    gold_path = GOLDEN_DIR / f"{sc.name}.golden.json"
    if not gold_path.exists():
        pytest.skip(f"no golden captured for {sc.name} (run capture.py)")

    c_trace = [step_from_dict(s) for s in json.loads(gold_path.read_text())["trace"]]

    rng_mm.seed_mm(sc.seed)
    initialize_world()
    char = create_test_character(sc.char_name, sc.start_room)
    char.level = sc.char_level
    # Mirror the C shim's test char: ROM new_char() seeds hit/mana/move from the
    # recycle.c:299-304 defaults (20/100/100), which make_test_char then copies
    # into the live pools. create_test_character (a shared test stub) leaves them
    # at the dataclass default 0, so set them here for a fair differential start.
    char.max_hit = char.hit = 20
    char.max_mana = char.mana = 100
    char.max_move = char.move = 100
    # Mirror the C shim's make_test_char (src/diff_shim/diffmain.c:380): class 0
    # (mage), perm_stat all 13 with prime (INT) +3, no gear. create_test_character
    # leaves perm_stat empty, which combat math reads; set it so effective
    # hitroll/damroll/AC match the C reference. ROM stat order: STR, INT, WIS, DEX, CON.
    char.ch_class = 0
    char.perm_stat = [13, 16, 13, 13, 13]
    char.hitroll = 0
    char.damroll = 0
    char.armor = [100, 100, 100, 100]

    chars_by_name = {sc.char_name: char}
    rooms_by_vnum = {v: room_registry[v] for v in sc.watch_rooms}

    # The C shim captures the descriptor's output buffer — everything ROM sends to
    # the player. The fair Python equivalent mirrors the live server loop
    # (mud/net/connection.py:1979-2000): the command's return value is sent first,
    # then char.messages (send_to_char delivery, e.g. movement auto-look) is drained.
    # Capturing only the return value (the v1 behavior) misses send_to_char output.
    assert not char.messages, f"unexpected pre-command messages: {char.messages}"

    py_trace = []
    for i, command in enumerate(sc.steps, start=1):
        # Meta-commands mirror the C shim's stdin driver (src/diff_shim/diffmain.c):
        # __seed reseeds the shared RNG, __mload spawns a mob into the PC's room,
        # __tick runs one violence_update() combat pulse. Everything else is an
        # ordinary ROM command.
        if command.startswith("__seed="):
            rng_mm.seed_mm(int(command[len("__seed=") :]))
            response = ""
        elif command.startswith("__learn="):
            # Teach the PC a skill/spell at 100% (mirrors the C shim's __learn,
            # src/diff_shim/diffmain.c). Canonicalize the name through the same
            # registry do_cast reads, so the key matches skill.name exactly —
            # a casing/spacing mismatch would make Python's cast silently fail
            # while C succeeds (a harness artifact, not a parity bug).
            from mud.skills import skill_registry

            spell_name = command[len("__learn=") :].strip()
            resolved = skill_registry.find_spell(char, spell_name)
            assert resolved is not None, f"__learn: unknown skill {spell_name!r}"
            if char.skills is None:
                char.skills = {}
            char.skills[resolved.name] = 100
            response = ""
        elif command.startswith("__mload="):
            mob = spawn_mob(int(command[len("__mload=") :]))
            assert mob is not None, f"spawn_mob failed for {command!r}"
            char.room.add_character(mob)
            chars_by_name[_person_key(mob)] = mob
            response = ""
        elif command.startswith("__tick"):
            from mud.game_loop import violence_tick

            violence_tick(do_combat=True)
            response = ""
        else:
            # Drive ordinary commands BELOW the wait-state gate, mirroring the C
            # shim, which calls interpret() directly (src/diff_shim/diffmain.c) —
            # ROM's wait gate lives in the comm.c input loop (src/comm.c:619-621/
            # :820-822), which the shim bypasses, so a WAIT_STATE'd C actor still
            # executes a directly-driven command. Python enforces wait inside the
            # command handlers (do_cast etc.), so without this the second
            # consecutive cast would be rejected where C's executes. This is the
            # synchronous-loop-vs-async architectural divergence FINDING-014 (akin
            # to MESSAGE_DELIVERY) — not a parity bug, and `wait` is not in the
            # snapshot schema, so clearing it changes nothing under comparison.
            char.wait = 0
            response = process_command(char, command) or ""
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

    report = diff_traces(c_trace, py_trace)
    if report is not None and sc.name in KNOWN_DIVERGENCES:
        pytest.xfail(f"{KNOWN_DIVERGENCES[sc.name]}\n\n{report}")
    assert report is None, f"Python diverged from C reference:\n{report}"
