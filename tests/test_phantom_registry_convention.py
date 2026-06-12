"""Guard: nobody may read or inject phantom ``registry.char_list`` / ``registry.players``.

``mud/registry.py`` defines exactly five registries — ``room_registry``,
``mob_registry``, ``obj_registry``, ``area_registry``, ``shop_registry``. It has
never had ``char_list`` or ``players``. Production code that read them via
``getattr(registry, "char_list", [])`` / ``getattr(registry, "players", {})``
silently scanned nothing in production (the INV-046 PHANTOM-REGISTRY bug class:
``transfer all``, ``force players``, ``gecho``, ``mwhere``, reboot/shutdown
announces all reached nobody), while tests *injected* the attributes to make
those dead walks observable — hiding the divergence.

The real walk structures are:

- ``mud.models.character.character_registry`` — ROM ``char_list``
  (walk ``reversed(...)`` for ROM's newest-first order, INV-045);
- ``registry.descriptor_list`` — ROM ``descriptor_list``, lazily attached by
  ``mud/net/connection.py:_descriptor_list`` (NOT phantom, deliberately allowed).

This scanner fails loudly if either side of the feedback loop reappears:
production reads under ``mud/``, or test injections under ``tests/`` that would
let new code "pass" against a structure the live game never populates.

See AGENTS.md "Cross-File Invariants" and
docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md INV-046.
"""

from __future__ import annotations

import re
from pathlib import Path

# Attribute access (read OR assignment) on any *registry* binding:
# registry.char_list, global_registry.players = {}, ...
_ATTR_PATTERN = re.compile(r"\bregistry\.(?:char_list|players)\b")

# getattr/hasattr/setattr/delattr with a phantom-attribute string literal on a
# *registry* binding: getattr(registry, "char_list", []), hasattr(global_registry, "players"), ...
_GETATTR_PATTERN = re.compile(r"\b(?:get|has|set|del)attr\(\s*\w*registry\w*\s*,\s*[\"'](?:char_list|players)[\"']")

_SCAN_DIRS = ("mud", "tests")
_SELF = Path("tests/test_phantom_registry_convention.py")


def test_no_phantom_registry_attributes() -> None:
    offenders: list[str] = []
    for scan_dir in _SCAN_DIRS:
        for path in sorted(Path(scan_dir).rglob("*.py")):
            if path == _SELF:
                continue
            for lineno, line in enumerate(path.read_text().splitlines(), start=1):
                code = line.split("#", 1)[0]  # ignore comments that cite the anti-pattern
                if _ATTR_PATTERN.search(code) or _GETATTR_PATTERN.search(code):
                    offenders.append(f"{path}:{lineno}: {line.strip()}")
    assert not offenders, (
        "phantom registry attribute found — mud/registry.py has no char_list/players "
        "(INV-046). Walk reversed(mud.models.character.character_registry) for ROM "
        "char_list, or registry.descriptor_list for the descriptor walk:\n" + "\n".join(offenders)
    )
