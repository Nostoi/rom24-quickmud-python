from mud.commands.dispatcher import process_command
from mud.commands.shop import _get_cost, do_buy
import re

from mud.models.character import Character, character_registry
from mud.models.constants import (
    ActFlag,
    AffectFlag,
    CommFlag,
    ItemType,
    RoomFlag,
    ITEM_HAD_TIMER,
    ITEM_INVENTORY,
    ITEM_INVIS,
    ITEM_NODROP,
    ITEM_SELL_EXTRACT,
)
from mud.models.mob import MobIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import mob_registry, room_registry, shop_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.obj_spawner import spawn_object
from mud.spawning.templates import MobInstance
from mud.time import time_info
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world
from mud.world.movement import can_carry_n, can_carry_w


def _total_wealth(char: Character) -> int:
    return int(char.gold) * 100 + int(char.silver)


def _create_shop_character(name: str, room_vnum: int) -> Character:
    char = create_test_character(name, room_vnum)
    char.level = 20
    char.perm_stat = [20, 15, 15, 15, 15]
    char.mod_stat = [0, 0, 0, 0, 0]
    return char


def test_buy_from_grocer():
    initialize_world("area/area.lst")
    assert 3002 in shop_registry
    char = _create_shop_character("Buyer", 3010)
    char.gold = 100
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        # Ensure grocer has at least one lantern in stock for this test
        if not any((obj.short_descr or "").lower().startswith("a hooded brass lantern") for obj in keeper.inventory):
            lantern = spawn_object(3031)
            assert lantern is not None
            lantern.prototype.short_descr = "a hooded brass lantern"
            keeper.inventory.append(lantern)
        list_output = process_command(char, "list")
        assert "[Lv Price Qty] Item" in list_output
        lantern_line = next(line for line in list_output.splitlines() if "hooded brass lantern" in line)
        assert "--" in lantern_line
        assert "112" in lantern_line
        buy_output = process_command(char, "buy lantern")
        assert "buy a hooded brass lantern" in buy_output.lower()
        assert char.gold == 98
        assert char.silver == 88
        assert any((obj.short_descr or "").lower().startswith("a hooded brass lantern") for obj in char.inventory)
    finally:
        time_info.hour = previous_hour


def test_buy_uses_gold_and_silver():
    initialize_world("area/area.lst")
    assert 3002 in shop_registry
    char = _create_shop_character("Buyer", 3010)
    char.gold = 0
    char.silver = 6050
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        if not any((obj.short_descr or "").lower().startswith("a hooded brass lantern") for obj in keeper.inventory):
            lantern = spawn_object(3031)
            assert lantern is not None
            lantern.prototype.short_descr = "a hooded brass lantern"
            keeper.inventory.append(lantern)
        before = _total_wealth(char)
        buy_output = process_command(char, "buy lantern")
        assert "buy a hooded brass lantern" in buy_output.lower()
        match = re.search(r"for (\d+) silver", buy_output)
        assert match is not None
        price_paid = int(match.group(1))
        assert _total_wealth(char) == before - price_paid
        assert char.gold == 0
    finally:
        time_info.hour = previous_hour


def test_buy_rejects_items_above_level():
    initialize_world("area/area.lst")
    assert 3002 in shop_registry
    char = _create_shop_character("Newbie", 3010)
    char.gold = 200
    char.level = 1
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        weapon = spawn_object(3032)
        assert weapon is not None
        weapon.prototype.short_descr = "a massive greatsword"
        weapon.prototype.cost = 20
        weapon.prototype.level = 10
        keeper.inventory.append(weapon)

        before_gold = char.gold
        response = process_command(char, "buy greatsword")
        assert response == "You can't use that yet."
        assert char.gold == before_gold
        assert not any("greatsword" in (obj.short_descr or "").lower() for obj in char.inventory)
        assert any("greatsword" in (obj.short_descr or "").lower() for obj in keeper.inventory)
    finally:
        time_info.hour = previous_hour


def test_buy_respects_carry_limits():
    initialize_world("area/area.lst")
    assert 3002 in shop_registry
    char = _create_shop_character("Packrat", 3010)
    char.gold = 200
    char.silver = 0
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        matching = [
            obj
            for obj in keeper.inventory
            if (obj.short_descr or obj.name or "").lower().startswith("a hooded brass lantern")
        ]
        if not matching:
            lantern = spawn_object(3031)
            assert lantern is not None
            lantern.prototype.short_descr = "a hooded brass lantern"
            keeper.inventory.append(lantern)
            matching = [lantern]
        lantern = matching[0]
        proto = getattr(lantern, "prototype", None)
        if proto is not None:
            proto.weight = max(int(getattr(proto, "weight", 0) or 0), 5)

        before_gold = char.gold
        before_silver = char.silver

        def lantern_count() -> int:
            return sum(
                1
                for obj in keeper.inventory
                if (obj.short_descr or obj.name or "").lower().startswith("a hooded brass lantern")
            )

        baseline_count = lantern_count()

        limit_number = can_carry_n(char)
        limit_weight = can_carry_w(char)

        # Number cap: reaching the slot limit should deny the purchase.
        char.carry_number = limit_number
        char.carry_weight = 0
        response = process_command(char, "buy lantern")
        assert response == "You can't carry that many items."
        assert char.gold == before_gold
        assert char.silver == before_silver
        assert not any(
            (obj.short_descr or obj.name or "").lower().startswith("a hooded brass lantern") for obj in char.inventory
        )
        assert lantern_count() == baseline_count

        # Weight cap: filling carry weight should trigger the second denial path.
        char.carry_number = limit_number - 1
        char.carry_weight = limit_weight
        response = process_command(char, "buy lantern")
        assert response == "You can't carry that much weight."
        assert char.gold == before_gold
        assert char.silver == before_silver
        assert not any(
            (obj.short_descr or obj.name or "").lower().startswith("a hooded brass lantern") for obj in char.inventory
        )
        assert lantern_count() == baseline_count
    finally:
        time_info.hour = previous_hour


