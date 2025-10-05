from __future__ import annotations

import shlex
from mud.models.area import Area
from mud.models.character import Character
from mud.models.room import Room
from mud.net.session import Session


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
    return f"[{room.vnum}] {name}\n{description}"


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
