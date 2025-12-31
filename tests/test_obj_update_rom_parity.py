"""
ROM Parity Tests: Object Timer Updates (ROM update.c:913-1075)

Tests object timer decrements, affect duration tracking, decay messages,
and content spilling behavior to match ROM 2.4b6 obj_update() exactly.

ROM C Reference: src/update.c:913-1059 (obj_update function)
"""

from __future__ import annotations

import pytest

from mud.game_loop import obj_update, _tick_object_affects, _object_decay_message, _spill_contents
from mud.models.constants import ItemType, WearLocation, WearFlag
from mud.models.obj import ObjIndex, ObjectData, Affect, object_registry


@pytest.fixture(autouse=True)
def cleanup_object_registry():
    """Clear object registry before and after each test."""
    object_registry.clear()
    yield
    object_registry.clear()


def create_test_object(item_type: ItemType, timer: int = 0, **kwargs) -> ObjectData:
    """Create a test object with specified item type and timer."""
    proto = ObjIndex(vnum=1000, short_descr="a test object")
    obj = ObjectData(
        item_type=int(item_type),
        timer=timer,
        short_descr=kwargs.get("short_descr", "a test object"),
        pIndexData=proto,
        **kwargs,
    )
    object_registry.append(obj)
    return obj


# =============================================================================
# Object Affect Duration Tracking (ROM update.c:926-962)
# =============================================================================


@pytest.mark.p0
class TestObjectAffectDuration:
    """Test object affect duration decrements mirror ROM update.c:926-962."""

    def test_affect_duration_decrements_each_tick(self):
        """
        ROM update.c:930-932:
            if (paf->duration > 0) {
                paf->duration--;
        """
        obj = create_test_object(ItemType.WEAPON, timer=10)
        affect = Affect(where=0, type=1, duration=5, modifier=10, location=1, bitvector=0, level=10)
        obj.affected = [affect]

        _tick_object_affects(obj)

        assert affect.duration == 4  # Decremented by 1

    def test_affect_level_fades_randomly(self):
        """
        ROM update.c:933-934:
            if (number_range(0, 4) == 0 && paf->level > 0)
                paf->level--;  /* spell strength fades with time */

        Note: This is probabilistic (20% chance), so we test the mechanism exists
        by running multiple iterations.
        """
        obj = create_test_object(ItemType.WEAPON, timer=10)
        affect = Affect(where=0, type=1, duration=100, modifier=10, location=1, bitvector=0, level=50)
        obj.affected = [affect]

        initial_level = affect.level
        ticks_run = 0

        # Run 50 ticks - statistically should see at least one level fade
        for _ in range(50):
            _tick_object_affects(obj)
            ticks_run += 1
            if affect.level < initial_level:
                break

        assert affect.level < initial_level, "Affect level should fade over 50 ticks (20% chance per tick)"
        assert affect.duration == 100 - ticks_run  # Duration decremented by number of ticks

    def test_negative_duration_affects_never_expire(self):
        """
        ROM update.c:936:
            else if (paf->duration < 0);  // No-op - permanent affects

        Permanent affects (duration < 0) should never decrement or be removed.
        """
        obj = create_test_object(ItemType.WEAPON, timer=10)
        affect = Affect(where=0, type=1, duration=-1, modifier=10, location=1, bitvector=0, level=10)
        obj.affected = [affect]

        _tick_object_affects(obj)

        assert affect.duration == -1  # Never changes
        assert affect in obj.affected  # Never removed

    def test_zero_duration_affects_removed(self):
        """
        ROM update.c:937-960:
            else {  // duration == 0
                ...
                affect_remove_obj(obj, paf);
            }

        When affect duration reaches 0, it should be removed from the object.
        """
        obj = create_test_object(ItemType.WEAPON, timer=10)
        affect = Affect(where=0, type=1, duration=1, modifier=10, location=1, bitvector=0, level=10)
        obj.affected = [affect]

        # First tick: duration 1 -> 0
        _tick_object_affects(obj)
        assert affect.duration == 0
        assert affect in obj.affected  # Still present at duration 0

        # Second tick: duration 0 -> removed
        _tick_object_affects(obj)
        assert affect not in obj.affected  # Removed


# =============================================================================
# Object Timer Decrements (ROM update.c:965-1001)
# =============================================================================


