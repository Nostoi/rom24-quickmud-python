"""Guard: group_commands.py must not define its own add_follower / stop_follower.

ROM src/act_comm.c defines ``add_follower`` and ``stop_follower`` in a single
place. Python's canonical port lives in ``mud.characters.follow``. A duplicate
in ``mud/commands/group_commands.py`` diverges in:

- charm-strip: local version only bit-clears ``affected_by``; canonical calls
  ``remove_spell_effect("charm person")`` + ``remove_affect(AffectFlag.CHARM)``,
  matching ROM ``affect_strip(ch, gsn_charm_person)`` in ``stop_follower``.
- ``add_follower`` guard: local returns early if ``char.master is not None``
  (any master); canonical checks identity and calls ``stop_follower`` first if
  following a *different* master, matching ROM src/act_comm.c:1591-1592.

All callers inside ``group_commands.py`` (``do_follow``) must use the canonical
implementation imported from ``mud.characters.follow``.

See docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md for the corresponding INV note.
"""

from __future__ import annotations

import ast
from pathlib import Path

_TARGET = Path("mud/commands/group_commands.py")
_FORBIDDEN_DEFS = frozenset({"add_follower", "stop_follower"})
_CANONICAL_MODULE = "mud.characters.follow"


def test_no_local_follow_helpers_in_group_commands() -> None:
    """group_commands.py must not define its own add_follower or stop_follower."""
    src = _TARGET.read_text()
    tree = ast.parse(src)
    offenders = [
        f"{_TARGET}:def {node.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name in _FORBIDDEN_DEFS
    ]
    assert not offenders, (
        f"Local definition(s) of follow helpers found in {_TARGET}. "
        f"These must be imported from {_CANONICAL_MODULE!r} instead:\n" + "\n".join(offenders)
    )


def test_group_commands_imports_canonical_follow_helpers() -> None:
    """group_commands.py must import add_follower and stop_follower from mud.characters.follow."""
    src = _TARGET.read_text()
    tree = ast.parse(src)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == _CANONICAL_MODULE:
                for alias in node.names:
                    imported.add(alias.asname or alias.name)
    missing = _FORBIDDEN_DEFS - imported
    assert not missing, (
        f"{_TARGET} does not import {missing} from {_CANONICAL_MODULE!r}. "
        "Import canonical follow helpers — do not re-define them locally."
    )
