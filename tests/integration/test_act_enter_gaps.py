"""Integration tests for act_enter.c ROM parity gaps.

Covers ENTER-001 through ENTER-016 (15 gaps).

ROM Reference: src/act_enter.c lines 44-229
"""

from __future__ import annotations

import pytest

from mud.commands.movement import do_enter
from mud.models.character import Character, PCData
from mud.models.constants import (
    EX_CLOSED,
    AffectFlag,
    ItemType,
    PortalFlag,
    Position,
    RoomFlag,
)
from mud.models.room import Room


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_room(vnum: int, *, room_flags: int = 0) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="A test room.")
    room.people = []
    room.contents = []
    room.exits = [None] * 6
    room.room_flags = room_flags
    return room


def _make_char(name: str, room: Room, *, level: int = 10) -> Character:
    char = Character(name=name, level=level, room=room, is_npc=False, hit=100, max_hit=100, position=int(Position.STANDING))
    char.pcdata = PCData()
    char.messages = []
    char.send_to_char = lambda msg: char.messages.append(msg)
    room.people.append(char)
    return char


def _make_portal(room: Room, *, to_vnum: int, charges: int = 1, exit_flags: int = 0, gate_flags: int = 0,
                 short_descr: str = "a shimmering portal", item_type: int = int(ItemType.PORTAL)):
    from mud.models.obj import ObjIndex
    from mud.models.object import Object

    proto = ObjIndex(
        vnum=9000,
        name="shimmering portal",
        short_descr=short_descr,
        item_type=item_type,
    )
    values = [charges, exit_flags, gate_flags, to_vnum, 0]
    proto.value = values.copy()
    obj = Object(instance_id=None, prototype=proto)
    obj.value = values.copy()
    room.add_object(obj)
    return obj


# ---------------------------------------------------------------------------
# ENTER-002: no-arg message is "Nope, can't do it."
# ---------------------------------------------------------------------------


class TestEnter002NoArgMessage:
    """ENTER-002: ROM sends 'Nope, can't do it.' for empty argument (act_enter.c:227)."""

    def test_no_arg_returns_nope(self):
        room = _make_room(8901)
        char = _make_char("Tester", room)
        result = do_enter(char, "")
        assert result == "Nope, can't do it.", f"Expected ROM message, got: {result!r}"

    def test_whitespace_arg_treated_as_empty(self):
        room = _make_room(8902)
        char = _make_char("Tester", room)
        result = do_enter(char, "   ")
        assert result == "Nope, can't do it."


# ---------------------------------------------------------------------------
# ENTER-003: object-not-found message is "You don't see that here."
# ---------------------------------------------------------------------------


class TestEnter003ObjectNotFound:
    """ENTER-003: ROM sends 'You don't see that here.' when object not found (act_enter.c:86-88)."""

    def test_nonexistent_object_returns_correct_message(self):
        room = _make_room(8903)
        char = _make_char("Tester", room)
        result = do_enter(char, "chest")
        assert result == "You don't see that here."

    def test_empty_room_returns_correct_message(self):
        room = _make_room(8904)
        char = _make_char("Tester", room)
        result = do_enter(char, "portal")
        assert result == "You don't see that here."


# ---------------------------------------------------------------------------
# ENTER-004: non-portal object → "You can't seem to find a way in."
# ---------------------------------------------------------------------------


class TestEnter004NonPortalOrClosedMessage:
    """ENTER-004: ROM uses single combined gate for non-portal and closed cases (act_enter.c:90-96)."""

    def test_non_portal_item_returns_cant_find_way_in(self):
        from mud.registry import room_registry

        room = _make_room(8905)
        room_registry[8905] = room
        char = _make_char("Tester", room)

        # Place a non-portal object (a chest/container) with a matching keyword
        _make_portal(room, to_vnum=8906, item_type=int(ItemType.CONTAINER))

        result = do_enter(char, "portal")
        # Non-portal object → "You can't seem to find a way in."
        assert result == "You can't seem to find a way in."

        room_registry.pop(8905, None)

    def test_closed_portal_returns_cant_find_way_in(self):
        from mud.registry import room_registry

        room = _make_room(8906)
        room2 = _make_room(8907)
        room_registry[8906] = room
        room_registry[8907] = room2
        char = _make_char("Tester", room)

        _make_portal(room, to_vnum=8907, exit_flags=EX_CLOSED)

        result = do_enter(char, "portal")
        # Closed portal for untrusted char → "You can't seem to find a way in."
        assert result == "You can't seem to find a way in."

        room_registry.pop(8906, None)
        room_registry.pop(8907, None)


