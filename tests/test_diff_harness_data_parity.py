"""Differential-harness input-source parity guard.

The harness compares ROM C against the Python port, but the two engines load
world data from *different sources*: the C shim reads ``.are`` files (a repaired
``midgaard`` overlay materialized under ``src/diff_shim/area/`` — the stock
``area/midgaard.are`` in this repo is malformed at the OBJECTS->ROOMS boundary:
``#`` instead of ``#ROOMS`` and a ``~ROOMS`` that swallowed the section keyword),
while the Python replay reads ``data/areas/*.json``.

A 2026-05-28 probe established the two sources cover an *identical* room/mobile/
object vnum set, so the asymmetry is structurally benign — the JSON was generated
from a correctly-parsed (or pre-repaired) source, not from the malformed parse.
But nothing *guarded* that equivalence: an edit to either ``area/midgaard.are`` or
``data/areas/midgaard.json`` could silently desync the two engines' world data and
manufacture false-positive (or mask true-positive) differential divergences.

This test locks the equivalence. It reconstructs the repaired ``.are`` in-memory
the same way ``src/Makefile.diffshim``'s ``area-overlay`` recipe does (so it does
not depend on the gitignored build artifact) and asserts its vnum sets match the
JSON the Python loader reads. See tools/diff_harness/FINDINGS.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ARE_PATH = REPO / "area" / "midgaard.are"
JSON_PATH = REPO / "data" / "areas" / "midgaard.json"


def _repair_are(text: str) -> str:
    """Mirror src/Makefile.diffshim area-overlay: inject the missing ``#ROOMS``
    section header and undo the ``~ROOMS`` keyword merge. Equivalent to the awk:

        NR>1 { if (prev=="#" && $0 ~ /^#[0-9]+$/) print "#ROOMS";
               else { sub(/^~ROOMS$/, "~", prev); print prev; } }
             { prev=$0 }
        END  { sub(/^~ROOMS$/, "~", prev); print prev }
    """
    lines = text.split("\n")
    out: list[str] = []
    prev: str | None = None
    for cur in lines:
        if prev is not None:
            if prev == "#" and re.fullmatch(r"#[0-9]+", cur):
                out.append("#ROOMS")
            else:
                out.append("~" if prev == "~ROOMS" else prev)
        prev = cur
    if prev is not None:
        out.append("~" if prev == "~ROOMS" else prev)
    return "\n".join(out)


def _section_vnums(repaired: str, start_header: str, end_header: str) -> set[int]:
    """Vnums (``#NNNN`` records, excluding the ``#0`` terminator) of one section."""
    seg = repaired.split(start_header, 1)[1].split(end_header, 1)[0]
    return {int(m) for m in re.findall(r"^#(\d+)$", seg, re.M) if int(m) != 0}


def test_midgaard_json_and_repaired_are_cover_identical_vnums():
    repaired = _repair_are(ARE_PATH.read_text())
    assert "\n#ROOMS\n" in "\n" + repaired, "repair failed to inject #ROOMS header"

    are_rooms = _section_vnums(repaired, "#ROOMS", "#RESETS")
    are_mobiles = _section_vnums(repaired, "#MOBILES", "#OBJECTS")
    are_objects = _section_vnums(repaired, "#OBJECTS", "#ROOMS")

    data = json.loads(JSON_PATH.read_text())
    json_rooms = {r["id"] for r in data["rooms"]}
    json_mobiles = {m["id"] for m in data["mobiles"]}
    json_objects = {o["id"] for o in data["objects"]}

    assert are_rooms == json_rooms, (
        f"room vnum drift between C .are and Python JSON: "
        f"only in .are={sorted(are_rooms - json_rooms)}, only in JSON={sorted(json_rooms - are_rooms)}"
    )
    assert are_mobiles == json_mobiles, (
        f"mobile vnum drift: only in .are={sorted(are_mobiles - json_mobiles)}, "
        f"only in JSON={sorted(json_mobiles - are_mobiles)}"
    )
    assert are_objects == json_objects, (
        f"object vnum drift: only in .are={sorted(are_objects - json_objects)}, "
        f"only in JSON={sorted(json_objects - are_objects)}"
    )