def test_buy_denied_when_coins_exceed_weight_cap():
    initialize_world("area/area.lst")
    assert 3002 in shop_registry
    char = create_test_character("HeavyPurse", 3010)
    char.gold = 1000
    char.silver = 0
    char.carry_number = 0
    char.carry_weight = 0
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        if not any(
            (obj.short_descr or obj.name or "").lower().startswith("a hooded brass lantern") for obj in keeper.inventory
        ):
            lantern = spawn_object(3031)
            assert lantern is not None
            lantern.prototype.short_descr = "a hooded brass lantern"
            keeper.inventory.append(lantern)

        limit_weight = can_carry_w(char)
        assert limit_weight == 100  # default with no stats

        response = process_command(char, "buy lantern")
        assert response == "You can't carry that much weight."
        assert char.gold == 1000
        assert char.silver == 0
        assert not any(
            (obj.short_descr or obj.name or "").lower().startswith("a hooded brass lantern") for obj in char.inventory
        )
    finally:
        time_info.hour = previous_hour


def test_buy_preserves_infinite_stock():
    initialize_world("area/area.lst")
    assert 3002 in shop_registry
    char = _create_shop_character("Quartermaster", 3010)
    char.gold = 200
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        ration = spawn_object(3031)
        assert ration is not None
        ration.prototype.short_descr = "a stack of ration packs"
        ration.prototype.cost = 25
        ration.prototype.extra_flags = int(getattr(ration.prototype, "extra_flags", 0) or 0) | int(ITEM_INVENTORY)
        ration.extra_flags = int(getattr(ration, "extra_flags", 0) or 0) | int(ITEM_INVENTORY)
        ration.timer = 12
        keeper.inventory.append(ration)

        before_wealth = _total_wealth(char)
        baseline_ids = {id(obj) for obj in keeper.inventory}

        response = process_command(char, "buy ration")
        assert "buy a stack of ration packs" in response.lower()
        match = re.search(r"for (\d+) silver", response)
        assert match is not None
        price_paid = int(match.group(1))
        assert _total_wealth(char) == before_wealth - price_paid

        assert {id(obj) for obj in keeper.inventory} == baseline_ids
        assert ration in keeper.inventory

        purchased = next(
            obj
            for obj in char.inventory
            if (obj.short_descr or obj.name or "").lower().startswith("a stack of ration packs")
        )
        assert purchased is not ration
        assert purchased.prototype is ration.prototype
        assert purchased.timer == 0
        assert int(getattr(purchased, "extra_flags", 0) or 0) & int(ITEM_HAD_TIMER) == 0
    finally:
        time_info.hour = previous_hour


def test_buy_handles_multiple_inventory_copies():
    initialize_world("area/area.lst")
    assert 3002 in shop_registry
    char = _create_shop_character("Quartermaster", 3010)
    char.gold = 300
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10

        def make_inventory_item() -> Object:
            ration = spawn_object(3031)
            assert ration is not None
            proto = ration.prototype
            proto.short_descr = "a stack of ration packs"
            proto.cost = 25
            proto.extra_flags = int(getattr(proto, "extra_flags", 0) or 0) | int(ITEM_INVENTORY)
            ration.extra_flags = int(getattr(ration, "extra_flags", 0) or 0) | int(ITEM_INVENTORY)
            ration.timer = 12
            return ration

        ration_a = make_inventory_item()
        ration_b = make_inventory_item()
        keeper.inventory.extend([ration_a, ration_b])

        baseline_ids = {id(ration_a), id(ration_b)}

        def buy_once() -> Object:
            before_wealth = _total_wealth(char)
            response = process_command(char, "buy ration")
            assert "buy a stack of ration packs" in response.lower()
            match = re.search(r"for (\d+) silver", response)
            assert match is not None
            price = int(match.group(1))
            assert _total_wealth(char) == before_wealth - price
            purchased = [
                obj
                for obj in char.inventory
                if (obj.short_descr or obj.name or "").lower().startswith("a stack of ration packs")
            ][-1]
            assert purchased.prototype is ration_a.prototype
            assert purchased.timer == 0
            assert int(getattr(purchased, "extra_flags", 0) or 0) & int(ITEM_HAD_TIMER) == 0
            return purchased

        first_purchase = buy_once()
        second_purchase = buy_once()

        assert first_purchase is not ration_a
        assert second_purchase is not ration_b
        remaining = {
            id(obj)
            for obj in keeper.inventory
            if (obj.short_descr or obj.name or "").lower().startswith("a stack of ration packs")
        }
        assert baseline_ids <= remaining
    finally:
        time_info.hour = previous_hour


