from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HelpJson:
    """Help entry matching ``schemas/help.schema.json``."""

    keywords: list[str]
    text: str
    level: int = 0
