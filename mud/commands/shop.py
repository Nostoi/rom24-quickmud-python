"""Shop command handlers."""

from mud.registry import shop_registry
from mud.models.character import Character
from mud.models.object import Object
from mud.models.constants import ItemType
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


def _get_cost(keeper, obj: Object, *, buy: bool) -> int:
    """Compute ROM-like shop price for an object.

    Mirrors src/act_obj.c:get_cost:
    - buy: base = obj.cost * profit_buy / 100
    - sell: base = obj.cost * profit_sell / 100 if type accepted; otherwise 0
    - inventory discount on sell when keeper already has same item:
        - if existing copy has ITEM_INVENTORY → base /= 2
        - else → base = base * 3 / 4
    - wand/staff charge scaling: value[1]==0 → base/=4; else base = base * value[2] / value[1]
    """
    proto = obj.prototype
    shop = _get_shop(keeper)
    if not shop:
        return 0
    cost = 0
    if buy:
        cost = c_div(getattr(proto, "cost", 0) * shop.profit_buy, 100)
    else:
        # ensure shop buys this type
        item_type = getattr(proto, "item_type", 0)
        if shop.buy_types and item_type not in shop.buy_types:
            return 0
        cost = c_div(getattr(proto, "cost", 0) * shop.profit_sell, 100)
        # inventory discount if keeper already has same item
        for other in getattr(keeper, "inventory", []) or []:
            op = getattr(other, "prototype", None)
            if not op:
                continue
            if op is proto or (
                getattr(op, "vnum", None) == getattr(proto, "vnum", None)
                and (getattr(op, "short_descr", None) or "") == (getattr(proto, "short_descr", None) or "")
            ):
                # treat bit 1<<18 as ITEM_INVENTORY in this port
                ITEM_INVENTORY = 1 << 18
                if getattr(op, "extra_flags", 0) & ITEM_INVENTORY:
                    cost = c_div(cost, 2)
                else:
                    cost = c_div(cost * 3, 4)
                break

    # Charge scaling for wand/staff
    if getattr(proto, "item_type", 0) in (int(ItemType.WAND), int(ItemType.STAFF)):
        vals = getattr(proto, "value", [0, 0, 0, 0, 0])
        total = vals[1]
        rem = vals[2]
        if total == 0:
            cost = c_div(cost, 4)
        elif total > 0:
            cost = c_div(cost * rem, total)
    return max(0, int(cost))


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
        price = _get_cost(keeper, obj, buy=True)
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
            price = _get_cost(keeper, obj, buy=True)
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
            price = _get_cost(keeper, obj, buy=False)
            if price <= 0:
                return "The shopkeeper doesn't buy that."
            char.gold += price
            char.inventory.remove(obj)
            keeper.inventory.append(obj)
            return f"You sell {obj.short_descr or obj.name} for {price} gold."
    return "You don't have that."
