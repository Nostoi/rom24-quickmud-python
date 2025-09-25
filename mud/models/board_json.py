from __future__ import annotations

from dataclasses import dataclass, field

from .json_io import JsonDataclass
from .note_json import NoteJson


@dataclass
class BoardJson(JsonDataclass):
    """Schema-aligned representation of a message board."""

    name: str
    description: str
    read_level: int = 0
    write_level: int = 0
    default_recipients: str = ""
    force_type: int = 0
    purge_days: int = 0
    notes: list[NoteJson] = field(default_factory=list)
