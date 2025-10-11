"""ROM clan table metadata for player death/communication flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from mud.models.constants import ROOM_VNUM_ALTAR


@dataclass(frozen=True)
class Clan:
    """Subset of ROM's ``clan_type`` structure (src/tables.c)."""

    name: str
    who_name: str
    hall_vnum: int
    is_independent: bool


CLAN_TABLE: Final[tuple[Clan, ...]] = (
    Clan("", "", ROOM_VNUM_ALTAR, True),
    Clan("loner", "[ Loner ] ", ROOM_VNUM_ALTAR, True),
    Clan("rom", "[  ROM  ] ", ROOM_VNUM_ALTAR, False),
)


def get_clan(clan_id: int) -> Clan:
    """Return clan metadata by id with clan 0 as the default fallback."""

    try:
        index = int(clan_id)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        index = 0
    if index < 0 or index >= len(CLAN_TABLE):
        index = 0
    return CLAN_TABLE[index]


def get_clan_hall_vnum(clan_id: int) -> int:
    """Return the hall vnum for *clan_id* falling back to the altar."""

    clan = get_clan(clan_id)
    hall = getattr(clan, "hall_vnum", ROOM_VNUM_ALTAR)
    try:
        return int(hall)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return ROOM_VNUM_ALTAR


def lookup_clan_id(name: str | int | None) -> int:
    """Return the clan id matching *name* mirroring ROM's ``clan_lookup``."""

    if name is None:
        return 0
    if isinstance(name, int):
        return name if 0 <= name < len(CLAN_TABLE) else 0
    text = str(name).strip()
    if not text:
        return 0
    try:
        numeric = int(text, 10)
    except ValueError:
        numeric = None
    else:
        if 0 <= numeric < len(CLAN_TABLE):
            return numeric
    lowered = text.lower()
    if lowered in {"none", "0"}:
        return 0
    for idx, clan in enumerate(CLAN_TABLE):
        if clan.name.lower() == lowered:
            return idx
    return 0


__all__ = [
    "Clan",
    "CLAN_TABLE",
    "get_clan",
    "get_clan_hall_vnum",
    "lookup_clan_id",
]
