from __future__ import annotations

from pathlib import Path
from typing import Dict
import os

from mud.models.board import Board
from mud.models.board_json import BoardJson
from mud.models.json_io import load_dataclass, dump_dataclass

BOARDS_DIR = Path("data/boards")

board_registry: Dict[str, Board] = {}


def load_boards() -> None:
    """Load all boards from ``BOARDS_DIR`` into ``board_registry``."""
    board_registry.clear()
    if not BOARDS_DIR.exists():
        return
    for path in BOARDS_DIR.glob("*.json"):
        with path.open() as f:
            data = load_dataclass(BoardJson, f)
        board_registry[data.name] = Board.from_json(data)


def save_board(board: Board) -> None:
    """Persist ``board`` to ``BOARDS_DIR`` atomically."""
    BOARDS_DIR.mkdir(parents=True, exist_ok=True)
    path = BOARDS_DIR / f"{board.name}.json"
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        dump_dataclass(board.to_json(), f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def get_board(name: str, description: str | None = None) -> Board:
    """Fetch a board by name, creating it if necessary."""
    board = board_registry.get(name)
    if not board:
        board = Board(name=name, description=description or name.title())
        board_registry[name] = board
    return board
