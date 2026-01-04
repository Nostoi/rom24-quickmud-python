"""Integration tests for do_password command (act_info.c:2833-2925).

Tests complete workflows for changing passwords with ROM 2.4b6 parity.

ROM Parity: src/act_info.c lines 2833-2925 (do_password)
"""

from __future__ import annotations

import pytest

from mud.account.account_manager import save_character
from mud.commands.character import do_password
from mud.models.character import Character, PCData
from mud.models.room import Room
from mud.registry import room_registry
from mud.security.hash_utils import hash_password, verify_password


@pytest.fixture
def password_room():
    """Create a test room"""
    room = Room(
        vnum=6000,
        name="Password Test Room",
        description="A room for testing password changes.",
        room_flags=0,
        sector_type=0,
    )
    room.people = []
    room.contents = []
    room_registry[6000] = room
    yield room
    room_registry.pop(6000, None)


@pytest.fixture
def password_char(password_room):
    """Create a test character with password set"""
    char = Character(
        name="TestChar",
        level=5,
        room=password_room,
        is_npc=False,
        hit=100,
        max_hit=100,
    )

    char.pcdata = PCData()
    char.pcdata.pwd = hash_password("oldpassword")

    char.messages = []
    char.wait = 0

    password_room.people.append(char)
    yield char
    if char in password_room.people:
        password_room.people.remove(char)


# ============================================================================
# P0 Tests (Critical Functionality)
# ============================================================================


def test_password_npc_returns_empty(password_room):
    """NPCs can't change password (ROM C line 2835-2836)"""
    npc = Character(
        name="test mob",
        level=5,
        room=password_room,
        is_npc=True,
        hit=50,
        max_hit=50,
    )

    output = do_password(npc, "old new")
    assert output == ""


def test_password_missing_args(password_char):
    """Missing arguments shows syntax error (ROM C lines 2859-2870)"""
    output = do_password(password_char, "")
    assert "Syntax: password <old> <new>" in output

    output = do_password(password_char, "onlyonearg")
    assert "Syntax: password <old> <new>" in output


def test_password_wrong_old(password_char):
    """Wrong old password returns error (ROM C lines 2890-2895)"""
    output = do_password(password_char, "wrongpassword newpassword")
    assert "Wrong password" in output


def test_password_wait_state_penalty(password_char):
    """Wrong password sets 10-second WAIT_STATE (ROM C lines 2893-2894)"""
    password_char.wait = 0

    output = do_password(password_char, "wrongpassword newpassword")

    assert password_char.wait == 40


def test_password_too_short(password_char):
    """New password must be at least 5 characters (ROM C lines 2897-2904)"""
    output = do_password(password_char, "oldpassword tiny")
    assert "at least five characters long" in output


def test_password_success(password_char, monkeypatch):
    """Password changed and saved successfully (ROM C lines 2916-2922)"""
    save_called = []

    def mock_save(ch):
        save_called.append(ch)

    monkeypatch.setattr("mud.commands.character.save_character", mock_save)

    output = do_password(password_char, "oldpassword newpassword123")

    assert output == "Ok."
    assert len(save_called) == 1
    assert save_called[0] == password_char


def test_password_hashing(password_char, monkeypatch):
    """New password is hashed, not stored in plaintext (ROM C line 2905)"""

    def mock_save(ch):
        pass

    monkeypatch.setattr("mud.commands.character.save_character", mock_save)

    old_pwd = password_char.pcdata.pwd

    do_password(password_char, "oldpassword newpassword123")

    new_pwd = password_char.pcdata.pwd

    assert new_pwd != "newpassword123"
    assert new_pwd != old_pwd
    assert verify_password("newpassword123", new_pwd)
    assert not verify_password("oldpassword", new_pwd)


def test_password_persistence(password_char, monkeypatch):
    """Character is saved to disk after password change (ROM C line 2916)"""
    save_called = []

    def mock_save(ch):
        save_called.append(ch)

    monkeypatch.setattr("mud.commands.character.save_character", mock_save)

    do_password(password_char, "oldpassword newpassword123")

    assert len(save_called) == 1, "save_character should be called exactly once"


# ============================================================================
# P1 Tests (Important Functionality)
# ============================================================================


def test_password_tilde_rejection(password_char, monkeypatch):
    """Tilde in hashed password causes rejection (ROM C lines 2906-2912)"""

    def mock_hash(pwd):
        return "has~tilde"

    def mock_save(ch):
        pass

    monkeypatch.setattr("mud.commands.character.hash_password", mock_hash)
    monkeypatch.setattr("mud.commands.character.save_character", mock_save)

    output = do_password(password_char, "oldpassword newpassword123")

    assert "not acceptable" in output.lower()


def test_password_verification(password_char):
    """Old password must match current password (ROM C lines 2890-2895)"""
    initial_pwd = password_char.pcdata.pwd

    output = do_password(password_char, "wrongpassword newpassword123")

    assert "Wrong password" in output
    assert password_char.pcdata.pwd == initial_pwd


def test_password_case_sensitive(password_char, monkeypatch):
    """Passwords are case-sensitive (ROM parity)"""

    def mock_save(ch):
        pass

    monkeypatch.setattr("mud.commands.character.save_character", mock_save)

    output1 = do_password(password_char, "oldpassword newpassword123")
    assert output1 == "Ok."

    output2 = do_password(password_char, "OLDPASSWORD another")
    assert "Wrong password" in output2


# ============================================================================
# P2 Tests (Optional/Edge Cases)
# ============================================================================


def test_password_whitespace_handling(password_char, monkeypatch):
    """Leading/trailing whitespace is handled correctly"""

    def mock_save(ch):
        pass

    monkeypatch.setattr("mud.commands.character.save_character", mock_save)

    output = do_password(password_char, "  oldpassword   newpassword123  ")
    assert output == "Ok."


def test_password_save_failure_reverts(password_char, monkeypatch):
    """Save failure reverts password change"""

    def mock_save(ch):
        raise Exception("Database error")

    monkeypatch.setattr("mud.commands.character.save_character", mock_save)

    old_pwd = password_char.pcdata.pwd

    output = do_password(password_char, "oldpassword newpassword123")

    assert "Error saving password" in output
    assert password_char.pcdata.pwd == old_pwd


def test_password_no_pcdata(password_room):
    """Character without pcdata returns error"""
    char = Character(
        name="NoPCData",
        level=5,
        room=password_room,
        is_npc=False,
        hit=100,
        max_hit=100,
    )
    char.pcdata = None

    output = do_password(char, "old new")
    assert "Error" in output


def test_password_no_pwd_set(password_char):
    """Character without password set returns error"""
    password_char.pcdata.pwd = None

    output = do_password(password_char, "old new")
    assert "Error" in output
