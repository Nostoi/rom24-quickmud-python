from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum

from .board_json import BoardJson
from .note import Note


class BoardForceType(IntEnum):
    """Recipient enforcement modes mirrored from ROM's board_data."""

    NORMAL = 0
    INCLUDE = 1
    EXCLUDE = 2


@dataclass
class NoteDraft:
    """Temporary staging record for in-progress note composition."""

    sender: str
    board_key: str
    to: str = ""
    subject: str = ""
    text: str = ""
    expire: float | None = None


@dataclass
class Board:
    """Runtime representation of a message board."""

    name: str
    description: str
    read_level: int = 0
    write_level: int = 0
    default_recipients: str = ""
    force_type: BoardForceType = BoardForceType.NORMAL
    purge_days: int = 0
    notes: list[Note] = field(default_factory=list)

    @staticmethod
    def _split_recipients(value: str) -> list[str]:
        return [token for token in value.replace(",", " ").split() if token]

    def resolve_recipients(self, recipients: str | None) -> tuple[str, bool, bool]:
        """Apply board-level recipient defaults and force rules."""

        tokens = self._split_recipients(recipients or "")
        required = self._split_recipients(self.default_recipients or "")
        added_required = False
        used_default = False

        if self.force_type is BoardForceType.NORMAL:
            if not tokens and required:
                tokens = required.copy()
                used_default = True
        elif self.force_type is BoardForceType.INCLUDE:
            lower = {token.lower() for token in tokens}
            if not tokens and required:
                tokens = required.copy()
                lower = {token.lower() for token in tokens}
                used_default = True
                added_required = True
            for req in required:
                if req.lower() not in lower:
                    tokens.append(req)
                    lower.add(req.lower())
                    added_required = True
        elif self.force_type is BoardForceType.EXCLUDE:
            if not tokens:
                raise ValueError("You must specify a recipient on this board.")
            lower = {token.lower() for token in tokens}
            for req in required:
                if req.lower() in lower:
                    raise ValueError(f"You are not allowed to send notes to {self.default_recipients} on this board.")

        final = " ".join(tokens).strip()
        return final, added_required, used_default

    def default_expire(self, *, base_timestamp: float | None = None) -> float:
        base = base_timestamp if base_timestamp is not None else time.time()
        if self.purge_days <= 0:
            return base
        return base + self.purge_days * 24 * 60 * 60

    def post(
        self,
        sender: str,
        subject: str,
        text: str,
        to: str | None = None,
        *,
        timestamp: float | None = None,
        expire: float | None = None,
    ) -> Note:
        resolved_to, _, _ = self.resolve_recipients(to)
        if not resolved_to:
            resolved_to = (self.default_recipients or "all").strip() or "all"
        actual_timestamp = time.time() if timestamp is None else timestamp
        note = Note(
            sender=sender,
            to=resolved_to,
            subject=subject,
            text=text,
            timestamp=actual_timestamp,
            expire=self.default_expire(base_timestamp=actual_timestamp)
            if expire is None
            else expire,
        )
        self.notes.append(note)
        return note

    def storage_key(self) -> str:
        """Return a normalized key for persistence and lookups."""

        return self.name.strip().lower()

    def unread_count(self, last_read: float | None) -> int:
        """Return the number of notes posted after ``last_read``."""

        cutoff = last_read or 0.0
        return sum(1 for note in self.notes if note.timestamp > cutoff)

    def can_read(self, trust: int) -> bool:
        return trust >= self.read_level

    def can_write(self, trust: int) -> bool:
        return trust >= self.write_level

    def to_json(self) -> BoardJson:
        return BoardJson(
            name=self.name,
            description=self.description,
            read_level=self.read_level,
            write_level=self.write_level,
            default_recipients=self.default_recipients,
            force_type=int(self.force_type),
            purge_days=self.purge_days,
            notes=[n.to_json() for n in self.notes],
        )

    @classmethod
    def from_json(cls, data: BoardJson) -> Board:
        return cls(
            name=data.name,
            description=data.description,
            read_level=getattr(data, "read_level", 0),
            write_level=getattr(data, "write_level", 0),
            default_recipients=getattr(data, "default_recipients", ""),
            force_type=BoardForceType(getattr(data, "force_type", 0)),
            purge_days=getattr(data, "purge_days", 0),
            notes=[Note.from_json(n) for n in data.notes],
        )
