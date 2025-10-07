from __future__ import annotations

import time
from typing import Iterable

from mud.advancement import gain_exp
from mud.characters import is_same_group
from mud.math.c_compat import urange
from mud.models.character import Character
from mud.models.constants import ActFlag, ExtraFlag, WearLocation
from mud.utils import rng_mm


def _resolve_level(value: int | None) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def group_members(ch: Character) -> list[Character]:
    """Return the characters in *ch*'s room that share the same group."""

    room = getattr(ch, "room", None)
    if room is None:
        return []
    people: Iterable[Character] = getattr(room, "people", []) or []
    return [gch for gch in people if is_same_group(gch, ch)]


def _act_has_flag(character: Character, flag: ActFlag) -> bool:
    try:
        return bool(int(getattr(character, "act", 0)) & int(flag))
    except (TypeError, ValueError):
        return False


def _alignment_value(character: Character) -> int:
    try:
        return int(getattr(character, "alignment", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _drop_alignment_conflicts(ch: Character) -> None:
    room = getattr(ch, "room", None)
    if room is None:
        return

    equipment = getattr(ch, "equipment", {}) or {}
    if not equipment:
        return

    alignment = _alignment_value(ch)

    for obj in list(equipment.values()):
        try:
            flags = int(getattr(obj, "extra_flags", 0) or 0)
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            flags = 0
        if flags == 0:
            continue

        is_evil = alignment <= -350
        is_good = alignment >= 350
        is_neutral = not is_good and not is_evil

        should_drop = False
        if flags & int(ExtraFlag.ANTI_EVIL) and is_evil:
            should_drop = True
        elif flags & int(ExtraFlag.ANTI_GOOD) and is_good:
            should_drop = True
        elif flags & int(ExtraFlag.ANTI_NEUTRAL) and is_neutral:
            should_drop = True

        if not should_drop:
            continue

        item_name = getattr(obj, "short_descr", None) or getattr(obj, "name", None) or "it"
        if hasattr(ch, "send_to_char"):
            ch.send_to_char(f"You are zapped by {item_name}.")
        room.broadcast(f"{getattr(ch, 'name', 'Someone')} is zapped by {item_name}.", exclude=ch)

        ch.remove_object(obj)
        obj.wear_loc = int(WearLocation.NONE)
        room.add_object(obj)


def group_gain(ch: Character, victim: Character) -> None:
    """Distribute experience to *ch*'s group following ROM ``group_gain``."""

    if victim is ch:
        return

    members = group_members(ch)
    if not members:
        members = [ch]

    total_levels = 0
    for gch in members:
        level = _resolve_level(getattr(gch, "level", 0))
        if level <= 0:
            continue
        if getattr(gch, "is_npc", False):
            total_levels += max(1, level // 2)
        else:
            total_levels += level

    if total_levels <= 0:
        total_levels = max(1, _resolve_level(getattr(ch, "level", 0)))

    for gch in members:
        if getattr(gch, "is_npc", False):
            continue
        xp = xp_compute(gch, victim, total_levels)
        if xp <= 0:
            _drop_alignment_conflicts(ch)
            continue
        gch.send_to_char(f"You receive {xp} experience points.")
        gain_exp(gch, xp)
        _drop_alignment_conflicts(ch)


def xp_compute(gch: Character, victim: Character, total_levels: int) -> int:
    """Compute XP awarded for *victim* mirroring ROM ``xp_compute``."""

    gch_level = max(1, _resolve_level(getattr(gch, "level", 0)))
    victim_level = _resolve_level(getattr(victim, "level", 0))
    level_range = victim_level - gch_level

    base_table = {
        -9: 1,
        -8: 2,
        -7: 5,
        -6: 9,
        -5: 11,
        -4: 22,
        -3: 33,
        -2: 50,
        -1: 66,
        0: 83,
        1: 99,
        2: 121,
        3: 143,
        4: 165,
    }
    if level_range in base_table:
        base_exp = base_table[level_range]
    elif level_range > 4:
        base_exp = 160 + 20 * (level_range - 4)
    else:
        base_exp = 0

    if base_exp <= 0:
        return 0

    victim_alignment = _resolve_level(getattr(victim, "alignment", 0))
    gch_alignment = _resolve_level(getattr(gch, "alignment", 0))
    align_delta = victim_alignment - gch_alignment

    if not _act_has_flag(victim, ActFlag.NOALIGN):
        if align_delta > 500:
            change = (align_delta - 500) * base_exp // 500 * gch_level // max(1, total_levels)
            change = max(1, change)
            gch.alignment = max(-1000, gch_alignment - change)
        elif align_delta < -500:
            change = (-align_delta - 500) * base_exp // 500 * gch_level // max(1, total_levels)
            change = max(1, change)
            gch.alignment = min(1000, gch_alignment + change)
        else:
            change = gch_alignment * base_exp // 500 * gch_level // max(1, total_levels)
            gch.alignment -= change

    if _act_has_flag(victim, ActFlag.NOALIGN):
        xp = base_exp
    elif gch_alignment > 500:
        if victim_alignment < -750:
            xp = (base_exp * 4) // 3
        elif victim_alignment < -500:
            xp = (base_exp * 5) // 4
        elif victim_alignment > 750:
            xp = base_exp // 4
        elif victim_alignment > 500:
            xp = base_exp // 2
        elif victim_alignment > 250:
            xp = (base_exp * 3) // 4
        else:
            xp = base_exp
    elif gch_alignment < -500:
        if victim_alignment > 750:
            xp = (base_exp * 5) // 4
        elif victim_alignment > 500:
            xp = (base_exp * 11) // 10
        elif victim_alignment < -750:
            xp = base_exp // 2
        elif victim_alignment < -500:
            xp = (base_exp * 3) // 4
        elif victim_alignment < -250:
            xp = (base_exp * 9) // 10
        else:
            xp = base_exp
    elif gch_alignment > 200:
        if victim_alignment < -500:
            xp = (base_exp * 6) // 5
        elif victim_alignment > 750:
            xp = base_exp // 2
        elif victim_alignment > 0:
            xp = (base_exp * 3) // 4
        else:
            xp = base_exp
    elif gch_alignment < -200:
        if victim_alignment > 500:
            xp = (base_exp * 6) // 5
        elif victim_alignment < -750:
            xp = base_exp // 2
        elif victim_alignment < 0:
            xp = (base_exp * 3) // 4
        else:
            xp = base_exp
    else:
        if abs(victim_alignment) > 500:
            xp = (base_exp * 4) // 3
        elif -200 < victim_alignment < 200:
            xp = base_exp // 2
        else:
            xp = base_exp

    if gch_level < 6:
        xp = 10 * xp // (gch_level + 4)
    if gch_level > 35:
        xp = 15 * xp // max(1, gch_level - 25)

    played_seconds = int(getattr(gch, "played", 0) or 0)
    logon_time = getattr(gch, "logon", None)
    try:
        logon_ts = float(logon_time) if logon_time is not None else time.time()
    except (TypeError, ValueError):
        logon_ts = time.time()
    elapsed = max(0, int(time.time() - logon_ts))
    numerator = 4 * (played_seconds + elapsed)
    time_per_level = 0
    if gch_level > 0:
        time_per_level = numerator // 3600 // gch_level
    time_per_level = urange(2, time_per_level, 12)
    if gch_level < 15:
        time_per_level = max(time_per_level, 15 - gch_level)
    xp = xp * time_per_level // 12

    low = xp * 3 // 4
    high = xp * 5 // 4
    xp = rng_mm.number_range(low, high)

    divisor = max(1, total_levels - 1)
    xp = xp * gch_level // divisor
    return max(0, xp)


__all__ = ["group_gain", "xp_compute", "group_members"]
