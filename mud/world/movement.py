from __future__ import annotations

from collections.abc import Iterable

from collections.abc import Callable

from mud import mobprog
from mud.models.character import Character
from mud.models.constants import (
    CLASS_GUILD_ROOMS,
    EX_CLOSED,
    EX_NOPASS,
    LEVEL_ANGEL,
    LEVEL_HERO,
    LEVEL_IMMORTAL,
    MAX_LEVEL,
    ActFlag,
    AffectFlag,
    Direction,
    ItemType,
    PortalFlag,
    Position,
    RoomFlag,
    Sector,
)
from mud.models.room import Exit, Room
from mud.net.protocol import broadcast_room
from mud.utils.act import act_format
from mud.registry import room_registry
from mud.world.look import look
from mud.world.vision import can_see_room
from mud.utils import rng_mm

dir_map: dict[str, Direction] = {
    "north": Direction.NORTH,
    "east": Direction.EAST,
    "south": Direction.SOUTH,
    "west": Direction.WEST,
    "up": Direction.UP,
    "down": Direction.DOWN,
}


def _coerce_sector_type(raw: object) -> Sector:
    """Clamp sector identifiers into the ROM sector enum range."""

    if isinstance(raw, Sector):
        numeric = int(raw)
    else:
        try:
            numeric = int(raw)
        except (TypeError, ValueError):
            numeric = int(Sector.MOUNTAIN)

    max_index = int(Sector.MAX) - 1
    if numeric < 0 or numeric > max_index:
        numeric = int(Sector.MOUNTAIN)

    return Sector(numeric)


def _get_trust(char: Character) -> int:
    trust = int(getattr(char, "trust", 0) or 0)
    if trust <= 0:
        trust = int(getattr(char, "level", 0) or 0)
    if char.is_admin and trust < LEVEL_IMMORTAL:
        return LEVEL_IMMORTAL
    return trust


def _collect_followers(current_room: Room, leader: Character) -> list[Character]:
    return [
        follower
        for follower in list(getattr(current_room, "people", []) or [])
        if follower is not leader and getattr(follower, "master", None) is leader
    ]


def _move_followers(
    leader: Character,
    current_room: Room,
    target_room: Room,
    target_room_flags: int,
    mover: Callable[[Character], None],
) -> None:
    for follower in _collect_followers(current_room, leader):
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
            if hasattr(leader, "send_to_char"):
                follower_name = getattr(follower, "name", None) or "someone"
                leader.send_to_char(f"You can't bring {follower_name} into the city.")
            if hasattr(follower, "send_to_char"):
                follower.send_to_char("You aren't allowed in the city.")
            continue
        # ENTER-007: ROM uses act("You follow $N.", fch, NULL, ch, TO_CHAR)
        # act_enter.c:195 — $N applies visibility; use act_format so invisible
        # leaders show as "someone"
        if hasattr(follower, "send_to_char"):
            follow_msg = act_format("You follow $N.", recipient=follower, actor=follower, arg2=leader)
            follower.send_to_char(follow_msg)
        mover(follower)


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


def _is_pet(ch: Character) -> bool:
    if not getattr(ch, "is_npc", True):
        return False
    act_flags = int(getattr(ch, "act", 0) or 0)
    return bool(act_flags & int(ActFlag.PET))


def can_carry_w(ch: Character) -> int:
    """Carry weight capacity.

    - If STR stat present: use ROM formula `str_app[STR].carry * 10 + level * 25`.
    - Otherwise: preserve prior fixed cap (100) to avoid changing existing tests.
    """
    level = int(getattr(ch, "level", 0) or 0)
    if not getattr(ch, "is_npc", True) and level >= LEVEL_IMMORTAL:
        return 10_000_000
    if _is_pet(ch):
        return 0

    s = _get_curr_stat(ch, 0)  # STAT_STR
    if s is None:
        return 100
    carry = _STR_CARRY[s]
    return carry * 10 + level * 25


