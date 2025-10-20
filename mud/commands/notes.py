from __future__ import annotations

import time

from mud.models.board import BoardForceType, NoteDraft
from mud.models.character import Character, PCData
from mud.models.constants import MAX_LEVEL
from mud.notes import (
    DEFAULT_BOARD_NAME,
    find_board,
    get_board,
    iter_boards,
    save_board,
)


def _ensure_pcdata(char: Character) -> PCData:
    if char.pcdata is None:
        char.pcdata = PCData()
    if not char.pcdata.board_name:
        char.pcdata.board_name = DEFAULT_BOARD_NAME
    return char.pcdata


def _resolve_current_board(char: Character):
    pcdata = _ensure_pcdata(char)
    key = pcdata.board_name or DEFAULT_BOARD_NAME
    board = find_board(key)
    if board is None:
        board = find_board(DEFAULT_BOARD_NAME)
        if board is None:
            board = get_board(DEFAULT_BOARD_NAME)
        pcdata.board_name = board.storage_key()
    return board


def _get_trust(char: Character) -> int:
    return char.trust if char.trust > 0 else char.level


def _board_change_message(board, trust: int) -> str:
    if trust < board.write_level:
        rights = "You can only read here."
    else:
        rights = "You can both read and write here."
    return f"Current board changed to {board.name}. {rights}"


def _board_last_read(pcdata: PCData, board) -> float:
    return pcdata.last_notes.get(board.storage_key(), 0.0)


def _set_last_read(pcdata: PCData, board, timestamp: float) -> None:
    key = board.storage_key()
    pcdata.last_notes[key] = max(timestamp, pcdata.last_notes.get(key, 0.0))


_IMMORTAL_TOKENS = {
    "imm",
    "imms",
    "immortal",
    "immortals",
    "god",
    "gods",
}

_IMPLEMENTOR_TOKENS = {
    "imp",
    "imps",
    "implementor",
    "implementors",
}


def _split_tokens(value: str) -> set[str]:
    return {token.lower() for token in value.replace(",", " ").split() if token}


def _is_note_visible_to(char: Character, note) -> bool:
    """Mirror ROM is_note_to checks for removal visibility."""

    name = (char.name or "").strip().lower()
    sender = (note.sender or "").strip().lower()
    if name and sender and name == sender:
        return True

    tokens = _split_tokens(note.to or "")
    if "all" in tokens:
        return True

    if char.is_immortal() and tokens & _IMMORTAL_TOKENS:
        return True

    trust = _get_trust(char)
    if trust == MAX_LEVEL and tokens & _IMPLEMENTOR_TOKENS:
        return True

    if name and name in tokens:
        return True

    to_field = (note.to or "").strip()
    if to_field.isdigit() and trust >= int(to_field):
        return True

    return False


def _find_visible_note_index(char: Character, board, number: int) -> int | None:
    if number < 1:
        return None

    for position, note in enumerate(board.notes, start=1):
        if position == number:
            return position - 1 if _is_note_visible_to(char, note) else None

    return None


def _next_readable_board(current_board, trust: int):
    readable = [board for board in iter_boards() if board.can_read(trust)]
    current_key = current_board.storage_key()
    for idx, board in enumerate(readable):
        if board.storage_key() == current_key:
            for candidate in readable[idx + 1 :]:
                return candidate
            break
    return None


def _format_note(note, number: int) -> str:
    sender = note.sender or ""
    subject = note.subject or ""
    to_field = note.to or ""
    date_str = time.ctime(note.timestamp)
    header = f"{{W[{number:4d}{{x] {{Y{sender}{{x: {{g{subject}{{x}}"
    date_line = f"{{YDate{{x:  {date_str}"
    to_line = f"{{YTo{{x:    {to_field}"
    separator = "{g==========================================================================={x"
    body = note.text or ""
    return "\n".join([header, date_line, to_line, separator, body])


def _read_next_unread_note(char: Character, pcdata: PCData, board, trust: int) -> str:
    last_read = _board_last_read(pcdata, board)
    for position, note in enumerate(board.notes, start=1):
        if not _is_note_visible_to(char, note):
            continue
        if note.timestamp > last_read:
            _set_last_read(pcdata, board, note.timestamp)
            return _format_note(note, position)

    message_lines = ["No new notes in this board."]
    next_board = _next_readable_board(board, trust)
    if next_board is not None:
        pcdata.board_name = next_board.storage_key()
        message_lines.append(f"Changed to next board, {next_board.name}.")
    else:
        message_lines.append("There are no more boards.")
    return "\n".join(message_lines)


