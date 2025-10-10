"""ROM kill_table counters tracking NPC prototype statistics."""

from __future__ import annotations

from dataclasses import dataclass

from mud.models.constants import MAX_LEVEL


@dataclass
class KillData:
    """Track how many prototypes exist at a level and how many have died."""

    number: int = 0
    killed: int = 0


kill_table: list[KillData] = [KillData() for _ in range(MAX_LEVEL)]


def _clamp_level(level: int) -> int:
    try:
        value = int(level)
    except (TypeError, ValueError):
        return 0
    if value < 0:
        return 0
    if value >= MAX_LEVEL:
        return MAX_LEVEL - 1
    return value


def increment_killed(level: int) -> None:
    entry = kill_table[_clamp_level(level)]
    entry.killed += 1


def reset_kill_table() -> None:
    for entry in kill_table:
        entry.number = 0
        entry.killed = 0


def get_kill_data(level: int) -> KillData:
    return kill_table[_clamp_level(level)]


__all__ = ["KillData", "kill_table", "get_kill_data", "increment_killed", "reset_kill_table"]
