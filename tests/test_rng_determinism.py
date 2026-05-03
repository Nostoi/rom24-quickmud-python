from __future__ import annotations

import re
from pathlib import Path


_PATTERN = re.compile(r"\bimport random\b|\bfrom random\b|\brandom\.")

_SCAN_DIRS = ["mud/combat", "mud/skills", "mud/spells"]


def test_no_stdlib_random_in_combat_skills_spells() -> None:
    offenders: list[str] = []
    for directory in _SCAN_DIRS:
        for path in sorted(Path(directory).rglob("*.py")):
            for lineno, line in enumerate(path.read_text().splitlines(), start=1):
                if _PATTERN.search(line):
                    offenders.append(f"{path}:{lineno}: {line.rstrip()}")
    assert not offenders, (
        "stdlib random.* found — all rolls must use mud.math.rng_mm (ROM src/db.c init_mm):\n"
        + "\n".join(offenders)
    )
