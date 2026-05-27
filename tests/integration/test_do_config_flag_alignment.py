"""Regression for PARALLEL-001: do_config display table read wrong bits.

The toggle commands (`do_autoloot`, `do_autosac`, `do_compact`, …) set the
canonical `PlayerFlag` / `CommFlag` IntEnum bits. The pre-fix `do_config`
display table hardcoded different hex literals so the ON/OFF column never
agreed with what the toggle actually did — `autoloot` toggle flipped bit 4
(`PlayerFlag.AUTOLOOT`) but the table read bit 15 (`0x00008000`).

ROM C uses single-letter macros (`A=1<<0`, `C=1<<2`, `E=1<<4`, ...);
`mud/models/constants.py` mirrors them. The hex constants in
`misc_player.py:90-100` did not. This test pins the toggle-vs-display
contract.
"""

from __future__ import annotations

import pytest

from mud.commands.auto_settings import (
    do_autoexit,
    do_autoloot,
    do_autosac,
    do_brief,
    do_combine,
    do_compact,
)
from mud.commands.misc_player import do_afk, do_config
from mud.models.character import Character


@pytest.fixture
def player() -> Character:
    char = Character(name="ConfigTester", level=1, is_npc=False)
    char.act = 0
    char.comm = 0
    return char


def _row(output: str, keyword: str) -> str:
    for line in output.splitlines():
        if f"[{keyword:^10s}]" in line:
            return line
    raise AssertionError(f"no row for {keyword!r} in:\n{output}")


def test_do_config_reports_on_after_toggles_set_canonical_flags(player: Character) -> None:
    do_autoloot(player, "")
    do_autosac(player, "")
    do_autoexit(player, "")
    do_compact(player, "")
    do_brief(player, "")
    do_combine(player, "")
    do_afk(player, "")

    output = do_config(player, "")

    assert " ON " in _row(output, "autoloot"), _row(output, "autoloot")
    assert " ON " in _row(output, "autosac"), _row(output, "autosac")
    assert " ON " in _row(output, "autoexit"), _row(output, "autoexit")
    assert " ON " in _row(output, "compact"), _row(output, "compact")
    assert " ON " in _row(output, "brief"), _row(output, "brief")
    assert " ON " in _row(output, "combine"), _row(output, "combine")
    assert " ON " in _row(output, "afk"), _row(output, "afk")


def test_do_config_reports_off_when_no_flags_set(player: Character) -> None:
    output = do_config(player, "")
    for keyword in ("autoloot", "autosac", "autoexit", "compact", "brief", "combine", "afk"):
        assert " OFF" in _row(output, keyword)