def test_buy_inventory_fallback_uses_original_object():
    initialize_world("area/area.lst")
    assert 3002 in shop_registry
    char = _create_shop_character("Forager", 3010)
    char.gold = 200
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10

        template = Object(instance_id=None, prototype=None)
        template.short_descr = "a rare ration pack"
        template.level = 0
        template.weight = 1
        template.cost = 30
        template.extra_flags = int(getattr(template, "extra_flags", 0) or 0) | int(ITEM_INVENTORY)
        template.timer = 9
        keeper.inventory.append(template)

        before_wealth = _total_wealth(char)
        response = process_command(char, "buy ration")
        assert "buy a rare ration pack" in response.lower()
        match = re.search(r"for (\d+) silver", response)
        assert match is not None
        price = int(match.group(1))
        assert price == 0
        assert _total_wealth(char) == before_wealth

        assert template not in keeper.inventory
        assert template in char.inventory
        assert template.timer == 0
        assert int(getattr(template, "extra_flags", 0) or 0) & int(ITEM_HAD_TIMER) == 0
    finally:
        time_info.hour = previous_hour


def test_buy_multiple_items_from_inventory():
    initialize_world("area/area.lst")
    assert 3002 in shop_registry
    char = _create_shop_character("BulkBuyer", 3010)
    char.gold = 5
    char.silver = 0
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        keeper.inventory = []
        baseline_count = 0
        for _ in range(3):
            ration = spawn_object(3001)
            assert ration is not None
            ration.prototype.short_descr = "a ration pack"
            ration.short_descr = "a ration pack"
            ration.prototype.cost = 18
            keeper.inventory.append(ration)
            baseline_count += 1

        before_wealth = _total_wealth(char)
        response = process_command(char, "buy 3*ration")
        assert "buy a ration pack[3]" in response.lower()
        match = re.search(r"for (\d+) silver", response)
        assert match is not None
        total_price = int(match.group(1))
        assert total_price > 0
        assert _total_wealth(char) == before_wealth - total_price
        ration_count = sum(1 for obj in char.inventory if (obj.short_descr or "").lower() == "a ration pack")
        assert ration_count == 3
        remaining = sum(1 for obj in keeper.inventory if (obj.short_descr or "").lower() == "a ration pack")
        assert remaining == max(baseline_count - 3, 0)
    finally:
        time_info.hour = previous_hour


def test_buy_specific_stock_slot():
    initialize_world("area/area.lst")
    assert 3002 in shop_registry
    char = _create_shop_character("TargetBuyer", 3010)
    char.gold = 5
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        keeper.inventory = []
        ration_items: list[Object] = []
        for _ in range(3):
            ration = spawn_object(3001)
            assert ration is not None
            ration.prototype.short_descr = "a ration pack"
            ration.short_descr = "a ration pack"
            ration.prototype.cost = 18
            keeper.inventory.append(ration)
            ration_items.append(ration)

        before = _total_wealth(char)
        response = process_command(char, "buy 2.ration")
        assert "buy a ration pack" in response.lower()
        match = re.search(r"for (\d+) silver", response)
        assert match is not None
        paid = int(match.group(1))
        assert _total_wealth(char) == before - paid
        first, second, third = ration_items
        assert any(existing is second for existing in char.inventory)
        assert any(existing is first for existing in keeper.inventory)
        assert all(existing is not second for existing in keeper.inventory)
        assert any(existing is third for existing in keeper.inventory)
    finally:
        time_info.hour = previous_hour


def test_list_price_matches_buy_price():
    initialize_world("area/area.lst")
    assert 3002 in shop_registry
    char = _create_shop_character("Buyer", 3010)
    char.gold = 100
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        if not any((obj.short_descr or "").lower().startswith("a hooded brass lantern") for obj in keeper.inventory):
            lantern = spawn_object(3031)
            assert lantern is not None
            lantern.prototype.short_descr = "a hooded brass lantern"
            keeper.inventory.append(lantern)
        out = process_command(char, "list")
        # Extract the lantern price from the ROM-formatted row
        import re

        lantern_line = next(line for line in out.splitlines() if "hooded brass lantern" in line)
        match = re.search(r"\[\s*\d+\s+(\d+)\s+", lantern_line)
        assert match
        price = int(match.group(1))
        before = _total_wealth(char)
        process_command(char, "buy lantern")
        assert _total_wealth(char) == before - price
    finally:
        time_info.hour = previous_hour


