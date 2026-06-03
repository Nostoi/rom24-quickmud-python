"""FINDING-020 — equip→remove must preserve ROM's carry-list position.

ROM keeps equipped objects in ``ch->carrying`` with only ``wear_loc`` set
(``src/handler.c`` ``get_eq_char`` loops the carry list); ``unequip_char`` merely
clears ``wear_loc``, so a removed object keeps its original carry-list slot.
New acquisitions head-insert *in front of* an equipped object, so its position
is **relative to acquisition order**, not a fixed index and not always head/tail.

The Python port stores equipped objects in a separate ``char.equipment`` dict
and historically re-**appended** them to ``inventory`` on remove, so a removed
item always landed at the tail regardless of when it was acquired.

The expected inventory orders below were captured from the instrumented ROM C
engine via ``tools/diff_harness`` (the live diffshim oracle) — they are C ground
truth, not Python-authored expectations:

    findings_case      remove sword (acquired AFTER bag)        -> [3021, 3032]
    interleave_case    remove sword (acquired FIRST, then bag+jacket) -> [3045, 3032, 3021]
    container_roundtrip re-acquire sword from bag, then remove  -> [3021, 3045, 3032]

Objects: small sword 3021 (wield), bag 3032 (container), scale-mail jacket 3045.
"""

from __future__ import annotations

import pytest

from tools.diff_harness.pyreplay import drive_python_replay
from tools.diff_harness.scenario import Scenario


def _scenario(name: str, steps: list[str]) -> Scenario:
    return Scenario(
        name=name,
        seed=12345,
        start_room=3001,
        char_name="Tester",
        char_level=50,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=steps,
    )


def _final_inventory(sc: Scenario) -> list[int]:
    trace = drive_python_replay(sc)
    assert trace, "replay produced no snapshots"
    last = trace[-1]
    assert last.chars, "no character snapshot"
    return last.chars[0].inventory


@pytest.mark.parametrize(
    ("name", "steps", "expected"),
    [
        (
            "findings_case",
            ["__oload=3032", "__oload=3021", "get bag", "get sword", "wield sword", "remove sword"],
            [3021, 3032],
        ),
        (
            "interleave_case",
            [
                "__oload=3021",
                "get sword",
                "wield sword",
                "__oload=3032",
                "get bag",
                "__oload=3045",
                "get jacket",
                "remove sword",
            ],
            [3045, 3032, 3021],
        ),
        (
            "container_roundtrip",
            [
                "__oload=3032",
                "get bag",
                "__oload=3021",
                "get sword",
                "__oload=3045",
                "get jacket",
                "put sword bag",
                "get sword bag",
                "wield sword",
                "remove sword",
            ],
            [3021, 3045, 3032],
        ),
    ],
)
def test_equip_remove_preserves_carry_list_position(name, steps, expected):
    assert _final_inventory(_scenario(name, steps)) == expected
