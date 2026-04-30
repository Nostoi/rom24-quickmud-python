"""OLC_SAVE-013 — save_area_list emits social.are prepend.

Mirrors ROM src/olc_save.c:94 (save_area_list writes "social.are\n" as the
first row of the area.lst file per ROM OLC convention). Python omitted the
prepend; this test ensures it is now emitted.

HAD/HELP_AREA standalone-help rows remain N/A pending OLC_SAVE-009 help-save
port.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.models.area import Area
from mud.olc.save import save_area_list
from mud.registry import area_registry


@pytest.fixture(autouse=True)
def _clean_registries():
    saved_areas = dict(area_registry)
    area_registry.clear()
    try:
        yield
    finally:
        area_registry.clear()
        area_registry.update(saved_areas)


def test_save_area_list_prepends_social_are_with_areas(tmp_path: Path):
    """Two areas registered → output begins with social.are then area filenames."""
    area1 = Area(
        vnum=100,
        name="Area 1",
        file_name="area1.are",
        min_vnum=1000,
        max_vnum=1099,
    )
    area2 = Area(
        vnum=200,
        name="Area 2",
        file_name="area2.json",
        min_vnum=2000,
        max_vnum=2099,
    )
    area_registry[area1.vnum] = area1
    area_registry[area2.vnum] = area2

    output_file = tmp_path / "area.lst"
    result = save_area_list(output_file=output_file)

    assert result is True
    content = output_file.read_text(encoding="utf-8")

    # Expected: social.are\n, then areas sorted by vnum (area1 then area2),
    # then $\n. Note: .are is converted to .json.
    lines = content.split("\n")
    assert lines[0] == "social.are", f"First line should be 'social.are', got: {lines[0]}"
    assert lines[1] == "area1.json", f"Second line should be 'area1.json', got: {lines[1]}"
    assert lines[2] == "area2.json", f"Third line should be 'area2.json', got: {lines[2]}"
    assert lines[3] == "$", f"Fourth line should be '$', got: {lines[3]}"


def test_save_area_list_social_are_prepend_empty_registry(tmp_path: Path):
    """Empty area_registry → output is exactly social.are\\n$\\n."""
    output_file = tmp_path / "area.lst"
    result = save_area_list(output_file=output_file)

    assert result is True
    content = output_file.read_text(encoding="utf-8")

    lines = content.split("\n")
    assert lines[0] == "social.are", f"First line should be 'social.are', got: {lines[0]}"
    assert lines[1] == "$", f"Second line should be '$', got: {lines[1]}"
