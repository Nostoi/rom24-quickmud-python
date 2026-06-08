"""INV-040 AFFECT-TO-CHAR-FULL-APPLY enforcement.

ROM ``src/handler.c:1266-1280 affect_to_char`` does two things:

1. Head-inserts into ``ch->affected``
2. Calls ``affect_modify(ch, paf, TRUE)`` — applies stat modifiers AND bitvectors

Python's ``Character.affect_to_char`` (mud/models/character.py) only OR-sets
``affected_by`` directly but skips ``affect_modify``, so any stat-modifier
carried by the AffectData (e.g. plague spread's APPLY_STR -5) is silently
dropped.

Additionally, ``mud/game_loop.py`` constructs the spread AffectData with
``location="str"`` (a string) instead of the integer constant ``APPLY_STR=1``,
so even if ``affect_modify`` were called, ``paf.location == 1`` evaluates False
and the modifier is still dropped.

ROM-observable contract: when plague spreads to a victim, the victim must
receive both the AFF_PLAGUE bitvector **and** the -5 STR modifier.
Enforcement points: ``mud/models/character.py:Character.affect_to_char`` +
``mud/game_loop.py`` plague-spread AffectData construction.
"""

from __future__ import annotations

import pytest

from mud.models.character import AffectData, Character, character_registry
from mud.models.constants import AffectFlag, Position, Stat
from mud.models.room import Room
from mud.registry import room_registry

_ROOM_VNUM = 9210


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)
    room_registry.pop(_ROOM_VNUM, None)


def _make_room() -> Room:
    room = Room(vnum=_ROOM_VNUM, name="INV-040 Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[_ROOM_VNUM] = room
    return room


def test_plague_spread_applies_str_modifier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plague spread must apply -5 STR via affect_modify, not just set AFF_PLAGUE.

    # mirrors ROM src/update.c:828-841 (plague spread) + src/handler.c:1278 (affect_to_char -> affect_modify)
    """
    from mud import game_loop as gl
    from mud.affects import saves as saves_module
    from mud.game_loop import _char_update_tick_effects

    room = _make_room()

    carrier = Character(
        name="Carrier",
        short_descr="Carrier",
        level=10,
        room=room,
        is_npc=True,
        hit=200,
        max_hit=200,
        mana=50,
        max_mana=50,
        move=50,
        max_move=50,
        position=int(Position.STANDING),
    )
    carrier.affected_by = int(AffectFlag.PLAGUE)
    carrier.affected = [
        AffectData(
            type="plague",
            level=10,
            duration=5,
            location=0,  # APPLY_NONE — carrier's affect entry, modifier tracking handled separately
            modifier=0,
            bitvector=int(AffectFlag.PLAGUE),
        )
    ]
    room.people.append(carrier)
    character_registry.append(carrier)

    victim = Character(
        name="Victim",
        short_descr="Victim",
        level=1,
        room=room,
        is_npc=True,
        hit=100,
        max_hit=100,
        mana=50,
        max_mana=50,
        move=50,
        max_move=50,
        position=int(Position.STANDING),
    )
    victim._ensure_mod_stat_capacity()
    baseline_str = victim.mod_stat[int(Stat.STR)]
    room.people.append(victim)
    character_registry.append(victim)

    # Force spread: number_bits(4) == 0 (1/16 chance gate) and saves_spell returns False.
    monkeypatch.setattr(gl.rng_mm, "number_bits", lambda _bits: 0)
    monkeypatch.setattr(gl.rng_mm, "number_range", lambda _lo, hi: hi)
    monkeypatch.setattr(saves_module, "saves_spell", lambda *_a, **_kw: False)

    _char_update_tick_effects(carrier)

    # Bitvector side — expected to already work (confirm it still does):
    assert victim.has_affect(AffectFlag.PLAGUE), "plague spread must set AFF_PLAGUE bitvector on victim"

    # Stat-mod side — INV-040 enforcement:
    # ROM src/handler.c:1278 affect_to_char calls affect_modify(ch, paf_new, TRUE),
    # which subtracts 5 from mod_stat[STR].  Python affect_to_char skips this call,
    # so the -5 STR is currently silently dropped.
    assert victim.mod_stat[int(Stat.STR)] == baseline_str - 5, (
        f"plague spread must apply -5 STR via affect_modify "
        f"(ROM src/handler.c:1278 affect_to_char -> affect_modify(TRUE)); "
        f"expected {baseline_str - 5}, got {victim.mod_stat[int(Stat.STR)]}"
    )


def test_affect_to_char_applies_stat_modifier_directly() -> None:
    """affect_to_char must apply the AffectData's stat modifier immediately.

    # mirrors ROM src/handler.c:1278 — affect_to_char calls affect_modify(TRUE)
    """
    ch = Character(name="test-pc", is_npc=False)
    ch._ensure_mod_stat_capacity()
    baseline_str = ch.mod_stat[int(Stat.STR)]

    affect = AffectData(
        type=1,  # integer SN — ROM-canonical form
        level=10,
        duration=5,
        location=1,  # APPLY_STR
        modifier=-3,
        bitvector=int(AffectFlag.HASTE),
        where=0,  # TO_AFFECTS
    )
    ch.affect_to_char(affect)

    assert ch.mod_stat[int(Stat.STR)] == baseline_str - 3, (
        "affect_to_char must call affect_modify(TRUE) to apply stat modifier "
        "(ROM src/handler.c:1278); currently only bitvector is applied"
    )
    assert ch.affected_by & int(AffectFlag.HASTE), "bitvector must also be set"
    assert affect in ch.affected, "affect must be added to ch.affected"
