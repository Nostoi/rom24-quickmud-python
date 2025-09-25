from __future__ import annotations

import asyncio
from dataclasses import dataclass

from mud.models.character import Character


@dataclass
class Session:
    name: str
    character: Character
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter


SESSIONS: dict[str, Session] = {}


def get_online_players() -> list[Character]:
    return [sess.character for sess in SESSIONS.values()]
