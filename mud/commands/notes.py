from mud.models.character import Character
from mud.notes import board_registry, get_board, save_board


def do_board(char: Character, args: str) -> str:
    if not args:
        if not board_registry:
            return "No boards."
        return "Boards: " + ", ".join(sorted(board_registry))
    return "Huh?"


def do_note(char: Character, args: str) -> str:
    if not args:
        return "Note what?"
    subcmd, *rest = args.split(None, 1)
    rest_str = rest[0] if rest else ""
    board = get_board("general")
    if subcmd == "post":
        if "|" not in rest_str:
            return "Usage: note post <subject>|<text>"
        subject, text = rest_str.split("|", 1)
        board.post(char.name or "someone", subject.strip(), text.strip())
        save_board(board)
        return "Note posted."
    elif subcmd == "list":
        if not board.notes:
            return "No notes."
        lines = [
            f"{i+1}: {note.subject} ({note.sender})"
            for i, note in enumerate(board.notes)
        ]
        return "\n".join(lines)
    elif subcmd == "read":
        try:
            index = int(rest_str.strip()) - 1
        except ValueError:
            return "Read which note?"
        if index < 0 or index >= len(board.notes):
            return "No such note."
        note = board.notes[index]
        return f"{note.subject}\n{note.text}"
    else:
        return "Huh?"
