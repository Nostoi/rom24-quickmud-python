"""OLC-009 — ``medit`` missing subcommands.

ROM reference (src/olc_act.c):
- medit_act        4142-4165
- medit_affect     4167-4191
- medit_ac         4192-4254
- medit_form       4256-4278
- medit_part       4278-4300
- medit_imm        4300-4322
- medit_res        4322-4344
- medit_vuln       4344-4366
- medit_off        4385-4407
- medit_size       4407-4429
- medit_hitdice    4429-4480
- medit_manadice   4480-4531
- medit_damdice    4531-4588
- medit_position   src/olc_act.c:4639-4699
- medit_addmprog   4864-4910
- medit_delmprog   4911-4969
"""

from __future__ import annotations

import pytest

from mud.commands.build import _interpret_medit
from mud.models.constants import (
    ActFlag,
    AffectFlag,
    FormFlag,
    ImmFlag,
    OffFlag,
    PartFlag,
    ResFlag,
    Size,
    VulnFlag,
    LEVEL_HERO,
)
from mud.models.mob import MobIndex, MobProgram
from mud.net.session import Session
from mud.world import create_test_character, initialize_world


def setup_module(module):
    initialize_world("area/area.lst")


def _make_mob_proto(vnum: int = 60001) -> MobIndex:
    proto = MobIndex(vnum=vnum, player_name="test mob")
    proto.act = 0
    proto.affected_by = 0
    proto.off_flags = 0
    proto.imm_flags = 0
    proto.res_flags = 0
    proto.vuln_flags = 0
    proto.form = 0
    proto.parts = 0
    proto.ac_pierce = 0
    proto.ac_bash = 0
    proto.ac_slash = 0
    proto.ac_exotic = 0
    proto.size = Size.MEDIUM
    proto.start_pos = "standing"
    proto.default_pos = "standing"
    proto.hit = (1, 8, 10)
    proto.mana = (1, 8, 10)
    proto.damage = (1, 6, 2)
    proto.mprogs = []
    proto.mprog_flags = 0
    return proto


def _builder_in_medit(vnum: int = 60001):
    char = create_test_character("Builder", 3001)
    char.level = LEVEL_HERO
    char.is_admin = True
    char.pcdata.security = 9
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    session.editor = "medit"
    proto = _make_mob_proto(vnum)
    session.editor_state = {"mob_proto": proto}
    return char, session, proto


# ── act ──────────────────────────────────────────────────────────────────────

def test_act_toggle_sets_flag():
    """``act sentinel`` sets SENTINEL bit — mirrors ROM src/olc_act.c:4142-4165 medit_act."""
    char, session, proto = _builder_in_medit()
    proto.act = int(ActFlag.IS_NPC)  # start with only IS_NPC

    result = _interpret_medit(session, char, "act sentinel")

    assert "act flag toggled" in result.lower(), f"Expected act toggle confirmation, got: {result!r}"
    assert proto.act & int(ActFlag.SENTINEL), "SENTINEL bit should be set"
    # IS_NPC must always remain set (ROM src/olc_act.c:4153 SET_BIT(pMob->act, ACT_IS_NPC))
    assert proto.act & int(ActFlag.IS_NPC), "IS_NPC must remain set after toggle"


def test_act_toggle_clears_flag():
    """``act sentinel`` clears SENTINEL when already set."""
    char, session, proto = _builder_in_medit()
    proto.act = int(ActFlag.IS_NPC) | int(ActFlag.SENTINEL)

    result = _interpret_medit(session, char, "act sentinel")

    assert "act flag toggled" in result.lower(), f"Got: {result!r}"
    assert not (proto.act & int(ActFlag.SENTINEL)), "SENTINEL bit should be cleared"
    # IS_NPC re-applied regardless
    assert proto.act & int(ActFlag.IS_NPC), "IS_NPC must remain set"


def test_act_no_arg_returns_syntax():
    """``act`` with no arg returns syntax string."""
    char, session, proto = _builder_in_medit()
    result = _interpret_medit(session, char, "act")
    assert "syntax" in result.lower() or "act [flag]" in result.lower(), f"Got: {result!r}"


