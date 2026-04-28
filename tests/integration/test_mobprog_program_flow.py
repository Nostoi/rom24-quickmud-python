"""Integration tests for ``_program_flow`` control-word state machine.

Covers ROM ``src/mob_prog.c:967-1156`` (``program_flow``) divergences from
the QuickMUD Python port.

MOBPROG-005 is structural-parity only — see
``docs/parity/MOB_PROG_C_AUDIT.md`` for why no failing-before/passing-after
behavioural test exists. The regression case below exercises a nested
``if/else { if ... endif } endif`` program to confirm the inner branch still
executes after the ROM-aligned ``state[level] = IN_BLOCK`` reset.
"""

from __future__ import annotations

import pytest

from mud.mobprog import Trigger, run_prog
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.mob import MobProgram
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _clear_registries():
    room_registry.clear()
    character_registry.clear()
    yield
    room_registry.clear()
    character_registry.clear()


def test_nested_if_inside_else_executes_inner_branch(monkeypatch):
    """ROM src/mob_prog.c:1127-1140 — `else` resets state to IN_BLOCK so a
    nested `if` inside the else block enters its body normally.
    """
    room = Room(vnum=4500, name="Hall")
    room_registry[4500] = room

    mob = Character(name="warden", is_npc=True)
    mob.position = Position.STANDING
    mob.default_pos = Position.STANDING
    room.add_character(mob)
    character_registry.append(mob)

    pc = Character(name="hero", is_npc=False)
    pc.position = Position.STANDING
    room.add_character(pc)
    character_registry.append(pc)

    # Outer if(isnpc $n) is False for a PC → flows into else; inner
    # if(ispc $n) must enter and execute the inner echoat.
    program = MobProgram(
        trig_type=int(Trigger.SPEECH),
        trig_phrase="hello",
        vnum=4501,
        code=(
            "if isnpc $n\n"
            "  mob echoat $n outer-true\n"
            "else\n"
            "  if ispc $n\n"
            "    mob echoat $n inner-pc\n"
            "  endif\n"
            "endif\n"
        ),
    )
    mob.mob_programs = [program]

    monkeypatch.setattr(
        "mud.commands.dispatcher.process_command",
        lambda char, line: "",
    )

    run_prog(mob, Trigger.SPEECH, actor=pc, phrase="hello")

    # The inner branch ran for the PC.
    assert any("inner-pc" in msg for msg in pc.messages)
    assert not any("outer-true" in msg for msg in pc.messages)
