"""Integration tests for ROM dex_app[DEX].defensive augmentation in GET_AC.

Mirrors ROM src/merc.h:2104-2106 GET_AC macro:

    #define GET_AC(ch, type) \
        ((ch)->armor[type] + (IS_AWAKE(ch) \
            ? dex_app[get_curr_stat(ch, STAT_DEX)].defensive : 0))

Where IS_AWAKE(ch) is (ch->position > POS_SLEEPING) — sleeping/stunned/incap/dead
victims do NOT receive the DEX defensive bonus.

Consumed at:
- src/fight.c:480-489 (combat AC for to-hit math; lower AC == better defense)
- src/act_info.c:1591-1650 (do_score AC tier display)
- src/act_wiz.c:1612-1613 (do_stat_char raw AC display)

Closes CONST-004.
"""

from __future__ import annotations

import pytest

from mud.combat import engine as combat_engine
from mud.math.stat_apps import DEX_APP, get_ac
from mud.models.character import Character
from mud.models.constants import Position


def _make_victim(dex: int, armor: int = 0, position: Position = Position.STANDING) -> Character:
    """Build a Character with permanent DEX = ``dex`` and four uniform armor values."""

    char = Character(name=f"Dex{dex}", level=20, is_npc=True)
    char.perm_stat = [13, 13, 13, dex, 13]
    char.mod_stat = [0, 0, 0, 0, 0]
    char.armor = [armor, armor, armor, armor]
    char.position = int(position)
    return char


@pytest.mark.parametrize(
    "dex, expected_defensive",
    [
        (3, 40),    # dex_app[3].defensive  (src/const.c:824)
        (8, 0),     # dex_app[8].defensive  — neutral band
        (13, 0),    # dex_app[13].defensive — neutral band
        (15, -10),  # dex_app[15].defensive (src/const.c:836)
        (25, -120), # dex_app[25].defensive (src/const.c:846)
    ],
)
def test_get_ac_adds_dex_app_defensive_when_awake(dex: int, expected_defensive: int) -> None:
    """get_ac(ch, type) for an awake char must equal armor[type] + dex_app[DEX].defensive."""

    char = _make_victim(dex=dex, armor=50)
    assert DEX_APP[dex].defensive == expected_defensive
    for ac_type in range(4):
        assert get_ac(char, ac_type) == 50 + expected_defensive


@pytest.mark.parametrize("position", [Position.SLEEPING, Position.STUNNED, Position.INCAP, Position.DEAD])
def test_get_ac_skips_dex_app_when_not_awake(position: Position) -> None:
    """IS_AWAKE gate: position <= SLEEPING means raw armor only.

    ROM src/merc.h:2103: #define IS_AWAKE(ch) (ch->position > POS_SLEEPING).
    """

    char = _make_victim(dex=25, armor=50, position=position)
    # DEX-25 awake would be 50 + (-120) = -70; while sleeping/stunned/etc, raw 50.
    for ac_type in range(4):
        assert get_ac(char, ac_type) == 50, f"position={position.name} should bypass DEX defensive"


def test_get_ac_resting_or_above_is_awake() -> None:
    """Position > SLEEPING → DEX defensive is applied.

    Per ROM src/tables.c position ordering: RESTING (5), SITTING (6), FIGHTING (7), STANDING (8)
    are all "awake" and receive dex_app[DEX].defensive.
    """

    for position in (Position.RESTING, Position.SITTING, Position.FIGHTING, Position.STANDING):
        char = _make_victim(dex=25, armor=50, position=position)
        assert get_ac(char, 0) == 50 + DEX_APP[25].defensive


def test_combat_engine_uses_get_ac(monkeypatch: pytest.MonkeyPatch) -> None:
    """attack_round must read victim AC through get_ac, not raw victim.armor.

    Spies engine.get_ac and asserts it is called with the victim during the
    THAC0 path's victim_ac computation.
    """

    monkeypatch.setattr(combat_engine, "COMBAT_USE_THAC0", True)

    seen_ac: list[int] = []
    real_get_ac = combat_engine.get_ac

    def spy_get_ac(ch, ac_type: int) -> int:
        value = real_get_ac(ch, ac_type)
        seen_ac.append(value)
        return value

    monkeypatch.setattr(combat_engine, "get_ac", spy_get_ac)

    attacker = Character(name="Attacker", level=20, is_npc=False)
    attacker.perm_stat = [13, 13, 13, 13, 13]
    attacker.mod_stat = [0, 0, 0, 0, 0]

    awake_dex25 = _make_victim(dex=25, armor=0, position=Position.STANDING)
    combat_engine.attack_round(attacker, awake_dex25)

    assert seen_ac, "engine.get_ac should be called by the THAC0 path"
    # DEX-25 standing: raw 0 + (-120) = -120
    assert -120 in seen_ac
