"""Integration tests for ``do_mpcast`` (MOBprog ``cast`` script command).

ROM C reference: ``src/mob_cmds.c:1043-1066`` — ROM ``do_mpcast`` switches on
``skill_table[sn].target`` (a ``TAR_*`` enum). For ``TAR_OBJ_CHAR_DEF``,
``TAR_OBJ_CHAR_OFF``, and ``TAR_OBJ_INV`` the routine resolves *only* an object
via ``get_obj_here`` and returns silently when no object matches the token —
even if a character with that name is standing right there. Python had been
dispatching off free-form strings (``"victim"`` / ``"friendly"`` / ``"object"`` /
``"character_or_object"``) and the ``"character_or_object"`` branch tried the
character first, so ``mob cast bless <PC>`` would erroneously bless the PC
instead of bugging out for lack of an object.

Closes MOBCMD-011 + MOBCMD-012.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud import mob_cmds
from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.room import Room
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.skills.registry import load_skills, skill_registry


@pytest.fixture(autouse=True)
def _reset_registries():
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    area_registry.clear()
    character_registry.clear()
    yield
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    area_registry.clear()
    character_registry.clear()


def _setup_room() -> Room:
    area = Area(vnum=1, name="Cast Test Area")
    area_registry[1] = area
    room = Room(vnum=9100, name="Cast Test Room", area=area)
    room_registry[room.vnum] = room
    return room


class TestMpCastObjTargetResolvesObjOnly:
    """ROM ``src/mob_cmds.c:1060-1066``: the ``TAR_OBJ_CHAR_DEF``,
    ``TAR_OBJ_CHAR_OFF``, and ``TAR_OBJ_INV`` cases all resolve via
    ``get_obj_here`` only — no character fallback. The Python dispatch needs
    to honour that, not silently re-target the spell at a same-named PC.
    """

    def test_obj_target_does_not_fall_back_to_character(self, monkeypatch):
        load_skills(Path("data/skills.json"))
        room = _setup_room()

        caster = Character(name="Cleric", is_npc=True, level=40)
        hero = Character(name="Hero", is_npc=False)
        for char in (caster, hero):
            room.add_character(char)
            character_registry.append(char)

        # bless is TAR_OBJ_CHAR_DEF (JSON: "character_or_object"). With no
        # object in the room named "Hero", ROM's switch falls through with
        # obj == NULL and returns. Python had wrongly resolved the character.
        invocations: list[tuple] = []

        def fake_bless(c, t):  # noqa: ANN001 - test stub
            invocations.append((c, t))
            return None

        monkeypatch.setitem(skill_registry.handlers, "bless", fake_bless)

        mob_cmds.mob_interpret(caster, "cast bless Hero")

        assert invocations == [], (
            "bless handler was invoked even though no object named 'Hero' is in"
            " the room; ROM src/mob_cmds.c:1060-1066 requires obj resolution"
            " for TAR_OBJ_CHAR_DEF — no character fallback in mob_cmds context."
        )

    def test_offensive_target_still_resolves_character(self, monkeypatch):
        """Positive control: ``TAR_CHAR_OFFENSIVE`` (JSON ``"victim"``) must
        still resolve the named character — switching to canonical-enum
        dispatch must not regress the working paths."""
        load_skills(Path("data/skills.json"))
        room = _setup_room()

        caster = Character(name="Invoker", is_npc=True, level=40)
        target = Character(name="Adventurer", is_npc=False)
        for char in (caster, target):
            room.add_character(char)
            character_registry.append(char)

        invocations: list[tuple] = []

        def fake_acid(c, t):  # noqa: ANN001 - test stub
            invocations.append((c, t))
            return None

        monkeypatch.setitem(skill_registry.handlers, "acid blast", fake_acid)

        mob_cmds.mob_interpret(caster, "cast 'acid blast' Adventurer")

        assert len(invocations) == 1, "TAR_CHAR_OFFENSIVE dispatch regressed."
        assert invocations[0][1] is target