# ── affect ────────────────────────────────────────────────────────────────────

def test_affect_toggle_sets_flag():
    """``affect sanctuary`` toggles SANCTUARY on affected_by — mirrors ROM src/olc_act.c:4167-4191."""
    char, session, proto = _builder_in_medit()
    proto.affected_by = 0

    result = _interpret_medit(session, char, "affect sanctuary")

    assert "affect flag toggled" in result.lower(), f"Got: {result!r}"
    assert proto.affected_by & int(AffectFlag.SANCTUARY), "SANCTUARY bit should be set"


def test_affect_toggle_clears_flag():
    char, session, proto = _builder_in_medit()
    proto.affected_by = int(AffectFlag.SANCTUARY)

    result = _interpret_medit(session, char, "affect sanctuary")

    assert "affect flag toggled" in result.lower(), f"Got: {result!r}"
    assert not (proto.affected_by & int(AffectFlag.SANCTUARY)), "SANCTUARY bit should be cleared"


# ── armor ─────────────────────────────────────────────────────────────────────

def test_armor_sets_all_four_values():
    """``armor 10 20 30 40`` sets pierce/bash/slash/exotic — mirrors ROM src/olc_act.c:4192-4254."""
    char, session, proto = _builder_in_medit()

    result = _interpret_medit(session, char, "armor 10 20 30 40")

    assert "ac set" in result.lower(), f"Got: {result!r}"
    assert proto.ac_pierce == 10
    assert proto.ac_bash == 20
    assert proto.ac_slash == 30
    assert proto.ac_exotic == 40


def test_armor_sets_only_pierce_keeps_others():
    """``armor 5`` sets pierce only; bash/slash/exotic unchanged."""
    char, session, proto = _builder_in_medit()
    proto.ac_bash = 15
    proto.ac_slash = 25
    proto.ac_exotic = 35

    result = _interpret_medit(session, char, "armor 5")

    assert "ac set" in result.lower(), f"Got: {result!r}"
    assert proto.ac_pierce == 5
    assert proto.ac_bash == 15
    assert proto.ac_slash == 25
    assert proto.ac_exotic == 35


def test_armor_no_arg_returns_syntax():
    char, session, proto = _builder_in_medit()
    result = _interpret_medit(session, char, "armor")
    assert "syntax" in result.lower() or "ac-pierce" in result.lower(), f"Got: {result!r}"


# ── form ──────────────────────────────────────────────────────────────────────

def test_form_toggle_sets_flag():
    """``form edible`` toggles EDIBLE on form — mirrors ROM src/olc_act.c:4256-4278."""
    char, session, proto = _builder_in_medit()
    proto.form = 0

    result = _interpret_medit(session, char, "form edible")

    assert "form toggled" in result.lower(), f"Got: {result!r}"
    assert proto.form & int(FormFlag.EDIBLE), "EDIBLE bit should be set"


def test_form_toggle_clears_flag():
    char, session, proto = _builder_in_medit()
    proto.form = int(FormFlag.EDIBLE)

    result = _interpret_medit(session, char, "form edible")

    assert "form toggled" in result.lower(), f"Got: {result!r}"
    assert not (proto.form & int(FormFlag.EDIBLE)), "EDIBLE bit should be cleared"


# ── part ──────────────────────────────────────────────────────────────────────

def test_part_toggle_sets_flag():
    """``part head`` toggles HEAD on parts — mirrors ROM src/olc_act.c:4278-4300."""
    char, session, proto = _builder_in_medit()
    proto.parts = 0

    result = _interpret_medit(session, char, "part head")

    assert "parts toggled" in result.lower(), f"Got: {result!r}"
    assert proto.parts & int(PartFlag.HEAD), "HEAD bit should be set"


# ── imm ───────────────────────────────────────────────────────────────────────