def can_carry_n(ch: Character) -> int:
    """Carry number capacity.

    - If DEX stat present: use ROM-like `MAX_WEAR + 2*DEX + level` (MAX_WEAR≈19).
    - Otherwise: preserve prior fixed cap (30).
    """
    level = int(getattr(ch, "level", 0) or 0)
    if not getattr(ch, "is_npc", True) and level >= LEVEL_IMMORTAL:
        return 1000
    if _is_pet(ch):
        return 0

    d = _get_curr_stat(ch, 1)  # STAT_DEX
    if d is None:
        return 30
    MAX_WEAR = 19
    return MAX_WEAR + 2 * d + level


def get_carry_weight(ch: Character) -> int:
    """Return total carry weight including coin burden, mirroring ROM `get_carry_weight`."""

    getter = getattr(ch, "get_carry_weight", None)
    if callable(getter):
        try:
            return int(getter())
        except TypeError:  # pragma: no cover - defensive fallback
            pass
    base_weight = int(getattr(ch, "carry_weight", 0) or 0)
    silver = int(getattr(ch, "silver", 0) or 0)
    gold = int(getattr(ch, "gold", 0) or 0)
    return base_weight + silver // 10 + (gold * 2) // 5


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


def _get_random_room(ch: Character) -> Room | None:
    """Find a random valid destination room, mirroring ROM src/act_enter.c:44-63.

    ROM uses an infinite for(;;) loop — it never returns NULL.  We use a very
    large iteration cap (100 000) to avoid hanging the process if the registry
    is empty, but in normal play this will always find a room.
    """
    # ENTER-013: ROM loops forever; use a large cap to match the invariant
    # (act_enter.c:48 for(;;))
    for _ in range(100_000):
        vnum = rng_mm.number_range(0, 65535)
        room = room_registry.get(vnum)
        if room is None:
            continue
        if not can_see_room(ch, room):
            continue
        if _room_is_private(room):
            continue
        flags = int(getattr(room, "room_flags", 0) or 0)
        if flags & (int(RoomFlag.ROOM_PRIVATE) | int(RoomFlag.ROOM_SOLITARY) | int(RoomFlag.ROOM_SAFE)):
            continue
        # ENTER-001: act_enter.c:57-58 — NPC or aggressive PC may enter LAW rooms
        act_flags = int(getattr(ch, "act", 0) or 0)
        if not ch.is_npc and not (act_flags & int(ActFlag.AGGRESSIVE)):
            if flags & int(RoomFlag.ROOM_LAW):
                continue
        return room
    return None


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
    """Stand up a charmed follower before portal transit.

    # mirroring ROM src/act_enter.c:178-180 — delegates to do_stand
    """
    # ENTER-006: ROM calls do_function(fch, &do_stand, "") — delegate to real do_stand.
    # do_stand returns the message string (Python convention); ROM C uses send_to_char
    # directly. Forward the message to the follower's message stream so observers like
    # tests/test_movement_followers.py can verify "You wake and stand up." was emitted.
    try:
        from mud.commands.position import do_stand as _do_stand

        result = _do_stand(follower, "")
        if isinstance(result, str) and result and hasattr(follower, "send_to_char"):
            for line in result.splitlines():
                line = line.rstrip("\r")
                if line:
                    follower.send_to_char(line)
    except Exception:
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

    if get_carry_weight(char) > can_carry_w(char) or char.carry_number > can_carry_n(char):
        current_wait = int(getattr(char, "wait", 0) or 0)
        char.wait = max(current_wait, 1)
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

    if not char.is_npc and not trusted and _is_foreign_guild_room(target_room, char.ch_class):
        return "You aren't allowed in there."

    # --- Sector-based gating and movement costs (ROM act_move.c) ---
    from_sector = _coerce_sector_type(getattr(current_room, "sector_type", 0))
    to_sector = _coerce_sector_type(getattr(target_room, "sector_type", 0))

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
        broadcast_room(target_room, f"{char_name} has arrived.", exclude=char)

    _auto_look(char)

    if current_room is target_room:
        return f"You walk {dir_key} to {target_room.name}."

    _move_followers(
        char,
        current_room,
        target_room,
        target_room_flags,
        lambda follower: move_character(follower, direction, _is_follow=True),
    )

    if char.is_npc:
        mobprog.mp_percent_trigger(char, trigger=mobprog.Trigger.ENTRY)
    else:
        mobprog.mp_greet_trigger(char)

    return f"You walk {dir_key} to {target_room.name}."


