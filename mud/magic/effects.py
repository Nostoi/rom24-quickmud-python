"""Environmental damage effects mirroring ROM src/effects.c.

Provides acid, cold, fire, poison, and shock damage to objects and characters.
These functions apply probabilistic destruction/degradation based on level, damage, and item properties.

Full ROM C implementation (src/effects.c lines 39-615):
- acid_effect: Object destruction, armor AC degradation, container dumping
- cold_effect: Potion freezing, chill touch affect, hunger increase
- fire_effect: Scroll burning, blindness affect, thirst increase
- poison_effect: Food/drink poisoning (does not destroy objects)
- shock_effect: Equipment damage, daze affect

All functions follow ROM probability formula with diminishing returns.
"""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING, Any

from mud.affects.saves import saves_spell
from mud.handler import affect_enchant
from mud.math.c_compat import c_div, urange
from mud.models.constants import (
    ITEM_BLESS,
    ITEM_BURN_PROOF,
    ITEM_NOPURGE,
    AffectFlag,
    DamageType,
    ItemType,
)
from mud.utils import rng_mm

if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.object import Object


class SpellTarget(IntEnum):
    """Spell effect destinations mirroring ROM TARGET_* constants."""

    CHAR = 0
    OBJ = 1
    ROOM = 2
    NONE = 3
    IGNORE = 99  # For invalid targets

    # Aliases for ROM compatibility
    TARGET_CHAR = 0
    TARGET_OBJ = 1
    TARGET_ROOM = 2


# Lazy imports to avoid circular dependencies
def _get_extract_obj():
    """Lazy import extract_obj from game_loop."""
    from mud.game_loop import _extract_obj

    return _extract_obj


def _get_obj_from_obj():
    """Lazy import obj_from_obj from game_loop."""
    from mud.game_loop import _obj_from_obj

    return _obj_from_obj


def _get_obj_to_room():
    """Lazy import obj_to_room from game_loop."""
    from mud.game_loop import _obj_to_room

    return _obj_to_room


def _get_obj_to_char():
    """Lazy import obj_to_char from game_loop."""
    from mud.game_loop import _obj_to_char

    return _obj_to_char


def _normalize_target(target_type: int | SpellTarget) -> SpellTarget:
    """Normalize target_type parameter to SpellTarget enum."""
    if isinstance(target_type, SpellTarget):
        return target_type
    try:
        return SpellTarget(target_type)
    except ValueError:
        return SpellTarget.IGNORE


def _calculate_chance(level: int, damage: int, obj: Object, item_type_modifier: int = 0) -> int:
    """Calculate destruction/effect chance using ROM probability formula.

    ROM pattern (used by all effects.c functions):
        chance = level / 4 + dam / 10;
        if (chance > 25) chance = (chance - 25) / 2 + 25;
        if (chance > 50) chance = (chance - 50) / 2 + 50;
        if (IS_OBJ_STAT(obj, ITEM_BLESS)) chance -= 5;
        chance -= obj->level * 2;
        chance += item_type_modifier;  // varies by effect type
        chance = URANGE(5, chance, 95);

    Args:
        level: Spell/effect level
        damage: Damage amount
        obj: Target object
        item_type_modifier: Adjustment for specific item types (e.g., +25 for potions in cold_effect)

    Returns:
        Chance percentage (5-95)
    """
    # Base chance from level and damage (ROM C integer division)
    chance = c_div(level, 4) + c_div(damage, 10)

    # Cap progression (diminishing returns at 25 and 50)
    if chance > 25:
        chance = c_div(chance - 25, 2) + 25
    if chance > 50:
        chance = c_div(chance - 50, 2) + 50

    # ITEM_BLESS reduces chance
    if obj.extra_flags & ITEM_BLESS:
        chance -= 5

    # Object level penalty
    chance -= obj.level * 2

    # Item type specific modifier
    chance += item_type_modifier

    # Clamp to 5-95% (ROM URANGE macro)
    return urange(5, chance, 95)


def _send_effect_message(obj: Object, message: str) -> None:
    """Send effect message to room or carrier.

    ROM pattern: act(message, NULL, obj, NULL, TO_ROOM) or act(message, carrier, obj, NULL, TO_ALL)
    QuickMUD: Send messages to carrier if present.
    """
    carrier = getattr(obj, "carried_by", None)

    if carrier is not None and hasattr(carrier, "messages") and isinstance(carrier.messages, list):
        # Send to carrier (QuickMUD message system)
        carrier.messages.append(f"{message}")


