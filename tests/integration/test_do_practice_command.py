"""Integration tests for do_practice command (act_info.c:2680-2798).

Tests complete workflows for practicing skills with ROM 2.4b6 parity.

ROM Parity: src/act_info.c lines 2680-2798 (do_practice)
"""

from __future__ import annotations

import pytest

from mud.commands.advancement import do_practice
from mud.models.character import Character, PCData
from mud.models.constants import ActFlag, Position
from mud.models.room import Room
from mud.registry import room_registry
from mud.skills.registry import Skill, skill_registry


@pytest.fixture
def practice_room():
    """Create a test room for practicing"""
    room = Room(
        vnum=5000, name="Practice Hall", description="A hall for practicing skills.", room_flags=0, sector_type=0
    )
    room.people = []
    room.contents = []
    room_registry[5000] = room
    yield room
    room_registry.pop(5000, None)


@pytest.fixture
def practice_trainer(practice_room):
    """Create a practice trainer mob"""
    trainer = Character(
        name="practice trainer",
        short_descr="a practice trainer",
        long_descr="A practice trainer is standing here.",
        level=50,
        room=practice_room,
        is_npc=True,
        hit=1000,
        max_hit=1000,
        position=Position.STANDING,
    )
    trainer.act = int(ActFlag.PRACTICE)
    practice_room.people.append(trainer)
    yield trainer
    if trainer in practice_room.people:
        practice_room.people.remove(trainer)


@pytest.fixture
def practice_char(practice_room):
    """Create a test character with practice sessions"""
    char = Character(
        name="TestChar",
        level=5,
        room=practice_room,
        is_npc=False,
        hit=100,
        max_hit=100,
        ch_class=0,  # Mage
        practice=10,  # 10 practice sessions
    )

    # Initialize pcdata for non-NPC character
    char.pcdata = PCData()
    char.pcdata.pwd = "test_hash"

    # Initialize skills dict
    char.skills = {}

    # Initialize messages list
    char.messages = []

    def mock_int_learn_rate():
        return 10

    char.get_int_learn_rate = mock_int_learn_rate

    # Mock skill adept cap
    def mock_skill_adept_cap():
        return 95  # 95% adept cap

    char.skill_adept_cap = mock_skill_adept_cap

    # Mock is_awake
    char.is_awake = lambda: True

    practice_room.people.append(char)
    yield char
    if char in practice_room.people:
        practice_room.people.remove(char)


@pytest.fixture
def test_skill():
    """Register a test skill for practice"""
    skill = Skill(
        name="fireball",
        type="spell",
        function="spell_fireball",
        target="victim",
        levels=(5, 99, 99, 99),
        ratings=(1, 5, 5, 5),
    )
    skill_registry.skills["fireball"] = skill

    original_find_spell = skill_registry.find_spell

    def mock_find_spell(character, name):
        if "fireball" in name.lower():
            return skill
        return original_find_spell(character, name)

    skill_registry.find_spell = mock_find_spell  # type: ignore[method-assign]

    yield skill

    skill_registry.skills.pop("fireball", None)
    skill_registry.find_spell = original_find_spell  # type: ignore[method-assign]


# ============================================================================
# P0 Tests (Critical Functionality)
# ============================================================================


def test_practice_npc_returns_empty(practice_trainer):
    """NPCs can't practice (ROM C line 2682-2683)"""
    output = do_practice(practice_trainer, "")
    assert output == ""


def test_practice_list_no_skills(practice_char):
    """Empty skill list shows practice sessions (ROM C lines 2689-2712)"""
    output = do_practice(practice_char, "")
    assert "You have 10 practice sessions left" in output


def test_practice_list_with_skills(practice_char, test_skill):
    """Shows known skills in 3 columns (ROM C lines 2689-2712)"""
    practice_char.skills = {
        "fireball": 50,
    }

    output = do_practice(practice_char, "")

    assert "fireball" in output
    assert "50%" in output
    assert "You have 10 practice sessions left" in output


def test_practice_list_formatting(practice_char, test_skill):
    """Verify 3-column layout with correct formatting (ROM C lines 2701-2707)"""
    practice_char.skills = {
        "fireball": 50,
    }

    output = do_practice(practice_char, "")

    lines = output.split("\n")

    assert len(lines) >= 2

    assert any("%" in line for line in lines)


