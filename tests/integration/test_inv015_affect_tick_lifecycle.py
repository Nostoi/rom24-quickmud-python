"""INV-015 AFFECT-TICK-LIFECYCLE enforcement.

ROM ``src/update.c:762-786 affect_update`` decrements each
``ch->affected`` entry's duration; on expiry it calls
``src/handler.c:1317 affect_remove``, which in turn:

1. calls ``affect_modify(ch, paf, FALSE)`` — subtracts the stat
   modifier (``mod_stat[STR] -= mod``) AND clears the bitvector in
   ``ch->affected_by`` (handler.c:1110-1117);
2. unlinks the affect from ``ch->affected``;
3. calls ``affect_check(ch, where, vector)``, which re-sets the
   bitvector ONLY if another affect (on ``ch`` or on equipped
   objects) still provides it.

The Python tick path at ``mud/affects/engine.py:tick_spell_effects``
historically just did ``affected.remove(affect)`` on expiry. When the
``AffectData`` carried an integer ``type`` (the ROM-canonical form,
since ``type`` is a spell SN per ``src/merc.h:648-659``), the parallel
``spell_effects`` cleanup at engine.py:55-68 never fired, because the
``isinstance(spell_name, str)`` guard skipped non-string types. Net:
the bitvector leaked into ``affected_by`` permanently, and any stat
modifier applied via ``affect_modify(TRUE)`` was never undone.

This test pins the contract: after enough ticks to expire an Affect
that was applied via the canonical ``affect_modify`` + list append
sequence, the stat mod must be undone and the bitvector must be
clear. Add a test here when introducing a new path that decrements
``AffectData.duration`` to zero.
"""

from __future__ import annotations

from mud.affects.engine import tick_spell_effects
from mud.handler import affect_modify
from mud.models.character import AffectData, Character
from mud.models.constants import AffectFlag, Stat
from mud.utils import rng_mm

APPLY_STR = 1
TO_AFFECTS = 0


def _build_char() -> Character:
    ch = Character(name="affect-tick-pc", is_npc=False)
    ch._ensure_mod_stat_capacity()
    return ch


def test_affect_with_stat_mod_undoes_on_tick_expiry() -> None:
    """A +2 STR / AFF_HASTE affect with duration=1 must fully unwind
    after two ticks: the +2 must be subtracted from mod_stat[STR] and
    the HASTE bit must be cleared from affected_by."""

    ch = _build_char()
    baseline_str = ch.mod_stat[int(Stat.STR)]
    baseline_affected_by = ch.affected_by

    affect = AffectData(
        type=1,  # ROM spell SN — integer, NOT a string spell name
        level=10,
        duration=1,
        location=APPLY_STR,
        modifier=2,
        bitvector=int(AffectFlag.HASTE),
        where=TO_AFFECTS,
    )

    # Canonical apply: affect_modify(True) updates mod_stat AND
    # affected_by, then append to ch.affected (ROM affect_to_char).
    affect_modify(ch, affect, True)  # type: ignore[arg-type]  # duck-typed: AffectData vs Affect
    ch.affected.append(affect)

    assert ch.mod_stat[int(Stat.STR)] == baseline_str + 2
    assert ch.affected_by & int(AffectFlag.HASTE)
    assert affect in ch.affected

    # Tick 1: duration 1 -> 0, affect stays in list.
    tick_spell_effects(ch)
    assert affect in ch.affected
    assert affect.duration == 0

    # Tick 2: duration == 0, ROM removes via affect_remove.
    tick_spell_effects(ch)

    # ROM contract — all three must hold:
    assert affect not in ch.affected, "expired affect must be unlinked"
    assert ch.affected_by & int(AffectFlag.HASTE) == 0, (
        "expired affect's bitvector must clear from affected_by "
        "(src/handler.c:1317 affect_remove -> affect_modify(FALSE))"
    )
    assert ch.mod_stat[int(Stat.STR)] == baseline_str, (
        "expired affect's stat modifier must be subtracted (src/handler.c:1317 affect_remove -> affect_modify(FALSE))"
    )
    assert ch.affected_by == baseline_affected_by


