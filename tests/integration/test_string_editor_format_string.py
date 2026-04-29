"""Integration tests for format_string (STRING-005).

Mirrors ROM src/string.c:299-451. Tests the word-wrap + sentence-capitalization
+ paren-rebalance formatter.
"""

from __future__ import annotations

import logging

from mud.utils.string_editor import format_string


def test_format_string_empty():
    """Empty string produces just the terminal newline."""
    result = format_string("")
    assert result == "\n\r"


def test_format_string_single_word():
    """Single word gets capitalized and terminates with \\n\\r."""
    result = format_string("hello")
    assert result == "Hello\n\r"


def test_format_string_leading_whitespace_stripped():
    """Leading spaces/whitespace are stripped (i=0 guard: no space appended)."""
    result = format_string("   hello")
    assert result == "Hello\n\r"


def test_format_string_multiple_spaces_collapsed():
    """Multiple internal spaces are collapsed to one."""
    result = format_string("hello    world")
    assert result == "Hello world\n\r"


def test_format_string_cr_lf_collapsed():
    """CR is silently dropped; LF is treated as a space between words.

    ROM src/string.c:313-321: '\\n' → space (if last char != ' '), '\\r' → skip.
    Tab is not in the ROM case list so it falls through to the normal char
    branch and is emitted as-is.
    """
    result = format_string("hello\rworld\nanother")
    # \r is skipped entirely; \n produces a space
    assert result == "Helloworld another\n\r"


def test_format_string_period_double_space():
    """Period followed by a word gets two spaces inserted."""
    result = format_string("hello. world")
    # After period: two spaces; next word capitalized
    assert result == "Hello.  World\n\r"


def test_format_string_question_mark_double_space():
    """Question mark similarly inserts two spaces and capitalizes."""
    result = format_string("hello? world")
    assert result == "Hello?  World\n\r"


def test_format_string_exclamation_double_space():
    """Exclamation mark similarly inserts two spaces and capitalizes."""
    result = format_string("hello! world")
    assert result == "Hello!  World\n\r"


def test_format_string_quote_after_period():
    """Period followed by quote: emit .'<space><space> and consume the quote."""
    # ROM: xbuf[i]= '.', xbuf[i+1]= '"', xbuf[i+2]=' ', xbuf[i+3]=' '
    result = format_string('hello." world')
    assert result == 'Hello."  World\n\r'


def test_format_string_capitalize_after_question():
    """Capitalize first alpha after '?'."""
    result = format_string("done? yes")
    assert result == "Done?  Yes\n\r"


def test_format_string_paren_rebalance():
    """Closing ) after '. ' rewrites so ) follows the punctuation directly.

    ROM: when xbuf ends in '.<space><space>' and next char is ')':
    replace the two trailing spaces with ')' then one space.
    E.g. 'He said hello.  )' becomes 'He said hello.)  '.
    """
    # Input: "He said hello.) Then" — ROM must catch `. ` before `)` paren case
    # The paren rebalance fires when buf already has "<punct><space><space>"
    # and we encounter ')'. ROM test: xbuf[i-1]==' ' && xbuf[i-2]==' ' &&
    # xbuf[i-3] in {'.','?','!'}.
    result = format_string("he said hello.) then")
    # After phase-1: "He said hello.)  Then\n\r"  (paren rebalance fires)
    assert result == "He said hello.)  Then\n\r"


def test_format_string_word_wrap_at_77():
    """A remaining segment of exactly 77 chars forces a line break.

    ROM for-loop runs i=0..76 (77 iterations); if none hit null, i==77 so
    i<77 is False and wrapping proceeds. The first wrap searches backward
    from column 73 (not 76) for a space.
    """
    # Build a string: 73 'a' chars + space + 'b' * 10 (total first segment = 84)
    # After first-pass tokenization the string is: "Aaaa...a bbbbbbbbbb\n\r"
    # First wrap scan: from pos 73 backward, finds space at pos 73 → wrap there
    word_a = "a" * 73
    word_b = "b" * 10
    result = format_string(f"{word_a} {word_b}")
    lines = result.split("\n\r")
    # First line should be exactly the 73 a-chars (lowered; then cap applied → 'A' + 'a'*72)
    assert lines[0] == "A" + "a" * 72
    assert lines[1].lstrip() == word_b


def test_format_string_wrap_76_chars_no_wrap():
    """76-char remaining segment does not force a line break."""
    # Build exactly 76 non-space chars
    word = "b" * 76
    result = format_string(word)
    # No \n\r except the trailing one
    assert result.count("\n\r") == 1
    assert result == "B" + "b" * 75 + "\n\r"


def test_format_string_long_word_mid_break(caplog):
    """A word > 77 chars triggers mid-word '-' break and logs a warning."""
    long_word = "x" * 80
    with caplog.at_level(logging.WARNING):
        result = format_string(long_word)
    # Should contain a '-\n\r' break
    assert "-\n\r" in result
    # Warning should have been emitted
    assert any("no spaces" in record.message.lower() for record in caplog.records)


def test_format_string_trailing_newline_cr():
    """Output always ends with \\n\\r (newline then carriage-return)."""
    result = format_string("hello")
    assert result.endswith("\n\r")


def test_format_string_multiple_sentences():
    """Multiple sentences are separated by two spaces, each starts capitalized."""
    result = format_string("first sentence. second sentence. third sentence.")
    assert result == "First sentence.  Second sentence.  Third sentence.\n\r"
