"""Port of ROM `src/string.c` editor helpers (STRING-001..012).

The descriptor-state setters (`string_edit`, `string_append`) and the
input dispatcher (`string_add`) live alongside the pure utilities here.
Descriptor plumbing is provided by `mud/olc/editor_state.py`
(OLC-INFRA-001).
"""

from __future__ import annotations


def string_unpad(argument: str) -> str:
    """Trim leading and trailing spaces (only spaces, not all whitespace).

    Mirrors ROM ``string_unpad`` (src/string.c:516-543). Used by
    `aedit_builder` when normalizing area-name input.
    """

    return argument.strip(" ")