def test_sell_to_grocer():
    initialize_world("area/area.lst")
    char = _create_shop_character("Seller", 3010)
    char.gold = 0
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    keeper.gold = 100
    keeper.silver = 0
    keeper.inventory = [
        obj
        for obj in getattr(keeper, "inventory", [])
        if "lantern" not in (getattr(obj.prototype, "short_descr", "") or "").lower()
    ]
    lantern = spawn_object(3031)
    assert lantern is not None
    lantern.prototype.item_type = 1
    char.add_object(lantern)
    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        sell_output = process_command(char, "sell lantern")
        assert "sell a hooded brass lantern" in sell_output.lower()
        match = re.search(r"for (\d+) silver", sell_output)
        assert match is not None
        price = int(match.group(1))
        assert _total_wealth(char) == price
        assert char.gold == price // 100
        assert char.silver == price % 100
        keeper = next(
            p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry
        )
        assert any((obj.short_descr or "").lower().startswith("a hooded brass lantern") for obj in keeper.inventory)
    finally:
        time_info.hour = previous_hour


def test_sell_awards_gold_and_silver():
    initialize_world("area/area.lst")
    char = _create_shop_character("Seller", 3010)
    char.gold = 0
    char.silver = 25
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    keeper.gold = 100
    keeper.silver = 0
    keeper.inventory = [
        obj
        for obj in getattr(keeper, "inventory", [])
        if "lantern" not in (getattr(obj.prototype, "short_descr", "") or "").lower()
    ]
    lantern = spawn_object(3031)
    assert lantern is not None
    lantern.prototype.item_type = int(ItemType.LIGHT)
    char.add_object(lantern)
    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        before = _total_wealth(char)
        sell_output = process_command(char, "sell lantern")
        assert "sell a hooded brass lantern" in sell_output.lower()
        match = re.search(r"for (\d+) silver", sell_output)
        assert match is not None
        price = int(match.group(1))
        assert _total_wealth(char) == before + price
    finally:
        time_info.hour = previous_hour


def test_sell_reports_gold_and_silver():
    initialize_world("area/area.lst")
    char = _create_shop_character("Merchant", 3010)
    char.gold = 0
    char.silver = 0
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    keeper.gold = 200
    keeper.silver = 50
    lantern = spawn_object(3031)
    assert lantern is not None
    lantern.prototype.item_type = int(ItemType.LIGHT)
    char.add_object(lantern)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        response = process_command(char, "sell lantern")
        match = re.search(r"for (\d+) silver(?: and (\d+) gold piece(s?))?\.\Z", response)
        assert match is not None
        silver = int(match.group(1))
        gold = int(match.group(2)) if match.group(2) is not None else 0
        suffix = match.group(3) or ""
        total_price = silver + gold * 100
        assert _total_wealth(char) == total_price
        if gold:
            assert suffix == ("" if gold == 1 else "s")
    finally:
        time_info.hour = previous_hour


def test_sell_respects_drop_and_visibility_gates():
    initialize_world("area/area.lst")
    char = _create_shop_character("Seller", 3010)
    char.gold = 0
    char.silver = 0

    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    keeper.gold = 200
    keeper.silver = 0
    keeper.inventory = [
        obj
        for obj in getattr(keeper, "inventory", [])
        if "lantern" not in (getattr(obj.prototype, "short_descr", "") or "").lower()
    ]

    previous_hour = time_info.hour
    nodrop_obj = None
    invis_obj = None
    try:
        time_info.hour = 10

        nodrop_obj = spawn_object(3031)
        assert nodrop_obj is not None
        nodrop_obj.extra_flags = int(ITEM_NODROP)
        nodrop_obj.prototype.item_type = int(ItemType.LIGHT)
        char.add_object(nodrop_obj)
        response = process_command(char, "sell lantern")
        assert response == "You can't let go of it."
        assert _total_wealth(char) == 0
        char.remove_object(nodrop_obj)

        invis_obj = spawn_object(3031)
        assert invis_obj is not None
        invis_obj.extra_flags = int(ITEM_INVIS)
        invis_obj.prototype.item_type = int(ItemType.LIGHT)
        if len(invis_obj.value) > 2:
            invis_obj.value[2] = 0
        char.add_object(invis_obj)
        response = process_command(char, "sell lantern")
        assert response == "The shopkeeper doesn't see what you are offering."
        assert _total_wealth(char) == 0
    finally:
        time_info.hour = previous_hour
        if nodrop_obj and nodrop_obj in char.inventory:
            char.remove_object(nodrop_obj)
        if invis_obj and invis_obj in char.inventory:
            char.remove_object(invis_obj)
        char.gold = 0
        char.silver = 0


def test_sell_sets_reply_after_missing_item():
    initialize_world("area/area.lst")
    char = _create_shop_character("ReplyLess", 3010)
    char.gold = 0
    char.silver = 0

    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        response = process_command(char, "sell lantern")
        assert response == "You don't have that."
        assert char.reply is keeper
    finally:
        time_info.hour = previous_hour


