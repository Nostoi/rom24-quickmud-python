"""affect_join — ROM src/handler.c:1464-1483 merge semantics.

When a character already carries an affect of the same type, affect_join
must:
  - average levels    (new.level + old.level) // 2
  - sum durations     new.duration += old.duration
  - sum modifiers     new.modifier += old.modifier
  - remove old        affect_remove(ch, old)
  - call affect_to_char(ch, merged)

The result is a single merged entry in ch.affected, not two stacked ones.
Stat modifiers must be applied via affect_modify exactly once.
"""

from __future__ import annotations

import pytest

from mud.models.character import AffectData, Character, character_registry
from mud.models.constants import AffectFlag, Position, Stat


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def _make_char(name: str = "victim") -> Character:
    ch = Character(
        name=name,
        level=10,
        is_npc=True,
        hit=100,
        max_hit=100,
        mana=50,
        max_mana=50,
        move=50,
        max_move=50,
        position=int(Position.STANDING),
    )
    ch._ensure_mod_stat_capacity()
    return ch


def test_affect_join_merges_existing_affect() -> None:
    """affect_join must yield exactly one affect entry when type matches existing.

    # mirrors ROM src/handler.c:1464-1483 affect_join
    """
    from mud.handler import affect_join

    ch = _make_char()

    # Existing affect already on character (e.g. from prior infection)
    old_af = AffectData(type="plague", level=8, duration=10, location=1, modifier=-3, bitvector=int(AffectFlag.PLAGUE))
    ch.affect_to_char(old_af)
    assert len(ch.affected) == 1

    # New incoming affect (re-infection)
    new_af = AffectData(type="plague", level=4, duration=6, location=1, modifier=-5, bitvector=int(AffectFlag.PLAGUE))

    affect_join(ch, new_af)

    # Must have exactly one affect, not two
    assert len(ch.affected) == 1, (
        f"affect_join must merge into one affect; found {len(ch.affected)} "
        "(ROM src/handler.c:1471-1477 removes old, then calls affect_to_char)"
    )


def test_affect_join_averages_level_and_sums_fields() -> None:
    """affect_join must average level, sum duration and modifier.

    # mirrors ROM src/handler.c:1471-1475:
    #   paf->level    = (paf->level += paf_old->level) / 2
    #   paf->duration += paf_old->duration
    #   paf->modifier += paf_old->modifier
    """
    from mud.handler import affect_join

    ch = _make_char()
    old_af = AffectData(type="plague", level=8, duration=10, location=1, modifier=-3, bitvector=int(AffectFlag.PLAGUE))
    ch.affect_to_char(old_af)

    new_af = AffectData(type="plague", level=4, duration=6, location=1, modifier=-5, bitvector=int(AffectFlag.PLAGUE))
    affect_join(ch, new_af)

    merged = ch.affected[0]
    assert merged.level == (4 + 8) // 2, f"level must be averaged; got {merged.level}"
    assert merged.duration == 10 + 6, f"duration must be summed; got {merged.duration}"
    assert merged.modifier == -3 + -5, f"modifier must be summed; got {merged.modifier}"


def test_affect_join_no_existing_applies_fresh() -> None:
    """affect_join with no prior same-type affect behaves like affect_to_char.

    # mirrors ROM src/handler.c:1481 — affect_to_char always called at end
    """
    from mud.handler import affect_join

    ch = _make_char()
    baseline_str = ch.mod_stat[int(Stat.STR)]

    af = AffectData(type="plague", level=6, duration=5, location=1, modifier=-5, bitvector=int(AffectFlag.PLAGUE))
    affect_join(ch, af)

    assert len(ch.affected) == 1
    assert ch.has_affect(AffectFlag.PLAGUE), "AFF_PLAGUE bitvector must be set"
    assert ch.mod_stat[int(Stat.STR)] == baseline_str - 5, "APPLY_STR -5 must be applied via affect_modify"


def test_affect_join_applies_merged_stat_modifier_once() -> None:
    """After merge, the net stat modifier (sum) must be applied exactly once.

    Old: modifier=-3 applied on affect_to_char (baseline_str - 3).
    Merge: new modifier=-5, old modifier=-3 → merged modifier=-8.
    After affect_join: old removed (restores +3), merged applied (-8).
    Net: baseline_str - 8.
    """
    from mud.handler import affect_join

    ch = _make_char()
    baseline_str = ch.mod_stat[int(Stat.STR)]

    old_af = AffectData(type="plague", level=8, duration=10, location=1, modifier=-3, bitvector=int(AffectFlag.PLAGUE))
    ch.affect_to_char(old_af)
    # str is now baseline - 3
    assert ch.mod_stat[int(Stat.STR)] == baseline_str - 3

    new_af = AffectData(type="plague", level=4, duration=6, location=1, modifier=-5, bitvector=int(AffectFlag.PLAGUE))
    affect_join(ch, new_af)

    # affect_remove undoes -3; affect_to_char applies merged -8
    expected = baseline_str - 8
    assert ch.mod_stat[int(Stat.STR)] == expected, (
        f"merged modifier must be applied once; expected {expected}, got {ch.mod_stat[int(Stat.STR)]}"
    )
