"""INV-026 — TRIG_FIGHT / TRIG_HPCNT fire only from violence_update.

ROM contract (``src/fight.c:60-99 violence_update``):

    multi_hit(ch, victim, TYPE_UNDEFINED);
    ...
    if ((victim = ch->fighting) == NULL) continue;   /* victim died */
    check_assist(ch, victim);
    if (IS_NPC(ch)) {
        if (HAS_TRIGGER(ch, TRIG_FIGHT))  mp_percent_trigger(ch, victim, ..., TRIG_FIGHT);
        if (HAS_TRIGGER(ch, TRIG_HPCNT))  mp_hprct_trigger(ch, victim);
    }

ROM fires these triggers ONLY from ``violence_update`` after ``multi_hit``
returns, ONLY when the victim is still fighting (skipped if victim died
during the round). They do NOT fire from any other caller of ``multi_hit``
(``do_kill``, ``assist``, ``spec_funs``, ``mob_cmds``).

Pre-INV-026 Python placed the dispatch at the end of
``mud/combat/engine.py:multi_hit`` (HPCNT-001's shallow enforcement
point), so the triggers fired from every caller of ``multi_hit`` —
including ``mud/combat/assist.py`` (assistant mobs joining combat),
``mud/spec_funs.py`` (special-function mob attacks), and
``mud/mob_cmds.py`` (``mob kill``). They also fired on a dead victim
if the killing blow landed during the round.

INV-026 moves the dispatch to ``mud/game_loop.py:violence_tick`` after
the ``multi_hit`` call, guarded by ``attacker.fighting is victim`` so a
victim killed during the round is skipped, matching ROM.
"""

from __future__ import annotations

import pytest

from mud import mobprog
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


def _record_triggers(monkeypatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(mobprog, "mp_fight_trigger", lambda mob, ch: (calls.append("fight"), False)[1])
    monkeypatch.setattr(mobprog, "mp_hprct_trigger", lambda mob, ch: (calls.append("hpcnt"), False)[1])
    monkeypatch.setattr(
        "mud.combat.engine.mobprog.mp_fight_trigger",
        lambda mob, ch: (calls.append("fight"), False)[1],
    )
    monkeypatch.setattr(
        "mud.combat.engine.mobprog.mp_hprct_trigger",
        lambda mob, ch: (calls.append("hpcnt"), False)[1],
    )
    return calls


def test_multi_hit_does_not_fire_fight_or_hpcnt_directly(monkeypatch) -> None:
    """``multi_hit`` itself must not dispatch TRIG_FIGHT / TRIG_HPCNT.

    ROM `src/fight.c:60-99` keeps the dispatch in ``violence_update``
    after ``multi_hit`` returns. Callers like ``assist`` and ``spec_funs``
    call ``multi_hit`` directly and must not provoke the triggers.
    """
    calls = _record_triggers(monkeypatch)
    monkeypatch.setattr(
        "mud.combat.engine.calculate_weapon_damage",
        lambda attacker, victim, dam_type, **kwargs: 5,
    )

    room = Room(vnum=99926, name="INV-026 probe")
    attacker = Character(name="AssistMob", is_npc=True, position=Position.STANDING)
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
        "ROM src/fight.c keeps TRIG_FIGHT/TRIG_HPCNT dispatch in "
        "violence_update, not multi_hit. Non-violence callers "
        f"(assist, spec_funs, mob_cmds) must not fire them; got {calls}"
    )


def test_violence_tick_fires_fight_and_hpcnt_on_npc_attacker(monkeypatch) -> None:
    """``violence_tick`` IS the ROM ``violence_update`` analog and must
    fire TRIG_FIGHT / TRIG_HPCNT on every NPC attacker still fighting
    after ``multi_hit`` returns. Mirrors ROM ``src/fight.c:92-98``.
    """
    from mud import game_loop

    calls = _record_triggers(monkeypatch)
    monkeypatch.setattr(
        "mud.combat.engine.calculate_weapon_damage",
        lambda attacker, victim, dam_type, **kwargs: 5,
    )

    room = Room(vnum=99927, name="INV-026 violence_tick")
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

    assert "fight" in calls, (
        f"ROM src/fight.c:94-95 fires TRIG_FIGHT from violence_update on the "
        f"NPC attacker after multi_hit returns; got {calls}"
    )
    assert "hpcnt" in calls, (
        f"ROM src/fight.c:96-97 fires TRIG_HPCNT from violence_update on the "
        f"NPC attacker after multi_hit returns; got {calls}"
    )


def test_violence_tick_skips_triggers_when_victim_died(monkeypatch) -> None:
    """If the victim died during ``multi_hit`` (``attacker.fighting``
    became ``None``), ``violence_tick`` must NOT fire TRIG_FIGHT /
    TRIG_HPCNT. Mirrors ROM ``src/fight.c:84-85`` —
    ``if ((victim = ch->fighting) == NULL) continue;``
    """
    from mud import game_loop

    calls = _record_triggers(monkeypatch)

    room = Room(vnum=99928, name="INV-026 victim died")
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

    # Stub multi_hit to simulate victim dying during the round (combat
    # ends, attacker.fighting cleared).
    def _kill_during_round(ch, vict, dt=None):
        ch.fighting = None
        vict.fighting = None
        vict.position = Position.DEAD
        return []

    monkeypatch.setattr("mud.combat.engine.multi_hit", _kill_during_round)

    game_loop.violence_tick(do_combat=True)

    assert calls == [], (
        f"ROM src/fight.c:84-85 skips TRIG_FIGHT / TRIG_HPCNT when the victim died during multi_hit; got {calls}"
    )
