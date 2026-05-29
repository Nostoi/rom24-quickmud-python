"""FIGHT-023 — mob dam_type is the ROM attack_table INDEX, not a DamageType class.

ROM stores ``ch->dam_type = attack_lookup(word)`` — an **attack_table index**
(`src/db2.c:270`, `src/handler.c:165`). `one_hit`/`dam_message` render the attack
noun as ``attack_table[ch->dam_type].noun`` (`src/fight.c:2176`), and derive the
damage *class* separately via ``attack_table[ch->dam_type].damage``
(`src/fight.c:431`). The drunk #3064's `.are` damtype word is "beating" →
``attack_lookup("beating") == 13`` → noun "beating", class DAM_BASH.

Python's `mud/spawning/templates.py` collapsed the index into a DamageType class
(`_resolve_damage_type` returned ``attack_damage_type(index)``), storing
``int(DamageType.BASH) == 1`` in `MobInstance.dam_type`. But `mud/combat/
engine.py` reads ``attacker.dam_type`` as an attack-table index, so the drunk
rendered ``attack_table[1].noun == "slice"`` instead of "beating" (FINDING-009
facet 2). The random-default block also assigned DamageType values
(``int(DamageType.SLASH/BASH/PIERCE) == 3/1/2``) where ROM `create_mobile`
(`src/db.c:2086-2099`) assigns attack-table indices ``3/7/11`` (slash/pound/
pierce).

These tests pin the contract: a spawned mob's `dam_type` is the ROM attack-table
index, and the random default uses ROM's literal indices {3, 7, 11}.
"""

from __future__ import annotations

from mud.combat.messages import TYPE_HIT, _resolve_attack_noun
from mud.models.constants import attack_lookup
from mud.models.mob import MobIndex
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.templates import MobInstance
from mud.utils import rng_mm
from mud.world import initialize_world


def test_drunk_dam_type_is_beating_attack_index():
    initialize_world()
    rng_mm.seed_mm(777)
    mob = spawn_mob(3064)  # the drunk — .are damtype word "beating"
    assert mob is not None

    # ROM: ch->dam_type = attack_lookup("beating") == 13 (an attack_table index),
    # NOT int(DamageType.BASH) == 1.
    assert mob.dam_type == attack_lookup("beating") == 13

    # one_hit renders the noun as attack_table[dam_type].noun (dt = TYPE_HIT +
    # dam_type). Index 13 → "beating"; the pre-fix index 1 rendered "slice".
    assert _resolve_attack_noun(TYPE_HIT + mob.dam_type) == "beating"


def test_random_default_dam_type_uses_rom_attack_indices():
    initialize_world()
    # A proto whose damtype resolves to 0 triggers ROM's random default
    # (src/db.c:2086-2099): number_range(1,3) → attack-table index 3/7/11
    # (slash/pound/pierce), NOT DamageType values 3/1/2.
    proto = MobIndex(
        vnum=99023,
        player_name="damtypemob",
        short_descr="a damtype default test mob",
        level=10,
        damage_type="none",  # resolves to 0 → random damtype roll
    )
    proto.hit = (1, 1, 10)
    proto.mana = (1, 1, 0)
    proto.damage = (1, 4, 0)

    rng_mm.seed_mm(777)
    mob = MobInstance.from_prototype(proto)

    # ROM assigns one of the attack-table indices {3 slash, 7 pound, 11 pierce}.
    assert mob.dam_type in {3, 7, 11}
    # And it must render a real ROM noun for that index (never the index-1 "slice"
    # the class-conflation produced for a BASH default).
    assert _resolve_attack_noun(TYPE_HIT + mob.dam_type) in {"slash", "pound", "pierce"}
