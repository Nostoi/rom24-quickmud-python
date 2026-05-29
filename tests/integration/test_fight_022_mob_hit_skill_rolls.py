"""FIGHT-022 — NPC mob_hit draws ROM's mob spell/skill rolls (FINDING-009 facet 1).

ROM `src/fight.c` routes NPC attackers through `mob_hit`, which after the
(unconditional, FIGHT-021) second/third-attack `number_percent()` checks rolls two
more values **when the mob is not waiting** (`if (ch->wait > 0) return;`):

    number = number_range (0, 2);   /* mob spell-cast check (casts stubbed in ROM) */
    ...
    number = number_range (0, 8);   /* off-skill dispatch by OFF_ flag */

Both draws happen even for a flag-less mob (no ACT_MAGE/CLERIC, no OFF_ skill
flags) — they are part of the shared combat RNG stream. The Python port had no NPC
`mob_hit` branch (`multi_hit` handled PC and NPC identically), so an NPC drew two
fewer `number_range` values than ROM per round, desyncing every later swing in the
tick. Surfaced by the differential harness `combat_melee_rounds`: the drunk #3064's
round consumed fewer draws than ROM `mob_hit`, so the player's follow-up swing read
a shifted stream.

These tests pin the ROM-faithful draw set for a flag-less mob and the `wait == 0`
gate that controls the two mob rolls.
"""

from __future__ import annotations

from mud.combat import engine
from mud.spawning.mob_spawner import spawn_mob
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


def _drunk_vs_victim():
    """The differential's combatants: drunk #3064 (no OFF_ skill / AREA_ATTACK /
    FAST flags, not ACT_MAGE/CLERIC) fighting a test PC in room 3008."""
    rng_mm.seed_mm(777)
    mob = spawn_mob(3064)
    assert mob is not None
    victim = create_test_character("Victim", 3008)
    victim.room.add_character(mob)
    mob.fighting = victim
    victim.fighting = mob
    return mob, victim


def _draw_counters(monkeypatch):
    """Count number_percent / number_range calls during mob_hit, isolating its own
    draws by stubbing attack_round (one_hit) to a no-op that draws nothing."""
    monkeypatch.setattr(engine, "attack_round", lambda *_a, **_k: "")
    counts = {"percent": 0, "range": 0}
    real_percent = rng_mm.number_percent
    real_range = rng_mm.number_range

    def counting_percent():
        counts["percent"] += 1
        return real_percent()

    def counting_range(low, high):
        counts["range"] += 1
        return real_range(low, high)

    monkeypatch.setattr(rng_mm, "number_percent", counting_percent)
    monkeypatch.setattr(rng_mm, "number_range", counting_range)
    return counts


def test_mob_hit_draws_spell_and_skill_rolls_when_not_waiting(monkeypatch):
    initialize_world()
    mob, victim = _drunk_vs_victim()
    mob.wait = 0  # gate open: ROM rolls the two mob checks

    counts = _draw_counters(monkeypatch)
    engine.mob_hit(mob, victim)

    # Second + third attack checks draw number_percent() unconditionally (FIGHT-021),
    # chance==0 for a skill-less mob so neither lands an extra swing.
    assert counts["percent"] == 2, counts
    # mob spell-cast number_range(0,2) + off-skill number_range(0,8) — both drawn
    # when wait==0; the flag-less drunk dispatches no skill, but the draws happen.
    assert counts["range"] == 2, counts


def test_mob_hit_skips_mob_skill_rolls_when_waiting(monkeypatch):
    initialize_world()
    mob, victim = _drunk_vs_victim()
    mob.wait = 10  # ROM src/fight.c mob_hit: `if (ch->wait > 0) return;` before the rolls

    counts = _draw_counters(monkeypatch)
    engine.mob_hit(mob, victim)

    # 2nd/3rd-attack draws still happen (they precede the wait gate)...
    assert counts["percent"] == 2, counts
    # ...but the two mob spell/skill number_range draws are gated out by wait > 0.
    assert counts["range"] == 0, counts