def test_sell_extracts_and_resets_timer():
    initialize_world("area/area.lst")
    char = _create_shop_character("Seller", 3010)
    char.gold = 0
    char.silver = 0

    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    keeper.gold = 500
    keeper.silver = 0
    keeper.affected_by = 0
    keeper.inventory = [
        obj
        for obj in getattr(keeper, "inventory", [])
        if "lantern" not in (getattr(obj.prototype, "short_descr", "") or "").lower()
    ]

    previous_hour = time_info.hour
    try:
        time_info.hour = 10

        extract_obj = spawn_object(3031)
        assert extract_obj is not None
        extract_obj.extra_flags = int(ITEM_SELL_EXTRACT)
        extract_obj.prototype.item_type = int(ItemType.LIGHT)
        char.add_object(extract_obj)
        wealth_before = _total_wealth(char)
        response = process_command(char, "sell lantern")
        assert "you sell" in response.lower()
        assert extract_obj not in keeper.inventory
        assert extract_obj not in char.inventory
        assert _total_wealth(char) > wealth_before
        char.gold = 0
        char.silver = 0

        keeper.inventory = [
            obj
            for obj in keeper.inventory
            if "lantern" not in (getattr(obj.prototype, "short_descr", "") or "").lower()
        ]

        fresh_obj = spawn_object(3031)
        assert fresh_obj is not None
        fresh_obj.timer = 0
        fresh_obj.extra_flags = 0
        fresh_obj.prototype.item_type = int(ItemType.LIGHT)
        char.add_object(fresh_obj)
        response = process_command(char, "sell lantern")
        assert "you sell" in response.lower()
        assert fresh_obj in keeper.inventory
        assert 50 <= fresh_obj.timer <= 100
        assert not (int(fresh_obj.extra_flags) & int(ITEM_HAD_TIMER))
        char.gold = 0
        char.silver = 0

        timed_obj = spawn_object(3031)
        assert timed_obj is not None
        timed_obj.timer = 12
        timed_obj.extra_flags = 0
        timed_obj.prototype.item_type = int(ItemType.LIGHT)
        char.add_object(timed_obj)
        response = process_command(char, "sell lantern")
        assert "you sell" in response.lower()
        assert timed_obj in keeper.inventory
        assert timed_obj.timer == 12
        assert int(timed_obj.extra_flags) & int(ITEM_HAD_TIMER)
    finally:
        time_info.hour = previous_hour


def test_sell_haggle_applies_discount():
    initialize_world("area/area.lst")
    char = _create_shop_character("Haggler", 3010)
    char.gold = 0
    char.silver = 0
    char.skills = {"haggle": 85}

    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    keeper.gold = 500
    keeper.silver = 0
    keeper.inventory = [
        obj
        for obj in getattr(keeper, "inventory", [])
        if "lantern" not in (getattr(obj.prototype, "short_descr", "") or "").lower()
    ]

    lantern = spawn_object(3031)
    assert lantern is not None
    lantern.extra_flags = 0
    lantern.prototype.item_type = int(ItemType.LIGHT)
    lantern.timer = 0
    char.add_object(lantern)

    base_sell = _get_cost(keeper, lantern, buy=False)
    buy_price = _get_cost(keeper, lantern, buy=True)
    proto_cost = int(getattr(lantern.prototype, "cost", getattr(lantern, "cost", 0)) or 0)

    original_roll = rng_mm.number_percent
    try:
        rng_mm.number_percent = lambda: 40
        response = process_command(char, "sell lantern")
    finally:
        rng_mm.number_percent = original_roll

    match = re.search(r"for (\d+) silver(?: and (\d+) gold)?", response)
    assert match is not None
    silver = int(match.group(1))
    gold = int(match.group(2)) if match.group(2) is not None else 0
    total_price = silver + gold * 100

    expected_bonus = (proto_cost // 2) * 40 // 100
    cap_by_buy = (95 * buy_price) // 100 if buy_price > 0 else base_sell + expected_bonus
    expected_total = min(base_sell + expected_bonus, cap_by_buy, keeper.gold * 100 + keeper.silver + base_sell)
    assert total_price == expected_total
    assert "You haggle with the shopkeeper." in getattr(char, "messages", [])


def test_value_respects_drop_and_visibility_gates():
    initialize_world("area/area.lst")
    char = _create_shop_character("Appraiser", 3010)
    char.gold = 0
    char.silver = 0

    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    keeper.inventory = [
        obj
        for obj in getattr(keeper, "inventory", [])
        if "lantern" not in (getattr(obj.prototype, "short_descr", "") or "").lower()
    ]

    previous_hour = time_info.hour
    nodrop_obj = None
    invis_obj = None
    try:
        time_info.hour = 10

        nodrop_obj = spawn_object(3031)
        assert nodrop_obj is not None
        nodrop_obj.extra_flags = int(ITEM_NODROP)
        nodrop_obj.prototype.item_type = int(ItemType.LIGHT)
        char.add_object(nodrop_obj)
        response = process_command(char, "value lantern")
        assert response == "You can't let go of it."
        char.remove_object(nodrop_obj)

        invis_obj = spawn_object(3031)
        assert invis_obj is not None
        invis_obj.extra_flags = int(ITEM_INVIS)
        invis_obj.prototype.item_type = int(ItemType.LIGHT)
        if len(invis_obj.value) > 2:
            invis_obj.value[2] = 0
        char.add_object(invis_obj)
        response = process_command(char, "value lantern")
        assert response == "The shopkeeper doesn't see what you are offering."
    finally:
        time_info.hour = previous_hour
        if nodrop_obj and nodrop_obj in char.inventory:
            char.remove_object(nodrop_obj)
        if invis_obj and invis_obj in char.inventory:
            char.remove_object(invis_obj)


def test_value_lists_offer():
    initialize_world("area/area.lst")
    char = _create_shop_character("Barter", 3010)
    char.gold = 0
    char.silver = 0

    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    keeper.gold = 500
    keeper.silver = 0
    keeper.inventory = [
        obj
        for obj in getattr(keeper, "inventory", [])
        if "lantern" not in (getattr(obj.prototype, "short_descr", "") or "").lower()
    ]

    previous_hour = time_info.hour
    try:
        time_info.hour = 10

        lantern = spawn_object(3031)
        assert lantern is not None
        lantern.prototype.item_type = int(ItemType.LIGHT)
        char.add_object(lantern)

        expected_cost = _get_cost(keeper, lantern, buy=False)
        response = process_command(char, "value lantern")
        descriptor = lantern.short_descr or lantern.name or "it"
        expected_message = (
            "The shopkeeper tells you "
            f"'I'll give you {expected_cost % 100} silver and {expected_cost // 100} gold coins for {descriptor}.'"
        )
        assert response == expected_message
        assert char.reply is keeper
        assert lantern in char.inventory
    finally:
        time_info.hour = previous_hour


def test_sell_numbered_selector():
    initialize_world("area/area.lst")
    char = _create_shop_character("Vendor", 3010)
    char.gold = 0
    char.silver = 0
    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)
    keeper.gold = 50
    keeper.silver = 500

    first = spawn_object(3031)
    second = spawn_object(3031)
    assert first is not None and second is not None
    for obj in (first, second):
        proto = getattr(obj, "prototype", None)
        if proto is not None:
            proto.item_type = int(ItemType.LIGHT)
            proto.cost = 120
        obj.item_type = int(ItemType.LIGHT)
        char.add_object(obj)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        before_char = _total_wealth(char)
        before_keeper = keeper.gold * 100 + keeper.silver

        response = process_command(char, "sell 2.lantern")
        assert "you sell" in response.lower()
        match = re.search(r"for (\d+) silver(?: and (\d+) gold piece(s?))?\.\Z", response)
        assert match is not None
        silver = int(match.group(1))
        gold = int(match.group(2)) if match.group(2) is not None else 0
        price = silver + gold * 100

        assert _total_wealth(char) == before_char + price
        assert keeper.gold * 100 + keeper.silver == before_keeper - price
        assert first in char.inventory
        assert all(obj is not second for obj in char.inventory)
        assert any(obj is second for obj in keeper.inventory)
    finally:
        time_info.hour = previous_hour


