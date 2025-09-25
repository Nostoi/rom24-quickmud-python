from __future__ import annotations

from dataclasses import dataclass, field

from .json_io import JsonDataclass


@dataclass
class AffectJson(JsonDataclass):
    """Per-object affect modifier."""

    location: str
    modifier: int


@dataclass
class ExtraDescriptionJson(JsonDataclass):
    """Extra description block for objects."""

    keyword: str
    description: str


@dataclass
class ObjectJson(JsonDataclass):
    """Object record matching ``schemas/object.schema.json``."""

    id: int
    name: str
    description: str
    item_type: str
    values: list[int]
    weight: int
    cost: int
    short_description: str | None = None
    flags: list[str] = field(default_factory=list)
    wear_flags: list[str] = field(default_factory=list)
    level: int = 0
    condition: int = 0
    material: str = ""
    affects: list[AffectJson] = field(default_factory=list)
    extra_descriptions: list[ExtraDescriptionJson] = field(default_factory=list)