def test_affect_check_preserves_bit_if_another_affect_provides_it() -> None:
    """When two affects share a bitvector and only one expires, the
    bit must remain set — ROM ``affect_check`` (src/handler.c:1182)
    re-sets it after ``affect_modify(FALSE)`` clears it."""

    ch = _build_char()

    short = AffectData(
        type=1,
        level=10,
        duration=1,
        location=APPLY_STR,
        modifier=2,
        bitvector=int(AffectFlag.HASTE),
        where=TO_AFFECTS,
    )
    long = AffectData(
        type=2,
        level=10,
        duration=10,
        location=APPLY_STR,
        modifier=3,
        bitvector=int(AffectFlag.HASTE),
        where=TO_AFFECTS,
    )

    affect_modify(ch, short, True)  # type: ignore[arg-type]
    ch.affected.append(short)
    affect_modify(ch, long, True)  # type: ignore[arg-type]
    ch.affected.append(long)

    baseline_str_with_long_only = ch.mod_stat[int(Stat.STR)] - 2  # subtract short's +2

    # Tick short to expiry.
    tick_spell_effects(ch)
    tick_spell_effects(ch)

    assert short not in ch.affected
    assert long in ch.affected
    assert ch.affected_by & int(AffectFlag.HASTE), (
        "HASTE bit must survive — `long` still provides it (src/handler.c:1182 affect_check re-sets after clear)"
    )
    assert ch.mod_stat[int(Stat.STR)] == baseline_str_with_long_only, (
        "only short's +2 must unwind; long's +3 must remain"
    )


def test_rng_slot_consumed_per_duration_positive_affect() -> None:
    """ROM src/update.c:768 — number_range(0,4) is called unconditionally
    for every duration>0 affect, BEFORE the level>0 check (GL-026).

    C ``&&`` is left-to-right: ``if (number_range(0,4) == 0 && paf->level > 0)``
    always advances the MM state, even when level == 0 makes the whole condition
    False.  If the Python operands were swapped (``level > 0 and
    number_range(0,4)``), level=0 affects would skip the roll, silently
    desyncing the global RNG stream for all downstream callers in the same tick.

    Verify: two duration>0 affects (one at level=10, one at level=0) must
    together consume exactly TWO RNG slots.
    """
    rng_mm.seed_mm(7777)
    rng_mm.number_range(0, 4)  # slot consumed by affect_high_level tick
    rng_mm.number_range(0, 4)  # slot consumed by affect_zero_level tick
    expected_v3 = rng_mm.number_range(0, 4)  # first post-tick value

    rng_mm.seed_mm(7777)
    ch = _build_char()

    affect_high_level = AffectData(type=1, level=10, duration=2, location=0, modifier=0, bitvector=0)
    affect_zero_level = AffectData(type=2, level=0, duration=2, location=0, modifier=0, bitvector=0)
    ch.affected.append(affect_high_level)
    ch.affected.append(affect_zero_level)

    tick_spell_effects(ch)  # must consume exactly 2 RNG slots

    # GL-026 regression guard: if operands were swapped, only 1 slot consumed
    # and the next call would return expected_v2 (not expected_v3).
    next_val = rng_mm.number_range(0, 4)
    assert next_val == expected_v3, (
        "Each duration>0 affect must consume one unconditional RNG slot "
        "(ROM src/update.c:768 C && left-to-right; GL-026); "
        f"expected {expected_v3}, got {next_val}"
    )


def test_msg_off_dedup_suppresses_all_but_last_same_type_affect() -> None:
    """ROM src/update.c:774-775 dedup predicate — only the last consecutive
    same-type affect expiring in a tick emits msg_off.

    ``if (paf_next == NULL || paf_next->type != paf->type || paf_next->duration > 0)``
    means: skip the message if the NEXT affect is the same type AND also expiring
    (duration == 0).  Only the final consecutive same-type expiry fires.

    Two duration=0 affects of the same type must produce exactly ONE wear-off
    message (from the last one), not two.
    """
    ch = _build_char()

    first_paf = AffectData(type=99, level=5, duration=0, location=0, modifier=0, bitvector=0)
    second_paf = AffectData(type=99, level=5, duration=0, location=0, modifier=0, bitvector=0)
    # _lookup_raw_affect_wear_off checks for a 'wear_off_message' attribute first.
    first_paf.wear_off_message = "A sanctuary fades."  # type: ignore[attr-defined]
    second_paf.wear_off_message = "A sanctuary fades."  # type: ignore[attr-defined]
    ch.affected.extend([first_paf, second_paf])

    messages = tick_spell_effects(ch)

    wear_off_count = sum(1 for m in messages if "sanctuary fades" in m)
    assert wear_off_count == 1, (
        f"ROM dedup (src/update.c:774-775) must emit msg_off only for the last "
        f"consecutive same-type expiry; expected 1 message, got {wear_off_count} "
        f"in {messages!r}"
    )
    assert first_paf not in ch.affected, "first same-type affect must be removed"
    assert second_paf not in ch.affected, "second same-type affect must be removed"