def test_wand_staff_price_scales_with_charges_and_inventory_discount():
    from mud.models.constants import ItemType
    from mud.spawning.mob_spawner import spawn_mob
    from mud.spawning.obj_spawner import spawn_object

    initialize_world("area/area.lst")
    # Move to a room and spawn an alchemist-type shopkeeper who buys wands
    ch = create_test_character("Seller", 3001)
    keeper = spawn_mob(3000)
    assert keeper is not None
    keeper.move_to_room(ch.room)

    # Create a wand with partial charges: total=10, remaining=5
    wand = spawn_object(3031)
    assert wand is not None
    wand.prototype.short_descr = "a test wand"
    wand.prototype.item_type = int(ItemType.WAND)
    wand.prototype.cost = 100
    vals = wand.prototype.value
    vals[1] = 10  # total
    vals[2] = 5  # remaining
    ch.add_object(wand)

    # Shop profit_sell for keeper 3000 is 15%; base sell price = 100*15/100 = 15
    # With 5/10 charges remaining → 15 * 5 / 10 = 7 (integer division)
    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        out = process_command(ch, "sell wand")
        assert out.endswith("7 silver.")

        # If shop already has an inventory copy of the same wand, price halves
        copy = spawn_object(3031)
        assert copy is not None
        copy.prototype.short_descr = "a test wand"
        copy.prototype.item_type = int(ItemType.WAND)
        copy.prototype.cost = 100
        copy.prototype.value[1] = 10
        copy.prototype.value[2] = 5
        # Mark as ITEM_INVENTORY using the port's bit (1<<18)
        copy.prototype.extra_flags |= 1 << 18
        keeper.inventory.append(copy)

        wand2 = spawn_object(3031)
        wand2.prototype.short_descr = "a test wand"
        wand2.prototype.item_type = int(ItemType.WAND)
        wand2.prototype.cost = 100
        wand2.prototype.value[1] = 10
        wand2.prototype.value[2] = 5
        ch.add_object(wand2)
        out2 = process_command(ch, "sell wand")
        # Base 15 → charge scaling 7 → inventory half → 3
        assert out2.endswith("3 silver.")
    finally:
        time_info.hour = previous_hour


