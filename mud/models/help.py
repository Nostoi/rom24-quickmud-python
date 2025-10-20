from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .help_json import HelpJson


@dataclass(eq=False)
class HelpEntry:
    """Runtime representation of a help entry."""

    keywords: list[str]
    text: str
    level: int = 0

    @classmethod
    def from_json(cls, data: HelpJson) -> HelpEntry:
        return cls(**data.to_dict())


# placeholder registry to track loaded help entries
help_registry: Dict[str, List[HelpEntry]] = {}
help_entries: List[HelpEntry] = []


def clear_help_registry() -> None:
    """Remove all registered help entries."""

    help_registry.clear()
    help_entries.clear()


def register_help(entry: HelpEntry) -> None:
    """Register a help entry under each keyword, preserving load order."""

    if entry not in help_entries:
        help_entries.append(entry)

    for keyword in entry.keywords:
        key = keyword.lower()
        bucket = help_registry.setdefault(key, [])
        if entry not in bucket:
            bucket.append(entry)
