"""Integration tests for GET-011: TO_ROOM act() messages for get actions.

ROM Parity References:
- src/act_obj.c:151 (container get TO_ROOM message)
- src/act_obj.c:158 (room get TO_ROOM message)

This test suite verifies that QuickMUD broadcasts get actions to other people
in the room using act() messages, matching ROM 2.4b6 behavior.

ROM C Reference (container get):
    act("You get $p from $P.", ch, obj, container, TO_CHAR);
    act("$n gets $p from $P.", ch, obj, container, TO_ROOM);

ROM C Reference (room get):
    act("You get $p.", ch, obj, container, TO_CHAR);
    act("$n gets $p.", ch, obj, container, TO_ROOM);
"""

from __future__ import annotations

import pytest

from mud.commands.inventory import do_get
from mud.models.constants import ItemType, WearFlag
from mud.models.object import ObjIndex, Object
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import initialize_world


@pytest.fixture(scope="module", autouse=True)
def _initialize_world():
    """Initialize world once for all tests in this module."""
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()


@pytest.fixture
def test_room_3001():
    """Ensure room 3001 exists for testing."""
    from mud.models.room import Room

    if 3001 not in room_registry:
        room = Room(vnum=3001, name="Test Room", description="A test room")
        room_registry[3001] = room
    return room_registry[3001]


@pytest.fixture(autouse=True)
def clean_test_objects(test_room_3001):
    """Remove test-created objects from registry and room before each test."""
    test_vnums = [vnum for vnum in list(obj_registry.keys()) if vnum >= 90000]
    for vnum in test_vnums:
        if vnum in obj_registry:
            del obj_registry[vnum]

    if hasattr(test_room_3001, "contents"):
        test_room_3001.contents.clear()

    if hasattr(test_room_3001, "people"):
        test_room_3001.people.clear()

    yield

    test_vnums = [vnum for vnum in list(obj_registry.keys()) if vnum >= 90000]
    for vnum in test_vnums:
        if vnum in obj_registry:
            del obj_registry[vnum]

    if hasattr(test_room_3001, "contents"):
        test_room_3001.contents.clear()

    if hasattr(test_room_3001, "people"):
        test_room_3001.people.clear()


_test_vnum_counter = 90000


def _get_unique_vnum() -> int:
    """Get a unique vnum for test objects."""
    global _test_vnum_counter
    _test_vnum_counter += 1
    return _test_vnum_counter


def test_get_from_room_broadcasts_to_room(test_room_3001):
    """
    GET-011-1: Getting from room broadcasts "$n gets $p." to other people.

    ROM C: act_obj.c:158
    """
    from mud.models.character import Character

    # Create actor character
    actor = Character(name="Alice", is_npc=False, race=0, ch_class=0)
    actor.room = test_room_3001
    actor.messages = []

    # Create observer character
    observer = Character(name="Bob", is_npc=False, race=0, ch_class=0)
    observer.room = test_room_3001
    observer.messages = []

    # Add both to room
    test_room_3001.people = [actor, observer]

    # Create object in room
    obj_vnum = _get_unique_vnum()
    obj_proto = ObjIndex(
        vnum=obj_vnum,
        name="sword test",
        short_descr="a test sword",
        description="A sword for testing.",
        item_type=int(ItemType.WEAPON),
        wear_flags=int(WearFlag.TAKE),
    )
    obj_registry[obj_vnum] = obj_proto
    obj = Object(prototype=obj_proto, instance_id=None)
    test_room_3001.contents.append(obj)

    # Actor gets object from room
    result = do_get(actor, "sword")

    # Verify actor got success message
    assert "You get" in result

    # ROM C: Observer should see "$n gets $p."
    assert len(observer.messages) > 0, "Observer should have received room message"
    room_message = " ".join(observer.messages).lower()
    assert "alice" in room_message, "Expected actor name in message"
    assert "gets" in room_message, "Expected 'gets' in message"
    assert "sword" in room_message or "test" in room_message, "Expected object name in message"