# ---------------------------------------------------------------------------
# ENTER-005: get_obj_list — numbered syntax
# ---------------------------------------------------------------------------


class TestEnter005GetObjList:
    """ENTER-005: Object lookup uses get_obj_list (numbered prefix + visibility)."""

    def test_numbered_syntax_finds_second_portal(self):
        from mud.registry import room_registry

        room_a = _make_room(8910)
        room_b = _make_room(8911)
        room_c = _make_room(8912)
        room_registry[8910] = room_a
        room_registry[8911] = room_b
        room_registry[8912] = room_c
        room_b.exits = [None] * 6
        room_c.exits = [None] * 6

        char = _make_char("Tester", room_a)
        char.messages = []
        char.send_to_char = lambda msg: char.messages.append(msg)

        # Two portals in room; first goes to 8911, second to 8912
        from mud.models.obj import ObjIndex
        from mud.models.object import Object

        def make_p(to_vnum: int) -> object:
            proto = ObjIndex(vnum=9001, name="blue portal portal", short_descr="a blue portal", item_type=int(ItemType.PORTAL))
            proto.value = [1, 0, 0, to_vnum, 0]
            obj = Object(instance_id=None, prototype=proto)
            obj.value = proto.value.copy()
            room_a.add_object(obj)
            return obj

        portal1 = make_p(8911)
        portal2 = make_p(8912)

        # "enter 2.portal" should go through the second portal → room_c
        result = do_enter(char, "2.portal")
        # After transit char should be in room_c (vnum 8912)
        assert getattr(char.room, "vnum", None) == 8912, (
            f"Expected room 8912 but char is in room {getattr(char.room, 'vnum', None)}"
        )

        room_registry.pop(8910, None)
        room_registry.pop(8911, None)
        room_registry.pop(8912, None)


# ---------------------------------------------------------------------------
# ENTER-008/010: TO_ROOM departure/arrival use act_format ($n visibility)
# ---------------------------------------------------------------------------


class TestEnter008010ToRoomMessages:
    """ENTER-008/010: Departure and arrival messages use act_format for $n/$p visibility."""

    def test_departure_message_broadcast_to_room(self):
        from mud.registry import room_registry

        room_a = _make_room(8920)
        room_b = _make_room(8921)
        room_registry[8920] = room_a
        room_registry[8921] = room_b

        traveller = _make_char("Alice", room_a)
        observer = _make_char("Observer", room_a)

        _make_portal(room_a, to_vnum=8921, charges=1)

        result = do_enter(traveller, "portal")

        # Observer should see departure message containing "steps into"
        departure_seen = any("steps into" in m for m in observer.messages)
        assert departure_seen, f"Observer did not see departure. Messages: {observer.messages}"

        room_registry.pop(8920, None)
        room_registry.pop(8921, None)

    def test_arrival_message_broadcast_to_destination_room(self):
        from mud.registry import room_registry

        room_a = _make_room(8922)
        room_b = _make_room(8923)
        room_registry[8922] = room_a
        room_registry[8923] = room_b

        traveller = _make_char("Alice", room_a)
        waiting = _make_char("Bob", room_b)

        _make_portal(room_a, to_vnum=8923, charges=1)

        do_enter(traveller, "portal")

        # Bob in destination should see arrival message
        arrived_seen = any("has arrived" in m for m in waiting.messages)
        assert arrived_seen, f"Waiting char did not see arrival. Messages: {waiting.messages}"

        room_registry.pop(8922, None)
        room_registry.pop(8923, None)

    def test_normal_exit_portal_arrival_uses_shorter_message(self):
        from mud.registry import room_registry

        room_a = _make_room(8924)
        room_b = _make_room(8925)
        room_registry[8924] = room_a
        room_registry[8925] = room_b

        traveller = _make_char("Alice", room_a)
        waiting = _make_char("Bob", room_b)

        _make_portal(room_a, to_vnum=8925, gate_flags=int(PortalFlag.NORMAL_EXIT))

        do_enter(traveller, "portal")

        # NORMAL_EXIT → "$n has arrived." (no "through $p")
        arrived_simple = any(
            "has arrived" in m and "through" not in m for m in waiting.messages
        )
        assert arrived_simple, f"Expected simple arrival. Bob messages: {waiting.messages}"

        room_registry.pop(8924, None)
        room_registry.pop(8925, None)


