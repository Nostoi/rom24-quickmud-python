"""MOBPROG-008 — mp_give_trigger phrase token matching.

ROM ``src/mob_prog.c:1302-1318`` treats a non-numeric GIVE trigger phrase as
a space-separated list of object-name tokens. Any token matching the given
object name, or the literal ``all``, fires the program.
"""

from __future__ import annotations

from mud import mobprog
from mud.models.character import Character
from mud.models.mob import MobProgram
from mud.models.obj import ObjIndex
from mud.models.object import Object


def test_give_trigger_matches_any_phrase_token(monkeypatch):
    """ROM src/mob_prog.c:1309-1318 — phrase is a token list, not one string."""
    mob = Character(name="collector", is_npc=True)
    giver = Character(name="giver", is_npc=False)
    obj = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=9101, name="ruby sword", short_descr="a ruby sword"),
    )
    mob.mob_programs = [
        MobProgram(
            trig_type=int(mobprog.Trigger.GIVE),
            trig_phrase="dagger sword shield",
            vnum=9102,
            code=":",
        )
    ]

    fired: list[int] = []

    def _record_flow(vnum, code, context, mob_arg, actor, arg1, arg2, phrase):
        fired.append(int(vnum))

    monkeypatch.setattr(mobprog, "_program_flow", _record_flow)

    assert mobprog.mp_give_trigger(mob, giver, obj) is True
    assert fired == [9102]


def test_give_trigger_all_token_matches_any_object(monkeypatch):
    """ROM src/mob_prog.c:1313 — literal `all` token matches every object."""
    mob = Character(name="collector", is_npc=True)
    giver = Character(name="giver", is_npc=False)
    obj = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=9103, name="plain rock", short_descr="a plain rock"),
    )
    mob.mob_programs = [
        MobProgram(
            trig_type=int(mobprog.Trigger.GIVE),
            trig_phrase="coin all gem",
            vnum=9104,
            code=":",
        )
    ]

    fired: list[int] = []

    def _record_flow(vnum, code, context, mob_arg, actor, arg1, arg2, phrase):
        fired.append(int(vnum))

    monkeypatch.setattr(mobprog, "_program_flow", _record_flow)

    assert mobprog.mp_give_trigger(mob, giver, obj) is True
    assert fired == [9104]