def move_character_through_portal(char: Character, portal: object, *, _is_follow: bool = False) -> str:
    """Move a character through a portal object.

    # mirroring ROM src/act_enter.c:66-229 (do_enter portal branch)
    """
    current_room = getattr(char, "room", None)
    if current_room is None:
        return "You are nowhere."

    # ENTER-016: ROM is silent when fighting (act_enter.c:70-71) — no message sent
    if getattr(char, "fighting", None) is not None:
        return ""

    proto = getattr(portal, "prototype", None)
    values = getattr(portal, "value", None)
    if not isinstance(values, list):
        proto_values = getattr(proto, "value", None)
        if isinstance(proto_values, list):
            values = list(proto_values)
        else:
            values = [0, 0, 0, 0, 0]
        if hasattr(portal, "value"):
            portal.value = values

    exit_flags = int(values[1]) if len(values) > 1 else 0
    gate_flags = int(values[2]) if len(values) > 2 else 0
    dest_vnum = int(values[3]) if len(values) > 3 else 0

    trust = _get_trust(char)
    is_trusted = char.is_admin or trust >= LEVEL_ANGEL

    if _is_follow and not is_trusted and not (gate_flags & int(PortalFlag.NOCURSE)):
        room_flags = int(getattr(current_room, "room_flags", 0) or 0)
        if char.has_affect(AffectFlag.CURSE) or room_flags & int(RoomFlag.ROOM_NO_RECALL):
            if hasattr(char, "send_to_char"):
                char.send_to_char("Something prevents you from leaving...")
            return "Something prevents you from leaving..."

    if exit_flags & EX_CLOSED and not is_trusted:
        return "You can't seem to find a way in."

    if not is_trusted and not (gate_flags & int(PortalFlag.NOCURSE)):
        room_flags = int(getattr(current_room, "room_flags", 0) or 0)
        if char.has_affect(AffectFlag.CURSE) or room_flags & int(RoomFlag.ROOM_NO_RECALL):
            return "Something prevents you from leaving..."

    destination: Room | None
    if gate_flags & int(PortalFlag.RANDOM) or dest_vnum == -1:
        destination = _get_random_room(char)
        if destination is not None and len(values) > 3:
            values[3] = int(getattr(destination, "vnum", 0) or 0)
    elif gate_flags & int(PortalFlag.BUGGY) and rng_mm.number_percent() < 5:
        destination = _get_random_room(char)
    else:
        destination = room_registry.get(dest_vnum)

    if (
        destination is None
        or destination is current_room
        or not can_see_room(char, destination)
        or (_room_is_private(destination) and not (char.is_admin or trust >= MAX_LEVEL))
    ):
        # ENTER-015: ROM uses act("$p doesn't seem to go anywhere.", ...) (act_enter.c:122)
        no_dest_msg = act_format("$p doesn't seem to go anywhere.", recipient=char, actor=char, arg1=portal)
        if hasattr(char, "send_to_char"):
            char.send_to_char(no_dest_msg)
        return no_dest_msg

    dest_flags = int(getattr(destination, "room_flags", 0) or 0)
    if char.is_npc and bool(getattr(char, "act", 0) & int(ActFlag.AGGRESSIVE)) and dest_flags & int(RoomFlag.ROOM_LAW):
        return "Something prevents you from leaving..."

    uses_normal_exit = bool(gate_flags & int(PortalFlag.NORMAL_EXIT))

    # ENTER-008: TO_ROOM departure uses act() for $n/$p visibility (act_enter.c:134)
    # "$n steps into $p." — $n resolves char visibility, $p resolves portal name
    departure_msg = act_format("$n steps into $p.", recipient=None, actor=char, arg1=portal)
    broadcast_room(current_room, departure_msg, exclude=char)

    # ENTER-009: TO_CHAR entry message sent BEFORE room move (act_enter.c:136-140)
    if uses_normal_exit:
        entry_msg = act_format("You enter $p.", recipient=char, actor=char, arg1=portal)
    else:
        entry_msg = act_format(
            "You walk through $p and find yourself somewhere else...", recipient=char, actor=char, arg1=portal
        )
    if hasattr(char, "send_to_char"):
        char.send_to_char(entry_msg)

    # Move character: char_from_room → char_to_room (act_enter.c:142-143)
    current_room.remove_character(char)
    destination.add_character(char)

    if gate_flags & int(PortalFlag.GOWITH):
        # GOWITH: take portal along (act_enter.c:145-149)
        contents = getattr(current_room, "contents", None)
        if isinstance(contents, list) and portal in contents:
            contents.remove(portal)
        destination.add_object(portal)

    # ENTER-010: TO_ROOM arrival uses act() for $n/$p visibility (act_enter.c:151-154)
    if uses_normal_exit:
        arrival_msg = act_format("$n has arrived.", recipient=None, actor=char, arg1=portal)
    else:
        arrival_msg = act_format("$n has arrived through $p.", recipient=None, actor=char, arg1=portal)
    broadcast_room(destination, arrival_msg, exclude=char)

    # do_look "auto" (act_enter.c:156)
    _auto_look(char)

    # Charge decrement (act_enter.c:158-164) — happens BEFORE follower cascade
    if len(values) > 0 and int(values[0]) > 0:
        values[0] = int(values[0]) - 1
        if values[0] == 0:
            values[0] = -1

    charges_remaining = int(values[0]) if len(values) > 0 else 0

    # Follower cascade — guard circular follow (act_enter.c:167-198)
    if not (gate_flags & int(PortalFlag.GOWITH)) and charges_remaining != -1:
        target_flags = dest_flags
        _move_followers(
            char,
            current_room,
            destination,
            target_flags,
            lambda follower: move_character_through_portal(follower, portal, _is_follow=False),
        )

    # Mob-prog triggers (act_enter.c:219-222)
    if char.is_npc:
        mobprog.mp_percent_trigger(char, trigger=mobprog.Trigger.ENTRY)
    else:
        mobprog.mp_greet_trigger(char)

    # ENTER-011: Portal fade-out (act_enter.c:200-213)
    # Broadcast logic depends on whether traveller ended up in a different room
    if charges_remaining == -1:
        _portal_fade_out(char, portal, current_room, destination)

    return entry_msg


