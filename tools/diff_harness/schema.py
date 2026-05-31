"""Canonical snapshot schema shared by the C-capture and Python-replay sides.

Identity is by stable key (character name; object vnum), never pointer/object-id.
Per-field list ordering policy:
  - inventory: ORDER-PRESERVED (ROM prepends on pickup; order is observable)
  - output:    ORDER-PRESERVED (message sequence is observable)
  - room.people, room.contents, char.affects, char.affect_flags: SORTED
    (ROM linked-list order is not behaviorally meaningful here)
Equipment keys are the wear-slot integer rendered as a string ("0".."18"),
language-neutral on both sides (ROM iWear / Python int(WearLocation)).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class CharSnap:
    key: str
    room: int | None
    position: str
    hp: int
    max_hp: int
    mana: int
    move: int
    level: int
    align: int
    gold: int
    fighting: str | None
    affects: list[str] = field(default_factory=list)
    affect_flags: list[str] = field(default_factory=list)
    inventory: list[int] = field(default_factory=list)
    equipment: dict[str, int] = field(default_factory=dict)
    eff_hitroll: int = 0
    eff_damroll: int = 0
    eff_ac: list[int] = field(default_factory=list)


@dataclass
class RoomSnap:
    vnum: int
    people: list[str] = field(default_factory=list)
    contents: list[int] = field(default_factory=list)


@dataclass
class StepSnap:
    step: int
    command: str
    chars: list[CharSnap] = field(default_factory=list)
    rooms: list[RoomSnap] = field(default_factory=list)
    output: list[str] = field(default_factory=list)


def step_to_dict(step: StepSnap) -> dict:
    return asdict(step)


def step_from_dict(data: dict) -> StepSnap:
    chars = [CharSnap(**c) for c in data.get("chars", [])]
    rooms = [RoomSnap(**r) for r in data.get("rooms", [])]
    return StepSnap(
        step=data["step"],
        command=data["command"],
        chars=chars,
        rooms=rooms,
        output=list(data.get("output", [])),
    )
