"""
Liquid container commands - fill and pour.

ROM Reference: src/act_obj.c do_fill (lines 965-1032), do_pour (lines 1033-1160)
"""
from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ItemType, LIQUID_TABLE
from mud.world.obj_find import get_obj_carry, get_obj_here


def do_fill(char: Character, args: str) -> str:
    """
    Fill a drink container from a fountain.
    
    ROM Reference: src/act_obj.c do_fill (lines 965-1032)
    
    Usage: fill <container>
    
    Drink containers have value array:
    - value[0]: max capacity
    - value[1]: current amount
    - value[2]: liquid type (index into LIQUID_TABLE)
    - value[3]: poisoned flag
    """
    container_name = (args or "").strip()
    
    if not container_name:
        return "Fill what?"
    
    # Find container in inventory
    obj = get_obj_carry(char, container_name)
    if obj is None:
        return "You do not have that item."
    
    # Find fountain in room
    room = getattr(char, "room", None)
    if not room:
        return "You are nowhere."
    
    fountain = None
    for content in getattr(room, "contents", []):
        item_type = getattr(content, "item_type", 0)
        if item_type == ItemType.FOUNTAIN:
            fountain = content
            break
    
    if fountain is None:
        return "There is no fountain here!"
    
    # Check if it's a drink container
    obj_type = getattr(obj, "item_type", 0)
    if obj_type != ItemType.DRINK_CON:
        return "You can't fill that."
    
    # Get container values
    obj_value = getattr(obj, "value", [0, 0, 0, 0, 0])
    if not isinstance(obj_value, list):
        obj_value = [0, 0, 0, 0, 0]
    
    fountain_value = getattr(fountain, "value", [0, 0, 0, 0, 0])
    if not isinstance(fountain_value, list):
        fountain_value = [0, 0, 0, 0, 0]
    
    max_capacity = obj_value[0] if len(obj_value) > 0 else 0
    current_amount = obj_value[1] if len(obj_value) > 1 else 0
    obj_liquid = obj_value[2] if len(obj_value) > 2 else 0
    fountain_liquid = fountain_value[2] if len(fountain_value) > 2 else 0
    
    # Check for incompatible liquids
    if current_amount != 0 and obj_liquid != fountain_liquid:
        return "There is already another liquid in it."
    
    # Check if already full
    if current_amount >= max_capacity:
        return "Your container is full."
    
    # Fill the container
    obj_value[2] = fountain_liquid
    obj_value[1] = max_capacity
    obj.value = obj_value
    
    # Get liquid name
    liquid_name = _get_liquid_name(fountain_liquid)
    
    obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "container")
    fountain_name = getattr(fountain, "short_descr", None) or getattr(fountain, "name", "fountain")
    
    return f"You fill {obj_name} with {liquid_name} from {fountain_name}."


