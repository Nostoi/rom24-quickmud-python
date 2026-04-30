"""OLC_ACT-006 — `medit create <vnum>` subcommand.

Mirrors ROM `src/olc_act.c:3704-3753` (`medit_create`) and `src/mem.c:365-424`
(`new_mob_index` defaults). The audit's flagged CRITICAL divergence is that
new mobs were constructed without `ACT_IS_NPC` — every NPC-classification
check downstream would misidentify newly-built mobs as players. This closure
verifies the flag is set, plus the full ROM validation chain and defaults.
"""

from __future__ import annotations

import pytest

from mud.commands.build import cmd_medit
from mud.models.area import Area
from mud.models.constants import LEVEL_HERO, ActFlag, Sex, Size
from mud.models.mob import MobIndex, mob_registry
from mud.net.session import Session
from mud.registry import area_registry


@pytest.fixture(autouse=True)
def _clean_registries():
    area_snap = dict(area_registry)
    mob_snap = dict(mob_registry)
    area_registry.clear()
    mob_registry.clear()
    yield
    area_registry.clear()
    area_registry.update(area_snap)
    mob_registry.clear()
    mob_registry.update(mob_snap)


@pytest.fixture
def builder_area():
    area = Area(
        vnum=1,
        name="Builder Area",
        file_name="builder.are",
        min_vnum=1000,
        max_vnum=1099,
        security=5,
        builders="testbuilder",
    )
    area_registry[1] = area
    return area


@pytest.fixture
def builder_char(builder_area):
    from mud.models.character import Character

    char = Character()
    char.name = "TestBuilder"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 9})()
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return char


@pytest.fixture
def non_builder_char(builder_area):
    from mud.models.character import Character

    char = Character()
    char.name = "Visitor"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 0})()
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return char


def test_medit_create_requires_vnum(builder_char):
    # mirrors ROM src/olc_act.c:3712-3716.
    result = cmd_medit(builder_char, "create")
    assert result == "Syntax:  medit create [vnum]\n\r"


def test_medit_create_zero_vnum_rejected(builder_char):
    result = cmd_medit(builder_char, "create 0")
    assert result == "Syntax:  medit create [vnum]\n\r"


def test_medit_create_unassigned_vnum_rejected(builder_char):
    # mirrors ROM src/olc_act.c:3718-3724.
    result = cmd_medit(builder_char, "create 5000")
    assert result == "MEdit:  That vnum is not assigned an area.\n\r"


def test_medit_create_non_builder_rejected(non_builder_char):
    # mirrors ROM src/olc_act.c:3726-3730 — IS_BUILDER security gate.
    result = cmd_medit(non_builder_char, "create 1050")
    assert result == "MEdit:  Vnum in an area you cannot build in.\n\r"


def test_medit_create_existing_vnum_rejected(builder_char):
    # mirrors ROM src/olc_act.c:3732-3736.
    mob_registry[1050] = MobIndex(vnum=1050)
    result = cmd_medit(builder_char, "create 1050")
    assert result == "MEdit:  Mobile vnum already exists.\n\r"


def test_medit_create_returns_rom_message(builder_char):
    # mirrors ROM src/olc_act.c:3751.
    result = cmd_medit(builder_char, "create 1050")
    assert result == "Mobile Created.\n\r"


def test_medit_create_registers_proto(builder_char):
    cmd_medit(builder_char, "create 1050")
    assert 1050 in mob_registry
    proto = mob_registry[1050]
    assert isinstance(proto, MobIndex)
    assert proto.vnum == 1050


def test_medit_create_sets_act_is_npc_flag(builder_char):
    # mirrors ROM src/olc_act.c:3745 — pMob->act = ACT_IS_NPC.
    # AUDIT's flagged CRITICAL divergence: new mobs without IS_NPC
    # would be misclassified as players by every NPC-checking path.
    cmd_medit(builder_char, "create 1050")
    proto = mob_registry[1050]
    assert int(proto.act_flags) & int(ActFlag.IS_NPC) != 0
    # Legacy `act` field also set for backward compat with code that reads it.
    assert int(proto.act) & int(ActFlag.IS_NPC) != 0


def test_medit_create_uses_rom_defaults(builder_char, builder_area):
    cmd_medit(builder_char, "create 1050")
    proto = mob_registry[1050]
    # mirrors ROM src/mem.c:384-423 — new_mob_index defaults.
    assert proto.player_name == "no name"
    assert proto.short_descr == "(no short description)"
    assert proto.long_descr == "(no long description)\n\r"
    assert proto.description == ""
    assert proto.level == 0
    assert proto.alignment == 0
    assert proto.material == "unknown"
    assert proto.size == Size.MEDIUM
    assert proto.sex == Sex.NONE
    assert proto.start_pos == "standing"
    assert proto.default_pos == "standing"
    assert proto.wealth == 0
    assert proto.new_format is True
    assert proto.area is builder_area


def test_medit_create_descriptor_edits_new_proto(builder_char):
    cmd_medit(builder_char, "create 1050")
    session = builder_char.desc
    # mirrors ROM src/olc_act.c:3749 — `ch->desc->pEdit = pMob`.
    assert session.editor == "medit"
    assert session.editor_state.get("mob_proto") is mob_registry[1050]


def test_medit_create_in_session_dispatches(builder_char):
    cmd_medit(builder_char, "create 1050")
    cmd_medit(builder_char, "create 1051")
    assert 1051 in mob_registry
    assert builder_char.desc.editor_state.get("mob_proto") is mob_registry[1051]


def test_medit_unknown_vnum_no_longer_auto_creates(builder_char):
    # `@medit <unknown_vnum>` without `create` keyword must NOT auto-create.
    result = cmd_medit(builder_char, "1050")
    assert 1050 not in mob_registry
    assert "does not exist" in result.lower() or "create" in result.lower()
