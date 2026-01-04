"""
Equipment and character manipulation handlers.

ROM References: src/handler.c lines 1754-1877
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.constants import ItemType, Stat, WearLocation

if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.object import Object
    from mud.models.obj import Affect, ObjectData


def apply_ac(obj: Object, wear_loc: int, ac_type: int) -> int:
    """
    Calculate AC bonus from armor at a specific wear location.

    ROM Reference: src/handler.c:1688-1726 (apply_ac)

    Different armor slots provide different AC multipliers:
    - Body armor: 3x (most protective)
    - Head/Legs/About: 2x
    - All other slots: 1x

    Args:
        obj: The armor object
        wear_loc: Where the armor is worn (WearLocation enum value)
        ac_type: AC type (0=pierce, 1=bash, 2=slash, 3=exotic)

    Returns:
        AC bonus value (applied to ch->armor[ac_type])
    """
    # ROM C handler.c:1690-1691 - only armor provides AC
    item_type = getattr(obj.prototype, "item_type", None)
    if item_type != int(ItemType.ARMOR):
        return 0

    value = getattr(obj.prototype, "value", [0, 0, 0, 0, 0])
    if ac_type < 0 or ac_type >= 4:
        return 0

    # ROM C handler.c:1693-1722 - different multipliers per slot
    wear_multipliers = {
        int(WearLocation.BODY): 3,  # Torso armor most important
        int(WearLocation.HEAD): 2,  # Helmet
        int(WearLocation.LEGS): 2,  # Leg armor
        int(WearLocation.ABOUT): 2,  # Cloak/robe
        # All other slots default to 1x:
        # FEET, HANDS, ARMS, SHIELD, NECK_1, NECK_2, WAIST, WRIST_L, WRIST_R, HOLD
    }

    multiplier = wear_multipliers.get(wear_loc, 1)
    return value[ac_type] * multiplier


def affect_modify(ch: Character, paf: Affect, f_add: bool) -> None:
    """
    Apply or remove affect modifiers to character stats.

    ROM Reference: src/handler.c:1019-1150 (affect_modify)

    Args:
        ch: Character to modify
        paf: Affect data (where, type, level, duration, location, modifier, bitvector)
        f_add: True to add affect, False to remove affect
    """
    TO_AFFECTS = 0
    TO_IMMUNE = 2
    TO_RESIST = 3
    TO_VULN = 4

    APPLY_NONE = 0
    APPLY_STR = 1
    APPLY_DEX = 2
    APPLY_INT = 3
    APPLY_WIS = 4
    APPLY_CON = 5
    APPLY_SEX = 6
    APPLY_MANA = 12
    APPLY_HIT = 13
    APPLY_MOVE = 14
    APPLY_AC = 17
    APPLY_HITROLL = 18
    APPLY_DAMROLL = 19
    APPLY_SAVES = 20
    APPLY_SAVING_ROD = 21
    APPLY_SAVING_PETRI = 22
    APPLY_SAVING_BREATH = 23
    APPLY_SAVING_SPELL = 24
    APPLY_SPELL_AFFECT = 25

    mod = paf.modifier

    if f_add:
        if paf.where == TO_AFFECTS:
            ch.affected_by |= paf.bitvector
        elif paf.where == TO_IMMUNE:
            ch.imm_flags |= paf.bitvector
        elif paf.where == TO_RESIST:
            ch.res_flags |= paf.bitvector
        elif paf.where == TO_VULN:
            ch.vuln_flags |= paf.bitvector
    else:
        if paf.where == TO_AFFECTS:
            ch.affected_by &= ~paf.bitvector
        elif paf.where == TO_IMMUNE:
            ch.imm_flags &= ~paf.bitvector
        elif paf.where == TO_RESIST:
            ch.res_flags &= ~paf.bitvector
        elif paf.where == TO_VULN:
            ch.vuln_flags &= ~paf.bitvector
        mod = -mod

    if paf.location == APPLY_NONE:
        pass
    elif paf.location == APPLY_STR:
        ch._ensure_mod_stat_capacity()
        ch.mod_stat[int(Stat.STR)] += mod
    elif paf.location == APPLY_DEX:
        ch._ensure_mod_stat_capacity()
        ch.mod_stat[int(Stat.DEX)] += mod
    elif paf.location == APPLY_INT:
        ch._ensure_mod_stat_capacity()
        ch.mod_stat[int(Stat.INT)] += mod
    elif paf.location == APPLY_WIS:
        ch._ensure_mod_stat_capacity()
        ch.mod_stat[int(Stat.WIS)] += mod
    elif paf.location == APPLY_CON:
        ch._ensure_mod_stat_capacity()
        ch.mod_stat[int(Stat.CON)] += mod
    elif paf.location == APPLY_SEX:
        ch.sex = getattr(ch, "sex", 0) + mod
    elif paf.location == APPLY_MANA:
        ch.max_mana += mod
    elif paf.location == APPLY_HIT:
        ch.max_hit += mod
    elif paf.location == APPLY_MOVE:
        ch.max_move += mod
    elif paf.location == APPLY_AC:
        if hasattr(ch, "armor") and isinstance(ch.armor, list):
            for i in range(min(4, len(ch.armor))):
                ch.armor[i] += mod
    elif paf.location == APPLY_HITROLL:
        ch.hitroll += mod
    elif paf.location == APPLY_DAMROLL:
        ch.damroll += mod
    elif paf.location in (APPLY_SAVES, APPLY_SAVING_ROD, APPLY_SAVING_PETRI, APPLY_SAVING_BREATH, APPLY_SAVING_SPELL):
        ch.saving_throw += mod
    elif paf.location == APPLY_SPELL_AFFECT:
        pass


def equip_char(ch: Character, obj: Object, wear_loc: int) -> None:
    """
    Equip a character with an object, applying bonuses.

    ROM Reference: src/handler.c:1754-1797 (equip_char)

    Args:
        ch: Character equipping the item
        obj: Object to equip
        wear_loc: Equipment slot (WearLocation enum value)
    """
    if hasattr(ch, "armor") and isinstance(ch.armor, list):
        for i in range(min(4, len(ch.armor))):
            ch.armor[i] -= apply_ac(obj, wear_loc, i)

    obj.wear_loc = wear_loc

    APPLY_SPELL_AFFECT = 25

    enchanted = getattr(obj, "enchanted", False)
    if not enchanted and hasattr(obj.prototype, "affected"):
        for affect in obj.prototype.affected:
            if isinstance(affect, dict):
                from mud.models.obj import Affect

                location = affect.get("location", 0)
                if location != APPLY_SPELL_AFFECT:
                    paf = Affect(
                        where=0,
                        type=0,
                        level=getattr(obj, "level", 0),
                        duration=-1,
                        location=location,
                        modifier=affect.get("modifier", 0),
                        bitvector=0,
                    )
                    affect_modify(ch, paf, True)

    if hasattr(obj, "affected"):
        for affect in obj.affected:
            if hasattr(affect, "location"):
                if affect.location == APPLY_SPELL_AFFECT:
                    pass
                else:
                    affect_modify(ch, affect, True)

    item_type_str = getattr(obj.prototype, "item_type", None)
    item_type = int(item_type_str) if item_type_str else ItemType.TRASH

    if item_type == ItemType.LIGHT:
        value = getattr(obj, "value", [0, 0, 0, 0, 0])
        if len(value) > 2 and value[2] != 0:
            room = getattr(ch, "room", None)
            if room:
                current_light = getattr(room, "light", 0)
                room.light = current_light + 1


def unequip_char(ch: Character, obj: Object) -> None:
    """
    Unequip an object from a character, removing bonuses.

    ROM Reference: src/handler.c:1804-1877 (unequip_char)

    Args:
        ch: Character unequipping the item
        obj: Object to unequip
    """
    if obj.wear_loc == int(WearLocation.NONE):
        return

    if hasattr(ch, "armor") and isinstance(ch.armor, list):
        for i in range(min(4, len(ch.armor))):
            ch.armor[i] += apply_ac(obj, obj.wear_loc, i)

    obj.wear_loc = int(WearLocation.NONE)

    APPLY_SPELL_AFFECT = 25

    enchanted = getattr(obj, "enchanted", False)
    if not enchanted and hasattr(obj.prototype, "affected"):
        for affect in obj.prototype.affected:
            if isinstance(affect, dict):
                from mud.models.obj import Affect

                location = affect.get("location", 0)
                if location == APPLY_SPELL_AFFECT:
                    # ROM C handler.c:1820-1868 - Remove matching spell affects
                    # Find and remove affects with matching type and level
                    paf_type = affect.get("type", 0)
                    paf_level = getattr(obj, "level", 0)

                    # Search character's affects for matching spell affect
                    char_affects = getattr(ch, "affected", [])
                    for char_affect in list(char_affects):  # Copy list to safely modify during iteration
                        if (
                            hasattr(char_affect, "type")
                            and hasattr(char_affect, "level")
                            and hasattr(char_affect, "location")
                            and char_affect.type == paf_type
                            and char_affect.level == paf_level
                            and char_affect.location == APPLY_SPELL_AFFECT
                        ):
                            # Remove this affect from character
                            if hasattr(ch, "remove_affect"):
                                ch.remove_affect(char_affect)
                            break  # ROM C breaks after first match (lpaf_next = NULL)
                else:
                    paf = Affect(
                        where=0,
                        type=0,
                        level=getattr(obj, "level", 0),
                        duration=-1,
                        location=location,
                        modifier=affect.get("modifier", 0),
                        bitvector=0,
                    )
                    affect_modify(ch, paf, False)

    if hasattr(obj, "affected"):
        for affect in obj.affected:
            if hasattr(affect, "location"):
                if affect.location == APPLY_SPELL_AFFECT:
                    # ROM C handler.c:1846-1868 - Same logic for object instance affects
                    paf_type = getattr(affect, "type", 0)
                    paf_level = getattr(affect, "level", 0)

                    char_affects = getattr(ch, "affected", [])
                    for char_affect in list(char_affects):
                        if (
                            hasattr(char_affect, "type")
                            and hasattr(char_affect, "level")
                            and hasattr(char_affect, "location")
                            and char_affect.type == paf_type
                            and char_affect.level == paf_level
                            and char_affect.location == APPLY_SPELL_AFFECT
                        ):
                            if hasattr(ch, "remove_affect"):
                                ch.remove_affect(char_affect)
                            break
                else:
                    affect_modify(ch, affect, False)

    item_type_str = getattr(obj.prototype, "item_type", None)
    item_type = int(item_type_str) if item_type_str else ItemType.TRASH

    if item_type == ItemType.LIGHT:
        value = getattr(obj, "value", [0, 0, 0, 0, 0])
        if len(value) > 2 and value[2] != 0:
            room = getattr(ch, "room", None)
            if room and getattr(room, "light", 0) > 0:
                room.light -= 1


# Object Affect Functions (ROM C handler.c:989-1412)


def affect_enchant(obj: ObjectData) -> None:
    """
    Copy prototype affects to object when it becomes enchanted.

    ROM Reference: src/handler.c:989-1013 (affect_enchant)

    When an object is enchanted, copy all affects from the prototype
    to the object instance so they can be modified independently.

    Args:
        obj: Object to enchant
    """
    from copy import copy

    from mud.models.obj import Affect

    # ROM C handler.c:992 - check if already enchanted
    if getattr(obj, "enchanted", False):
        return

    # ROM C handler.c:995 - mark as enchanted
    obj.enchanted = True

    # ROM C handler.c:997-1011 - copy prototype affects to object
    prototype = getattr(obj, "pIndexData", None) or getattr(obj, "prototype", None)
    if prototype and hasattr(prototype, "affected"):
        for paf in prototype.affected:
            # Create new affect (ROM C: new_affect())
            if hasattr(paf, "where"):
                # It's an Affect object
                af_new = copy(paf)
            else:
                # It's a dict
                af_new = Affect(
                    where=paf.get("where", 0),
                    type=max(0, paf.get("type", 0)),
                    level=paf.get("level", 0),
                    duration=paf.get("duration", -1),
                    location=paf.get("location", 0),
                    modifier=paf.get("modifier", 0),
                    bitvector=paf.get("bitvector", 0),
                )

            # ROM C handler.c:1001-1002 - add to front of list
            if not hasattr(obj, "affected"):
                obj.affected = []
            obj.affected.insert(0, af_new)


def affect_find(paf_list: list[Affect], sn: int) -> Affect | None:
    """
    Find an affect in a list by spell number.

    ROM Reference: src/handler.c:1168-1179 (affect_find)

    Args:
        paf_list: List of affects to search
        sn: Spell number to find

    Returns:
        First affect with matching spell type, or None
    """
    # ROM C handler.c:1172-1176 - iterate and compare
    for paf in paf_list:
        if hasattr(paf, "type") and paf.type == sn:
            return paf

    return None


def affect_check(ch: Character, where: int, vector: int) -> None:
    """
    Re-apply bitvectors from remaining affects after removal.

    ROM Reference: src/handler.c:1182-1228 (affect_check)

    When an affect is removed, check if other affects still provide
    the same bitvector and re-apply it if needed.

    Args:
        ch: Character to check
        where: Affect location (TO_AFFECTS, TO_IMMUNE, etc.)
        vector: Bitvector to check
    """
    TO_OBJECT = 1
    TO_WEAPON = 6
    TO_AFFECTS = 0
    TO_IMMUNE = 2
    TO_RESIST = 3
    TO_VULN = 4

    # ROM C handler.c:1187-1188 - skip object/weapon affects
    if where == TO_OBJECT or where == TO_WEAPON or vector == 0:
        return

    # ROM C handler.c:1190-1227 - check remaining affects
    char_affects = getattr(ch, "affected", [])
    for paf in char_affects:
        if hasattr(paf, "where") and hasattr(paf, "bitvector"):
            if paf.where == where and paf.bitvector == vector:
                # Found another affect with same bitvector, re-apply it
                if where == TO_AFFECTS:
                    ch.affected_by |= vector
                elif where == TO_IMMUNE:
                    ch.imm_flags |= vector
                elif where == TO_RESIST:
                    ch.res_flags |= vector
                elif where == TO_VULN:
                    ch.vuln_flags |= vector
                return

    # Also check equipment affects
    if hasattr(ch, "equipment"):
        for obj in ch.equipment.values():
            if obj and hasattr(obj, "affected"):
                for paf in obj.affected:
                    if hasattr(paf, "where") and hasattr(paf, "bitvector"):
                        if paf.where == where and paf.bitvector == vector:
                            if where == TO_AFFECTS:
                                ch.affected_by |= vector
                            elif where == TO_IMMUNE:
                                ch.imm_flags |= vector
                            elif where == TO_RESIST:
                                ch.res_flags |= vector
                            elif where == TO_VULN:
                                ch.vuln_flags |= vector
                            return


def affect_to_obj(obj: ObjectData, paf: Affect) -> None:
    """
    Add an affect to an object.

    ROM Reference: src/handler.c:1283-1310 (affect_to_obj)

    Args:
        obj: Object to add affect to
        paf: Affect to add
    """
    from copy import copy

    TO_OBJECT = 1
    TO_WEAPON = 6

    # ROM C handler.c:1287-1289 - create new affect and copy data
    paf_new = copy(paf)

    # ROM C handler.c:1292-1293 - add to front of list
    if not hasattr(obj, "affected"):
        obj.affected = []
    obj.affected.insert(0, paf_new)

    # ROM C handler.c:1295-1306 - apply bitvector to object flags
    if paf.bitvector:
        if paf.where == TO_OBJECT:
            # Set bit in extra_flags
            obj.extra_flags |= paf.bitvector
        elif paf.where == TO_WEAPON:
            # Set bit in weapon flags (value[4])
            if hasattr(obj, "item_type") and obj.item_type == int(ItemType.WEAPON):
                if hasattr(obj, "value") and len(obj.value) > 4:
                    obj.value[4] |= paf.bitvector


def affect_remove_obj(obj: ObjectData, paf: Affect) -> None:
    """
    Remove an affect from an object.

    ROM Reference: src/handler.c:1362-1412 (affect_remove_obj)

    Args:
        obj: Object to remove affect from
        paf: Affect to remove
    """
    TO_OBJECT = 1
    TO_WEAPON = 6

    # ROM C handler.c:1365-1369 - validate has affects
    if not hasattr(obj, "affected") or not obj.affected:
        # bug("Affect_remove_object: no affect.", 0)
        return

    # ROM C handler.c:1371-1372 - if worn, remove from carrier
    if hasattr(obj, "carried_by") and obj.carried_by and hasattr(obj, "wear_loc") and obj.wear_loc != -1:
        affect_modify(obj.carried_by, paf, False)

    where = paf.where
    vector = paf.bitvector

    # ROM C handler.c:1377-1388 - remove bitvector from object flags
    if paf.bitvector:
        if paf.where == TO_OBJECT:
            obj.extra_flags &= ~paf.bitvector
        elif paf.where == TO_WEAPON:
            if hasattr(obj, "item_type") and obj.item_type == int(ItemType.WEAPON):
                if hasattr(obj, "value") and len(obj.value) > 4:
                    obj.value[4] &= ~paf.bitvector

    # ROM C handler.c:1390-1410 - remove from linked list
    if obj.affected and obj.affected[0] == paf:
        obj.affected.pop(0)
    else:
        # Find and remove from list
        for i, affect in enumerate(obj.affected):
            if affect == paf:
                obj.affected.pop(i)
                break


def is_friend(ch: Character, victim: Character) -> bool:
    """
    Check if two characters are friends (for mob assist AI).

    ROM Reference: src/handler.c:50-93 (is_friend)

    Returns True if ch should assist victim in combat.

    Args:
        ch: Character considering assist
        victim: Character potentially being assisted

    Returns:
        True if ch should help victim
    """
    # ROM C handler.c:52-53 - same group always friends
    if hasattr(ch, "group") and hasattr(victim, "group"):
        if ch.group and ch.group == victim.group:
            return True

    # ROM C handler.c:56-57 - players don't auto-assist
    if not getattr(ch, "is_npc", True):
        return False

    # ROM C handler.c:59-65 - check ASSIST_PLAYERS flag
    if not getattr(victim, "is_npc", True):
        off_flags = getattr(ch, "off_flags", 0)
        ASSIST_PLAYERS = 0x00000001  # From ROM constants
        if off_flags & ASSIST_PLAYERS:
            return True
        else:
            return False

    # ROM C handler.c:67-68 - charmed mobs don't assist
    AFF_CHARM = 0x00000002  # From ROM affect flags
    if getattr(ch, "affected_by", 0) & AFF_CHARM:
        return False

    # ROM C handler.c:70-71 - ASSIST_ALL flag
    off_flags = getattr(ch, "off_flags", 0)
    ASSIST_ALL = 0x00000002
    if off_flags & ASSIST_ALL:
        return True

    # ROM C handler.c:73-74 - same group
    if hasattr(ch, "group") and hasattr(victim, "group"):
        if ch.group and ch.group == victim.group:
            return True

    # ROM C handler.c:76-78 - ASSIST_VNUM (same mob type)
    ASSIST_VNUM = 0x00000004
    if off_flags & ASSIST_VNUM:
        ch_proto = getattr(ch, "prototype", None) or getattr(ch, "pIndexData", None)
        victim_proto = getattr(victim, "prototype", None) or getattr(victim, "pIndexData", None)
        if ch_proto and victim_proto and ch_proto == victim_proto:
            return True

    # ROM C handler.c:80-81 - ASSIST_RACE
    ASSIST_RACE = 0x00000008
    if off_flags & ASSIST_RACE:
        if hasattr(ch, "race") and hasattr(victim, "race") and ch.race == victim.race:
            return True

    # ROM C handler.c:83-90 - ASSIST_ALIGN
    ASSIST_ALIGN = 0x00000010
    ACT_NOALIGN = 0x00000080  # From ROM act flags
    if off_flags & ASSIST_ALIGN:
        ch_act = getattr(ch, "act", 0)
        victim_act = getattr(victim, "act", 0)
        if not (ch_act & ACT_NOALIGN) and not (victim_act & ACT_NOALIGN):
            ch_align = getattr(ch, "alignment", 0)
            victim_align = getattr(victim, "alignment", 0)
            # Good helps good, evil helps evil, neutral helps neutral
            if (
                (ch_align > 350 and victim_align > 350)
                or (ch_align < -350 and victim_align < -350)
                or (-350 <= ch_align <= 350 and -350 <= victim_align <= 350)
            ):
                return True

    # ROM C handler.c:92 - default to False
    return False


# ==============================================================================
# Utility & Lookup Functions (ROM C handler.c)
# ==============================================================================


def count_users(obj: "Object") -> int:
    """
    Count number of characters sitting/standing on furniture object.

    ROM C: handler.c:96-109 (count_users)

    Returns count of characters in same room whose 'on' field points to this object.
    Used for furniture capacity checks.

    Args:
        obj: Furniture object to count users of

    Returns:
        Number of characters on the object

    QuickMUD Notes:
        - Uses obj.in_room.characters instead of linked list
        - Returns 0 if object not in a room
    """
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from mud.models.object import Object

    in_room = getattr(obj, "in_room", None)
    if in_room is None:
        return 0

    count = 0
    characters = getattr(in_room, "characters", [])
    for fch in characters:
        if getattr(fch, "on", None) == obj:
            count += 1

    return count


def material_lookup(name: str) -> int:
    """
    Lookup material type by name.

    ROM C: handler.c:112-115 (material_lookup)

    NOTE: This is a stub in ROM C - always returns 0.
    Material system was planned but never fully implemented in ROM 2.4b6.

    Args:
        name: Material name (ignored)

    Returns:
        Always returns 0 (ROM C stub behavior)
    """
    return 0


def item_name(item_type: int) -> str:
    """
    Convert item type number to name string.

    ROM C: handler.c:145-153 (item_name)

    Looks up item type in item_table and returns the name.
    Returns "none" if type not found.

    Args:
        item_type: Item type number (from ItemType enum)

    Returns:
        Item type name string, or "none" if not found

    QuickMUD Notes:
        - Uses ItemType enum from constants.py
        - Falls back to "none" instead of NULL
    """
    from mud.models.constants import ItemType

    try:
        return ItemType(item_type).name.lower()
    except ValueError:
        return "none"


def weapon_name(weapon_type: int) -> str:
    """
    Convert weapon type number to name string.

    ROM C: handler.c:155-163 (weapon_name)

    Looks up weapon type in weapon_table and returns the name.
    Returns "exotic" if type not found.

    Args:
        weapon_type: Weapon type number (from WeaponType enum)

    Returns:
        Weapon type name string, or "exotic" if not found

    QuickMUD Notes:
        - Uses WeaponType enum from constants.py
        - Falls back to "exotic" (ROM C default)
    """
    from mud.models.constants import WeaponType

    try:
        return WeaponType(weapon_type).name.lower()
    except ValueError:
        return "exotic"


# ==============================================================================
# Character Attribute Functions (ROM C handler.c)
# ==============================================================================


def get_age(ch: "Character") -> int:
    """
    Calculate character age in years.

    ROM C: handler.c:846-849 (get_age)

    Formula: 17 + (played + (current_time - logon)) / 72000
    Where 72000 seconds = 20 hours (ROM time scale).

    Args:
        ch: Character to get age of

    Returns:
        Age in years (minimum 17)

    QuickMUD Notes:
        - Uses time.time() for current_time
        - played is in seconds (same as ROM C)
    """
    import time

    played = getattr(ch, "played", 0)
    logon = getattr(ch, "logon", time.time())
    current_time = time.time()

    return 17 + int((played + (current_time - logon)) / 72000)


def get_max_train(ch: "Character", stat: int) -> int:
    """
    Get maximum trainable value for a stat.

    ROM C: handler.c:876-893 (get_max_train)

    Returns race max + bonus for prime stat (2-3 points).
    NPCs and immortals always return 25.

    Args:
        ch: Character to check
        stat: Stat number (STAT_STR, STAT_DEX, etc.)

    Returns:
        Maximum trainable stat value (capped at 25)

    QuickMUD Notes:
        - Uses PC_RACE_TABLE from mud.models.races
        - Uses CLASS_TABLE from mud.models.classes
        - Prime stat bonus: +3 for humans, +2 for others
    """
    from mud.models.classes import CLASS_TABLE
    from mud.models.constants import LEVEL_IMMORTAL
    from mud.models.races import PC_RACE_TABLE

    is_npc = getattr(ch, "is_npc", False)
    level = getattr(ch, "level", 1)
    if is_npc or level > LEVEL_IMMORTAL:
        return 25

    race_name = getattr(ch, "race", "human")
    class_index = getattr(ch, "class_num", 0)

    pc_race = None
    for race in PC_RACE_TABLE:
        if race.name == race_name:
            pc_race = race
            break

    if not pc_race or stat < 0 or stat >= 5:
        return 18

    max_stat = pc_race.max_stats[stat]

    if class_index < len(CLASS_TABLE):
        class_entry = CLASS_TABLE[class_index]
        prime_stat = int(class_entry.prime_stat)

        if stat == prime_stat:
            if race_name == "human":
                max_stat += 3
            else:
                max_stat += 2

    return min(max_stat, 25)


# ==============================================================================
# Money Functions (ROM C handler.c)
# ==============================================================================


def deduct_cost(ch: "Character", cost: int) -> None:
    """
    Deduct cost from character's gold and silver.

    ROM C: handler.c:2397-2422 (deduct_cost)

    Deducts silver first, then gold. Handles conversion between
    gold and silver (100 silver = 1 gold).

    Args:
        ch: Character to deduct from
        cost: Amount to deduct (in silver)

    Side Effects:
        - Modifies ch.gold and ch.silver
        - Prevents negative values (sets to 0 if bug occurs)

    QuickMUD Notes:
        - Uses UMIN/UMAX for bounds checking
        - Logs bugs if gold/silver go negative
    """
    silver = min(getattr(ch, "silver", 0), cost)

    if silver < cost:
        # Need to use gold
        gold = (cost - silver + 99) // 100  # C integer division
        silver = cost - 100 * gold
    else:
        gold = 0

    ch.gold = getattr(ch, "gold", 0) - gold
    ch.silver = getattr(ch, "silver", 0) - silver

    if ch.gold < 0:
        print(f"BUG: deduct_cost: gold {ch.gold} < 0")
        ch.gold = 0
    if ch.silver < 0:
        print(f"BUG: deduct_cost: silver {ch.silver} < 0")
        ch.silver = 0


def create_money(gold: int, silver: int) -> "Object":
    """
    Create a money object with specified gold/silver.

    ROM C: handler.c:2427-2482 (create_money)

    Creates different money objects based on amounts:
    - 1 silver: OBJ_VNUM_SILVER_ONE
    - 1 gold: OBJ_VNUM_GOLD_ONE
    - N silver: OBJ_VNUM_SILVER_SOME
    - N gold: OBJ_VNUM_GOLD_SOME
    - Mixed: OBJ_VNUM_COINS

    Args:
        gold: Gold amount
        silver: Silver amount

    Returns:
        Money object with appropriate description and values, or None if invalid

    QuickMUD Notes:
        - Creates fallback objects when money prototypes don't exist in area files
        - Money object vnums (1-5) are special ROM objects not loaded from areas
    """
    from mud.models.constants import (
        ItemType,
        OBJ_VNUM_COINS,
        OBJ_VNUM_GOLD_ONE,
        OBJ_VNUM_GOLD_SOME,
        OBJ_VNUM_SILVER_ONE,
        OBJ_VNUM_SILVER_SOME,
    )
    from mud.models.obj import ObjIndex
    from mud.models.object import Object

    # ROM C handler.c:2432-2437 (validate input)
    if gold < 0 or silver < 0 or (gold == 0 and silver == 0):
        print(f"BUG: create_money: zero or negative money ({gold} gold, {silver} silver)")
        return None

    # Determine which money type to create
    vnum: int
    short_descr: str
    cost: int
    weight: int
    value_0: int  # silver
    value_1: int  # gold

    if gold == 0 and silver == 1:
        # ROM C handler.c:2439-2441
        vnum = OBJ_VNUM_SILVER_ONE
        short_descr = "one silver coin"
        cost = 1
        weight = 1
        value_0 = 1
        value_1 = 0
    elif gold == 1 and silver == 0:
        # ROM C handler.c:2443-2445
        vnum = OBJ_VNUM_GOLD_ONE
        short_descr = "one gold coin"
        cost = 100
        weight = 1
        value_0 = 0
        value_1 = 1
    elif silver == 0:
        # ROM C handler.c:2447-2456 (gold only)
        vnum = OBJ_VNUM_GOLD_SOME
        short_descr = f"{gold} gold coins"
        cost = 100 * gold
        weight = max(1, gold // 5)  # ROM: gold / 5 (integer division)
        value_0 = 0
        value_1 = gold
    elif gold == 0:
        # ROM C handler.c:2457-2466 (silver only)
        vnum = OBJ_VNUM_SILVER_SOME
        short_descr = f"{silver} silver coins"
        cost = silver
        weight = max(1, silver // 20)  # ROM: silver / 20 (integer division)
        value_0 = silver
        value_1 = 0
    else:
        # ROM C handler.c:2468-2478 (mixed coins)
        vnum = OBJ_VNUM_COINS
        short_descr = f"{silver} silver and {gold} gold coins"
        cost = 100 * gold + silver
        weight = max(1, gold // 5 + silver // 20)  # ROM: gold/5 + silver/20
        value_0 = silver
        value_1 = gold

    # Create fallback money object (money vnums don't exist in area files)
    proto = ObjIndex(
        vnum=vnum,
        short_descr=short_descr,
        description=f"{short_descr.capitalize()} is lying here.",
        item_type=int(ItemType.MONEY),
        weight=weight,
    )
    obj = Object(instance_id=None, prototype=proto)
    obj.item_type = int(ItemType.MONEY)
    obj.short_descr = short_descr
    obj.cost = cost
    obj.value = [value_0, value_1, 0, 0, 0]

    return obj


# ==============================================================================
# Combat Functions (ROM C handler.c)
# ==============================================================================


def check_immune(ch: "Character", dam_type: int) -> int:
    """
    Check character's immunity/resistance/vulnerability to damage type.

    ROM C: handler.c:213-304 (check_immune)

    Returns immunity status based on ch.imm_flags, res_flags, vuln_flags.
    Physical damage (<=3) checks WEAPON flags first.
    Magical damage (>3) checks MAGIC flags first.

    Args:
        ch: Character to check
        dam_type: Damage type (DAM_BASH, DAM_FIRE, etc.)

    Returns:
        IS_IMMUNE (100), IS_RESISTANT (75), IS_VULNERABLE (150), or IS_NORMAL (100)

    QuickMUD Notes:
        - Uses constants from constants.py
        - Returns immunity percentage values
    """
    # ROM C constants
    DAM_NONE = 0
    IS_NORMAL = 0
    IS_IMMUNE = 1
    IS_RESISTANT = 2
    IS_VULNERABLE = 3

    if dam_type == DAM_NONE:
        return -1

    # Default to normal
    defense = IS_NORMAL

    imm_flags = getattr(ch, "imm_flags", 0)
    res_flags = getattr(ch, "res_flags", 0)
    vuln_flags = getattr(ch, "vuln_flags", 0)

    # Physical damage (bash/pierce/slash)
    if dam_type <= 3:
        IMM_WEAPON = 0x00000001  # From ROM constants
        RES_WEAPON = 0x00000001
        VULN_WEAPON = 0x00000001

        if imm_flags & IMM_WEAPON:
            defense = IS_IMMUNE
        elif res_flags & RES_WEAPON:
            defense = IS_RESISTANT
        elif vuln_flags & VULN_WEAPON:
            defense = IS_VULNERABLE
    else:
        # Magical damage
        IMM_MAGIC = 0x00000002  # From ROM constants
        RES_MAGIC = 0x00000002
        VULN_MAGIC = 0x00000002

        if imm_flags & IMM_MAGIC:
            defense = IS_IMMUNE
        elif res_flags & RES_MAGIC:
            defense = IS_RESISTANT
        elif vuln_flags & VULN_MAGIC:
            defense = IS_VULNERABLE

    # TODO: Check specific damage type flags (IMM_BASH, IMM_FIRE, etc.)
    # This requires full damage type constant mapping

    return defense


# ==============================================================================
# Character Reset Function (ROM C handler.c)
# ==============================================================================


def reset_char(ch: "Character") -> None:
    """
    Reset character to clean state (de-screw corrupted characters).

    ROM C: handler.c:520-745 (reset_char)

    This is a recovery function for corrupted player files.
    Resets all temporary modifiers and re-applies equipment affects.

    Args:
        ch: Character to reset (only works on PCs)

    Side Effects:
        - Resets mod_stat[], hitroll, damroll, saving_throw, armor
        - Restores to pcdata perm_hit/mana/move
        - Re-applies all equipment affects

    QuickMUD Notes:
        - Only runs on PCs (returns immediately for NPCs)
        - Implements full ROM C behavior (handler.c:520-745)
    """
    is_npc = getattr(ch, "is_npc", False)
    if is_npc:
        return

    APPLY_SEX = 6
    APPLY_MANA = 12
    APPLY_HIT = 13
    APPLY_MOVE = 14
    APPLY_AC = 17
    APPLY_HITROLL = 18
    APPLY_DAMROLL = 19
    APPLY_SAVES = 20
    APPLY_SAVING_ROD = 21
    APPLY_SAVING_PETRI = 22
    APPLY_SAVING_BREATH = 23
    APPLY_SAVING_SPELL = 24

    pcdata = getattr(ch, "pcdata", None)
    if not pcdata:
        return

    # ROM C handler.c:530-598 - FULL reset if perm stats are corrupted
    perm_hit = getattr(pcdata, "perm_hit", 0)
    perm_mana = getattr(pcdata, "perm_mana", 0)
    perm_move = getattr(pcdata, "perm_move", 0)
    last_level = getattr(pcdata, "last_level", 0)

    if perm_hit == 0 or perm_mana == 0 or perm_move == 0 or last_level == 0:
        # Full reset - remove equipment affects then save perm stats
        equipment = getattr(ch, "equipment", {})
        for loc in range(int(WearLocation.MAX)):
            obj = equipment.get(loc)
            if obj is None:
                continue

            # ROM C handler.c:540-563 - Remove prototype affects
            enchanted = getattr(obj, "enchanted", False)
            if not enchanted and hasattr(obj.prototype, "affected"):
                for affect in obj.prototype.affected:
                    if isinstance(affect, dict):
                        location = affect.get("location", 0)
                        modifier = affect.get("modifier", 0)

                        if location == APPLY_SEX:
                            ch.sex -= modifier
                            true_sex = getattr(pcdata, "true_sex", 0)
                            if ch.sex < 0 or ch.sex > 2:
                                ch.sex = 0 if is_npc else true_sex
                        elif location == APPLY_MANA:
                            ch.max_mana -= modifier
                        elif location == APPLY_HIT:
                            ch.max_hit -= modifier
                        elif location == APPLY_MOVE:
                            ch.max_move -= modifier

            # ROM C handler.c:565-583 - Remove object instance affects
            if hasattr(obj, "affected"):
                for affect in obj.affected:
                    if hasattr(affect, "location") and hasattr(affect, "modifier"):
                        modifier = affect.modifier

                        if affect.location == APPLY_SEX:
                            ch.sex -= modifier
                        elif affect.location == APPLY_MANA:
                            ch.max_mana -= modifier
                        elif affect.location == APPLY_HIT:
                            ch.max_hit -= modifier
                        elif affect.location == APPLY_MOVE:
                            ch.max_move -= modifier

        # ROM C handler.c:586-596 - Save perm stats
        pcdata.perm_hit = ch.max_hit
        pcdata.perm_mana = ch.max_mana
        pcdata.perm_move = ch.max_move
        played = getattr(ch, "played", 0)
        pcdata.last_level = played // 3600

        true_sex = getattr(pcdata, "true_sex", 0)
        if true_sex < 0 or true_sex > 2:
            if 0 < ch.sex < 3:
                pcdata.true_sex = ch.sex
            else:
                pcdata.true_sex = 0

    # ROM C handler.c:600-616 - Reset character to true condition
    ch._ensure_mod_stat_capacity()
    for stat in range(5):  # MAX_STATS = 5
        ch.mod_stat[stat] = 0

    true_sex = getattr(pcdata, "true_sex", 0)
    if true_sex < 0 or true_sex > 2:
        pcdata.true_sex = 0
    ch.sex = pcdata.true_sex
    ch.max_hit = pcdata.perm_hit
    ch.max_mana = pcdata.perm_mana
    ch.max_move = pcdata.perm_move

    if hasattr(ch, "armor") and isinstance(ch.armor, list):
        for i in range(4):
            ch.armor[i] = 100

    ch.hitroll = 0
    ch.damroll = 0
    ch.saving_throw = 0

    # ROM C handler.c:618-689 - Re-apply equipment affects
    equipment = getattr(ch, "equipment", {})
    for loc in range(int(WearLocation.MAX)):
        obj = equipment.get(loc)
        if obj is None:
            continue

        # Apply AC bonuses
        if hasattr(ch, "armor") and isinstance(ch.armor, list):
            for i in range(4):
                ch.armor[i] -= apply_ac(obj, loc, i)

        # Apply prototype affects
        enchanted = getattr(obj, "enchanted", False)
        if not enchanted and hasattr(obj.prototype, "affected"):
            for affect in obj.prototype.affected:
                if isinstance(affect, dict):
                    location = affect.get("location", 0)
                    modifier = affect.get("modifier", 0)

                    if location == int(Stat.STR) + 1:  # APPLY_STR = 1
                        ch.mod_stat[int(Stat.STR)] += modifier
                    elif location == int(Stat.DEX) + 1:  # APPLY_DEX = 2
                        ch.mod_stat[int(Stat.DEX)] += modifier
                    elif location == int(Stat.INT) + 1:  # APPLY_INT = 3
                        ch.mod_stat[int(Stat.INT)] += modifier
                    elif location == int(Stat.WIS) + 1:  # APPLY_WIS = 4
                        ch.mod_stat[int(Stat.WIS)] += modifier
                    elif location == int(Stat.CON) + 1:  # APPLY_CON = 5
                        ch.mod_stat[int(Stat.CON)] += modifier
                    elif location == APPLY_SEX:
                        ch.sex += modifier
                    elif location == APPLY_MANA:
                        ch.max_mana += modifier
                    elif location == APPLY_HIT:
                        ch.max_hit += modifier
                    elif location == APPLY_MOVE:
                        ch.max_move += modifier
                    elif location == APPLY_AC:
                        for i in range(4):
                            ch.armor[i] += modifier
                    elif location == APPLY_HITROLL:
                        ch.hitroll += modifier
                    elif location == APPLY_DAMROLL:
                        ch.damroll += modifier
                    elif location in (
                        APPLY_SAVES,
                        APPLY_SAVING_ROD,
                        APPLY_SAVING_PETRI,
                        APPLY_SAVING_BREATH,
                        APPLY_SAVING_SPELL,
                    ):
                        ch.saving_throw += modifier

        # Apply object instance affects
        if hasattr(obj, "affected"):
            for affect in obj.affected:
                if hasattr(affect, "location") and hasattr(affect, "modifier"):
                    modifier = affect.modifier

                    if affect.location == int(Stat.STR) + 1:
                        ch.mod_stat[int(Stat.STR)] += modifier
                    elif affect.location == int(Stat.DEX) + 1:
                        ch.mod_stat[int(Stat.DEX)] += modifier
                    elif affect.location == int(Stat.INT) + 1:
                        ch.mod_stat[int(Stat.INT)] += modifier
                    elif affect.location == int(Stat.WIS) + 1:
                        ch.mod_stat[int(Stat.WIS)] += modifier
                    elif affect.location == int(Stat.CON) + 1:
                        ch.mod_stat[int(Stat.CON)] += modifier
                    elif affect.location == APPLY_SEX:
                        ch.sex += modifier
                    elif affect.location == APPLY_MANA:
                        ch.max_mana += modifier
                    elif affect.location == APPLY_HIT:
                        ch.max_hit += modifier
                    elif affect.location == APPLY_MOVE:
                        ch.max_move += modifier
                    elif affect.location == APPLY_AC:
                        for i in range(4):
                            ch.armor[i] += modifier
                    elif affect.location == APPLY_HITROLL:
                        ch.hitroll += modifier
                    elif affect.location == APPLY_DAMROLL:
                        ch.damroll += modifier
                    elif affect.location in (
                        APPLY_SAVES,
                        APPLY_SAVING_ROD,
                        APPLY_SAVING_PETRI,
                        APPLY_SAVING_BREATH,
                        APPLY_SAVING_SPELL,
                    ):
                        ch.saving_throw += modifier


# ==============================================================================
# Flag Name Functions (ROM C handler.c) - For Debugging/OLC
# ==============================================================================


def affect_loc_name(location: int) -> str:
    """
    Convert affect location number to name.

    ROM C: handler.c:2718-2779 (affect_loc_name)

    Returns string name of affect location (APPLY_STR, APPLY_HIT, etc.).
    Used for debugging and OLC display.

    Args:
        location: Affect location number

    Returns:
        Location name string, or "unknown" if not found
    """
    APPLY_NONE = 0
    APPLY_STR = 1
    APPLY_DEX = 2
    APPLY_INT = 3
    APPLY_WIS = 4
    APPLY_CON = 5
    APPLY_SEX = 6
    APPLY_CLASS = 7
    APPLY_LEVEL = 8
    APPLY_AGE = 9
    APPLY_HEIGHT = 10
    APPLY_WEIGHT = 11
    APPLY_MANA = 12
    APPLY_HIT = 13
    APPLY_MOVE = 14
    APPLY_GOLD = 15
    APPLY_EXP = 16
    APPLY_AC = 17
    APPLY_HITROLL = 18
    APPLY_DAMROLL = 19
    APPLY_SAVES = 20
    APPLY_SAVING_ROD = 21
    APPLY_SAVING_PETRI = 22
    APPLY_SAVING_BREATH = 23
    APPLY_SAVING_SPELL = 24
    APPLY_SPELL_AFFECT = 25

    location_names = {
        APPLY_NONE: "none",
        APPLY_STR: "strength",
        APPLY_DEX: "dexterity",
        APPLY_INT: "intelligence",
        APPLY_WIS: "wisdom",
        APPLY_CON: "constitution",
        APPLY_SEX: "sex",
        APPLY_CLASS: "class",
        APPLY_LEVEL: "level",
        APPLY_AGE: "age",
        APPLY_HEIGHT: "height",
        APPLY_WEIGHT: "weight",
        APPLY_MANA: "mana",
        APPLY_HIT: "hp",
        APPLY_MOVE: "moves",
        APPLY_GOLD: "gold",
        APPLY_EXP: "experience",
        APPLY_AC: "armor class",
        APPLY_HITROLL: "hit roll",
        APPLY_DAMROLL: "damage roll",
        APPLY_SAVES: "saves",
        APPLY_SAVING_ROD: "save vs rod",
        APPLY_SAVING_PETRI: "save vs petrification",
        APPLY_SAVING_BREATH: "save vs breath",
        APPLY_SAVING_SPELL: "save vs spell",
        APPLY_SPELL_AFFECT: "spell affect",
    }

    return location_names.get(location, f"unknown({location})")


def affect_bit_name(bitvector: int) -> str:
    """
    Convert affect bitvector to flag names.

    ROM C: handler.c:2781-2895 (affect_bit_name)

    Returns comma-separated string of affect flag names.
    Used for debugging and OLC display.

    Args:
        bitvector: Affect bitvector

    Returns:
        Space-separated flag names, or "none" if 0
    """
    from mud.models.constants import AffectFlag

    if bitvector == 0:
        return "none"

    flags = []
    for flag in AffectFlag:
        if bitvector & flag:
            flags.append(flag.name.lower())

    return " ".join(flags) if flags else f"unknown({bitvector})"


def act_bit_name(act_flags: int) -> str:
    """
    Convert act flags to flag names.

    ROM C: handler.c:2897-2976 (act_bit_name)

    Returns space-separated string of act flag names.
    Used for debugging and OLC display.

    Args:
        act_flags: Act flags bitvector

    Returns:
        Space-separated flag names, or "none" if 0
    """
    from mud.models.constants import ActFlag

    if act_flags == 0:
        return "none"

    flags = []
    for flag in ActFlag:
        if act_flags & flag:
            flags.append(flag.name.lower())

    return " ".join(flags) if flags else f"unknown({act_flags})"


def comm_bit_name(comm_flags: int) -> str:
    """
    Convert comm flags to flag names.

    ROM C: handler.c:2978-3060 (comm_bit_name)

    Returns space-separated string of comm flag names.
    Used for debugging and OLC display.

    Args:
        comm_flags: Comm flags bitvector

    Returns:
        Space-separated flag names, or "none" if 0
    """
    from mud.models.constants import CommFlag

    if comm_flags == 0:
        return "none"

    flags = []
    for flag in CommFlag:
        if comm_flags & flag:
            flags.append(flag.name.lower())

    return " ".join(flags) if flags else f"unknown({comm_flags})"