def _ensure_draft(char: Character, board) -> NoteDraft:
    pcdata = _ensure_pcdata(char)
    draft = pcdata.in_progress
    board_key = board.storage_key()
    if draft is None or draft.board_key != board_key:
        draft = NoteDraft(
            sender=char.name or "someone",
            board_key=board_key,
            expire=board.default_expire(),
        )
        pcdata.in_progress = draft
    else:
        draft.sender = char.name or draft.sender
        if draft.expire is None:
            draft.expire = board.default_expire()
    return draft


def _recipient_message(board, final: str, added: bool, used_default: bool) -> str:
    if added and board.default_recipients:
        return f"Recipient list updated to {final or board.default_recipients} (forced {board.default_recipients})."
    if used_default and final:
        return f"Recipient list defaulted to {final}."
    if final:
        return f"Recipient list set to {final}."
    return "Recipient list cleared."


def do_board(char: Character, args: str) -> str:
    if char.is_npc:
        return "NPCs cannot use boards."

    pcdata = _ensure_pcdata(char)
    current_board = _resolve_current_board(char)
    trust = _get_trust(char)
    available = [(idx, board) for idx, board in enumerate(iter_boards(), start=1) if board.can_read(trust)]

    args = args.strip()
    if not args:
        lines = [
            "{RNum          Name Unread Description{x",
            "{R==== ============ ====== ============================={x",
        ]
        for idx, board in available:
            last_read = _board_last_read(pcdata, board)
            unread = board.unread_count(last_read)
            unread_color = "{G" if unread else "{g"
            lines.append(
                f"({{W{idx:2d}{{x) {{g{board.name:<12}{{x [{unread_color}{unread:4}{{x] {{y{board.description}{{x"
            )
        lines.append("")
        lines.append(f"You current board is {{W{current_board.name}{{x.")
        if not current_board.can_read(trust):
            lines.append("You cannot read nor write notes on this board.")
        elif trust < current_board.write_level:
            lines.append("You can only read notes from this board.")
        else:
            lines.append("You can both read and write on this board.")
        return "\n".join(lines)

    if pcdata.in_progress:
        return "Please finish your interrupted note first."

    if args.isdigit():
        number = int(args)
        if number < 1 or number > len(available):
            return "No such board."
        board = available[number - 1][1]
        pcdata.board_name = board.storage_key()
        return _board_change_message(board, trust)

    board = find_board(args)
    if board is None or not board.can_read(trust):
        return "No such board."
    pcdata.board_name = board.storage_key()
    return _board_change_message(board, trust)


