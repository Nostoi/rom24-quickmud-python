"""OLC-008 — ``oedit`` missing subcommands: addaffect, addapply, delaffect, extra, wear.

ROM reference:
- oedit_addaffect  src/olc_act.c:2818-2858
- oedit_addapply   src/olc_act.c:2859-2925
- oedit_delaffect  src/olc_act.c:2926-2983
- oedit_extra      src/olc_act.c:3370-3393
- oedit_wear       src/olc_act.c:3394-3450
"""

from __future__ import annotations

from mud.commands.build import _interpret_oedit
from mud.models.constants import LEVEL_HERO, ExtraFlag, WearFlag
from mud.models.obj import Affect, ObjIndex
from mud.net.session import Session
from mud.world import create_test_character, initialize_world
from mud.registry import obj_registry


def setup_module(module):
    initialize_world("area/area.lst")


def _make_obj_proto(vnum: int = 50001) -> ObjIndex:
    proto = ObjIndex(vnum=vnum, name="test sword", short_descr="a test sword")
    proto.extra_flags = 0
    proto.wear_flags = 0
    proto.affected = []
    proto.level = 10
    return proto


def _builder_in_oedit(vnum: int = 50001):
    char = create_test_character("Builder", 3001)
    char.level = LEVEL_HERO
    char.is_admin = True
    char.pcdata.security = 9
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    session.editor = "oedit"
    proto = _make_obj_proto(vnum)
    session.editor_state = {"obj_proto": proto}
    return char, session, proto


# ── extra ────────────────────────────────────────────────────────────────────

def test_extra_toggle_sets_flag():
    """``extra glow`` toggles GLOW bit on extra_flags.

    # mirrors ROM src/olc_act.c:3370-3393 — oedit_extra
    """
    char, session, proto = _builder_in_oedit()
    proto.extra_flags = 0

    result = _interpret_oedit(session, char, "extra glow")

    assert "toggled" in result.lower() or "Extra flag toggled" in result, \
        f"Expected toggle confirmation, got: {result!r}"
    assert int(proto.extra_flags) & int(ExtraFlag.GLOW), \
        "GLOW bit should be set after extra glow"


def test_extra_toggle_clears_flag():
    """``extra glow`` twice clears the GLOW bit (TOGGLE_BIT).

    # mirrors ROM src/olc_act.c:3376 — TOGGLE_BIT(pObj->extra_flags, value)
    """
    char, session, proto = _builder_in_oedit()
    proto.extra_flags = int(ExtraFlag.GLOW)

    result = _interpret_oedit(session, char, "extra glow")

    assert "toggled" in result.lower() or "Extra flag toggled" in result
    assert not (int(proto.extra_flags) & int(ExtraFlag.GLOW)), \
        "GLOW bit should be cleared after second toggle"


def test_extra_no_arg_returns_syntax():
    """``extra`` with no arg returns syntax hint.

    # mirrors ROM src/olc_act.c:3388-3392
    """
    char, session, proto = _builder_in_oedit()
    result = _interpret_oedit(session, char, "extra")
    assert "Syntax" in result or "syntax" in result or "extra" in result.lower(), \
        f"Expected syntax hint, got: {result!r}"


def test_extra_invalid_flag_returns_syntax():
    """``extra xyzzy_not_a_flag`` returns syntax hint.

    # mirrors ROM src/olc_act.c:3386 — flag_value returns NO_FLAG → syntax
    """
    char, session, proto = _builder_in_oedit()
    result = _interpret_oedit(session, char, "extra xyzzy_not_a_flag")
    assert "Syntax" in result or "syntax" in result or "extra" in result.lower(), \
        f"Expected syntax hint, got: {result!r}"


# ── wear ─────────────────────────────────────────────────────────────────────

def test_wear_toggle_sets_flag():
    """``wear take`` toggles TAKE bit on wear_flags.

    # mirrors ROM src/olc_act.c:3394-3450 — oedit_wear
    """
    char, session, proto = _builder_in_oedit()
    proto.wear_flags = 0

    result = _interpret_oedit(session, char, "wear take")

    assert "toggled" in result.lower() or "Wear flag toggled" in result, \
        f"Expected toggle confirmation, got: {result!r}"
    assert int(proto.wear_flags) & int(WearFlag.TAKE), \
        "TAKE bit should be set after wear take"


def test_wear_toggle_clears_flag():
    """``wear take`` twice clears TAKE bit.

    # mirrors ROM src/olc_act.c:3402 — TOGGLE_BIT(pObj->wear_flags, value)
    """
    char, session, proto = _builder_in_oedit()
    proto.wear_flags = int(WearFlag.TAKE)

    result = _interpret_oedit(session, char, "wear take")

    assert "toggled" in result.lower() or "Wear flag toggled" in result
    assert not (int(proto.wear_flags) & int(WearFlag.TAKE)), \
        "TAKE bit should be cleared after second toggle"


def test_wear_no_arg_returns_syntax():
    """``wear`` without arg returns syntax hint.

    # mirrors ROM src/olc_act.c:3444-3449
    """
    char, session, proto = _builder_in_oedit()
    result = _interpret_oedit(session, char, "wear")
    assert "Syntax" in result or "syntax" in result or "wear" in result.lower(), \
        f"Expected syntax hint, got: {result!r}"


# ── addaffect ────────────────────────────────────────────────────────────────