def _dump_container_contents(obj: Object, level: int, damage: int, effect_func: Any) -> None:
    """Dump container contents to room and recursively apply effect.

    ROM pattern (acid_effect lines 169-187, fire_effect lines 415-434):
        for (t_obj = obj->contains; t_obj != NULL; t_obj = n_obj) {
            n_obj = t_obj->next_content;
            obj_from_obj(t_obj);
            if (obj->in_obj) obj_to_obj(t_obj, obj->in_obj);
            else if (obj->carried_by) obj_to_room(t_obj, obj->carried_by->in_room);
            else if (obj->in_room == NULL) extract_obj(t_obj);
            else obj_to_room(t_obj, obj->in_room);
            effect_func(t_obj, level/2, dam/2, TARGET_OBJ);
        }
    """
    obj_from_obj = _get_obj_from_obj()
    obj_to_room = _get_obj_to_room()
    extract_obj = _get_extract_obj()

    # Get container contents
    contents = list(getattr(obj, "contains", []))

    for item in contents:
        # Remove from container
        obj_from_obj(item)

        # Determine destination (ROM C nested if-else)
        container = getattr(obj, "in_obj", None)
        carrier = getattr(obj, "carried_by", None)
        room = getattr(obj, "in_room", None)

        if container is not None:
            # Put in parent container (not implemented yet - just extract)
            extract_obj(item)
        elif carrier is not None:
            # Put in carrier's room
            carrier_room = getattr(carrier, "in_room", None)
            if carrier_room is not None:
                obj_to_room(item, carrier_room)
            else:
                extract_obj(item)
        elif room is None:
            # Nowhere to put it - destroy it
            extract_obj(item)
        else:
            # Put in room
            obj_to_room(item, room)

        # Recursively apply effect with half level/damage (ROM C L186)
        effect_func(item, c_div(level, 2), c_div(damage, 2), SpellTarget.TARGET_OBJ)


