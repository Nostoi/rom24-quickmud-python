from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

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
    values: List[int]
    weight: int
    cost: int
    short_description: Optional[str] = None
    flags: List[str] = field(default_factory=list)
    wear_flags: List[str] = field(default_factory=list)
    level: int = 0
    condition: int = 0
    material: str = ""
    affects: List[AffectJson] = field(default_factory=list)
    extra_descriptions: List[ExtraDescriptionJson] = field(default_factory=list)
