"""FIGHT-027 — unarmed NPC damage rolls the mob damage dice, not the PC formula
(FINDING-010).

ROM `src/fight.c:522-560` `one_hit` routes an NPC attacker with no wielded weapon
through a dedicated branch:

    if (IS_NPC (ch) && (!ch->pIndexData->new_format || wield == NULL))
        if (!ch->pIndexData->new_format)
            dam = number_range (ch->level / 2, ch->level * 3 / 2);   /* old format */
        else
            dam = dice (ch->damage[DICE_NUMBER], ch->damage[DICE_TYPE]);
    else
        ...
        else  /* PC, unarmed */
            dam = number_range (1 + 4*skill/100, 2*ch->level/3*skill/100);

ROM `convert_mobile` (src/db.c) upgrades *every* mob to `new_format` at load, so the
runtime path is always `dice(damage[DICE_NUMBER], damage[DICE_TYPE])`.

Before the fix `calculate_weapon_damage` had no NPC branch, so an unarmed mob fell
through to the PC-unarmed formula. For the drunk #3064 (level 2, damage dice 1d6)
that resolves to a degenerate `number_range(3, 0)` → ROM returns `from` = constant 3,
consuming **zero** RNG draws — so the drunk dealt a constant 3 every hit (and the
missing draw desynced the shared combat stream). ROM rolls `dice(1, 6)` (range 1–6,
one `number_mm` draw).

Surfaced by the differential harness `combat_melee_rounds` step 6: C
"beating scratches you" (1 dmg) vs py "beating hits you" (3 dmg).
"""

from __future__ import annotations

from mud.combat import engine
from mud.models.constants import DamageType
from mud.spawning.mob_spawner import spawn_mob
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


def _drunk_vs_victim():
    """The differential's combatants: drunk #3064 (unarmed, damage dice 1d6) vs a
    test PC in room 3008, both FIGHTING (no position damage multiplier)."""
    mob = spawn_mob(3064)
    assert mob is not None
    victim = create_test_character("Victim", 3008)
    victim.room.add_character(mob)
    return mob, victim


def test_unarmed_npc_damage_spans_its_damage_dice_range():
    """An unarmed mob's base damage must come from dice(DICE_NUMBER, DICE_TYPE).

    dice(1, 6) yields up to 6 distinct values (1–6). The buggy PC-unarmed path
    resolves to a degenerate `number_range(3, 0)` → a single constant (no RNG drawn),
    and the old-format `number_range(level/2, level*3/2)` would span only 1–3 for a
    level-2 mob. Observing ≥4 distinct damage values rules out both: only `dice(1, 6)`
    can produce that spread.
    """
    initialize_world()
    mob, victim = _drunk_vs_victim()
    # Drunk #3064 carries damage dice 1d6 (mirrors ROM ch->damage[] post-convert_mobile).
    assert tuple(mob.damage[:2]) == (1, 6), mob.damage

    seen = set()
    for seed in range(300):
        rng_mm.seed_mm(seed)
        dam = engine.calculate_weapon_damage(mob, victim, int(DamageType.BASH))
        seen.add(dam)

    # Buggy code draws no RNG → exactly one constant value. dice(1,6) varies widely.
    assert len(seen) >= 4, f"expected dice(1,6) spread, got {sorted(seen)}"


def test_unarmed_npc_consumes_one_dice_draw(monkeypatch):
    """ROM dice(1,6) consumes exactly one number_mm draw (one number_range(1,6)); the
    degenerate PC-unarmed `number_range(3,0)` consumes none. The missing draw is what
    desynced the combat-tick RNG stream after round 1 in FINDING-010."""
    initialize_world()
    mob, victim = _drunk_vs_victim()

    count = {"mm": 0}
    real_mm = rng_mm.number_mm

    def counting_mm():
        count["mm"] += 1
        return real_mm()

    monkeypatch.setattr(rng_mm, "number_mm", counting_mm)
    rng_mm.seed_mm(777)
    engine.calculate_weapon_damage(mob, victim, int(DamageType.BASH))

    # One die of size 6 → one number_range(1,6) → one number_mm draw. A skill-less mob
    # has no enhanced-damage skill, so no other draw fires in this path.
    assert count["mm"] == 1, count
