from __future__ import annotations

from pathlib import Path

import pytest

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from tools.diff_harness.compare import diff_traces, normalize_step
from tools.diff_harness.oracle import build_c_input, drive_c_oracle
from tools.diff_harness.pyreplay import drive_python_replay
from tools.diff_harness.pysnap import snapshot_python
from tools.diff_harness.scenario import Scenario, load_scenario
from tools.diff_harness.schema import CharSnap, RoomSnap, StepSnap, step_from_dict, step_to_dict


def _sample_step() -> StepSnap:
    return StepSnap(
        step=3,
        command="get sword",
        chars=[
            CharSnap(
                key="Tester",
                room=3001,
                position="STANDING",
                hp=100,
                max_hp=100,
                mana=100,
                move=100,
                level=5,
                align=0,
                gold=0,
                silver=0,
                fighting=None,
                affects=["bless"],
                affect_flags=["INFRARED"],
                inventory=[3022],
                equipment={"16": 1},
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
        step=1,
        command="look",
        chars=[
            CharSnap(
                key="Tester",
                room=3001,
                position="STANDING",
                hp=1,
                max_hp=1,
                mana=0,
                move=0,
                level=1,
                align=0,
                gold=0,
                silver=0,
                fighting=None,
                affects=["bless", "armor"],
                affect_flags=["B", "A"],
                inventory=[3010, 3022],
                equipment={},
            )
        ],
        rooms=[RoomSnap(vnum=3001, people=["zeke", "abe"], contents=[3010, 3001])],
        # Real ANSI escapes AND raw ROM colour tokens ({2…{x) — the Python engine
        # emits the latter; the C shim's colour-off descriptor strips them
        # (FINDING-008 sub-issue 2). Both must normalize to plain text.
        output=["\x1b[31mRed\x1b[0m text\r\n", "{2You miss the drunk.{x"],
    )
    norm = normalize_step(step)
    assert norm.chars[0].affects == ["armor", "bless"]  # sorted
    assert norm.chars[0].affect_flags == ["a", "b"]  # sorted, lowercased
    assert norm.chars[0].inventory == [3010, 3022]  # order preserved
    assert norm.rooms[0].people == ["abe", "zeke"]  # sorted
    assert norm.rooms[0].contents == [3001, 3010]  # sorted
    # ANSI escapes + ROM colour tokens both stripped; CRLF/trailing trimmed.
    assert norm.output == ["Red text", "You miss the drunk."]


def test_diff_traces_reports_first_divergence():
    a = [
        StepSnap(
            step=1,
            command="get sword",
            chars=[CharSnap("T", 3001, "STANDING", 1, 1, 0, 0, 1, 0, 0, 0, None, inventory=[3022])],
            rooms=[],
            output=[],
        )
    ]
    b = [
        StepSnap(
            step=1,
            command="get sword",
            chars=[CharSnap("T", 3001, "STANDING", 1, 1, 0, 0, 1, 0, 0, 0, None, inventory=[3010])],
            rooms=[],
            output=[],
        )
    ]
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
        step=2,
        command="look",
        chars_by_name=chars_by_name,
        rooms_by_vnum=rooms_by_vnum,
        output=["You see a room."],
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
        step=1,
        command="cast armor",
        chars_by_name={"Tester": char},
        rooms_by_vnum={3001: room},
        output=[],
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
    char.affect_to_char(AffectData(type=armor_sn, level=10, duration=24, location=17, modifier=-20, bitvector=0))

    step = snapshot_python(
        step=1,
        command="look",
        chars_by_name={"Tester": char},
        rooms_by_vnum={3001: room},
        output=[],
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


def test_build_c_input_accepts_in_memory_scenario():
    sc = Scenario(
        name="generated",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester", "drunk"],
        watch_rooms=[3001, 3054],
        steps=["look", "north"],
    )

    assert build_c_input(sc).splitlines() == [
        "boot seed=777 start_room=3001 level=5 char=Tester",
        "look",
        "__snapshot chars=Tester,drunk rooms=3001,3054",
        "north",
        "__snapshot chars=Tester,drunk rooms=3001,3054",
    ]


def test_drive_c_oracle_parses_live_trace_without_golden(tmp_path: Path):
    sc = Scenario(
        name="generated",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["look"],
    )

    def fake_run(*args, **kwargs):
        assert kwargs["input"] == build_c_input(sc)
        return type(
            "Result",
            (),
            {
                "returncode": 0,
                "stderr": "",
                "stdout": (
                    '{"type":"output","lines":["A room."]}\n'
                    '{"type":"snapshot","chars":[{"key":"Tester","room":3001,'
                    '"position":"STANDING","hp":20,"max_hp":20,"mana":100,"move":100,'
                    '"level":5,"align":0,"gold":0,"fighting":null}],'
                    '"rooms":[{"vnum":3001,"people":["Tester"],"contents":[]}]}\n'
                ),
            },
        )()

    trace = drive_c_oracle(sc, tmp_path / "diffshim", run=fake_run)

    assert trace == [
        StepSnap(
            step=1,
            command="look",
            chars=[CharSnap("Tester", 3001, "STANDING", 20, 20, 100, 100, 5, 0, 0, 0, None)],
            rooms=[RoomSnap(vnum=3001, people=["Tester"], contents=[])],
            output=["A room."],
        )
    ]


def test_drive_c_oracle_raises_on_binary_failure(tmp_path: Path):
    sc = Scenario(
        name="generated",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["look"],
    )

    def fake_run(*args, **kwargs):
        return type("Result", (), {"returncode": 2, "stderr": "boom", "stdout": ""})()

    with pytest.raises(RuntimeError, match=r"(?s)C binary exited 2.*boom"):
        drive_c_oracle(sc, tmp_path / "diffshim", run=fake_run)


def test_drive_python_replay_accepts_in_memory_scenario():
    sc = Scenario(
        name="generated",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["inventory"],
    )

    trace = drive_python_replay(sc)

    assert len(trace) == 1
    assert trace[0].command == "inventory"
    assert trace[0].chars[0].key == "Tester"
    assert trace[0].chars[0].hp == 20
    assert trace[0].chars[0].mana == 100
    assert trace[0].chars[0].move == 100


def test_drive_python_replay_goto_moves_character_between_watched_rooms():
    sc = Scenario(
        name="generated_goto",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001, 3110],
        steps=["__goto=3110"],
    )

    trace = drive_python_replay(sc)

    assert trace[0].chars[0].room == 3110
    rooms = {room.vnum: room for room in trace[0].rooms}
    assert "Tester" not in rooms[3001].people
    assert "Tester" in rooms[3110].people


def test_drive_python_replay_level_meta_updates_character_level():
    sc = Scenario(
        name="generated_level",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__level=30"],
    )

    trace = drive_python_replay(sc)

    assert trace[0].chars[0].level == 30


def test_drive_python_replay_learn_pct_meta_sets_partial_skill():
    sc = Scenario(
        name="generated_learn_pct",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=7,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__learn_pct=armor=17", "practice"],
    )

    trace = drive_python_replay(sc)

    assert trace[1].output == ["armor               17%  ", "You have 5 practice sessions left.", ""]


def test_drive_python_replay_plr_autoloot_meta_sets_flag():
    sc = Scenario(
        name="generated_plr_autoloot",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__plr_autoloot=1", "autoloot"],
    )

    trace = drive_python_replay(sc)

    assert trace[1].output == ["Autolooting removed."]


def test_drive_python_replay_plr_autogold_meta_sets_flag():
    sc = Scenario(
        name="generated_plr_autogold",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__plr_autogold=1", "autogold"],
    )

    trace = drive_python_replay(sc)

    assert trace[1].output == ["Autogold removed."]


def test_drive_python_replay_plr_autosac_meta_sets_flag():
    sc = Scenario(
        name="generated_plr_autosac",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__plr_autosac=1", "autosac"],
    )

    trace = drive_python_replay(sc)

    assert trace[1].output == ["Autosacrificing removed."]


def test_drive_python_replay_mana_meta_sets_mana_and_max_mana():
    sc = Scenario(
        name="generated_mana",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__mana=500"],
    )

    trace = drive_python_replay(sc)

    assert trace[0].chars[0].mana == 500


def test_drive_python_replay_char_class_meta_affects_hit_gain():
    # Warrior (class 3, hp_max=15) vs default mage (class 0, hp_max=8).
    # With CON=13, level=5, standing, no skills: warrior gain=17//4=4, mage=10//4=2.
    # Mana and move start at max so only hit_gain is called (no other RNG draw).
    sc = Scenario(
        name="generated_char_class",
        seed=12345,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__hp=1", "__char_class=3", "__char_update"],
    )

    trace = drive_python_replay(sc)

    # After __char_update (step 3), warrior adds 4 HP: 1 + 4 = 5.
    assert trace[2].chars[0].hp == 5


def test_drive_python_replay_char_position_meta_affects_hit_gain():
    # Sleeping (position=4) gives full hit_gain; standing (default) gives gain//4.
    # Mage, CON=13, level=5: base gain = max(3, 13-3+2) + (8-10) = 10.
    # Sleeping: 10 (no division). Standing: 10//4 = 2.
    # Mana and move start at max so only hit_gain is called.
    sc = Scenario(
        name="generated_char_position",
        seed=12345,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__hp=1", "__char_position=4", "__char_update"],
    )

    trace = drive_python_replay(sc)

    # After __char_update (step 2), sleeping mage adds 10 HP: 1 + 10 = 11.
    assert trace[2].chars[0].hp == 11
    assert trace[1].chars[0].position == "SLEEPING"


def test_drive_python_replay_char_position_resting_halves_all_gain():
    # Resting (position=5) halves HP and mana gain vs sleeping; move uses DEX/2.
    # Mage, level 5: hit base=10, resting=10//2=5; mana base=17, resting=17//2=8;
    # move base=UMAX(15,5)+DEX//2=15+6=21.  HP starts at 5/20, mana 30/100, move 20/100.
    sc = Scenario(
        name="generated_resting",
        seed=12345,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__hp=5", "__mana=30", "__move=20", "__char_position=5", "__seed=12345", "__char_update"],
    )

    trace = drive_python_replay(sc)

    after = trace[5].chars[0]  # step 6 = after __char_update
    assert after.position == "RESTING"
    assert after.hp == 10  # 5 + 5
    assert after.mana == 38  # 30 + 8
    assert after.move == 41  # 20 + 21


def test_drive_python_replay_oload_exercises_get_wield_remove_drop():
    sc = Scenario(
        name="generated_oload",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__oload=3021", "get sword", "wield sword", "remove sword", "drop sword"],
    )

    trace = drive_python_replay(sc)

    char_snaps = [step.chars[0] for step in trace]
    room_snaps = [step.rooms[0] for step in trace]
    assert room_snaps[0].contents == [3021]
    assert char_snaps[1].inventory == [3021]
    assert char_snaps[2].equipment == {"16": 3021}
    assert char_snaps[3].inventory == [3021]
    assert room_snaps[4].contents == [3021]


def test_drive_python_replay_hunger_thirst_zero_halves_regen_twice():
    # hunger=0 halves gain; thirst=0 halves it again.  Applied in SLEEPING (no
    # position penalty) so gains remain nonzero and visibly distinct from the
    # baseline.  C oracle (seed 12345): HP +2, mana +4, move +7 per pulse.
    # Compare: sleeping WITHOUT conditions → HP +10, mana +17, move +28/pulse.
    sc = Scenario(
        name="generated_hungry_thirsty",
        seed=12345,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__char_position=4",
            "__hp=1",
            "__mana=5",
            "__move=5",
            "__cond_hunger=0",
            "__cond_thirst=0",
            "__char_update",
        ],
    )

    trace = drive_python_replay(sc)

    after = trace[6].chars[0]  # step 6 = after __char_update
    assert after.position == "SLEEPING"
    assert after.hp == 3  # 1 + 2 (sleeping base //2 hunger //2 thirst)
    assert after.mana == 9  # 5 + 4
    assert after.move == 12  # 5 + 7


def test_drive_python_replay_comm_combine_groups_identical_room_objects():
    """drive_python_replay sets COMM_COMBINE on the test char, mirroring
    C shim make_test_char (diffmain.c:462: ch->comm = COMM_COMBINE|COMM_PROMPT).
    Two identical objects in a room must produce a single '( 2) ...' line
    in the look output, not two separate lines (FINDING-033)."""
    sc = Scenario(
        name="combine_test",
        seed=777,
        start_room=3008,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3008],
        steps=["__oload=3135", "__oload=3135", "look"],
    )

    trace = drive_python_replay(sc)
    look_step = trace[2]  # step index 2 = "look"
    output_lines = [line for line in look_step.output if "fountain" in line.lower()]
    # With COMM_COMBINE: one grouped line '( 2) A small white fountain...'
    # Without COMM_COMBINE: two identical lines (FINDING-033 symptom)
    assert len(output_lines) == 1, f"Expected 1 grouped fountain line, got {len(output_lines)}: {output_lines}"
    assert output_lines[0].startswith("( 2)"), f"Expected '( 2) ...' prefix, got: {output_lines[0]!r}"


