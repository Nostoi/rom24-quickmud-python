"""OLC_SAVE-014..017 — ``cmd_asave`` ROM-exact message strings.

ROM reference: src/olc_save.c

- OLC_SAVE-014: numeric-vnum branch is silent on success (src/olc_save.c:982-995)
- OLC_SAVE-015: "world" branch returns "You saved the world.\\n\\r" (src/olc_save.c:1013)
- OLC_SAVE-016: "changed" empty case returns "Saved zones:\\n\\r" + "None.\\n\\r" (src/olc_save.c:1059-1064)
- OLC_SAVE-017: "area" branch returns "Area saved.\\n\\r" (src/olc_save.c:1126)
"""
from __future__ import annotations

import pytest

from mud.commands.build import cmd_asave
from mud.models.area import Area
from mud.models.constants import LEVEL_HERO
from mud.models.room import Room
from mud.net.session import Session
from mud.registry import area_registry, room_registry
from mud.world import create_test_character, initialize_world


def setup_module(module):
    initialize_world("area/area.lst")


@pytest.fixture()
def builder_char(tmp_path):
    char = create_test_character("Builder", 3001)
    char.level = LEVEL_HERO
    char.is_npc = False
    char.is_admin = True
    if char.pcdata:
        char.pcdata.security = 9
    session = Session(name="Builder", character=char, reader=None, connection=None)
    char.desc = session
    return char


@pytest.fixture()
def test_area(tmp_path):
    area = Area(name="TestArea014", vnum=19001, min_vnum=19001, max_vnum=19100,
                file_name=str(tmp_path / "test_014.json"), builders="None", security=1)
    area_registry[19001] = area
    yield area
    area_registry.pop(19001, None)


# ── OLC_SAVE-014: numeric-vnum branch silent on success ──────────────────────

def test_asave_numeric_vnum_silent_on_success(builder_char, test_area, tmp_path):
    """ROM numeric-vnum asave returns nothing (silent) on success.

    ROM src/olc_save.c:982-995 — no ``send_to_char`` on success path.
    """
    result = cmd_asave(builder_char, str(test_area.vnum))
    # ROM is silent — empty string
    assert result == "", repr(result)


# ── OLC_SAVE-015: "world" branch exact message ───────────────────────────────

def test_asave_world_exact_message(builder_char):
    """ROM 'world' branch sends "You saved the world.\\n\\r".

    ROM src/olc_save.c:1013 — ``send_to_char("You saved the world.\\n\\r", ch)``.
    """
    result = cmd_asave(builder_char, "world")
    assert result == "You saved the world.\n\r", repr(result)


# ── OLC_SAVE-016: "changed" empty case ──────────────────────────────────────

def test_asave_changed_empty_sends_header_then_none(builder_char):
    """ROM 'changed' with nothing to save: 'Saved zones:\\n\\r' + 'None.\\n\\r'.

    ROM src/olc_save.c:1023-1064 — header always sent, then 'None.\\n\\r' fallback.
    """
    # Ensure no areas are marked changed for this builder
    for area in area_registry.values():
        area.changed = False

    result = cmd_asave(builder_char, "changed")
    assert result == "Saved zones:\n\rNone.\n\r", repr(result)


def test_asave_changed_saved_area_no_none_suffix(builder_char, test_area, tmp_path):
    """When areas ARE saved, header + rows emitted but NOT 'None.\\n\\r'.

    ROM src/olc_save.c:1059-1064 — 'None.\\n\\r' only if buf was never overwritten.
    """
    test_area.changed = True
    test_area.builders = "None"  # _is_builder passes for admin
    result = cmd_asave(builder_char, "changed")
    assert result.startswith("Saved zones:\n\r"), repr(result)
    assert "None.\n\r" not in result


# ── OLC_SAVE-017: "area" branch exact message ────────────────────────────────

def test_asave_area_exact_message(builder_char, test_area):
    """ROM 'area' branch sends "Area saved.\\n\\r".

    ROM src/olc_save.c:1126 — ``send_to_char("Area saved.\\n\\r", ch)``.
    """
    room = Room(vnum=19002, name="r", area=test_area)
    room_registry[19002] = room
    try:
        builder_char.desc.editor = "redit"
        builder_char.desc.editor_state = {"room": room}
        result = cmd_asave(builder_char, "area")
        assert result == "Area saved.\n\r", repr(result)
    finally:
        room_registry.pop(19002, None)
