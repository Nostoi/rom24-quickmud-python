"""Regression: mob HP/mana/damage dice must match the .are source (FINDING-006).

ROM new-format mob stat line (src/db2.c load_mobiles) is
``level hitroll <hp-dice> <mana-dice> <dam-dice> damtype`` with the four AC values on
the FOLLOWING line — there is NO scalar AC token on the stat line. ``mob_loader``
previously assumed a scalar ``ac`` token at index [2], which shifted every dice field
by one: ``hit_dice`` received the ``.are`` *mana* dice, ``mana_dice`` the *damage*
dice, ``damage_dice`` the *damtype* word, and the real HP dice was dropped. Result:
every JSON-loaded mob had the wrong HP, mana, and damage. See
tools/diff_harness/FINDINGS.md FINDING-006.

These values are read directly from area/midgaard.are and confirmed against the ROM C
reference engine (the diff-harness shim spawns the drunk at HP 31 = a 2d6+22 roll).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.loaders import load_area_file
from mud.registry import area_registry, mob_registry, obj_registry, room_registry


@pytest.fixture
def midgaard_mobs():
    for reg in (area_registry, mob_registry, obj_registry, room_registry):
        reg.clear()
    load_area_file(str(Path("area") / "midgaard.are"))
    yield mob_registry
    for reg in (area_registry, mob_registry, obj_registry, room_registry):
        reg.clear()


@pytest.mark.parametrize(
    "vnum,hit_dice,mana_dice,damage_dice,damage_type",
    [
        # drunk #3064:  `2 -1 2d6+22 1d1+99 1d6+0 beating`
        (3064, "2d6+22", "1d1+99", "1d6+0", "beating"),
        # cityguard/Hassan #3001: hp dice `1d1+999` -> 1000 HP (tough justice keeper)
        (3001, "1d1+999", "1d1+99", "1d8+20", None),
    ],
)
def test_mob_dice_match_are(midgaard_mobs, vnum, hit_dice, mana_dice, damage_dice, damage_type):
    mob = midgaard_mobs[vnum]
    assert mob.hit_dice == hit_dice, f"#{vnum} hit_dice"
    assert mob.mana_dice == mana_dice, f"#{vnum} mana_dice"
    assert mob.damage_dice == damage_dice, f"#{vnum} damage_dice"
    if damage_type is not None:
        assert mob.damage_type == damage_type, f"#{vnum} damage_type"
