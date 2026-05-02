"""Integration tests for MPEDIT-003: MprogCode model + registry infrastructure.

Mirrors ROM src/olc_mpcode.c MPROG_CODE linked-list / recycle.c new_mpcode().
"""
from __future__ import annotations

import pytest

from mud.models.mob import MprogCode, mprog_code_registry, get_mprog_index


@pytest.fixture(autouse=True)
def clear_registry():
    """Ensure registry is clean before and after each test."""
    mprog_code_registry.clear()
    yield
    mprog_code_registry.clear()


# ---------------------------------------------------------------------------
# MprogCode model
# ---------------------------------------------------------------------------

def test_mprog_code_has_vnum_and_code():
    """MprogCode stores vnum and code — mirrors ROM MPROG_CODE fields."""
    m = MprogCode(vnum=1234, code="say Hello!\n")
    assert m.vnum == 1234
    assert m.code == "say Hello!\n"


def test_mprog_code_default_code_is_empty_string():
    """new_mpcode() in ROM zero-initialises code → Python default is ''."""
    m = MprogCode(vnum=99)
    assert m.code == ""


# ---------------------------------------------------------------------------
# Registry / get_mprog_index
# ---------------------------------------------------------------------------

def test_get_mprog_index_returns_none_when_missing():
    """get_mprog_index returns None for unknown vnum — mirrors ROM NULL return."""
    assert get_mprog_index(9999) is None


def test_get_mprog_index_returns_entry_after_insert():
    """After inserting into registry, get_mprog_index finds it."""
    m = MprogCode(vnum=500)
    mprog_code_registry[500] = m
    found = get_mprog_index(500)
    assert found is m


def test_registry_supports_multiple_entries():
    """Registry holds multiple independent entries by vnum."""
    m1 = MprogCode(vnum=100, code="say one")
    m2 = MprogCode(vnum=200, code="say two")
    mprog_code_registry[100] = m1
    mprog_code_registry[200] = m2
    assert get_mprog_index(100) is m1
    assert get_mprog_index(200) is m2


def test_registry_overwrite_replaces_entry():
    """Inserting a new MprogCode at an existing vnum replaces the old one."""
    old = MprogCode(vnum=300, code="old")
    new = MprogCode(vnum=300, code="new")
    mprog_code_registry[300] = old
    mprog_code_registry[300] = new
    assert get_mprog_index(300) is new
