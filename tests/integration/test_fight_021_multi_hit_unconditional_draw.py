"""FIGHT-021 — multi_hit second/third-attack number_percent() draws unconditionally.

ROM `src/fight.c` `multi_hit` (PC) and `mob_hit` (NPC) both resolve the second and
third extra attacks with::

    chance = get_skill (ch, gsn_second_attack) / 2;   /* or /4 for third */
    ...
    if (number_percent () < chance) { one_hit (...); ... }

`number_percent()` is the LEFT operand of the comparison, so the RNG draw fires on
*every* round even when ``chance == 0`` (an attacker with no second/third-attack
skill — most mobs and every low-level mage). The Python port guarded the draw
behind ``if skill > 0`` (`mud/combat/engine.py`), so a 0-skill attacker drew **two
fewer** values than ROM, desyncing the shared combat RNG stream for every
subsequent swing in the tick. Surfaced by the differential harness as FINDING-009
facet 1: with the drunk swinging first (FINDING-009 facet 3), the drunk's swing
consumed fewer draws than ROM's `mob_hit`, so the player's follow-up swing read a
shifted stream and resolved to a different hit/miss.

This test pins the ROM-faithful draw count: a skill-less, haste-less attacker must
still consume exactly two ``number_percent()`` draws (one per 2nd/3rd-attack check)
and land no extra swing.
"""

from __future__ import annotations

from mud.combat import engine
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


def test_multi_hit_draws_second_and_third_attack_unconditionally(monkeypatch):
    initialize_world()
    attacker = create_test_character("Attacker", 3001)
    victim = create_test_character("Victim", 3001)

    # A skill-less attacker: chance == 0 for both extra-attack checks.
    attacker.second_attack_skill = 0
    attacker.third_attack_skill = 0

    # multi_hit proceeds past the first swing only while attacker.fighting is the
    # same victim (ROM src/fight.c:212 `if (ch->fighting != victim) return;`).
    attacker.fighting = victim
    victim.fighting = attacker

    # Isolate multi_hit's OWN draws: stub the per-swing one_hit (attack_round) so
    # only the 2nd/3rd-attack number_percent() checks reach the counter. With
    # chance == 0 the comparison is always False, so no extra swing fires.
    monkeypatch.setattr(engine, "attack_round", lambda *_a, **_k: "")

    draws = {"n": 0}
    real_number_percent = rng_mm.number_percent

    def counting_number_percent():
        draws["n"] += 1
        return real_number_percent()

    monkeypatch.setattr(rng_mm, "number_percent", counting_number_percent)

    engine.multi_hit(attacker, victim)

    # ROM draws number_percent() for BOTH the second- and third-attack checks
    # regardless of skill (chance==0 still evaluates the left operand). Pre-fix
    # the guarded path drew 0; ROM-faithful is exactly 2.
    assert draws["n"] == 2, f"expected 2 unconditional 2nd/3rd-attack draws, got {draws['n']}"
