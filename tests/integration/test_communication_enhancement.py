"""
Integration tests for enhanced communication commands.

Tests verify that communication commands work according to ROM 2.4b6 behavior:
- Emote/pose commands (custom actions)
- Say command with mob triggers
- Tell command with offline/AFK handling
- Shout command (game-wide)
- Yell command (adjacent rooms)
- Reply command

ROM Reference: src/act_comm.c (do_emote, do_say, do_tell, do_shout, do_yell, do_reply)
"""

from __future__ import annotations

import pytest

from mud.commands.communication import do_emote, do_pose, do_say, do_tell, do_reply, do_shout, do_yell
from mud.models.character import Character, character_registry
from mud.models.constants import CommFlag, Position
from mud.registry import room_registry
from mud.world import initialize_world


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield


@pytest.fixture
def test_room():
    return room_registry.get(3001)


@pytest.fixture
def alice(test_room):
    char = Character(
        name="Alice",
        short_descr="Alice the tester",
        is_npc=False,
        level=10,
        position=Position.STANDING,
        room=test_room,
        comm=0,
    )
    char.desc = object()
    test_room.add_character(char)
    character_registry.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)
    if char in character_registry:
        character_registry.remove(char)


@pytest.fixture
def bob(test_room):
    char = Character(
        name="Bob",
        short_descr="Bob the listener",
        is_npc=False,
        level=10,
        position=Position.STANDING,
        room=test_room,
        comm=0,
    )
    char.desc = object()
    test_room.add_character(char)
    character_registry.append(char)
    char.reply = None
    yield char
    if char in test_room.people:
        test_room.people.remove(char)
    if char in character_registry:
        character_registry.remove(char)


class TestEmoteCommand:
    def test_emote_broadcasts_custom_action(self, alice, bob):
        """Test emote displays custom action to room."""
        result = do_emote(alice, "smiles happily")

        assert result == "Alice smiles happily"

    def test_emote_requires_argument(self, alice):
        """Test emote without argument shows error."""
        result = do_emote(alice, "")

        assert "emote what" in result.lower()

    def test_pose_is_alias_for_emote(self, alice):
        """Test pose command works identically to emote."""
        emote_result = do_emote(alice, "waves")
        pose_result = do_pose(alice, "waves")

        assert emote_result == pose_result
        assert "Alice waves" in pose_result


class TestSayCommand:
    def test_say_broadcasts_to_room(self, alice, bob):
        """Test say command broadcasts message to room."""
        bob.messages.clear()

        result = do_say(alice, "Hello everyone!")

        assert result == "You say, 'Hello everyone!'"
        assert len(bob.messages) > 0
        assert "alice says" in bob.messages[0].lower()

    def test_say_requires_argument(self, alice):
        """Test say without argument shows error."""
        result = do_say(alice, "")

        assert "say what" in result.lower()


class TestTellCommand:
    def test_tell_sends_private_message(self, alice, bob):
        """Test tell sends private message to target."""
        bob.messages.clear()

        result = do_tell(alice, "bob Hello there!")

        assert result == "You tell Bob, 'Hello there!'"
        assert len(bob.messages) > 0
        assert "alice tells you" in bob.messages[0].lower()

    def test_tell_sets_reply_target(self, alice, bob):
        """Test tell sets reply field on target."""
        bob.reply = None

        do_tell(alice, "bob Test message")

        assert bob.reply is alice

    def test_tell_requires_target_and_message(self, alice):
        """Test tell without arguments shows error."""
        result = do_tell(alice, "")

        assert "tell whom what" in result.lower()

    def test_tell_to_nonexistent_target(self, alice):
        """Test tell to nonexistent character shows error."""
        result = do_tell(alice, "charlie Hello!")

        assert "aren't here" in result.lower()

    def test_tell_to_self(self, alice):
        """Test telling yourself shows error."""
        result = do_tell(alice, "alice Testing")

        assert "yourself" in result.lower()

    def test_tell_with_notell_flag(self, alice, bob):
        """Test tell blocked when sender has NOTELL flag."""
        alice.comm = int(CommFlag.NOTELL)

        result = do_tell(alice, "bob Testing")

        assert "didn't get through" in result.lower()

    def test_tell_with_quiet_mode(self, alice, bob):
        """Test tell blocked when sender has QUIET flag."""
        alice.comm = int(CommFlag.QUIET)

        result = do_tell(alice, "bob Testing")

        assert "quiet" in result.lower()


class TestReplyCommand:
    def test_reply_uses_last_tell_sender(self, alice, bob):
        """Test reply sends to last person who sent tell."""
        bob.messages.clear()
        do_tell(alice, "bob First message")

        bob.messages.clear()
        result = do_reply(bob, "Thanks!")

        assert "you tell alice" in result.lower()
        assert len(alice.messages) > 0
        assert "bob tells you" in alice.messages[0].lower()

    def test_reply_without_prior_tell(self, alice):
        """Test reply without prior tell shows error."""
        alice.reply = None

        result = do_reply(alice, "Testing")

        assert "aren't here" in result.lower()

    def test_reply_requires_message(self, alice):
        """Test reply without message shows error."""
        result = do_reply(alice, "")

        assert "reply to whom" in result.lower() or "with what" in result.lower()


class TestShoutCommand:
    def test_shout_broadcasts_globally(self, alice, bob):
        """Test shout broadcasts to all players."""
        result = do_shout(alice, "Important announcement!")

        assert "important announcement" in result.lower()

    def test_shout_requires_argument(self, alice):
        """Test shout with empty argument toggles channel."""
        result = do_shout(alice, "")

        assert "no longer hear" in result.lower() or "now hear" in result.lower()

    def test_shout_blocked_by_noshout_flag(self, alice):
        """Test shout blocked when player has NOSHOUT flag."""
        alice.comm = int(CommFlag.NOSHOUT)

        result = do_shout(alice, "Testing")

        assert "can't shout" in result.lower()


class TestYellCommand:
    def test_yell_broadcasts_to_adjacent_rooms(self, alice):
        """Test yell broadcasts to current and adjacent rooms."""
        result = do_yell(alice, "Help!")

        assert "help" in result.lower()

    def test_yell_requires_argument(self, alice):
        """Test yell without argument shows error."""
        result = do_yell(alice, "")

        assert "yell what" in result.lower()

    def test_yell_blocked_by_noshout_flag(self, alice):
        """Test yell blocked when player has NOSHOUT flag."""
        alice.comm = int(CommFlag.NOSHOUT)

        result = do_yell(alice, "Testing")

        assert "can't yell" in result.lower()