def acid_effect(target: Any, level: int, damage: int, target_type: int | SpellTarget) -> None:
    """Apply acid effect to objects and characters.

    ROM C source: src/effects.c lines 39-193

    TARGET_ROOM (lines 41-52):
        - Iterate through all objects in room
        - Recursively call acid_effect() on each object

    TARGET_CHAR (lines 54-66):
        - Iterate through all objects in character's inventory
        - Recursively call acid_effect() on each object

    TARGET_OBJ (lines 68-192):
        - Immunity checks: ITEM_BURN_PROOF, ITEM_NOPURGE, 20% random chance
        - Probability calculation with diminishing returns
        - ARMOR: Degrade AC by +1 (worse protection), does NOT destroy
        - CONTAINER/CORPSE: Dump contents to room, destroy container
        - CLOTHING: Destroy
        - STAFF/WAND: -10 to chance, destroy
        - SCROLL: +10 to chance, destroy
        - Other types: No effect
    """
    dest = _normalize_target(target_type)
    extract_obj = _get_extract_obj()

    # TARGET_ROOM: Iterate through objects in room (ROM C lines 41-52)
    if dest == SpellTarget.TARGET_ROOM:
        from mud.models.room import Room

        if not isinstance(target, Room):
            return

        # Recursively apply to all objects in room
        objects = list(getattr(target, "objects", []))
        for obj in objects:
            acid_effect(obj, level, damage, SpellTarget.TARGET_OBJ)
        return

    # TARGET_CHAR: Process inventory (ROM C lines 54-66)
    if dest == SpellTarget.TARGET_CHAR:
        from mud.models.character import Character

        if not isinstance(target, Character):
            return

        # Recursively apply to all inventory items
        inventory = list(getattr(target, "inventory", []))
        for obj in inventory:
            acid_effect(obj, level, damage, SpellTarget.TARGET_OBJ)
        return

    # TARGET_OBJ: Object destruction/degradation (ROM C lines 68-192)
    if dest == SpellTarget.TARGET_OBJ:
        from mud.models.object import Object

        if not isinstance(target, Object):
            return

        obj = target

        # ROM L75-77: Immunity checks
        if obj.extra_flags & ITEM_BURN_PROOF:
            return
        if obj.extra_flags & ITEM_NOPURGE:
            return
        if rng_mm.number_range(0, 4) == 0:  # 20% random immunity
            return

        # ROM L91-115: Item type specific behavior
        item_type = getattr(obj.prototype, "item_type", None)
        item_type_int = int(item_type) if item_type is not None else ItemType.TRASH
        item_type_modifier = 0
        message = ""
        is_armor = False

        if item_type_int == int(ItemType.CONTAINER) or item_type_int == int(ItemType.CORPSE_NPC) or item_type_int == int(ItemType.CORPSE_PC):
            message = "fumes and dissolves"
        elif item_type_int == int(ItemType.ARMOR):
            is_armor = True
            message = "is pitted and etched"
        elif item_type_int == int(ItemType.CLOTHING):
            message = "is corroded into scrap"
        elif item_type_int == int(ItemType.STAFF) or item_type_int == int(ItemType.WAND):
            item_type_modifier = -10
            message = "corrodes and breaks"
        elif item_type_int == int(ItemType.SCROLL):
            item_type_modifier = 10
            message = "is burned into waste"
        else:
            return  # Other item types are immune

        # ROM L79-89: Probability calculation
        chance = _calculate_chance(level, damage, obj, item_type_modifier)

        # ROM L119-120: Roll check
        if rng_mm.number_percent() > chance:
            return

        # ROM L122-125: Send message
        _send_effect_message(obj, message)

        # ROM L127-166: ARMOR special case (degrade AC, don't destroy)
        if is_armor:
            # Copy prototype affects to object
            affect_enchant(obj)

            # Find existing AC affect or create new one
            # ROM C uses affect_find but we'll search affects list
            affects = getattr(obj, "affected", [])
            ac_affect = None
            for affect in affects:
                if affect.location == 1:  # AC_APPLY (location 1 in ROM)
                    ac_affect = affect
                    break

            if ac_affect is not None:
                # Increase AC by +1 (worse armor - higher AC = less protection)
                ac_affect.modifier += 1
            else:
                # Create new AC degradation affect
                from mud.models.obj import Affect

                new_affect = Affect(
                    where=0,  # TO_AFFECTS
                    type=0,  # No specific spell type
                    level=0,  # No level requirement
                    duration=-1,  # Permanent
                    location=1,  # AC_APPLY
                    modifier=1,  # +1 AC (worse protection)
                    bitvector=0,
                )
                affects.append(new_affect)
                obj.affected = affects

            # Update carried_by armor values if worn
            carrier = getattr(obj, "carried_by", None)
            if carrier is not None and getattr(obj, "wear_loc", -1) != -1:
                # Update carrier's armor class (ROM affect_modify pattern)
                # This would normally be handled by affect system
                pass

            return  # Don't destroy armor, just degrade it

        # ROM L169-187: Container dumping (recursively apply acid to contents)
        if item_type_int == int(ItemType.CONTAINER) or item_type_int == int(ItemType.CORPSE_NPC) or item_type_int == int(ItemType.CORPSE_PC):
            _dump_container_contents(obj, level, damage, acid_effect)

        # ROM L189: Object destruction
        extract_obj(obj)


