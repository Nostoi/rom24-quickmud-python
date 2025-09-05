from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
import time

from .board_json import BoardJson
from .note import Note


@dataclass
class Board:
    """Runtime representation of a message board."""

    name: str
    description: str
    notes: List[Note] = field(default_factory=list)

    def post(
        self,
        sender: str,
        subject: str,
        text: str,
        to: str = "all",
    ) -> Note:
        note = Note(
            sender=sender,
            to=to,
            subject=subject,
            text=text,
            timestamp=time.time(),
        )
        self.notes.append(note)
        return note

    def to_json(self) -> BoardJson:
        return BoardJson(
            name=self.name,
            description=self.description,
            notes=[n.to_json() for n in self.notes],
        )

    @classmethod
    def from_json(cls, data: BoardJson) -> "Board":
        return cls(
            name=data.name,
            description=data.description,
            notes=[Note.from_json(n) for n in data.notes],
        )
