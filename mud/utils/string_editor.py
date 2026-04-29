"""Port of ROM `src/string.c` editor helpers (STRING-001..012).

The descriptor-state setters (`string_edit`, `string_append`) and the
input dispatcher (`string_add`) live alongside the pure utilities here.
Descriptor plumbing is provided by `mud/olc/editor_state.py`
(OLC-INFRA-001).
"""

from __future__ import annotations


def merc_getline(string: str) -> tuple[str, str]:
    """Read one ``\\n``-terminated line; return ``(rest, line)``.

    Mirrors ROM ``merc_getline`` (src/string.c:647-674). When ``\\n`` is
    followed by ``\\r``, both are consumed (the ROM canonical line-ending
    pair). The terminator is not included in the returned line.
    """

    nl = string.find("\n")
    if nl == -1:
        return "", string
    line = string[:nl]
    rest_start = nl + 1
    if rest_start < len(string) and string[rest_start] == "\r":
        rest_start += 1
    return string[rest_start:], line


def first_arg(argument: str, lower: bool = False) -> tuple[str, str]:
    """Quote/paren-aware single-arg parser.

    Mirrors ROM ``first_arg`` (src/string.c:468-508). Returns
    ``(rest, word)`` — the remainder of *argument* (with leading spaces
    stripped) and the parsed first word.

    Recognized quote characters: ``'``, ``"``, ``%`` (each pairs with
    itself); ``(`` pairs with ``)``. Quoted words may contain spaces.
    Unterminated quotes consume the rest of the input.

    When ``lower`` is True (ROM ``fCase``), the parsed word is
    lowercased; otherwise its case is preserved.
    """

    i = 0
    n = len(argument)
    while i < n and argument[i] == " ":
        i += 1

    end_char = " "
    if i < n and argument[i] in ("'", '"', "%", "("):
        if argument[i] == "(":
            end_char = ")"
        else:
            end_char = argument[i]
        i += 1

    chars: list[str] = []
    while i < n:
        c = argument[i]
        if c == end_char:
            i += 1
            break
        chars.append(c.lower() if lower else c)
        i += 1

    while i < n and argument[i] == " ":
        i += 1

    return argument[i:], "".join(chars)


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


def numlines(string: str) -> str:
    """Format string as line-numbered listing (``%2d. <line>\n\r``).

    Mirrors ROM ``numlines`` (src/string.c:676-692). Returns a string where
    each line from the input is prefixed with its 1-indexed line number in
    ``%2d`` format (right-aligned 2-char width), followed by a period and
    the line content, with ``\n\r`` appended to each line.

    Used by ``.s`` dot-command and `string_append` greeting.
    """

    if not string:
        return ""

    lines: list[str] = []
    line_num = 1
    rest = string

    while rest:
        rest, line = merc_getline(rest)
        lines.append(f"{line_num:2d}. {line}\n\r")
        line_num += 1

    return "".join(lines)