def test_shop_respects_open_hours():
    initialize_world("area/area.lst")
    char = _create_shop_character("Captain patron", 3001)
    char.gold = 500
    keeper = spawn_mob(3006)
    assert keeper is not None
    keeper.move_to_room(char.room)

    raft = spawn_object(3050)
    assert raft is not None
    raft.prototype.short_descr = "a small river raft"
    raft.prototype.item_type = int(ItemType.BOAT)
    raft.prototype.cost = 200
    keeper.inventory.append(raft)

    canoe = spawn_object(3051)
    assert canoe is not None
    canoe.prototype.short_descr = "a spare canoe"
    canoe.prototype.item_type = int(ItemType.BOAT)
    canoe.prototype.cost = 180
    char.add_object(canoe)

    previous_hour = time_info.hour
    try:
        time_info.hour = 3
        closed_list = process_command(char, "list")
        assert closed_list == "Sorry, I am closed. Come back later."
        assert process_command(char, "buy raft") == "Sorry, I am closed. Come back later."
        assert process_command(char, "sell canoe") == "Sorry, I am closed. Come back later."

        time_info.hour = 23
        closed_list_night = process_command(char, "list")
        assert closed_list_night == "Sorry, I am closed. Come back tomorrow."
        assert process_command(char, "buy raft") == "Sorry, I am closed. Come back tomorrow."
        assert process_command(char, "sell canoe") == "Sorry, I am closed. Come back tomorrow."

        time_info.hour = 10
        listing = process_command(char, "list")
        assert "small river raft" in listing
        before_gold = char.gold
        buy_msg = process_command(char, "buy raft")
        assert "buy a small river raft" in buy_msg.lower()
        assert char.gold < before_gold

        after_buy_gold = char.gold
        sell_msg = process_command(char, "sell canoe")
        assert "sell a spare canoe" in sell_msg.lower()
        assert char.gold > after_buy_gold
    finally:
        time_info.hour = previous_hour


def test_list_shows_rom_columns_and_filters():
    initialize_world("area/area.lst")
    char = _create_shop_character("List patron", 3001)
    char.gold = 500
    keeper = spawn_mob(3006)
    assert keeper is not None
    keeper.move_to_room(char.room)
    keeper.inventory.clear()

    ration_one = spawn_object(3050)
    ration_two = spawn_object(3050)
    assert ration_one is not None and ration_two is not None
    ration_one.prototype.short_descr = "a travel ration"
    ration_two.prototype.short_descr = "a travel ration"
    ration_one.prototype.item_type = int(ItemType.FOOD)
    ration_two.prototype.item_type = int(ItemType.FOOD)
    ration_one.prototype.cost = 15
    ration_two.prototype.cost = 15

    apples = spawn_object(3051)
    assert apples is not None
    apples.prototype.short_descr = "a rack of apples"
    apples.prototype.item_type = int(ItemType.FOOD)
    apples.prototype.cost = 10
    apples.extra_flags = getattr(apples, "extra_flags", 0) | int(ITEM_INVENTORY)

    keeper.inventory.extend([ration_one, ration_two, apples])

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        listing = process_command(char, "list")
        assert "[Lv Price Qty] Item" in listing
        lines = listing.splitlines()
        ration_line = next(line for line in lines if "travel ration" in line)
        apples_line = next(line for line in lines if "rack of apples" in line)
        assert " 2 ]" in ration_line  # shows finite quantity
        assert "--" in apples_line  # infinite stock marker

        filtered = process_command(char, "list ration")
        assert "travel ration" in filtered
        assert "rack of apples" not in filtered

        mixed_case = process_command(char, "list TrAveL RAtion")
        assert "travel ration" in mixed_case
        assert "rack of apples" not in mixed_case

        empty = process_command(char, "list dagger")
        assert empty == "You can't buy anything here."
    finally:
        time_info.hour = previous_hour


def test_list_filters_empty_inventory():
    initialize_world("area/area.lst")
    char = _create_shop_character("Filter patron", 3001)
    keeper = spawn_mob(3006)
    assert keeper is not None
    keeper.move_to_room(char.room)
    keeper.inventory.clear()

    ration = spawn_object(3050)
    assert ration is not None
    ration.prototype.short_descr = "a travel ration"
    ration.prototype.item_type = int(ItemType.FOOD)
    ration.prototype.cost = 15
    keeper.inventory.append(ration)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        baseline = process_command(char, "list")
        assert "travel ration" in baseline

        no_match = process_command(char, "list lantern")
        assert no_match == "You can't buy anything here."
    finally:
        time_info.hour = previous_hour


def test_shop_refuses_invisible_customers():
    initialize_world("area/area.lst")
    char = _create_shop_character("Sneaky patron", 3001)
    char.gold = 500
    char.add_affect(AffectFlag.INVISIBLE)
    keeper = spawn_mob(3006)
    assert keeper is not None
    keeper.move_to_room(char.room)

    raft = spawn_object(3050)
    assert raft is not None
    raft.prototype.short_descr = "a small river raft"
    raft.prototype.item_type = int(ItemType.BOAT)
    raft.prototype.cost = 200
    keeper.inventory.append(raft)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        denied = process_command(char, "list")
        assert denied == "I don't trade with folks I can't see."

        keeper.affected_by = getattr(keeper, "affected_by", 0) | int(AffectFlag.DETECT_INVIS)
        allowed = process_command(char, "list")
        assert "small river raft" in allowed
    finally:
        time_info.hour = previous_hour


