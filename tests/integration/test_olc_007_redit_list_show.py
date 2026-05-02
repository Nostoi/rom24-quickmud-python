"""OLC-007 — ``redit`` mlist / rlist / olist / mshow / oshow subcommands.

ROM reference: src/olc_act.c:329-570, src/olc.c:242-279.

Five subcommands are present in ``redit_table[]`` but not dispatched from
``_interpret_redit``:

- ``rlist``  — list all rooms in area  (src/olc_act.c:329-371)
- ``mlist``  — list mobs in area by name/all  (src/olc_act.c:374-428)
- ``olist``  — list objects in area by name/type/all  (src/olc_act.c:431-486)
- ``mshow``  — show mob proto given vnum  (src/olc_act.c:489-523)
- ``oshow``  — show obj proto given vnum  (src/olc_act.c:525-569)
"""

from __future__ import annotations

from mud.commands.build import _interpret_redit
from mud.models.constants import LEVEL_HERO
from mud.net.session import Session
from mud.world import create_test_character, initialize_world
from mud.registry import room_registry, mob_registry, obj_registry


def setup_module(module):
    initialize_world("area/area.lst")


def _builder_in_redit(room_vnum: int = 3001):
    char = create_test_character("Builder", room_vnum)
    char.level = LEVEL_HERO
    char.is_admin = True
    char.pcdata.security = 9
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    session.editor = "redit"
    room = room_registry.get(room_vnum)
    if room is None:
        room = next(iter(room_registry.values()))
    session.editor_state = {"room": room}
    return char, session, room


# ── rlist ────────────────────────────────────────────────────────────────────

def test_rlist_returns_room_entries():
    """``rlist`` lists rooms in the current area with [vnum] name columns.

    # mirrors ROM src/olc_act.c:329-371 — redit_rlist
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "rlist")
    assert "Room(s) not found" not in result or len(result) > 0
    # should contain at least one bracketed vnum
    assert "[" in result, f"Expected vnum listing in rlist output, got: {result!r}"


def test_rlist_no_args_still_works():
    """``rlist`` requires no argument — scans current area automatically.

    # mirrors ROM src/olc_act.c:343 — pArea = ch->in_room->area
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "rlist")
    # should NOT return "Unknown room editor command"
    assert "Unknown room editor command" not in result


# ── mlist ────────────────────────────────────────────────────────────────────

def test_mlist_requires_argument():
    """``mlist`` without argument returns syntax hint.

    # mirrors ROM src/olc_act.c:385-388 — if arg[0] == '\0' → syntax
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "mlist")
    assert "Syntax" in result or "syntax" in result or "mlist" in result.lower(), \
        f"Expected syntax hint for bare mlist, got: {result!r}"


def test_mlist_all_returns_listing_or_not_found():
    """``mlist all`` returns all mobs in area or 'not found' message.

    # mirrors ROM src/olc_act.c:395 — fAll = !str_cmp(arg, "all")
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "mlist all")
    assert "Unknown room editor command" not in result
    # either a list with vnums or a "not found" message
    assert "[" in result or "not found" in result.lower(), \
        f"Expected mob listing or not-found, got: {result!r}"


def test_mlist_unknown_name_returns_not_found():
    """``mlist <name>`` with no matching mob returns 'Mobile(s) not found'.

    # mirrors ROM src/olc_act.c:413-416 — if !found → send 'not found'
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "mlist xyzzy_no_mob_ever")
    assert "not found" in result.lower(), f"Expected 'not found', got: {result!r}"


# ── olist ────────────────────────────────────────────────────────────────────

def test_olist_requires_argument():
    """``olist`` without argument returns syntax hint.

    # mirrors ROM src/olc_act.c:443-446 — if arg[0] == '\0' → syntax
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "olist")
    assert "Syntax" in result or "syntax" in result or "olist" in result.lower(), \
        f"Expected syntax hint for bare olist, got: {result!r}"


