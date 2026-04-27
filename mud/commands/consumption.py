"""
Consumption commands for eat and drink.

ROM References: src/act_obj.c lines 300-600
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.constants import AffectFlag, ItemType, Position
from mud.net.protocol import broadcast_room
from mud.utils.act import act_format
from mud.utils.rng_mm import number_fuzzy

if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.object import Object


def do_eat(ch: Character, args: str) -> str:
    """
    Consume food to restore hunger.

    ROM Reference: src/act_obj.c lines 1284-1365 (do_eat)

    condition list indices (ROM merc.h):
        COND_DRUNK = 0, COND_FULL = 1, COND_THIRST = 2, COND_HUNGER = 3
    """
    # ROM constants for condition list indices
    _COND_FULL = 1
    _COND_HUNGER = 3

    args = args.strip()

    if not args:
        return "Eat what?"

    # Find object in inventory
    obj = _find_obj_inventory(ch, args)
    if not obj:
        return "You do not have that item."

    # Normalize item_type to int for comparison (obj.item_type may be int or enum)
    item_type_raw = getattr(obj, "item_type", int(ItemType.TRASH))
    item_type_int = int(item_type_raw) if item_type_raw is not None else int(ItemType.TRASH)

    # EAT-002: IS_IMMORTAL bypass — type-check and fullness-check skipped for immortals
    # ROM src/act_obj.c:1302-1315
    if not ch.is_immortal():
        # EAT-001/EAT-002: accept FOOD or PILL; reject everything else
        # ROM src/act_obj.c:1304
        if item_type_int != int(ItemType.FOOD) and item_type_int != int(ItemType.PILL):
            return "That's not edible."

        # EAT-003: fullness pre-check for mortal PCs (list-based condition)
        # ROM src/act_obj.c:1310-1314  COND_FULL index = 1
        if not getattr(ch, "is_npc", True):
            condition = getattr(ch, "condition", None)
            if isinstance(condition, list) and len(condition) > _COND_FULL:
                if condition[_COND_FULL] > 40:
                    return "You are too full to eat more."

    # EAT-004: TO_ROOM broadcast fires before TO_CHAR
    # ROM src/act_obj.c:1317
    room = getattr(ch, "room", None) or getattr(ch, "location", None)
    if room is not None:
        room_message = act_format("$n eats $p.", recipient=None, actor=ch, arg1=obj)
        broadcast_room(room, room_message, exclude=ch)

    obj_name = getattr(obj, "short_descr", "something")
    messages = [f"You eat {obj_name}."]

    # EAT-001: PILL path — cast spells then extract (no hunger/poison logic)
    # ROM src/act_obj.c:1356-1360
    if item_type_int == int(ItemType.PILL):
        from mud.commands.obj_manipulation import _obj_cast_spell

        obj_value = getattr(obj, "value", [0, 0, 0, 0, 0])
        spell_level = obj_value[0] if len(obj_value) > 0 else 1
        for i in range(1, 4):
            if len(obj_value) > i and obj_value[i]:
                _obj_cast_spell(obj_value[i], spell_level, ch, ch, None)
        _destroy_object(ch, obj)
        return "\n".join(messages)

    # FOOD path (and immortal eating non-food falls through to extract below)
    if item_type_int == int(ItemType.FOOD):
        # Restore full/hunger conditions for non-NPC PCs
        # ROM src/act_obj.c:1324-1334  (gain_condition uses list indices)
        if not getattr(ch, "is_npc", True):
            condition = getattr(ch, "condition", None)
            if isinstance(condition, list) and len(condition) > _COND_HUNGER:
                food_value = getattr(obj, "value", [0, 0, 0, 0, 0])
                old_hunger = condition[_COND_HUNGER]
                if isinstance(food_value, list):
                    # value[0] = full gain, value[1] = hunger gain (ROM gain_condition calls)
                    if len(food_value) > 0 and food_value[0]:
                        condition[_COND_FULL] = min(48, condition[_COND_FULL] + food_value[0])
                    if len(food_value) > 1 and food_value[1]:
                        condition[_COND_HUNGER] = min(48, condition[_COND_HUNGER] + food_value[1])
                new_hunger = condition[_COND_HUNGER]
                if old_hunger == 0 and new_hunger > 0:
                    messages.append("You are no longer hungry.")
                elif condition[_COND_FULL] > 40:
                    messages.append("You are full.")

        # EAT-005: poison affect with ROM-correct fields
        # ROM src/act_obj.c:1337-1353
        obj_value = getattr(obj, "value", [0, 0, 0, 0, 0])
        if isinstance(obj_value, list) and len(obj_value) > 3 and obj_value[3] != 0:
            # Poison TO_ROOM: "$n chokes and gags." (ROM src/act_obj.c:1342)
            if room is not None:
                choke_msg = act_format("$n chokes and gags.", recipient=None, actor=ch, arg1=None)
                broadcast_room(room, choke_msg, exclude=ch)
            messages.append("You choke and gag.")

            # EAT-005: apply poison flag; store ROM-correct affect metadata on ch.affects
            # ROM af: level=number_fuzzy(value[0]), duration=2*value[0], location=APPLY_NONE=0, modifier=0
            if hasattr(ch, "add_affect"):
                level_val = obj_value[0] if obj_value[0] else 1
                # add_affect(AffectFlag) sets ch.affected_by |= flag
                ch.add_affect(AffectFlag.POISON)
                # Store full ROM affect metadata for game_loop poison tick
                affects_list = getattr(ch, "affects", None)
                if affects_list is None:
                    affects_list = []
                    ch.affects = affects_list
                affects_list.append(
                    {
                        "where": "affects",
                        "type": "poison",
                        "level": number_fuzzy(level_val),
                        "duration": 2 * level_val,
                        "location": 0,   # APPLY_NONE
                        "modifier": 0,
                        "bitvector": int(AffectFlag.POISON),
                    }
                )

    # Destroy the object (food, pill already returned, or immortal-non-food)
    # ROM src/act_obj.c:1363
    _destroy_object(ch, obj)

    return "\n".join(messages)


def do_drink(ch: Character, args: str) -> str:
    """
    Drink from a container or fountain.

    ROM Reference: src/act_obj.c lines 1161-1280 (do_drink)

    DRINK-001: empty arg scans room for ITEM_FOUNTAIN before "Drink what?"
    DRINK-002: drunk pre-check (condition[DRUNK] > 10) fires after lookup
    DRINK-003: non-empty arg uses get_obj_here (inventory + room)
    DRINK-004: condition is list[int] via pcdata; use gain_condition()
    DRINK-005: liq_table affect values drive amount / gain_condition
    DRINK-006: post-condition feedback messages (drunk/full/thirst)
    DRINK-007: act() TO_ROOM and TO_CHAR broadcast messages
    DRINK-008: poison affect with ROM-correct fields (duration=3*amount)
    DRINK-009: immortal bypasses "too full" check
    """
    from mud.characters.conditions import gain_condition
    from mud.models.constants import Condition, LIQUID_TABLE
    from mud.world.obj_find import get_obj_here

    args = args.strip()

    room = getattr(ch, "room", None)

    # DRINK-001: empty arg — scan room for first FOUNTAIN; else "Drink what?"
    # ROM src/act_obj.c:1170-1182
    if not args:
        obj = None
        for candidate in getattr(room, "contents", []):
            ctype = int(getattr(candidate, "item_type", 0))
            if ctype == int(ItemType.FOUNTAIN):
                obj = candidate
                break
        if obj is None:
            return "Drink what?"
    else:
        # DRINK-003: use get_obj_here (room first, then inventory, then equipment)
        # ROM src/act_obj.c:1186-1190
        obj = get_obj_here(ch, args)
        if obj is None:
            return "You can't find it."

    # DRINK-002: drunk pre-check — must be before type-switch
    # ROM src/act_obj.c:1193-1197
    is_npc = getattr(ch, "is_npc", True)
    if not is_npc:
        pcdata = getattr(ch, "pcdata", None)
        cond = getattr(pcdata, "condition", None) if pcdata else None
        if isinstance(cond, list) and len(cond) > int(Condition.DRUNK):
            if cond[int(Condition.DRUNK)] > 10:
                return "You fail to reach your mouth.  *Hic*"

    # Dispatch by item_type
    # ROM src/act_obj.c:1199-1230
    item_type_int = int(getattr(obj, "item_type", 0))
    value = getattr(obj, "value", [0, 0, 0, 0, 0])
    if not isinstance(value, list):
        value = [0, 0, 0, 0, 0]

    if item_type_int == int(ItemType.FOUNTAIN):
        # ROM: amount = liq_affect[4] * 3; no value decrement
        liquid_idx = value[2] if len(value) > 2 else 0
        if liquid_idx < 0:
            liquid_idx = 0
        liq = LIQUID_TABLE[liquid_idx] if liquid_idx < len(LIQUID_TABLE) else LIQUID_TABLE[0]
        amount = liq.ssize * 3

    elif item_type_int == int(ItemType.DRINK_CON):
        # ROM: check empty, then amount = min(ssize, value[1])
        if len(value) < 2 or value[1] <= 0:
            return "It is already empty."
        liquid_idx = value[2] if len(value) > 2 else 0
        if liquid_idx < 0:
            liquid_idx = 0
        liq = LIQUID_TABLE[liquid_idx] if liquid_idx < len(LIQUID_TABLE) else LIQUID_TABLE[0]
        amount = min(liq.ssize, value[1])

    else:
        return "You can't drink from that."

    # DRINK-009: immortal bypasses fullness check
    # ROM src/act_obj.c:1231-1236
    if not is_npc:
        pcdata = getattr(ch, "pcdata", None)
        cond = getattr(pcdata, "condition", None) if pcdata else None
        if not ch.is_immortal() and isinstance(cond, list) and len(cond) > int(Condition.FULL):
            if cond[int(Condition.FULL)] > 45:
                return "You're too full to drink more."

    # DRINK-007: TO_ROOM and TO_CHAR act() messages
    # ROM src/act_obj.c:1238-1241
    obj_short = getattr(obj, "short_descr", "something")
    if room is not None:
        room_msg = act_format(
            "$n drinks $T from $p.",
            recipient=None,
            actor=ch,
            arg1=obj,
            arg2=liq.name,
        )
        broadcast_room(room, room_msg, exclude=ch)

    messages = [f"You drink {liq.name} from {obj_short}."]

    # DRINK-005: gain_condition using liq_table affect values
    # ROM src/act_obj.c:1243-1250
    gain_condition(ch, Condition.DRUNK,  amount * liq.proof  // 36)
    gain_condition(ch, Condition.FULL,   amount * liq.full   // 4)
    gain_condition(ch, Condition.THIRST, amount * liq.thirst // 10)
    gain_condition(ch, Condition.HUNGER, amount * liq.food   // 2)

    # DRINK-006: post-condition feedback messages
    # ROM src/act_obj.c:1252-1257
    if not is_npc:
        pcdata = getattr(ch, "pcdata", None)
        cond = getattr(pcdata, "condition", None) if pcdata else None
        if isinstance(cond, list):
            if len(cond) > int(Condition.DRUNK) and cond[int(Condition.DRUNK)] > 10:
                messages.append("You feel drunk.")
            if len(cond) > int(Condition.FULL) and cond[int(Condition.FULL)] > 40:
                messages.append("You are full.")
            if len(cond) > int(Condition.THIRST) and cond[int(Condition.THIRST)] > 40:
                messages.append("Your thirst is quenched.")

    # DRINK-008: poison affect with ROM-correct fields
    # ROM src/act_obj.c:1259-1274
    if len(value) > 3 and value[3] != 0:
        if room is not None:
            choke_msg = act_format("$n chokes and gags.", recipient=None, actor=ch, arg1=None)
            broadcast_room(room, choke_msg, exclude=ch)
        messages.append("You choke and gag.")

        if hasattr(ch, "add_affect"):
            ch.add_affect(AffectFlag.POISON)
            affects_list = getattr(ch, "affects", None)
            if affects_list is None:
                affects_list = []
                ch.affects = affects_list
            affects_list.append(
                {
                    "where": "affects",
                    "type": "poison",
                    "level": number_fuzzy(amount),
                    "duration": 3 * amount,
                    "location": 0,    # APPLY_NONE
                    "modifier": 0,
                    "bitvector": int(AffectFlag.POISON),
                }
            )

    # DRINK-005: decrement container only (not fountain); only if value[0] > 0
    # ROM src/act_obj.c:1276-1277
    if item_type_int == int(ItemType.DRINK_CON) and len(value) > 0 and value[0] > 0:
        value[1] -= amount

    return "\n".join(messages)


def _find_obj_inventory(ch: Character, name: str) -> Object | None:
    """Find an object in character's inventory by name.

    ROM Reference: src/handler.c get_obj_carry — searches `ch->carrying`.
    QuickMUD stores the carrying list on `Character.inventory` (see
    `mud/models/character.py:396`). Previous code read `ch.carrying` which
    does not exist, so every `do_eat`/`do_drink` lookup failed.
    """
    inventory = getattr(ch, "inventory", None)
    if inventory is None:
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
    """Remove an object from character's inventory and destroy it.

    NOTE: ROM uses `extract_obj` which also unlinks from object_registry.
    See ACT_OBJ_C_CONSUMABLES_AUDIT.md for the gap.
    """
    inventory = getattr(ch, "inventory", None)
    if inventory is None:
        inventory = getattr(ch, "carrying", [])
    if obj in inventory:
        inventory.remove(obj)

    # Update carry weight and count
    if hasattr(ch, "carry_weight"):
        obj_weight = getattr(obj, "weight", 0)
        ch.carry_weight = max(0, ch.carry_weight - obj_weight)

    if hasattr(ch, "carry_number"):
        ch.carry_number = max(0, ch.carry_number - 1)
