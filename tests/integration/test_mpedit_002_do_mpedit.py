"""Integration tests for MPEDIT-002: do_mpedit entry command.

Mirrors ROM src/olc_mpcode.c:96-151 do_mpedit().
"""
from __future__ import annotations

import pytest

from mud.models.mob import MprogCode, mprog_code_registry


@pytest.fixture(autouse=True)
def clear_registry():
    mprog_code_registry.clear()
    yield
    mprog_code_registry.clear()


# ---------------------------------------------------------------------------
# No args → syntax
# ---------------------------------------------------------------------------

def test_do_mpedit_no_args_returns_syntax(movable_char_factory):
    from mud.commands.imm_olc import do_mpedit
    char = movable_char_factory("builder", 1)
    result = do_mpedit(char, "")
    assert "mpedit" in result.lower() or "sintaxis" in result.lower() or "syntax" in result.lower()


# ---------------------------------------------------------------------------
# Non-numeric arg (not "create") → double syntax lines
# ---------------------------------------------------------------------------

def test_do_mpedit_non_numeric_returns_syntax(movable_char_factory):
    from mud.commands.imm_olc import do_mpedit
    char = movable_char_factory("builder", 1)
    result = do_mpedit(char, "abc")
    assert "mpedit" in result.lower() or "sintaxis" in result.lower()


# ---------------------------------------------------------------------------
# Numeric vnum not in registry → error
# ---------------------------------------------------------------------------

def test_do_mpedit_vnum_not_exist(movable_char_factory):
    from mud.commands.imm_olc import do_mpedit
    char = movable_char_factory("builder", 1)
    result = do_mpedit(char, "9999")
    # ROM: "MPEdit : That vnum does not exist.\n\r"
    assert "does not exist" in result.lower() or "mpedit" in result.lower()


# ---------------------------------------------------------------------------
# Numeric vnum exists → opens mpedit session silently
# ---------------------------------------------------------------------------

def test_do_mpedit_vnum_exists_opens_session(movable_char_factory):
    from mud.commands.imm_olc import do_mpedit
    from mud.net.session import Session
    from mud.olc.editor_state import EditorMode
    from mud.registry import area_registry
    from mud.models.area import Area

    # Register a test area covering vnum 100
    test_area = Area(name="Test Area", min_vnum=100, max_vnum=199, security=9, builders="None")
    area_registry["test_mpedit_002"] = test_area
    try:
        char = movable_char_factory("builder", 1)
        if hasattr(char, "pcdata") and char.pcdata:
            char.pcdata.security = 10
        char.level = 60

        m = MprogCode(vnum=100, code="say hello")
        mprog_code_registry[100] = m

        session = Session(name="builder", character=char, reader=None, connection=None)
        char.desc = session

        result = do_mpedit(char, "100")
        # ROM: silent on success
        assert result == ""
        assert session.editor == "mpedit"
        assert session.editor_state.get("mpcode") is m
    finally:
        area_registry.pop("test_mpedit_002", None)


# ---------------------------------------------------------------------------
# "create" with no vnum arg → syntax
# ---------------------------------------------------------------------------

def test_do_mpedit_create_no_arg_returns_syntax(movable_char_factory):
    from mud.commands.imm_olc import do_mpedit
    char = movable_char_factory("builder", 1)
    result = do_mpedit(char, "create")
    assert "mpedit" in result.lower() or "sintaxis" in result.lower()


# ---------------------------------------------------------------------------
# "create" with existing vnum → error
# ---------------------------------------------------------------------------

def test_do_mpedit_create_existing_vnum_error(movable_char_factory):
    from mud.commands.imm_olc import do_mpedit
    char = movable_char_factory("builder", 1)
    if hasattr(char, "pcdata") and char.pcdata:
        char.pcdata.security = 10
    char.level = 60

    m = MprogCode(vnum=200, code="")
    mprog_code_registry[200] = m

    result = do_mpedit(char, "create 200")
    assert "already exists" in result.lower() or "mpedit" in result.lower()
