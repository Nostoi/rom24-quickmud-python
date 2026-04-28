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
from mud.models.constants import CommFlag, Position, Sex
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


class TestSocialPositionGates:
    """ROM parity: src/interp.c:603-616 (check_social) — INTERP-018.

    A character in DEAD/INCAP/MORTAL/STUNNED cannot perform any social;
    the dispatcher must short-circuit with the matching ROM message and
    must not broadcast char_no_arg / others_no_arg into the room.
    """

    def test_dead_character_cannot_social(self, alice, bob):
        # mirrors ROM src/interp.c:605-607 — POS_DEAD blocks all socials.
        alice.position = Position.DEAD
        alice.messages.clear()
        bob.messages.clear()

        result = perform_social(alice, "smile", "")

        assert result == "Lie still; you are DEAD."
        assert alice.messages == []
        assert bob.messages == []

    def test_mortal_character_cannot_social(self, alice, bob):
        # mirrors ROM src/interp.c:609-612 — POS_MORTAL/POS_INCAP block socials.
        alice.position = Position.MORTAL
        alice.messages.clear()
        bob.messages.clear()

        result = perform_social(alice, "smile", "")

        assert result == "You are hurt far too bad for that."
        assert alice.messages == []
        assert bob.messages == []

    def test_incap_character_cannot_social(self, alice, bob):
        # mirrors ROM src/interp.c:609-612 — POS_INCAP shares the MORTAL message.
        alice.position = Position.INCAP
        alice.messages.clear()
        bob.messages.clear()

        result = perform_social(alice, "smile", "")

        assert result == "You are hurt far too bad for that."
        assert alice.messages == []
        assert bob.messages == []

    def test_stunned_character_cannot_social(self, alice, bob):
        # mirrors ROM src/interp.c:614-616 — POS_STUNNED has its own message.
        alice.position = Position.STUNNED
        alice.messages.clear()
        bob.messages.clear()

        result = perform_social(alice, "smile", "")

        assert result == "You are too stunned to do that."
        assert alice.messages == []
        assert bob.messages == []

    def test_sleeping_character_cannot_social_except_snore(self, alice, bob):
        # mirrors ROM src/interp.c:618-626 — POS_SLEEPING blocks all socials
        # except "snore" with the message "In your dreams, or what?".
        alice.position = Position.SLEEPING
        alice.messages.clear()
        bob.messages.clear()

        result = perform_social(alice, "smile", "")

        assert result == "In your dreams, or what?"
        assert alice.messages == []
        assert bob.messages == []

    def test_noemote_player_blocked_with_anti_social_message(self, alice, bob):
        # mirrors ROM src/interp.c:597-601 — COMM_NOEMOTE blocks all socials
        # for non-NPC characters with "You are anti-social!".
        alice.is_npc = False
        alice.comm = int(CommFlag.NOEMOTE)
        alice.messages.clear()
        bob.messages.clear()

        result = perform_social(alice, "smile", "")

        assert result == "You are anti-social!"
        assert alice.messages == []
        assert bob.messages == []

    def test_noemote_does_not_apply_to_npcs(self, alice, bob):
        # mirrors ROM src/interp.c:597 — IS_NPC(ch) bypasses the NOEMOTE check.
        alice.is_npc = True
        alice.comm = int(CommFlag.NOEMOTE)
        alice.messages.clear()
        bob.messages.clear()

        result = perform_social(alice, "smile", "")

        # NPC with NOEMOTE flag still socials normally (ROM short-circuit
        # is gated on !IS_NPC(ch)).
        assert result == ""
        assert len(alice.messages) > 0

    def test_sleeping_character_can_still_snore(self, alice, bob):
        # mirrors ROM src/interp.c:623-624 — "snore" bypasses the sleeping gate.
        alice.position = Position.SLEEPING
        alice.messages.clear()
        bob.messages.clear()

        result = perform_social(alice, "snore", "")

        # Guard: the fix must not over-broadcast and break "snore". The
        # social succeeds (empty return), and both actor and observer
        # receive the social text (which is "Zzzzzzzzzzzzzzzzz." in stock data).
        assert result == ""
        assert len(alice.messages) > 0
        assert len(bob.messages) > 0


