"""STRING-008 — `string_proper(argument)` helper.

Mirrors ROM `src/string.c:551-572`. Uppercases the first character of
each space-delimited word, leaving the rest of each word unchanged.
**Differs from Python `str.title()`** which also lowercases the rest of
each word — ROM `string_proper` does not.
"""

from __future__ import annotations

from mud.utils.string_editor import string_proper


def test_string_proper_capitalizes_first_letter_of_each_word() -> None:
    assert string_proper("hello world") == "Hello World"


def test_string_proper_leaves_rest_of_word_alone() -> None:
    # mirrors ROM src/string.c:561-563 — UPPER only on the boundary char.
    # Existing capitalization in the rest of the word is preserved.
    assert string_proper("heLLo wOrLd") == "HeLLo WOrLd"


def test_string_proper_handles_multiple_spaces() -> None:
    assert string_proper("a   b   c") == "A   B   C"


def test_string_proper_empty_string() -> None:
    assert string_proper("") == ""


def test_string_proper_single_word() -> None:
    assert string_proper("forest") == "Forest"


def test_string_proper_already_proper_unchanged() -> None:
    assert string_proper("Forest Of Doom") == "Forest Of Doom"


def test_string_proper_leading_space_preserved() -> None:
    assert string_proper(" hello world") == " Hello World"


def test_string_proper_non_letter_first_char_unchanged() -> None:
    # ROM `UPPER` is a no-op on non-alpha; punctuation stays.
    assert string_proper("3-headed dog") == "3-headed Dog"
