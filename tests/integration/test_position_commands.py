"""Integration tests for position commands with furniture support.

ROM Reference: src/act_move.c
- do_stand (lines 999-1106)
- do_rest  (lines 1110-1246)
- do_sit   (lines 1249-1372)
- do_sleep (lines 1375-1449)
- do_wake  (lines 1453-1492)

Audit IDs covered: STAND-001..006, REST-001..006, SIT-001..007,
SLEEP-001..005, WAKE-001..004.
"""

from __future__ import annotations

import pytest

from mud.commands.position import do_rest, do_sit, do_sleep, do_stand, do_wake
from mud.models.constants import AffectFlag, FurnitureFlag, ItemType, Position, WearFlag
from mud.models.object import ObjIndex, Object
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import initialize_world


@pytest.fixture(scope="module", autouse=True)
def _initialize_world():
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()


@pytest.fixture
def test_room():
    from mud.models.room import Room

    if 3001 not in room_registry:
        room_registry[3001] = Room(vnum=3001, name="Test Room", description="A test room")
    return room_registry[3001]


@pytest.fixture(autouse=True)
def _clean(test_room):
    for vnum in [v for v in list(obj_registry.keys()) if v >= 91000]:
        del obj_registry[vnum]
    test_room.contents.clear()
    # Clear room people of test characters between tests
    test_room.people.clear()
    yield
    for vnum in [v for v in list(obj_registry.keys()) if v >= 91000]:
        del obj_registry[vnum]
    test_room.contents.clear()
    test_room.people.clear()


_vnum_counter = 91000


def _next_vnum() -> int:
    global _vnum_counter
    _vnum_counter += 1
    return _vnum_counter


def _make_furn(*, flags: FurnitureFlag, capacity: int = 1, name: str = "chair wooden",
               short: str = "a wooden chair") -> Object:
    vnum = _next_vnum()
    proto = ObjIndex(
        vnum=vnum,
        name=name,
        short_descr=short,
        description="A piece of furniture sits here.",
        item_type=int(ItemType.FURNITURE),
        wear_flags=int(WearFlag.TAKE),
        value=[capacity, 100, int(flags), 0, 0],
    )
    obj_registry[vnum] = proto
    obj = Object(instance_id=vnum, prototype=proto)
    obj.value = list(proto.value)
    return obj


def _place(test_room, obj: Object) -> Object:
    test_room.add_object(obj)
    return obj


# ---------------------------------------------------------------------------
# do_stand
# ---------------------------------------------------------------------------


