"""FIGHT-100 — damage() epilogue: wimpy auto-flee legs.

ROM src/fight.c:993-1012, immediately after the FIGHT-099 link-dead block:

    /*
     * Wimp out?
     */
    if (IS_NPC (victim) && dam > 0 && victim->wait < PULSE_VIOLENCE / 2)
    {
        if ((IS_SET (victim->act, ACT_WIMPY) && number_bits (2) == 0
             && victim->hit < victim->max_hit / 5)
            || (IS_AFFECTED (victim, AFF_CHARM) && victim->master != NULL
                && victim->master->in_room != victim->in_room))
            do_function (victim, &do_flee, "");
    }

    if (!IS_NPC (victim)
        && victim->hit > 0
        && victim->hit <= victim->wimpy && victim->wait < PULSE_VIOLENCE / 2)
        do_function (victim, &do_flee, "");

Three flee triggers after damage lands (victim alive, victim != ch):
(a) NPC ACT_WIMPY at hit < max_hit/5, 25% chance (number_bits(2) == 0);
(b) charmed NPC whose master is in another room (unconditional);
(c) PC with 0 < hit <= wimpy. All gated on wait < PULSE_VIOLENCE / 2.

Python's apply_damage had none of these — wimpy'd mobs and players never
auto-fled on damage. Sibling of FIGHT-099 (same contiguous ROM epilogue).
"""

from __future__ import annotations

import pytest

from mud.combat.engine import apply_damage, set_fighting
from mud.models.character import Character
from mud.models.constants import ActFlag, AffectFlag
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world

_ROOM = 3005


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _open_door(char: Character) -> int:
    """First exit index with an open to_room an NPC may flee into (no ROOM_NO_MOB)."""
    from mud.models.constants import RoomFlag

    for idx, ex in enumerate(getattr(char.room, "exits", []) or []):
        to_room = getattr(ex, "to_room", None) if ex is not None else None
        if to_room is None:
            continue
        if int(getattr(to_room, "room_flags", 0) or 0) & int(RoomFlag.ROOM_NO_MOB):
            continue
        return idx
    raise AssertionError("test room has no open NPC-fleeable exit")


def _combatants(name_v: str, name_a: str, *, victim_npc: bool) -> tuple[Character, Character]:
    victim = create_test_character(name_v, _ROOM)
    victim.is_npc = victim_npc
    victim.level = 10
    victim.max_hit = 100
    victim.hit = 100
    victim.wait = 0
    victim.move = 100  # flee pays a sector move cost for PCs (FIGHT-061)
    victim.max_move = 100
    victim.desc = object() if not victim_npc else None  # connected PC — isolate from FIGHT-099
    attacker = create_test_character(name_a, _ROOM)
    attacker.is_npc = True
    attacker.level = 10
    set_fighting(attacker, victim)
    return victim, attacker


def test_fight100_npc_wimpy_flees_at_low_hp(monkeypatch) -> None:
    """mirrors ROM src/fight.c:996-999 — ACT_WIMPY NPC below max_hit/5 with
    number_bits(2) == 0 flees after damage."""
    victim, attacker = _combatants("WimpyMob", "Bruiser", victim_npc=True)
    victim.act = int(getattr(victim, "act", 0) or 0) | int(ActFlag.WIMPY)
    victim.hit = 25  # 25 - 10 = 15 < 100/5 after damage

    door = _open_door(victim)
    monkeypatch.setattr(rng_mm, "number_bits", lambda _bits: 0)  # 25% roll hits
    monkeypatch.setattr(rng_mm, "number_door", lambda: door)

    apply_damage(attacker, victim, 10)

    assert victim.room is not None and victim.room.vnum != _ROOM, (
        "an ACT_WIMPY NPC below max_hit/5 must auto-flee after damage "
        f"(ROM src/fight.c:996-1004); still in {getattr(victim.room, 'vnum', None)}"
    )


def test_fight100_npc_wimpy_stays_above_threshold(monkeypatch) -> None:
    """hit >= max_hit/5 → the wimpy leg never fires, even with the roll made."""
    victim, attacker = _combatants("BraveMob", "Bruiser2", victim_npc=True)
    victim.act = int(getattr(victim, "act", 0) or 0) | int(ActFlag.WIMPY)
    victim.hit = 90  # 90 - 10 = 80 >= 20

    monkeypatch.setattr(rng_mm, "number_bits", lambda _bits: 0)
    monkeypatch.setattr(rng_mm, "number_door", lambda: _open_door(victim))

    apply_damage(attacker, victim, 10)

    assert victim.room is not None and victim.room.vnum == _ROOM


def test_fight100_charmed_npc_flees_when_master_absent(monkeypatch) -> None:
    """mirrors ROM src/fight.c:1000-1001 — a charmed NPC whose master is in
    ANOTHER room flees unconditionally (no wimpy flag, no hp threshold)."""
    victim, attacker = _combatants("Pet", "Bully", victim_npc=True)
    master = create_test_character("Owner", 3001)  # different room
    victim.affected_by = int(getattr(victim, "affected_by", 0) or 0) | int(AffectFlag.CHARM)
    victim.master = master
    victim.hit = 90  # well above the wimpy threshold — charm leg is hp-independent

    monkeypatch.setattr(rng_mm, "number_door", lambda: _open_door(victim))

    apply_damage(attacker, victim, 10)

    assert victim.room is not None and victim.room.vnum != _ROOM, (
        "a charmed NPC with an absent master must auto-flee after damage "
        f"(ROM src/fight.c:1000-1004); still in {getattr(victim.room, 'vnum', None)}"
    )


def test_fight100_pc_flees_at_or_below_wimpy(monkeypatch) -> None:
    """mirrors ROM src/fight.c:1007-1012 — a PC with 0 < hit <= wimpy and
    wait < PULSE_VIOLENCE / 2 flees after damage."""
    victim, attacker = _combatants("Cautious", "Mugger", victim_npc=False)
    victim.wimpy = 30
    victim.hit = 35  # 35 - 10 = 25 <= 30, and > 0

    monkeypatch.setattr(rng_mm, "number_door", lambda: _open_door(victim))

    apply_damage(attacker, victim, 10)

    assert victim.room is not None and victim.room.vnum != _ROOM, (
        "a PC at hit <= wimpy must auto-flee after damage "
        f"(ROM src/fight.c:1007-1012); still in {getattr(victim.room, 'vnum', None)}"
    )


def test_fight100_wait_gate_blocks_both_legs(monkeypatch) -> None:
    """wait >= PULSE_VIOLENCE / 2 suppresses both wimpy legs (ROM gates)."""
    victim, attacker = _combatants("Lagged", "Mugger2", victim_npc=False)
    victim.wimpy = 30
    victim.hit = 35
    victim.wait = 6  # PULSE_VIOLENCE(12) / 2

    monkeypatch.setattr(rng_mm, "number_door", lambda: _open_door(victim))

    apply_damage(attacker, victim, 10)

    assert victim.room is not None and victim.room.vnum == _ROOM, (
        f"wait >= PULSE_VIOLENCE/2 must suppress the auto-flee; ended in {getattr(victim.room, 'vnum', None)}"
    )
