"""ARITH-208 regression: mob hp/mana source floor removed + coupled UB-divisor
floors narrowed to a zero-only guard.

ROM ``create_mobile`` (``src/db.c:2074-2077``) stores
``max_hit = dice(number, size) + bonus`` **raw** (can be negative; ``dice()`` at
``src/db.c:3628`` returns ``0`` for size 0 and ``number`` for size 1) and then
sets ``mob->hit = mob->max_hit``. The Python port previously floored the roll at
``0`` (``templates._roll_dice``) **and** floored every ``100 * hit / max_hit``
divisor at ``1`` (``max(1, max_hit)``).

Removing only the source floor would unmask the divisor floor as a NEW sign
divergence: ``100 * neg_hit / 1`` (large negative) where ROM computes
``neg / neg = positive``. The coordinated fix removes the source floor and
narrows the divisor floors to a **zero-only guard** (``x or 1``) so a negative
``max_hit`` flows through BOTH sides — reproducing ROM's ``neg/neg = positive`` —
while still guarding the exact-zero divisor (the ``docs/divergences/UB_DIVISORS.md``
crash policy).
"""

from __future__ import annotations

from mud.combat.messages import _severity_terms
from mud.mobprog import _cmd_eval
from mud.models.mob import MobIndex
from mud.spawning.templates import MobInstance, _roll_dice


def test_roll_dice_no_longer_floors_negative_result():
    # ROM dice(1,1) = 1 (src/db.c:3637 size==1 → number), + (-4) = -3. No floor.
    assert _roll_dice((1, 1, -4)) == -3


def test_roll_dice_zero_size_keeps_negative_bonus():
    # ROM dice(n,0) = 0 (src/db.c:3635), + (-5) = -5. Python previously max(0,)→0.
    assert _roll_dice((0, 0, -5)) == -5


def test_spawned_mob_propagates_negative_max_hit():
    proto = MobIndex(vnum=98765, short_descr="degenerate mob")
    proto.hit = (1, 1, -4)  # dice(1,1) + (-4) = -3
    proto.mana = (0, 0, 0)
    proto.damage = (0, 0, 0)

    mob = MobInstance.from_prototype(proto)

    assert mob.max_hit == -3
    # ROM mob->hit = mob->max_hit (src/db.c:2077) — raw, negative propagates.
    assert mob.hit == -3


def test_dam_message_divisor_zero_guard_no_crash():
    """max_hit == 0 must NOT raise ZeroDivisionError (UB_DIVISORS policy)."""

    class V:
        max_hit = 0

    pct = _severity_terms(10, V())[2]
    assert isinstance(pct, int)


def test_hpcnt_negative_max_hit_yields_rom_truncated_percent(movable_char_factory):
    """ROM ``mob_cmds.c`` hpcnt: ``percent = current * 100 / max_hit``.

    With ``hit == max_hit == -50`` ROM computes ``100*-50/-50 = +100``
    (neg/neg). The old ``max(1, max_hit)`` floor gave ``100*-50/1 = -5000``, so
    ``hpcnt $n > 50`` flips from False (floored) to True (ROM-faithful).
    """
    mob = movable_char_factory("watcher", 3001)
    target = movable_char_factory("victim", 3001)
    target.max_hit = -50
    target.hit = -50

    assert _cmd_eval("hpcnt", "$n > 50", mob, target, None, None, None) is True
