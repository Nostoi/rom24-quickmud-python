"""STRING-007 — `string_unpad(argument)` helper.

Mirrors ROM `src/string.c:516-543`. Trims leading and trailing spaces
(but not internal whitespace) from a string. Used by `aedit_builder`
when normalizing area-name input.
"""

from __future__ import annotations

from mud.utils.string_editor import string_unpad


def test_string_unpad_trims_leading_spaces() -> None:
    assert string_unpad("   hello") == "hello"


def test_string_unpad_trims_trailing_spaces() -> None:
    assert string_unpad("hello   ") == "hello"


def test_string_unpad_trims_both() -> None:
    assert string_unpad("   hello world   ") == "hello world"


def test_string_unpad_preserves_internal_spaces() -> None:
    assert string_unpad("  a  b  c  ") == "a  b  c"


def test_string_unpad_empty_string() -> None:
    assert string_unpad("") == ""


def test_string_unpad_only_spaces_yields_empty() -> None:
    assert string_unpad("     ") == ""


def test_string_unpad_no_spaces_unchanged() -> None:
    assert string_unpad("hello") == "hello"
