from mud.models.character import Character
from mud.registry import shop_registry


def _find_shopkeeper(char: Character):
    for mob in getattr(char.room, "people", []):
        proto = getattr(mob, "prototype", None)
        if proto and proto.vnum in shop_registry:
            return mob
    return None


def do_list(char: Character, args: str = "") -> str:
    keeper = _find_shopkeeper(char)
    if not keeper:
        return "You can't do that here."
    if not keeper.inventory:
        return "The shop is out of stock."
    items = []
    for obj in keeper.inventory:
        name = obj.short_descr or obj.name or "item"
        cost = getattr(obj.prototype, "cost", 0)
        items.append(f"{name} {cost} gold")
    return "Items for sale: " + ", ".join(items)


def do_buy(char: Character, args: str) -> str:
    if not args:
        return "Buy what?"
    keeper = _find_shopkeeper(char)
    if not keeper:
        return "You can't do that here."
    name = args.lower()
    for obj in list(keeper.inventory):
        obj_name = (obj.short_descr or obj.name or "").lower()
        if name in obj_name:
            cost = getattr(obj.prototype, "cost", 0)
            if char.gold < cost:
                return "You can't afford that."
            char.gold -= cost
            keeper.inventory.remove(obj)
            char.add_object(obj)
            return f"You buy {obj.short_descr or obj.name} for {cost} gold."
    return "The shopkeeper doesn't sell that."
