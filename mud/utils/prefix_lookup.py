"""ROM-faithful prefix-match name lookup.

Mirrors ROM `str_prefix(short, full)` semantics (returns 0 when `short` is
a case-insensitive prefix of `full`) as used throughout `src/lookup.c` and
`src/bit.c:flag_lookup`.

Use this anywhere ROM accepts an abbreviation: flag names, race names,
class names, position/sex/size/item-type names, etc.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import IntFlag
from typing import TypeVar

T = TypeVar("T")


def prefix_lookup_index(name: str | None, candidates: Iterable[str]) -> int:
    """Return the index of the first candidate whose name is prefix-matched.

    Mirrors ROM `src/lookup.c` family (e.g. `race_lookup`, `position_lookup`).
    Case-insensitive; accepts ``name`` when it is a prefix of any candidate.
    Returns ``-1`` on no match — callers map that to whatever sentinel ROM
    returns for their specific table (-1, 0, NO_FLAG, etc.).
    """
    if not name:
        return -1
    needle = name.lower()
    for index, candidate in enumerate(candidates):
        if not candidate:
            continue
        if candidate.lower().startswith(needle):
            return index
    return -1


def prefix_lookup_intflag(name: str | None, flag_enum: type[IntFlag]) -> int | None:
    """Return the int bit value of the first IntFlag member prefix-matched.

    Mirrors ROM `flag_lookup(name, flag_table)` (src/bit.c). Returns ``None``
    on no match — callers map that to ROM's ``NO_FLAG`` semantics.

    Lookup order (ROM-faithful):

    1. The ROM ``src/tables.c`` table-name alias map for *flag_enum*
       (`rom_flag_aliases`). ROM table names like ``npc``/``healer``/
       ``can_loot``/``dirt_kick`` differ from Python member names
       (``IS_NPC``/``IS_HEALER``/``CANLOOT``/``KICK_DIRT``) but must
       prefix-match per ROM `flag_lookup`. Alias keys are lowercase.
    2. Fallback to Python member names (case-insensitive prefix-match).

    See TABLES-002 in `docs/parity/TABLES_C_AUDIT.md`.
    """
    if not name:
        return None
    needle = name.lower()

    # mirroring ROM src/tables.c — table NAMES are the ROM-canonical strings
    # `flag_lookup` matches against. Consult the alias map first so ROM names
    # win when they would otherwise be hidden by a non-prefix Python member name.
    aliases = rom_flag_aliases(flag_enum)
    for alias_name, member in aliases.items():
        if alias_name.startswith(needle):
            return int(member)

    for member in flag_enum.__members__.values():
        if member.name and member.name.lower().startswith(needle):
            return int(member)
    return None


# ROM `src/tables.c` table-name → Python IntFlag member aliases.
# Populated lazily on first call to `rom_flag_aliases` to avoid an import
# cycle with `mud.models.constants` at module-load time. See TABLES-002.
_ROM_FLAG_ALIAS_CACHE: dict[type[IntFlag], dict[str, IntFlag]] = {}


def rom_flag_aliases(flag_enum: type[IntFlag]) -> dict[str, IntFlag]:
    """Return the ROM table-name → IntFlag member alias map for *flag_enum*.

    Mirrors ROM `src/tables.c` flag-table names that don't directly
    prefix-match Python member names. Empty for IntFlags whose Python
    member names already match ROM table names.
    """
    cached = _ROM_FLAG_ALIAS_CACHE.get(flag_enum)
    if cached is not None:
        return cached

    from mud.models.constants import (
        ActFlag,
        CommFlag,
        OffFlag,
        PlayerFlag,
    )

    aliases: dict[type[IntFlag], dict[str, IntFlag]] = {
        # ROM src/tables.c:82-106 act_flags table.
        ActFlag: {
            "npc": ActFlag.IS_NPC,
            "healer": ActFlag.IS_HEALER,
            "changer": ActFlag.IS_CHANGER,
        },
        # ROM src/tables.c:108-128 plr_flags table.
        PlayerFlag: {
            "npc": PlayerFlag.IS_NPC,
            "can_loot": PlayerFlag.CANLOOT,
        },
        # ROM src/tables.c:163-186 off_flags table.
        OffFlag: {
            "dirt_kick": OffFlag.KICK_DIRT,
        },
        # ROM src/tables.c:271-296 comm_flags table —
        # ROM table name `noclangossip` for the auction-channel slot.
        CommFlag: {
            "noclangossip": CommFlag.NOAUCTION,
        },
    }
    result = aliases.get(flag_enum, {})
    _ROM_FLAG_ALIAS_CACHE[flag_enum] = result
    return result


def liq_lookup(name: str | None) -> int:
    """Return the int LIQUID_TABLE index whose name is prefix-matched by *name*.

    Mirrors ROM ``liq_lookup`` (src/lookup.c:138-150). Returns ``-1`` on miss.

    Note: ``mud/loaders/obj_loader.py:_liq_lookup`` is a separate, internal
    helper that returns ``0`` (water) on miss for object-loading defaults.
    Use this public ``liq_lookup`` for ROM-faithful semantics.
    """
    # mirroring ROM src/lookup.c:138-150 — liq_lookup uses str_prefix.
    from mud.models.constants import LIQUID_TABLE

    if not name:
        return -1
    needle = name.lower()
    for index, liquid in enumerate(LIQUID_TABLE):
        liq_name = getattr(liquid, "name", "") or ""
        if liq_name and liq_name.lower().startswith(needle):
            return index
    return -1


def item_lookup(name: str | None) -> int:
    """Return the int ItemType value whose name is prefix-matched by *name*.

    Mirrors ROM ``item_lookup`` (src/lookup.c:124-136): returns the
    ``item_table[].type`` value (the ITEM_X constant), NOT the index.
    Python's ``ItemType`` IntEnum values are equal to ROM ITEM_X constants
    so ``int(member)`` is correct. Returns ``-1`` on miss.
    """
    # mirroring ROM src/lookup.c:124-136 — item_lookup uses str_prefix.
    from mud.models.constants import ItemType

    if not name:
        return -1
    needle = name.lower()
    for member in ItemType.__members__.values():
        if member.name and member.name.lower().startswith(needle):
            return int(member)
    return -1


def size_lookup(name: str | None) -> int:
    """Return the int Size index whose name is prefix-matched by *name*.

    Mirrors ROM ``size_lookup`` (src/lookup.c:95-107). Returns ``-1`` on miss.
    """
    # mirroring ROM src/lookup.c:95-107 — size_lookup uses str_prefix.
    from mud.models.constants import Size

    if not name:
        return -1
    needle = name.lower()
    for member in Size.__members__.values():
        if member.name and member.name.lower().startswith(needle):
            return int(member)
    return -1


def sex_lookup(name: str | None) -> int:
    """Return the int Sex index whose name is prefix-matched by *name*.

    Mirrors ROM ``sex_lookup`` (src/lookup.c:81-93). Returns ``-1`` on miss.
    """
    # mirroring ROM src/lookup.c:81-93 — sex_lookup uses str_prefix.
    from mud.models.constants import Sex

    if not name:
        return -1
    needle = name.lower()
    for member in Sex.__members__.values():
        if member.name and member.name.lower().startswith(needle):
            return int(member)
    return -1


def position_lookup(name: str | None) -> int:
    """Return the int Position index whose name is prefix-matched by *name*.

    Mirrors ROM ``position_lookup`` (src/lookup.c:67-79):
    case-insensitive prefix-match against the position table. Returns ``-1``
    on no match (ROM fall-through).
    """
    # mirroring ROM src/lookup.c:67-79 — position_lookup uses str_prefix.
    from mud.models.constants import Position

    if not name:
        return -1
    needle = name.lower()
    for member in Position.__members__.values():
        if member.name and member.name.lower().startswith(needle):
            return int(member)
    return -1
