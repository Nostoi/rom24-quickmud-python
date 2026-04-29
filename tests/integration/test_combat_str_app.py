"""Integration tests for ROM str_app[STR].tohit augmentation in combat.

Mirrors ROM src/merc.h:2107-2108 GET_HITROLL macro:

    #define GET_HITROLL(ch) \
        ((ch)->hitroll + str_app[get_curr_stat(ch, STAT_STR)].tohit)

Consumed at src/fight.c:471:

    thac0 -= GET_HITROLL(ch) * skill / 100;

The Python THAC0 path at mud/combat/engine.py:411 must read the
str_app-augmented hitroll, not the raw ch->hitroll field.

Closes CONST-002.
"""

from __future__ import annotations

import pytest

from mud.combat import engine as combat_engine
from mud.math.stat_apps import STR_APP, get_hitroll
from mud.models.character import Character
from mud.models.constants import Stat


def _make_attacker(strength: int, hitroll: int = 0) -> Character:
    """Build a Character with permanent STR set to ``strength`` and given hitroll."""

    char = Character(name=f"Str{strength}", level=20, hitroll=hitroll, is_npc=False)
    char.perm_stat = [13, 13, 13, 13, 13]
    char.perm_stat[Stat.STR] = strength
    char.mod_stat = [0, 0, 0, 0, 0]
    return char


@pytest.mark.parametrize(
    "strength, expected_tohit",
    [
        (3, -3),   # str_app[3].tohit  (src/const.c:732)
        (8, 0),    # str_app[8].tohit  — neutral band
        (13, 0),   # str_app[13].tohit — neutral band
        (18, 2),   # str_app[18].tohit (src/const.c:746)
        (25, 6),   # str_app[25].tohit (src/const.c:753)
    ],
)
def test_get_hitroll_adds_str_app_tohit(strength: int, expected_tohit: int) -> None:
    """get_hitroll must equal ch.hitroll + str_app[STR].tohit."""

    char = _make_attacker(strength=strength, hitroll=0)
    assert STR_APP[strength].tohit == expected_tohit
    assert get_hitroll(char) == expected_tohit


def test_get_hitroll_preserves_raw_hitroll_addend() -> None:
    """A non-zero ch.hitroll is added to the str_app contribution, not replaced."""

    weak = _make_attacker(strength=3, hitroll=10)
    strong = _make_attacker(strength=25, hitroll=10)
    assert get_hitroll(weak) == 10 + STR_APP[3].tohit
    assert get_hitroll(strong) == 10 + STR_APP[25].tohit
    # Sanity — the STR-25 attacker hits 9 better than the STR-3 attacker
    # at identical raw hitroll (src/const.c str_app delta 6 - (-3) = 9).
    assert get_hitroll(strong) - get_hitroll(weak) == 9


def test_engine_thac0_path_uses_str_app_tohit(monkeypatch: pytest.MonkeyPatch) -> None:
    """mud/combat/engine.py THAC0 path must pass get_hitroll(attacker) into compute_thac0.

    Forces COMBAT_USE_THAC0 on, captures the hitroll kwarg compute_thac0 was
    called with for a STR-3 and a STR-25 attacker that share an identical
    ch.hitroll, and asserts the delta equals str_app[25].tohit - str_app[3].tohit (== 9).
    """

    monkeypatch.setattr(combat_engine, "COMBAT_USE_THAC0", True)

    captured: list[int] = []
    real_compute_thac0 = combat_engine.compute_thac0

    def spy_compute_thac0(level: int, ch_class: int, *, hitroll: int, skill: int) -> int:
        captured.append(hitroll)
        return real_compute_thac0(level, ch_class, hitroll=hitroll, skill=skill)

    monkeypatch.setattr(combat_engine, "compute_thac0", spy_compute_thac0)

    weak = _make_attacker(strength=3, hitroll=5)
    strong = _make_attacker(strength=25, hitroll=5)
    victim = Character(name="Dummy", level=20, hit=100, max_hit=100, is_npc=True)
    victim.armor = [0, 0, 0, 0]

    combat_engine.attack_round(weak, victim)
    combat_engine.attack_round(strong, victim)

    assert len(captured) >= 2, "compute_thac0 should have been called for each attacker"
    weak_hitroll = captured[0]
    strong_hitroll = captured[-1]
    assert strong_hitroll - weak_hitroll == STR_APP[25].tohit - STR_APP[3].tohit == 9


def test_engine_percent_path_uses_str_app_tohit(monkeypatch: pytest.MonkeyPatch) -> None:
    """The non-THAC0 percent fallback at mud/combat/engine.py must also use
    get_hitroll(attacker), not the raw attacker.hitroll.

    Asserts engine.get_hitroll is invoked with the attacker during attack_round.
    """

    monkeypatch.setattr(combat_engine, "COMBAT_USE_THAC0", False)

    seen: list[int] = []
    real_get_hitroll = combat_engine.get_hitroll

    def spy_get_hitroll(ch) -> int:
        value = real_get_hitroll(ch)
        seen.append(value)
        return value

    monkeypatch.setattr(combat_engine, "get_hitroll", spy_get_hitroll)

    weak = _make_attacker(strength=3, hitroll=0)
    strong = _make_attacker(strength=25, hitroll=0)
    victim = Character(name="Dummy", level=20, hit=100, max_hit=100, is_npc=True)
    victim.armor = [0, 0, 0, 0]

    combat_engine.attack_round(weak, victim)
    combat_engine.attack_round(strong, victim)

    assert seen, "engine.get_hitroll should be called by the percent path"
    # str_app[3].tohit == -3, str_app[25].tohit == 6
    assert STR_APP[3].tohit in seen
    assert STR_APP[25].tohit in seen
