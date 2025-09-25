from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from mud.models.board import Board, BoardForceType
from mud.models.board_json import BoardJson
from mud.models.json_io import dump_dataclass, load_dataclass

BOARDS_DIR = Path("data/boards")

DEFAULT_BOARD_NAME = "general"


def _normalize_board_name(name: str) -> str:
    return name.strip().lower()


board_registry: dict[str, Board] = {}


def load_boards() -> None:
    """Load all boards from ``BOARDS_DIR`` into ``board_registry``."""
    board_registry.clear()
    if not BOARDS_DIR.exists():
        return
    for path in sorted(BOARDS_DIR.glob("*.json")):
        with path.open() as f:
            data = load_dataclass(BoardJson, f)
        board = Board.from_json(data)
        board_registry[board.storage_key()] = board


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
