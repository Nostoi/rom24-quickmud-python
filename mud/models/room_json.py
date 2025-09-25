from __future__ import annotations

from dataclasses import dataclass, field

from .json_io import JsonDataclass


@dataclass
class ExitJson(JsonDataclass):
    """Exit specification for JSON rooms."""

    to_room: int
    description: str | None = None
    keyword: str | None = None
    flags: list[str] = field(default_factory=list)


@dataclass
class ExtraDescriptionJson(JsonDataclass):
    """Extra description block for JSON rooms."""

    keyword: str
    description: str


@dataclass
class ResetJson(JsonDataclass):
    """Reset command affecting a room."""

    command: str
    arg1: int | None = None
    arg2: int | None = None
    arg3: int | None = None
    arg4: int | None = None


@dataclass
class RoomJson(JsonDataclass):
    """Room record matching ``schemas/room.schema.json``."""

    id: int
    name: str
    description: str
    sector_type: str
    area: int
    flags: list[str] = field(default_factory=list)
    exits: dict[str, ExitJson] = field(default_factory=dict)
    extra_descriptions: list[ExtraDescriptionJson] = field(default_factory=list)
    resets: list[ResetJson] = field(default_factory=list)
