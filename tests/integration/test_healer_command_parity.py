"""Integration parity tests for ROM healer command behavior.

ROM reference: ``src/healer.c``.
"""

from __future__ import annotations

from mud.commands.dispatcher import process_command
from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import ActFlag
from mud.utils import rng_mm


def _place_healer(room, *, level: int = 30) -> Character:
    healer = Character(
        name="Healer",
        short_descr="a healer",
        level=level,
        room=room,
        is_npc=True,
        act=int(ActFlag.IS_HEALER),
    )
    healer.messages = []
    room.people.append(healer)
    return healer


def test_heal_lists_rom_price_table_for_act_is_healer(test_room, test_player):
    """HEALER-001 — mirrors ROM `src/healer.c:63-79`.

    ROM detects healers via `ACT_IS_HEALER` and prints the exact price table,
    including the historical display quirk where `serious` shows `15 gold`
    even though the actual cost is 1600 silver.
    """

    _place_healer(test_room)

    result = process_command(test_player, "heal")

    assert "I offer the following spells:" in result
    assert "light: cure light wounds      10 gold" in result
    assert "serious: cure serious wounds  15 gold" in result
    assert "critic: cure critical wounds  25 gold" in result
    assert "Type heal <type> to be healed." in result


def test_heal_mana_uses_total_wealth_rom_formula_and_room_utterance(test_room, test_player):
    """HEALER-002 — mirrors ROM `src/healer.c:171-190`.

    ROM checks `gold * 100 + silver`, deducts in silver, broadcasts the spoken
    words, and restores mana via `dice(2, 8) + mob->level / 3`.
    """

    healer = _place_healer(test_room, level=30)
    observer = Character(name="Observer", level=10, room=test_room, is_npc=False)
    observer.messages = []
    test_room.people.append(observer)

    test_player.gold = 9
    test_player.silver = 100
    test_player.mana = 5
    test_player.max_mana = 100

    rng_mm.seed_mm(12345)
    expected_gain = rng_mm.dice(2, 8) + c_div(healer.level, 3)
    rng_mm.seed_mm(12345)

    result = process_command(test_player, "heal mana")

    assert result == "A warm glow passes through you."
    assert test_player.gold == 0
    assert test_player.silver == 0
    assert test_player.mana == 5 + expected_gain
    assert any("a healer utters the words 'energizer'." in msg for msg in observer.messages)


def test_heal_refresh_uses_spell_refresh_not_full_restore(test_room, test_player):
    """HEALER-003 — mirrors ROM `src/healer.c:156-168, 193-197`.

    `refresh` must invoke the real spell, which restores movement by healer
    level and does not jump directly to `max_move` unless that cap is reached.
    """

    _place_healer(test_room, level=30)
    test_player.gold = 0
    test_player.silver = 500
    test_player.move = 10
    test_player.max_move = 100

    result = process_command(test_player, "heal refresh")

    assert result == "You feel less tired."
    assert test_player.move == 40


def test_heal_spell_uses_rom_heal_amount_not_full_heal(test_room, test_player):
    """HEALER-004 — mirrors ROM `src/healer.c:193-197` via `spell_heal`.

    The healer command must cast the underlying heal spell, which restores
    100 hit points rather than always filling to max.
    """

    _place_healer(test_room, level=30)
    test_player.gold = 50
    test_player.silver = 0
    test_player.hit = 1
    test_player.max_hit = 250

    result = process_command(test_player, "heal heal")

    assert result == "A warm feeling fills your body."
    assert test_player.hit == 101
