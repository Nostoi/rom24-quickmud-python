"""FIGHT-049 — _murder_safety_check PC-vs-PC clan/level guards.

ROM src/fight.c:1096-1121: when both ch and victim are PCs the `else` branch
inside is_safe checks:

    1. !is_clan(ch)            → "Join a clan if you want to kill players."
    2. PLR_KILLER | PLR_THIEF  → return FALSE (allow attack, skip rest)
    3. !is_clan(victim)        → "They aren't in a clan, leave them alone."
    4. ch->level > victim->level + 8 → "Pick on someone your own size."

Python _murder_safety_check (mud/commands/murder.py) currently only checks
ROOM_SAFE, kill-stealing, and the charm-master guard — missing the entire PC-vs-PC
clan/level path.
"""

from __future__ import annotations

import pytest

from mud.commands.murder import _murder_safety_check
from mud.models.character import Character
from mud.models.constants import PlayerFlag
from mud.world import create_test_character, initialize_world

_ROOM = 2300  # a non-safe room present in area.lst


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _make_pc(name: str, room_vnum: int = _ROOM) -> Character:
    ch = create_test_character(name, room_vnum)
    ch.is_npc = False
    ch.level = 20
    ch.clan = 0
    ch.act = 0
    return ch


def test_fight049_non_clan_attacker_blocked() -> None:
    # mirrors ROM src/fight.c:1098-1103 — !is_clan(ch)
    char = _make_pc("Attacker")
    victim = _make_pc("Victim")
    char.clan = 0  # not a clan member

    result = _murder_safety_check(char, victim)

    assert result == "Join a clan if you want to kill players.", (
        f"Expected clan gate message; got {result!r}. "
        "ROM src/fight.c:1100: !is_clan(ch) → send_to_char('Join a clan ...')"
    )


def test_fight049_killer_flagged_victim_allowed() -> None:
    # mirrors ROM src/fight.c:1105-1107 — PLR_KILLER bypasses remaining checks
    char = _make_pc("Attacker")
    victim = _make_pc("Victim")
    char.clan = 1
    victim.clan = 0  # non-clan BUT has KILLER flag → attack allowed
    victim.act = int(PlayerFlag.KILLER)

    result = _murder_safety_check(char, victim)

    assert result is None, (
        f"KILLER-flagged victim should be attackable; got {result!r}. "
        "ROM src/fight.c:1105-1107: IS_SET(victim->act, PLR_KILLER) → return FALSE"
    )


def test_fight049_thief_flagged_victim_allowed() -> None:
    # mirrors ROM src/fight.c:1105-1107 — PLR_THIEF bypasses remaining checks
    char = _make_pc("Attacker")
    victim = _make_pc("Victim")
    char.clan = 1
    victim.clan = 0
    victim.act = int(PlayerFlag.THIEF)

    result = _murder_safety_check(char, victim)

    assert result is None, (
        f"THIEF-flagged victim should be attackable; got {result!r}. "
        "ROM src/fight.c:1106: IS_SET(victim->act, PLR_THIEF) → return FALSE"
    )


def test_fight049_non_clan_victim_blocked() -> None:
    # mirrors ROM src/fight.c:1109-1113 — !is_clan(victim)
    char = _make_pc("Attacker")
    victim = _make_pc("Victim")
    char.clan = 1
    victim.clan = 0  # non-clan, no KILLER/THIEF flag

    result = _murder_safety_check(char, victim)

    assert result == "They aren't in a clan, leave them alone.", (
        f"Expected non-clan victim message; got {result!r}. "
        "ROM src/fight.c:1111: !is_clan(victim) → send_to_char('They aren\\'t in a clan...')"
    )


def test_fight049_level_difference_blocked() -> None:
    # mirrors ROM src/fight.c:1116-1119 — ch->level > victim->level + 8
    char = _make_pc("Attacker")
    victim = _make_pc("Victim")
    char.clan = 1
    victim.clan = 1
    char.level = 30
    victim.level = 20  # 30 > 20+8=28 → blocked

    result = _murder_safety_check(char, victim)

    assert result == "Pick on someone your own size.", (
        f"Expected level-diff message; got {result!r}. "
        "ROM src/fight.c:1118: ch->level > victim->level + 8 → 'Pick on someone your own size.'"
    )


def test_fight049_equal_clan_level_allowed() -> None:
    # baseline: same-clan, same-level PCs → no safety block
    char = _make_pc("Attacker")
    victim = _make_pc("Victim")
    char.clan = 1
    victim.clan = 1
    char.level = 20
    victim.level = 20  # 20 > 20+8=28 → False → allowed

    result = _murder_safety_check(char, victim)

    assert result is None, f"Same-clan same-level PC should be attackable; got {result!r}."
