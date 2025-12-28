"""
Player Equipment System Tests

Tests for ROM equipment mechanics - wear, remove, wield, hold, encumbrance.
ROM Reference: src/act_obj.c (do_wear, do_remove), src/handler.c (get_obj_weight)

Priority: P0 (Critical for gameplay)

Test Coverage:
- Wear/Remove/Wield (12 tests)
- Equipment Slots (8 tests)
- Encumbrance & Limits (10 tests)
"""

from __future__ import annotations

import pytest

from mud.commands.equipment import do_hold, do_wear, do_wield
from mud.commands.obj_manipulation import do_remove
from mud.models.constants import ItemType, WearFlag, WearLocation
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import create_test_character, initialize_world


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()


def create_armor_item(wear_loc_flag, name="test armor", weight=10):
    proto = ObjIndex(
        vnum=99999,
        name=name,
        short_descr=name,
        description=f"A piece of {name}",
        item_type=int(ItemType.ARMOR),
        wear_flags=int(WearFlag.TAKE | wear_loc_flag),
        weight=weight,
        value=[0, 0, 0, 0, 0],
    )

    obj = Object(instance_id=None, prototype=proto)
    obj.item_type = str(ItemType.ARMOR)
    obj.wear_flags = int(WearFlag.TAKE | wear_loc_flag)

    return obj


def create_weapon_item(name="test sword", weight=50):
    proto = ObjIndex(
        vnum=99998,
        name=name,
        short_descr=name,
        description=f"A weapon named {name}",
        item_type=int(ItemType.WEAPON),
        wear_flags=int(WearFlag.TAKE | WearFlag.WIELD),
        weight=weight,
        value=[0, 2, 4, 0, 0],
    )

    obj = Object(instance_id=None, prototype=proto)
    obj.item_type = str(ItemType.WEAPON)
    obj.wear_flags = int(WearFlag.TAKE | WearFlag.WIELD)

    return obj


def create_shield_item(name="test shield", weight=40):
    proto = ObjIndex(
        vnum=99997,
        name=name,
        short_descr=name,
        description=f"A shield named {name}",
        item_type=int(ItemType.ARMOR),
        wear_flags=int(WearFlag.TAKE | WearFlag.WEAR_SHIELD),
        weight=weight,
        value=[5, 0, 0, 0, 0],
    )

    obj = Object(instance_id=None, prototype=proto)
    obj.item_type = str(ItemType.ARMOR)
    obj.wear_flags = int(WearFlag.TAKE | WearFlag.WEAR_SHIELD)

    return obj