def do_note(char: Character, args: str) -> str:
    if char.is_npc:
        return "NPCs cannot use boards."

    pcdata = _ensure_pcdata(char)
    board = _resolve_current_board(char)
    trust = _get_trust(char)

    if not board.can_read(trust):
        return "You cannot read notes on this board."

    args = args.strip()
    if not args:
        return _read_next_unread_note(char, pcdata, board, trust)

    subcmd, *rest = args.split(None, 1)
    subcmd = subcmd.lower()
    rest_str = rest[0] if rest else ""

    if subcmd == "post":
        if not board.can_write(trust):
            return "You cannot write on this board."
        if "|" not in rest_str:
            return "Usage: note post <subject>|<text>"
        subject, text = rest_str.split("|", 1)
        timestamp = time.time()
        try:
            note = board.post(
                char.name or "someone",
                subject.strip(),
                text.strip(),
                to=None,
                timestamp=timestamp,
                expire=board.default_expire(base_timestamp=timestamp),
            )
        except ValueError as exc:
            return str(exc)
        save_board(board)
        _set_last_read(pcdata, board, note.timestamp)
        return "Note posted."

    if subcmd == "list":
        show_count: int | None = None
        arg = rest_str.strip()
        if arg:
            try:
                parsed = int(arg)
            except ValueError:
                parsed = 0
            if parsed > 0:
                show_count = parsed
        last_read = _board_last_read(pcdata, board)
        visible_total = sum(1 for note in board.notes if _is_note_visible_to(char, note))
        if visible_total == 0:
            return "No notes."
        header = ["{WNotes on this board:{x", "{rNum> Author        Subject{x"]
        lines: list[str] = []
        shown_visible = 0
        for index, note in enumerate(board.notes, start=1):
            if not _is_note_visible_to(char, note):
                continue
            shown_visible += 1
            if show_count is not None and visible_total - show_count >= shown_visible:
                continue
            marker = "*" if note.timestamp > last_read else " "
            sender = (note.sender or "")[:13]
            subject = note.subject or ""
            formatted_sender = f"{sender:<13}"
            line = (
                "{W"
                + f"{index:3d}"
                + "{x>"
                + "{B"
                + marker
                + "{x"
                + "{Y"
                + formatted_sender
                + "{x"
                + "{y"
                + subject
                + "{x"
            )
            lines.append(line)
        if not lines:
            return "No notes."
        return "\n".join(header + lines)

    if subcmd == "read":
        if not rest_str.strip():
            return _read_next_unread_note(char, pcdata, board, trust)
        try:
            number = int(rest_str.strip())
        except ValueError:
            return "Read which note?"
        index = _find_visible_note_index(char, board, number)
        if index is None:
            return "No such note."
        note = board.notes[index]
        _set_last_read(pcdata, board, note.timestamp)
        return _format_note(note, index + 1)

    if subcmd == "write":
        if not board.can_write(trust):
            return "You cannot write on this board."
        draft = _ensure_draft(char, board)
        message = [
            ("You continue your note on the" if (draft.subject or draft.text) else "You begin writing a note on the")
        ]
        message.append(f" {board.name} board.")
        if board.force_type is BoardForceType.INCLUDE and board.default_recipients:
            message.append(f" The recipient list must include {board.default_recipients}.")
        elif board.force_type is BoardForceType.EXCLUDE and board.default_recipients:
            message.append(f" The recipient list must not include {board.default_recipients}.")
        elif board.default_recipients:
            message.append(f" Default recipient is {board.default_recipients}.")
        return "".join(message)

    if subcmd == "to":
        if not board.can_write(trust):
            return "You cannot write on this board."
        draft = _ensure_draft(char, board)
        try:
            final, added, used_default = board.resolve_recipients(rest_str)
        except ValueError as exc:
            return str(exc)
        draft.to = final
        return _recipient_message(board, final, added, used_default)

    if subcmd == "subject":
        if not board.can_write(trust):
            return "You cannot write on this board."
        subject = rest_str.strip()
        if not subject:
            return "What should the subject be?"
        draft = _ensure_draft(char, board)
        draft.subject = subject
        return f"Subject set to {subject}."

    if subcmd == "text":
        if not board.can_write(trust):
            return "You cannot write on this board."
        text = rest_str.rstrip()
        if not text:
            return "You need to write some text first."
        draft = _ensure_draft(char, board)
        draft.text = f"{draft.text}\n{text}".strip()
        return "Note text updated."

    if subcmd == "send":
        if not board.can_write(trust):
            return "You cannot write on this board."
        draft = pcdata.in_progress
        if draft is None or draft.board_key != board.storage_key():
            return "You have no note in progress."
        if not draft.subject:
            return "You need to set a subject first."
        if not draft.text:
            return "You need to write some text first."
        try:
            final, _, _ = board.resolve_recipients(draft.to)
        except ValueError as exc:
            return str(exc)
        draft.to = final
        timestamp = time.time()
        expire = draft.expire
        if expire is None:
            expire = board.default_expire(base_timestamp=timestamp)
        note = board.post(
            draft.sender or char.name or "someone",
            draft.subject,
            draft.text,
            to=final,
            timestamp=timestamp,
            expire=expire,
        )
        save_board(board)
        _set_last_read(pcdata, board, note.timestamp)
        pcdata.in_progress = None
        return "Note posted."

    if subcmd == "expire":
        if not board.can_write(trust):
            return "You cannot write on this board."
        if not char.is_immortal():
            return "Only immortals may set the expiration."
        draft = pcdata.in_progress
        if draft is None or draft.board_key != board.storage_key():
            return "You have no note in progress."
        now = time.time()
        arg = rest_str.strip()
        if arg:
            try:
                days = int(arg)
            except ValueError:
                return "Please provide the number of days."
            if days <= 0:
                return "Expiration must be a positive number of days."
            expire_at = now + days * 24 * 60 * 60
        else:
            expire_at = board.default_expire(base_timestamp=now)
        draft.expire = expire_at
        return f"This note will expire on {time.ctime(expire_at)}."

    if subcmd == "remove":
        if not rest_str.strip():
            return "Remove which note?"
        try:
            number = int(rest_str.strip())
        except ValueError:
            return "Remove which note?"
        index = _find_visible_note_index(char, board, number)
        if index is None:
            return "No such note."
        note = board.notes[index]
        sender = (note.sender or "").lower()
        actor = (char.name or "").lower()
        if sender != actor and trust < MAX_LEVEL:
            return "You are not authorized to remove this note."
        del board.notes[index]
        save_board(board)
        return "Note removed!"

    if subcmd == "catchup":
        if not board.notes:
            return "Alas, there are no notes in that board."
        last_note = board.notes[-1]
        _set_last_read(pcdata, board, last_note.timestamp)
        return "All mesages skipped."

    return "Huh?"