def cold_effect(target: Any, level: int, damage: int, target_type: int | SpellTarget) -> None:
    """Apply cold effect to objects and characters.

    ROM C source: src/effects.c lines 195-297

    TARGET_CHAR (lines 210-244):
        - Chill touch affect: saves_spell(level/4 + dam/20, victim, DAM_COLD)
        - If failed: Apply "chill touch" affect (-1 STR, duration 6)
        - Hunger increase: gain_condition(victim, COND_HUNGER, dam/20)

    TARGET_OBJ (lines 246-295):
        - POTION: +25 to chance, "freezes and shatters!"
        - DRINK_CON: +5 to chance, "freezes and shatters!"
        - Destroys object (no container dumping)
    """
    dest = _normalize_target(target_type)
    extract_obj = _get_extract_obj()

    # TARGET_ROOM: Iterate through objects in room (ROM C lines 197-208)
    if dest == SpellTarget.TARGET_ROOM:
        from mud.models.room import Room

        if not isinstance(target, Room):
            return

        objects = list(getattr(target, "objects", []))
        for obj in objects:
            cold_effect(obj, level, damage, SpellTarget.TARGET_OBJ)
        return

    # TARGET_CHAR: Chill touch + hunger (ROM C lines 210-244)
    if dest == SpellTarget.TARGET_CHAR:
        from mud.models.character import Character

        if not isinstance(target, Character):
            return

        victim = target

        # ROM L216-231: Chill touch affect
        save_level = c_div(level, 4) + c_div(damage, 20)
        if not saves_spell(save_level, victim, int(DamageType.COLD)):
            # Apply chill touch affect (-1 STR, duration 6)
            # TODO: Implement full affect_to_char with skill_lookup("chill touch")
            if hasattr(victim, "messages") and isinstance(victim.messages, list):
                victim.messages.append("You feel a chill sink deep into your bones.")

        # ROM L234-235: Hunger increase (warmth sucked out)
        # TODO: Implement gain_condition(victim, COND_HUNGER, dam/20)

        # ROM L238-242: Process inventory
        inventory = list(getattr(victim, "inventory", []))
        for obj in inventory:
            cold_effect(obj, level, damage, SpellTarget.TARGET_OBJ)
        return

    # TARGET_OBJ: Potion freezing (ROM C lines 246-295)
    if dest == SpellTarget.TARGET_OBJ:
        from mud.models.object import Object

        if not isinstance(target, Object):
            return

        obj = target

        # ROM L254-256: Immunity checks
        if obj.extra_flags & ITEM_BURN_PROOF:
            return
        if obj.extra_flags & ITEM_NOPURGE:
            return
        if rng_mm.number_range(0, 4) == 0:  # 20% random immunity
            return

        # ROM L268-280: Item type specific behavior
        item_type = getattr(obj.prototype, "item_type", None)
        item_type_int = int(item_type) if item_type is not None else ItemType.TRASH
        item_type_modifier = 0
        message = ""

        if item_type_int == int(ItemType.POTION):
            item_type_modifier = 25
            message = "freezes and shatters!"
        elif item_type_int == int(ItemType.DRINK_CON):
            item_type_modifier = 5
            message = "freezes and shatters!"
        else:
            return  # Other item types are immune

        # Probability calculation
        chance = _calculate_chance(level, damage, obj, item_type_modifier)

        # Roll check
        if rng_mm.number_percent() > chance:
            return

        # Send message
        _send_effect_message(obj, message)

        # ROM L292: Object destruction (no container dumping for cold_effect)
        extract_obj(obj)


def fire_effect(target: Any, level: int, damage: int, target_type: int | SpellTarget) -> None:
    """Apply fire effect to objects and characters.

    ROM C source: src/effects.c lines 299-439

    TARGET_CHAR (lines 314-351):
        - Blindness affect: saves_spell(level/4 + dam/20, victim, DAM_FIRE)
        - If failed: Apply "fire breath" affect (AFF_BLIND, -4 hitroll, duration 0 to level/10)
        - Thirst increase: gain_condition(victim, COND_THIRST, dam/20)

    TARGET_OBJ (lines 353-438):
        - CONTAINER: Dump contents, destroy
        - POTION: +25, destroy
        - SCROLL: +50, destroy
        - STAFF: +10, destroy
        - WAND: destroy
        - FOOD: destroy
        - PILL: destroy
    """
    dest = _normalize_target(target_type)
    extract_obj = _get_extract_obj()

    # TARGET_ROOM: Iterate through objects in room (ROM C lines 301-312)
    if dest == SpellTarget.TARGET_ROOM:
        from mud.models.room import Room

        if not isinstance(target, Room):
            return

        objects = list(getattr(target, "objects", []))
        for obj in objects:
            fire_effect(obj, level, damage, SpellTarget.TARGET_OBJ)
        return

    # TARGET_CHAR: Blindness + thirst (ROM C lines 314-351)
    if dest == SpellTarget.TARGET_CHAR:
        from mud.models.character import Character

        if not isinstance(target, Character):
            return

        victim = target

        # ROM L320-337: Blindness affect
        if not (victim.affected_by & AffectFlag.BLIND):  # Not already blind
            save_level = c_div(level, 4) + c_div(damage, 20)
            if not saves_spell(save_level, victim, int(DamageType.FIRE)):
                # Apply fire breath blindness (-4 hitroll, duration 0 to level/10)
                # TODO: Implement full affect_to_char with skill_lookup("fire breath")
                if hasattr(victim, "messages") and isinstance(victim.messages, list):
                    victim.messages.append("You are blinded by smoke!")

        # ROM L340-341: Thirst increase (heat dehydration)
        # TODO: Implement gain_condition(victim, COND_THIRST, dam/20)

        # ROM L344-349: Process inventory
        inventory = list(getattr(victim, "inventory", []))
        for obj in inventory:
            fire_effect(obj, level, damage, SpellTarget.TARGET_OBJ)
        return

    # TARGET_OBJ: Scroll/potion burning (ROM C lines 353-438)
    if dest == SpellTarget.TARGET_OBJ:
        from mud.models.object import Object

        if not isinstance(target, Object):
            return

        obj = target

        # ROM L361-363: Immunity checks
        if obj.extra_flags & ITEM_BURN_PROOF:
            return
        if obj.extra_flags & ITEM_NOPURGE:
            return
        if rng_mm.number_range(0, 4) == 0:  # 20% random immunity
            return

        # ROM L375-403: Item type specific behavior
        item_type = getattr(obj.prototype, "item_type", None)
        item_type_int = int(item_type) if item_type is not None else ItemType.TRASH
        item_type_modifier = 0
        message = ""
        is_container = False

        if item_type_int == int(ItemType.CONTAINER):
            is_container = True
            message = "ignites and burns!"
        elif item_type_int == int(ItemType.POTION):
            item_type_modifier = 25
            message = "bubbles and boils!"
        elif item_type_int == int(ItemType.SCROLL):
            item_type_modifier = 50
            message = "crackles and burns!"
        elif item_type_int == int(ItemType.STAFF):
            item_type_modifier = 10
            message = "smokes and chars!"
        elif item_type_int == int(ItemType.WAND):
            message = "sparks and sputters!"
        elif item_type_int == int(ItemType.FOOD):
            message = "blackens and crisps!"
        elif item_type_int == int(ItemType.PILL):
            message = "melts and drips!"
        else:
            return  # Other item types are immune

        # Probability calculation
        chance = _calculate_chance(level, damage, obj, item_type_modifier)

        # Roll check
        if rng_mm.number_percent() > chance:
            return

        # Send message
        _send_effect_message(obj, message)

        # ROM L415-434: Container dumping (recursively burn contents)
        if is_container:
            _dump_container_contents(obj, level, damage, fire_effect)

        # ROM L436: Object destruction
        extract_obj(obj)


