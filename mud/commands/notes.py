from __future__ import annotations

from mud.models.board import BoardForceType, NoteDraft
from mud.models.character import Character, PCData
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


def _ensure_draft(char: Character, board) -> NoteDraft:
    pcdata = _ensure_pcdata(char)
    draft = pcdata.in_progress
    board_key = board.storage_key()
    if draft is None or draft.board_key != board_key:
        draft = NoteDraft(sender=char.name or "someone", board_key=board_key)
        pcdata.in_progress = draft
    else:
        draft.sender = char.name or draft.sender
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
            "Num  Name         Unread Description",
            "==== ============ ====== =============================",
        ]
        for idx, board in available:
            last_read = _board_last_read(pcdata, board)
            unread = board.unread_count(last_read)
            lines.append(f"({idx:2d}) {board.name:<12} [{unread:>3}] {board.description}")
        lines.append("")
        lines.append(f"Current board: {current_board.name}.")
        if not current_board.can_read(trust):
            lines.append("You cannot read or write on this board.")
        elif trust < current_board.write_level:
            lines.append("You can only read on this board.")
        else:
            lines.append("You can read and write on this board.")
        return "\n".join(lines)

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

    if not args:
        return "Note what?"

    pcdata = _ensure_pcdata(char)
    board = _resolve_current_board(char)
    trust = _get_trust(char)

    if not board.can_read(trust):
        return "You cannot read notes on this board."

    subcmd, *rest = args.split(None, 1)
    rest_str = rest[0] if rest else ""

    if subcmd == "post":
        if not board.can_write(trust):
            return "You cannot write on this board."
        if "|" not in rest_str:
            return "Usage: note post <subject>|<text>"
        subject, text = rest_str.split("|", 1)
        note = board.post(
            char.name or "someone",
            subject.strip(),
            text.strip(),
            to=None,
        )
        save_board(board)
        _set_last_read(pcdata, board, note.timestamp)
        return "Note posted."

    if subcmd == "list":
        if not board.notes:
            return "No notes."
        last_read = _board_last_read(pcdata, board)
        lines = []
        for i, note in enumerate(board.notes, start=1):
            marker = "*" if note.timestamp > last_read else " "
            lines.append(f"{i:2d}{marker}: {note.subject} ({note.sender})")
        return "\n".join(lines)

    if subcmd == "read":
        try:
            index = int(rest_str.strip()) - 1
        except ValueError:
            return "Read which note?"
        if index < 0 or index >= len(board.notes):
            return "No such note."
        note = board.notes[index]
        _set_last_read(pcdata, board, note.timestamp)
        return f"{note.subject}\n{note.text}"

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
        note = board.post(
            draft.sender or char.name or "someone",
            draft.subject,
            draft.text,
            to=final,
        )
        save_board(board)
        _set_last_read(pcdata, board, note.timestamp)
        pcdata.in_progress = None
        return "Note posted."

    if subcmd == "remove":
        if not rest_str.strip():
            return "Remove which note?"
        try:
            index = int(rest_str.strip()) - 1
        except ValueError:
            return "Remove which note?"
        if index < 0 or index >= len(board.notes):
            return "No such note."
        note = board.notes[index]
        sender = (note.sender or "").lower()
        actor = (char.name or "").lower()
        if not char.is_immortal() and sender != actor:
            return "You are not the author of that note."
        del board.notes[index]
        save_board(board)
        return "Note removed."

    if subcmd == "catchup":
        if not board.notes:
            return "Alas, there are no notes in that board."
        last_note = board.notes[-1]
        _set_last_read(pcdata, board, last_note.timestamp)
        return "All messages skipped."

    return "Huh?"
