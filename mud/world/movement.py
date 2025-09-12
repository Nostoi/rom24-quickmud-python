from __future__ import annotations
from typing import Dict, Iterable

from mud.models.character import Character
from mud.models.constants import Direction, Sector, AffectFlag, ItemType
from mud.net.protocol import broadcast_room


dir_map: Dict[str, Direction] = {
    "north": Direction.NORTH,
    "east": Direction.EAST,
    "south": Direction.SOUTH,
    "west": Direction.WEST,
    "up": Direction.UP,
    "down": Direction.DOWN,
}


# ROM str_app carry table (carry column only) for STR 0..25.
# Source: src/const.c:str_app (third field), multiplied by 10 in handler.c.
_STR_CARRY = [
    0,   # 0
    3, 3, 10, 25, 55,  # 1..5
    80, 90, 100, 100, 115, 115, 130, 130, 140, 150, 165, 180, 200, 225, 250, 300, 350, 400, 450, 500,
]


def _get_curr_stat(ch: Character, idx: int) -> int | None:
    stats = getattr(ch, "perm_stat", None) or []
    if idx < len(stats) and stats[idx] > 0:
        val = stats[idx]
        return max(0, min(25, int(val)))
    return None


def can_carry_w(ch: Character) -> int:
    """Carry weight capacity.

    - If STR stat present: use ROM formula `str_app[STR].carry * 10 + level * 25`.
    - Otherwise: preserve prior fixed cap (100) to avoid changing existing tests.
    """
    s = _get_curr_stat(ch, 0)  # STAT_STR
    if s is None:
        return 100
    carry = _STR_CARRY[s]
    return carry * 10 + ch.level * 25


def can_carry_n(ch: Character) -> int:
    """Carry number capacity.

    - If DEX stat present: use ROM-like `MAX_WEAR + 2*DEX + level` (MAX_WEAR≈19).
    - Otherwise: preserve prior fixed cap (30).
    """
    d = _get_curr_stat(ch, 1)  # STAT_DEX
    if d is None:
        return 30
    MAX_WEAR = 19
    return MAX_WEAR + 2 * d + ch.level


def move_character(char: Character, direction: str) -> str:
    dir_key = direction.lower()
    if dir_key not in dir_map:
        return "You cannot go that way."

    if char.carry_weight > can_carry_w(char) or char.carry_number > can_carry_n(char):
        return "You are too encumbered to move."

    idx = dir_map[dir_key]
    exit = char.room.exits[idx]
    if exit is None or exit.to_room is None:
        return "You cannot go that way."

    current_room = char.room
    target_room = exit.to_room

    # --- Sector-based gating and movement costs (ROM act_move.c) ---
    from_sector = Sector(current_room.sector_type)
    to_sector = Sector(target_room.sector_type)

    # Air requires flying unless immortal/admin
    if (from_sector == Sector.AIR or to_sector == Sector.AIR):
        if not char.is_admin and not bool(char.affected_by & AffectFlag.FLYING):
            return "You can't fly."

    # Water (no swim) requires a boat unless flying or immortal
    if (from_sector == Sector.WATER_NOSWIM or to_sector == Sector.WATER_NOSWIM):
        if not char.is_admin and not bool(char.affected_by & AffectFlag.FLYING):
            def has_boat(objs: Iterable):
                for o in objs:
                    proto = getattr(o, "prototype", None)
                    if proto and getattr(proto, "item_type", None) == int(ItemType.BOAT):
                        return True
                return False

            has_boat_item = has_boat(char.inventory) or has_boat(getattr(char, "equipment", {}).values())
            if not has_boat_item:
                return "You need a boat to go there."

    movement_loss = {
        Sector.INSIDE: 1,
        Sector.CITY: 2,
        Sector.FIELD: 2,
        Sector.FOREST: 3,
        Sector.HILLS: 4,
        Sector.MOUNTAIN: 6,
        Sector.WATER_SWIM: 4,
        Sector.WATER_NOSWIM: 1,
        Sector.UNUSED: 6,
        Sector.AIR: 10,
        Sector.DESERT: 6,
    }

    move_cost = (movement_loss.get(from_sector, 2) + movement_loss.get(to_sector, 2)) // 2
    # Conditional effects
    if char.affected_by & AffectFlag.FLYING or char.affected_by & AffectFlag.HASTE:
        move_cost = max(0, move_cost // 2)
    if char.affected_by & AffectFlag.SLOW:
        move_cost *= 2

    if char.move < move_cost:
        return "You are too exhausted."

    # Apply short wait-state and deduct movement points
    char.wait = max(char.wait, 1)
    char.move -= move_cost

    broadcast_room(current_room, f"{char.name} leaves {dir_key}.", exclude=char)
    if char in current_room.people:
        current_room.people.remove(char)
    target_room.people.append(char)
    char.room = target_room
    broadcast_room(target_room, f"{char.name} arrives.", exclude=char)
    return f"You walk {dir_key} to {target_room.name}."
