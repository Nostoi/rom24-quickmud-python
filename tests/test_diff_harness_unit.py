from __future__ import annotations

from pathlib import Path

import pytest

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from tools.diff_harness.compare import diff_traces, normalize_step
from tools.diff_harness.pysnap import snapshot_python
from tools.diff_harness.scenario import Scenario, load_scenario
from tools.diff_harness.schema import CharSnap, RoomSnap, StepSnap, step_from_dict, step_to_dict


def _sample_step() -> StepSnap:
    return StepSnap(
        step=3,
        command="get sword",
        chars=[
            CharSnap(
                key="Tester", room=3001, position="STANDING",
                hp=100, max_hp=100, mana=100, move=100,
                level=5, align=0, gold=0, fighting=None,
                affects=["bless"], affect_flags=["INFRARED"],
                inventory=[3022], equipment={"16": 1},
            )
        ],
        rooms=[RoomSnap(vnum=3001, people=["Tester"], contents=[3010, 3010])],
        output=["You pick up a sword."],
    )


def test_step_roundtrips_through_dict():
    step = _sample_step()
    restored = step_from_dict(step_to_dict(step))
    assert restored == step


def test_normalize_sorts_unordered_lists_and_strips_ansi():
    step = StepSnap(
        step=1, command="look",
        chars=[CharSnap(
            key="Tester", room=3001, position="STANDING",
            hp=1, max_hp=1, mana=0, move=0, level=1, align=0, gold=0,
            fighting=None, affects=["bless", "armor"], affect_flags=["B", "A"],
            inventory=[3010, 3022], equipment={},
        )],
        rooms=[RoomSnap(vnum=3001, people=["zeke", "abe"], contents=[3010, 3001])],
        # Real ANSI escapes AND raw ROM colour tokens ({2…{x) — the Python engine
        # emits the latter; the C shim's colour-off descriptor strips them
        # (FINDING-008 sub-issue 2). Both must normalize to plain text.
        output=["\x1b[31mRed\x1b[0m text\r\n", "{2You miss the drunk.{x"],
    )
    norm = normalize_step(step)
    assert norm.chars[0].affects == ["armor", "bless"]        # sorted
    assert norm.chars[0].affect_flags == ["A", "B"]           # sorted
    assert norm.chars[0].inventory == [3010, 3022]            # order preserved
    assert norm.rooms[0].people == ["abe", "zeke"]            # sorted
    assert norm.rooms[0].contents == [3001, 3010]             # sorted
    # ANSI escapes + ROM colour tokens both stripped; CRLF/trailing trimmed.
    assert norm.output == ["Red text", "You miss the drunk."]


def test_diff_traces_reports_first_divergence():
    a = [StepSnap(step=1, command="get sword",
                  chars=[CharSnap("T", 3001, "STANDING", 1, 1, 0, 0, 1, 0, 0, None,
                                  inventory=[3022])], rooms=[], output=[])]
    b = [StepSnap(step=1, command="get sword",
                  chars=[CharSnap("T", 3001, "STANDING", 1, 1, 0, 0, 1, 0, 0, None,
                                  inventory=[3010])], rooms=[], output=[])]
    report = diff_traces(a, b)
    assert report is not None
    assert "step 1" in report
    assert "inventory" in report


def test_diff_traces_identical_returns_none():
    a = [StepSnap(step=1, command="look", chars=[], rooms=[], output=["hi"])]
    b = [StepSnap(step=1, command="look", chars=[], rooms=[], output=["hi"])]
    assert diff_traces(a, b) is None


@pytest.fixture
def watched_world():
    room = Room(vnum=3001, name="R", description="")
    char = Character(name="Tester", level=5, position=Position.STANDING)
    char.hit = char.max_hit = 100
    char.room = room
    room.add_character(char)
    return room, char


def test_snapshot_python_captures_watch_set(watched_world):
    room, char = watched_world
    rooms_by_vnum = {3001: room}
    chars_by_name = {"Tester": char}

    step = snapshot_python(
        step=2, command="look",
        chars_by_name=chars_by_name, rooms_by_vnum=rooms_by_vnum, output=["You see a room."],
    )

    assert step.step == 2
    assert step.command == "look"
    assert step.chars[0].key == "Tester"
    assert step.chars[0].room == 3001
    assert step.chars[0].position == "STANDING"
    assert step.chars[0].hp == 100
    assert step.rooms[0].vnum == 3001
    assert "Tester" in step.rooms[0].people
    assert step.output == ["You see a room."]


def test_snapshot_reads_affects_from_spell_effect(watched_world):
    """A SpellEffect applied via apply_spell_effect must surface in the snapshot's
    `affects` list under the ROM skill name, matching the C shim's
    skill_table[paf->type].name. The real affect model (AffectData) stores the
    identity in `.type`, not `.spell_name`/`.name`, so pysnap must read `.type`.
    No differential golden exercises affects, so this is the only regression
    guard for that instrument read."""
    from mud.models.character import SpellEffect

    room, char = watched_world
    # ROM spell_armor: APPLY_AC -20, no bitvector (character.py armor handler).
    char.apply_spell_effect(SpellEffect(name="armor", duration=24, level=10, ac_mod=-20))

    step = snapshot_python(
        step=1, command="cast armor",
        chars_by_name={"Tester": char}, rooms_by_vnum={3001: room}, output=[],
    )
    assert step.chars[0].affects == ["armor"]


def test_snapshot_reads_affects_from_int_sn_affect(watched_world):
    """AffectData added via affect_to_char carries an int ROM SN in `.type`;
    pysnap must map it through the skill_table index so it matches the C shim's
    skill_table[paf->type].name (lowercase)."""
    from mud.models.character import AffectData
    from mud.skills.metadata import ROM_SKILL_NAMES_BY_INDEX

    room, char = watched_world
    armor_sn = ROM_SKILL_NAMES_BY_INDEX.index("armor")
    char.affect_to_char(
        AffectData(type=armor_sn, level=10, duration=24, location=17, modifier=-20, bitvector=0)
    )

    step = snapshot_python(
        step=1, command="look",
        chars_by_name={"Tester": char}, rooms_by_vnum={3001: room}, output=[],
    )
    assert step.chars[0].affects == ["armor"]


def test_load_scenario_parses_fields(tmp_path: Path):
    p = tmp_path / "s.json"
    p.write_text(
        '{"name":"s","seed":1234,"start_room":3001,'
        '"char":{"name":"Tester","level":5},'
        '"watch":{"chars":["Tester"],"rooms":[3001,3054]},'
        '"steps":["look","north"]}'
    )
    sc = load_scenario(p)
    assert isinstance(sc, Scenario)
    assert sc.name == "s"
    assert sc.seed == 1234
    assert sc.start_room == 3001
    assert sc.char_name == "Tester"
    assert sc.char_level == 5
    assert sc.watch_chars == ["Tester"]
    assert sc.watch_rooms == [3001, 3054]
    assert sc.steps == ["look", "north"]
