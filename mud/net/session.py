from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mud.models.character import Character

if TYPE_CHECKING:
    from mud.net.connection import TelnetStream


@dataclass
class Session:
    name: str
    character: Character
    reader: asyncio.StreamReader
    connection: TelnetStream
    account_name: str = ""
    last_command: str = field(default="")
    repeat_count: int = field(default=0)
    editor: str | None = None
    editor_state: dict[str, object] = field(default_factory=dict)
    ansi_enabled: bool = True


SESSIONS: dict[str, Session] = {}


def get_online_players() -> list[Character]:
    return [sess.character for sess in SESSIONS.values()]
