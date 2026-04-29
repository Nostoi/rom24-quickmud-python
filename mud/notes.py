from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from mud.models.board import Board, BoardForceType
from mud.models.board_json import BoardJson
from mud.models.constants import LEVEL_IMMORTAL
from mud.models.json_io import dump_dataclass, load_dataclass

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


def load_boards() -> None:
    """Load all boards from ``BOARDS_DIR`` into ``board_registry``.

    Mirrors ROM ``load_boards`` (``src/board.c:399-405``) which iterates the
    hardcoded ``boards[MAX_BOARD]`` table and calls ``load_board`` on each
    entry. We seed those five defaults first, then overlay any persisted
    notes from JSON.
    """

    board_registry.clear()
    _seed_default_boards()
    if not BOARDS_DIR.exists():
        return
    for path in sorted(BOARDS_DIR.glob("*.json")):
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