def test_drive_python_replay_poison_affect_halves_regen_by_four():
    # AFF_POISON (bit 4096, ROM AFF_POISON = 1<<12) causes hit_gain/mana_gain/
    # move_gain to divide by 4 (ROM src/update.c:276-278).  Applied in SLEEPING
    # (no position penalty) so gains remain clearly nonzero.
    # C oracle (seed 12345): HP +2, mana +4, move +7 per pulse.
    # __add_affect=4096 sets only the bitmask without a spell-affect entry,
    # exercising the IS_AFFECTED branch without tick-side interference.
    sc = Scenario(
        name="generated_poison",
        seed=12345,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__char_position=4",
            "__hp=1",
            "__mana=5",
            "__move=5",
            "__add_affect=4096",
            "__char_update",
        ],
    )

    trace = drive_python_replay(sc)

    after = trace[5].chars[0]  # step 6 = after __char_update
    assert after.position == "SLEEPING"
    assert after.hp == 3  # 1 + 2  (sleeping base 10 // 4 = 2)
    assert after.mana == 9  # 5 + 4  (sleeping base 17 // 4 = 4)
    assert after.move == 12  # 5 + 7  (sleeping base 28 // 4 = 7)


def test_drive_python_replay_haste_affect_halves_regen_by_two():
    # AFF_HASTE (bit 2097152, ROM AFF_HASTE = 1<<21) causes hit_gain/mana_gain/
    # move_gain to divide by 2 (ROM src/update.c:280-282).  Applied in SLEEPING.
    # C oracle (seed 12345): HP +5, mana +8, move +14 per pulse.
    # __add_affect=2097152 sets only the bitmask without a spell-affect entry.
    sc = Scenario(
        name="generated_haste",
        seed=12345,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__char_position=4",
            "__hp=1",
            "__mana=5",
            "__move=5",
            "__add_affect=2097152",
            "__char_update",
        ],
    )

    trace = drive_python_replay(sc)

    after = trace[5].chars[0]  # step 6 = after __char_update
    assert after.position == "SLEEPING"
    assert after.hp == 6  # 1 + 5  (sleeping base 10 // 2 = 5)
    assert after.mana == 13  # 5 + 8  (sleeping base 17 // 2 = 8)
    assert after.move == 19  # 5 + 14 (sleeping base 28 // 2 = 14)