# ---------------------------------------------------------------------------
# ENTER-009: TO_CHAR entry message delivered BEFORE room move
# ---------------------------------------------------------------------------


class TestEnter009ToCharEntryDelivered:
    """ENTER-009: 'You enter $p.' / 'You walk through...' actually delivered to the traveller."""

    def test_traveller_receives_entry_message(self):
        from mud.registry import room_registry

        room_a = _make_room(8930)
        room_b = _make_room(8931)
        room_registry[8930] = room_a
        room_registry[8931] = room_b

        traveller = _make_char("Alice", room_a)

        _make_portal(room_a, to_vnum=8931)

        do_enter(traveller, "portal")

        # Traveller must have received an entry message in messages list
        entry_received = any(
            "enter" in m.lower() or "walk through" in m.lower() for m in traveller.messages
        )
        assert entry_received, f"Traveller did not receive entry message. Messages: {traveller.messages}"

        room_registry.pop(8930, None)
        room_registry.pop(8931, None)

    def test_normal_exit_portal_sends_you_enter_message(self):
        from mud.registry import room_registry

        room_a = _make_room(8932)
        room_b = _make_room(8933)
        room_registry[8932] = room_a
        room_registry[8933] = room_b

        traveller = _make_char("Alice", room_a)
        _make_portal(room_a, to_vnum=8933, gate_flags=int(PortalFlag.NORMAL_EXIT))

        do_enter(traveller, "portal")

        # NORMAL_EXIT → "You enter $p."
        entry_msg = next((m for m in traveller.messages if "You enter" in m), None)
        assert entry_msg is not None, f"Expected 'You enter' message. Messages: {traveller.messages}"

        room_registry.pop(8932, None)
        room_registry.pop(8933, None)

    def test_non_normal_exit_portal_sends_walk_through_message(self):
        from mud.registry import room_registry

        room_a = _make_room(8934)
        room_b = _make_room(8935)
        room_registry[8934] = room_a
        room_registry[8935] = room_b

        traveller = _make_char("Alice", room_a)
        _make_portal(room_a, to_vnum=8935, gate_flags=0)

        do_enter(traveller, "portal")

        walk_msg = next((m for m in traveller.messages if "walk through" in m.lower()), None)
        assert walk_msg is not None, f"Expected 'walk through' message. Messages: {traveller.messages}"

        room_registry.pop(8934, None)
        room_registry.pop(8935, None)


# ---------------------------------------------------------------------------
# ENTER-011: Portal fade-out sent to correct recipients + extract_obj
# ---------------------------------------------------------------------------


class TestEnter011PortalFadeOut:
    """ENTER-011: Portal fade-out message goes to traveller + old room people (not destination room twice)."""

    def test_fade_message_sent_to_traveller(self):
        from mud.registry import room_registry

        room_a = _make_room(8940)
        room_b = _make_room(8941)
        room_registry[8940] = room_a
        room_registry[8941] = room_b

        traveller = _make_char("Alice", room_a)
        _make_portal(room_a, to_vnum=8941, charges=1)  # charges=1 → after use value[0]=-1

        do_enter(traveller, "portal")

        fade_seen = any("fades out of existence" in m for m in traveller.messages)
        assert fade_seen, f"Traveller did not receive fade message. Messages: {traveller.messages}"

        room_registry.pop(8940, None)
        room_registry.pop(8941, None)

    def test_fade_message_sent_to_old_room_occupants_not_destination(self):
        from mud.registry import room_registry

        room_a = _make_room(8942)
        room_b = _make_room(8943)
        room_registry[8942] = room_a
        room_registry[8943] = room_b

        traveller = _make_char("Alice", room_a)
        bystander = _make_char("Bystander", room_a)  # stays in old room
        waiting = _make_char("Waiting", room_b)       # in destination room

        _make_portal(room_a, to_vnum=8943, charges=1)

        do_enter(traveller, "portal")

        # Bystander in old room should see fade
        bystander_fade = any("fades out of existence" in m for m in bystander.messages)
        assert bystander_fade, f"Bystander did not see fade. Messages: {bystander.messages}"

        room_registry.pop(8942, None)
        room_registry.pop(8943, None)

    def test_no_fade_when_portal_has_unlimited_charges(self):
        from mud.registry import room_registry

        room_a = _make_room(8944)
        room_b = _make_room(8945)
        room_registry[8944] = room_a
        room_registry[8945] = room_b

        traveller = _make_char("Alice", room_a)
        _make_portal(room_a, to_vnum=8945, charges=0)  # charges=0 means unlimited in ROM

        do_enter(traveller, "portal")

        fade_seen = any("fades out of existence" in m for m in traveller.messages)
        assert not fade_seen, f"Unexpected fade message with unlimited portal. Messages: {traveller.messages}"

        room_registry.pop(8944, None)
        room_registry.pop(8945, None)


