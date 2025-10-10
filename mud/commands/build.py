from __future__ import annotations

import shlex
from collections import defaultdict

from mud.models.area import Area
from mud.models.character import Character
from mud.models.constants import (
    Direction,
    EX_CLOSED,
    EX_EASY,
    EX_HARD,
    EX_INFURIATING,
    EX_ISDOOR,
    EX_LOCKED,
    EX_NOPASS,
    EX_NOLOCK,
    EX_NOCLOSE,
    EX_PICKPROOF,
)
from mud.models.room import ExtraDescr, Exit, Room
from mud.net.session import Session
from mud.registry import room_registry


def _get_session(char: Character) -> Session | None:
    desc = getattr(char, "desc", None)
    if isinstance(desc, Session):
        return desc
    return None


def _is_builder(char: Character, area: Area | None) -> bool:
    if area is None:
        return False
    pcdata = getattr(char, "pcdata", None)
    area_security = int(getattr(area, "security", 0))
    char_security = int(getattr(pcdata, "security", 0)) if pcdata else 0
    if area_security > 0 and char_security >= area_security:
        return True
    builders = (getattr(area, "builders", "") or "").strip()
    if builders and builders.lower() not in {"none"}:
        tokens = {token.lower() for token in builders.replace(",", " ").split()}
        if char.name and char.name.lower() in tokens:
            return True
    return False


def _mark_area_changed(room: Room | None) -> None:
    if not room:
        return
    area = getattr(room, "area", None)
    if area is not None:
        area.changed = True


def _ensure_session_room(session: Session, room: Room) -> None:
    session.editor = "redit"
    session.editor_state["room"] = room


def _clear_session(session: Session) -> None:
    session.editor = None
    session.editor_state.clear()


def _room_summary(room: Room) -> str:
    description = room.description or "(no description set)"
    name = room.name or "(no name)"
    exit_bits: list[str] = []
    for idx, exit_obj in enumerate(room.exits):
        if not exit_obj:
            continue
        direction = Direction(idx).name.lower()
        target = exit_obj.vnum or "(unset)"
        exit_bits.append(f"{direction}->{target}")
    extra_keywords = [extra.keyword for extra in room.extra_descr if extra.keyword]
    extras = ", ".join(extra_keywords) if extra_keywords else "none"
    exits_display = "; ".join(exit_bits) if exit_bits else "none"
    return (
        f"[{room.vnum}] {name}\n{description}\n"
        f"Exits: {exits_display}\nExtras: {extras}"
    )


_DIRECTION_ALIASES: dict[str, Direction] = {
    "north": Direction.NORTH,
    "n": Direction.NORTH,
    "east": Direction.EAST,
    "e": Direction.EAST,
    "south": Direction.SOUTH,
    "s": Direction.SOUTH,
    "west": Direction.WEST,
    "w": Direction.WEST,
    "up": Direction.UP,
    "u": Direction.UP,
    "down": Direction.DOWN,
    "d": Direction.DOWN,
}

_EXIT_FLAG_ALIASES: dict[str, int] = {
    "none": 0,
    "door": EX_ISDOOR,
    "closed": EX_CLOSED,
    "locked": EX_LOCKED,
    "pickproof": EX_PICKPROOF,
    "nopass": EX_NOPASS,
    "easy": EX_EASY,
    "hard": EX_HARD,
    "infuriating": EX_INFURIATING,
    "noclose": EX_NOCLOSE,
    "nolock": EX_NOLOCK,
}


def _ensure_exit(room: Room, direction: Direction) -> Exit:
    if direction.value >= len(room.exits):
        room.exits.extend([None] * (direction.value - len(room.exits) + 1))
    exit_obj = room.exits[direction.value]
    if exit_obj is None:
        exit_obj = Exit()
        room.exits[direction.value] = exit_obj
    return exit_obj


def _format_exit_flags(exit_info: int) -> str:
    if not exit_info:
        return "none"
    tokens: list[str] = []
    for name, flag in _EXIT_FLAG_ALIASES.items():
        if name == "none":
            continue
        if exit_info & flag:
            tokens.append(name)
    return " ".join(tokens) if tokens else "none"


