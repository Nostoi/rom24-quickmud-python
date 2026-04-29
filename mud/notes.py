from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from mud.models.board import Board, BoardForceType
from mud.models.board_json import BoardJson
from mud.models.constants import LEVEL_IMMORTAL, MAX_LEVEL
from mud.models.json_io import dump_dataclass, load_dataclass

if False:  # TYPE_CHECKING
    from mud.models.character import Character
    from mud.models.note import Note


_IMMORTAL_TOKENS = frozenset({"imm", "imms", "immortal", "immortals", "god", "gods"})
_IMPLEMENTOR_TOKENS = frozenset({"imp", "imps", "implementor", "implementors"})


def _split_recipient_tokens(value: str) -> set[str]:
    return {token.lower() for token in value.replace(",", " ").split() if token}


def is_note_to(char, note) -> bool:
    """Return True if ``note`` is addressed to ``char``.

    Mirrors ROM ``is_note_to`` at ``src/board.c:408-440``: the sender always
    sees their own notes; "all" / immortal / implementor tokens; an explicit
    name match against ``ch->name``; and a numeric ``to_list`` meaning
    "trust ≥ that number" (``src/board.c:436-437``).
    """

    name = (getattr(char, "name", None) or "").strip().lower()
    sender = (getattr(note, "sender", None) or "").strip().lower()
    if name and sender and name == sender:
        return True

    tokens = _split_recipient_tokens(getattr(note, "to", None) or "")
    if "all" in tokens:
        return True

    is_immortal_fn = getattr(char, "is_immortal", None)
    if callable(is_immortal_fn) and is_immortal_fn() and tokens & _IMMORTAL_TOKENS:
        return True

    trust = getattr(char, "trust", 0) or getattr(char, "level", 0) or 0
    if trust == MAX_LEVEL and tokens & _IMPLEMENTOR_TOKENS:
        return True

    if name and name in tokens:
        return True

    to_field = (getattr(note, "to", None) or "").strip()
    if to_field.isdigit() and trust >= int(to_field):
        return True

    return False

BOARDS_DIR = Path("data/boards")

DEFAULT_BOARD_NAME = "general"


# ROM hardcoded board table mirroring ``src/board.c:67-76``.
#   { short_name, description, read_level, write_level,
#     default_recipients, force_type, purge_days }
ROM_DEFAULT_BOARDS: tuple[tuple[str, str, int, int, str, BoardForceType, int], ...] = (
    ("General", "General discussion", 0, 2, "all", BoardForceType.INCLUDE, 21),
    ("Ideas", "Suggestion for improvement", 0, 2, "all", BoardForceType.NORMAL, 60),
    ("Announce", "Announcements from Immortals", 0, LEVEL_IMMORTAL, "all", BoardForceType.NORMAL, 60),
    ("Bugs", "Typos, bugs, errors", 0, 1, "imm", BoardForceType.NORMAL, 60),
    ("Personal", "Personal messages", 0, 1, "all", BoardForceType.EXCLUDE, 28),
)


def _normalize_board_name(name: str) -> str:
    return name.strip().lower()


board_registry: dict[str, Board] = {}

# ROM ``last_note_stamp`` global (``src/board.c:81``). Tracks the most recently
# assigned ``date_stamp`` so two notes posted in the same wall-clock second
# still get distinct, monotonically increasing timestamps. ``finish_note``
# (``src/board.c:154-160``) consults / increments this.
_last_note_stamp: float = 0.0


def next_note_stamp(base: float) -> float:
    """Return a unique note timestamp ≥ ``base``.

    Mirrors ROM ``finish_note`` at ``src/board.c:154-160``:

        if (last_note_stamp >= current_time)
            note->date_stamp = ++last_note_stamp;
        else {
            note->date_stamp = current_time;
            last_note_stamp = current_time;
        }
    """

    global _last_note_stamp
    if _last_note_stamp >= base:
        _last_note_stamp += 1
    else:
        _last_note_stamp = base
    return _last_note_stamp


def _seed_default_boards() -> None:
    """Seed the ROM hardcoded board table from ``src/board.c:67-76``.

    Existing entries (e.g. boards already loaded from JSON) keep their notes
    but get their static metadata reset to ROM defaults so config drift on
    disk cannot lower a board's read/write level below what ROM ships.
    """

    for name, description, read_level, write_level, recipients, force_type, purge_days in ROM_DEFAULT_BOARDS:
        key = _normalize_board_name(name)
        existing = board_registry.get(key)
        if existing is None:
            board_registry[key] = Board(
                name=name,
                description=description,
                read_level=read_level,
                write_level=write_level,
                default_recipients=recipients,
                force_type=force_type,
                purge_days=purge_days,
            )
        else:
            existing.name = name
            existing.description = description
            existing.read_level = read_level
            existing.write_level = write_level
            existing.default_recipients = recipients
            existing.force_type = force_type
            existing.purge_days = purge_days


