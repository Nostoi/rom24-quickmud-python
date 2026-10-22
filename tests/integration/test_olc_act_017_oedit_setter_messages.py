"""OLC_ACT-017: oedit level/weight/cost/material match ROM's exact messages.

ROM src/olc_act.c:3140-3157 (oedit_weight), :3158-3177 (oedit_cost),
:3451-3469 (oedit_material), :3470-3488 (oedit_level):
  - numeric setters reject empty OR non-number with the single verbatim string
    `"Syntax:  X [number]\\n\\r"` (note the DOUBLE space after the colon);
  - material rejects only empty with `"Syntax:  material [string]\\n\\r"`;
  - all emit a BARE success string with NO value echoed
    (`"Level set."` / `"Weight set."` / `"Cost set."` / `"Material set."`);
  - ROM `is_number`/`atoi` accept a leading `-`, so a NEGATIVE object level is
    valid (Python's non-ROM `level >= 0` guard is removed).

Python previously used English placeholders (`"Usage: ..."`,
`"... must be a number."`), leaked the value (`"... set to {n}."`), and
rejected negative levels.
"""

from __future__ import annotations

from mud.commands.build import _interpret_oedit
from mud.models.area import Area
from mud.models.obj import ObjIndex


class _StubChar:
    name = "Tester"
    pcdata = type("PC", (), {"security": 9})()


class _StubSession:
    def __init__(self, proto: ObjIndex) -> None:
        self.editor = "obj_proto"
        self.editor_state = {"obj_proto": proto}


def _session() -> tuple[_StubSession, ObjIndex]:
    proto = ObjIndex(vnum=2000, name="thing")
    proto.area = Area(vnum=20, name="A", builders="Tester")
    return _StubSession(proto), proto


def test_oedit_weight_bare_success_and_syntax() -> None:
    session, proto = _session()
    assert _interpret_oedit(session, _StubChar(), "weight 15") == "Weight set."
    assert proto.weight == 15
    assert _interpret_oedit(session, _StubChar(), "weight abc") == "Syntax:  weight [number]"
    assert _interpret_oedit(session, _StubChar(), "weight") == "Syntax:  weight [number]"


def test_oedit_cost_bare_success_and_syntax() -> None:
    session, proto = _session()
    assert _interpret_oedit(session, _StubChar(), "cost 500") == "Cost set."
    assert proto.cost == 500
    assert _interpret_oedit(session, _StubChar(), "cost x") == "Syntax:  cost [number]"


def test_oedit_level_bare_success_and_allows_negative() -> None:
    session, proto = _session()
    assert _interpret_oedit(session, _StubChar(), "level 20") == "Level set."
    assert proto.level == 20
    # ROM is_number/atoi accept a leading '-' → negative level is valid.
    assert _interpret_oedit(session, _StubChar(), "level -3") == "Level set."
    assert proto.level == -3
    assert _interpret_oedit(session, _StubChar(), "level abc") == "Syntax:  level [number]"


def test_oedit_material_bare_success_and_syntax() -> None:
    session, proto = _session()
    assert _interpret_oedit(session, _StubChar(), "material steel") == "Material set."
    assert proto.material == "steel"
    assert _interpret_oedit(session, _StubChar(), "material") == "Syntax:  material [string]"
