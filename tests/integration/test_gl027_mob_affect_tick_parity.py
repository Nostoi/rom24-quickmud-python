"""GL-027 — a mob's spell affects must tick through ROM's affect loop, not the
dict-only fallback.

Production path: ~40 spell handlers call ``target.apply_spell_effect(effect)``.
For a mob that resolves to ``MobInstance.apply_spell_effect``
(``mud/spawning/templates.py``).  Before GL-027 the mob stored the effect in a
``spell_effects`` dict with **no** ``affected`` mirror, so ``char_update`` →
``tick_spell_effects`` (``mud/affects/engine.py``) routed it through the
**dict-only fallback**, which diverges from ROM's ``char_update`` affect loop
(``src/update.c:762-786``) in two ways:

  1. **RNG desync (the GL-026 contract).** ROM rolls ``number_range(0, 4)``
     unconditionally for every affect with ``duration > 0``.  The fallback
     decrements durations but rolls **zero** times — so a mob with K active
     affects consumed K rolls fewer than ROM, desyncing the global MM stream
     for every downstream consumer that tick (plague/poison damage, AoE saves,
     combat hit/miss) and beyond.

  2. **Off-by-one expiry.** ROM decrements-and-stays: a ``duration == 1`` affect
     decrements to 0 this tick and is removed only on a *later* tick when it is
     re-entered at ``duration == 0``.  The fallback removed it on the same tick
     (``1 → 0 → remove``), expiring mob debuffs one tick early.

The fix gives ``MobInstance`` a real ``affected`` list and syncs shadow
``AffectData`` on apply, so mobs collapse onto the main ``affected``-list path
(the same path PCs use, which already honors the GL-026 contract).

These tests assert the contract directly against ``tick_spell_effects`` —
mirroring ``test_gl026_affect_tick_rng_consumption.py``'s RNG-stream style —
using a **modifier-bearing** effect (a hitroll debuff), because a modifier-less
effect syncs no shadow and would silently exercise the wrong path.
"""

from __future__ import annotations

from mud.affects.engine import tick_spell_effects
from mud.models.character import SpellEffect
from mud.models.constants import AffectFlag
from mud.models.mob import MobIndex
from mud.spawning.templates import MobInstance
from mud.utils import rng_mm

_REF_SEED = 4242


def _mob() -> MobInstance:
    proto = MobIndex(vnum=9611, short_descr="a hapless mob", level=10)
    return MobInstance.from_prototype(proto)


def test_mob_duration_positive_affect_consumes_one_roll_per_affect():
    """A mob with one ``duration > 0`` affect must consume exactly one
    ``number_range(0, 4)`` roll per tick — the GL-026 contract.  The dict-only
    fallback consumed zero, desyncing the MM stream for the rest of the tick.
    """
    mob = _mob()
    # Modifier-bearing so the sync produces a shadow AffectData on mob.affected
    # (a modifier-less effect would route through the fallback and test nothing).
    mob.apply_spell_effect(SpellEffect(name="curse", duration=3, level=20, hitroll_mod=-5))

    # Reference: one number_range(0,4) draw, mirroring the ROM loop's single
    # per-affect roll, then three tail draws to fingerprint the stream position.
    rng_mm.seed_mm(_REF_SEED)
    reference = [rng_mm.number_range(0, 4) for _ in range(1 + 3)]

    rng_mm.seed_mm(_REF_SEED)
    tick_spell_effects(mob)
    tail = [rng_mm.number_range(0, 4) for _ in range(3)]

    assert tail == reference[1:4], (
        "mob affect tick must consume exactly one number_range roll (GL-026 contract); "
        f"stream tail {tail} != reference[1:] {reference[1:4]}"
    )


def test_mob_affect_decrements_and_stays_one_extra_tick():
    """ROM ``src/update.c:765-770`` decrements-and-stays: a ``duration == 1``
    affect must still be present after one tick (decrement to 0), and be removed
    only on a later tick.  The dict-only fallback removed it on the same tick.
    """
    mob = _mob()
    mob.apply_spell_effect(SpellEffect(name="curse", duration=1, level=20, hitroll_mod=-5))
    assert "curse" in mob.spell_effects

    # First tick: ROM decrements 1 -> 0 and KEEPS the affect (off-by-one in the
    # old fallback removed it here).
    tick_spell_effects(mob)
    assert "curse" in mob.spell_effects, "duration-1 affect must survive its first tick (decrement-and-stay)"

    # Second tick: re-entered at duration 0 -> removed, hitroll restored.
    tick_spell_effects(mob)
    assert "curse" not in mob.spell_effects, "affect must be removed on the later duration==0 tick"
    assert mob.hitroll == 0, "hitroll modifier must be unwound on removal"


def test_flag_only_affect_ticks_alongside_modifier_affect():
    """A flag-only buff (no numeric modifier) must keep ticking down even while
    a modifier-bearing affect is also active.

    Regression guard: routing mobs onto the main ``affected``-list path means an
    effect with no shadow AffectData would be invisible to that loop — so a
    flag-only effect (e.g. sanctuary) would freeze its duration for every tick a
    modifier-bearing affect kept ``affected`` non-empty (the old dict-only
    fallback, which iterated all ``spell_effects``, decremented it). The fix
    emits one base AffectData (APPLY_NONE) for modifier-less effects so they tick
    on the main path too. ROM ticks every affect on ``ch->affected`` regardless
    of modifier (src/update.c:762-786).
    """
    mob = _mob()
    mob.apply_spell_effect(SpellEffect(name="curse", duration=4, level=20, hitroll_mod=-5))
    mob.apply_spell_effect(SpellEffect(name="sanctuary", duration=1, level=20, affect_flag=AffectFlag.SANCTUARY))

    # sanctuary (duration 1) must decrement-and-stay one tick, then expire on the
    # next — NOT freeze behind curse (duration 4).
    for _ in range(2):
        tick_spell_effects(mob)

    assert "sanctuary" not in mob.spell_effects, "flag-only affect must not freeze behind a modifier-bearing affect"
    assert "curse" in mob.spell_effects, "the longer modifier-bearing affect should still be active"
    assert not mob.has_affect(AffectFlag.SANCTUARY), "expired sanctuary must clear its AFF bit"
