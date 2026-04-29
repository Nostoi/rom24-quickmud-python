"""Port of ROM `src/string.c` editor helpers (STRING-001..012).

The descriptor-state setters (`string_edit`, `string_append`) and the
input dispatcher (`string_add`) live alongside the pure utilities here.
Descriptor plumbing is provided by `mud/olc/editor_state.py`
(OLC-INFRA-001).
"""

from __future__ import annotations


def string_proper(argument: str) -> str:
    """Uppercase the first character of each space-delimited word.

    Mirrors ROM ``string_proper`` (src/string.c:551-572). Differs from
    ``str.title()``: ROM only uppercases the boundary character — the
    rest of each word is left as-is.
    """

    chars = list(argument)
    i = 0
    n = len(chars)
    while i < n:
        if chars[i] != " ":
            chars[i] = chars[i].upper()
            while i < n and chars[i] != " ":
                i += 1
        else:
            i += 1
    return "".join(chars)


def string_unpad(argument: str) -> str:
    """Trim leading and trailing spaces (only spaces, not all whitespace).

    Mirrors ROM ``string_unpad`` (src/string.c:516-543). Used by
    `aedit_builder` when normalizing area-name input.
    """

    return argument.strip(" ")
