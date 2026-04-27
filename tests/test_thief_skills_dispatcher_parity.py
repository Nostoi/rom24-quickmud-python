"""ROM parity tests for the dispatcher-level do_sneak / do_hide.

ROM Reference: src/act_move.c:1496-1542

ROM C does NOT bail out early when the character has zero skill — the message
"You attempt to move silently." / "You attempt to hide." is always emitted, the
affect strip / removal still happens, and check_improve still runs (which can
no-op silently for a 0% skill).  Earlier QuickMUD code returned
"You don't know how to ..." which violated parity.  These tests lock in the
ROM-faithful behavior.
"""
from __future__ import annotations

from mud.commands.thief_skills import do_hide, do_sneak
from mud.models.character import Character
from mud.models.constants import AffectFlag


def _make_char(name: str = "Shade") -> Character:
    char = Character(name=name, level=10, is_npc=False)
    char.messages.clear()
    return char


def test_do_sneak_emits_attempt_message_even_with_zero_skill() -> None:
    """ROM L1500: send_to_char unconditional — no "don't know how" bail-out."""
    char = _make_char()
    # No skills["sneak"] entry → effectively skill 0.

    result = do_sneak(char, "")

    assert result == "You attempt to move silently."
    assert "You don't know how to sneak." not in char.messages
    # ROM L1500 sends the attempt message before any skill check.
    assert "You attempt to move silently." in char.messages
    # Skill 0 → roll always >= 0, so AFF_SNEAK must NOT be set.
    assert not (int(getattr(char, "affected_by", 0)) & int(AffectFlag.SNEAK))


def test_do_hide_emits_attempt_message_even_with_zero_skill() -> None:
    """ROM L1528: send_to_char unconditional — no "don't know how" bail-out."""
    char = _make_char()

    result = do_hide(char, "")

    assert result == "You attempt to hide."
    assert "You don't know how to hide." not in char.messages
    assert "You attempt to hide." in char.messages
    assert not (int(getattr(char, "affected_by", 0)) & int(AffectFlag.HIDE))


def test_do_hide_clears_existing_aff_hide_before_reroll(monkeypatch) -> None:
    """ROM L1530-1531: REMOVE_BIT(ch->affected_by, AFF_HIDE) before the roll."""
    from mud.utils import rng_mm

    char = _make_char()
    char.skills["hide"] = 75
    char.affected_by = int(AffectFlag.HIDE)

    # Force failure so AFF_HIDE is NOT re-set.
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 99)

    do_hide(char, "")

    # Existing AFF_HIDE must have been stripped and not re-set on failure.
    assert not (int(getattr(char, "affected_by", 0)) & int(AffectFlag.HIDE))


def test_do_sneak_already_sneaking_returns_without_reapplying(monkeypatch) -> None:
    """ROM L1503-1504: if already AFF_SNEAK, return after the strip+message."""
    from mud.utils import rng_mm

    char = _make_char()
    char.skills["sneak"] = 75
    char.affected_by = int(AffectFlag.SNEAK)

    rolls: list[int] = []

    def record_roll() -> int:
        rolls.append(1)
        return 1

    monkeypatch.setattr(rng_mm, "number_percent", record_roll)

    do_sneak(char, "")

    # ROM strips first, then checks IS_AFFECTED, returning before number_percent.
    # Canonical handler also short-circuits without rolling.
    assert rolls == []