@pytest.mark.p0
class TestObjectTimerDecrement:
    """Test object timer decrements mirror ROM update.c:965-1001."""

    def test_timer_decrements_each_tick(self):
        """
        ROM update.c:965:
            if (obj->timer <= 0 || --obj->timer > 0)
                continue;

        Timer should decrement by 1 each obj_update() call.
        """
        obj = create_test_object(ItemType.FOOD, timer=5)

        obj_update()
        assert obj.timer == 4

        obj_update()
        assert obj.timer == 3

    def test_zero_timer_objects_ignored(self):
        """
        ROM update.c:965:
            if (obj->timer <= 0 || --obj->timer > 0)
                continue;

        Objects with timer <= 0 should not be processed.
        """
        obj = create_test_object(ItemType.FOOD, timer=0)
        initial_registry_size = len(object_registry)

        obj_update()

        # Object should still exist (not extracted)
        assert obj in object_registry
        assert len(object_registry) == initial_registry_size

    def test_timer_expires_extracts_object(self):
        """
        ROM update.c:1055:
            extract_obj(obj);

        When timer reaches 0 (after decrement), object should be extracted.
        """
        obj = create_test_object(ItemType.FOOD, timer=1)

        obj_update()  # timer 1 -> 0, should extract

        assert obj not in object_registry  # Object removed


# =============================================================================
# Decay Messages by Item Type (ROM update.c:968-1001)
# =============================================================================


@pytest.mark.p0
class TestDecayMessages:
    """Test decay messages match ROM update.c:968-1001 exactly."""

    def test_fountain_decay_message(self):
        """ROM update.c:973-975: ITEM_FOUNTAIN -> "$p dries up." """
        obj = create_test_object(ItemType.FOUNTAIN, timer=1)
        msg = _object_decay_message(obj)
        assert msg == "$p dries up."

    def test_corpse_npc_decay_message(self):
        """ROM update.c:976-978: ITEM_CORPSE_NPC -> "$p decays into dust." """
        obj = create_test_object(ItemType.CORPSE_NPC, timer=1)
        msg = _object_decay_message(obj)
        assert msg == "$p decays into dust."

    def test_corpse_pc_decay_message(self):
        """ROM update.c:979-981: ITEM_CORPSE_PC -> "$p decays into dust." """
        obj = create_test_object(ItemType.CORPSE_PC, timer=1)
        msg = _object_decay_message(obj)
        assert msg == "$p decays into dust."

    def test_food_decay_message(self):
        """ROM update.c:982-984: ITEM_FOOD -> "$p decomposes." """
        obj = create_test_object(ItemType.FOOD, timer=1)
        msg = _object_decay_message(obj)
        assert msg == "$p decomposes."

    def test_potion_decay_message(self):
        """ROM update.c:985-987: ITEM_POTION -> "$p has evaporated from disuse." """
        obj = create_test_object(ItemType.POTION, timer=1)
        msg = _object_decay_message(obj)
        assert msg == "$p has evaporated from disuse."

    def test_portal_decay_message(self):
        """ROM update.c:988-990: ITEM_PORTAL -> "$p fades out of existence." """
        obj = create_test_object(ItemType.PORTAL, timer=1)
        msg = _object_decay_message(obj)
        assert msg == "$p fades out of existence."

    def test_container_float_with_contents_message(self):
        """
        ROM update.c:991-996:
            case ITEM_CONTAINER:
                if (CAN_WEAR(obj, ITEM_WEAR_FLOAT))
                    if (obj->contains)
                        message = "$p flickers and vanishes, spilling its contents on the floor.";
        """
        proto = ObjIndex(vnum=1001, short_descr="a bag")
        obj = ObjectData(
            item_type=int(ItemType.CONTAINER),
            timer=1,
            short_descr="a bag",
            wear_flags=int(WearFlag.WEAR_FLOAT),
            pIndexData=proto,
        )

        # Add contained item
        inner_proto = ObjIndex(vnum=1002, short_descr="a coin")
        inner_obj = ObjectData(item_type=int(ItemType.TREASURE), timer=0, short_descr="a coin", pIndexData=inner_proto)
        obj.contains = [inner_obj]

        msg = _object_decay_message(obj)
        assert msg == "$p flickers and vanishes, spilling its contents on the floor."

    def test_container_float_empty_message(self):
        """
        ROM update.c:996-997:
            else
                message = "$p flickers and vanishes.";
        """
        proto = ObjIndex(vnum=1001, short_descr="a bag")
        obj = ObjectData(
            item_type=int(ItemType.CONTAINER),
            timer=1,
            short_descr="a bag",
            wear_flags=int(WearFlag.WEAR_FLOAT),
            pIndexData=proto,
        )
        obj.contains = []

        msg = _object_decay_message(obj)
        assert msg == "$p flickers and vanishes."

    def test_default_decay_message(self):
        """ROM update.c:970-972: default -> "$p crumbles into dust." """
        obj = create_test_object(ItemType.WEAPON, timer=1)
        msg = _object_decay_message(obj)
        assert msg == "$p crumbles into dust."


