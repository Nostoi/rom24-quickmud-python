"""OLC_SAVE-009 — area-grouped help-save / help-load round trip.

Mirrors ROM src/olc_save.c:826-872 (save_helps writes the per-area
``#HELPS`` block as ``<level> <keyword>~`` followed by tilde-terminated
text; save_other_helps walks the global ``had_list`` writing each
file). Without a Python help-save path, hedit edits and AREA_CHANGED
help-area work were silently unsaveable; the OLC_SAVE-010 hedit
dispatcher branch had to no-op behind a "Grabando area :" placeholder.

JSON-authoritative framing: emit a top-level ``helps`` list per area
JSON file (symmetric with mobs / objects / rooms / mob_programs /
shops / specials). Loader-side rehydration appends each entry to
``area.helps`` and registers it in the global ``help_registry`` so
``do help <keyword>`` keeps working after a save→reload cycle.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mud.loaders.json_loader import load_area_from_json
from mud.models.area import Area
from mud.models.help import (
    HelpEntry,
    clear_help_registry,
    help_registry,
    register_help,
)
from mud.olc.save import save_area_to_json
from mud.registry import area_registry


@pytest.fixture(autouse=True)
def _clean_registries():
    saved_areas = dict(area_registry)
    saved_helps = {k: list(v) for k, v in help_registry.items()}
    area_registry.clear()
    clear_help_registry()
    try:
        yield
    finally:
        area_registry.clear()
        clear_help_registry()
        area_registry.update(saved_areas)
        for k, v in saved_helps.items():
            help_registry[k] = list(v)


def _build_area() -> Area:
    return Area(
        vnum=920,
        name="OLC_SAVE-009 Test Area",
        file_name="olc_save_009_test.are",
        min_vnum=9200,
        max_vnum=9209,
    )


def test_serialized_area_emits_helps_section(tmp_path: Path):
    """ROM save_helps writes one row per HELP_DATA in the area's HAD.
    JSON-authoritative analogue: one entry per `area.helps` element."""
    area = _build_area()
    area.helps = [
        HelpEntry(level=0, keywords=["dragon", "wyrm"], text="A scaled beast."),
        HelpEntry(level=15, keywords=["arcane"], text="Lore of magic."),
    ]
    area_registry[area.vnum] = area

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_009_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)

    helps = data.get("helps")
    assert isinstance(helps, list)
    assert len(helps) == 2
    assert helps[0] == {"level": 0, "keywords": ["dragon", "wyrm"], "text": "A scaled beast."}
    assert helps[1] == {"level": 15, "keywords": ["arcane"], "text": "Lore of magic."}


def test_helps_round_trip_through_save_and_load(tmp_path: Path):
    """save → clear registries → load_area_from_json → area.helps and
    help_registry are rehydrated."""
    area = _build_area()
    entry = HelpEntry(level=0, keywords=["griffin"], text="A flying beast.")
    area.helps = [entry]
    area_registry[area.vnum] = area
    register_help(entry)

    assert "griffin" in help_registry

    save_ok = save_area_to_json(area, output_dir=tmp_path)
    assert save_ok is True

    # Wipe runtime state, then reload from disk.
    area_registry.clear()
    clear_help_registry()
    assert "griffin" not in help_registry

    saved_path = tmp_path / "olc_save_009_test.json"
    reloaded = load_area_from_json(str(saved_path))

    assert len(reloaded.helps) == 1
    rehydrated = reloaded.helps[0]
    assert rehydrated.keywords == ["griffin"]
    assert rehydrated.text == "A flying beast."
    assert rehydrated.level == 0
    assert "griffin" in help_registry


def test_area_with_no_helps_omits_or_emits_empty_section(tmp_path: Path):
    """Area with empty `area.helps` must not crash the writer; the
    section may be omitted or emitted as []."""
    area = _build_area()
    area.helps = []
    area_registry[area.vnum] = area

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_009_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)

    assert data.get("helps", []) == []
