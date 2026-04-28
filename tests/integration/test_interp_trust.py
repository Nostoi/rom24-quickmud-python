"""Integration test for INTERP-001 — command trust must match ROM cmd_table.

ROM Reference: src/interp.c:63-381 cmd_table[], src/interp.h:34-44 trust macros.
"""
from __future__ import annotations

import pytest

from mud.commands.dispatcher import COMMANDS
from mud.models.constants import MAX_LEVEL

# (command_name, expected_min_trust). Mirrors ROM src/interp.c cmd_table trust column.
INTERP_001_TRUST = [
    # ML = 60
    ("advance", MAX_LEVEL),
    ("copyover", MAX_LEVEL),
    ("dump", MAX_LEVEL),
    ("trust", MAX_LEVEL),
    ("violate", MAX_LEVEL),
    ("qmconfig", MAX_LEVEL),
    # L1 = 59
    ("deny", MAX_LEVEL - 1),
    ("permban", MAX_LEVEL - 1),
    ("protect", MAX_LEVEL - 1),
    ("reboo", MAX_LEVEL - 1),
    ("reboot", MAX_LEVEL - 1),
    ("shutdow", MAX_LEVEL - 1),
    ("shutdown", MAX_LEVEL - 1),
    ("log", MAX_LEVEL - 1),
    # L2 = 58
    ("allow", MAX_LEVEL - 2),
    ("ban", MAX_LEVEL - 2),
    ("set", MAX_LEVEL - 2),
    ("wizlock", MAX_LEVEL - 2),
    # L3 = 57
    ("disconnect", MAX_LEVEL - 3),
    ("pardon", MAX_LEVEL - 3),
    ("sla", MAX_LEVEL - 3),
    ("slay", MAX_LEVEL - 3),
    # L4 = 56
    ("flag", MAX_LEVEL - 4),
    ("freeze", MAX_LEVEL - 4),
    ("guild", MAX_LEVEL - 4),
    ("load", MAX_LEVEL - 4),
    ("newlock", MAX_LEVEL - 4),
    ("pecho", MAX_LEVEL - 4),
    ("purge", MAX_LEVEL - 4),
    ("restore", MAX_LEVEL - 4),
    ("sockets", MAX_LEVEL - 4),
    ("vnum", MAX_LEVEL - 4),
    ("zecho", MAX_LEVEL - 4),
    ("gecho", MAX_LEVEL - 4),
    # L5 = 55
    ("nochannels", MAX_LEVEL - 5),
    ("noemote", MAX_LEVEL - 5),
    ("noshout", MAX_LEVEL - 5),
    ("notell", MAX_LEVEL - 5),
    ("peace", MAX_LEVEL - 5),
    ("snoop", MAX_LEVEL - 5),
    ("string", MAX_LEVEL - 5),
    ("transfer", MAX_LEVEL - 5),
    ("teleport", MAX_LEVEL - 5),
    ("clone", MAX_LEVEL - 5),
    # L6 = 54
    ("at", MAX_LEVEL - 6),
    ("echo", MAX_LEVEL - 6),
    ("recho", MAX_LEVEL - 6),
    ("return", MAX_LEVEL - 6),
    ("switch", MAX_LEVEL - 6),
    # L7 = 53
    ("force", MAX_LEVEL - 7),
]


@pytest.mark.parametrize("name,expected_trust", INTERP_001_TRUST)
def test_interp_001_command_trust_matches_rom(name, expected_trust):
    # mirrors ROM src/interp.c:63-381 cmd_table[] trust_level column.
    matches = [c for c in COMMANDS if c.name == name]
    assert matches, f"command {name!r} not registered in COMMANDS"
    assert len(matches) == 1, f"command {name!r} registered multiple times"
    assert matches[0].min_trust == expected_trust, (
        f"{name}: min_trust={matches[0].min_trust} != ROM expected={expected_trust}"
    )
