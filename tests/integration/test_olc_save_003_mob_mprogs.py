"""OLC_SAVE-003 — mob mprog assignments persisted on JSON save.

Mirrors ROM src/olc_save.c:245-250 (save_mobile emits per-mob MPROG list)
plus src/olc_save.c:151-169 (save_mobprogs writes the area-level
#MOBPROGS section). Without this, a save→reload cycle silently erases
all mob program bindings.

Python's JSON model keeps program code area-wide under ``mob_programs``
with assignments back to mobs (see mud/loaders/json_loader.py:496-530),
so the serializer reverses that: walk every mob in the area, collect
their ``mprogs`` lists, group by program vnum, and emit the structured
``mob_programs`` payload.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mud.mobprog import Trigger
from mud.models.area import Area
from mud.models.mob import MobIndex, MobProgram
from mud.olc.save import save_area_to_json
from mud.registry import mob_registry


@pytest.fixture(autouse=True)
def _clean_mob_registry():
    saved = dict(mob_registry)
    mob_registry.clear()
    try:
        yield
    finally:
        mob_registry.clear()
        mob_registry.update(saved)


def _build_area() -> Area:
    return Area(
        vnum=999,
        name="OLC_SAVE-003 Test Area",
        file_name="olc_save_003_test.are",
        min_vnum=9000,
        max_vnum=9009,
    )


def test_serialized_area_emits_mob_programs_section(tmp_path: Path):
    """One mob with one mprog assignment → one ``mob_programs`` entry."""
    area = _build_area()
    mob = MobIndex(vnum=9001, short_descr="prog mob", area=area)
    mob.mprogs.append(
        MobProgram(
            trig_type=int(Trigger.GREET),
            trig_phrase="hello",
            vnum=9001,
            code="say hi to $n",
        )
    )
    mob_registry[mob.vnum] = mob

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_003_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)

    assert "mob_programs" in data
    assert len(data["mob_programs"]) == 1
    program = data["mob_programs"][0]
    assert program["vnum"] == 9001
    assert program["code"] == "say hi to $n"
    assert len(program["assignments"]) == 1
    assignment = program["assignments"][0]
    assert assignment["mob_vnum"] == 9001
    assert assignment["trigger"].lower() == "greet"
    assert assignment["phrase"] == "hello"


def test_multiple_mobs_share_one_program(tmp_path: Path):
    """Two mobs assigned the same program vnum → one program entry, two assignments."""
    area = _build_area()
    code = "say shared script"
    for vnum, trigger in ((9001, Trigger.GREET), (9002, Trigger.SPEECH)):
        mob = MobIndex(vnum=vnum, short_descr=f"mob {vnum}", area=area)
        mob.mprogs.append(
            MobProgram(trig_type=int(trigger), trig_phrase="x", vnum=9100, code=code)
        )
        mob_registry[mob.vnum] = mob

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_003_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)

    programs = data["mob_programs"]
    assert len(programs) == 1
    assert programs[0]["vnum"] == 9100
    assert programs[0]["code"] == code
    assignments = sorted(programs[0]["assignments"], key=lambda a: a["mob_vnum"])
    assert [a["mob_vnum"] for a in assignments] == [9001, 9002]


def test_mob_with_no_mprogs_emits_empty_section(tmp_path: Path):
    area = _build_area()
    mob = MobIndex(vnum=9001, short_descr="no progs", area=area)
    mob_registry[mob.vnum] = mob

    assert save_area_to_json(area, output_dir=tmp_path) is True

    saved_path = tmp_path / "olc_save_003_test.json"
    with open(saved_path, encoding="utf-8") as fh:
        data = json.load(fh)

    assert data.get("mob_programs", []) == []