def test_addaffect_adds_affect_to_list():
    """``addaffect strength 5`` appends an Affect with location=STR, modifier=5.

    # mirrors ROM src/olc_act.c:2818-2858 — oedit_addaffect
    # pAf->location = flag_value(apply_flags, loc); pAf->modifier = atoi(mod)
    # pAf->where = TO_OBJECT (1); pAf->type = -1; pAf->duration = -1
    """
    char, session, proto = _builder_in_oedit()
    proto.affected = []

    result = _interpret_oedit(session, char, "addaffect strength 5")

    assert "added" in result.lower(), f"Expected 'added' confirmation, got: {result!r}"
    assert len(proto.affected) == 1, f"Expected 1 affect, got {len(proto.affected)}"
    af = proto.affected[0]
    assert af.location == 1, f"location should be APPLY_STR (1), got {af.location}"
    assert af.modifier == 5, f"modifier should be 5, got {af.modifier}"
    assert af.where == 1, f"where should be TO_OBJECT (1), got {af.where}"
    assert af.type == -1
    assert af.duration == -1


def test_addaffect_no_args_returns_syntax():
    """``addaffect`` without args returns syntax hint.

    # mirrors ROM src/olc_act.c:2828-2832
    """
    char, session, proto = _builder_in_oedit()
    result = _interpret_oedit(session, char, "addaffect")
    assert "Syntax" in result or "syntax" in result or "addaffect" in result.lower(), \
        f"Expected syntax hint, got: {result!r}"


def test_addaffect_invalid_location_returns_error():
    """``addaffect xyzzy 5`` with invalid location returns error.

    # mirrors ROM src/olc_act.c:2833-2837 — flag_value(apply_flags, loc) == NO_FLAG
    """
    char, session, proto = _builder_in_oedit()
    result = _interpret_oedit(session, char, "addaffect xyzzy_invalid_loc 5")
    assert "Valid" in result or "valid" in result or "Unknown" in result or "Invalid" in result, \
        f"Expected error for invalid location, got: {result!r}"


def test_addaffect_non_numeric_modifier_returns_syntax():
    """``addaffect strength abc`` with non-numeric mod returns syntax.

    # mirrors ROM src/olc_act.c:2828 — !is_number(mod)
    """
    char, session, proto = _builder_in_oedit()
    result = _interpret_oedit(session, char, "addaffect strength abc")
    assert "Syntax" in result or "syntax" in result or "number" in result.lower(), \
        f"Expected syntax/number error, got: {result!r}"


# ── delaffect ────────────────────────────────────────────────────────────────

def test_delaffect_removes_first_affect():
    """``delaffect 0`` removes the first affect in the list.

    # mirrors ROM src/olc_act.c:2957-2961 — value==0: pObj->affected = pAf->next
    """
    char, session, proto = _builder_in_oedit()
    proto.affected = [
        Affect(where=1, type=-1, level=10, duration=-1, location=1, modifier=5, bitvector=0),
        Affect(where=1, type=-1, level=10, duration=-1, location=2, modifier=3, bitvector=0),
    ]

    result = _interpret_oedit(session, char, "delaffect 0")

    assert "removed" in result.lower() or "Affect removed" in result, \
        f"Expected removal confirmation, got: {result!r}"
    assert len(proto.affected) == 1
    assert proto.affected[0].location == 2, "Second affect should remain"


def test_delaffect_removes_middle_affect():
    """``delaffect 1`` removes the second affect.

    # mirrors ROM src/olc_act.c:2963-2976 — walk to index, splice out next
    """
    char, session, proto = _builder_in_oedit()
    proto.affected = [
        Affect(where=1, type=-1, level=10, duration=-1, location=1, modifier=5, bitvector=0),
        Affect(where=1, type=-1, level=10, duration=-1, location=2, modifier=3, bitvector=0),
        Affect(where=1, type=-1, level=10, duration=-1, location=3, modifier=1, bitvector=0),
    ]

    result = _interpret_oedit(session, char, "delaffect 1")

    assert "removed" in result.lower() or "Affect removed" in result
    assert len(proto.affected) == 2
    assert proto.affected[0].location == 1
    assert proto.affected[1].location == 3


def test_delaffect_no_args_returns_syntax():
    """``delaffect`` without number returns syntax.

    # mirrors ROM src/olc_act.c:2936-2940
    """
    char, session, proto = _builder_in_oedit()
    result = _interpret_oedit(session, char, "delaffect")
    assert "Syntax" in result or "syntax" in result or "delaffect" in result.lower(), \
        f"Expected syntax hint, got: {result!r}"


def test_delaffect_on_empty_list_returns_error():
    """``delaffect 0`` with no affects returns 'Non-existant affect'.

    # mirrors ROM src/olc_act.c:2942-2946 — if !pObj->affected → error
    """
    char, session, proto = _builder_in_oedit()
    proto.affected = []

    result = _interpret_oedit(session, char, "delaffect 0")

    assert "affect" in result.lower(), \
        f"Expected affect-not-found error, got: {result!r}"


def test_delaffect_out_of_range_returns_error():
    """``delaffect 5`` on a single-affect list returns 'No such affect'.

    # mirrors ROM src/olc_act.c:2975-2979 — if !pAf_next → 'No such affect'
    """
    char, session, proto = _builder_in_oedit()
    proto.affected = [
        Affect(where=1, type=-1, level=10, duration=-1, location=1, modifier=5, bitvector=0),
    ]

    result = _interpret_oedit(session, char, "delaffect 5")

    assert "affect" in result.lower() or "No such" in result, \
        f"Expected out-of-range error, got: {result!r}"
