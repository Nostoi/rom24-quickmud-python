"""Aggressive mobile update loop mirroring ROM src/update.c:aggr_update."""

from __future__ import annotations

from collections.abc import Iterable

from mud.combat import multi_hit
from mud.models.character import Character, character_registry
from mud.models.constants import LEVEL_IMMORTAL, ActFlag, AffectFlag, RoomFlag
from mud.utils import rng_mm


def _has_flag(value: int, flag: ActFlag) -> bool:
    try:
        return bool(int(value) & int(flag))
    except Exception:
        return False


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
        if _has_flag(getattr(ch, "act", 0), ActFlag.WIMPY) and candidate.is_awake():
            continue
        if not _can_see(ch, candidate):
            continue
        yield candidate


def aggressive_update() -> None:
    """Wake aggressive NPCs and initiate combat when players enter their rooms."""

    # mirroring ROM src/update.c:1087 — aggr_update walks ``char_list`` for the
    # PC watcher ``wch``; src/db.c:2256-2257 / src/nanny.c:757-758 head-insert,
    # so ROM visits the NEWEST character first. ``character_registry`` is
    # append-order, so iterate it reversed — load-bearing for the shared RNG
    # draw order (number_bits(1) aggression coin, number_range victim
    # reservoir), like violence_tick/char_update/mobile_update. GL-043.
    for watcher in reversed(list(character_registry)):
        # mirroring ROM's saved ``wch_next`` pointer — a char extracted
        # mid-tick (multi_hit kill) is never revisited in ROM's walk. GL-043.
        if watcher not in character_registry:
            continue
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
            if mob.has_affect(AffectFlag.CALM):
                continue
            if getattr(mob, "fighting", None) is not None:
                continue
            if mob.has_affect(AffectFlag.CHARM):
                continue
            if not mob.is_awake():
                continue
            if _has_flag(getattr(mob, "act", 0), ActFlag.WIMPY) and watcher.is_awake():
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

            # mirroring ROM src/update.c:1136 — aggr_update ends each aggression
            # with a bare multi_hit(ch, victim, TYPE_UNDEFINED). It does NOT call
            # check_assist: auto-assist is exclusively violence_update's job
            # (src/fight.c:90, run on the next PULSE_VIOLENCE — Python's
            # game_loop.violence_tick). Calling check_assist here started assists
            # a full tick early and drew extra coins from the shared MM RNG
            # stream (the comment that used to cite "fight.c:90" mislabeled the
            # violence_update site as if it belonged to aggr_update).
            multi_hit(mob, victim)
