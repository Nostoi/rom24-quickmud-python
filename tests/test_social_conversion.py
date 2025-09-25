from __future__ import annotations

import json
from pathlib import Path

from mud.scripts.convert_social_are_to_json import convert, parse_socials


def test_parse_socials_smile_and_kiss():
    text = Path("area/social.are").read_text(encoding="utf-8")
    data = parse_socials(text)
    names = {d["name"] for d in data}
    assert "smile" in names and "kiss" in names
    smile = next(d for d in data if d["name"] == "smile")
    assert smile["char_no_arg"].startswith("You smile")
    assert "$n" in smile["others_no_arg"]
    # Ensure field order count is 8 message fields
    for key in (
        "char_no_arg",
        "others_no_arg",
        "char_found",
        "others_found",
        "vict_found",
        "not_found",
        "char_auto",
        "others_auto",
    ):
        assert key in smile


def test_convert_social_are_to_json_matches_layout(tmp_path):
    out = tmp_path / "socials.json"
    convert("area/social.are", out)
    js = json.loads(out.read_text(encoding="utf-8"))
    # Validate a few canonical entries against source text
    smile = next(d for d in js if d["name"] == "smile")
    assert smile["char_no_arg"] == "You smile happily."
    assert smile["others_no_arg"] == "$n smiles happily."
    assert smile["char_found"] == "You smile at $M."
    assert smile["vict_found"].endswith("you.")
    assert smile["char_auto"].startswith("You smile at yourself")

    kiss = next(d for d in js if d["name"] == "kiss")
    # "$" stands for empty field in ROM files
    assert kiss["others_no_arg"] == ""
    assert kiss["char_no_arg"].startswith("Isn't there someone you want to kiss?")

    # '#' early terminator fills remaining fields with empty strings
    sulk = next(d for d in js if d["name"] == "sulk")
    assert sulk["char_no_arg"].startswith("You sulk.")
    assert sulk["others_no_arg"].startswith("$n sulks")
    assert sulk["char_found"] == ""
