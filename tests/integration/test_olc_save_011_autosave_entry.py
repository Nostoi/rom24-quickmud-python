"""OLC_SAVE-011 — `cmd_asave(None, "world")` autosave entry path.

Mirrors ROM src/olc_save.c:931-936 — `if (!ch) sec = 9` lets the
autosave timer fire `do_asave(NULL, "world")` and persist every area
regardless of builder. Python previously typed `cmd_asave(char, args)`
with `char: Character` (non-null) and `_is_builder(None, area)`
returns False, so a NULL-ch autosave would either crash on attribute
access or save zero areas.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.commands.build import cmd_asave
from mud.models.area import Area
from mud.registry import area_registry


@pytest.fixture(autouse=True)
def _chdir_tmp(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "areas").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def two_areas():
    a1 = Area(
        vnum=901,
        name="Area One",
        file_name="autosave_one.are",
        min_vnum=9100,
        max_vnum=9109,
        security=5,
        builders="None",
        changed=True,
    )
    a2 = Area(
        vnum=902,
        name="Area Two",
        file_name="autosave_two.are",
        min_vnum=9110,
        max_vnum=9119,
        security=5,
        builders="None",
        changed=True,
    )
    area_registry[901] = a1
    area_registry[902] = a2
    yield a1, a2
    area_registry.pop(901, None)
    area_registry.pop(902, None)


def test_autosave_world_with_null_char_saves_every_area(two_areas, tmp_path: Path):
    """ROM autosave: `do_asave(NULL, "world")` walks every area
    skipping the IS_BUILDER gate. Both 'None'-builder areas must save."""
    result = cmd_asave(None, "world")

    assert (tmp_path / "data" / "areas" / "autosave_one.json").exists()
    assert (tmp_path / "data" / "areas" / "autosave_two.json").exists()
    assert result == ""  # `if (ch) send_to_char(...)`; null-ch is silent


def test_autosave_world_with_null_char_does_not_crash_on_no_areas():
    """No registered areas → no crash, empty silent return."""
    saved = dict(area_registry)
    area_registry.clear()
    try:
        result = cmd_asave(None, "world")
        assert result == ""
    finally:
        area_registry.update(saved)


def test_autosave_world_player_path_still_returns_message(two_areas):
    """Regression: real player still gets the success message."""
    from mud.models.character import Character
    from mud.models.constants import LEVEL_HERO
    from mud.net.session import Session

    char = Character()
    char.name = "Builder"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 9})()

    char.is_npc = False
    char.desc = Session(name=char.name, character=char, reader=None, connection=None)

    result = cmd_asave(char, "world")
    assert "saved the world" in result.lower()