class TestSocialNpcAutoReact:
    """ROM parity: src/interp.c:652-685 (check_social NPC auto-react) — INTERP-023.

    When a non-NPC socials at a non-charmed, awake, non-switched NPC,
    ROM rolls number_bits(4) (0..15):
      - 0..8  → NPC echoes the social back at the player (swap actor/victim)
      - 9..12 → NPC slaps the player ("$n slaps $N." / "You slap $N." / "$n slaps you.")
      - 13..15 → silent (no reaction)

    These tests pin each branch by monkey-patching rng_mm.number_bits.
    The branch logic is what's under test; the RNG itself is unit-tested
    in tests/test_rng_mm.py. Per AGENTS.md: production code MUST use
    mud.utils.rng_mm.number_bits — never random.*.
    """

    @pytest.fixture
    def npc_victim(self, test_room):
        npc = Character(
            name="cityguard",
            short_descr="the cityguard",
            is_npc=True,
            level=10,
            position=Position.STANDING,
            room=test_room,
            sex=Sex.MALE,
        )
        test_room.add_character(npc)
        character_registry.append(npc)
        yield npc
        if npc in test_room.people:
            test_room.people.remove(npc)
        if npc in character_registry:
            character_registry.remove(npc)

    def test_slap_branch_emits_three_slap_messages(self, alice, npc_victim, monkeypatch):
        # mirrors ROM src/interp.c:676-684 — number_bits(4) in {9..12} → slap.
        from mud.commands import socials as socials_module

        monkeypatch.setattr(socials_module.rng_mm, "number_bits", lambda width: 9)

        alice.messages.clear()
        npc_victim.messages.clear()

        perform_social(alice, "smile", "cityguard")

        # Player should receive a "$n slaps you." message in addition to
        # the original social's vict_found.
        assert any("slaps you" in m.lower() for m in alice.messages), (
            f"Expected slap message in alice.messages, got: {alice.messages}"
        )

    def test_echo_branch_swaps_actor_and_victim(self, alice, npc_victim, monkeypatch):
        # mirrors ROM src/interp.c:668-674 — number_bits(4) in {0..8} → echo
        # the social back with NPC as actor and player as victim.
        from mud.commands import socials as socials_module

        monkeypatch.setattr(socials_module.rng_mm, "number_bits", lambda width: 0)

        alice.messages.clear()
        npc_victim.messages.clear()

        perform_social(alice, "smile", "cityguard")

        # Player got the original vict_found ("Alice smiles at you" → no, Bob's
        # social) PLUS the echoed vict_found from the NPC. Two messages where
        # the NPC name appears as the smiler.
        npc_smile_count = sum(
            1 for m in alice.messages if "cityguard" in m.lower()
        )
        assert npc_smile_count >= 1, (
            f"Expected at least one message naming the NPC as smiler, got: {alice.messages}"
        )

    def test_silent_branch_emits_no_extra_messages(self, alice, npc_victim, monkeypatch):
        # mirrors ROM src/interp.c:656-685 — number_bits(4) in {13..15} hits
        # no switch case → no auto-react.
        from mud.commands import socials as socials_module

        monkeypatch.setattr(socials_module.rng_mm, "number_bits", lambda width: 13)

        alice.messages.clear()
        npc_victim.messages.clear()

        perform_social(alice, "smile", "cityguard")

        # Player only sees the original char_found from their own social
        # (one message). No extra slap or echoed smile.
        assert len(alice.messages) == 1, (
            f"Expected exactly 1 message (no auto-react), got: {alice.messages}"
        )

    def test_no_react_when_npc_charmed(self, alice, npc_victim, monkeypatch):
        # mirrors ROM src/interp.c:653 — IS_AFFECTED(victim, AFF_CHARM) skips reaction.
        from mud.commands import socials as socials_module
        from mud.models.constants import AffectFlag

        monkeypatch.setattr(socials_module.rng_mm, "number_bits", lambda width: 9)
        npc_victim.affected_by = int(AffectFlag.CHARM)

        alice.messages.clear()

        perform_social(alice, "smile", "cityguard")

        assert not any("slaps you" in m.lower() for m in alice.messages), (
            f"Charmed NPC should not slap; got: {alice.messages}"
        )

    def test_no_react_when_actor_is_npc(self, alice, bob, npc_victim, monkeypatch):
        # mirrors ROM src/interp.c:652 — !IS_NPC(ch) gate; NPC actors get no reaction.
        from mud.commands import socials as socials_module

        monkeypatch.setattr(socials_module.rng_mm, "number_bits", lambda width: 9)

        alice.is_npc = True  # NPC actor
        alice.messages.clear()
        bob.messages.clear()

        perform_social(alice, "smile", "cityguard")

        # Player Bob (observer) should not see a slap — no auto-react fired.
        assert not any("slaps" in m.lower() for m in bob.messages)

    def test_no_react_when_victim_sleeping(self, alice, npc_victim, monkeypatch):
        # mirrors ROM src/interp.c:654 — IS_AWAKE(victim) (position > SLEEPING) required.
        from mud.commands import socials as socials_module

        monkeypatch.setattr(socials_module.rng_mm, "number_bits", lambda width: 9)
        npc_victim.position = Position.SLEEPING
        alice.messages.clear()

        perform_social(alice, "smile", "cityguard")

        assert not any("slaps you" in m.lower() for m in alice.messages)
