"""STRING-011 — `merc_getline(str)` helper.

Mirrors ROM `src/string.c:647-674`. Reads one ``\\n``-terminated line
into ``buf``, consuming a trailing ``\\r`` if present (so ``\\n\\r``
line endings — the ROM canonical pair — are fully consumed). Returns
``(rest_of_str, line)``.
"""

from __future__ import annotations

from mud.utils.string_editor import merc_getline


def test_merc_getline_reads_one_line() -> None:
    rest, line = merc_getline("hello\n\rworld\n\r")
    assert line == "hello"
    assert rest == "world\n\r"


def test_merc_getline_handles_lf_only() -> None:
    # mirrors ROM src/string.c:663-669 — `*(str+1) == '\r'` → +2, else +1.
    # Pure `\n` (no `\r`) is +1.
    rest, line = merc_getline("hello\nworld")
    assert line == "hello"
    assert rest == "world"


def test_merc_getline_no_newline_consumes_all() -> None:
    rest, line = merc_getline("hello world")
    assert line == "hello world"
    assert rest == ""


def test_merc_getline_empty_string() -> None:
    rest, line = merc_getline("")
    assert line == ""
    assert rest == ""


def test_merc_getline_immediate_newline() -> None:
    rest, line = merc_getline("\n\rrest")
    assert line == ""
    assert rest == "rest"


def test_merc_getline_consecutive_calls() -> None:
    # Numlines pattern: loop merc_getline until rest is empty.
    rest = "alpha\n\rbravo\n\rcharlie\n\r"
    lines = []
    while rest:
        rest, line = merc_getline(rest)
        lines.append(line)
    assert lines == ["alpha", "bravo", "charlie"]
