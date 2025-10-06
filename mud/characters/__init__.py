"""Character subsystem helpers for the QuickMUD port."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported for type checkers only
    from mud.models.character import Character


def _group_leader(character: Character | None) -> Character | None:
    """Return the canonical group leader following ROM ``is_same_group`` semantics."""

    if character is None:
        return None
    leader = getattr(character, "leader", None)
    return leader or character


def is_same_group(ach: Character | None, bch: Character | None) -> bool:
    """Mirror ``src/act_comm.c:is_same_group`` by comparing resolved leaders."""

    leader_a = _group_leader(ach)
    leader_b = _group_leader(bch)
    if leader_a is None or leader_b is None:
        return False
    return leader_a is leader_b


def _clan_id(character: Character | None) -> int:
    """Return the integer clan identifier for a character (0 when unset)."""

    if character is None:
        return 0
    try:
        return int(getattr(character, "clan", 0) or 0)
    except (TypeError, ValueError):
        return 0


def is_clan_member(character: Character | None) -> bool:
    """Mirror ROM `is_clan` by treating any positive clan id as membership."""

    return _clan_id(character) > 0


def is_same_clan(ach: Character | None, bch: Character | None) -> bool:
    """Return True when both characters share the same non-zero clan id."""

    clan_a = _clan_id(ach)
    if clan_a <= 0:
        return False
    return clan_a == _clan_id(bch)


__all__ = ["is_same_group", "is_clan_member", "is_same_clan"]
