"""RECALL-002 — do_recall must call check_improve on failure and success.

ROM src/act_move.c:1601: ``check_improve(ch, gsn_recall, FALSE, 6)`` on failure
ROM src/act_move.c:1610: ``check_improve(ch, gsn_recall, TRUE, 4)`` on success

Python had ``# TODO: check_improve(...)`` stubs that never fired, so the recall
skill never improved from use.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from mud.commands.session import do_recall
from mud.models.constants import Position
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def test_recall002_check_improve_called_on_failure() -> None:
    # mirrors ROM src/act_move.c:1601 — check_improve(ch, gsn_recall, FALSE, 6)
    ch = create_test_character("Tester", 2300)
    ch.position = int(Position.FIGHTING)
    ch.skills["recall"] = 50
    ch.desc = None

    with (
        patch("mud.utils.rng_mm.number_percent", return_value=1),  # 1 < 80*50//100=40 → fail
        patch("mud.commands.session.check_improve") as improve_mock,
    ):
        do_recall(ch, "")

    assert improve_mock.called, (
        "do_recall did not call check_improve on failure. "
        "ROM src/act_move.c:1601 calls check_improve(ch, gsn_recall, FALSE, 6)."
    )
    args, kwargs = improve_mock.call_args
    multiplier = kwargs.get("multiplier", args[3] if len(args) > 3 else None)
    assert args[0] is ch
    assert args[1] == "recall"
    assert args[2] is False
    assert multiplier == 6, f"ROM passes multiplier=6 on failure; got {multiplier!r}"


def test_recall002_check_improve_called_on_success() -> None:
    # mirrors ROM src/act_move.c:1610 — check_improve(ch, gsn_recall, TRUE, 4)
    ch = create_test_character("Tester", 2300)
    ch.position = int(Position.FIGHTING)
    ch.skills["recall"] = 0  # skill=0 → threshold=0, number_percent always >= 0 → success
    ch.desc = None

    with (
        patch("mud.commands.session.check_improve") as improve_mock,
        patch("mud.advancement.gain_exp"),  # suppress side effects
    ):
        do_recall(ch, "")

    assert improve_mock.called, (
        "do_recall did not call check_improve on success. "
        "ROM src/act_move.c:1610 calls check_improve(ch, gsn_recall, TRUE, 4)."
    )
    args, kwargs = improve_mock.call_args
    multiplier = kwargs.get("multiplier", args[3] if len(args) > 3 else None)
    assert args[0] is ch
    assert args[1] == "recall"
    assert args[2] is True
    assert multiplier == 4, f"ROM passes multiplier=4 on success; got {multiplier!r}"
