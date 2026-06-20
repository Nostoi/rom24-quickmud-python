"""ARITH-210 regression: mob spawn ``current_hp`` zero floor removed.

ROM ``create_mobile`` (``src/db.c:2077``) sets ``mob->hit = mob->max_hit`` **raw**.
A degenerate prototype with ``hit = (0, X, 0)`` rolls ``dice(0, X) + 0 == 0``, so
ROM spawns the mob with ``hit == 0``. The Python port previously floored the
``max_hit == 0`` case to ``max(proto.hit[1] + proto.hit[2], 1)`` — i.e. it
returned the dice *size* (``X``), not even ``1`` — diverging from ROM's ``0``.

Negative ``max_hit`` already propagates (truthy), so only the exact-zero case
diverged. This mirrors the ARITH-205/207/209 defensive-floor class: ROM uses the
raw value, the floor is a Python-only invention. Reachability: a 0-hp spawn flows
through ``update_pos`` (``src/fight.c``) exactly as ROM — an NPC with ``hit < 1``
is set to ``POS_DEAD`` — with no Python-only crash (``current_hp``/``hit`` is a
numerator everywhere, never a divisor; the ``100*hit/max_hit`` percent sites
divide by ``max_hit``, handled by ARITH-208/211).
"""

from __future__ import annotations

from mud.models.mob import MobIndex
from mud.spawning.templates import MobInstance


def test_spawned_mob_zero_max_hit_yields_zero_current_hp():
    proto = MobIndex(vnum=98766, short_descr="zero-hp husk")
    proto.hit = (0, 4, 0)  # dice(0, 4) + 0 == 0
    proto.mana = (0, 0, 0)
    proto.damage = (0, 0, 0)

    mob = MobInstance.from_prototype(proto)

    # ROM mob->hit = mob->max_hit (src/db.c:2077) — raw zero, no floor.
    assert mob.max_hit == 0
    assert mob.current_hp == 0
    assert mob.hit == 0


def test_spawned_mob_positive_max_hit_unaffected():
    proto = MobIndex(vnum=98767, short_descr="healthy mob")
    proto.hit = (1, 1, 19)  # dice(1, 1) + 19 == 20
    proto.mana = (0, 0, 0)
    proto.damage = (0, 0, 0)

    mob = MobInstance.from_prototype(proto)

    assert mob.max_hit == 20
    assert mob.current_hp == 20