def test_get_from_container_broadcasts_to_room(test_room_3001):
    """
    GET-011-2: Getting from container broadcasts "$n gets $p from $P." to other people.

    ROM C: act_obj.c:151
    """
    from mud.models.character import Character

    # Create actor character
    actor = Character(name="Alice", is_npc=False, race=0, ch_class=0)
    actor.room = test_room_3001
    actor.messages = []

    # Create observer character
    observer = Character(name="Bob", is_npc=False, race=0, ch_class=0)
    observer.room = test_room_3001
    observer.messages = []

    # Add both to room
    test_room_3001.people = [actor, observer]

    # Create container in room
    container_vnum = _get_unique_vnum()
    container_proto = ObjIndex(
        vnum=container_vnum,
        name="bag backpack",
        short_descr="a leather backpack",
        description="A sturdy leather backpack.",
        item_type=int(ItemType.CONTAINER),
        wear_flags=int(WearFlag.TAKE),
    )
    obj_registry[container_vnum] = container_proto
    container = Object(prototype=container_proto, instance_id=None)
    test_room_3001.contents.append(container)

    # Create object in container
    obj_vnum = _get_unique_vnum()
    obj_proto = ObjIndex(
        vnum=obj_vnum,
        name="sword test",
        short_descr="a test sword",
        description="A sword for testing.",
        item_type=int(ItemType.WEAPON),
        wear_flags=int(WearFlag.TAKE),
    )
    obj_registry[obj_vnum] = obj_proto
    obj = Object(prototype=obj_proto, instance_id=None)
    container.contained_items = [obj]

    # Actor gets object from container
    result = do_get(actor, "sword backpack")

    # Verify actor got success message
    assert "You get" in result
    assert "from" in result

    # ROM C: Observer should see "$n gets $p from $P."
    assert len(observer.messages) > 0, "Observer should have received room message"
    room_message = " ".join(observer.messages).lower()
    assert "alice" in room_message, "Expected actor name in message"
    assert "gets" in room_message, "Expected 'gets' in message"
    assert "from" in room_message, "Expected 'from' in message"
    assert "sword" in room_message or "test" in room_message, "Expected object name in message"
    assert "backpack" in room_message or "bag" in room_message, "Expected container name in message"


def test_get_excludes_actor_from_broadcast(test_room_3001):
    """
    GET-011-3: Actor doesn't receive their own TO_ROOM message.

    ROM C: TO_ROOM excludes the actor
    """
    from mud.models.character import Character

    # Create actor character
    actor = Character(name="Alice", is_npc=False, race=0, ch_class=0)
    actor.room = test_room_3001
    actor.messages = []

    # Add to room (solo)
    test_room_3001.people = [actor]

    # Create object in room
    obj_vnum = _get_unique_vnum()
    obj_proto = ObjIndex(
        vnum=obj_vnum,
        name="sword test",
        short_descr="a test sword",
        description="A sword for testing.",
        item_type=int(ItemType.WEAPON),
        wear_flags=int(WearFlag.TAKE),
    )
    obj_registry[obj_vnum] = obj_proto
    obj = Object(prototype=obj_proto, instance_id=None)
    test_room_3001.contents.append(obj)

    # Actor gets object from room
    result = do_get(actor, "sword")

    # Verify actor got success message
    assert "You get" in result

    # ROM C: Actor should NOT receive TO_ROOM message (only TO_CHAR)
    # messages list might be empty or only have TO_CHAR messages
    room_messages = [msg for msg in actor.messages if "gets" in msg.lower()]
    # If there are any "gets" messages, they should NOT use third person
    for msg in room_messages:
        assert "alice gets" not in msg.lower(), "Actor should not receive their own TO_ROOM message"


def test_multiple_observers_receive_broadcast(test_room_3001):
    """
    GET-011-4: All observers in room receive TO_ROOM broadcast.

    ROM C: act() TO_ROOM sends to all in room except actor
    """
    from mud.models.character import Character

    # Create actor character
    actor = Character(name="Alice", is_npc=False, race=0, ch_class=0)
    actor.room = test_room_3001
    actor.messages = []

    # Create multiple observers
    observer1 = Character(name="Bob", is_npc=False, race=0, ch_class=0)
    observer1.room = test_room_3001
    observer1.messages = []

    observer2 = Character(name="Carol", is_npc=False, race=0, ch_class=0)
    observer2.room = test_room_3001
    observer2.messages = []

    observer3 = Character(name="Dave", is_npc=False, race=0, ch_class=0)
    observer3.room = test_room_3001
    observer3.messages = []

    # Add all to room
    test_room_3001.people = [actor, observer1, observer2, observer3]

    # Create object in room
    obj_vnum = _get_unique_vnum()
    obj_proto = ObjIndex(
        vnum=obj_vnum,
        name="sword test",
        short_descr="a test sword",
        description="A sword for testing.",
        item_type=int(ItemType.WEAPON),
        wear_flags=int(WearFlag.TAKE),
    )
    obj_registry[obj_vnum] = obj_proto
    obj = Object(prototype=obj_proto, instance_id=None)
    test_room_3001.contents.append(obj)

    # Actor gets object from room
    result = do_get(actor, "sword")

    # Verify actor got success message
    assert "You get" in result

    # ROM C: All observers should receive TO_ROOM message
    for observer in [observer1, observer2, observer3]:
        assert len(observer.messages) > 0, f"{observer.name} should have received room message"
        room_message = " ".join(observer.messages).lower()
        assert "alice" in room_message, f"Expected actor name in message to {observer.name}"
        assert "gets" in room_message, f"Expected 'gets' in message to {observer.name}"
