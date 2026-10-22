"""OLC_ACT-019: `aedit security` enforces the builder's own clearance.

ROM src/olc_act.c:825-863 (aedit_security): the max settable value is the
BUILDER's own security (`value > ch->pcdata->security`), NOT a hardcoded 0-9.
A security-5 builder cannot raise an area above 5. On rejection ROM sends
`"Security is 0-<sec>.\\n\\r"` (or `"Security is 0 only.\\n\\r"` when the
builder's security is 0); on non-number `"Syntax:  security [#xlevel]\\n\\r"`;
on success bare `"Security set.\\n\\r"`.

Python previously used a flat `0-9` clamp ignoring the builder's clearance
(a permission divergence) and leaked the value (`"Security level set to {n}."`).
"""

from __future__ import annotations

from mud.commands.build import _interpret_aedit
from mud.models.area import Area


class _Builder:
    def __init__(self, security: int) -> None:
        self.name = "Tester"
        self.pcdata = type("PC", (), {"security": security})()


class _Session:
    def __init__(self, area: Area) -> None:
        self.editor = "area"
        self.editor_state = {"area": area}


def _area() -> Area:
    return Area(vnum=10, name="A", security=1, builders="Tester")


def test_security_set_within_clearance() -> None:
    area = _area()
    result = _interpret_aedit(_Session(area), _Builder(9), "security 7")
    assert result == "Security set."
    assert area.security == 7


def test_security_above_own_clearance_rejected() -> None:
    area = _area()
    # A security-5 builder may NOT set the area to 6 (ROM value > ch->security).
    result = _interpret_aedit(_Session(area), _Builder(5), "security 6")
    assert result == "Security is 0-5."
    assert area.security == 1  # unchanged


def test_security_at_own_clearance_allowed() -> None:
    area = _area()
    result = _interpret_aedit(_Session(area), _Builder(5), "security 5")
    assert result == "Security set."
    assert area.security == 5


def test_security_zero_builder_message() -> None:
    area = _area()
    result = _interpret_aedit(_Session(area), _Builder(0), "security 1")
    assert result == "Security is 0 only."
    assert area.security == 1


def test_security_negative_rejected() -> None:
    area = _area()
    result = _interpret_aedit(_Session(area), _Builder(9), "security -1")
    assert result == "Security is 0-9."


def test_security_non_number_syntax() -> None:
    area = _area()
    result = _interpret_aedit(_Session(area), _Builder(9), "security abc")
    assert result == "Syntax:  security [#xlevel]"
