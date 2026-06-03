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
