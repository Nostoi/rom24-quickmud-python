"""check_assist dispatch scope — ROM src/fight.c:90.

ROM contract (``src/fight.c:60-99 violence_update``)::

    multi_hit(ch, victim, TYPE_UNDEFINED);
    ...
    if ((victim = ch->fighting) == NULL) continue;   /* victim died */
    check_assist(ch, victim);
    if (IS_NPC(ch)) { TRIG_FIGHT / TRIG_HPCNT }

ROM calls ``check_assist`` from ``violence_update`` after ``multi_hit``
returns, NOT from inside ``multi_hit``. Non-violence callers of
``multi_hit`` (assist itself, ``spec_funs``, ``mob_cmds``) must not
provoke assist on every call — only the violence tick does.

Same misplacement shape as INV-026; intentionally split off for commit
hygiene. No new INV row (single-file move inside the existing combat
contract).
"""

from __future__ import annotations

import pytest

from mud.combat.engine import multi_hit
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def test_multi_hit_does_not_call_check_assist_directly(monkeypatch) -> None:
    """``multi_hit`` itself must not dispatch ``check_assist``.

    ROM ``src/fight.c:90`` keeps the call in ``violence_update`` after
    ``multi_hit`` returns. Callers like ``mud/combat/assist.py`` (the
    recursive assist round) and ``mud/spec_funs.py`` call ``multi_hit``
    directly and must not provoke another assist round.
    """
    calls: list[tuple[str, str]] = []

    def _record(ch, victim):
        calls.append((getattr(ch, "name", "?"), getattr(victim, "name", "?")))

    monkeypatch.setattr("mud.combat.assist.check_assist", _record)
    monkeypatch.setattr(
        "mud.combat.engine.calculate_weapon_damage",
        lambda attacker, victim, dam_type, **kwargs: 5,
    )

    room = Room(vnum=99930, name="check_assist probe")
    attacker = Character(name="Attacker", is_npc=True, position=Position.STANDING)
    attacker.level = 20
    attacker.hit = 100
    attacker.max_hit = 100
    attacker.hitroll = 100
    victim = Character(name="Victim", is_npc=False, position=Position.STANDING)
    victim.level = 20
    victim.hit = 100
    victim.max_hit = 100
    room.add_character(attacker)
    room.add_character(victim)

    multi_hit(attacker, victim)

    assert calls == [], (
        "ROM src/fight.c:90 keeps check_assist in violence_update, not "
        "multi_hit. Non-violence callers (assist, spec_funs, mob_cmds) "
        f"must not provoke it; got {calls}"
    )


def test_violence_tick_calls_check_assist_after_multi_hit(monkeypatch) -> None:
    """``violence_tick`` IS the ROM ``violence_update`` analog and must
    call ``check_assist`` once per round after ``multi_hit`` returns.
    Mirrors ROM ``src/fight.c:90``.
    """
    from mud import game_loop

    calls: list[tuple[str, str]] = []

    def _record(ch, victim):
        calls.append((getattr(ch, "name", "?"), getattr(victim, "name", "?")))

    monkeypatch.setattr("mud.combat.assist.check_assist", _record)
    monkeypatch.setattr(
        "mud.combat.engine.calculate_weapon_damage",
        lambda attacker, victim, dam_type, **kwargs: 5,
    )

    room = Room(vnum=99931, name="check_assist violence_tick")
    attacker = Character(name="Guard", is_npc=True, position=Position.STANDING)
    attacker.level = 20
    attacker.hit = 100
    attacker.max_hit = 100
    attacker.hitroll = 100
    victim = Character(name="Hero", is_npc=False, position=Position.STANDING)
    victim.level = 20
    victim.hit = 100
    victim.max_hit = 100
    room.add_character(attacker)
    room.add_character(victim)
    character_registry.append(attacker)
    character_registry.append(victim)

    attacker.fighting = victim
    victim.fighting = attacker

    game_loop.violence_tick(do_combat=True)

    assert ("Guard", "Hero") in calls, (
        f"ROM src/fight.c:90 calls check_assist(ch, victim) from violence_update after multi_hit returns; got {calls}"
    )


def test_violence_tick_skips_check_assist_when_victim_died(monkeypatch) -> None:
    """If the victim died during ``multi_hit`` (``attacker.fighting``
    became ``None``), ``violence_tick`` must NOT call ``check_assist``.
    Mirrors ROM ``src/fight.c:84-85`` —
    ``if ((victim = ch->fighting) == NULL) continue;``
    """
    from mud import game_loop

    calls: list[tuple[str, str]] = []

    def _record(ch, victim):
        calls.append((getattr(ch, "name", "?"), getattr(victim, "name", "?")))

    monkeypatch.setattr("mud.combat.assist.check_assist", _record)

    room = Room(vnum=99932, name="check_assist victim died")
    attacker = Character(name="Killer", is_npc=True, position=Position.STANDING)
    attacker.level = 20
    attacker.hit = 100
    attacker.max_hit = 100
    victim = Character(name="Doomed", is_npc=False, position=Position.STANDING)
    victim.level = 1
    victim.hit = 1
    victim.max_hit = 1
    room.add_character(attacker)
    room.add_character(victim)
    character_registry.append(attacker)
    character_registry.append(victim)

    attacker.fighting = victim
    victim.fighting = attacker

    def _kill_during_round(ch, vict, dt=None):
        ch.fighting = None
        vict.fighting = None
        vict.position = Position.DEAD
        return []

    monkeypatch.setattr("mud.combat.engine.multi_hit", _kill_during_round)

    game_loop.violence_tick(do_combat=True)

    assert calls == [], f"ROM src/fight.c:84-85 skips check_assist when the victim died during multi_hit; got {calls}"
