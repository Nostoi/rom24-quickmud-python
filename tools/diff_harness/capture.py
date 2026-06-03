"""Drive the instrumented C binary through a scenario and write a golden trace.

Usage:
    python3 -m tools.diff_harness.capture --scenario <name|path> [--binary src/diffshim]
    python3 -m tools.diff_harness.capture --all
    python3 -m tools.diff_harness.capture --check     # re-capture, diff vs committed
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from tools.diff_harness.oracle import drive_c_oracle
from tools.diff_harness.scenario import Scenario, load_scenario
from tools.diff_harness.schema import step_to_dict

REPO = Path(__file__).resolve().parents[2]
SCEN_DIR = REPO / "tools" / "diff_harness" / "scenarios"
GOLDEN_DIR = REPO / "tests" / "data" / "golden" / "diff"
DEFAULT_BINARY = REPO / "src" / "diffshim"


def _c_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO).decode().strip()


def _drive(sc: Scenario, binary: Path) -> list[dict]:
    return [step_to_dict(step) for step in drive_c_oracle(sc, binary)]


def capture(sc: Scenario, binary: Path) -> dict:
    return {
        "scenario": sc.name,
        "c_commit": _c_commit(),
        "build_flags": "-DOLD_RAND",
        "seed": sc.seed,
        "trace": _drive(sc, binary),
    }


def _write_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    tmp.replace(path)


def _resolve(scenario: str) -> Scenario:
    p = Path(scenario)
    if not p.exists():
        p = SCEN_DIR / f"{scenario}.json"
    return load_scenario(p)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--binary", default=str(DEFAULT_BINARY))
    args = ap.parse_args(argv)
    binary = Path(args.binary)

    if args.all or args.check:
        scenarios = [load_scenario(p) for p in sorted(SCEN_DIR.glob("*.json"))]
    elif args.scenario:
        scenarios = [_resolve(args.scenario)]
    else:
        ap.error("one of --scenario / --all / --check required")

    failures = 0
    for sc in scenarios:
        payload = capture(sc, binary)
        gold = GOLDEN_DIR / f"{sc.name}.golden.json"
        if args.check:
            existing = json.loads(gold.read_text()) if gold.exists() else None
            if existing is None or existing.get("trace") != payload["trace"]:
                print(f"CHANGED: {sc.name}")
                failures += 1
            else:
                print(f"ok: {sc.name}")
        else:
            _write_atomic(gold, payload)
            print(f"wrote {gold.relative_to(REPO)} ({len(payload['trace'])} steps)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
