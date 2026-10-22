"""FIGHT-097 — attack_round must carry ROM one_hit's opening guards.

ROM src/fight.c:426-437 one_hit:

    /* just in case */
    if (victim == ch || ch == NULL || victim == NULL)
        return;
    /*
     * Can't beat a dead char!
     * Guard against weird room-leavings.
     */
    if (victim->position == POS_DEAD || ch->in_room != victim->in_room)
        return;

The guards fire BEFORE any RNG draw, so a whiffed swing consumes ZERO values
from the shared Mitchell-Moore stream and never calls set_fighting. The
cross-room leg is load-bearing for FIGHT-095: ROM check_assist can
reservoir-pick a same-group target in another room; the follow-up
multi_hit -> one_hit silently whiffs (the check_assist_cross_room C golden
captures exactly this — scream, no damage, assister stays non-fighting).
"""

from __future__ import annotations

import pytest

from mud.combat.engine import attack_round
from mud.models.constants import Position
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world

_ROOM_A = 3001
_ROOM_B = 3008


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _fresh_stream_probe(seed: int) -> list[int]:
    rng_mm.seed_mm(seed)
    return [rng_mm.number_percent() for _ in range(3)]


def test_fight097_cross_room_swing_whiffs_with_zero_rng() -> None:
    """ch->in_room != victim->in_room → return before any draw (src/fight.c:436)."""
    attacker = create_test_character("Attacker", _ROOM_A)
    attacker.is_npc = True
    victim = create_test_character("Remote", _ROOM_B)
    victim.is_npc = False
    baseline_hp = victim.hit

    expected = _fresh_stream_probe(4242)

    rng_mm.seed_mm(4242)
    attack_round(attacker, victim)

    assert victim.hit == baseline_hp, "cross-room swing must not damage the victim"
    assert getattr(attacker, "fighting", None) is None, "whiff must not set_fighting"
    assert [rng_mm.number_percent() for _ in range(3)] == expected, (
        "cross-room whiff must consume ZERO shared-RNG draws (ROM one_hit returns "
        "before any roll) — a consumed draw desyncs every later swing in the tick"
    )


def test_fight097_self_swing_is_a_no_op() -> None:
    """victim == ch → return (src/fight.c:429)."""
    ch = create_test_character("Selfish", _ROOM_A)
    ch.is_npc = True
    baseline_hp = ch.hit

    expected = _fresh_stream_probe(777)
    rng_mm.seed_mm(777)
    attack_round(ch, ch)

    assert ch.hit == baseline_hp
    assert [rng_mm.number_percent() for _ in range(3)] == expected


def test_fight097_dead_victim_swing_is_a_no_op() -> None:
    """victim->position == POS_DEAD → return (src/fight.c:436)."""
    attacker = create_test_character("Basher", _ROOM_A)
    attacker.is_npc = True
    corpse = create_test_character("Corpse", _ROOM_A)
    corpse.position = Position.DEAD

    expected = _fresh_stream_probe(999)
    rng_mm.seed_mm(999)
    attack_round(attacker, corpse)

    assert getattr(attacker, "fighting", None) is None
    assert [rng_mm.number_percent() for _ in range(3)] == expected