def _archive_expired_notes(board: Board, now: float) -> int:
    """Move notes whose ``expire`` is in the past into ``<board>.old.json``.

    Mirrors ROM ``load_board`` archive sweep at ``src/board.c:365-383``: any
    note whose ``expire < current_time`` is appended to ``<short_name>.old``
    and dropped from the active board. We use a parallel ``.old.json`` file
    so the archive is readable with the same JSON schema as live boards.

    Returns the number of notes archived.
    """

    if not board.notes:
        return 0

    expired: list = []
    keep: list = []
    for note in board.notes:
        if note.expire and note.expire < now:
            expired.append(note)
        else:
            keep.append(note)

    if not expired:
        return 0

    board.notes = keep

    BOARDS_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = BOARDS_DIR / f"{board.storage_key()}.old.json"
    archive: Board
    if archive_path.exists():
        with archive_path.open() as f:
            archive_data = load_dataclass(BoardJson, f)
        archive = Board.from_json(archive_data)
    else:
        archive = Board(name=f"{board.name}.old", description=board.description)

    archive.notes.extend(expired)

    tmp = archive_path.with_suffix(".tmp")
    with tmp.open("w") as f:
        dump_dataclass(archive.to_json(), f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, archive_path)

    return len(expired)


def load_boards() -> None:
    """Load all boards from ``BOARDS_DIR`` into ``board_registry``.

    Mirrors ROM ``load_boards`` (``src/board.c:399-405``) which iterates the
    hardcoded ``boards[MAX_BOARD]`` table and calls ``load_board`` on each
    entry. We seed those five defaults first, then overlay any persisted
    notes from JSON, then sweep expired notes into ``<board>.old.json``
    (ROM ``load_board`` archive at ``src/board.c:365-383``).
    """

    import time

    board_registry.clear()
    _seed_default_boards()
    if not BOARDS_DIR.exists():
        return
    for path in sorted(BOARDS_DIR.glob("*.json")):
        if path.name.endswith(".old.json"):
            continue
        with path.open() as f:
            data = load_dataclass(BoardJson, f)
        board = Board.from_json(data)
        key = board.storage_key()
        existing = board_registry.get(key)
        if existing is not None:
            # Preserve ROM static metadata (levels, force_type, purge_days)
            # but adopt persisted notes. JSON is authoritative for content.
            existing.notes = board.notes
        else:
            board_registry[key] = board

    now = time.time()
    for board in board_registry.values():
        archived = _archive_expired_notes(board, now)
        if archived:
            save_board(board)


def save_board(board: Board) -> None:
    """Persist ``board`` to ``BOARDS_DIR`` atomically."""
    BOARDS_DIR.mkdir(parents=True, exist_ok=True)
    path = BOARDS_DIR / f"{board.storage_key()}.json"
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        dump_dataclass(board.to_json(), f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def get_board(
    name: str,
    description: str | None = None,
    *,
    read_level: int | None = None,
    write_level: int | None = None,
    default_recipients: str | None = None,
    force_type: int | BoardForceType | None = None,
    purge_days: int | None = None,
) -> Board:
    """Fetch a board by name, creating it if necessary."""

    key = _normalize_board_name(name)
    board = board_registry.get(key)
    if not board:
        board = Board(
            name=name,
            description=description or name.title(),
            read_level=read_level or 0,
            write_level=write_level or 0,
            default_recipients=default_recipients or "",
            force_type=BoardForceType(force_type) if force_type is not None else BoardForceType.NORMAL,
            purge_days=purge_days or 0,
        )
        board_registry[key] = board
    else:
        if description is not None:
            board.description = description
        if read_level is not None:
            board.read_level = read_level
        if write_level is not None:
            board.write_level = write_level
        if default_recipients is not None:
            board.default_recipients = default_recipients
        if force_type is not None:
            board.force_type = BoardForceType(force_type)
        if purge_days is not None:
            board.purge_days = purge_days
    return board


def find_board(name: str) -> Board | None:
    """Return the board registered under ``name`` (case-insensitive)."""

    return board_registry.get(_normalize_board_name(name))


def iter_boards() -> Iterable[Board]:
    """Iterate over registered boards in insertion/file order."""

    return board_registry.values()
