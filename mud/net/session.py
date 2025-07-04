from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import asyncio

from mud.models.character import Character


@dataclass
class Session:
    name: str
    character: Character
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter


SESSIONS: Dict[str, Session] = {}
