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
KNOWN_DIVERGENCES = {
    # FINDING-011: FINDING-010 (unarmed-NPC damage used the PC formula, not the mob
    # damage dice) is resolved on master — FIGHT-027 (v2.11.15): an unarmed NPC now
    # rolls dice(damage[DICE_NUMBER], damage[DICE_TYPE]) instead of the degenerate
    # PC-unarmed number_range. Steps 1–6 now converge (hp + severity verbs match
    # end-to-end). The first divergence advanced to step 7 (the *third* __tick round),
    # a MISS-LINE rendering gap: when an NPC with a resolved attack type misses, ROM
    # renders the attack noun (C=["The drunk's beating misses you.", ...]) but Python
    # drops it (py=['The drunk misses you.', ...]). Distinct root cause from FIGHT-027
    # (dam_message miss-path rendering, not damage calc). See FINDINGS.md FINDING-011
    # / FIGHT_C_AUDIT.md FIGHT-028.
    "combat_melee_rounds": "FINDING-011 — combat miss line drops the attack noun: C \"The drunk's beating misses you.\" vs py 'The drunk misses you.'",
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
            rng_mm.seed_mm(int(command[len("__seed="):]))
            response = ""
        elif command.startswith("__mload="):
            mob = spawn_mob(int(command[len("__mload="):]))
            assert mob is not None, f"spawn_mob failed for {command!r}"
            char.room.add_character(mob)
            chars_by_name[_person_key(mob)] = mob
            response = ""
        elif command.startswith("__tick"):
            from mud.game_loop import violence_tick

            violence_tick(do_combat=True)
            response = ""
        else:
            response = process_command(char, command) or ""
        drained = list(char.messages)
        char.messages.clear()
        lines: list[str] = []
        for chunk in (response, *drained):
            lines.extend(chunk.split("\n"))
        py_trace.append(
            snapshot_python(
                step=i, command=command,
                chars_by_name=chars_by_name, rooms_by_vnum=rooms_by_vnum,
                output=lines,
            )
        )

    report = diff_traces(c_trace, py_trace)
    if report is not None and sc.name in KNOWN_DIVERGENCES:
        pytest.xfail(f"{KNOWN_DIVERGENCES[sc.name]}\n\n{report}")
    assert report is None, f"Python diverged from C reference:\n{report}"
