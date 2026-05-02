"""OLC-010 / OLC-015 — ``do_olc`` / ``editor_table[]`` routing.

ROM reference: src/olc.c:646-690.

``do_olc`` (exposed as both ``olc`` and ``edit`` in the dispatcher) must:
- Reject NPCs immediately (IS_NPC guard).
- Return help text on no argument or unrecognised subcmd.
- Route ``olc area``   → ``cmd_aedit``   with remainder args.
- Route ``olc room``   → ``cmd_redit``   with remainder args.
- Route ``olc object`` → ``cmd_oedit``   with remainder args.
- Route ``olc mobile`` → ``cmd_medit``   with remainder args.
- Route ``olc mpcode`` → ``do_mpedit``   with remainder args.
- Route ``olc hedit``  → ``cmd_hedit``   with remainder args.
- Use prefix matching (``str_prefix``): ``olc mob`` must match ``mobile``.
"""

from __future__ import annotations

from mud.commands.imm_olc import do_edit
from mud.models.constants import LEVEL_HERO
from mud.net.session import Session
from mud.world import create_test_character, initialize_world


def setup_module(module):
    initialize_world("area/area.lst")


def _builder(room_vnum: int = 3001):
    char = create_test_character("Tester", room_vnum)
    char.level = LEVEL_HERO
    char.is_admin = True
    char.pcdata.security = 9
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return char


def _npc(room_vnum: int = 3001):
    char = create_test_character("Mob", room_vnum)
    char.is_npc = True
    return char


# ── NPC guard ────────────────────────────────────────────────────────────────

def test_npc_is_rejected():
    """ROM IS_NPC guard — NPC input must produce empty string."""
    mob = _npc()
    result = do_edit(mob, "room")
    assert result == ""


# ── No-arg / unknown → help ───────────────────────────────────────────────────

def test_no_arg_returns_help():
    char = _builder()
    result = do_edit(char, "")
    assert "olc" in result.lower() or "syntax" in result.lower()


def test_unknown_subcmd_returns_help():
    char = _builder()
    result = do_edit(char, "xyzzyfoo")
    assert "olc" in result.lower() or "syntax" in result.lower()


# ── Exact subcmd routing ──────────────────────────────────────────────────────

def test_routes_area_to_cmd_aedit(monkeypatch):
    """``olc area`` must delegate to ``cmd_aedit``."""
    char = _builder()
    calls = []

    import mud.commands.imm_olc as mod
    import mud.commands.build as build_mod

    original = build_mod.cmd_aedit

    def fake_aedit(c, a):
        calls.append(("aedit", c, a))
        return "aedit called"

    monkeypatch.setattr(build_mod, "cmd_aedit", fake_aedit)
    result = do_edit(char, "area 3000")
    assert calls, "cmd_aedit was not called"
    assert calls[0][2] == "3000"
    assert result == "aedit called"


def test_routes_room_to_cmd_redit(monkeypatch):
    char = _builder()
    calls = []

    import mud.commands.build as build_mod

    def fake_redit(c, a):
        calls.append(a)
        return "redit called"

    monkeypatch.setattr(build_mod, "cmd_redit", fake_redit)
    result = do_edit(char, "room 3001")
    assert calls == ["3001"]
    assert result == "redit called"


def test_routes_object_to_cmd_oedit(monkeypatch):
    char = _builder()
    calls = []

    import mud.commands.build as build_mod

    def fake_oedit(c, a):
        calls.append(a)
        return "oedit called"

    monkeypatch.setattr(build_mod, "cmd_oedit", fake_oedit)
    result = do_edit(char, "object 3001")
    assert calls == ["3001"]
    assert result == "oedit called"


def test_routes_mobile_to_cmd_medit(monkeypatch):
    char = _builder()
    calls = []

    import mud.commands.build as build_mod

    def fake_medit(c, a):
        calls.append(a)
        return "medit called"

    monkeypatch.setattr(build_mod, "cmd_medit", fake_medit)
    result = do_edit(char, "mobile 3005")
    assert calls == ["3005"]
    assert result == "medit called"


def test_routes_mpcode_to_do_mpedit(monkeypatch):
    char = _builder()
    calls = []

    import mud.commands.imm_olc as mod

    def fake_mpedit(c, a):
        calls.append(a)
        return "mpedit called"

    monkeypatch.setattr(mod, "do_mpedit", fake_mpedit)
    result = mod.do_edit(char, "mpcode 3001")
    assert calls == ["3001"]
    assert result == "mpedit called"


def test_routes_hedit_to_cmd_hedit(monkeypatch):
    char = _builder()
    calls = []

    import mud.commands.build as build_mod

    def fake_hedit(c, a):
        calls.append(a)
        return "hedit called"

    monkeypatch.setattr(build_mod, "cmd_hedit", fake_hedit)
    result = do_edit(char, "hedit greeting")
    assert calls == ["greeting"]
    assert result == "hedit called"


# ── Prefix matching (str_prefix) ─────────────────────────────────────────────

def test_prefix_mob_matches_mobile(monkeypatch):
    """``olc mob`` is a prefix of ``mobile`` and must route to cmd_medit."""
    char = _builder()
    calls = []

    import mud.commands.build as build_mod

    def fake_medit(c, a):
        calls.append(a)
        return "medit called"

    monkeypatch.setattr(build_mod, "cmd_medit", fake_medit)
    result = do_edit(char, "mob 3005")
    assert calls, "cmd_medit not called for prefix 'mob'"


def test_prefix_r_matches_room(monkeypatch):
    """``olc r`` is a prefix of ``room``."""
    char = _builder()
    calls = []

    import mud.commands.build as build_mod

    def fake_redit(c, a):
        calls.append(a)
        return "redit called"

    monkeypatch.setattr(build_mod, "cmd_redit", fake_redit)
    result = do_edit(char, "r")
    assert calls, "cmd_redit not called for prefix 'r'"


def test_prefix_obj_matches_object(monkeypatch):
    """``olc obj`` is a prefix of ``object``."""
    char = _builder()
    calls = []

    import mud.commands.build as build_mod

    def fake_oedit(c, a):
        calls.append(a)
        return "oedit called"

    monkeypatch.setattr(build_mod, "cmd_oedit", fake_oedit)
    result = do_edit(char, "obj 3001")
    assert calls, "cmd_oedit not called for prefix 'obj'"


# ── Remainder args passed through ─────────────────────────────────────────────

def test_remainder_args_passed_correctly(monkeypatch):
    """Args after subcmd must be passed verbatim as the remainder."""
    char = _builder()
    calls = []

    import mud.commands.build as build_mod

    def fake_redit(c, a):
        calls.append(a)
        return ""

    monkeypatch.setattr(build_mod, "cmd_redit", fake_redit)
    do_edit(char, "room create 9999")
    assert calls == ["create 9999"]


def test_no_remainder_passes_empty_string(monkeypatch):
    """When no args follow the subcmd, remainder must be empty string."""
    char = _builder()
    calls = []

    import mud.commands.build as build_mod

    def fake_redit(c, a):
        calls.append(a)
        return ""

    monkeypatch.setattr(build_mod, "cmd_redit", fake_redit)
    do_edit(char, "room")
    assert calls == [""]
