"""Prompt parity: displayed hit must clamp to >= 0.

Regression for the live death-path bug where the WS prompt rendered
``<0hp 100m 100mv>`` immediately after lethal damage and again the
``<-15hp ...>`` of an unclamped negative hit could leak between
``update_pos`` setting POS_DEAD and ``raw_kill``'s
``hit = max(1, hit)`` clamp (mud/combat/death.py:584).

ROM ``src/comm.c:1420ff`` runs in a single-threaded loop so the prompt
never sees the negative transient. Python's async dispatch breaks that
invariant, so the safe ROM-faithful equivalent is to clamp the
displayed value at the render site.
"""

from __future__ import annotations

from types import SimpleNamespace

from mud.utils.prompt import bust_a_prompt


def _make_char(*, hit: int, prompt: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        hit=hit,
        max_hit=100,
        mana=100,
        max_mana=100,
        move=100,
        max_move=100,
        comm=0,
        prompt=prompt,
        prefix="",
    )


def test_default_prompt_clamps_negative_hit_to_zero() -> None:
    char = _make_char(hit=-15)
    assert "0hp" in bust_a_prompt(char)
    assert "-15hp" not in bust_a_prompt(char)


def test_default_prompt_passes_through_positive_hit() -> None:
    char = _make_char(hit=42)
    assert "42hp" in bust_a_prompt(char)


def test_custom_prompt_h_token_clamps_negative_hit_to_zero() -> None:
    char = _make_char(hit=-7, prompt="%h/%H")
    assert bust_a_prompt(char).startswith("0/100")


def test_custom_prompt_h_token_passes_through_positive_hit() -> None:
    char = _make_char(hit=37, prompt="%h/%H")
    assert bust_a_prompt(char).startswith("37/100")
