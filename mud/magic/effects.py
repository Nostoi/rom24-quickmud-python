"""Spell side-effect helpers ported from ROM src/effects.c."""

from __future__ import annotations

from enum import IntEnum
from typing import Any


class SpellTarget(IntEnum):
    """Spell effect destinations mirroring ROM TARGET_* constants."""

    CHAR = 0
    OBJ = 1
    ROOM = 2
    NONE = 3


def _normalize_target(target: int | SpellTarget) -> SpellTarget:
    try:
        return SpellTarget(int(target))
    except ValueError:  # pragma: no cover - defensive fallback
        return SpellTarget.NONE


def _record_effect(target: Any, name: str, level: int, damage: int, dest: SpellTarget) -> None:
    """Attach lightweight effect breadcrumbs for parity tests."""

    if target is None:
        return

    breadcrumb = {
        "effect": name,
        "level": int(level),
        "damage": int(damage),
        "target": dest,
    }
    history = getattr(target, "last_spell_effects", None)
    if history is None:
        history = []
        setattr(target, "last_spell_effects", history)
    history.append(breadcrumb)


def acid_effect(target: Any, level: int, damage: int, target_type: int | SpellTarget) -> None:
    """Mirror ROM acid_effect bookkeeping (object destruction pending)."""

    dest = _normalize_target(target_type)
    _record_effect(target, "acid", level, damage, dest)


def fire_effect(target: Any, level: int, damage: int, target_type: int | SpellTarget) -> None:
    """Mirror ROM fire_effect bookkeeping (burning/room smoke TBD)."""

    dest = _normalize_target(target_type)
    _record_effect(target, "fire", level, damage, dest)


def cold_effect(target: Any, level: int, damage: int, target_type: int | SpellTarget) -> None:
    """Mirror ROM cold_effect bookkeeping (frost bite TBD)."""

    dest = _normalize_target(target_type)
    _record_effect(target, "cold", level, damage, dest)


def poison_effect(target: Any, level: int, damage: int, target_type: int | SpellTarget) -> None:
    """Mirror ROM poison_effect breadcrumbs (object rot pending)."""

    dest = _normalize_target(target_type)
    _record_effect(target, "poison", level, damage, dest)


def shock_effect(target: Any, level: int, damage: int, target_type: int | SpellTarget) -> None:
    """Mirror ROM shock_effect breadcrumbs (equipment fry TBD)."""

    dest = _normalize_target(target_type)
    _record_effect(target, "shock", level, damage, dest)


__all__ = [
    "SpellTarget",
    "acid_effect",
    "fire_effect",
    "cold_effect",
    "poison_effect",
    "shock_effect",
]