def test_drive_python_replay_plague_affect_divides_regen_by_eight():
    # AFF_PLAGUE (bit 8388608, ROM AFF_PLAGUE = 1<<23) causes hit_gain/mana_gain/
    # move_gain to divide by 8 (ROM src/update.c:277-279).  Applied in SLEEPING.
    # C oracle (seed 12345): HP +1, mana +2, move +3 per pulse.
    # GL-038: __add_affect=8388608 sets only the bitmask (no spell-affect entry).
    # C's plague tick gate is is_affected(ch, gsn_plague) — spell LIST check — so
    # the tick never fires and the bitmask persists across all pulses.  After fix,
    # Python matches: plague flag stays set, ÷8 divisor applies every pulse.
    sc = Scenario(
        name="generated_plague",
        seed=12345,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__char_position=4",
            "__hp=1",
            "__mana=5",
            "__move=5",
            "__add_affect=8388608",
            "__char_update",
        ],
    )

    trace = drive_python_replay(sc)

    after = trace[5].chars[0]  # step 6 = after __char_update
    assert after.position == "SLEEPING"
    assert after.hp == 2  # 1 + 1  (sleeping base 10 // 8 = 1)
    assert after.mana == 7  # 5 + 2  (sleeping base 17 // 8 = 2)
    assert after.move == 8  # 5 + 3  (sleeping base 28 // 8 = 3)
    assert any(f.lower() == "plague" for f in after.affect_flags)  # bit persists — no spell entry, tick never fires


