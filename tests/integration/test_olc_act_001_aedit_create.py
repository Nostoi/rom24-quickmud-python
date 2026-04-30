"""OLC_ACT-001 — `aedit create` subcommand.

Mirrors ROM `src/olc_act.c:667-679` (`aedit_create`) and `src/mem.c:91-122`
(`new_area` defaults). Verifies that `cmd_aedit(char, "create")` allocates a
fresh `Area` with the ROM-default fields, registers it in `area_registry`,
sets the descriptor's edit pointer to the new area, sets the `AREA_ADDED`
bit, and returns the verbatim "Area Created.\\n\\r" message.
"""

from __future__ import annotations

import pytest

from mud.commands.build import cmd_aedit
from mud.models.area import Area
from mud.models.constants import LEVEL_HERO, AreaFlag
from mud.net.session import Session
from mud.registry import area_registry


@pytest.fixture
def builder_char():
    from mud.models.character import Character

    char = Character()
    char.name = "TestBuilder"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 9})()

    char.is_npc = False
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return char


@pytest.fixture(autouse=True)
def _clean_area_registry():
    snapshot = dict(area_registry)
    area_registry.clear()
    yield
    area_registry.clear()
    area_registry.update(snapshot)


def test_aedit_create_returns_rom_message(builder_char):
    result = cmd_aedit(builder_char, "create")
    # mirrors ROM src/olc_act.c:677 — exact verbatim message with \n\r line ending.
    assert result == "Area Created.\n\r"


def test_aedit_create_registers_new_area(builder_char):
    assert len(area_registry) == 0
    cmd_aedit(builder_char, "create")
    assert len(area_registry) == 1


def test_aedit_create_uses_rom_defaults(builder_char):
    cmd_aedit(builder_char, "create")
    area = next(iter(area_registry.values()))
    # mirrors ROM src/mem.c:107-120 — `new_area()` defaults.
    assert area.name == "New area"
    assert area.builders == "None"
    assert area.security == 1
    assert area.min_vnum == 0
    assert area.max_vnum == 0
    assert area.age == 0
    assert area.nplayer == 0
    assert area.empty is True


def test_aedit_create_sets_area_added_flag(builder_char):
    cmd_aedit(builder_char, "create")
    area = next(iter(area_registry.values()))
    # mirrors ROM src/mem.c:110 + src/olc_act.c:676 — AREA_ADDED bit set.
    assert area.area_flags & int(AreaFlag.ADDED) != 0


def test_aedit_create_assigns_filename_from_vnum(builder_char):
    cmd_aedit(builder_char, "create")
    area = next(iter(area_registry.values()))
    # mirrors ROM src/mem.c:118-120 — filename derived from vnum (sprintf "area%d.are").
    assert area.file_name == f"area{area.vnum}.are"


def test_aedit_create_descriptor_edits_new_area(builder_char):
    cmd_aedit(builder_char, "create")
    # mirrors ROM src/olc_act.c:674 — `ch->desc->pEdit = (void *) pArea`.
    session = builder_char.desc
    assert isinstance(session, Session)
    assert session.editor == "aedit"
    edited = session.editor_state.get("area")
    assert isinstance(edited, Area)
    assert edited is next(iter(area_registry.values()))


def test_aedit_create_assigns_unique_vnums(builder_char):
    cmd_aedit(builder_char, "create")
    cmd_aedit(builder_char, "create")
    cmd_aedit(builder_char, "create")
    vnums = [a.vnum for a in area_registry.values()]
    assert len(vnums) == 3
    assert len(set(vnums)) == 3  # all unique


def test_aedit_create_no_existing_session_required(builder_char):
    # mirrors ROM `aedit create` — the create path is reachable from the
    # entry-point `aedit create` form (before any session is open).
    session = builder_char.desc
    assert session.editor != "aedit"  # no prior session
    result = cmd_aedit(builder_char, "create")
    assert result == "Area Created.\n\r"
    assert session.editor == "aedit"


def test_aedit_create_existing_session_uses_dispatcher(builder_char):
    # When already in an aedit session, `create` typed inside the editor
    # should still create a new area and switch the edit target (matches
    # ROM dispatch via aedit_table at src/olc.c:222).
    cmd_aedit(builder_char, "create")
    first_area = next(iter(area_registry.values()))
    session = builder_char.desc
    assert session.editor_state.get("area") is first_area

    cmd_aedit(builder_char, "create")
    assert len(area_registry) == 2
    new_area = [a for a in area_registry.values() if a is not first_area][0]
    assert session.editor_state.get("area") is new_area