# =============================================================================
# Content Spilling on Decay (ROM update.c:1025-1053)
# =============================================================================


@pytest.mark.p0
class TestContentSpilling:
    """Test content spilling matches ROM update.c:1025-1053."""

    def test_corpse_pc_spills_contents(self):
        """
        ROM update.c:1025-1026:
            if ((obj->item_type == ITEM_CORPSE_PC || obj->wear_loc == WEAR_FLOAT)
                && obj->contains)

        PC corpses should spill contents when decaying.
        """
        from mud.models.room import Room

        room = Room(vnum=3001, name="Test Room", description="A test.")

        proto = ObjIndex(vnum=1001, short_descr="a corpse")
        corpse = ObjectData(item_type=int(ItemType.CORPSE_PC), timer=1, short_descr="a corpse", pIndexData=proto)
        corpse.in_room = room

        # Add contained item
        inner_proto = ObjIndex(vnum=1002, short_descr="a sword")
        sword = ObjectData(item_type=int(ItemType.WEAPON), timer=0, short_descr="a sword", pIndexData=inner_proto)
        corpse.contains = [sword]
        sword.in_obj = corpse

        initial_contains = len(corpse.contains)
        _spill_contents(corpse)

        # Sword should be removed from corpse
        assert len(corpse.contains) < initial_contains

    def test_floating_object_spills_contents(self):
        """
        ROM update.c:1025-1026:
            if ((obj->item_type == ITEM_CORPSE_PC || obj->wear_loc == WEAR_FLOAT)
                && obj->contains)

        Objects worn as WEAR_FLOAT should spill contents.
        """
        proto = ObjIndex(vnum=1001, short_descr="a disc")
        disc = ObjectData(
            item_type=int(ItemType.CONTAINER),
            timer=1,
            short_descr="a disc",
            wear_loc=int(WearLocation.FLOAT),
            pIndexData=proto,
        )

        # Add contained item
        inner_proto = ObjIndex(vnum=1002, short_descr="a gem")
        gem = ObjectData(item_type=int(ItemType.TREASURE), timer=0, short_descr="a gem", pIndexData=inner_proto)
        disc.contains = [gem]
        gem.in_obj = disc

        initial_contains = len(disc.contains)
        _spill_contents(disc)

        # Gem should be removed from disc
        assert len(disc.contains) < initial_contains


# =============================================================================
# Integration Tests: Full obj_update() Flow
# =============================================================================


@pytest.mark.p0
class TestObjectUpdateIntegration:
    """Integration tests for complete obj_update() flow."""

    def test_full_decay_cycle(self):
        """Test complete decay from timer=3 to extraction."""
        obj = create_test_object(ItemType.FOOD, timer=3)

        # Tick 1: timer 3 -> 2
        obj_update()
        assert obj.timer == 2
        assert obj in object_registry

        # Tick 2: timer 2 -> 1
        obj_update()
        assert obj.timer == 1
        assert obj in object_registry

        # Tick 3: timer 1 -> 0, extract
        obj_update()
        assert obj not in object_registry

    def test_multiple_objects_with_different_timers(self):
        """Test that multiple objects decay independently."""
        obj1 = create_test_object(ItemType.FOOD, timer=2)
        obj2 = create_test_object(ItemType.POTION, timer=5)
        obj3 = create_test_object(ItemType.WEAPON, timer=1)

        # First tick
        obj_update()
        assert obj1.timer == 1
        assert obj2.timer == 4
        assert obj3 not in object_registry  # timer 1 -> 0, extracted

        # Second tick
        obj_update()
        assert obj1 not in object_registry  # timer 1 -> 0, extracted
        assert obj2.timer == 3

    def test_affect_and_timer_both_decrement(self):
        """Test that object affects and timer both decrement in same tick."""
        obj = create_test_object(ItemType.WEAPON, timer=5)
        affect = Affect(where=0, type=1, duration=3, modifier=10, location=1, bitvector=0, level=5)
        obj.affected = [affect]

        obj_update()

        # Both should decrement
        assert obj.timer == 4
        assert affect.duration == 2

    def test_zero_timer_objects_not_processed(self):
        """Objects with timer=0 should be skipped entirely."""
        obj = create_test_object(ItemType.FOOD, timer=0)

        obj_update()

        # Object should remain unchanged
        assert obj.timer == 0
        assert obj in object_registry