class TestDoStand:
    def test_standing_already(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.STANDING
        assert "already standing" in do_stand(ch, "")

    def test_fighting_blocks(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.FIGHTING
        assert "already fighting" in do_stand(ch, "")

    def test_sitting_to_standing_no_obj_broadcasts(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        observer = movable_char_factory("Watcher", 3001)
        ch.position = Position.SITTING
        result = do_stand(ch, "")
        assert "You stand up." in result
        assert ch.position == Position.STANDING
        assert ch.on is None
        assert any("stands up" in m for m in observer.messages), observer.messages

    def test_sleeping_magical_sleep_blocks(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.SLEEPING
        ch.affected_by |= AffectFlag.SLEEP
        assert "can't wake up" in do_stand(ch, "")

    def test_stand_on_furniture(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        observer = movable_char_factory("Watcher", 3001)
        ch.position = Position.RESTING
        chair = _place(test_room, _make_furn(flags=FurnitureFlag.STAND_ON, capacity=2))
        result = do_stand(ch, "chair")
        assert "stand on a wooden chair" in result
        assert ch.position == Position.STANDING
        assert ch.on is chair
        assert any("stands on a wooden chair" in m for m in observer.messages)

    def test_stand_at_furniture(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.RESTING
        desk = _place(test_room, _make_furn(flags=FurnitureFlag.STAND_AT, capacity=4,
                                            name="desk oak", short="an oak desk"))
        assert "stand at an oak desk" in do_stand(ch, "desk")
        assert ch.on is desk

    def test_stand_capacity_rejected(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        other = movable_char_factory("Other", 3001)
        ch.position = Position.RESTING
        chair = _place(test_room, _make_furn(flags=FurnitureFlag.STAND_ON, capacity=1))
        other.on = chair
        other.position = Position.STANDING
        assert "no room to stand" in do_stand(ch, "chair")
        assert ch.on is None

    def test_stand_non_furniture_rejected(self, movable_char_factory, test_room):
        from mud.models.object import Object as Obj

        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.RESTING
        proto = ObjIndex(
            vnum=_next_vnum(), name="rock", short_descr="a rock",
            item_type=int(ItemType.TREASURE), value=[0, 0, 0, 0, 0],
        )
        obj_registry[proto.vnum] = proto
        rock = Obj(instance_id=proto.vnum, prototype=proto)
        test_room.add_object(rock)
        assert "find a place to stand" in do_stand(ch, "rock")

    def test_stand_unknown_target(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.RESTING
        assert "don't see that here" in do_stand(ch, "phantom")

    def test_wake_and_stand_no_obj_clears_on(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        observer = movable_char_factory("Watcher", 3001)
        chair = _place(test_room, _make_furn(flags=FurnitureFlag.SLEEP_ON, capacity=2))
        ch.position = Position.SLEEPING
        ch.on = chair
        result = do_stand(ch, "")
        assert "wake and stand up" in result
        assert ch.on is None
        assert ch.position == Position.STANDING
        assert any("wakes and stands up" in m for m in observer.messages)


# ---------------------------------------------------------------------------
# do_rest
# ---------------------------------------------------------------------------


class TestDoRest:
    def test_already_resting(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.RESTING
        assert "already resting" in do_rest(ch, "")

    def test_fighting_blocks(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.FIGHTING
        assert "already fighting" in do_rest(ch, "")

    def test_standing_no_obj(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        observer = movable_char_factory("Watcher", 3001)
        ch.position = Position.STANDING
        assert "You rest." in do_rest(ch, "")
        assert ch.position == Position.RESTING
        assert any("sits down and rests" in m for m in observer.messages)

    def test_rest_on_sofa(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.STANDING
        sofa = _place(test_room, _make_furn(flags=FurnitureFlag.REST_ON, capacity=3,
                                            name="sofa", short="a sofa"))
        assert "sit on a sofa and rest" in do_rest(ch, "sofa")
        assert ch.on is sofa

    def test_rest_default_uses_ch_on(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.STANDING
        bed = _place(test_room, _make_furn(flags=FurnitureFlag.REST_ON, capacity=2,
                                           name="bed", short="a bed"))
        ch.on = bed
        result = do_rest(ch, "")
        assert "sit on a bed and rest" in result
        assert ch.on is bed

    def test_rest_capacity_rejected(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        other = movable_char_factory("Other", 3001)
        ch.position = Position.STANDING
        sofa = _place(test_room, _make_furn(flags=FurnitureFlag.REST_ON, capacity=1,
                                            name="sofa", short="a sofa"))
        other.on = sofa
        assert "no more room on a sofa" in do_rest(ch, "sofa")
        assert ch.on is None

    def test_rest_wake_no_obj(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.SLEEPING
        result = do_rest(ch, "")
        assert "wake up and start resting" in result
        assert ch.position == Position.RESTING

    def test_rest_non_furniture_rejected(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.STANDING
        proto = ObjIndex(
            vnum=_next_vnum(), name="rock", short_descr="a rock",
            item_type=int(ItemType.TREASURE), value=[0, 0, 0, 0, 0],
        )
        obj_registry[proto.vnum] = proto
        rock = Object(instance_id=proto.vnum, prototype=proto)
        test_room.add_object(rock)
        assert "can't rest on that" in do_rest(ch, "rock")


# ---------------------------------------------------------------------------
# do_sit
# ---------------------------------------------------------------------------


class TestDoSit:
    def test_already_sitting(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.SITTING
        assert "already sitting" in do_sit(ch, "")

    def test_fighting_blocks(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.FIGHTING
        assert "finish this fight first" in do_sit(ch, "")

    def test_standing_no_obj(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        observer = movable_char_factory("Watcher", 3001)
        ch.position = Position.STANDING
        assert "You sit down." in do_sit(ch, "")
        assert ch.position == Position.SITTING
        assert any("sits down on the ground" in m for m in observer.messages)

    def test_sit_at_desk(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.STANDING
        desk = _place(test_room, _make_furn(flags=FurnitureFlag.SIT_AT, capacity=4,
                                            name="desk", short="a desk"))
        assert "You sit down at a desk." in do_sit(ch, "desk")
        assert ch.on is desk
        assert ch.position == Position.SITTING

    def test_sit_on_chair(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.STANDING
        chair = _place(test_room, _make_furn(flags=FurnitureFlag.SIT_ON, capacity=1))
        assert "You sit on a wooden chair." in do_sit(ch, "chair")
        assert ch.on is chair

    def test_sit_capacity_rejected(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        other = movable_char_factory("Other", 3001)
        ch.position = Position.STANDING
        chair = _place(test_room, _make_furn(flags=FurnitureFlag.SIT_ON, capacity=1))
        other.on = chair
        assert "no more room on" in do_sit(ch, "chair")

    def test_sit_from_resting_no_obj(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.RESTING
        assert "stop resting" in do_sit(ch, "")
        assert ch.position == Position.SITTING

    def test_sit_from_sleeping_wakes(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.SLEEPING
        result = do_sit(ch, "")
        assert "wake and sit up" in result
        assert ch.position == Position.SITTING


# ---------------------------------------------------------------------------
# do_sleep
# ---------------------------------------------------------------------------


class TestDoSleep:
    def test_already_sleeping(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.SLEEPING
        assert "already sleeping" in do_sleep(ch, "")

    def test_fighting_blocks(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.FIGHTING
        assert "already fighting" in do_sleep(ch, "")

    def test_sleep_no_obj(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        observer = movable_char_factory("Watcher", 3001)
        ch.position = Position.STANDING
        assert "go to sleep" in do_sleep(ch, "")
        assert ch.position == Position.SLEEPING
        assert any("goes to sleep" in m for m in observer.messages)

    def test_sleep_on_bed(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.STANDING
        bed = _place(test_room, _make_furn(flags=FurnitureFlag.SLEEP_ON, capacity=1,
                                           name="bed", short="a bed"))
        assert "You go to sleep on a bed." in do_sleep(ch, "bed")
        assert ch.on is bed
        assert ch.position == Position.SLEEPING

    def test_sleep_default_uses_ch_on(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.STANDING
        bed = _place(test_room, _make_furn(flags=FurnitureFlag.SLEEP_ON, capacity=1,
                                           name="bed", short="a bed"))
        ch.on = bed
        assert "go to sleep on a bed" in do_sleep(ch, "")

    def test_sleep_capacity_rejected(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        other = movable_char_factory("Other", 3001)
        ch.position = Position.STANDING
        bed = _place(test_room, _make_furn(flags=FurnitureFlag.SLEEP_ON, capacity=1,
                                           name="bed", short="a bed"))
        other.on = bed
        assert "no room on a bed for you" in do_sleep(ch, "bed")

    def test_sleep_non_furniture_rejected(self, movable_char_factory, test_room):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.STANDING
        proto = ObjIndex(
            vnum=_next_vnum(), name="rock", short_descr="a rock",
            item_type=int(ItemType.TREASURE), value=[0, 0, 0, 0, 0],
        )
        obj_registry[proto.vnum] = proto
        rock = Object(instance_id=proto.vnum, prototype=proto)
        test_room.add_object(rock)
        assert "can't sleep on that" in do_sleep(ch, "rock")


# ---------------------------------------------------------------------------
# do_wake
# ---------------------------------------------------------------------------


class TestDoWake:
    def test_wake_self_no_arg_stands(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.SLEEPING
        result = do_wake(ch, "")
        assert "wake and stand up" in result
        assert ch.position == Position.STANDING

    def test_wake_self_already_awake(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.STANDING
        assert "already standing" in do_wake(ch, "")

    def test_wake_target_when_caller_asleep(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        sleeper = movable_char_factory("Bob", 3001)
        ch.position = Position.SLEEPING
        sleeper.position = Position.SLEEPING
        assert "asleep yourself" in do_wake(ch, "Bob")

    def test_wake_target_not_here(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        ch.position = Position.STANDING
        assert "aren't here" in do_wake(ch, "Phantom")

    def test_wake_target_already_awake(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        target = movable_char_factory("Bob", 3001)
        ch.position = Position.STANDING
        target.position = Position.STANDING
        assert "is already awake" in do_wake(ch, "Bob")

    def test_wake_target_magical_sleep(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        target = movable_char_factory("Bob", 3001)
        ch.position = Position.STANDING
        target.position = Position.SLEEPING
        target.affected_by |= AffectFlag.SLEEP
        assert "can't wake" in do_wake(ch, "Bob")

    def test_wake_target_succeeds_sends_to_vict(self, movable_char_factory):
        ch = movable_char_factory("Tester", 3001)
        target = movable_char_factory("Bob", 3001)
        ch.position = Position.STANDING
        target.position = Position.SLEEPING
        # Caller stands (no-op since standing); ROM faithfulness: target gets TO_VICT msg
        do_wake(ch, "Bob")
        assert any("wakes you" in m for m in target.messages), target.messages