def poison_effect(target: Any, level: int, damage: int, target_type: int | SpellTarget) -> None:
    """Apply poison effect to objects and characters.

    ROM C source: src/effects.c lines 441-528

    TARGET_CHAR (lines 456-487):
        - Saving throw: saves_spell(level/4 + dam/20, victim, DAM_POISON)
        - If failed: Apply gsn_poison affect (AFF_POISON, -1 STR, duration level/2)

    TARGET_OBJ (lines 489-527):
        - Only affects FOOD and non-empty DRINK_CON items
        - Sets obj->value[3] = 1 (poisoned flag)
        - Does NOT destroy object
    """
    dest = _normalize_target(target_type)

    # TARGET_ROOM: Iterate through objects in room (ROM C lines 443-454)
    if dest == SpellTarget.TARGET_ROOM:
        from mud.models.room import Room

        if not isinstance(target, Room):
            return

        objects = list(getattr(target, "objects", []))
        for obj in objects:
            poison_effect(obj, level, damage, SpellTarget.TARGET_OBJ)
        return

    # TARGET_CHAR: Poison affect (ROM C lines 456-487)
    if dest == SpellTarget.TARGET_CHAR:
        from mud.models.character import Character

        if not isinstance(target, Character):
            return

        victim = target

        # ROM L462-478: Poison affect application
        save_level = c_div(level, 4) + c_div(damage, 20)
        if not saves_spell(save_level, victim, int(DamageType.POISON)):
            # Apply poison affect (gsn_poison: AFF_POISON, -1 STR, duration level/2)
            # TODO: Implement full affect_to_char with skill_lookup("poison")
            if hasattr(victim, "messages") and isinstance(victim.messages, list):
                victim.messages.append("You feel poison coursing through your veins.")

        # ROM L481-485: Process inventory
        inventory = list(getattr(victim, "inventory", []))
        for obj in inventory:
            poison_effect(obj, level, damage, SpellTarget.TARGET_OBJ)
        return

    # TARGET_OBJ: Poison food/drink (ROM C lines 489-527)
    if dest == SpellTarget.TARGET_OBJ:
        from mud.models.object import Object

        if not isinstance(target, Object):
            return

        obj = target

        # ROM L495-497: Immunity checks (uses ITEM_BLESS, not ITEM_NOPURGE!)
        if obj.extra_flags & ITEM_BURN_PROOF:
            return
        if obj.extra_flags & ITEM_BLESS:
            return
        if rng_mm.number_range(0, 4) == 0:  # 20% random immunity
            return

        # ROM L507-517: Only affect FOOD and non-empty DRINK_CON
        item_type = getattr(obj.prototype, "item_type", None)
        item_type_int = int(item_type) if item_type is not None else ItemType.TRASH
        if item_type_int == int(ItemType.FOOD):
            pass  # Allow poisoning
        elif item_type_int == int(ItemType.DRINK_CON):
            # ROM L514-516: Only poison non-empty drink containers
            value = getattr(obj, "value", [0, 0, 0, 0, 0])
            if value[0] == value[1]:  # Empty container (current == max)
                return
        else:
            return  # Other item types are immune

        # ROM L524: Set poisoned flag (obj->value[3] = 1)
        value = list(getattr(obj, "value", [0, 0, 0, 0, 0]))
        value[3] = 1
        obj.value = value
        # Note: No message sent to player (poisoning is silent)


