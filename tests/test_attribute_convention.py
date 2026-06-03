"""Guard: production code must use the canonical ROM-port attribute names.

AGENTS.md "ROM Parity Rules" mandates:
  - character inventory is `char.inventory`, never `char.carrying`
  - room occupants are `room.people`, never `room.characters`
  - equipped gear is `char.equipment` (int-keyed), never `char.equipped`
    (the `char.equipped["held"]` anti-pattern — `.equipped` doesn't exist, so it
    silently reads `{}`; this caused the `compare`-vs-worn-weapon bug fixed 2.9.87)

These are not behavioral bugs on their own, but the wrong name silently reads a
non-existent / stale attribute. The codebase is currently clean (0 occurrences);
this scanner locks that in the same way `test_rng_determinism.py` bans `random.*`
and `test_equipment_key_convention.py` bans string-keyed equipment access.

If a legitimate future use of one of these names ever appears on an unrelated
class, narrow the pattern — do not delete the guard.
"""

from __future__ import annotations

import re
from pathlib import Path

# Attribute access (preceded by `.`) to a banned name, word-bounded so
# `.character_registry`, `.inventory`, etc. are not matched. The `(?<!mud)`
# lookbehind excludes the `mud.characters` package path (an import, not the
# room-occupant attribute).
_PATTERN = re.compile(r"\.carrying\b|\.equipped\b|(?<!mud)\.characters\b")

_SCAN_DIR = "mud"


def test_no_legacy_attribute_names_in_production() -> None:
    offenders: list[str] = []
    for path in sorted(Path(_SCAN_DIR).rglob("*.py")):
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            code = line.split("#", 1)[0]  # ignore comments that cite the anti-pattern
            if _PATTERN.search(code):
                offenders.append(f"{path}:{lineno}: {line.strip()}")
    assert not offenders, (
        "legacy attribute name found — use `char.inventory` (not `.carrying`) and "
        "`room.people` (not `.characters`) per AGENTS.md ROM Parity Rules:\n" + "\n".join(offenders)
    )