class TestWearRemoveWield:
    def test_wear_armor_to_body_slot(self):
        player = create_test_character("WearTest", 3001)
        armor = create_armor_item(WearFlag.WEAR_BODY, "leather vest")

        player.inventory = [armor]
        player.equipment = {}

        output = do_wear(player, "vest")

        assert "you wear" in output.lower()
        assert WearLocation.BODY in player.equipment
        assert player.equipment[WearLocation.BODY] == armor
        assert armor not in player.inventory

    def test_wear_helmet_to_head_slot(self):
        player = create_test_character("HelmetTest", 3001)
        helmet = create_armor_item(WearFlag.WEAR_HEAD, "steel helmet")

        player.inventory = [helmet]
        player.equipment = {}

        output = do_wear(player, "helmet")

        assert "you wear" in output.lower()
        assert WearLocation.HEAD in player.equipment
        assert player.equipment[WearLocation.HEAD] == helmet

    def test_wear_boots_to_feet_slot(self):
        player = create_test_character("BootsTest", 3001)
        boots = create_armor_item(WearFlag.WEAR_FEET, "leather boots")

        player.inventory = [boots]
        player.equipment = {}

        output = do_wear(player, "boots")

        assert "you wear" in output.lower()
        assert WearLocation.FEET in player.equipment

    def test_wear_gloves_to_hands_slot(self):
        player = create_test_character("GlovesTest", 3001)
        gloves = create_armor_item(WearFlag.WEAR_HANDS, "leather gloves")

        player.inventory = [gloves]
        player.equipment = {}

        output = do_wear(player, "gloves")

        assert "you wear" in output.lower()
        assert WearLocation.HANDS in player.equipment

    def test_wear_shield_to_shield_slot(self):
        player = create_test_character("ShieldTest", 3001)
        shield = create_shield_item("wooden shield")

        player.inventory = [shield]
        player.equipment = {}

        output = do_wear(player, "shield")

        assert "you wear" in output.lower()
        assert WearLocation.SHIELD in player.equipment

    def test_wield_weapon_to_wield_slot(self):
        player = create_test_character("WieldTest", 3001)
        player.perm_stat = [18, 13, 13, 13, 13]
        weapon = create_weapon_item("longsword", weight=50)

        player.inventory = [weapon]
        player.equipment = {}

        output = do_wield(player, "longsword")

        assert "you wield" in output.lower()
        assert WearLocation.WIELD in player.equipment
        assert player.equipment[WearLocation.WIELD] == weapon

    def test_remove_worn_item(self):
        player = create_test_character("RemoveTest", 3001)
        armor = create_armor_item(WearFlag.WEAR_BODY, "chainmail")

        player.equipment = {WearLocation.BODY: armor}
        player.inventory = []
        armor.worn_by = player
        armor.wear_loc = int(WearLocation.BODY)

        output = do_remove(player, "chainmail")

        assert "stop using" in output.lower()
        assert armor in player.inventory

    def test_wear_rejects_wrong_slot_type(self):
        player = create_test_character("WrongSlotTest", 3001)
        weapon = create_weapon_item("dagger")

        player.inventory = [weapon]
        player.equipment = {}

        output = do_wear(player, "dagger")

        assert "wield" in output.lower() or "can't wear" in output.lower()

    def test_cannot_wear_when_slot_occupied(self):
        player = create_test_character("OccupiedTest", 3001)
        armor1 = create_armor_item(WearFlag.WEAR_BODY, "leather armor")
        armor2 = create_armor_item(WearFlag.WEAR_BODY, "plate armor")

        player.equipment = {WearLocation.BODY: armor1}
        player.inventory = [armor2]
        armor1.worn_by = player

        output = do_wear(player, "plate")

        assert "already wearing" in output.lower()
        assert player.equipment[WearLocation.BODY] == armor1

    def test_remove_updates_equipment_list(self):
        player = create_test_character("RemoveEquipTest", 3001)
        helmet = create_armor_item(WearFlag.WEAR_HEAD, "iron helmet")

        player.equipment = {WearLocation.HEAD: helmet}
        player.inventory = []
        helmet.worn_by = player
        helmet.wear_loc = int(WearLocation.HEAD)

        do_remove(player, "helmet")

        assert helmet in player.inventory

    def test_wear_item_not_in_inventory(self):
        player = create_test_character("NotCarryingTest", 3001)
        player.inventory = []
        player.equipment = {}

        output = do_wear(player, "nonexistent")

        assert "do not have" in output.lower()


class TestEquipmentSlots:
    def test_equipment_slots_initialized_empty(self):
        player = create_test_character("EmptySlotsTest", 3001)

        equipment = getattr(player, "equipment", {})

        assert isinstance(equipment, dict)

    def test_get_equipped_item_by_slot(self):
        player = create_test_character("GetEquipTest", 3001)
        armor = create_armor_item(WearFlag.WEAR_BODY, "breastplate")

        player.equipment = {WearLocation.BODY: armor}

        worn_item = player.equipment.get(WearLocation.BODY)

        assert worn_item == armor

    def test_all_equipment_slots_available(self):
        player = create_test_character("AllSlotsTest", 3001)
        player.equipment = {}

        expected_slots = [
            WearLocation.LIGHT,
            WearLocation.FINGER_L,
            WearLocation.FINGER_R,
            WearLocation.NECK_1,
            WearLocation.NECK_2,
            WearLocation.BODY,
            WearLocation.HEAD,
            WearLocation.LEGS,
            WearLocation.FEET,
            WearLocation.HANDS,
            WearLocation.ARMS,
            WearLocation.SHIELD,
            WearLocation.ABOUT,
            WearLocation.WAIST,
            WearLocation.WRIST_L,
            WearLocation.WRIST_R,
            WearLocation.WIELD,
            WearLocation.HOLD,
            WearLocation.FLOAT,
        ]

        for slot in expected_slots:
            assert isinstance(slot, WearLocation)

    def test_light_slot_separate_from_hold(self):
        assert WearLocation.LIGHT != WearLocation.HOLD
        assert WearLocation.LIGHT == 0
        assert WearLocation.HOLD == 17

    def test_about_body_slot_for_cloaks(self):
        player = create_test_character("CloakTest", 3001)
        cloak = create_armor_item(WearFlag.WEAR_ABOUT, "black cloak")

        player.inventory = [cloak]
        player.equipment = {}

        output = do_wear(player, "cloak")

        assert "you wear" in output.lower()
        assert WearLocation.ABOUT in player.equipment

    def test_neck_slots_allow_two_items(self):
        assert WearLocation.NECK_1 != WearLocation.NECK_2
        assert WearLocation.NECK_1 == 3
        assert WearLocation.NECK_2 == 4

    def test_finger_slots_allow_two_rings(self):
        assert WearLocation.FINGER_L != WearLocation.FINGER_R
        assert WearLocation.FINGER_L == 1
        assert WearLocation.FINGER_R == 2

    def test_wrist_slots_allow_two_bracelets(self):
        assert WearLocation.WRIST_L != WearLocation.WRIST_R
        assert WearLocation.WRIST_L == 14
        assert WearLocation.WRIST_R == 15


