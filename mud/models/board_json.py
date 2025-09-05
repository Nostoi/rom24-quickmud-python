from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .json_io import JsonDataclass
from .note_json import NoteJson


@dataclass
class BoardJson(JsonDataclass):
    """Schema-aligned representation of a message board."""

    name: str
    description: str
    notes: List[NoteJson] = field(default_factory=list)
