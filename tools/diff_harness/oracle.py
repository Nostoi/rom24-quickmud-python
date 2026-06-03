"""Live C-oracle driver for arbitrary differential harness scenarios."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tools.diff_harness.scenario import Scenario
from tools.diff_harness.schema import StepSnap, step_from_dict

REPO = Path(__file__).resolve().parents[2]


def build_c_input(sc: Scenario) -> str:
    """Build the stdin protocol consumed by src/diffshim for one scenario."""
    lines = [f"boot seed={sc.seed} start_room={sc.start_room} level={sc.char_level} char={sc.char_name}"]
    watch_chars = ",".join(sc.watch_chars)
    watch_rooms = ",".join(map(str, sc.watch_rooms))
    for step in sc.steps:
        lines.append(step)
        lines.append(f"__snapshot chars={watch_chars} rooms={watch_rooms}")
    return "\n".join(lines) + "\n"


def drive_c_oracle(
    sc: Scenario,
    binary: Path,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> list[StepSnap]:
    """Run diffshim live for ``sc`` and return the captured C trace.

    This is the Phase-A primitive for generated scenarios: callers can pass an
    in-memory Scenario and compare the returned StepSnap list without writing or
    reading a committed golden.
    """
    proc = run(
        [str(binary)],
        input=build_c_input(sc),
        capture_output=True,
        text=True,
        cwd=REPO / "src",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"C binary exited {proc.returncode}\nstderr:\n{proc.stderr}")

    events = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    return _events_to_trace(sc, events)


def _events_to_trace(sc: Scenario, events: list[dict[str, Any]]) -> list[StepSnap]:
    trace: list[StepSnap] = []
    pending_output: list[str] = []
    cmd_iter = iter(sc.steps)
    for ev in events:
        if ev["type"] == "output":
            pending_output.extend(ev["lines"])
        elif ev["type"] == "snapshot":
            snap = dict(ev)
            snap["step"] = len(trace) + 1
            snap["command"] = next(cmd_iter)
            snap["output"] = pending_output
            snap.pop("type", None)
            trace.append(step_from_dict(snap))
            pending_output = []
    return trace
