from __future__ import annotations

from tools.diff_harness.compare import diff_traces, normalize_step
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
        output=["\x1b[31mRed\x1b[0m text\r\n"],
    )
    norm = normalize_step(step)
    assert norm.chars[0].affects == ["armor", "bless"]        # sorted
    assert norm.chars[0].affect_flags == ["A", "B"]           # sorted
    assert norm.chars[0].inventory == [3010, 3022]            # order preserved
    assert norm.rooms[0].people == ["abe", "zeke"]            # sorted
    assert norm.rooms[0].contents == [3001, 3010]             # sorted
    assert norm.output == ["Red text"]                        # ANSI/CRLF/trailing stripped


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
