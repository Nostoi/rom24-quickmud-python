"""OLC_ACT-016: `redit room`/`redit sector` match ROM's exact messages.

ROM src/olc_act.c:4972-4988 (redit_room) and :4990-5007 (redit_sector) both:
  - emit ROM's verbatim (Spanish, as shipped) syntax string on any failure —
    `"Sintaxis: room [flags]\\n\\r"` / `"Sintaxis: sector [tipo]\\n\\r"` — for
    BOTH the empty-argument and the unknown-flag cases (`flag_value` returns
    NO_FLAG for either);
  - emit a bare success string with NO value echoed —
    `"Room flags toggled.\\n\\r"` / `"Sector type set.\\n\\r"`.

This mirrors the established `imm_olc.py` mpedit precedent, which already
reproduces ROM's `"Sintaxis :"` strings verbatim. Python previously used
English placeholder text (`"Usage: ..."`, `"Unknown ... flags: X"`) and leaked
the sector value (`"Sector type set to {token}."`).
"""

from __future__ import annotations

from mud.commands.build import (
    _handle_room_flags_command,
    _handle_sector_command,
)
from mud.models.constants import RoomFlag
from mud.models.room import Room


def _room() -> Room:
    return Room(vnum=4200, name="R", room_flags=0, sector_type=0)


def test_redit_room_valid_flag_toggles_with_rom_message() -> None:
    room = _room()
    result = _handle_room_flags_command(room, ["dark"])
    assert result == "Room flags toggled."
    assert room.room_flags & int(RoomFlag.ROOM_DARK)


def test_redit_room_unknown_flag_emits_rom_syntax() -> None:
    room = _room()
    result = _handle_room_flags_command(room, ["notaflag"])
    assert result == "Sintaxis: room [flags]"
    assert room.room_flags == 0  # no toggle on failure


def test_redit_room_empty_emits_rom_syntax() -> None:
    room = _room()
    assert _handle_room_flags_command(room, []) == "Sintaxis: room [flags]"


def test_redit_sector_valid_sets_with_bare_message() -> None:
    room = _room()
    result = _handle_sector_command(room, ["city"])
    assert result == "Sector type set."
    assert room.sector_type == 1  # city


def test_redit_sector_unknown_emits_rom_syntax() -> None:
    room = _room()
    result = _handle_sector_command(room, ["notasector"])
    assert result == "Sintaxis: sector [tipo]"


def test_redit_sector_empty_emits_rom_syntax() -> None:
    room = _room()
    assert _handle_sector_command(room, []) == "Sintaxis: sector [tipo]"
