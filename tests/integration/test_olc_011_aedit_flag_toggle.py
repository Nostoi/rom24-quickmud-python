"""OLC-011 — ``aedit`` flag-toggle prefix.

ROM reference: src/olc.c:443-449.

Inside an active ``aedit`` session, typing a bare flag name (e.g. ``changed``,
``added``, ``loading``) must toggle that bit on ``pArea->area_flags`` and
send ``"Flag toggled.\n\r"`` — mirroring ROM::

    if ((value = flag_value(area_flags, command)) != NO_FLAG)
    {
        TOGGLE_BIT(pArea->area_flags, value);
        send_to_char("Flag toggled.\\n\\r", ch);
        return;
    }

This check happens **before** the aedit_table[] dispatch and **after** the
``done`` / empty-input guards, so it must not shadow real subcommands.
"""

from __future__ import annotations

from mud.commands.build import _interpret_aedit
from mud.models.constants import AreaFlag, LEVEL_HERO
from mud.net.session import Session
from mud.world import create_test_character, initialize_world


def setup_module(module):
    initialize_world("area/area.lst")


def _builder_in_aedit(area_vnum: int = 3000):
    char = create_test_character("Builder", 3001)
    char.level = LEVEL_HERO
    char.is_admin = True
    char.pcdata.security = 9
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    session.editor = "aedit"
    from mud.registry import area_registry
    area = area_registry.get(area_vnum)
    if area is None:
        # pick any available area
        area = next(iter(area_registry.values()))
    session.editor_state = {"area": area}
    return char, session, area


# ── Flag toggled on (bit was clear) ─────────────────────────────────────────

def test_typing_loading_flag_name_toggles_bit():
    """``loading`` typed in aedit session toggles AREA_LOADING on area_flags.

    # mirrors ROM src/olc.c:443-449 — flag_value(area_flags, command) != NO_FLAG
    """
    char, session, area = _builder_in_aedit()
    original_flags = area.area_flags
    # ensure LOADING is clear before toggle
    area.area_flags = area.area_flags & ~int(AreaFlag.LOADING)

    result = _interpret_aedit(session, char, "loading")

    assert "Flag toggled" in result, f"Expected 'Flag toggled' in result, got: {result!r}"
    assert area.area_flags & int(AreaFlag.LOADING), "AREA_LOADING should be set after toggle"

    # restore
    area.area_flags = original_flags


def test_typing_added_flag_name_toggles_bit():
    """``added`` typed in aedit session toggles AREA_ADDED.

    # mirrors ROM src/olc.c:443-449
    """
    char, session, area = _builder_in_aedit()
    original_flags = area.area_flags
    area.area_flags = area.area_flags & ~int(AreaFlag.ADDED)

    result = _interpret_aedit(session, char, "added")

    assert "Flag toggled" in result
    assert area.area_flags & int(AreaFlag.ADDED)

    area.area_flags = original_flags


# ── Toggle off (bit was set) ─────────────────────────────────────────────────

def test_toggling_already_set_flag_clears_it():
    """TOGGLE_BIT clears the flag if it was already set.

    # mirrors ROM src/olc.c:446 — TOGGLE_BIT(pArea->area_flags, value)
    """
    char, session, area = _builder_in_aedit()
    original_flags = area.area_flags
    area.area_flags = area.area_flags | int(AreaFlag.LOADING)

    result = _interpret_aedit(session, char, "loading")

    assert "Flag toggled" in result
    assert not (area.area_flags & int(AreaFlag.LOADING)), "AREA_LOADING should be cleared after second toggle"

    area.area_flags = original_flags


# ── Prefix matching via flag_value ────────────────────────────────────────────

def test_prefix_load_matches_loading():
    """``load`` is a prefix of ``loading``; flag_value must match via prefix_lookup.

    # mirrors ROM src/bit.c:111-142 — flag_lookup does str_prefix matching
    """
    char, session, area = _builder_in_aedit()
    original_flags = area.area_flags
    area.area_flags = area.area_flags & ~int(AreaFlag.LOADING)

    result = _interpret_aedit(session, char, "load")

    assert "Flag toggled" in result, f"Prefix 'load' should match 'loading', got: {result!r}"
    assert area.area_flags & int(AreaFlag.LOADING)

    area.area_flags = original_flags


# ── Flag toggle does NOT shadow real subcommands ─────────────────────────────

def test_show_command_not_shadowed_by_flag_toggle():
    """``show`` is not an area_flags name; it must dispatch to aedit_show, not flag-toggle.

    # mirrors ROM src/olc.c: flag check comes before table dispatch,
    # but 'show' is not in area_flags so flag_value returns NO_FLAG.
    """
    char, session, area = _builder_in_aedit()
    result = _interpret_aedit(session, char, "show")
    # should return area display info, not "Flag toggled"
    assert "Flag toggled" not in result


def test_done_command_not_shadowed():
    """``done`` must exit the editor, not flag-toggle.

    # mirrors ROM src/olc.c:433-436 — done check is before flag_value check.
    """
    char, session, area = _builder_in_aedit()
    result = _interpret_aedit(session, char, "done")
    assert "Flag toggled" not in result
    assert session.editor is None or session.editor != "aedit" or session.editor_state is None or "area" not in (session.editor_state or {})


def test_name_command_not_shadowed():
    """``name`` is an aedit_table command, not an area flag; must not trigger flag-toggle."""
    char, session, area = _builder_in_aedit()
    result = _interpret_aedit(session, char, "name TestAreaName")
    assert "Flag toggled" not in result
