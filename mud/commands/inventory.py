from mud.models.character import Character


def do_get(char: Character, args: str) -> str:
    if not args:
        return "Get what?"
    name = args.lower()
    for obj in list(char.room.contents):
        obj_name = (obj.short_descr or obj.name or "").lower()
        if name in obj_name:
            char.room.contents.remove(obj)
            char.add_object(obj)
            return f"You pick up {obj.short_descr or obj.name}."
    return "You don't see that here."


def do_drop(char: Character, args: str) -> str:
    if not args:
        return "Drop what?"
    name = args.lower()
    for obj in list(char.inventory):
        obj_name = (obj.short_descr or obj.name or "").lower()
        if name in obj_name:
            char.inventory.remove(obj)
            char.room.add_object(obj)
            return f"You drop {obj.short_descr or obj.name}."
    return "You aren't carrying that."


def do_inventory(char: Character, args: str = "") -> str:
    if not char.inventory:
        return "You are carrying nothing."
    return "You are carrying: " + ", ".join(obj.short_descr or obj.name or "object" for obj in char.inventory)


def do_equipment(char: Character, args: str = "") -> str:
    if not char.equipment:
        return "You are wearing nothing."
    parts = []
    for slot, obj in char.equipment.items():
        parts.append(f"{slot}: {obj.short_descr or obj.name or 'object'}")
    return "You are using: " + ", ".join(parts)
