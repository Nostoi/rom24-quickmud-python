from __future__ import annotations

from collections.abc import Iterable

from mud import mobprog
from mud.models.character import Character
from mud.models.constants import (
    CLASS_GUILD_ROOMS,
    EX_CLOSED,
    EX_NOPASS,
    LEVEL_HERO,
    ActFlag,
    AffectFlag,
    Direction,
    ItemType,
    Position,
    RoomFlag,
    Sector,
)
from mud.models.room import Exit, Room
from mud.net.protocol import broadcast_room
from mud.world.look import look
from mud.world.vision import can_see_room

dir_map: dict[str, Direction] = {
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
    0,  # 0
    3,
    3,
    10,
    25,
    55,  # 1..5
    80,
    90,
    100,
    100,
    115,
    115,
    130,
    130,
    140,
    150,
    165,
    180,
    200,
    225,
    250,
    300,
    350,
    400,
    450,
    500,
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


def _exit_block_message(char: Character, exit: Exit) -> str | None:
    """Return ROM-style denial message if a closed exit blocks movement."""

    exit_info = int(getattr(exit, "exit_info", 0) or 0)
    if not exit_info:
        return None

    is_closed = bool(exit_info & EX_CLOSED)
    if not is_closed:
        return None

    has_pass_door = bool(char.affected_by & AffectFlag.PASS_DOOR)
    exit_nopass = bool(exit_info & EX_NOPASS)
    is_trusted = char.is_admin or char.is_immortal()

    if (has_pass_door and not exit_nopass) or is_trusted:
        return None

    keyword = (exit.keyword or "door").strip() or "door"
    return f"The {keyword} is closed."


def _is_room_owner(char: Character, room: Room) -> bool:
    owner = (getattr(room, "owner", None) or "").strip()
    if not owner or not char.name:
        return False
    owner_names = {token.lower() for token in owner.split() if token}
    return char.name.lower() in owner_names


def _room_is_private(room: Room) -> bool:
    if getattr(room, "owner", None):
        return True

    occupants = len(getattr(room, "people", []) or [])
    flags = int(getattr(room, "room_flags", 0) or 0)

    if flags & int(RoomFlag.ROOM_PRIVATE) and occupants >= 2:
        return True
    if flags & int(RoomFlag.ROOM_SOLITARY) and occupants >= 1:
        return True
    if flags & int(RoomFlag.ROOM_IMP_ONLY):
        return True
    return False


def _is_foreign_guild_room(room: Room, ch_class: int) -> bool:
    vnum = getattr(room, "vnum", 0)
    if not vnum:
        return False

    for class_id, guild_vnums in CLASS_GUILD_ROOMS.items():
        if class_id == ch_class:
            continue
        if any(vnum == guild for guild in guild_vnums if guild):
            return True
    return False


def _auto_look(char: Character) -> None:
    """Send the destination room description like ROM `do_look auto`."""

    if not hasattr(char, "send_to_char"):
        return
    view = look(char)
    if view:
        char.send_to_char(view)


def _stand_charmed_follower(follower: Character) -> None:
    """Mimic ROM `do_stand` wake-up for charmed followers."""

    if follower.position <= Position.SLEEPING:
        message = "You wake and stand up."
    else:
        message = "You stand up."
    follower.position = Position.STANDING
    if hasattr(follower, "send_to_char"):
        follower.send_to_char(message)


def move_character(char: Character, direction: str, *, _is_follow: bool = False) -> str:
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
    target_room_flags = int(getattr(target_room, "room_flags", 0) or 0)

    if not char.is_npc:
        if mobprog.mp_exit_trigger(char, idx):
            return ""

    if not can_see_room(char, target_room):
        return "Alas, you cannot go that way."

    blocked_msg = _exit_block_message(char, exit)
    if blocked_msg:
        return blocked_msg

    if char.has_affect(AffectFlag.CHARM):
        master = getattr(char, "master", None)
        if master is not None and getattr(master, "room", None) is current_room:
            return "What?  And leave your beloved master?"

    trusted = char.is_admin or char.is_immortal()
    if not trusted and not _is_room_owner(char, target_room) and _room_is_private(target_room):
        return "That room is private right now."

    followers_to_move = [
        follower
        for follower in list(current_room.people)
        if follower is not char and getattr(follower, "master", None) is char
    ]

    if not char.is_npc and not trusted and _is_foreign_guild_room(target_room, char.ch_class):
        return "You aren't allowed in there."

    # --- Sector-based gating and movement costs (ROM act_move.c) ---
    from_sector = Sector(current_room.sector_type)
    to_sector = Sector(target_room.sector_type)

    if not char.is_npc:
        is_privileged = char.is_admin or char.is_immortal()

        # Air requires flying unless immortal/admin
        if from_sector == Sector.AIR or to_sector == Sector.AIR:
            if not (is_privileged or bool(char.affected_by & AffectFlag.FLYING)):
                return "You can't fly."

        # Water (no swim) requires a boat unless flying or immortal
        if from_sector == Sector.WATER_NOSWIM or to_sector == Sector.WATER_NOSWIM:
            if not (is_privileged or bool(char.affected_by & AffectFlag.FLYING)):

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

    char_name = char.name or "someone"
    show_movement = not (char.has_affect(AffectFlag.SNEAK) or getattr(char, "invis_level", 0) >= LEVEL_HERO)

    if show_movement:
        broadcast_room(current_room, f"{char_name} leaves {dir_key}.", exclude=char)
    current_room.remove_character(char)
    target_room.add_character(char)
    if show_movement:
        broadcast_room(target_room, f"{char_name} arrives.", exclude=char)

    _auto_look(char)

    if current_room is target_room:
        return f"You walk {dir_key} to {target_room.name}."

    for follower in followers_to_move:
        if follower.room is not current_room:
            continue
        if follower.has_affect(AffectFlag.CHARM) and follower.position < Position.STANDING:
            _stand_charmed_follower(follower)
        if follower.position < Position.STANDING:
            continue
        if not can_see_room(follower, target_room):
            continue
        if (
            target_room_flags & int(RoomFlag.ROOM_LAW)
            and follower.is_npc
            and bool(getattr(follower, "act", 0) & int(ActFlag.AGGRESSIVE))
        ):
            if hasattr(char, "send_to_char"):
                char.send_to_char("You can't bring that follower into the city.")
            if hasattr(follower, "send_to_char"):
                follower.send_to_char("You aren't allowed in the city.")
            continue

        if hasattr(follower, "send_to_char") and char.name:
            follower.send_to_char(f"You follow {char.name}.")
        move_character(follower, direction, _is_follow=True)

    if char.is_npc:
        mobprog.mp_percent_trigger(char, trigger=mobprog.Trigger.ENTRY)
    else:
        mobprog.mp_greet_trigger(char)

    return f"You walk {dir_key} to {target_room.name}."
