"""Differential smoke test: drive the Python engine through each captured
scenario and assert its per-step state+output matches the committed C golden."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mud.commands.dispatcher import process_command
from mud.registry import room_registry
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world
from tools.diff_harness.compare import diff_traces
from tools.diff_harness.pysnap import snapshot_python
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
    "movement_get_drop": (
        "Two real ROM parity bugs (deferred to master gap-closers), surfaced once "
        "the harness output capture was made fair:\n"
        "  FINDING-003 — movement emits a non-ROM 'You walk <dir> to <room>.' line "
        "(ROM act_move.c:204 shows room-only via do_look auto). mud/world/movement.py:455,470.\n"
        "  FINDING-004 — room object list shows obj name ('the donation pit') not "
        "ROM's ground description ('A pit for sacrifices...'). mud/world/look.py:172-173.\n"
        "Harness start-state/capture asymmetries (FINDING-002 hp/level, people-key, "
        "output channel) are resolved. See tools/diff_harness/FINDINGS.md."
    ),
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
