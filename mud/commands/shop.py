"""Shop command handlers."""

from mud.registry import shop_registry
from mud.models.character import Character
from mud.math.c_compat import c_div


def _find_shopkeeper(char: Character):
    for mob in getattr(char.room, "people", []):
        proto = getattr(mob, "prototype", None)
        if proto and proto.vnum in shop_registry:
            return mob
    return None


def _get_shop(keeper):
    proto = getattr(keeper, "prototype", None)
    if proto:
        return shop_registry.get(proto.vnum)
    return None


def do_list(char: Character, args: str = "") -> str:
    keeper = _find_shopkeeper(char)
    if not keeper:
        return "You can't do that here."
    shop = _get_shop(keeper)
    if not shop:
        return "You can't do that here."
    if not keeper.inventory:
        return "The shop is out of stock."
    items = []
    for obj in keeper.inventory:
        name = obj.short_descr or obj.name or "item"
        base_cost = getattr(obj.prototype, "cost", 0)
        price = c_div(base_cost * shop.profit_buy, 100)
        items.append(f"{name} {price} gold")
    return "Items for sale: " + ", ".join(items)


def do_buy(char: Character, args: str) -> str:
    if not args:
        return "Buy what?"
    keeper = _find_shopkeeper(char)
    if not keeper:
        return "You can't do that here."
    shop = _get_shop(keeper)
    if not shop:
        return "You can't do that here."
    name = args.lower()
    for obj in list(keeper.inventory):
        obj_name = (obj.short_descr or obj.name or "").lower()
        if name in obj_name:
            base_cost = getattr(obj.prototype, "cost", 0)
            price = c_div(base_cost * shop.profit_buy, 100)
            if char.gold < price:
                return "You can't afford that."
            char.gold -= price
            keeper.inventory.remove(obj)
            char.add_object(obj)
            return f"You buy {obj.short_descr or obj.name} for {price} gold."
    return "The shopkeeper doesn't sell that."


def do_sell(char: Character, args: str) -> str:
    if not args:
        return "Sell what?"
    keeper = _find_shopkeeper(char)
    if not keeper:
        return "You can't do that here."
    shop = _get_shop(keeper)
    if not shop:
        return "You can't do that here."
    name = args.lower()
    for obj in list(char.inventory):
        obj_name = (obj.short_descr or obj.name or "").lower()
        if name in obj_name:
            item_type = getattr(obj.prototype, "item_type", 0)
            if shop.buy_types and item_type not in shop.buy_types:
                return "The shopkeeper doesn't buy that."
            base_cost = getattr(obj.prototype, "cost", 0)
            price = c_div(base_cost * shop.profit_sell, 100)
            char.gold += price
            char.inventory.remove(obj)
            keeper.inventory.append(obj)
            return f"You sell {obj.short_descr or obj.name} for {price} gold."
    return "You don't have that."