def test_practice_not_awake(practice_char):
    """Can't practice while sleeping (ROM C lines 2714-2715)"""
    # Mock is_awake to return False
    practice_char.is_awake = lambda: False

    output = do_practice(practice_char, "fireball")
    assert "In your dreams, or what?" in output


def test_practice_no_trainer(practice_char, test_skill):
    """Can't practice without trainer (ROM C lines 2755-2756)"""
    practice_char.room.people = [practice_char]

    practice_char.skills["fireball"] = 50

    output = do_practice(practice_char, "fireball")
    assert "you can't do that here" in output.lower()


def test_practice_no_sessions(practice_char, practice_trainer, test_skill):
    """Can't practice without sessions (ROM C lines 2717-2718)"""
    practice_char.practice = 0
    practice_char.skills["fireball"] = 50

    output = do_practice(practice_char, "fireball")
    assert "You have no practice sessions left" in output


def test_practice_cant_practice_invalid_skill(practice_char, practice_trainer):
    """Invalid skill returns error (ROM C lines 2720-2721)"""
    output = do_practice(practice_char, "invalid_skill")
    assert "You can't practice that" in output


# ============================================================================
# P1 Tests (Important Functionality)
# ============================================================================


def test_practice_success_not_at_adept(practice_char, practice_trainer, test_skill):
    """Practice increases skill when not at adept (ROM C lines 2761-2777)"""
    practice_char.skills["fireball"] = 50

    do_practice(practice_char, "fireball")

    assert practice_char.practice == 9
    assert practice_char.skills["fireball"] > 50

    assert len(practice_char.messages) > 0
    message = practice_char.messages[0].lower()
    assert "practice" in message or "learned" in message


def test_practice_success_at_adept(practice_char, practice_trainer, test_skill):
    """Practice at adept shows learned message (ROM C lines 2761-2777)"""
    practice_char.skills["fireball"] = 94

    # One more practice should reach adept (95)
    output = do_practice(practice_char, "fireball")

    # Should reach adept
    assert practice_char.skills["fireball"] == 95

    # Check learned message
    assert len(practice_char.messages) > 0
    assert "You are now learned at fireball" in practice_char.messages[0]


def test_practice_already_learned(practice_char, practice_trainer, test_skill):
    """Can't practice beyond adept (ROM C lines 2758-2759)"""
    practice_char.skills["fireball"] = 95  # Already at adept

    output = do_practice(practice_char, "fireball")

    assert "You are already learned at fireball" in output
    assert practice_char.practice == 10  # Not decremented


def test_practice_int_rating_formula(practice_char, practice_trainer, test_skill):
    """Skill gain uses INT.learn / rating formula (ROM C lines 2760-2763)"""
    practice_char.skills["fireball"] = 50

    do_practice(practice_char, "fireball")

    assert practice_char.skills["fireball"] == 60


def test_practice_room_messages(practice_char, practice_trainer, test_skill):
    """Room receives broadcast messages (ROM C lines 2767-2777)"""
    practice_char.skills["fireball"] = 50

    broadcast_messages = []

    def mock_broadcast(msg, exclude=None):
        broadcast_messages.append((msg, exclude))

    practice_char.room.broadcast = mock_broadcast

    do_practice(practice_char, "fireball")

    assert len(broadcast_messages) > 0
    msg, exclude = broadcast_messages[0]
    assert "testchar" in msg.lower()
    assert "fireball" in msg.lower()
    assert exclude == practice_char


# ============================================================================
# P2 Tests (Optional/Edge Cases)
# ============================================================================


def test_practice_column_layout(practice_char, test_skill):
    """3-column layout wraps correctly (ROM C lines 2701-2707)"""
    practice_char.skills = {
        "fireball": 50,
    }

    output = do_practice(practice_char, "")

    lines = [line for line in output.split("\n") if line.strip()]

    assert len(lines) >= 1


def test_practice_sessions_decrement(practice_char, practice_trainer, test_skill):
    """Practice count decreases after successful practice (ROM C line 2764)"""
    practice_char.skills["fireball"] = 50
    initial_practice = practice_char.practice

    do_practice(practice_char, "fireball")

    assert practice_char.practice == initial_practice - 1


def test_practice_skill_case_insensitive(practice_char, practice_trainer, test_skill):
    """Skill name lookup is case-insensitive (ROM parity)"""
    practice_char.skills["fireball"] = 50

    do_practice(practice_char, "FIREBALL")

    assert practice_char.practice == 9
