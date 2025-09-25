from __future__ import annotations

import json
from pathlib import Path

from mud.scripts.convert_help_are_to_json import parse_help_are


def test_convert_help_are_preserves_wizlock_entry(tmp_path: Path) -> None:
    src = Path("area/help.are")
    out = tmp_path / "help.json"

    entries = parse_help_are(src)
    with out.open("w", encoding="utf-8") as fp:
        json.dump(entries, fp, ensure_ascii=False, indent=2)

    # Find the WIZLOCK/NEWLOCK entry; ROM shows level 56 with both keywords.
    wiz = None
    for e in entries:
        kws = {k.lower() for k in e.get("keywords", [])}
        if {"wizlock", "newlock"}.issubset(kws):
            wiz = e
            break

    assert wiz is not None, "Expected WIZLOCK/NEWLOCK help entry in area/help.are"
    assert wiz["level"] == 56

    text: str = wiz["text"]
    # Verify key text lines (including newline between syntax lines)
    assert "Syntax: wizlock\n\tnewlock" in text
    assert "Wizlock and newlock both block login attempts" in text
