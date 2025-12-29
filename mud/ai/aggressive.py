"""Aggressive mobile update loop mirroring ROM src/update.c:aggr_update."""

from __future__ import annotations

from collections.abc import Iterable

from mud.combat import multi_hit
from mud.models.character import Character, character_registry
from mud.models.constants import ActFlag, AffectFlag, LEVEL_IMMORTAL, Position, RoomFlag
from mud.utils import rng_mm


def _has_flag(value: int, flag: ActFlag) -> bool:
    try:
        return bool(int(value) & int(flag))
    except Exception:
        return False


def _has_affect(ch: Character, flag: AffectFlag) -> bool:
    checker = getattr(ch, "has_affect", None)
    if callable(checker):
        return bool(checker(flag))
    affected = getattr(ch, "affected_by", 0)
    try:
        return bool(int(affected) & int(flag))
    except Exception:
        return False


def _is_awake(ch: Character) -> bool:
    checker = getattr(ch, "is_awake", None)
    if callable(checker):
        return bool(checker())
    return int(getattr(ch, "position", 0)) > int(Position.SLEEPING)


def _can_see(attacker: Character, target: Character | None) -> bool:
    if attacker is None or target is None:
        return False
    room = getattr(attacker, "room", None)
    if room is None or target not in getattr(room, "people", []):
        return False
    invis_level = int(getattr(target, "invis_level", 0))
    attacker_level = int(getattr(attacker, "level", 0))
    if invis_level > attacker_level:
        return False
    visible_checker = getattr(attacker, "can_see", None)
    if callable(visible_checker):
        try:
            return bool(visible_checker(target))
        except Exception:
            return False
    return True


def _eligible_victims(ch: Character, occupants: Iterable[Character]) -> Iterable[Character]:
    for candidate in occupants:
        if getattr(candidate, "is_npc", True):
            continue
        if int(getattr(candidate, "level", 0)) >= LEVEL_IMMORTAL:
            continue
        if int(getattr(ch, "level", 0)) < int(getattr(candidate, "level", 0)) - 5:
            continue
        if _has_flag(getattr(ch, "act", 0), ActFlag.WIMPY) and _is_awake(candidate):
            continue
        if not _can_see(ch, candidate):
            continue
        yield candidate


def aggressive_update() -> None:
    """Wake aggressive NPCs and initiate combat when players enter their rooms."""

    for watcher in list(character_registry):
        if getattr(watcher, "is_npc", False):
            continue
        if watcher.is_immortal():
            continue
        room = getattr(watcher, "room", None)
        if room is None:
            continue
        area = getattr(room, "area", None)
        if area is not None and getattr(area, "empty", False):
            continue

        for mob in list(getattr(room, "people", [])):
            if mob is watcher or not getattr(mob, "is_npc", False):
                continue
            if not _has_flag(getattr(mob, "act", 0), ActFlag.AGGRESSIVE):
                continue
            if int(getattr(room, "room_flags", 0)) & int(RoomFlag.ROOM_SAFE):
                continue
            if _has_affect(mob, AffectFlag.CALM):
                continue
            if getattr(mob, "fighting", None) is not None:
                continue
            if _has_affect(mob, AffectFlag.CHARM):
                continue
            if not _is_awake(mob):
                continue
            if _has_flag(getattr(mob, "act", 0), ActFlag.WIMPY) and _is_awake(watcher):
                continue
            if not _can_see(mob, watcher):
                continue
            if rng_mm.number_bits(1) == 0:
                continue

            victim = None
            count = 0
            for candidate in _eligible_victims(mob, getattr(room, "people", [])):
                if rng_mm.number_range(0, count) == 0:
                    victim = candidate
                count += 1

            if victim is None:
                continue

            multi_hit(mob, victim)

            # ROM src/fight.c:90 - Check for assist after combat starts
            from mud.combat.assist import check_assist

            check_assist(mob, victim)