def _handle_exit_command(room: Room, direction: Direction, args_parts: list[str]) -> str:
    if not args_parts:
        exit_obj = room.exits[direction.value] if direction.value < len(room.exits) else None
        if exit_obj is None:
            return f"No exit set for {direction.name.lower()}."
        target = exit_obj.vnum if exit_obj.vnum is not None else "(unset)"
        key = exit_obj.key if exit_obj.key else 0
        flags = _format_exit_flags(int(getattr(exit_obj, "exit_info", 0) or 0))
        keyword = exit_obj.keyword or "(none)"
        description = exit_obj.description or "(no description)"
        return (
            f"Exit {direction.name.lower()} -> {target}\n"
            f"Key: {key} Flags: {flags}\n"
            f"Keyword: {keyword}\n{description}"
        )

    subcmd = args_parts[0].lower()
    rest = args_parts[1:]
    if subcmd == "create":
        if not rest:
            return "Usage: <direction> create <target vnum>"
        try:
            target_vnum = int(rest[0])
        except ValueError:
            return "Target vnum must be a number."
        exit_obj = _ensure_exit(room, direction)
        exit_obj.vnum = target_vnum
        exit_obj.to_room = room_registry.get(target_vnum)
        exit_obj.exit_info = 0
        exit_obj.key = 0
        exit_obj.keyword = None
        exit_obj.description = None
        _mark_area_changed(room)
        return f"Exit {direction.name.lower()} now leads to room {target_vnum}."

    if subcmd in {"delete", "remove"}:
        if direction.value >= len(room.exits) or room.exits[direction.value] is None:
            return "No exit to delete."
        room.exits[direction.value] = None
        _mark_area_changed(room)
        return f"Exit {direction.name.lower()} removed."

    exit_obj = _ensure_exit(room, direction)

    if subcmd in {"room", "to"}:
        if not rest:
            return "Usage: <direction> room <target vnum>"
        try:
            target_vnum = int(rest[0])
        except ValueError:
            return "Target vnum must be a number."
        exit_obj.vnum = target_vnum
        exit_obj.to_room = room_registry.get(target_vnum)
        _mark_area_changed(room)
        return f"Exit {direction.name.lower()} now leads to room {target_vnum}."

    if subcmd == "key":
        if not rest:
            return "Usage: <direction> key <object vnum>"
        try:
            key_vnum = int(rest[0])
        except ValueError:
            return "Key must be a number."
        exit_obj.key = key_vnum
        _mark_area_changed(room)
        return f"Exit {direction.name.lower()} key set to {key_vnum}."

    if subcmd in {"desc", "description"}:
        if not rest:
            return "Usage: <direction> desc <text>"
        description = " ".join(rest)
        exit_obj.description = description
        _mark_area_changed(room)
        return "Exit description updated."

    if subcmd in {"keyword", "keywords"}:
        if not rest:
            return "Usage: <direction> keyword <text>"
        exit_obj.keyword = " ".join(rest)
        _mark_area_changed(room)
        return "Exit keyword updated."

    if subcmd == "flags":
        if not rest:
            return "Usage: <direction> flags <flag list>"
        if len(rest) == 1 and rest[0].lower() == "none":
            exit_obj.exit_info = 0
            _mark_area_changed(room)
            return "Exit flags cleared."
        bits = 0
        unknown: defaultdict[str, int] = defaultdict(int)
        for token in rest:
            flag = _EXIT_FLAG_ALIASES.get(token.lower())
            if flag is None:
                unknown[token.lower()] += 1
                continue
            bits |= flag
        if unknown:
            bad = ", ".join(sorted(unknown))
            return f"Unknown exit flags: {bad}."
        exit_obj.exit_info = bits
        _mark_area_changed(room)
        return f"Exit flags set to {_format_exit_flags(bits)}."

    return "Unknown exit editor command."


def _find_extra(room: Room, keyword: str) -> ExtraDescr | None:
    for extra in room.extra_descr:
        if (extra.keyword or "").lower() == keyword.lower():
            return extra
    return None


