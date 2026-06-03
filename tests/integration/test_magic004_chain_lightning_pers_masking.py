"""MAGIC-004 — chain_lightning room/vict lines render ``$n``/``$N`` per-recipient.

ROM ``spell_chain_lightning`` (``src/magic.c:1234-1307``) emits its visible lines
through ``act()``, so ``comm.c`` renders ``$n``/``$N`` per recipient via
``PERS()``/``can_see`` — an actor a recipient cannot see masks to ``"someone"``.
Because every token here is **mid-sentence** ("A lightning bolt …", "The bolt …"),
the mask renders **lowercase** ``"someone"`` (``act`` only capitalizes the buffer's
first letter, which is the "A"/"The").

First strike (``:1244-1249``):
  * TO_ROOM ``"A lightning bolt leaps from $n's hand and arcs to $N."`` (excludes
    only ``ch`` — the victim *is* a recipient; this is ``TO_ROOM``, not TO_NOTVICT).
  * TO_CHAR ``"A lightning bolt leaps from your hand and arcs to $N."``
  * TO_VICT ``"A lightning bolt leaps from $n's hand and hits you!"``

Chain bounce (``:1270``): TO_ROOM ``"The bolt arcs to $n!"`` (subject = bounced
victim).

The Python port baked ``caster``/``victim`` names into every leg instead of
rendering ``$n``/``$N`` through PERS, leaking the names of actors a witness
cannot see (INV-027).
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import AffectFlag
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.utils import rng_mm


def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rng_mm, "dice", lambda number, size: 10)
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda level, target, dtype: False)


def test_first_strike_room_masks_invisible_caster(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch)
    caster = Character(name="Stormcaller", level=12, is_npc=False, hit=220, max_hit=220)
    caster.add_affect(AffectFlag.INVISIBLE)
    victim = Character(name="Sentinel", level=10, is_npc=False, hit=180, max_hit=180)
    witness = Character(name="Watcher", level=9, is_npc=False, hit=170, max_hit=170)
    room = Room(vnum=42900)
    for c in (caster, victim, witness):
        room.add_character(c)
        c.messages.clear()

    skill_handlers.chain_lightning(caster, victim)

    # $n (caster) masked lowercase mid-sentence; $N (visible victim) keeps its name.
    assert "A lightning bolt leaps from someone's hand and arcs to Sentinel." in witness.messages, witness.messages
    assert not any("Stormcaller" in m for m in witness.messages), witness.messages


def test_first_strike_vict_masks_invisible_caster(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch)
    caster = Character(name="Stormcaller", level=12, is_npc=False, hit=220, max_hit=220)
    caster.add_affect(AffectFlag.INVISIBLE)
    victim = Character(name="Sentinel", level=10, is_npc=False, hit=180, max_hit=180)
    room = Room(vnum=42901)
    for c in (caster, victim):
        room.add_character(c)
        c.messages.clear()

    skill_handlers.chain_lightning(caster, victim)

    assert "A lightning bolt leaps from someone's hand and hits you!" in victim.messages, victim.messages


def test_first_strike_room_masks_invisible_victim(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch)
    caster = Character(name="Stormcaller", level=12, is_npc=False, hit=220, max_hit=220)
    victim = Character(name="Sentinel", level=10, is_npc=False, hit=180, max_hit=180)
    victim.add_affect(AffectFlag.INVISIBLE)
    witness = Character(name="Watcher", level=9, is_npc=False, hit=170, max_hit=170)
    room = Room(vnum=42902)
    for c in (caster, victim, witness):
        room.add_character(c)
        c.messages.clear()

    skill_handlers.chain_lightning(caster, victim)

    # $N (invisible victim) masked lowercase; $n (visible caster) keeps its name.
    assert "A lightning bolt leaps from Stormcaller's hand and arcs to someone." in witness.messages, witness.messages


def test_bounce_room_masks_invisible_bounce_target(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch)
    caster = Character(name="Stormcaller", level=12, is_npc=False, hit=220, max_hit=220)
    v1 = Character(name="Sentinel", level=10, is_npc=True, hit=180, max_hit=180)
    v2 = Character(name="Raider", level=9, is_npc=True, hit=170, max_hit=170)
    v2.add_affect(AffectFlag.INVISIBLE)
    witness = Character(name="Watcher", level=8, is_npc=False, hit=160, max_hit=160)
    room = Room(vnum=42903)
    for c in (caster, v1, v2, witness):
        room.add_character(c)
        c.messages.clear()

    skill_handlers.chain_lightning(caster, v1)

    # The bounce subject ($n) is the invisible v2 — a witness sees "someone".
    assert "The bolt arcs to someone!" in witness.messages, witness.messages
    assert not any("Raider" in m for m in witness.messages), witness.messages