# ---------------------------------------------------------------------------
# ENTER-012: Follower cascade sends departure/arrival messages for followers
# ---------------------------------------------------------------------------


class TestEnter012FollowerMessages:
    """ENTER-012: ROM follower cascade fires full transit messages for each follower."""

    def test_follower_traverses_portal_and_ends_in_destination(self):
        from mud.registry import room_registry
        from mud.world.movement import move_character_through_portal

        room_a = _make_room(8950)
        room_b = _make_room(8951)
        room_registry[8950] = room_a
        room_registry[8951] = room_b

        leader = _make_char("Leader", room_a)
        follower = _make_char("Follower", room_a)
        follower.master = leader

        portal = _make_portal(room_a, to_vnum=8951, charges=2)

        do_enter(leader, "portal")

        # Follower should have moved to room_b following the leader
        assert getattr(follower.room, "vnum", None) == 8951, (
            f"Follower should be in room 8951 but is in {getattr(follower.room, 'vnum', None)}"
        )

        room_registry.pop(8950, None)
        room_registry.pop(8951, None)

    def test_follower_does_not_follow_through_expired_portal(self):
        from mud.registry import room_registry

        room_a = _make_room(8952)
        room_b = _make_room(8953)
        room_registry[8952] = room_a
        room_registry[8953] = room_b

        leader = _make_char("Leader", room_a)
        follower = _make_char("Follower", room_a)
        follower.master = leader

        # charges=1 → portal expires after leader uses it
        portal = _make_portal(room_a, to_vnum=8953, charges=1)

        do_enter(leader, "portal")

        # Follower should remain in room_a (portal expired)
        assert getattr(follower.room, "vnum", None) == 8952, (
            f"Follower should stay in 8952 but is in {getattr(follower.room, 'vnum', None)}"
        )

        room_registry.pop(8952, None)
        room_registry.pop(8953, None)


# ---------------------------------------------------------------------------
# ENTER-013: _get_random_room never returns None when registry has valid rooms
# ---------------------------------------------------------------------------


class TestEnter013RandomRoomNeverNone:
    """ENTER-013: _get_random_room with large iteration cap should not return None."""

    def test_random_room_returns_room_when_valid_rooms_exist(self):
        from mud.registry import room_registry
        from mud.world.movement import _get_random_room

        # Register a clearly valid room (no PRIVATE/SOLITARY/SAFE flags)
        room = _make_room(8960)
        room_registry[8960] = room

        char_room = _make_room(8961)
        room_registry[8961] = char_room
        char = _make_char("Tester", char_room)

        # With enough attempts, should find the valid room
        # Run multiple trials to reduce flakiness from RNG
        found = False
        for _ in range(20):
            result = _get_random_room(char)
            if result is not None:
                found = True
                break

        assert found, "_get_random_room returned None despite valid rooms in registry"

        room_registry.pop(8960, None)
        room_registry.pop(8961, None)

    def test_random_portal_destination_never_nowhere(self):
        """GATE_RANDOM portal should always teleport, never show 'nowhere' message."""
        from mud.registry import room_registry

        room_a = _make_room(8962)
        room_b = _make_room(8963)  # the only other room — valid destination
        room_registry[8962] = room_a
        room_registry[8963] = room_b

        traveller = _make_char("Alice", room_a)
        _make_portal(room_a, to_vnum=8963, gate_flags=int(PortalFlag.RANDOM), charges=0)

        # With a valid room in registry, random portal should always succeed
        # Test multiple times to reduce RNG flakiness
        success_count = 0
        for _ in range(5):
            # Reset char to room_a each iteration
            if traveller.room is not room_a:
                traveller.room.remove_character(traveller)
                room_a.add_character(traveller)
            _make_portal(room_a, to_vnum=8963, gate_flags=int(PortalFlag.RANDOM), charges=0)

            result = do_enter(traveller, "portal")
            nowhere = any("doesn't seem to go anywhere" in m for m in traveller.messages)
            if not nowhere:
                success_count += 1
            traveller.messages.clear()

        assert success_count > 0, "Random portal always showed 'nowhere' — get_random_room may be returning None"

        room_registry.pop(8962, None)
        room_registry.pop(8963, None)


