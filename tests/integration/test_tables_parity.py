"""ROM ``src/tables.c`` parity reproducers.

These tests pin down ROM-correct expectations for the data tables in
``src/tables.c``. Where Python diverges from ROM, the test is marked
``xfail`` with the gap ID so closure flips it to xpass.

See ``docs/parity/TABLES_C_AUDIT.md`` for the gap catalogue.
"""

from __future__ import annotations

import pytest

from mud.models.constants import (
    ActFlag,
    AffectFlag,
    CommFlag,
    OffFlag,
    PlayerFlag,
    convert_flags_from_letters,
)

# ---------------------------------------------------------------------------
# Value-equivalence spot-checks — these PASS today.
# ---------------------------------------------------------------------------


def test_act_flag_letters_match_rom() -> None:
    """ROM ``src/tables.c:82-106`` letters A..dd map 1:1 to ``ActFlag`` bits."""
    assert int(ActFlag.IS_NPC) == 1 << 0  # A=npc
    assert int(ActFlag.AGGRESSIVE) == 1 << 5  # F=aggressive
    assert int(ActFlag.IS_HEALER) == 1 << 26  # aa=healer
    assert int(ActFlag.IS_CHANGER) == 1 << 29  # dd=changer


def test_player_flag_letters_match_rom() -> None:
    """ROM ``src/tables.c:108-128`` letters A..aa map 1:1 to ``PlayerFlag`` bits."""
    assert int(PlayerFlag.IS_NPC) == 1 << 0  # A=npc
    assert int(PlayerFlag.HOLYLIGHT) == 1 << 13  # N=holylight
    assert int(PlayerFlag.CANLOOT) == 1 << 15  # P=can_loot
    assert int(PlayerFlag.KILLER) == 1 << 26  # aa=killer


def test_off_flag_letters_match_rom() -> None:
    """ROM ``src/tables.c:163-186`` letters A..U map 1:1 to ``OffFlag`` bits."""
    assert int(OffFlag.AREA_ATTACK) == 1 << 0  # A=area_attack
    assert int(OffFlag.KICK_DIRT) == 1 << 9  # J=dirt_kick
    assert int(OffFlag.ASSIST_VNUM) == 1 << 20  # U=assist_vnum


def test_comm_flag_letters_match_rom() -> None:
    """ROM ``src/tables.c:271-296`` ``CommFlag`` bit positions match ``COMM_*``."""
    assert int(CommFlag.QUIET) == 1 << 0
    assert int(CommFlag.AFK) == 1 << 25


# ---------------------------------------------------------------------------
# TABLES-001 — AffectFlag bit positions diverge from ROM merc.h.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TABLES-003 — programmatic merc.h letter-macro vs Python IntFlag verification.
# ---------------------------------------------------------------------------


def _parse_merc_letter_macros() -> dict[str, int]:
    """Parse ``src/merc.h`` for ``#define NAME (X)`` letter-mapped macros.

    Returns a dict mapping macro name (e.g. ``ACT_AGGRESSIVE``) to its
    expected bit value. Letters A..Z map to ``1<<0..1<<25``; lowercase
    pairs (aa..dd) map to ``1<<26..1<<29``.
    """
    import pathlib
    import re

    text = pathlib.Path("src/merc.h").read_text()
    out: dict[str, int] = {}
    for match in re.finditer(r"#define\s+(\w+)\s+\(([A-Za-z]{1,2})\)", text):
        name, token = match.group(1), match.group(2)
        if len(token) == 1 and "A" <= token <= "Z":
            out[name] = 1 << (ord(token) - ord("A"))
        elif len(token) == 2 and token[0] == token[1] and "a" <= token[0] <= "z":
            out[name] = 1 << (26 + ord(token[0]) - ord("a"))
    return out


# Maps merc.h macro prefix → (Python IntFlag class, set of macro suffixes that
# map to specific Python member names — required when Python renamed a member
# but kept the bit position).
_PREFIX_TO_ENUM: dict[str, tuple[type, dict[str, str]]] = {}


