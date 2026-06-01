"""Regression for CAST-009 (advisor review, 2026-05-31; closed 2026-06-01).

ROM `do_cast` improves a spell skill on *failure* as well as success: the
concentration-lost branch calls `check_improve(ch, sn, FALSE, 1)` before
deducting half mana (`src/magic.c:551-554`). Failing a spell is a valid path
to improving it (core skill progression).

Python's `do_cast` returned "You lost your concentration." before ever reaching
`_check_improve`, so a failed cast never trained the skill — the lone
`_check_improve(...)` call only ran on the success path.

ROM C: src/magic.c:551-554 (do_cast concentration-lost branch).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.commands.combat import do_cast
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills.registry import load_skills, skill_registry
from mud.utils import rng_mm


@pytest.fixture(autouse=True)
def _load_skills():
    skill_registry.skills.clear()
    skill_registry.handlers.clear()
    load_skills(Path("data/skills.json"))
    yield
    skill_registry.skills.clear()
    skill_registry.handlers.clear()


def test_failed_cast_calls_check_improve_with_false(monkeypatch):
    room = Room(vnum=99100, name="Arena")
    caster = Character(
        name="Tester",
        level=20,
        ch_class=0,
        is_npc=False,
        perm_stat=[0, 18, 0, 0, 0],
        mana=200,
        position=int(Position.STANDING),
        # Low learned % so the concentration roll fails deterministically.
        skills={"magic missile": 5},
    )
    victim = Character(name="Fido", level=20, ch_class=0, is_npc=True, hit=200, max_hit=200)
    caster.room = room
    victim.room = room
    room.people.extend([caster, victim])
    caster.messages = []

    calls: list[bool] = []
    orig = skill_registry._check_improve

    def _spy(caster_arg, skill_arg, name_arg, success_arg, *args, **kwargs):
        calls.append(success_arg)
        return orig(caster_arg, skill_arg, name_arg, success_arg, *args, **kwargs)

    monkeypatch.setattr(skill_registry, "_check_improve", _spy)

    rng_mm.seed_mm(1)
    result = do_cast(caster, "'magic missile' Fido")

    # The cast must have failed (concentration lost).
    assert result == "You lost your concentration."
    # ROM src/magic.c:553 — the failure branch trains the skill with success=FALSE.
    assert calls == [False], f"expected one check_improve(success=False) call, got {calls}"
