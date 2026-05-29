"""FIGHT-019 — ROM `one_hit` THAC0 attack roll is the only melee-hit model.

ROM `src/fight.c:386-516` resolves every swing through a single model: the
THAC0 / `number_bits(5)` attack roll (re-roll loop until `< 20`, then miss on
`diceroll == 0` or `diceroll != 19 && diceroll < thac0 - victim_ac`). The Python
port historically shipped a *non-ROM* percent model (`50 + hitroll + AC/2`,
rolled with `number_percent()`) behind `COMBAT_USE_THAC0`, defaulted off — a pure
divergence both in the RNG draw and the hit/miss decision.

Surfaced by the differential harness (FINDING-008): from seed 777 the drunk
#3064's first incoming attack is a **miss** in ROM C but registered a **hit**
("scratch") under the Python percent model. This test pins the ROM-faithful
outcome so the percent model cannot silently return.
"""

from __future__ import annotations

from mud.combat import engine
from mud.spawning.mob_spawner import spawn_mob
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


def _scenario_char():
    """The differential harness's test PC (tools/diff_harness, FINDING-008):
    class 0 (mage), perm_stat all 13 with INT +3, no gear, level 5, ROM
    new_char() pool defaults."""
    char = create_test_character("Tester", 3008)
    char.level = 5
    char.max_hit = char.hit = 20
    char.max_mana = char.mana = 100
    char.max_move = char.move = 100
    char.ch_class = 0
    char.perm_stat = [13, 16, 13, 13, 13]  # ROM order STR, INT, WIS, DEX, CON
    char.hitroll = 0
    char.damroll = 0
    char.armor = [100, 100, 100, 100]
    return char


def test_fight_019_seed_777_first_attack_is_a_miss():
    """Reproduces the harness scenario `combat_melee_rounds` step 4: seed 777,
    spawn drunk #3064, then resolve the player's first swing. ROM C produces
    `You miss the drunk.`; the retired percent model produced a `scratch` (hit)."""
    initialize_world()
    char = _scenario_char()

    # __seed=777 ; __mload=3064 — the spawn consumes the RNG stream identically
    # to the C shim's __mload (SPAWN-001 / FINDING-007 aligned the draw order).
    rng_mm.seed_mm(777)
    drunk = spawn_mob(3064)
    assert drunk is not None
    char.room.add_character(drunk)

    # __seed=777 — combat resolves from a fresh, known RNG state.
    rng_mm.seed_mm(777)
    results = engine.multi_hit(char, drunk)

    # ROM multi_hit fires exactly one one_hit for a skill-less, haste-less L5
    # mage (src/fight.c:209-246) — a single result line, not a double-send.
    assert len(results) == 1, results
    line = results[0]
    assert "miss" in line.lower(), f"expected a ROM miss, got {line!r}"
    assert "scratch" not in line.lower(), f"percent-model hit leaked back: {line!r}"


def test_fight_019_npc_attacker_thac0_pair_from_act_flag(monkeypatch):
    """ROM src/fight.c:445-457 — an NPC attacker's (thac0_00, thac0_32) comes from
    its ACT class flag (thac0_00 always 20; thac0_32 = -10 WARRIOR / 6 MAGE), not
    the PC class table. attack_round must select the pair from the mob's act flags;
    the retired percent model never reached compute_thac0, so this path was untested
    until THAC0 became the only model."""
    from mud.models.constants import ActFlag

    initialize_world()
    victim = _scenario_char()
    rng_mm.seed_mm(777)
    mob = spawn_mob(3064)
    assert mob is not None
    victim.room.add_character(mob)

    captured: dict[str, tuple[int, int] | None] = {}
    real_compute_thac0 = engine.compute_thac0

    def spy(level, ch_class, *, hitroll, skill, thac0_pair=None):
        captured["pair"] = thac0_pair
        return real_compute_thac0(level, ch_class, hitroll=hitroll, skill=skill, thac0_pair=thac0_pair)

    monkeypatch.setattr(engine, "compute_thac0", spy)

    mob.act = int(ActFlag.IS_NPC | ActFlag.WARRIOR)
    engine.attack_round(mob, victim)
    assert captured["pair"] == (20, -10)

    mob.act = int(ActFlag.IS_NPC | ActFlag.MAGE)
    engine.attack_round(mob, victim)
    assert captured["pair"] == (20, 6)
