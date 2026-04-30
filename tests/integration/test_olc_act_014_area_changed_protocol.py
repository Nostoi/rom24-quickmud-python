"""OLC_ACT-014 — every OLC builder mutation marks its area as changed.

ROM `src/olc.c:452-463`/`:510-521` and friends use a return-value protocol:
each subcommand handler returns `TRUE` on a state mutation, and the editor
dispatcher then `SET_BIT (pArea->area_flags, AREA_CHANGED)`. Python uses an
imperative pattern instead — each `_interpret_*edit` branch sets
`area.changed = True` directly via `_mark_area_changed(room)` or a direct
assignment after the mutation lands.

The structural divergence is intentional and documented in
`docs/parity/OLC_ACT_C_AUDIT.md` (OLC_ACT-014). These tests lock the
invariant for one representative mutation per editor (the `name`
subcommand from OLC_ACT-011) so a future builder added without the
imperative `area.changed = True` call surfaces here as a regression
instead of as silent missed `.are` writes.
"""

from __future__ import annotations

from mud.commands.build import (
    _interpret_aedit,
    _interpret_medit,
    _interpret_oedit,
    _interpret_redit,
)
from mud.models.area import Area
from mud.models.constants import ActFlag
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.room import Room


class _StubChar:
    name = "Tester"
    pcdata = type("PC", (), {"security": 9})()


class _StubSession:
    def __init__(self, state_key: str, value) -> None:
        self.editor = state_key
        self.editor_state = {state_key: value}


def test_aedit_name_marks_area_changed() -> None:
    area = Area(vnum=10, name="Old", security=1, builders="Tester")
    area.changed = False
    session = _StubSession("area", area)
    _interpret_aedit(session, _StubChar(), "name New Name")
    assert area.changed is True


def test_redit_name_marks_area_changed() -> None:
    area = Area(vnum=42, name="A", builders="Tester")
    area.changed = False
    room = Room(vnum=4200, name="Old Room")
    room.area = area
    session = _StubSession("room", room)
    _interpret_redit(session, _StubChar(), "name A Better Name")
    assert area.changed is True


def test_oedit_name_marks_area_changed() -> None:
    area = Area(vnum=20, name="A", builders="Tester")
    area.changed = False
    proto = ObjIndex(vnum=2000, name="old keywords")
    proto.area = area
    session = _StubSession("obj_proto", proto)
    _interpret_oedit(session, _StubChar(), "name sword weapon blade")
    assert area.changed is True


def test_medit_name_marks_area_changed() -> None:
    area = Area(vnum=30, name="A", builders="Tester")
    area.changed = False
    proto = MobIndex(vnum=3000)
    proto.player_name = "old"
    proto.area = area
    proto.act_flags = int(ActFlag.IS_NPC)
    session = _StubSession("mob_proto", proto)
    _interpret_medit(session, _StubChar(), "name guard soldier")
    assert area.changed is True


def test_aedit_security_marks_area_changed() -> None:
    """Second representative subcommand (non-name) per editor — ensures the
    invariant covers more than just the *_name path."""
    area = Area(vnum=11, name="Old", security=1, builders="Tester")
    area.changed = False
    session = _StubSession("area", area)
    _interpret_aedit(session, _StubChar(), "security 5")
    assert area.changed is True


def test_aedit_failed_mutation_does_not_mark_changed() -> None:
    """Mirrors ROM dispatch: handlers that return FALSE (no mutation) must
    not set AREA_CHANGED. Python equivalent: failed paths must not set
    `area.changed = True`. Here `security` with no arg returns a usage
    string and must be a no-op on `area.changed`."""
    area = Area(vnum=12, name="Old", security=1, builders="Tester")
    area.changed = False
    session = _StubSession("area", area)
    result = _interpret_aedit(session, _StubChar(), "security")
    assert "Usage" in result or "must be" in result
    assert area.changed is False
