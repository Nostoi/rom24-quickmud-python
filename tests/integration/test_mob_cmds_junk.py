"""Integration tests for ``do_mpjunk`` (MOBprog ``junk`` script command).

ROM C reference: ``src/mob_cmds.c:409-446`` — ROM uses ``arg[3] == '\\0' ||
is_name(&arg[4], obj->name)`` inside the all-loop. ROM's ``is_name`` returns
``FALSE`` for an empty needle, so a literal ``mob junk all.`` (trailing dot
with no suffix) matches nothing. Python had been short-circuiting on
``not suffix`` and discarded every carried object, an over-broad match.

Closes MOBCMD-004.
"""

from __future__ import annotations

import pytest

from mud.mob_cmds import do_mpjunk
from mud.models.character import Character
from mud.models.obj import ObjIndex
from mud.models.object import Object


@pytest.fixture
def hoarder_mob() -> Character:
    mob = Character(name="Hoarder", is_npc=True)
    coin_proto = ObjIndex(vnum=8401, short_descr="a silver coin", name="coin")
    torch_proto = ObjIndex(vnum=8402, short_descr="a travel torch", name="torch")
    mob.add_object(Object(instance_id=None, prototype=coin_proto))
    mob.add_object(Object(instance_id=None, prototype=torch_proto))
    return mob


class TestMpJunkAllSuffixParsing:
    """MOBCMD-004: ROM ``src/mob_cmds.c:436`` — the all-loop matches via
    ``arg[3] == '\\0' || is_name(&arg[4], obj->name)``. ``arg[3] == '\\0'``
    is the bare ``"all"`` case; otherwise ROM defers to ``is_name`` which
    returns FALSE for an empty needle. ``mob junk all.`` (trailing dot, no
    suffix) therefore matches nothing in ROM.
    """

    def test_all_dot_with_empty_suffix_matches_nothing(self, hoarder_mob):
        """``mob junk all.`` must NOT discard anything — ROM's ``is_name``
        on an empty string returns FALSE for every object."""
        do_mpjunk(hoarder_mob, "all.")

        assert len(hoarder_mob.inventory) == 2, (
            "do_mpjunk('all.') discarded inventory; ROM src/mob_cmds.c:436"
            " evaluates is_name with an empty needle which returns FALSE,"
            " so no items should match."
        )

    def test_bare_all_still_clears_inventory(self, hoarder_mob):
        """Positive control: bare ``mob junk all`` (the ``arg[3] == '\\0''``
        path) discards everything."""
        do_mpjunk(hoarder_mob, "all")

        assert hoarder_mob.inventory == []
