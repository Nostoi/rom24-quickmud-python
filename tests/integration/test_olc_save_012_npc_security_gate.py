"""OLC_SAVE-012 — NPC security gate on `_is_builder`.

Mirrors ROM IS_BUILDER macro (`src/merc.h`):
    #define IS_BUILDER(ch, Area)  (!IS_NPC((ch)) && (
        (ch)->pcdata->security >= (Area)->security
        || strstr((Area)->builders, (ch)->name)))

ROM `cmd_asave` (src/olc_save.c:931-936) sets `sec = 0` for NPCs, then
relies on IS_BUILDER's leading `!IS_NPC` check to fail. Python
`_is_builder` walked `pcdata.security` and the `builders` name list
without an `is_npc` short-circuit — so an NPC whose `name` happens to
appear in the builders list (e.g. mob_special spawning a mob named
"admin") would pass the gate.
"""

from __future__ import annotations

import pytest

from mud.commands.build import _is_builder
from mud.models.area import Area
from mud.models.character import Character


@pytest.fixture
def builder_area():
    return Area(
        vnum=910,
        name="OLC_SAVE-012 Area",
        file_name="olc_save_012.are",
        min_vnum=9200,
        max_vnum=9209,
        security=5,
        builders="admin TestBuilder",
    )


def test_npc_with_matching_name_is_not_builder(builder_area):
    """An NPC whose name matches the builders list must NOT pass the gate."""
    npc = Character()
    npc.name = "admin"
    npc.is_npc = True
    npc.pcdata = None  # NPCs have no pcdata

    assert _is_builder(npc, builder_area) is False


def test_npc_with_high_pcdata_security_is_not_builder(builder_area):
    """ROM `IS_NPC(ch) → sec = 0` — even a malformed NPC carrying a
    pcdata with high security must fail the gate (pcdata is irrelevant
    once IS_NPC short-circuits)."""
    npc = Character()
    npc.name = "OnlyAStub"
    npc.is_npc = True
    npc.pcdata = type("PCData", (), {"security": 9})()

    assert _is_builder(npc, builder_area) is False


def test_player_with_matching_name_still_passes(builder_area):
    """Regression: a real PC whose name is on the builders list passes."""
    pc = Character()
    pc.name = "TestBuilder"
    pc.is_npc = False
    pc.pcdata = type("PCData", (), {"security": 0})()

    assert _is_builder(pc, builder_area) is True
