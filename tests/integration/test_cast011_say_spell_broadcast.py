"""CAST-011 — do_cast broadcasts the spell incantation (say_spell) to the room.

ROM ``do_cast`` (``src/magic.c:545``)::

    if (str_cmp (skill_table[sn].name, "ventriloquate"))
        say_spell (ch, sn);

So *every* spell except ``ventriloquate`` broadcasts ``"$n utters the words,
'...'"`` to the room (actual words to same-class observers, garbled to others —
``src/magic.c:199-204``), fired after the mana check and before WAIT_STATE/the
success roll. The Python ``mud/commands/combat.py:do_cast`` never called the
existing ``broadcast_spell_words`` helper, so casting was silent to the room.
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


def _mage(name: str, room: Room, *, spell: str) -> Character:
    ch = Character(
        name=name,
        level=60,
        ch_class=0,
        is_npc=False,
        perm_stat=[0, 18, 0, 0, 0],
        mana=500,
        position=int(Position.STANDING),
        skills={spell: 90},
    )
    ch.room = room
    room.people.append(ch)
    ch.messages = []
    ch.wait = 0
    return ch


def test_do_cast_broadcasts_say_spell_for_normal_spell(monkeypatch):
    """ROM src/magic.c:545 — non-ventriloquate spells call say_spell(ch, sn)."""
    import mud.commands.combat as combat_mod

    calls: list[str] = []
    monkeypatch.setattr(
        combat_mod, "broadcast_spell_words", lambda caster, spell_name: calls.append(spell_name), raising=False
    )

    room = Room(vnum=99300, name="Arena")
    caster = _mage("Mage", room, spell="fly")

    rng_mm.seed_mm(12345)
    do_cast(caster, "fly")

    assert calls == ["fly"], f"expected say_spell broadcast for 'fly', got {calls}"


def test_do_cast_skips_say_spell_for_ventriloquate(monkeypatch):
    """ROM src/magic.c:544 — `if (str_cmp(name, "ventriloquate")) say_spell(...)` skips it."""
    import mud.commands.combat as combat_mod

    calls: list[str] = []
    monkeypatch.setattr(
        combat_mod, "broadcast_spell_words", lambda caster, spell_name: calls.append(spell_name), raising=False
    )
    # Avoid running the real ventriloquate handler.
    monkeypatch.setattr(skill_registry, "handlers", {}, raising=False)

    room = Room(vnum=99301, name="Arena")
    caster = _mage("Mage", room, spell="ventriloquate")

    rng_mm.seed_mm(12345)
    do_cast(caster, "ventriloquate Mage hi")

    assert calls == [], f"ventriloquate must NOT broadcast say_spell, got {calls}"
