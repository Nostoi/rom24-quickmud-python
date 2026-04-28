"""INTERP-017 — prefix-match table-order parity sweep.

ROM's `cmd_table[]` is hand-ordered (src/interp.c:63-381) so that 1- and
2-letter abbreviations resolve to the canonical command. Python's
`COMMANDS` list is grouped by feature, so prefix resolution can diverge.

This test parses ROM's cmd_table at collection time (so it stays in sync
with the C source automatically), computes the ROM winner for each of the
26 single-letter prefixes plus a curated set of 2-letter prefixes that
ROM was hand-ordered to disambiguate, and asserts Python's
`resolve_command(prefix, trust=60)` returns a command of the same name.

Skipped automatically when ROM's winner has no Python counterpart at all
(cross-table command).
"""
from __future__ import annotations

import re
import string
from pathlib import Path

import pytest

from mud.commands.dispatcher import COMMAND_INDEX, COMMANDS, resolve_command

ROM_INTERP_C = Path(__file__).resolve().parents[2] / "src" / "interp.c"

# src/merc.h numeric levels.
_ROM_LEVEL = {
    "0": 0,
    "ML": 60,
    "L1": 59,
    "L2": 58,
    "L3": 57,
    "L4": 56,
    "L5": 55,
    "L6": 54,
    "L7": 53,
    "L8": 52,
    "IM": 52,
    "HE": 51,
}

_CMD_ROW = re.compile(r'^\s*\{\s*"([^"]+)"\s*,\s*\w+\s*,\s*\w+\s*,\s*([A-Z0-9_]+)\s*,')


def _parse_rom_cmd_table() -> list[tuple[str, int]]:
    """Return [(name, level), ...] in ROM cmd_table declaration order."""
    rows: list[tuple[str, int]] = []
    text = ROM_INTERP_C.read_text(encoding="latin-1")
    in_table = False
    for line in text.splitlines():
        if "cmd_table[]" in line:
            in_table = True
            continue
        if not in_table:
            continue
        # Sentinel `{ "", ... }` ends the table.
        if re.search(r'^\s*\{\s*""\s*,', line):
            break
        m = _CMD_ROW.match(line)
        if not m:
            continue
        name, level_token = m.group(1), m.group(2)
        rows.append((name, _ROM_LEVEL.get(level_token, 0)))
    return rows


ROM_CMD_TABLE = _parse_rom_cmd_table()
assert ROM_CMD_TABLE, "failed to parse ROM cmd_table from src/interp.c"

# Names ROM exposes at trust 60 (everything in the table).
_ROM_NAMES_AT_60 = {name for name, level in ROM_CMD_TABLE if level <= 60}
# Names Python exposes (Command.name + aliases).
_PY_NAMES = set(COMMAND_INDEX.keys()) | {cmd.name for cmd in COMMANDS}


def _rom_winner(prefix: str) -> str | None:
    """First cmd_table entry whose name startswith(prefix) at trust 60."""
    for name, level in ROM_CMD_TABLE:
        if level > 60:
            continue
        if name.startswith(prefix):
            return name
    return None


def _build_cases() -> list[tuple[str, str]]:
    """(prefix, expected_python_name) for every prefix where ROM has a winner
    AND that winner exists in Python's command set."""
    prefixes: list[str] = list(string.ascii_lowercase)
    # Common 2-letter prefixes ROM disambiguates by hand-ordering.
    prefixes += [
        "go", "gr", "mu", "we", "wi", "ho", "he", "re", "qu", "sa",
        "sc", "st", "sh", "sn", "so", "sp", "tr", "un", "wh", "wo",
    ]
    cases: list[tuple[str, str]] = []
    for prefix in prefixes:
        winner = _rom_winner(prefix)
        if winner is None:
            continue
        if winner not in _PY_NAMES:
            # ROM-only command (no Python counterpart yet) — skip rather than fail.
            continue
        cases.append((prefix, winner))
    return cases


PREFIX_CASES = _build_cases()


@pytest.mark.parametrize("prefix,expected_name", PREFIX_CASES)
def test_interp_017_prefix_winner_matches_rom(prefix: str, expected_name: str) -> None:
    # mirrors ROM src/interp.c:63-381 cmd_table[] hand-ordering and
    # interpret() at lines 442-453: first entry whose name starts with
    # the user input wins (trust gating already applied).
    cmd = resolve_command(prefix, trust=60)
    assert cmd is not None, (
        f"Python returned no command for prefix {prefix!r}; ROM resolves to {expected_name!r}"
    )
    # ROM cmd_table rows that share a do_fun (e.g. "hit" + "kill" both
    # call do_kill) are modelled in Python as a Command plus aliases, so
    # the matched name may be the canonical Command.name OR an alias.
    matched = (cmd.name, *cmd.aliases)
    assert expected_name in matched, (
        f"prefix {prefix!r}: Python -> {cmd.name!r} (aliases {cmd.aliases}), "
        f"ROM -> {expected_name!r}"
    )