def _handle_extra_command(room: Room, args_parts: list[str]) -> str:
    if not args_parts:
        return "Usage: ed <add|desc|delete|list> ..."
    subcmd = args_parts[0].lower()
    rest = args_parts[1:]
    if subcmd == "list":
        if not room.extra_descr:
            return "No extra descriptions defined."
        lines = ["Extra descriptions:"]
        for extra in room.extra_descr:
            keyword = extra.keyword or "(none)"
            desc = extra.description or "(no description)"
            lines.append(f"- {keyword}: {desc}")
        return "\n".join(lines)

    if subcmd == "add":
        if not rest:
            return "Usage: ed add <keyword>"
        keyword = rest[0]
        extra = _find_extra(room, keyword)
        if extra is None:
            extra = ExtraDescr(keyword=keyword, description="")
            room.extra_descr.append(extra)
        else:
            extra.keyword = keyword
        _mark_area_changed(room)
        return f"Extra description '{keyword}' created. Use 'ed desc {keyword} <text>' to set the text."

    if subcmd in {"delete", "remove"}:
        if not rest:
            return "Usage: ed delete <keyword>"
        keyword = rest[0]
        extra = _find_extra(room, keyword)
        if extra is None:
            return f"No extra description named '{keyword}'."
        room.extra_descr.remove(extra)
        _mark_area_changed(room)
        return f"Extra description '{keyword}' removed."

    if subcmd in {"desc", "description"}:
        if len(rest) < 2:
            return "Usage: ed desc <keyword> <text>"
        keyword = rest[0]
        text = " ".join(rest[1:])
        extra = _find_extra(room, keyword)
        if extra is None:
            extra = ExtraDescr(keyword=keyword)
            room.extra_descr.append(extra)
        extra.description = text
        _mark_area_changed(room)
        return f"Extra description '{keyword}' updated."

    return "Unknown extra description command."


def _interpret_redit(session: Session, char: Character, raw_input: str) -> str:
    room = session.editor_state.get("room") if session.editor_state else None
    if not isinstance(room, Room):
        _clear_session(session)
        return "Room editor session lost. Type '@redit' to begin again."

    stripped = raw_input.strip()
    if not stripped:
        return "Syntax: name <value> | desc <value> | show | done"

    try:
        parts = shlex.split(stripped)
    except ValueError:
        return "Invalid room editor syntax."
    if not parts:
        return "Syntax: name <value> | desc <value> | show | done"

    cmd = parts[0].lower()
    args_parts = parts[1:]
    if cmd == "@redit":
        if not args_parts:
            return "You are already editing this room."
        cmd = args_parts[0].lower()
        args_parts = args_parts[1:]

    if cmd in {"done", "exit"}:
        _clear_session(session)
        return "Exiting room editor."

    if cmd == "show":
        return _room_summary(room)

    direction = _DIRECTION_ALIASES.get(cmd)
    if direction is not None:
        return _handle_exit_command(room, direction, args_parts)

    if cmd == "ed":
        return _handle_extra_command(room, args_parts)

    value = " ".join(args_parts)
    if cmd == "name":
        if not value:
            return "Usage: name <new room name>"
        room.name = value
        _mark_area_changed(room)
        return f"Room name set to {value}"

    if cmd in {"desc", "description"}:
        if not value:
            return "Usage: desc <new room description>"
        room.description = value
        _mark_area_changed(room)
        return "Room description updated."

    return "Unknown room editor command."


def cmd_redit(char: Character, args: str) -> str:
    room = getattr(char, "room", None)
    if room is None:
        return "You are nowhere."

    if not _is_builder(char, getattr(room, "area", None)):
        return "You do not have builder rights for this area."

    session = _get_session(char)
    if session is None:
        return "You do not have an active connection to edit from."

    trimmed = args.strip()

    if trimmed and trimmed.lower() in {"done", "exit"}:
        if session.editor == "redit":
            _clear_session(session)
            return "Exiting room editor."
        return "You are not editing any room."

    if session.editor == "redit" and trimmed:
        return _interpret_redit(session, char, trimmed)

    if trimmed:
        _ensure_session_room(session, room)
        return _interpret_redit(session, char, trimmed)

    if session.editor == "redit":
        return "You are already editing this room."

    _ensure_session_room(session, room)
    return "Room editor activated. Type 'show' to review the room and 'done' to exit."


def handle_redit_command(char: Character, session: Session, input_str: str) -> str:
    return _interpret_redit(session, char, input_str)
