"""Guard: production code must never read Character.equipment by a string slot key.

ROM keys equipped objects by the integer wear slot — `get_eq_char(ch, int iWear)`
(`src/handler.c:1733`) loops `obj->wear_loc == iWear`; there are no string slot
names in ROM. Python's `Character.equipment` is therefore keyed strictly by
`int(WearLocation.X)`. The write paths (`do_wear`, `Character.equip_object`, the
JSON restore in `from_orm`) all canonicalize via
`mud.models.constants.canonical_wear_slot`; every reader must look up the int key.

A string-literal access like `equipment.get("wield")` or `equipment["shield"]`
silently misses objects equipped under the canonical int key — exactly the class
of bug fixed in 2.9.87 (school-banner light uncounted in room lighting; worn
shield invisible to the combat shield check). This scanner fails loudly if any
such access reappears, the same way `test_rng_determinism.py` bans `random.*`.

See AGENTS.md "Equipment lookup" and
docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md INV-028.
"""

from __future__ import annotations

import re
from pathlib import Path

# (1) Subscript or .get() access to an `equipment` mapping with a string literal
# key: equipment["x"], equipment.get('x'), foo_equipment["x"], etc.
_EQUIPMENT_PATTERN = re.compile(r"equipment\s*(?:\.get\(|\[)\s*[\"']")

# (2) Subscript or .get() with a DISTINCTIVE wear-slot name on ANY variable —
# catches `equipped.get("wield")` (different var name) and the
# `getattr(x, "equipment", {}).get("hold")` chain that pattern (1) misses. Only
# unambiguous slot names are listed (no "body"/"head"/"light" — those could be
# legitimate keys in unrelated dicts and would false-positive).
_SLOT_NAME_PATTERN = re.compile(
    r"(?:\.get\(|\[)\s*[\"']"
    r"(?:wield|wielded|hold|float|floating|shield|lfinger|rfinger|lwrist|rwrist|neck1|neck2|main_hand)"
    r"[\"']"
)

_SCAN_DIR = "mud"


def test_no_string_keyed_equipment_access_in_production() -> None:
    offenders: list[str] = []
    for path in sorted(Path(_SCAN_DIR).rglob("*.py")):
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            code = line.split("#", 1)[0]  # ignore comments that cite the anti-pattern
            if _EQUIPMENT_PATTERN.search(code) or _SLOT_NAME_PATTERN.search(code):
                offenders.append(f"{path}:{lineno}: {line.strip()}")
    assert not offenders, (
        "string-keyed equipment access found — Character.equipment is keyed by "
        "int(WearLocation.X) (ROM src/handler.c get_eq_char). Use the int key or "
        "mud.models.constants.canonical_wear_slot():\n" + "\n".join(offenders)
    )
