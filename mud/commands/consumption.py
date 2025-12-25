"""
Consumption commands for eat and drink.

ROM References: src/act_obj.c lines 300-600
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.constants import ItemType, Position

if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.object import Object


def do_eat(ch: Character, args: str) -> str:
    """
    Consume food to restore hunger.

    ROM Reference: src/act_obj.c lines 343-430 (do_eat)
    """
    args = args.strip()

    if not args:
        return "Eat what?"

    # Find object in inventory
    obj = _find_obj_inventory(ch, args)
    if not obj:
        return "You do not have that item."

    # Check if it's food
    item_type = getattr(obj, "item_type", ItemType.TRASH)
    if item_type != ItemType.FOOD:
        return "That's not edible."

    # Check position
    if ch.position < Position.RESTING:
        return "You can't do that right now."

    # Eat the food
    obj_name = getattr(obj, "short_descr", "something")
    messages = [f"You eat {obj_name}."]

    # Restore hunger (if character has condition tracking)
    if hasattr(ch, "condition") and isinstance(getattr(ch, "condition", None), dict):
        food_value = getattr(obj, "value", [0, 0, 0, 0])
        if isinstance(food_value, list) and len(food_value) > 0:
            hunger_gain = food_value[0] if food_value[0] > 0 else 5
            ch.condition["hunger"] = min(48, ch.condition.get("hunger", 0) + hunger_gain)

            if ch.condition["hunger"] >= 40:
                messages.append("You are full.")

    # Check for poison
    if hasattr(obj, "value") and isinstance(obj.value, list) and len(obj.value) > 3:
        if obj.value[3] != 0:  # Poisoned food
            messages.append("You choke and gag.")
            messages.append("You feel poison coursing through your veins.")

            # Apply poison effect
            if hasattr(ch, "add_affect"):
                from mud.models.constants import AffectFlag

                # Create poison affect
                try:
                    ch.add_affect(
                        {
                            "type": "poison",
                            "duration": 3,
                            "modifier": -2,
                            "location": "strength",
                            "bitvector": int(AffectFlag.POISON),
                        }
                    )
                except Exception:
                    pass  # Poison application failed

    # Destroy the food object
    _destroy_object(ch, obj)

    return "\n".join(messages)


def do_drink(ch: Character, args: str) -> str:
    """
    Drink from a container or fountain.

    ROM Reference: src/act_obj.c lines 432-590 (do_drink)
    """
    args = args.strip()

    if not args:
        return "Drink what?"

    # Check for fountain in room first
    room = getattr(ch, "room", None)
    if args.lower() in ["fountain", "from fountain"]:
        if room:
            # Look for fountain object in room
            for obj in getattr(room, "objects", []):
                item_type = getattr(obj, "item_type", ItemType.TRASH)
                if item_type == ItemType.FOUNTAIN:
                    return _drink_from_fountain(ch, obj)
        return "You can't find a fountain here."

    # Find object in inventory
    obj = _find_obj_inventory(ch, args)
    if not obj:
        return "You do not have that item."

    # Check if it's drinkable
    item_type = getattr(obj, "item_type", ItemType.TRASH)
    if item_type not in (ItemType.DRINK_CON, ItemType.FOUNTAIN):
        return "You can't drink from that."

    # Check position
    if ch.position < Position.RESTING:
        return "You can't do that right now."

    # Check if empty
    value = getattr(obj, "value", [0, 0, 0, 0])
    if not isinstance(value, list) or len(value) < 2:
        return "It is empty."

    quantity = value[1] if len(value) > 1 else 0
    if quantity <= 0:
        return "It is empty."

    # Drink from it
    obj_name = getattr(obj, "short_descr", "something")
    liquid_type = value[2] if len(value) > 2 else 0
    liquid_name = _get_liquid_name(liquid_type)

    messages = [f"You drink {liquid_name} from {obj_name}."]

    # Restore thirst
    if hasattr(ch, "condition") and isinstance(getattr(ch, "condition", None), dict):
        thirst_value = 10  # Standard drink amount
        ch.condition["thirst"] = min(48, ch.condition.get("thirst", 0) + thirst_value)

        if ch.condition["thirst"] >= 40:
            messages.append("You do not feel thirsty.")

    # Reduce quantity in container
    if item_type == ItemType.DRINK_CON:
        value[1] = max(0, value[1] - 1)
        if value[1] <= 0:
            messages.append(f"{obj_name.capitalize()} is now empty.")

    # Check for poison
    if len(value) > 3 and value[3] != 0:  # Poisoned drink
        messages.append("You choke and gag.")
        messages.append("You feel poison coursing through your veins.")

        # Apply poison effect
        if hasattr(ch, "add_affect"):
            from mud.models.constants import AffectFlag

            try:
                ch.add_affect(
                    {
                        "type": "poison",
                        "duration": 3,
                        "modifier": -2,
                        "location": "strength",
                        "bitvector": int(AffectFlag.POISON),
                    }
                )
            except Exception:
                pass

    return "\n".join(messages)


def _drink_from_fountain(ch: Character, fountain: Object) -> str:
    """Drink from a fountain object."""
    value = getattr(fountain, "value", [0, 0, 0, 0])
    liquid_type = value[2] if len(value) > 2 else 0
    liquid_name = _get_liquid_name(liquid_type)

    messages = [f"You drink {liquid_name} from the fountain."]

    # Restore thirst
    if hasattr(ch, "condition") and isinstance(getattr(ch, "condition", None), dict):
        ch.condition["thirst"] = min(48, ch.condition.get("thirst", 0) + 10)

        if ch.condition["thirst"] >= 40:
            messages.append("You do not feel thirsty.")

    # Check for poison (fountains can be poisoned)
    if len(value) > 3 and value[3] != 0:
        messages.append("You choke and gag.")
        messages.append("You feel poison coursing through your veins.")

    return "\n".join(messages)


def _get_liquid_name(liquid_type: int) -> str:
    """Get the name of a liquid type."""
    liquids = {
        0: "water",
        1: "beer",
        2: "red wine",
        3: "ale",
        4: "dark ale",
        5: "whisky",
        6: "lemonade",
        7: "firebreather",
        8: "local specialty",
        9: "slime mold juice",
        10: "milk",
        11: "tea",
        12: "coffee",
        13: "blood",
        14: "salt water",
        15: "coke",
    }
    return liquids.get(liquid_type, "water")


def _find_obj_inventory(ch: Character, name: str) -> Object | None:
    """Find an object in character's inventory by name."""
    inventory = getattr(ch, "carrying", [])
    if not inventory or not name:
        return None

    name_lower = name.lower()
    for obj in inventory:
        # Check short description
        short_descr = getattr(obj, "short_descr", "")
        if name_lower in short_descr.lower():
            return obj

        # Check name
        obj_name = getattr(obj, "name", "")
        if name_lower in obj_name.lower():
            return obj

    return None


def _destroy_object(ch: Character, obj: Object) -> None:
    """Remove an object from character's inventory and destroy it."""
    inventory = getattr(ch, "carrying", [])
    if obj in inventory:
        inventory.remove(obj)

    # Update carry weight and count
    if hasattr(ch, "carry_weight"):
        obj_weight = getattr(obj, "weight", 0)
        ch.carry_weight = max(0, ch.carry_weight - obj_weight)

    if hasattr(ch, "carry_number"):
        ch.carry_number = max(0, ch.carry_number - 1)
