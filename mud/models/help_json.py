from __future__ import annotations

from dataclasses import dataclass

from .json_io import JsonDataclass


@dataclass
class HelpJson(JsonDataclass):
    """Help entry matching ``schemas/help.schema.json``."""

    keywords: list[str]
    text: str
    level: int = 0
