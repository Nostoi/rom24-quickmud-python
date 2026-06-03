from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import settings
from hypothesis.stateful import run_state_machine_as_test

from tools.diff_harness.compare import diff_traces
from tools.diff_harness.generated import DeterministicNoRngDiffMachine
from tools.diff_harness.oracle import drive_c_oracle
from tools.diff_harness.pyreplay import drive_python_replay
from tools.diff_harness.scenario import Scenario

REPO = Path(__file__).resolve().parents[1]
DIFFSHIM = REPO / "src" / "diffshim"


def test_generated_no_rng_sequences_match_live_c():
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    run_state_machine_as_test(
        lambda: DeterministicNoRngDiffMachine(binary=DIFFSHIM),
        settings=settings(max_examples=4, stateful_step_count=5, deadline=None),
    )


def test_generated_object_lifecycle_sequence_matches_live_c():
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_oload",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__oload=3021", "get sword", "wield sword", "remove sword", "drop sword"],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None
