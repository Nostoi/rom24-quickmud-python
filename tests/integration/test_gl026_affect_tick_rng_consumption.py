"""GL-026 — affect-tick RNG consumption must match ROM's per-affect contract.

ROM ``char_update`` affect loop (``src/update.c:762-786``):

    if (paf->duration > 0)
    {
        paf->duration--;
        if (number_range (0, 4) == 0 && paf->level > 0)
            paf->level--;        /* spell strength fades with time */
    }

C ``&&`` is left-to-right short-circuit, and ``number_range`` advances the
Mitchell-Moore state as a side effect the compiler cannot elide — so the
``number_range(0,4)`` roll is consumed **unconditionally for every affect
with ``duration > 0``**, regardless of ``level``; ``level > 0`` is only
tested afterwards to decide whether to decrement.

The Python port had the operands **swapped**
(``if level > 0 and number_range(0,4) == 0``), so the roll was skipped
whenever ``level == 0`` — and ``level`` reaches 0 naturally via the fade
mechanic on long-lived affects.  Each skipped roll desyncs the global RNG
stream for every downstream consumer in the same tick (the immediately
following plague/poison damage in ``_char_update_tick_effects``) and beyond.

Contract locked here (the narrow thing the fix delivers): **K affects with
``duration > 0`` consume exactly K ``number_range`` rolls, in list order,
independent of each affect's level.**  ``duration <= 0`` affects consume
none.
"""

from __future__ import annotations

from mud.affects.engine import tick_spell_effects
from mud.models.character import AffectData, Character
from mud.utils import rng_mm

_REF_SEED = 4242


def _make_affect(level: int, duration: int) -> AffectData:
    # type=0 (int SN) keeps it out of the spell_effects-managed branch, so the
    # only RNG site exercised is the duration>0 level-fade roll.
    return AffectData(type=0, level=level, duration=duration, location=0, modifier=0, bitvector=0)


def _char_with_affects(*affects: AffectData) -> Character:
    ch = Character(level=10)
    ch.affected = list(affects)
    return ch


def _assert_tick_consumes(ch: Character, expected_rolls: int) -> None:
    """Assert ``tick_spell_effects(ch)`` advances the MM stream by exactly
    ``expected_rolls`` ``number_range(0, 4)`` draws."""
    rng_mm.seed_mm(_REF_SEED)
    reference = [rng_mm.number_range(0, 4) for _ in range(expected_rolls + 3)]

    rng_mm.seed_mm(_REF_SEED)
    tick_spell_effects(ch)
    tail = [rng_mm.number_range(0, 4) for _ in range(3)]

    assert tail == reference[expected_rolls : expected_rolls + 3], (
        f"expected the tick to consume exactly {expected_rolls} number_range roll(s); "
        f"stream tail {tail} != reference[{expected_rolls}:] {reference[expected_rolls : expected_rolls + 3]}"
    )


def test_level_zero_duration_positive_affect_still_consumes_one_roll():
    """The regression: ROM rolls for a level-0 affect (left operand of &&);
    the swapped Python condition skipped it."""
    ch = _char_with_affects(_make_affect(level=0, duration=2))
    _assert_tick_consumes(ch, expected_rolls=1)


def test_level_positive_duration_positive_affect_consumes_one_roll():
    """Control: a level>0 affect consumes exactly one roll both before and
    after the fix (the operand order only matters at level 0)."""
    ch = _char_with_affects(_make_affect(level=5, duration=2))
    _assert_tick_consumes(ch, expected_rolls=1)


def test_multiple_duration_positive_affects_consume_one_roll_each_in_order():
    """K affects with duration>0 → exactly K rolls, mixing level 0 and >0."""
    ch = _char_with_affects(
        _make_affect(level=0, duration=2),
        _make_affect(level=7, duration=3),
        _make_affect(level=0, duration=4),
    )
    _assert_tick_consumes(ch, expected_rolls=3)


def test_permanent_affect_consumes_no_roll():
    """duration < 0 is permanent (ROM's empty `else if (paf->duration < 0);`
    statement) — never decremented, never rolled."""
    ch = _char_with_affects(_make_affect(level=20, duration=-1))
    _assert_tick_consumes(ch, expected_rolls=0)
