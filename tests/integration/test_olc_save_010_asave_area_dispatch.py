"""OLC_SAVE-010 — `@asave area` dispatcher coverage for all editor types.

Mirrors ROM src/olc_save.c:1080-1128 (`cmd_asave` "area" branch). ROM
dispatches on `ch->desc->editor` across ED_AREA / ED_ROOM / ED_OBJECT /
ED_MOBILE / ED_HELP. Python previously only handled `redit` (ED_ROOM),
so aedit/oedit/medit/hedit users got "You are not editing an area" and
their changes were silently unsaveable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.commands.build import cmd_asave
from mud.models.area import Area
from mud.models.character import Character
from mud.models.constants import LEVEL_HERO
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.room import Room
from mud.net.session import Session
from mud.registry import area_registry, mob_registry, obj_registry, room_registry


@pytest.fixture
def builder_char():
    char = Character()
    char.name = "TestBuilder"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 9})()
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return char


@pytest.fixture
def test_area(tmp_path: Path):
    area = Area(
        vnum=900,
        name="OLC_SAVE-010 Area",
        file_name="olc_save_010_test.are",
        min_vnum=9000,
        max_vnum=9099,
        security=5,
        builders="TestBuilder",
        changed=True,
    )
    area_registry[900] = area
    yield area
    area_registry.pop(900, None)


@pytest.fixture(autouse=True)
def _chdir_tmp(monkeypatch, tmp_path):
    """`cmd_asave area` writes via save_area_to_json which writes into
    the cwd `area/` tree. Redirect to tmp_path to keep tests hermetic."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "area").mkdir()
    return tmp_path


def test_asave_area_dispatches_aedit_session(builder_char, test_area):
    """ED_AREA → save the area pointed at by editor_state['area']."""
    builder_char.desc.editor = "aedit"
    builder_char.desc.editor_state = {"area": test_area}

    result = cmd_asave(builder_char, "area")

    assert "saved" in result.lower()
    assert "OLC_SAVE-010 Area" in result


def test_asave_area_dispatches_oedit_session(builder_char, test_area):
    """ED_OBJECT → save obj_proto.area."""
    obj = ObjIndex(vnum=9001, name="x", short_descr="x", area=test_area)
    obj_registry[9001] = obj
    try:
        builder_char.desc.editor = "oedit"
        builder_char.desc.editor_state = {"obj_proto": obj}

        result = cmd_asave(builder_char, "area")

        assert "saved" in result.lower()
        assert "OLC_SAVE-010 Area" in result
    finally:
        obj_registry.pop(9001, None)


def test_asave_area_dispatches_medit_session(builder_char, test_area):
    """ED_MOBILE → save mob_proto.area."""
    mob = MobIndex(vnum=9002, short_descr="x", area=test_area)
    mob_registry[9002] = mob
    try:
        builder_char.desc.editor = "medit"
        builder_char.desc.editor_state = {"mob_proto": mob}

        result = cmd_asave(builder_char, "area")

        assert "saved" in result.lower()
        assert "OLC_SAVE-010 Area" in result
    finally:
        mob_registry.pop(9002, None)


def test_asave_area_dispatches_redit_session(builder_char, test_area):
    """ED_ROOM still works (regression guard)."""
    room = Room(vnum=9003, name="r", area=test_area)
    room_registry[9003] = room
    try:
        builder_char.desc.editor = "redit"
        builder_char.desc.editor_state = {"room": room}

        result = cmd_asave(builder_char, "area")

        assert "saved" in result.lower()
        assert "OLC_SAVE-010 Area" in result
    finally:
        room_registry.pop(9003, None)


def test_asave_area_hedit_emits_help_save_marker(builder_char, test_area):
    """ED_HELP → ROM calls save_other_helps. OLC_SAVE-009 covers the
    actual help-save port; here we only verify the dispatcher reaches
    the help branch and emits the ROM-faithful 'Grabando area :' prefix
    rather than falling through to the redit error."""
    builder_char.desc.editor = "hedit"
    builder_char.desc.editor_state = {"help": object()}

    result = cmd_asave(builder_char, "area")

    assert "Grabando area" in result


def test_asave_area_no_editor_returns_rom_error(builder_char):
    """ED_NONE → ROM 'You are not editing an area, therefore an area
    vnum is required.'"""
    builder_char.desc.editor = None

    result = cmd_asave(builder_char, "area")

    assert "not editing an area" in result.lower()