def do_pour(char: Character, args: str) -> str:
    """
    Pour liquid from one container to another, or pour out.
    
    ROM Reference: src/act_obj.c do_pour (lines 1033-1160)
    
    Usage:
    - pour <container> out - Empty container on ground
    - pour <container> <target> - Pour into another container
    - pour <container> <character> - Pour into what character is holding
    """
    parts = (args or "").strip().split(None, 1)
    
    if len(parts) < 2:
        return "Pour what into what?"
    
    source_name = parts[0]
    target_arg = parts[1]
    
    # Find source container in inventory
    source = get_obj_carry(char, source_name)
    if source is None:
        return "You don't have that item."
    
    source_type = getattr(source, "item_type", 0)
    if source_type != ItemType.DRINK_CON:
        return "That's not a drink container."
    
    source_value = getattr(source, "value", [0, 0, 0, 0, 0])
    if not isinstance(source_value, list):
        source_value = [0, 0, 0, 0, 0]
    
    # Handle "pour out"
    if target_arg.lower() == "out":
        return _pour_out(char, source, source_value)
    
    # Find target (container in room or character holding something)
    target = get_obj_here(char, target_arg)
    target_char = None
    
    if target is None:
        # Try to find a character and use what they're holding
        from mud.world.char_find import get_char_room
        target_char = get_char_room(char, target_arg)
        
        if target_char is None:
            return "Pour into what?"
        
        # Get what they're holding
        equipped = getattr(target_char, "equipped", {})
        target = equipped.get("held") or equipped.get("hold")
        
        if target is None:
            return "They aren't holding anything."
    
    target_type = getattr(target, "item_type", 0)
    if target_type != ItemType.DRINK_CON:
        return "You can only pour into other drink containers."
    
    if target is source:
        return "You cannot change the laws of physics!"
    
    target_value = getattr(target, "value", [0, 0, 0, 0, 0])
    if not isinstance(target_value, list):
        target_value = [0, 0, 0, 0, 0]
    
    source_liquid = source_value[2] if len(source_value) > 2 else 0
    target_liquid = target_value[2] if len(target_value) > 2 else 0
    source_amount = source_value[1] if len(source_value) > 1 else 0
    target_amount = target_value[1] if len(target_value) > 1 else 0
    target_max = target_value[0] if len(target_value) > 0 else 0
    
    # Check liquid compatibility
    if target_amount != 0 and target_liquid != source_liquid:
        return "They don't hold the same liquid."
    
    # Check if source is empty
    if source_amount == 0:
        source_name_str = getattr(source, "short_descr", None) or getattr(source, "name", "container")
        return f"There's nothing in {source_name_str} to pour."
    
    # Check if target is full
    if target_amount >= target_max:
        target_name_str = getattr(target, "short_descr", None) or getattr(target, "name", "container")
        return f"{target_name_str} is already filled to the top."
    
    # Calculate amount to pour
    amount = min(source_amount, target_max - target_amount)
    
    # Update values
    target_value[1] = target_amount + amount
    target_value[2] = source_liquid
    source_value[1] = source_amount - amount
    
    target.value = target_value
    source.value = source_value
    
    liquid_name = _get_liquid_name(source_liquid)
    source_name_str = getattr(source, "short_descr", None) or getattr(source, "name", "container")
    target_name_str = getattr(target, "short_descr", None) or getattr(target, "name", "container")
    
    if target_char:
        char_name = getattr(target_char, "name", "them")
        return f"You pour some {liquid_name} for {char_name}."
    else:
        return f"You pour {liquid_name} from {source_name_str} into {target_name_str}."


def _pour_out(char: Character, source, source_value: list) -> str:
    """Pour out a container onto the ground."""
    source_amount = source_value[1] if len(source_value) > 1 else 0
    
    if source_amount == 0:
        return "It's already empty."
    
    source_liquid = source_value[2] if len(source_value) > 2 else 0
    liquid_name = _get_liquid_name(source_liquid)
    
    # Empty the container
    source_value[1] = 0
    source_value[3] = 0  # Clear poisoned flag
    source.value = source_value
    
    source_name_str = getattr(source, "short_descr", None) or getattr(source, "name", "container")
    
    return f"You invert {source_name_str}, spilling {liquid_name} all over the ground."


def do_empty(char: Character, args: str) -> str:
    """
    Alias for 'pour <container> out'.
    
    Usage: empty <container>
    """
    container_name = (args or "").strip()
    
    if not container_name:
        return "Empty what?"
    
    return do_pour(char, f"{container_name} out")


def _get_liquid_name(liquid_index: int) -> str:
    """Get liquid name from LIQUID_TABLE."""
    if 0 <= liquid_index < len(LIQUID_TABLE):
        return LIQUID_TABLE[liquid_index].name
    return "water"


def _get_liquid_color(liquid_index: int) -> str:
    """Get liquid color from LIQUID_TABLE."""
    if 0 <= liquid_index < len(LIQUID_TABLE):
        return LIQUID_TABLE[liquid_index].color
    return "clear"
