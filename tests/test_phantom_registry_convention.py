"""Guard: nobody may read or inject phantom attributes off ``mud.registry``.

``mud/registry.py`` defines exactly five registry dicts — ``room_registry``,
``mob_registry``, ``obj_registry``, ``area_registry``, ``shop_registry`` — plus
the scalar ``max_on_today``. It has never had ``char_list``, ``players``,
``skill_table``, ``object_list``, ``areas``, ``rooms``, ``helps``, ``socials``,
``social_table``, ``social_registry``, ``player_registry``, ``note_boards`` or
``group_table``. Production code that read those via
``getattr(registry, "<name>", default)`` silently scanned the empty default (the
INV-046 PHANTOM-REGISTRY bug class — families 1–3b): ``transfer all``,
``force players``, ``gecho``, ``mwhere``, reboot/shutdown announces reached
nobody; ``memory``/``dump`` printed zero counts; ``slookup``/``owhere``/
``socials``/``groups`` listed nothing; ``sset`` and ``peek`` silently no-op'd —
while tests *injected* the attributes to make those dead reads observable,
hiding the divergence.

The real backing structures are:

- ``mud.models.character.character_registry`` — ROM ``char_list``/``player_registry``
  (walk ``reversed(...)`` for ROM's newest-first order, INV-045);
- ``registry.descriptor_list`` — ROM ``descriptor_list``, lazily attached by
  ``mud/net/connection.py:_descriptor_list`` (NOT phantom, deliberately allowed);
- ``registry.area_registry`` / ``registry.room_registry`` — areas/rooms;
- ``mud.skills.registry.skill_registry`` / ``char.skills`` — skill table + learned;
- ``mud.models.obj.object_registry`` — live objects;
- ``mud.models.help.help_entries`` — help entries;
- ``mud.models.social.social_registry`` — socials;
- ``mud.notes.board_registry`` — note boards;
- ``mud.skills.groups`` — skill groups.

This scanner fails loudly if either side of the feedback loop reappears:
production reads under ``mud/``, or test injections under ``tests/`` that would
let new code "pass" against a structure the live game never populates.

See AGENTS.md "Cross-File Invariants" and
docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md INV-046.
"""

from __future__ import annotations

import re
from pathlib import Path

# Phantom attribute names that ``mud/registry.py`` does NOT define. Reading any
# of these off the ``registry`` module returns the getattr default in production
# (empty/zero), the INV-046 bug class. The real backing structures are:
#   char_list/players  → mud.models.character.character_registry (+ descriptor_list)
#   skill_table        → mud.skills.registry.skill_registry / char.skills (family 3b)
#   object_list        → mud.models.obj.object_registry
#   areas/rooms        → registry.area_registry / registry.room_registry
#   helps              → mud.models.help.help_entries
#   socials/social_*   → mud.models.social.social_registry
#   player_registry    → character_registry (PC filter)
#   note_boards        → mud.notes.board_registry
#   group_table        → mud.skills.groups
# NOTE: max_on_today IS a real attribute (mud/registry.py, ROM's static max_on) —
# deliberately NOT banned. The five real *_registry dicts are likewise allowed.
_PHANTOM_NAMES = (
    "char_list",
    "players",
    "skill_table",
    "object_list",
    "areas",
    "rooms",
    "helps",
    "socials",
    "social_table",
    "social_registry",
    "player_registry",
    "note_boards",
    "group_table",
)
_NAMES_ALT = "|".join(_PHANTOM_NAMES)

# Attribute access (read OR assignment) on any *registry* binding:
# registry.char_list, global_registry.players = {}, registry.skill_table, ...
_ATTR_PATTERN = re.compile(rf"\bregistry\.(?:{_NAMES_ALT})\b")

# getattr/hasattr/setattr/delattr with a phantom-attribute string literal on a
# *registry* binding: getattr(registry, "char_list", []), getattr(registry, "skill_table", []), ...
_GETATTR_PATTERN = re.compile(rf"\b(?:get|has|set|del)attr\(\s*\w*registry\w*\s*,\s*[\"'](?:{_NAMES_ALT})[\"']")

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
        "phantom registry attribute found — mud/registry.py defines only the five "
        "*_registry dicts + max_on_today (INV-046). Use the real backing structure: "
        "character_registry (char_list/players), area_registry/room_registry, "
        "skill_registry/char.skills (skill_table), object_registry, help_entries, "
        "social_registry, board_registry (note_boards), mud.skills.groups (group_table):\n" + "\n".join(offenders)
    )
