from __future__ import annotations

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