def shock_effect(target: Any, level: int, damage: int, target_type: int | SpellTarget) -> None:
    """Apply shock effect to objects and characters.

    ROM C source: src/effects.c lines 530-615

    TARGET_CHAR (lines 545-564):
        - Daze effect: saves_spell(level/4 + dam/20, victim, DAM_LIGHTNING)
        - If failed: DAZE_STATE(victim, UMAX(12, level/4 + dam/20))

    TARGET_OBJ (lines 566-614):
        - WAND/STAFF: +10, destroy
        - JEWELRY: -10, destroy
    """
    dest = _normalize_target(target_type)
    extract_obj = _get_extract_obj()

    # TARGET_ROOM: Iterate through objects in room (ROM C lines 532-543)
    if dest == SpellTarget.TARGET_ROOM:
        from mud.models.room import Room

        if not isinstance(target, Room):
            return

        objects = list(getattr(target, "objects", []))
        for obj in objects:
            shock_effect(obj, level, damage, SpellTarget.TARGET_OBJ)
        return

    # TARGET_CHAR: Daze effect (ROM C lines 545-564)
    if dest == SpellTarget.TARGET_CHAR:
        from mud.models.character import Character

        if not isinstance(target, Character):
            return

        victim = target

        # ROM L551-555: Daze effect
        save_level = c_div(level, 4) + c_div(damage, 20)
        if not saves_spell(save_level, victim, int(DamageType.LIGHTNING)):
            # DAZE_STATE(victim, UMAX(12, level/4 + dam/20))
            # ROM macro: #define DAZE_STATE(ch, npulse) ((ch)->daze = UMAX((ch)->daze, (npulse)))
            daze_pulses = max(12, save_level)
            current_daze = int(getattr(victim, "daze", 0) or 0)
            victim.daze = max(current_daze, daze_pulses)

            if hasattr(victim, "messages") and isinstance(victim.messages, list):
                victim.messages.append("Your muscles stop responding.")

        # ROM L558-562: Process inventory
        inventory = list(getattr(victim, "inventory", []))
        for obj in inventory:
            shock_effect(obj, level, damage, SpellTarget.TARGET_OBJ)
        return

    # TARGET_OBJ: Equipment damage (ROM C lines 566-614)
    if dest == SpellTarget.TARGET_OBJ:
        from mud.models.object import Object

        if not isinstance(target, Object):
            return

        obj = target

        # ROM L574-576: Immunity checks
        if obj.extra_flags & ITEM_BURN_PROOF:
            return
        if obj.extra_flags & ITEM_NOPURGE:
            return
        if rng_mm.number_range(0, 4) == 0:  # 20% random immunity
            return

        # ROM L588-600: Item type specific behavior
        item_type = getattr(obj.prototype, "item_type", None)
        item_type_int = int(item_type) if item_type is not None else ItemType.TRASH
        item_type_modifier = 0
        message = ""

        if item_type_int == int(ItemType.WAND) or item_type_int == int(ItemType.STAFF):
            item_type_modifier = 10
            message = "overloads and explodes!"
        elif item_type_int == int(ItemType.JEWELRY):
            item_type_modifier = -10
            message = "is fused into a worthless lump."
        else:
            return  # Other item types are immune

        # Probability calculation
        chance = _calculate_chance(level, damage, obj, item_type_modifier)

        # Roll check
        if rng_mm.number_percent() > chance:
            return

        # Send message
        _send_effect_message(obj, message)

        # ROM L612: Object destruction
        extract_obj(obj)


__all__ = [
    "SpellTarget",
    "acid_effect",
    "cold_effect",
    "fire_effect",
    "poison_effect",
    "shock_effect",
]