def test_drive_python_replay_room_rates_heal_and_mana_independent():
    # heal_rate multiplies hit_gain and move_gain (ROM src/update.c:215,326:
    #   gain = gain * ch->in_room->heal_rate / 100).
    # mana_rate multiplies mana_gain ONLY (ROM src/update.c:297:
    #   gain = gain * ch->in_room->mana_rate / 100).
    # heal_rate=50 → HP ÷2 (+5) and move ÷2 (+14).
    # mana_rate=200 → mana ×2 (+34).
    # C oracle (seed 12345, SLEEPING L5 mage): HP +5/pulse, mana +34/pulse,
    # move +14/pulse.
    sc = Scenario(
        name="generated_room_rates",
        seed=12345,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__char_position=4",
            "__hp=1",
            "__mana=5",
            "__move=5",
            "__set_heal_rate=50",
            "__set_mana_rate=200",
            "__char_update",
        ],
    )

    trace = drive_python_replay(sc)

    after = trace[6].chars[0]  # step 7 = after __char_update
    assert after.position == "SLEEPING"
    assert after.hp == 6  # 1 + 5   (base 10 * 50/100 = 5)
    assert after.mana == 39  # 5 + 34  (base 17 * 200/100 = 34)
    assert after.move == 19  # 5 + 14  (base 28 * 50/100 = 14)


