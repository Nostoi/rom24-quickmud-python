from __future__ import annotations

from dataclasses import dataclass

from .note_json import NoteJson


@dataclass
class Note:
    """Runtime representation of a message board note."""

    sender: str
    to: str
    subject: str
    text: str
    timestamp: float
    expire: float = 0.0

    def to_json(self) -> NoteJson:
        return NoteJson(
            sender=self.sender,
            to=self.to,
            subject=self.subject,
            text=self.text,
            timestamp=self.timestamp,
            expire=self.expire,
        )

    @classmethod
    def from_json(cls, data: NoteJson) -> Note:
        return cls(**data.to_dict())
