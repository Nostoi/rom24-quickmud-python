"""HPCNT-001 — TRIG_HPCNT fires once per violence pulse, not per damage.

ROM ``src/fight.c:97`` is the **only** ``mp_hprct_trigger`` site in
the C codebase. It fires inside ``violence_update`` after
``multi_hit`` returns, exactly once per pulse per NPC, on the
NPC's per-pulse turn through the character list. ROM ``damage()``
(fight.c:825-870) drops victim hp, calls ``update_pos``, and
broadcasts the position line — it does NOT fire HPCNT on the
victim.

The Python ``mud/combat/engine.py:_apply_damage`` historically
fired ``mp_hprct_trigger(victim, attacker)`` on every damage
application against an NPC victim (with a misattributed
``ROM Reference: src/fight.c:1094-1136`` comment — that range is
``is_safe_spell``, not HPCNT). Symptoms: HP-percent mob scripts
that gate on ``hpcnt N`` would fire N+1 times per ``multi_hit``
(once per landed hit plus once at multi_hit's end), and would also
fire on spell-damage paths where ROM doesn't fire HPCNT at all.

The enforcement point is ``mud/combat/engine.py:multi_hit`` —
HPCNT fires exactly once there, on the NPC attacker, mirroring
ROM ``src/fight.c:91-98``. The ``_apply_damage`` site was
deleted.
"""

from __future__ import annotations

from mud import mobprog
from mud.combat.engine import attack_round, multi_hit
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room


def _record_hpcnt(monkeypatch) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []

    def _stub(mob, ch):
        calls.append((getattr(mob, "name", "?"), getattr(ch, "name", "?")))
        return False

    monkeypatch.setattr(mobprog, "mp_hprct_trigger", _stub)
    monkeypatch.setattr("mud.combat.engine.mobprog.mp_hprct_trigger", _stub)
    return calls


def test_hpcnt_does_not_fire_inside_apply_damage(monkeypatch) -> None:
    """A PC attacking an NPC victim must NOT trigger HPCNT inside
    ``_apply_damage``. ROM fires HPCNT only from ``violence_update``
    on the NPC attacker's turn; the victim-side firing was a Python
    divergence.
    """
    calls = _record_hpcnt(monkeypatch)
    monkeypatch.setattr(
        "mud.combat.engine.calculate_weapon_damage",
        lambda attacker, victim, dam_type, **kwargs: 5,
    )

    room = Room(vnum=99917, name="hpcnt probe room")
    attacker = Character(name="Hero", is_npc=False, position=Position.STANDING)
    attacker.level = 30
    attacker.hit = 100
    attacker.max_hit = 100
    attacker.hitroll = 100
    victim = Character(name="VictimMob", is_npc=True, position=Position.STANDING)
    victim.level = 1
    victim.hit = 50
    victim.max_hit = 50
    room.add_character(attacker)
    room.add_character(victim)

    attack_round(attacker, victim)

    assert calls == [], (
        "ROM src/fight.c:damage does not fire mp_hprct_trigger on the "
        f"victim NPC; got {len(calls)} call(s): {calls}"
    )


def test_hpcnt_fires_exactly_once_per_multi_hit(monkeypatch) -> None:
    """When an NPC attacker runs through ``multi_hit`` (the ROM
    violence_update path), HPCNT fires exactly once at the end —
    not once per landed hit. Mirrors ROM ``src/fight.c:91-98``.
    """
    calls = _record_hpcnt(monkeypatch)
    monkeypatch.setattr(
        "mud.combat.engine.calculate_weapon_damage",
        lambda attacker, victim, dam_type, **kwargs: 5,
    )

    room = Room(vnum=99918, name="hpcnt multi_hit room")
    attacker = Character(name="AttackerMob", is_npc=True, position=Position.STANDING)
    attacker.level = 30
    attacker.hit = 100
    attacker.max_hit = 100
    attacker.hitroll = 100
    attacker.second_attack_skill = 100
    attacker.third_attack_skill = 100
    victim = Character(name="VictimPC", is_npc=False, position=Position.STANDING)
    victim.level = 30
    victim.hit = 100
    victim.max_hit = 100
    room.add_character(attacker)
    room.add_character(victim)

    multi_hit(attacker, victim)

    assert len(calls) == 1, (
        "ROM src/fight.c:97 fires mp_hprct_trigger exactly once at the "
        f"end of multi_hit on the NPC attacker; got {len(calls)} call(s): "
        f"{calls}"
    )
    assert calls[0] == ("AttackerMob", "VictimPC"), (
        f"HPCNT must fire on (attacker NPC, victim) per ROM; got {calls[0]}"
    )