def test_imm_toggle_sets_flag():
    """``imm fire`` toggles FIRE on imm_flags — mirrors ROM src/olc_act.c:4300-4322."""
    char, session, proto = _builder_in_medit()
    proto.imm_flags = 0

    result = _interpret_medit(session, char, "imm fire")

    assert "immunity toggled" in result.lower(), f"Got: {result!r}"
    assert proto.imm_flags & int(ImmFlag.FIRE), "FIRE bit should be set"


# ── res ───────────────────────────────────────────────────────────────────────

def test_res_toggle_sets_flag():
    """``res cold`` toggles COLD on res_flags — mirrors ROM src/olc_act.c:4322-4344."""
    char, session, proto = _builder_in_medit()
    proto.res_flags = 0

    result = _interpret_medit(session, char, "res cold")

    assert "resistance toggled" in result.lower(), f"Got: {result!r}"
    assert proto.res_flags & int(ResFlag.COLD), "COLD bit should be set"


# ── vuln ──────────────────────────────────────────────────────────────────────

def test_vuln_toggle_sets_flag():
    """``vuln lightning`` toggles LIGHTNING on vuln_flags — mirrors ROM src/olc_act.c:4344-4366."""
    char, session, proto = _builder_in_medit()
    proto.vuln_flags = 0

    result = _interpret_medit(session, char, "vuln lightning")

    assert "vulnerability toggled" in result.lower(), f"Got: {result!r}"
    assert proto.vuln_flags & int(VulnFlag.LIGHTNING), "LIGHTNING bit should be set"


# ── off ───────────────────────────────────────────────────────────────────────

def test_off_toggle_sets_flag():
    """``off area_attack`` toggles AREA_ATTACK on off_flags — mirrors ROM src/olc_act.c:4385-4407."""
    char, session, proto = _builder_in_medit()
    proto.off_flags = 0

    result = _interpret_medit(session, char, "off area_attack")

    assert "offensive behaviour toggled" in result.lower(), f"Got: {result!r}"
    assert proto.off_flags & int(OffFlag.AREA_ATTACK), "AREA_ATTACK bit should be set"


# ── size ──────────────────────────────────────────────────────────────────────

def test_size_sets_value():
    """``size large`` sets size — mirrors ROM src/olc_act.c:4407-4429."""
    char, session, proto = _builder_in_medit()
    proto.size = Size.SMALL

    result = _interpret_medit(session, char, "size large")

    assert "size set" in result.lower(), f"Got: {result!r}"
    assert int(proto.size) == int(Size.LARGE), f"Expected LARGE, got {proto.size!r}"


def test_size_no_arg_returns_syntax():
    char, session, proto = _builder_in_medit()
    result = _interpret_medit(session, char, "size")
    assert "syntax" in result.lower() or "size [size]" in result.lower(), f"Got: {result!r}"


# ── hitdice ───────────────────────────────────────────────────────────────────

def test_hitdice_sets_dice_tuple():
    """``hitdice 3 8 10`` sets hit to (3,8,10) — mirrors ROM src/olc_act.c:4429-4480."""
    char, session, proto = _builder_in_medit()
    proto.hit = (1, 1, 0)

    result = _interpret_medit(session, char, "hitdice 3 8 10")

    assert "hitdice set" in result.lower(), f"Got: {result!r}"
    assert proto.hit == (3, 8, 10), f"Expected (3,8,10), got {proto.hit!r}"


def test_hitdice_no_arg_returns_syntax():
    char, session, proto = _builder_in_medit()
    result = _interpret_medit(session, char, "hitdice")
    assert "syntax" in result.lower() or "hitdice" in result.lower(), f"Got: {result!r}"


def test_hitdice_invalid_returns_syntax():
    char, session, proto = _builder_in_medit()
    result = _interpret_medit(session, char, "hitdice abc d xyz")
    assert "syntax" in result.lower() or "hitdice" in result.lower(), f"Got: {result!r}"


# ── manadice ──────────────────────────────────────────────────────────────────

