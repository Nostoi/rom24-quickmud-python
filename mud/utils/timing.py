"""Wait-state and timing helpers — canonical entry point.

ROM C: src/skills.c WAIT_STATE macro: ch->wait = UMAX(ch->wait, beats).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.character import Character


def apply_wait_state(char: "Character", beats: int) -> None:
    """ROM WAIT_STATE: char.wait = max(char.wait, beats).

    Beats are 1/4-second ticks. Zero/negative is a no-op so callers can
    pass skill lag values without guarding.
    """
    if beats <= 0 or not hasattr(char, "wait"):
        return
    current = int(getattr(char, "wait", 0) or 0)
    char.wait = max(current, int(beats))
