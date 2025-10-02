from __future__ import annotations

from dataclasses import dataclass

from .json_io import JsonDataclass


@dataclass
class NoteJson(JsonDataclass):
    """Schema-aligned representation of a message board note."""

    sender: str
    to: str
    subject: str
    text: str
    timestamp: float
    expire: float = 0.0
