"""Scenario loader — the single source both capture and replay read."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Scenario:
    name: str
    seed: int
    start_room: int
    char_name: str
    char_level: int
    watch_chars: list[str]
    watch_rooms: list[int]
    steps: list[str]


def load_scenario(path: str | Path) -> Scenario:
    data = json.loads(Path(path).read_text())
    char = data["char"]
    watch = data["watch"]
    return Scenario(
        name=data["name"],
        seed=int(data["seed"]),
        start_room=int(data["start_room"]),
        char_name=char["name"],
        char_level=int(char.get("level", 1)),
        watch_chars=list(watch["chars"]),
        watch_rooms=[int(v) for v in watch["rooms"]],
        steps=list(data["steps"]),
    )
