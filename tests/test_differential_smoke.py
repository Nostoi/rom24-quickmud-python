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
        "FINDING-002: test-character hp differs (C=20 vs py=0) — harness "
        "char-creation asymmetry (C shim new_char vs Python create_test_character), "
        "not a parity bug. Room/output rendering now matches after FINDING-001 "
        "(LOOK-001/002) was fixed. See tools/diff_harness/FINDINGS.md."
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

    chars_by_name = {sc.char_name: char}
    rooms_by_vnum = {v: room_registry[v] for v in sc.watch_rooms}

    py_trace = []
    for i, command in enumerate(sc.steps, start=1):
        output = process_command(char, command) or ""
        py_trace.append(
            snapshot_python(
                step=i, command=command,
                chars_by_name=chars_by_name, rooms_by_vnum=rooms_by_vnum,
                output=output.split("\n"),
            )
        )

    report = diff_traces(c_trace, py_trace)
    if report is not None and sc.name in KNOWN_DIVERGENCES:
        pytest.xfail(f"{KNOWN_DIVERGENCES[sc.name]}\n\n{report}")
    assert report is None, f"Python diverged from C reference:\n{report}"