def _build_prefix_map() -> dict[str, tuple[type, dict[str, str]]]:
    if _PREFIX_TO_ENUM:
        return _PREFIX_TO_ENUM
    from mud.models.constants import (
        ActFlag,
        CommFlag,
        FormFlag,
        FurnitureFlag,
        ImmFlag,
        OffFlag,
        PartFlag,
        PlayerFlag,
        PortalFlag,
        ResFlag,
        RoomFlag,
        VulnFlag,
        WeaponFlag,
    )

    # Member-rename overrides where Python member name differs from the
    # merc.h macro suffix. Format: {macro_suffix: python_member_name}.
    from mud.models.constants import AffectFlag

    _PREFIX_TO_ENUM.update(
        {
            "ACT": (ActFlag, {"AGGRESSIVE": "AGGRESSIVE"}),
            "AFF": (AffectFlag, {}),
            "PLR": (PlayerFlag, {}),
            "OFF": (OffFlag, {"KICK_DIRT": "KICK_DIRT", "DIRT_KICK": "KICK_DIRT"}),
            "IMM": (ImmFlag, {}),
            "RES": (ResFlag, {}),
            "VULN": (VulnFlag, {}),
            "FORM": (FormFlag, {}),
            "PART": (PartFlag, {"EAR": "EARS", "EYE": "EYES"}),
            "COMM": (CommFlag, {"NOAUCTION": "NOAUCTION"}),
            "ROOM": (RoomFlag, {}),
            "GATE": (PortalFlag, {}),
            "FURN": (FurnitureFlag, {}),
            "WEAPON": (WeaponFlag, {}),
        }
    )
    return _PREFIX_TO_ENUM


def _expected_python_member(prefix: str, suffix: str, enum_cls):
    """Return the Python IntFlag member that corresponds to ``<prefix>_<suffix>``."""
    overrides = _build_prefix_map()[prefix][1]
    candidate_name = overrides.get(suffix, suffix)
    members = enum_cls.__members__
    if candidate_name in members:
        return members[candidate_name]
    # Common rename pattern: ROM `NPC` → Python `IS_NPC`, `HEALER` → `IS_HEALER`.
    if f"IS_{suffix}" in members:
        return members[f"IS_{suffix}"]
    if f"ROOM_{suffix}" in members:
        return members[f"ROOM_{suffix}"]
    return None


def test_merc_h_letter_macros_match_python_intflag_values() -> None:
    """Cross-check every merc.h ``#define X (letter)`` against Python IntFlag bits.

    For every ``ACT_*`` / ``PLR_*`` / ``OFF_*`` / ``IMM_*`` / ``RES_*`` /
    ``VULN_*`` / ``FORM_*`` / ``PART_*`` / ``COMM_*`` / ``ROOM_*`` /
    ``GATE_*`` / ``FURN_*`` / ``WEAPON_*`` macro defined in ``src/merc.h``,
    assert the Python IntFlag member named (with prefix stripped) has the
    matching bit value.

    Excludes ``AFF_*`` — covered separately by TABLES-001 reproducer below.
    """
    macros = _parse_merc_letter_macros()
    prefix_map = _build_prefix_map()

    mismatches: list[str] = []
    checked = 0
    for macro_name, expected_bit in sorted(macros.items()):
        prefix, sep, suffix = macro_name.partition("_")
        if not sep:
            continue
        if prefix not in prefix_map:
            continue
        enum_cls, _overrides = prefix_map[prefix]
        member = _expected_python_member(prefix, suffix, enum_cls)
        if member is None:
            # Some merc.h macros (e.g. unused slots) have no Python equivalent.
            continue
        checked += 1
        if int(member) != expected_bit:
            mismatches.append(
                f"  {macro_name} = {expected_bit:#x} (bit {expected_bit.bit_length()-1}) "
                f"but {enum_cls.__name__}.{member.name} = {int(member):#x} "
                f"(bit {int(member).bit_length()-1})"
            )

    assert not mismatches, "merc.h letter-macro / Python IntFlag value drift:\n" + "\n".join(mismatches)
    assert checked >= 150, f"sanity: expected ~200+ macros checked, only {checked}"


# ---------------------------------------------------------------------------
# TABLES-001 — AffectFlag bit positions diverge from ROM merc.h.
# ---------------------------------------------------------------------------


def test_affect_flag_letters_match_rom_merc_h() -> None:
    """ROM ``src/merc.h:953-982`` letter-to-bit mapping for ``AFF_*``.

    Reproducer for TABLES-001. Decodes ROM letters via
    ``convert_flags_from_letters`` (which uses the ROM-correct A→0, G→6
    mapping) and asserts the resulting bits agree with the Python
    ``AffectFlag`` symbol that ROM names for that letter.
    """
    decoded_g = int(convert_flags_from_letters("G", AffectFlag))
    assert decoded_g == int(AffectFlag.DETECT_GOOD), (
        f"ROM G should be AFF_DETECT_GOOD; got {decoded_g:#x}, "
        f"AffectFlag.DETECT_GOOD={int(AffectFlag.DETECT_GOOD):#x}"
    )

    decoded_h = int(convert_flags_from_letters("H", AffectFlag))
    assert decoded_h == int(AffectFlag.SANCTUARY)

    decoded_z = int(convert_flags_from_letters("Z", AffectFlag))
    assert decoded_z == int(AffectFlag.DARK_VISION)

    decoded_dd = int(convert_flags_from_letters("dd", AffectFlag))
    assert decoded_dd == int(AffectFlag.SLOW)