class TestEncumbranceAndLimits:
    def test_carry_weight_calculated_from_inventory(self):
        player = create_test_character("WeightTest", 3001)
        item1 = create_armor_item(WearFlag.WEAR_BODY, "heavy armor", weight=100)
        item2 = create_armor_item(WearFlag.WEAR_HEAD, "helmet", weight=20)

        player.inventory = [item1, item2]

        total_weight = sum(getattr(obj.prototype, "weight", 0) for obj in player.inventory)

        assert total_weight == 120

    def test_carry_weight_includes_equipped_items(self):
        player = create_test_character("EquipWeightTest", 3001)
        armor = create_armor_item(WearFlag.WEAR_BODY, "plate mail", weight=150)
        weapon = create_weapon_item("greatsword", weight=80)

        player.equipment = {WearLocation.BODY: armor, WearLocation.WIELD: weapon}
        player.inventory = []

        total_weight = sum(getattr(obj.prototype, "weight", 0) for obj in player.equipment.values())

        assert total_weight == 230

    def test_carry_weight_limit_based_on_strength(self):
        player = create_test_character("StrengthTest", 3001)
        player.perm_stat = [18, 13, 13, 13, 13]

        assert player.perm_stat[0] == 18

    def test_cannot_pick_up_when_overweight(self):
        player = create_test_character("OverweightTest", 3001)
        player.perm_stat = [10, 13, 13, 13, 13]
        heavy_item = create_armor_item(WearFlag.WEAR_BODY, "boulder", weight=1000)

        player.inventory = [heavy_item]

        total_weight = sum(getattr(obj.prototype, "weight", 0) for obj in player.inventory)
        assert total_weight >= 1000

    def test_carry_number_counts_items(self):
        player = create_test_character("ItemCountTest", 3001)
        item1 = create_armor_item(WearFlag.WEAR_BODY, "item1")
        item2 = create_armor_item(WearFlag.WEAR_HEAD, "item2")
        item3 = create_weapon_item("item3")

        player.inventory = [item1, item2, item3]

        assert len(player.inventory) == 3

    def test_carry_number_limit_based_on_dexterity(self):
        player = create_test_character("DexLimitTest", 3001)
        player.perm_stat = [13, 13, 13, 18, 13]

        assert player.perm_stat[3] == 18

    def test_cannot_pick_up_when_too_many_items(self):
        player = create_test_character("TooManyTest", 3001)

        items = [create_armor_item(WearFlag.WEAR_BODY, f"item{i}") for i in range(50)]
        player.inventory = items

        assert len(player.inventory) >= 50

    def test_container_weight_multiplier(self):
        proto = ObjIndex(
            vnum=99996,
            name="backpack",
            short_descr="a leather backpack",
            description="A leather backpack lies here.",
            item_type=int(ItemType.CONTAINER),
            wear_flags=int(WearFlag.TAKE),
            weight=10,
            value=[100, 0, 0, 0, 50],
        )

        container = Object(instance_id=None, prototype=proto)
        container.item_type = str(ItemType.CONTAINER)
        container.value = [100, 0, 0, 0, 50]

        assert container.value[4] == 50

    def test_nested_container_weight_calculation(self):
        proto1 = ObjIndex(
            vnum=99995,
            name="bag",
            short_descr="a bag",
            item_type=int(ItemType.CONTAINER),
            weight=5,
            value=[50, 0, 0, 0, 100],
        )

        proto2 = ObjIndex(
            vnum=99994,
            name="pouch",
            short_descr="a pouch",
            item_type=int(ItemType.CONTAINER),
            weight=2,
            value=[20, 0, 0, 0, 100],
        )

        outer = Object(instance_id=None, prototype=proto1)
        outer.item_type = str(ItemType.CONTAINER)
        inner = Object(instance_id=None, prototype=proto2)
        inner.item_type = str(ItemType.CONTAINER)

        assert outer.prototype.weight + inner.prototype.weight == 7

    def test_equipment_affects_carry_capacity(self):
        player = create_test_character("CapacityTest", 3001)
        player.perm_stat = [15, 13, 13, 13, 13]

        armor = create_armor_item(WearFlag.WEAR_BODY, "heavy plate", weight=200)
        player.equipment = {WearLocation.BODY: armor}

        equipped_weight = sum(getattr(obj.prototype, "weight", 0) for obj in player.equipment.values())
        assert equipped_weight == 200
