"""OLC_ACT-005 — `oedit create <vnum>` subcommand.

Mirrors ROM `src/olc_act.c:3178-3225` (`oedit_create`) and `src/mem.c:297-335`
(`new_obj_index` defaults). Verifies the explicit `create` keyword path with
ROM's full validation chain: vnum required → area assignment → builder
security → already-exists check → ROM defaults applied.
"""

from __future__ import annotations

import pytest

from mud.commands.build import cmd_oedit
from mud.models.area import Area
from mud.models.constants import LEVEL_HERO
from mud.models.obj import ObjIndex, obj_index_registry
from mud.net.session import Session
from mud.registry import area_registry


@pytest.fixture(autouse=True)
def _clean_registries():
    area_snap = dict(area_registry)
    obj_snap = dict(obj_index_registry)
    area_registry.clear()
    obj_index_registry.clear()
    yield
    area_registry.clear()
    area_registry.update(area_snap)
    obj_index_registry.clear()
    obj_index_registry.update(obj_snap)


@pytest.fixture
def builder_area():
    area = Area(
        vnum=1,
        name="Builder Area",
        file_name="builder.are",
        min_vnum=1000,
        max_vnum=1099,
        security=5,
        builders="testbuilder",
    )
    area_registry[1] = area
    return area


@pytest.fixture
def builder_char(builder_area):
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


@pytest.fixture
def non_builder_char(builder_area):
    from mud.models.character import Character

    char = Character()
    char.name = "Visitor"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 0})()

    char.is_npc = False
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return char


def test_oedit_create_requires_vnum(builder_char):
    # mirrors ROM src/olc_act.c:3186-3190 — empty argument or 0 → syntax message.
    result = cmd_oedit(builder_char, "create")
    assert result == "Syntax:  oedit create [vnum]\n\r"


def test_oedit_create_zero_vnum_rejected(builder_char):
    # mirrors ROM src/olc_act.c:3186 — `value == 0` matches the empty branch.
    result = cmd_oedit(builder_char, "create 0")
    assert result == "Syntax:  oedit create [vnum]\n\r"


def test_oedit_create_unassigned_vnum_rejected(builder_char):
    # mirrors ROM src/olc_act.c:3192-3197 — vnum outside any area.
    result = cmd_oedit(builder_char, "create 5000")
    assert result == "OEdit:  That vnum is not assigned an area.\n\r"


def test_oedit_create_non_builder_rejected(non_builder_char):
    # mirrors ROM src/olc_act.c:3199-3203 — IS_BUILDER security gate.
    result = cmd_oedit(non_builder_char, "create 1050")
    assert result == "OEdit:  Vnum in an area you cannot build in.\n\r"


def test_oedit_create_existing_vnum_rejected(builder_char):
    # mirrors ROM src/olc_act.c:3205-3209 — already-exists.
    obj_index_registry[1050] = ObjIndex(vnum=1050)
    result = cmd_oedit(builder_char, "create 1050")
    assert result == "OEdit:  Object vnum already exists.\n\r"


def test_oedit_create_returns_rom_message(builder_char):
    # mirrors ROM src/olc_act.c:3223 — verbatim "Object Created.\n\r".
    result = cmd_oedit(builder_char, "create 1050")
    assert result == "Object Created.\n\r"


def test_oedit_create_registers_proto(builder_char):
    cmd_oedit(builder_char, "create 1050")
    assert 1050 in obj_index_registry
    proto = obj_index_registry[1050]
    assert isinstance(proto, ObjIndex)
    assert proto.vnum == 1050


def test_oedit_create_uses_rom_defaults(builder_char, builder_area):
    cmd_oedit(builder_char, "create 1050")
    proto = obj_index_registry[1050]
    # mirrors ROM src/mem.c:313-332 — new_obj_index defaults.
    assert proto.name == "no name"
    assert proto.short_descr == "(no short description)"
    assert proto.description == "(no description)"
    assert proto.material == "unknown"
    assert proto.item_type == "trash"
    assert proto.extra_flags == 0
    assert proto.wear_flags == 0
    assert proto.weight == 0
    assert proto.cost == 0
    assert proto.value == [0, 0, 0, 0, 0]
    assert proto.new_format is True
    assert proto.area is builder_area


def test_oedit_create_descriptor_edits_new_proto(builder_char):
    cmd_oedit(builder_char, "create 1050")
    session = builder_char.desc
    # mirrors ROM src/olc_act.c:3221 — `ch->desc->pEdit = pObj`.
    assert session.editor == "oedit"
    assert session.editor_state.get("obj_proto") is obj_index_registry[1050]


def test_oedit_create_in_session_dispatches(builder_char):
    # `create <vnum>` typed inside an active oedit session also creates
    # and switches the edit target (mirrors ROM oedit_table dispatch).
    cmd_oedit(builder_char, "create 1050")
    assert builder_char.desc.editor == "oedit"
    cmd_oedit(builder_char, "create 1051")
    assert 1051 in obj_index_registry
    assert builder_char.desc.editor_state.get("obj_proto") is obj_index_registry[1051]


def test_oedit_unknown_vnum_no_longer_auto_creates(builder_char):
    # mirrors ROM dispatcher — `@oedit <unknown_vnum>` without explicit
    # `create` keyword must NOT auto-create. Pre-fix Python silently created
    # any unknown vnum; ROM requires the explicit `create` subcommand.
    result = cmd_oedit(builder_char, "1050")
    assert 1050 not in obj_index_registry
    assert "does not exist" in result.lower() or "create" in result.lower()