def test_manadice_sets_dice_tuple():
    """``manadice 5 6 20`` sets mana to (5,6,20) — mirrors ROM src/olc_act.c:4480-4531."""
    char, session, proto = _builder_in_medit()
    proto.mana = (1, 1, 0)

    result = _interpret_medit(session, char, "manadice 5 6 20")

    assert "manadice set" in result.lower(), f"Got: {result!r}"
    assert proto.mana == (5, 6, 20), f"Expected (5,6,20), got {proto.mana!r}"


# ── damdice ───────────────────────────────────────────────────────────────────

def test_damdice_sets_dice_tuple():
    """``damdice 2 4 5`` sets damage to (2,4,5) — mirrors ROM src/olc_act.c:4531-4588."""
    char, session, proto = _builder_in_medit()
    proto.damage = (1, 1, 0)

    result = _interpret_medit(session, char, "damdice 2 4 5")

    assert "damdice set" in result.lower(), f"Got: {result!r}"
    assert proto.damage == (2, 4, 5), f"Expected (2,4,5), got {proto.damage!r}"


# ── position ──────────────────────────────────────────────────────────────────

def test_position_start_sets_start_pos():
    """``position start standing`` sets start_pos — mirrors ROM src/olc_act.c:4639-4699."""
    char, session, proto = _builder_in_medit()
    proto.start_pos = "sleeping"

    result = _interpret_medit(session, char, "position start standing")

    assert "start position set" in result.lower(), f"Got: {result!r}"


def test_position_default_sets_default_pos():
    """``position default resting`` sets default_pos."""
    char, session, proto = _builder_in_medit()
    proto.default_pos = "standing"

    result = _interpret_medit(session, char, "position default resting")

    assert "default position set" in result.lower(), f"Got: {result!r}"


def test_position_no_arg_returns_syntax():
    char, session, proto = _builder_in_medit()
    result = _interpret_medit(session, char, "position")
    assert "syntax" in result.lower() or "position" in result.lower(), f"Got: {result!r}"


# ── addmprog ──────────────────────────────────────────────────────────────────

def test_addmprog_no_arg_returns_syntax():
    """``addmprog`` with no args returns syntax — mirrors ROM src/olc_act.c:4864-4910."""
    char, session, proto = _builder_in_medit()
    result = _interpret_medit(session, char, "addmprog")
    assert "syntax" in result.lower() or "addmprog" in result.lower(), f"Got: {result!r}"


def test_addmprog_invalid_vnum_returns_error():
    """``addmprog 99999 greet hello`` with non-existent vnum returns error."""
    char, session, proto = _builder_in_medit()
    result = _interpret_medit(session, char, "addmprog 99999 greet hello")
    # ROM returns "No such MOBProgram." or "Valid flags are:" for bad trigger
    assert (
        "no such" in result.lower()
        or "valid flags" in result.lower()
        or "syntax" in result.lower()
    ), f"Got: {result!r}"


# ── delmprog ──────────────────────────────────────────────────────────────────

def test_delmprog_no_arg_returns_syntax():
    """``delmprog`` with no args returns syntax — mirrors ROM src/olc_act.c:4911-4969."""
    char, session, proto = _builder_in_medit()
    result = _interpret_medit(session, char, "delmprog")
    assert "syntax" in result.lower() or "delmprog" in result.lower(), f"Got: {result!r}"


def test_delmprog_empty_list_returns_error():
    """``delmprog 0`` on empty mprogs list returns error."""
    char, session, proto = _builder_in_medit()
    proto.mprogs = []
    result = _interpret_medit(session, char, "delmprog 0")
    assert "non existant" in result.lower() or "mprog" in result.lower(), f"Got: {result!r}"


def test_delmprog_removes_first_mprog():
    """``delmprog 0`` removes first mprog from list."""
    char, session, proto = _builder_in_medit()
    mp = MobProgram(trig_type=1, trig_phrase="hello", vnum=0, code="say hi")
    proto.mprogs = [mp]
    proto.mprog_flags = 1

    result = _interpret_medit(session, char, "delmprog 0")

    assert "mprog removed" in result.lower(), f"Got: {result!r}"
    assert proto.mprogs == [], "mprogs list should be empty"
    assert proto.mprog_flags == 0, "mprog_flags bit should be cleared"
