"""SPAWN-001 / FINDING-007 — mob spawn RNG draw-order must match ROM create_mobile.

ROM ``create_mobile`` (``src/db.c:2047-2113``) consumes the RNG in this order:

  1. gold/wealth — ``number_range(wealth/2, 3*wealth/2)`` then
     ``number_range(wealth/200, wealth/100)`` (the 2nd draw is a no-op when the
     rolled wealth is small enough that ``wealth/200 == wealth/100``);
  2. HP dice — ``dice(hit[NUMBER], hit[TYPE]) + hit[BONUS]``;
  3. mana dice — ``dice(mana[NUMBER], mana[TYPE]) + mana[BONUS]``;
  4. random damtype — ``number_range(1, 3)`` *only if* ``dam_type == 0``;
  5. random sex — ``number_range(1, 2)`` *only if* ``sex == 3`` (EITHER).

``MobInstance.from_prototype`` historically drew these in nearly the reverse
order (sex first, then damtype, then HP/mana, with gold last), so a seeded spawn
landed at a different RNG stream position for every draw — the drunk #3064 rolled
HP 33 in Python vs 31 in ROM C from the same seed. Surfaced by the differential
harness ``combat_melee_rounds`` scenario; see ``tools/diff_harness/FINDINGS.md``
FINDING-007 and ``docs/parity/DB_C_AUDIT.md`` SPAWN-001.

The replay below calls the *real* RNG primitives in ROM's order (never a
hardcoded draw count — ``number_range`` and ``dice`` short-circuit without
consuming the stream, so the count is data-dependent), then asserts the spawned
mob's rolled values match. The final sentinel draw locks the *total* draw count
and order: same seed + identical draw sequence ⇒ identical post-spawn RNG state.
"""

from __future__ import annotations

from mud.models.constants import Sex
from mud.models.mob import MobIndex
from mud.spawning.templates import MobInstance, _roll_dice
from mud.utils import rng_mm

SEED = 777


def _order_test_proto() -> MobIndex:
    """A prototype that exercises every reordered draw: real gold (wealth>0),
    HP/mana dice with size>1, dam_type==0 (random damtype), sex EITHER (random)."""
    proto = MobIndex(
        vnum=99001,
        player_name="ordermob",
        short_descr="an RNG order test mob",
        level=20,
        wealth=600,  # >0 -> ROM draws gold BEFORE the HP roll
        sex="either",  # Sex.EITHER -> ROM random-sex draw, drawn LAST
        damage_type="none",  # dam_type resolves to 0 -> ROM random-damtype draw
    )
    proto.hit = (4, 8, 30)  # 4d8+30 (size>1 -> real dice draws)
    proto.mana = (3, 5, 10)  # 3d5+10 (size>1 -> real dice draws)
    proto.damage = (2, 5, 6)
    return proto


def test_spawn_rng_draw_order_matches_rom_create_mobile():
    proto = _order_test_proto()
    wealth = proto.wealth

    # --- Replay ROM create_mobile draw order with the real primitives. ---
    rng_mm.seed_mm(SEED)
    # 1. gold/wealth (mirror from_prototype's exact arithmetic, ROM src/db.c:2055-2058)
    low = wealth // 2
    high = (3 * wealth) // 2
    if high < low:
        high = low
    total = rng_mm.number_range(low, high)
    gold_min = total // 200
    gold_max = max(total // 100, gold_min)
    exp_gold = rng_mm.number_range(gold_min, gold_max)
    exp_silver = max(total - exp_gold * 100, 0)
    # 2. HP dice, 3. mana dice (ROM src/db.c:2074-2082)
    exp_hp = _roll_dice((4, 8, 30))
    exp_mana = _roll_dice((3, 5, 10))
    # 4. random damtype (dam_type == 0), 5. random sex (sex == EITHER)
    rng_mm.number_range(1, 3)
    rng_mm.number_range(int(Sex.MALE), int(Sex.FEMALE))
    sentinel_replay = rng_mm.number_mm()

    # --- Spawn from the same seed; production must consume the same draws. ---
    rng_mm.seed_mm(SEED)
    mob = MobInstance.from_prototype(proto)
    sentinel_spawn = rng_mm.number_mm()

    # Per-field: HP/mana/gold land at the ROM stream positions.
    assert mob.max_hit == exp_hp, "HP roll must follow the two gold draws (ROM order)"
    assert mob.max_mana == exp_mana
    assert mob.gold == exp_gold
    assert mob.silver == exp_silver
    # Stream sentinel: total draw count AND order match ROM end-to-end (this also
    # locks the damtype-before-sex tail ordering, which no field assertion can).
    assert sentinel_spawn == sentinel_replay