def _portal_fade_out(char: Character, portal: object, old_room: object, destination: object) -> None:
    """Handle portal fade-out after charge expiry.

    # mirroring ROM src/act_enter.c:200-213
    """
    # Lazy import to avoid circular imports
    try:
        from mud.game_loop import _extract_obj as extract_obj
    except ImportError:
        extract_obj = None

    fade_fmt = "$p fades out of existence."

    # TO_CHAR: traveller (now in destination) always gets the message
    to_char_msg = act_format(fade_fmt, recipient=char, actor=char, arg1=portal)
    if hasattr(char, "send_to_char"):
        char.send_to_char(to_char_msg)

    if char.room is old_room:
        # Destination == origin: also TO_ROOM in that room (act_enter.c:204)
        to_room_msg = act_format(fade_fmt, recipient=None, actor=char, arg1=portal)
        broadcast_room(old_room, to_room_msg, exclude=char)
    else:
        # Destination != origin: notify old_room occupants (act_enter.c:205-211)
        old_people = list(getattr(old_room, "people", []) or [])
        if old_people:
            witness = old_people[0]
            to_char_old_msg = act_format(fade_fmt, recipient=witness, actor=witness, arg1=portal)
            if hasattr(witness, "send_to_char"):
                witness.send_to_char(to_char_old_msg)
            to_room_old_msg = act_format(fade_fmt, recipient=None, actor=witness, arg1=portal)
            broadcast_room(old_room, to_room_old_msg, exclude=witness)

    # extract_obj equivalent (act_enter.c:212).
    # game_loop._extract_obj keys off `in_room`, but Object uses `location`; always
    # do the explicit room-contents cleanup so portals fully detach regardless.
    if extract_obj is not None:
        try:
            extract_obj(portal)
        except Exception:
            pass
    for room in (old_room, destination):
        contents = getattr(room, "contents", None)
        if isinstance(contents, list) and portal in contents:
            contents.remove(portal)
    if hasattr(portal, "location"):
        portal.location = None
