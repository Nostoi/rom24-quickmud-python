"""GL-028 — a spell cast on a mob must tick to expiry without crashing the loop.

Production path: ~40 spell handlers call ``target.apply_spell_effect(effect)``.
When the target is a mob, that resolves to ``MobInstance.apply_spell_effect``
(``mud/spawning/templates.py``), which stores the effect in the mob's
``spell_effects`` dict but — unlike ``Character.apply_spell_effect`` — does
NOT mirror it into an ``affected`` list. ``char_update`` then ticks the whole
``character_registry`` (mobs included) through
``tick_spell_effects``; with an empty/absent ``affected`` list the mob routes
through the **dict-only fallback** (``mud/affects/engine.py``), which calls
``character.remove_spell_effect(name)`` on expiry.

``MobInstance`` has no ``remove_spell_effect`` method, so the fallback raises
``AttributeError`` the moment any mob's spell effect expires. Because
``char_update`` (``mud/game_loop.py``) wraps neither its per-character loop
body nor the ``char_update()`` call in ``game_tick`` in a ``try/except``, the
exception propagates out of the whole tick — every character after the mob in
the registry is skipped, along with ``obj_update``/``pump_idle``/
``aggressive_update`` for that tick.

This test drives the real ``char_update`` tick and asserts the effect ticks to
expiry without an exception escaping, and is then gone.
"""

from __future__ import annotations

import pytest

from mud.game_loop import char_update
from mud.models.character import SpellEffect, character_registry
from mud.models.constants import Position
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.registry import room_registry
from mud.spawning.templates import MobInstance


@pytest.fixture(autouse=True)
def _isolate_registries():
    chars = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(chars)
    room_registry.pop(9610, None)


def _spawn_mob_in_room() -> MobInstance:
    room = Room(vnum=9610, name="Test Cell", description="", room_flags=0, sector_type=0)
    room.people = []
    room_registry[9610] = room

    proto = MobIndex(vnum=9611, short_descr="a hapless mob", level=10)
    mob = MobInstance.from_prototype(proto)
    mob.position = int(Position.STANDING)
    mob.room = room
    # zone == room.area so the GL-009 "wanders home" extract branch is skipped
    mob.zone = getattr(room, "area", None)
    room.people.append(mob)
    character_registry.append(mob)
    return mob


def test_mob_spell_effect_ticks_to_expiry_without_crashing():
    """A short-duration debuff cast on a mob must tick to expiry without an
    exception escaping char_update, and then be gone.

    The assertion is bounded-ticks rather than exactly-one-tick on purpose:
    the dict-only fallback currently expires a duration-1 affect on the first
    tick (off-by-one vs ROM's decrement-and-stay / expire-when-zero), tracked
    separately — this test must stay green under either timing so it keeps
    testing the crash-free-expiry contract, not the buggy timing."""
    mob = _spawn_mob_in_room()
    # Faithful to the production cast path (every spell handler does this).
    mob.apply_spell_effect(
        SpellEffect(name="weaken", duration=1, level=20, wear_off_message="You feel stronger.")
    )
    assert "weaken" in mob.spell_effects

    # Tick a bounded number of times; none may raise out of char_update.
    for _ in range(4):
        char_update()
        if "weaken" not in mob.spell_effects:
            break

    assert "weaken" not in mob.spell_effects, "expired mob spell effect should be removed within a few ticks"
    assert mob in character_registry, "mob must survive the tick"
