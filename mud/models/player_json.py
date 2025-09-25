from __future__ import annotations

from dataclasses import dataclass, field

from .json_io import JsonDataclass


@dataclass
class PlayerJson(JsonDataclass):
    """Player record matching ``schemas/player.schema.json``."""

    name: str
    level: int
    race: int
    ch_class: int
    sex: int
    trust: int
    security: int
    hit: int
    max_hit: int
    mana: int
    max_mana: int
    move: int
    max_move: int
    perm_hit: int
    perm_mana: int
    perm_move: int
    gold: int
    silver: int
    exp: int
    practice: int
    train: int
    saving_throw: int
    alignment: int
    hitroll: int
    damroll: int
    wimpy: int
    points: int
    true_sex: int
    last_level: int
    position: int
    room_vnum: int | None = None
    conditions: list[int] = field(default_factory=lambda: [0, 48, 48, 48])
    armor: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    perm_stat: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    mod_stat: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    inventory: list[int] = field(default_factory=list)
    equipment: dict[str, int] = field(default_factory=dict)
    plr_flags: int = 0
    affected_by: int = 0
    comm_flags: int = 0
    wiznet: int = 0