def test_drive_python_replay_slow_affect_halves_regen_by_two():
    # AFF_SLOW (bit 536870912, ROM AFF_SLOW = 1<<29) causes hit_gain/mana_gain/
    # move_gain to divide by 2, same branch as HASTE (ROM src/update.c:280-282).
    # C oracle (seed 12345): HP +5, mana +8, move +14 per pulse.
    # No tick side-effects for SLOW — only the regen divisor branch.
    sc = Scenario(
        name="generated_slow",
        seed=12345,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__char_position=4",
            "__hp=1",
            "__mana=5",
            "__move=5",
            "__add_affect=536870912",
            "__char_update",
        ],
    )

    trace = drive_python_replay(sc)

    after = trace[5].chars[0]  # step 6 = after __char_update
    assert after.position == "SLEEPING"
    assert after.hp == 6  # 1 + 5  (sleeping base 10 // 2 = 5)
    assert after.mana == 13  # 5 + 8  (sleeping base 17 // 2 = 8)
    assert after.move == 19  # 5 + 14 (sleeping base 28 // 2 = 14)


def test_drive_python_replay_furniture_bonus_scales_regen():
    # Furniture sitting bonus: ROM src/update.c:217-218 (hit_gain), :299-300
    # (mana_gain), :350-351 (move_gain).
    # value[3] = 150 → HP and move both scale by * 150 / 100.
    # value[4] = 200 → mana scales by * 200 / 100.
    # Distinct multipliers (150 ≠ 200) make a value-index swap detectable:
    # if move used value[4] or mana used value[3] the numbers would differ.
    # C oracle (seed 12345, SLEEPING L5, bench vnum 3134):
    #   HP  +15 per pulse (base 10 * 150/100 = 15).
    #   mana +34 per pulse (base 17 * 200/100 = 34).
    #   move +42 per pulse (base 28 * 150/100 = 42).
    sc = Scenario(
        name="generated_furniture",
        seed=12345,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__char_position=4",
            "__hp=1",
            "__mana=5",
            "__move=5",
            "__set_on=3134",
            "__set_on_val3=150",
            "__set_on_val4=200",
            "__seed=12345",
            "__char_update",
        ],
    )

    trace = drive_python_replay(sc)

    after = trace[8].chars[0]  # step 9 = after __char_update
    assert after.position == "SLEEPING"
    assert after.hp == 16  # 1 + 15  (base 10 * 150/100 = 15)
    assert after.mana == 39  # 5 + 34  (base 17 * 200/100 = 34)
    assert after.move == 47  # 5 + 42  (base 28 * 150/100 = 42)
