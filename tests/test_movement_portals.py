from mud.commands.dispatcher import process_command
from mud.models.constants import AffectFlag, PortalFlag, Position, RoomFlag
from mud.registry import room_registry
from mud.world import create_test_character, initialize_world
from mud.world.movement import move_character_through_portal


def test_cursed_player_blocked_by_nocurse_portal(portal_factory):
    initialize_world("area/area.lst")
    ch = create_test_character("Traveler", 3001)
    ch.add_affect(AffectFlag.CURSE)
    ch.room.room_flags |= int(RoomFlag.ROOM_NO_RECALL)

    portal = portal_factory(3001, to_vnum=3054)

    out = process_command(ch, "enter portal")
    assert out == "Something prevents you from leaving..."
    assert ch.room.vnum == 3001

    portal.value[2] = int(PortalFlag.NOCURSE)
    portal.prototype.value[2] = int(PortalFlag.NOCURSE)

    out = process_command(ch, "enter portal")
    assert out == "You walk through a shimmering portal and find yourself somewhere else..."
    assert ch.room.vnum == 3054


def test_random_gate_rolls_destination(monkeypatch, portal_factory):
    initialize_world("area/area.lst")
    ch = create_test_character("Traveler", 3001)

    portal = portal_factory(3001, to_vnum=-1, gate_flags=int(PortalFlag.RANDOM))

    destination_vnum = next(
        vnum
        for vnum, room in room_registry.items()
        if not (int(getattr(room, "room_flags", 0) or 0) & int(RoomFlag.ROOM_LAW))
    )
    destination = room_registry[destination_vnum]

    import mud.world.movement as movement
    from mud.time import Sunlight, time_info

    time_info.sunlight = Sunlight.LIGHT
    monkeypatch.setattr(movement, "_get_random_room", lambda _ch: destination)

    out = process_command(ch, "enter portal")
    assert out == "You walk through a shimmering portal and find yourself somewhere else..."
    assert ch.room is destination
    assert portal.value[3] == destination.vnum


def test_portal_charges_and_followers(portal_factory):
    initialize_world("area/area.lst")
    leader = create_test_character("Leader", 3001)
    follower = create_test_character("Follower", 3001)
    follower.master = leader
    follower.is_npc = True

    portal = portal_factory(
        3001,
        to_vnum=3054,
        gate_flags=int(PortalFlag.GOWITH),
        charges=1,
    )

    start_room = leader.room
    destination = room_registry[3054]

    out = process_command(leader, "enter portal")

    assert out == "You walk through a shimmering portal and find yourself somewhere else..."
    assert leader.room is destination
    assert follower.room is start_room
    assert all("follow" not in msg.lower() for msg in follower.messages)

    assert portal.value[0] == -1
    assert portal not in start_room.contents
    assert portal not in destination.contents
    assert portal.location is None

    fade_message = "portal fades out of existence"
    assert any(fade_message in msg.lower() for msg in leader.messages)


def test_portal_normal_exit_messages(portal_factory):
    initialize_world("area/area.lst")
    leader = create_test_character("Leader", 3001)
    onlooker = create_test_character("Onlooker", 3001)
    observer = create_test_character("Observer", 3054)

    portal_factory(
        3001,
        to_vnum=3054,
        gate_flags=int(PortalFlag.NORMAL_EXIT),
    )

    for ch in (leader, onlooker, observer):
        ch.messages.clear()

    out = process_command(leader, "enter portal")

    assert out == "You enter a shimmering portal."
    assert leader.room.vnum == 3054
    assert "Leader steps into a shimmering portal." in onlooker.messages
    assert "Leader has arrived." in observer.messages


def test_enter_portal_does_not_add_wait(portal_factory):
    initialize_world("area/area.lst")
    ch = create_test_character("Traveler", 3001)

    portal_factory(3001, to_vnum=3054)

    ch.wait = 0

    out = process_command(ch, "enter portal")

    assert out == "You walk through a shimmering portal and find yourself somewhere else..."
    assert ch.wait == 0


def test_move_through_portal_blocked_while_fighting(portal_factory):
    initialize_world("area/area.lst")
    ch = create_test_character("Fighter", 3001)
    opponent = create_test_character("Opponent", 3001)

    portal = portal_factory(3001, to_vnum=3054)

    ch.fighting = opponent
    opponent.fighting = ch
    ch.position = int(Position.FIGHTING)
    ch.messages.clear()

    out = move_character_through_portal(ch, portal)

    assert out == "No way!  You are still fighting!"
    assert ch.room.vnum == 3001
    assert "No way!  You are still fighting!" in ch.messages
