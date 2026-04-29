"""STRING-006 — `first_arg(argument, lower)` helper.

Mirrors ROM `src/string.c:468-508`. Quote/paren-aware single-arg parser:
recognizes `'`, `"`, `%`, `(`/`)` as balanced quote pairs; returns the
parsed word and the remainder.
"""

from __future__ import annotations

from mud.utils.string_editor import first_arg


def test_first_arg_simple_word() -> None:
    rest, word = first_arg("hello world")
    assert word == "hello"
    assert rest == "world"


def test_first_arg_skips_leading_spaces() -> None:
    rest, word = first_arg("   hello   world")
    assert word == "hello"
    assert rest == "world"


def test_first_arg_single_quote() -> None:
    rest, word = first_arg("'hello world' rest")
    assert word == "hello world"
    assert rest == "rest"


def test_first_arg_double_quote() -> None:
    rest, word = first_arg('"hello world" rest')
    assert word == "hello world"
    assert rest == "rest"


def test_first_arg_percent_quote() -> None:
    rest, word = first_arg("%hello world% rest")
    assert word == "hello world"
    assert rest == "rest"


def test_first_arg_paren_quote() -> None:
    # mirrors ROM src/string.c:479-483 — `(` opens, `)` closes.
    rest, word = first_arg("(hello world) rest")
    assert word == "hello world"
    assert rest == "rest"


def test_first_arg_lower_flag_lowercases() -> None:
    # mirrors ROM src/string.c:495-498 — fCase=TRUE -> LOWER each char.
    rest, word = first_arg("HeLLo WoRLD", lower=True)
    assert word == "hello"
    assert rest == "WoRLD"


def test_first_arg_default_preserves_case() -> None:
    rest, word = first_arg("HeLLo WoRLD")
    assert word == "HeLLo"
    assert rest == "WoRLD"


def test_first_arg_empty_string() -> None:
    rest, word = first_arg("")
    assert word == ""
    assert rest == ""


def test_first_arg_unterminated_quote_consumes_rest() -> None:
    # mirrors ROM src/string.c:488-501 — loop runs until `*argument == '\0'`,
    # so an unterminated quote eats the entire remainder.
    rest, word = first_arg("'never ending")
    assert word == "never ending"
    assert rest == ""
