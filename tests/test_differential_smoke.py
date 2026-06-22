"""Differential smoke test: drive the Python engine through each captured
scenario and assert its per-step state+output matches the committed C golden."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.diff_harness.compare import diff_traces
from tools.diff_harness.pyreplay import drive_python_replay
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
    # Empty — every committed scenario (49 as of 2026-06-22: movement/get-drop,
    # containers, doors, melee + spell combat, the full mob-trigger set, char_update
    # regen variants, affects, shops, cast-position gate, group/follow cycle, …)
    # converges end-to-end.
    # Historical notes on scenarios that once diverged are kept below for provenance.
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

    py_trace = drive_python_replay(sc)

    report = diff_traces(c_trace, py_trace)
    if report is not None and sc.name in KNOWN_DIVERGENCES:
        pytest.xfail(f"{KNOWN_DIVERGENCES[sc.name]}\n\n{report}")
    assert report is None, f"Python diverged from C reference:\n{report}"
