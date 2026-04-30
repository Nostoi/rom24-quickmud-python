"""OLC_ACT-012: `aedit reset` subcommand mirrors ROM `aedit_reset`.

ROM src/olc_act.c:653-663 — calls `reset_area(pArea)` and sends
`"Area reset.\\n\\r"`.
"""

from __future__ import annotations

from unittest.mock import patch

from mud.commands.build import _interpret_aedit
from mud.models.area import Area


class _StubChar:
    name = "Tester"
    pcdata = type("PC", (), {"security": 9})()


class _StubSession:
    def __init__(self, area: Area) -> None:
        self.editor = "aedit"
        self.editor_state = {"area": area}


def test_aedit_reset_emits_rom_message_and_calls_apply_resets() -> None:
    area = Area(vnum=42, name="Reset Test", builders="Tester")
    session = _StubSession(area)
    with patch("mud.spawning.reset_handler.apply_resets") as mock_apply:
        result = _interpret_aedit(session, _StubChar(), "reset")
    assert result == "Area reset."
    mock_apply.assert_called_once_with(area)
    assert area.changed is True
