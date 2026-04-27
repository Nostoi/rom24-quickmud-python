"""Integration tests for ``do_mptransfer`` (MOBprog ``transfer`` script command).

ROM C reference: ``src/mob_cmds.c:791-806`` — when the first arg is the
literal token ``"all"``, ROM iterates the room's PCs and *recursively
calls itself* with each PC's name + the original location arg, so the
full per-target validation runs on each victim. Python had been
inlining the iteration with a direct ``_transfer_character`` call,
short-circuiting the recursive validation path.

Closes MOBCMD-017.
"""

from __future__ import annotations

import pytest

from mud import mob_cmds as mob_cmds_mod
from mud.mob_cmds import do_mptransfer
from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.room import Room
from mud.registry import area_registry, room_registry


@pytest.fixture(autouse=True)
def _reset_registries():
    room_registry.clear()
    area_registry.clear()
    character_registry.clear()
    yield
    room_registry.clear()
    area_registry.clear()
    character_registry.clear()


@pytest.fixture
def two_rooms() -> tuple[Room, Room]:
    area = Area(vnum=1, name="Transfer Test Area")
    area_registry[1] = area
    src = Room(vnum=9930, name="Transfer Source", area=area)
    dst = Room(vnum=9931, name="Transfer Dest", area=area)
    room_registry[src.vnum] = src
    room_registry[dst.vnum] = dst
    return src, dst


class TestMpTransferAllRecursesThroughDispatch:
    """MOBCMD-017: ROM ``mob transfer all <loc>`` recursively calls
    ``do_mptransfer(ch, "<name> <loc>")`` once per PC, so the full
    per-target validation pipeline runs (room privacy, location
    resolution, etc.). Python had been inlining the loop and bypassing
    the recursive path."""

    def test_all_arg_recurses_once_per_pc(self, monkeypatch, two_rooms):
        src, dst = two_rooms

        controller = Character(name="Controller", is_npc=True)
        src.add_character(controller)
        character_registry.append(controller)

        hero = Character(name="Hero", is_npc=False)
        sage = Character(name="Sage", is_npc=False)
        bystander_npc = Character(name="Stander", is_npc=True)
        for char in (hero, sage, bystander_npc):
            src.add_character(char)
            character_registry.append(char)

        # Monkeypatch the module-level reference so the recursion sees the
        # spy. Without recursion, the spy will record only the original
        # outer call; with recursion, the spy records one inner call per PC.
        invocations: list[tuple[Character, str]] = []
        original = mob_cmds_mod.do_mptransfer

        def spy(c, arg):  # noqa: ANN001
            invocations.append((c, arg))
            return original(c, arg)

        monkeypatch.setattr(mob_cmds_mod, "do_mptransfer", spy)

        # Outer call enters via the module attribute so subsequent recursion
        # is also intercepted.
        mob_cmds_mod.do_mptransfer(controller, f"all {dst.vnum}")

        # The outer call records itself; ROM-faithful recursion adds two
        # more entries (Hero + Sage). NPCs are skipped per ROM line 799.
        recursive_calls = [args for c, args in invocations if args != f"all {dst.vnum}"]
        assert len(recursive_calls) == 2, (
            f"do_mptransfer('all') made {len(recursive_calls)} recursive"
            " calls; ROM src/mob_cmds.c:791-806 expects one self-recursion"
            " per PC in the room (Hero + Sage)."
        )
        assert any("Hero" in arg for arg in recursive_calls)
        assert any("Sage" in arg for arg in recursive_calls)
        assert not any("Stander" in arg for arg in recursive_calls), (
            "NPC was recursed on; ROM line 799 (`!IS_NPC(victim)`) skips NPCs."
        )

        # And the actual transfer outcome should still hold.
        assert hero.room is dst
        assert sage.room is dst
        assert bystander_npc.room is src