def test_shop_respects_keeper_wealth():
    initialize_world("area/area.lst")
    char = _create_shop_character("Consigner", 3001)
    char.gold = 0
    keeper = spawn_mob(3006)
    assert keeper is not None
    keeper.move_to_room(char.room)

    canoe = spawn_object(3051)
    assert canoe is not None
    canoe.prototype.short_descr = "a spare canoe"
    canoe.prototype.item_type = int(ItemType.BOAT)
    canoe.prototype.cost = 180
    char.add_object(canoe)

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        keeper.gold = 1
        keeper.silver = 0
        denied = process_command(char, "sell canoe")
        assert denied == "I'm afraid I don't have enough wealth to buy that."
        assert char.gold == 0
        assert canoe in char.inventory
        assert canoe not in keeper.inventory

        keeper.gold = 2
        keeper.silver = 0
        accepted = process_command(char, "sell canoe")
        silver_match = re.search(r"(\d+) silver", accepted)
        assert silver_match is not None
        silver = int(silver_match.group(1))

        gold_match = re.search(r"(\d+) gold", accepted)
        gold = int(gold_match.group(1)) if gold_match is not None else 0

        price = gold * 100 + silver
        assert _total_wealth(char) == price
        assert char.gold == price // 100
        assert char.silver == price % 100
        assert canoe not in char.inventory
        assert canoe in keeper.inventory
        assert keeper.gold == 0
        assert keeper.silver == 38
    finally:
        time_info.hour = previous_hour


def _setup_pet_shop(proto_level: int = 5) -> tuple[Character, Room, Room, MobIndex]:
    room_registry.clear()
    mob_registry.clear()
    character_registry.clear()

    storefront = Room(vnum=9600, name="Pet Shop Lobby")
    storefront.room_flags = int(RoomFlag.ROOM_PET_SHOP)
    kennel = Room(vnum=9601, name="Kennel")
    room_registry[storefront.vnum] = storefront
    room_registry[kennel.vnum] = kennel

    proto = MobIndex(vnum=9602, short_descr="a cuddly companion", player_name="companion pet")
    proto.description = "A bright-eyed pet watches you expectantly.\n"
    proto.level = proto_level
    proto.act_flags = int(ActFlag.PET)
    mob_registry[proto.vnum] = proto

    kennel_pet = MobInstance.from_prototype(proto)
    kennel.add_mob(kennel_pet)

    buyer = Character(name="Buyer", level=10, is_npc=False)
    buyer.gold = 5
    buyer.silver = 0
    storefront.add_character(buyer)
    character_registry.append(buyer)

    return buyer, storefront, kennel, proto


def test_pet_shop_purchase_creates_charmed_pet():
    rng_mm.seed_mm(1)
    buyer, storefront, _, proto = _setup_pet_shop()
    buyer.skills["haggle"] = 95

    response = do_buy(buyer, "companion Fluffy")

    assert response == "Enjoy your pet."
    assert buyer.gold == 2
    assert buyer.silver == 90
    assert buyer.messages[-3:] == [
        "You haggle the price down to 210 coins.",
        "companion pet Fluffy now follows you.",
        "Enjoy your pet.",
    ]

    pet = buyer.pet
    assert pet is not None
    assert pet.master is buyer
    assert pet.leader is buyer
    assert pet.messages[-2:] == [
        "You now follow Buyer.",
        "Buyer bought a cuddly companion as a pet.",
    ]
    assert pet in storefront.people
    assert pet.room is storefront
    assert pet in character_registry
    assert pet.short_descr == proto.short_descr
    assert pet.name.endswith("Fluffy")
    assert "I belong to Buyer" in pet.description
    assert pet.has_affect(AffectFlag.CHARM)
    assert pet.act & int(ActFlag.PET)
    assert pet.has_comm_flag(CommFlag.NOTELL)
    assert pet.has_comm_flag(CommFlag.NOSHOUT)
    assert pet.has_comm_flag(CommFlag.NOCHANNELS)


def test_pet_shop_rejects_second_pet():
    rng_mm.seed_mm(5)
    buyer, storefront, kennel, proto = _setup_pet_shop()

    first_purchase = do_buy(buyer, "companion")
    assert first_purchase == "Enjoy your pet."
    original_pet = buyer.pet
    assert original_pet is not None

    second_attempt = do_buy(buyer, "companion")
    assert second_attempt == "You already own a pet."
    assert buyer.pet is original_pet
    assert sum(1 for entry in character_registry if getattr(entry, "master", None) is buyer) == 1
    assert isinstance(kennel.people[0], MobInstance)
    assert int(getattr(proto, "act_flags", 0) or 0) & int(ActFlag.PET)