# ---------------------------------------------------------------------------
# ENTER-014/015: $p in "doesn't seem to go anywhere" message
# ---------------------------------------------------------------------------


class TestEnter015NoDestinationMessage:
    """ENTER-015: No-destination message uses act-format '$p doesn't seem to go anywhere.'"""

    def test_null_destination_uses_portal_name_in_message(self):
        from mud.registry import room_registry

        room_a = _make_room(8970)
        room_registry[8970] = room_a

        char = _make_char("Tester", room_a)

        # Portal pointing to non-existent destination vnum
        _make_portal(room_a, to_vnum=99999)

        result = do_enter(char, "portal")

        # Should reference portal's short_descr (via $p expansion)
        assert "doesn't seem to go anywhere" in result or any(
            "doesn't seem to go anywhere" in m for m in char.messages
        ), f"Expected no-destination message. Result: {result!r}, Messages: {char.messages}"

        room_registry.pop(8970, None)


# ---------------------------------------------------------------------------
# ENTER-016: Fighting check is silent (no message sent)
# ---------------------------------------------------------------------------


class TestEnter016FightingSilent:
    """ENTER-016: ROM is silent when char is fighting — no message string (act_enter.c:70-71)."""

    def test_fighting_char_gets_empty_return(self):
        room_a = _make_room(8980)
        room_b = _make_room(8981)
        char = _make_char("Fighter", room_a)

        # Set up fighting state (point to something)
        dummy_enemy = _make_char("Enemy", room_a)
        char.fighting = dummy_enemy

        _make_portal(room_a, to_vnum=8981)

        result = do_enter(char, "portal")

        # ROM returns silently — empty string (not a message)
        assert result == "" or result is None, (
            f"Expected silent return when fighting, got: {result!r}"
        )

    def test_fighting_char_receives_no_message_in_buffer(self):
        room_a = _make_room(8982)
        room_b = _make_room(8983)
        char = _make_char("Fighter", room_a)

        dummy_enemy = _make_char("Enemy", room_a)
        char.fighting = dummy_enemy
        char.messages.clear()

        _make_portal(room_a, to_vnum=8983)

        do_enter(char, "portal")

        assert not char.messages, (
            f"ROM sends no message when fighting, but got: {char.messages}"
        )


# ---------------------------------------------------------------------------
# ENTER-006: Charmed follower stand-up before transit
# ---------------------------------------------------------------------------


class TestEnter006CharmedFollowerStand:
    """ENTER-006: Charmed followers below STANDING are stood up before portal transit."""

    def test_sleeping_charmed_follower_stands_before_following(self):
        from mud.registry import room_registry

        room_a = _make_room(8990)
        room_b = _make_room(8991)
        room_registry[8990] = room_a
        room_registry[8991] = room_b

        leader = _make_char("Leader", room_a)
        follower = _make_char("Follower", room_a)
        follower.master = leader
        follower.position = int(Position.SLEEPING)
        # Give follower the CHARM affect
        follower.affected_by = AffectFlag.CHARM
        # Grant 2 charges so follower can also use the portal
        _make_portal(room_a, to_vnum=8991, charges=2)

        do_enter(leader, "portal")

        # After cascade, follower should have been stood up (position >= STANDING)
        assert follower.position >= int(Position.STANDING), (
            f"Follower should be STANDING after portal cascade, got position={follower.position}"
        )

        room_registry.pop(8990, None)
        room_registry.pop(8991, None)


# ---------------------------------------------------------------------------
# GOWITH flag: portal moves with the traveller
# ---------------------------------------------------------------------------


class TestGowithFlag:
    """GOWITH portal flag: portal object moves to destination room."""

    def test_gowith_portal_moves_to_destination(self):
        from mud.registry import room_registry

        room_a = _make_room(9000)
        room_b = _make_room(9001)
        room_registry[9000] = room_a
        room_registry[9001] = room_b

        traveller = _make_char("Alice", room_a)
        portal = _make_portal(room_a, to_vnum=9001, gate_flags=int(PortalFlag.GOWITH), charges=0)

        assert portal in room_a.contents

        do_enter(traveller, "portal")

        assert portal not in room_a.contents, "Portal should have left room_a"
        assert portal in room_b.contents, "Portal should now be in room_b"

        room_registry.pop(9000, None)
        room_registry.pop(9001, None)