def test_olist_all_returns_listing_or_not_found():
    """``olist all`` returns all objects in area or 'not found' message.

    # mirrors ROM src/olc_act.c:452 — fAll = !str_cmp(arg, "all")
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "olist all")
    assert "Unknown room editor command" not in result
    assert "[" in result or "not found" in result.lower(), \
        f"Expected obj listing or not-found, got: {result!r}"


def test_olist_unknown_name_returns_not_found():
    """``olist <name>`` with no match returns 'Object(s) not found'.

    # mirrors ROM src/olc_act.c:473-476
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "olist xyzzy_no_obj_ever")
    assert "not found" in result.lower(), f"Expected 'not found', got: {result!r}"


# ── mshow ────────────────────────────────────────────────────────────────────

def test_mshow_requires_argument():
    """``mshow`` without vnum returns syntax hint.

    # mirrors ROM src/olc_act.c:495-498 — if argument[0] == '\0' → syntax
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "mshow")
    assert "Syntax" in result or "syntax" in result or "mshow" in result.lower(), \
        f"Expected syntax hint, got: {result!r}"


def test_mshow_nonexistent_vnum_returns_error():
    """``mshow 99999`` with no matching mob returns error message.

    # mirrors ROM src/olc_act.c:507-510 — if !pMob → 'does not exist'
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "mshow 99999")
    assert "does not exist" in result.lower() or "not exist" in result.lower(), \
        f"Expected 'does not exist', got: {result!r}"


def test_mshow_nonnumeric_returns_error():
    """``mshow foo`` (non-numeric) returns REdit error.

    # mirrors ROM src/olc_act.c:500-503 — if !is_number → 'Must be a number'
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "mshow foo")
    assert "number" in result.lower(), f"Expected 'number' error, got: {result!r}"


def test_mshow_valid_vnum_returns_mob_info():
    """``mshow <vnum>`` for an existing mob returns its stats block.

    # mirrors ROM src/olc_act.c:511-515 — calls medit_show
    """
    char, session, room = _builder_in_redit()
    # find a real mob vnum in the registry
    if not mob_registry:
        return  # skip if no mobs loaded
    vnum = next(iter(mob_registry))
    result = _interpret_redit(session, char, f"mshow {vnum}")
    assert "Unknown room editor command" not in result
    # medit_show output should contain Name or Vnum label
    assert "Name" in result or "Vnum" in result or "vnum" in result.lower(), \
        f"Expected mob stats in mshow output, got: {result!r}"


# ── oshow ────────────────────────────────────────────────────────────────────

def test_oshow_requires_argument():
    """``oshow`` without vnum returns syntax hint.

    # mirrors ROM src/olc_act.c:531-534
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "oshow")
    assert "Syntax" in result or "syntax" in result or "oshow" in result.lower(), \
        f"Expected syntax hint, got: {result!r}"


def test_oshow_nonexistent_vnum_returns_error():
    """``oshow 99999`` with no matching object returns error.

    # mirrors ROM src/olc_act.c:543-546
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "oshow 99999")
    assert "does not exist" in result.lower() or "not exist" in result.lower(), \
        f"Expected 'does not exist', got: {result!r}"


def test_oshow_nonnumeric_returns_error():
    """``oshow bar`` (non-numeric) returns error.

    # mirrors ROM src/olc_act.c:536-539
    """
    char, session, room = _builder_in_redit()
    result = _interpret_redit(session, char, "oshow bar")
    assert "number" in result.lower(), f"Expected 'number' error, got: {result!r}"


def test_oshow_valid_vnum_returns_obj_info():
    """``oshow <vnum>`` for an existing object returns its stats block.

    # mirrors ROM src/olc_act.c:547-551 — calls oedit_show
    """
    char, session, room = _builder_in_redit()
    if not obj_registry:
        return
    vnum = next(iter(obj_registry))
    result = _interpret_redit(session, char, f"oshow {vnum}")
    assert "Unknown room editor command" not in result
    assert "Name" in result or "Vnum" in result or "vnum" in result.lower(), \
        f"Expected obj stats in oshow output, got: {result!r}"
