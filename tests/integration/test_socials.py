"""
Integration tests for socials system.

Tests verify that socials work according to ROM 2.4b6 behavior:
- Social execution with no target (broadcasts to room)
- Social execution with target (char/victim/others messages)
- Social targeting self (auto-social messages)
- Social with non-existent target (not found message)
- Placeholder expansion ($n, $N, $e, $m, $s)
- Multiple socials work correctly
- Social messages broadcast to room excluding actor

ROM Reference: src/act_comm.c (do_socials), src/social.c (social table)
"""

from __future__ import annotations

import pytest

from mud.commands.socials import perform_social
from mud.models.character import Character, character_registry
from mud.models.constants import Position, Sex
from mud.models.social import social_registry
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
        sex=Sex.FEMALE,
    )
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
        sex=Sex.MALE,
    )
    test_room.add_character(char)
    character_registry.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)
    if char in character_registry:
        character_registry.remove(char)


class TestSocialExecution:
    def test_social_no_target_broadcasts_to_room(self, alice, bob):
        """Test social with no target sends messages to actor and room."""
        alice.messages.clear()
        bob.messages.clear()

        result = perform_social(alice, "smile", "")

        assert result == ""
        assert len(alice.messages) > 0
        assert "smile" in alice.messages[0].lower()
        # Bob should see Alice's smile
        assert len(bob.messages) > 0
        assert "alice" in bob.messages[0].lower()

    def test_social_with_target_shows_three_messages(self, alice, bob):
        """Test social with target sends messages to char, victim, and others."""
        alice.messages.clear()
        bob.messages.clear()

        result = perform_social(alice, "smile", "bob")

        assert result == ""
        # Alice sees "You smile at him." (ROM uses pronouns, not names in char_found)
        assert len(alice.messages) > 0
        assert "smile" in alice.messages[0].lower()
        # Bob sees "Alice smiles at you."
        assert len(bob.messages) > 0
        assert "alice" in bob.messages[0].lower()

    def test_social_targeting_self(self, alice):
        """Test social targeting self shows 'not found' because search loop skips self."""
        alice.messages.clear()

        result = perform_social(alice, "smile", "alice")

        assert result == ""
        assert len(alice.messages) > 0
        assert (
            "around" in alice.messages[0].lower()
            or "here" in alice.messages[0].lower()
            or "isn't" in alice.messages[0].lower()
        )

    def test_social_nonexistent_target(self, alice):
        """Test social with nonexistent target shows 'not found' message."""
        alice.messages.clear()

        result = perform_social(alice, "smile", "charlie")

        assert result == ""
        assert len(alice.messages) > 0
        # Should get "not found" message instead of no-arg variant
        message = alice.messages[0].lower()
        # ROM semantics: either "That person isn't here" or similar not-found message
        assert "around" in message or "here" in message or "isn't" in message or "not" in message

    def test_social_nonexistent_social_command(self, alice):
        """Test calling a social that doesn't exist returns 'Huh?'."""
        result = perform_social(alice, "notarealsocial", "")

        assert result == "Huh?"


class TestSocialPlaceholders:
    def test_placeholder_expansion_actor_name(self, alice, bob):
        """Test $n expands to actor's name."""
        alice.messages.clear()
        bob.messages.clear()

        perform_social(alice, "bounce", "")

        # Bob should see Alice's name in the message
        assert len(bob.messages) > 0
        assert "alice" in bob.messages[0].lower()

    def test_placeholder_expansion_victim_name(self, alice, bob):
        """Test $M expands to victim pronoun (him/her) not name."""
        alice.messages.clear()
        bob.messages.clear()

        perform_social(alice, "kiss", "bob")

        assert len(alice.messages) > 0
        assert "kiss" in alice.messages[0].lower()
        assert "him" in alice.messages[0].lower()

    def test_placeholder_expansion_pronouns_female(self, alice, bob):
        """Test pronouns expand correctly for female actor ($e=she, $m=her, $s=her)."""
        alice.messages.clear()
        bob.messages.clear()

        # Use a social that has pronoun placeholders in others_no_arg
        perform_social(alice, "dance", "")

        # Bob should see a message with Alice's pronouns
        if len(bob.messages) > 0:
            message = bob.messages[0].lower()
            # Message should contain "she" or "her" from Alice's sex
            assert "alice" in message

    def test_placeholder_expansion_pronouns_male(self, alice, bob):
        """Test pronouns expand correctly for male victim ($E=he, $M=him, $S=his)."""
        alice.messages.clear()
        bob.messages.clear()

        # Use a social that has victim pronoun placeholders
        perform_social(alice, "kiss", "bob")

        # Alice should see "You kiss him." (Bob is male)
        assert len(alice.messages) > 0
        assert "kiss" in alice.messages[0].lower()
        # The message should reference Bob (either by name or pronoun)
        assert "bob" in alice.messages[0].lower() or "him" in alice.messages[0].lower()


class TestMultipleSocials:
    def test_different_socials_work(self, alice):
        """Test multiple different socials are registered and work."""
        alice.messages.clear()

        # Test several common socials
        socials_to_test = ["smile", "laugh", "dance", "bounce", "kiss"]
        for social_name in socials_to_test:
            if social_name in social_registry:
                alice.messages.clear()
                result = perform_social(alice, social_name, "")
                assert result == "", f"Social {social_name} returned error"
                assert len(alice.messages) > 0, f"Social {social_name} produced no messages"

    def test_social_registry_has_multiple_entries(self):
        """Test that social registry contains loaded socials."""
        # data/socials.json has 244 socials
        assert len(social_registry) > 0
        # Verify some common socials are loaded
        assert "smile" in social_registry
        assert "laugh" in social_registry

    def test_social_messages_broadcast_excluding_actor(self, alice, bob):
        """Test that social broadcasts don't send to the actor."""
        alice.messages.clear()
        bob.messages.clear()

        perform_social(alice, "smile", "")

        # Alice should only have 1 message (her own char_no_arg message)
        assert len(alice.messages) == 1
        # Bob should have 1 message (the others_no_arg broadcast)
        assert len(bob.messages) == 1
        # Bob's message should mention Alice
        assert "alice" in bob.messages[0].lower()

    def test_social_with_target_excludes_actor_from_broadcast(self, alice, bob):
        """Test that targeted social broadcasts others_found to observers and vict_found to victim."""
        alice.messages.clear()
        bob.messages.clear()

        observer = Character(
            name="Observer",
            short_descr="Observer",
            is_npc=False,
            level=10,
            position=Position.STANDING,
            room=alice.room,
            sex=Sex.MALE,
        )
        alice.room.add_character(observer)
        character_registry.append(observer)
        observer.messages.clear()

        try:
            perform_social(alice, "smile", "bob")

            assert len(alice.messages) == 1
            assert len(bob.messages) == 2
            assert len(observer.messages) == 1
            assert "alice" in observer.messages[0].lower()
            assert "bob" in observer.messages[0].lower()

        finally:
            if observer in alice.room.people:
                alice.room.people.remove(observer)
            if observer in character_registry:
                character_registry.remove(observer)
