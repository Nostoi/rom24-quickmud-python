"""HANDLER-004 — `is_name` must mirror ROM's whole-word `str_prefix` + all-parts rule.

ROM `src/handler.c:932-969` (`is_name`): each space-separated part of the search
`str` must be a `str_prefix` (whole-word *prefix*, not substring) of some word in
`namelist`, and **all** parts must match. Python's `is_name` previously used a
substring test (`name_lower in word`) and had no all-parts conjunction.
"""

from __future__ import annotations

from mud.world.char_find import is_name


def test_mid_word_substring_does_not_match():
    # mirrors ROM src/handler.c:962-965 — str_prefix("uard","guard") != 0
    # ("uard" is NOT a prefix of "guard"), so ROM returns FALSE. The old Python
    # substring test ("uard" in "guard") wrongly returned True.
    assert is_name("uard", "guard") is False


def test_prefix_matches():
    # mirrors ROM src/handler.c:965 — "gua" IS a prefix of "guard" → match.
    assert is_name("gua", "guard") is True
    assert is_name("guard", "guard") is True


def test_all_parts_must_match_multiword():
    # mirrors ROM src/handler.c:946-952 — "we need ALL parts of string to match
    # part of namelist". Both "big" and "guard" prefix a namelist word, in any
    # order, so the multi-word arg matches.
    assert is_name("big guard", "big guard") is True
    assert is_name("guard big", "big guard") is True


def test_one_unmatched_part_fails_whole_match():
    # mirrors ROM src/handler.c:959-960 — if any part matches no namelist word,
    # the loop returns FALSE even though other parts matched.
    assert is_name("big dog", "big guard") is False


def test_each_part_prefix_not_substring():
    # "ard" is a substring of "guard" but NOT a prefix → no match (parity with
    # the single-word case, applied per part).
    assert is_name("big ard", "big guard") is False


def test_empty_inputs_return_false():
    # mirrors ROM src/handler.c:938-943 — empty namelist or empty str → FALSE.
    assert is_name("", "guard") is False
    assert is_name("guard", "") is False
