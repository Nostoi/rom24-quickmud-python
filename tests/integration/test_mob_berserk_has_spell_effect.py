"""MOB-BERSERK-001 — `MobInstance` must support `has_spell_effect`.

ROM routes an OFF_BERSERK mob through `mob_hit` → `do_berserk` (src/fight.c
`mob_hit` off-skill switch). `mud/commands/combat.py:do_berserk` guards on
`char.has_spell_effect("berserk")` (the `is_affected(ch, gsn_berserk)` analogue).
`MobInstance` defined `has_affect`, `apply_spell_effect`, and
`remove_spell_effect` but **not** `has_spell_effect`, so the moment a berserker
mob's offensive roll landed on the berserk case the call raised
`AttributeError` — and because neither the per-character combat loop nor the
`char_update()`/`violence_tick()` call in `game_tick` is wrapped in try/except,
the exception propagated out of the entire game tick (same blast radius as
GL-028). Observed live: a berserker mob fighting a player crashed the loop every
round.
"""

from __future__ import annotations

from mud.commands.combat import do_berserk
from mud.models.constants import OffFlag, Position
from mud.spawning.mob_spawner import spawn_mob
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


def test_mob_has_spell_effect_does_not_crash_do_berserk():
    initialize_world()
    rng_mm.seed_mm(12345)

    mob = spawn_mob(3064)
    assert mob is not None

    victim = create_test_character("Victim", 3008)
    victim.room.add_character(mob)

    # OFF_BERSERK + enough mana so do_berserk reaches the has_spell_effect guard.
    mob.off_flags = int(OffFlag.BERSERK)
    mob.mana = 100
    mob.max_mana = 100
    mob.wait = 0
    mob.position = int(Position.FIGHTING)
    mob.fighting = victim
    victim.fighting = mob

    # has_spell_effect is the ROM is_affected(ch, gsn_berserk) guard. Pre-fix this
    # raised AttributeError on MobInstance.
    assert mob.has_spell_effect("berserk") is False

    # The full command path must not raise.
    result = do_berserk(mob, "")
    assert isinstance(result, str)
