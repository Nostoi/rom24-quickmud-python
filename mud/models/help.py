from __future__ import annotations

from dataclasses import dataclass

from .help_json import HelpJson


@dataclass
class HelpEntry:
    """Runtime representation of a help entry."""

    keywords: list[str]
    text: str
    level: int = 0

    @classmethod
    def from_json(cls, data: HelpJson) -> "HelpEntry":
        return cls(**data.to_dict())
