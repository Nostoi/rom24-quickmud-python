"""
Equipment and character manipulation handlers.

ROM References: src/handler.c lines 1754-1877
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.constants import ItemType, Stat, WearFlag, WearLocation
from mud.utils.fix_sex import fix_sex

if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.models.obj import Affect
    from mud.models.object import Object


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


def affect_enchant(obj: Object) -> None:
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

    # ROM src/handler.c:1211-1265 — per-instance affects, then (when
    # the obj is not enchanted) the prototype's affects. The prototype
    # walk is load-bearing: `.are` files put `A` entries on prototypes,
    # not on every spawned instance, so a `+sanc` ring whose grant lives
    # on `obj->pIndexData->affected` would otherwise be invisible here.
    # equip_char / unequip_char already walk the prototype affects on
    # equip / remove (mud/handler.py:179, 240); affect_check must match
    # so a temporary spell expiry doesn't strip a flag the equipment
    # still grants.
    if hasattr(ch, "equipment"):
        for obj in ch.equipment.values():
            if obj is None:
                continue
            obj_affected = getattr(obj, "affected", None) or []
            for paf in obj_affected:
                if not (hasattr(paf, "where") and hasattr(paf, "bitvector")):
                    continue
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

            if getattr(obj, "enchanted", False):
                continue

            prototype = getattr(obj, "prototype", None)
            proto_affected = getattr(prototype, "affected", None) or []
            for paf in proto_affected:
                if isinstance(paf, dict):
                    paf_where = paf.get("where", 0)
                    paf_vector = paf.get("bitvector", 0)
                else:
                    paf_where = getattr(paf, "where", 0)
                    paf_vector = getattr(paf, "bitvector", 0)
                if paf_where == where and paf_vector == vector:
                    if where == TO_AFFECTS:
                        ch.affected_by |= vector
                    elif where == TO_IMMUNE:
                        ch.imm_flags |= vector
                    elif where == TO_RESIST:
                        ch.res_flags |= vector
                    elif where == TO_VULN:
                        ch.vuln_flags |= vector
                    return


def affect_remove(ch: Character, paf: Affect) -> None:
    """Remove an affect from a character — ROM ``src/handler.c:1317``.

    Mirrors ROM exactly: ``affect_modify(ch, paf, FALSE)`` (subtracts
    the stat modifier and clears the bitvector in
    ``affected_by``/``imm_flags``/``res_flags``/``vuln_flags``),
    unlinks ``paf`` from ``ch.affected``, then calls
    ``affect_check(ch, where, vector)`` which re-sets the bitvector
    only if another affect on the char or equipped objects still
    provides it. INV-015 enforcement point for the affect-tick
    lifecycle contract.
    """

    affected = getattr(ch, "affected", None)
    if not isinstance(affected, list) or not affected:
        return

    where = getattr(paf, "where", 0)
    vector = getattr(paf, "bitvector", 0)

    affect_modify(ch, paf, False)

    try:
        affected.remove(paf)
    except ValueError:
        pass

    affect_check(ch, where, vector)


def affect_join(ch: Character, paf: Affect) -> None:
    """Add or enhance an affect — ROM ``src/handler.c:1464-1483``.

    Searches ``ch.affected`` for an existing entry with the same type.  When
    found, the new paf absorbs it: level is averaged, duration and modifier
    are summed, the old entry is removed via ``affect_remove``.  Then
    ``affect_to_char`` is called unconditionally with the (possibly merged) paf.

    # mirroring ROM src/handler.c:1464-1483 affect_join
    """
    affected = getattr(ch, "affected", None)
    if isinstance(affected, list):
        for paf_old in list(affected):
            if getattr(paf_old, "type", None) == getattr(paf, "type", None):
                # ROM: paf->level = (paf->level += paf_old->level) / 2
                paf.level = (paf.level + paf_old.level) // 2
                paf.duration += paf_old.duration
                paf.modifier += paf_old.modifier
                affect_remove(ch, paf_old)
                break

    ch.affect_to_char(paf)  # type: ignore[arg-type]  # AffectData duck-types Affect


def affect_to_obj(obj: Object, paf: Affect) -> None:
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


def affect_remove_obj(obj: Object, paf: Affect) -> None:
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


# NOTE: a dead `is_friend()` duplicate lived here. It was removed in the
# divergence-class flag-hex sweep (HANDLER-DEAD-001) — it hardcoded wrong assist
# bit values (`ASSIST_PLAYERS = 0x1` etc., bits 0-4) that disagreed with the
# canonical `OffFlag.ASSIST_PLAYERS = 1 << 18` (ROM letter macro `(S)`). It had
# no callers; the live mob-assist path is `mud/combat/assist.py`, which uses the
# `OffFlag` enum directly.


# ==============================================================================
# Utility & Lookup Functions (ROM C handler.c)
# ==============================================================================


def count_users(obj: Object) -> int:
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
        - Uses room.people (canonical attribute) instead of linked list
        - Returns 0 if object not in a room
    """
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        pass

    in_room = getattr(obj, "in_room", None) or getattr(obj, "location", None)
    if in_room is None:
        return 0

    count = 0
    characters = getattr(in_room, "people", None)
    if characters is None:
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
    from mud.models.weapon_table import weapon_name_for_type

    return weapon_name_for_type(weapon_type)


# ==============================================================================
# Character Attribute Functions (ROM C handler.c)
# ==============================================================================


def get_age(ch: Character) -> int:
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

    from mud.math.c_compat import c_div

    played = getattr(ch, "played", 0)
    current_time = time.time()
    logon = getattr(ch, "logon", current_time)
    if not logon:
        logon = current_time

    return 17 + c_div(int(played + (current_time - logon)), 72000)


def get_max_train(ch: Character, stat: int) -> int:
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
    from mud.models.races import get_pc_race, get_race_by_index

    is_npc = getattr(ch, "is_npc", False)
    level = getattr(ch, "level", 1)
    # ROM: IS_NPC(ch) || ch->level > LEVEL_IMMORTAL -> 25 (note: strict >)
    if is_npc or level > LEVEL_IMMORTAL:
        return 25

    # TRAIN-004: `ch.race` / `ch.ch_class` are int indices (mirroring ROM's
    # `ch->race` / `ch->class`), not name strings. Bridge the race index to
    # the pc_race_table by name; the RACE_TABLE sentinel offset means the
    # indices don't line up with PC_RACE_TABLE directly.
    race = get_race_by_index(getattr(ch, "race", 0))
    if race is None:
        return 25
    pc_race = get_pc_race(race.name)
    if pc_race is None or stat < 0 or stat >= len(pc_race.max_stats):
        # A real PC always resolves to a pc_race row; fall back defensively to
        # 25 (the NPC/immortal value) — ROM has no race_max fallback here.
        return 25

    max_stat = pc_race.max_stats[stat]

    # ROM src/handler.c:884-889 — the class's prime stat gets a bonus:
    # +3 for humans, +2 for every other race.
    class_index = getattr(ch, "ch_class", 0)
    if 0 <= class_index < len(CLASS_TABLE):
        prime_stat = int(CLASS_TABLE[class_index].prime_stat)
        if stat == prime_stat:
            max_stat += 3 if race.name == "human" else 2

    return min(max_stat, 25)  # ROM UMIN(max, 25)


# ==============================================================================
# Money Functions (ROM C handler.c)
# ==============================================================================


def deduct_cost(ch: Character, cost: int) -> None:
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


def create_money(gold: int, silver: int) -> Object:
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
    from mud.math.c_compat import c_div
    from mud.models.constants import (
        OBJ_VNUM_COINS,
        OBJ_VNUM_GOLD_ONE,
        OBJ_VNUM_GOLD_SOME,
        OBJ_VNUM_SILVER_ONE,
        OBJ_VNUM_SILVER_SOME,
        ItemType,
    )
    from mud.models.obj import ObjIndex
    from mud.models.object import create_object

    # ROM C handler.c:2432-2437 (validate input). NOTE: ROM bug()s then *clamps*
    # (`gold = UMAX(1, gold)`) and continues — it never returns NULL. The Python
    # port returns None here and callers guard on it; that return-None-vs-clamp
    # divergence is filed separately (not exercised by any current scenario).
    if gold < 0 or silver < 0 or (gold == 0 and silver == 0):
        print(f"BUG: create_money: zero or negative money ({gold} gold, {silver} silver)")
        return None

    # ROM money prototypes are real objects in limbo.are (#1-#5); ROM create_money
    # (src/handler.c:2438-2480) does `create_object(get_obj_index(VNUM))` then uses
    # the proto's short_descr as a printf format string. We fabricate an
    # equivalent per-call ObjIndex: Python reads object weight from
    # `obj.prototype.weight` (mud/commands/inventory.py:_get_obj_weight), so each
    # money object needs its OWN prototype — the shared registry proto cannot
    # carry a per-amount weight. The name keywords / short_descr formats /
    # descriptions / base values below are byte-for-byte limbo.are #1-#5.
    #
    # 2.13.11 wording-parity fix: Python previously fabricated "one silver coin" /
    # "N silver and N gold coins" with cost `100*gold`, diverging from ROM's
    # "a silver coin" / "N silver coins and N gold coins" and `cost = gold`.
    # Surfaced by the diff-harness money_drop_get_give scenario (C ground truth).
    vnum: int
    name: str
    short_descr: str
    description: str
    cost: int
    weight: int
    value_0: int  # silver
    value_1: int  # gold

    if gold == 0 and silver == 1:
        # ROM uses OBJ_VNUM_SILVER_ONE untouched (proto: value[0]=1, cost 0, weight 10).
        vnum = OBJ_VNUM_SILVER_ONE
        name = "coin silver gcash"
        short_descr = "a silver coin"
        description = "One miserable silver coin."
        cost = 0
        weight = 10
        value_0 = 1
        value_1 = 0
    elif gold == 1 and silver == 0:
        # ROM uses OBJ_VNUM_GOLD_ONE untouched (proto: value[1]=1, cost 0, weight 10).
        vnum = OBJ_VNUM_GOLD_ONE
        name = "coin gold gcash"
        short_descr = "a gold coin"
        description = "One valuable gold coin."
        cost = 0
        weight = 10
        value_0 = 0
        value_1 = 1
    elif silver == 0:
        # ROM src/handler.c:2448-2456 — `obj->cost = gold` (NOT 100*gold).
        vnum = OBJ_VNUM_GOLD_SOME
        name = "coins gold gcash"
        # ROM proto short_descr "%d gold coins" sprintf'd with gold.
        short_descr = f"{gold} gold coins"
        description = "A pile of gold coins."
        cost = gold
        weight = c_div(gold, 5)  # raw `gold / 5` (1-4 gold → weight 0)
        value_0 = 0
        value_1 = gold
    elif gold == 0:
        # ROM src/handler.c:2458-2466 — `obj->cost = silver`.
        vnum = OBJ_VNUM_SILVER_SOME
        name = "coins silver gcash"
        # ROM proto short_descr "%d silver coins" sprintf'd with silver.
        short_descr = f"{silver} silver coins"
        description = "A pile of silver coins."
        cost = silver
        weight = c_div(silver, 20)  # raw `silver / 20` (1-19 silver → weight 0)
        value_0 = silver
        value_1 = 0
    else:
        # ROM src/handler.c:2468-2479 — short_descr is "%d silver coins and %d
        # gold coins" (note the first "coins"); cost = 100*gold + silver.
        vnum = OBJ_VNUM_COINS
        name = "coins silver gold gcash"
        # ROM proto short_descr "%d silver coins and %d gold coins" (note the
        # first "coins") sprintf'd with (silver, gold).
        short_descr = f"{silver} silver coins and {gold} gold coins"
        description = "A pile of coins."
        cost = 100 * gold + silver
        weight = c_div(gold, 5) + c_div(silver, 20)  # raw `gold / 5 + silver / 20`
        value_0 = silver
        value_1 = gold

    # Per-call prototype so object weight (read from prototype.weight) is
    # per-amount and never mutates a shared registry proto.
    proto = ObjIndex(
        vnum=vnum,
        name=name,
        short_descr=short_descr,
        description=description,
        item_type=int(ItemType.MONEY),
        wear_flags=int(WearFlag.TAKE),
        value=[value_0, value_1, 0, 0, 0],
        weight=weight,
    )
    obj = create_object(proto)
    obj.item_type = int(ItemType.MONEY)
    obj.short_descr = short_descr
    obj.cost = cost
    obj.value = [value_0, value_1, 0, 0, 0]

    return obj


# NOTE: a dead `check_immune()` duplicate lived here. It was removed in the
# divergence-class flag-hex sweep (HANDLER-DEAD-002) — it hardcoded wrong RIV
# bit values (`IMM_WEAPON = 0x1` bit 0, `IMM_MAGIC = 0x2` bit 1) that disagreed
# with the canonical `DefenseBit.WEAPON = 1 << 3` / `DefenseBit.MAGIC = 1 << 2`
# (ROM letter macros `(D)` / `(C)`), and only handled WEAPON/MAGIC (TODO stub).
# It had no callers; the live RIV path is `mud/affects/saves.py::_check_immune`,
# exercised by `tests/test_saves_rom_parity.py`.


# ==============================================================================
# Character Reset Function (ROM C handler.c)
# ==============================================================================


def reset_char(ch: Character) -> None:
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
        for loc in range(19):  # mirrors ROM src/merc.h:1356 — MAX_WEAR = 19
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
                            fix_sex(ch)  # mirroring ROM src/comm.c:2178-2182
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
    for loc in range(19):  # mirrors ROM src/merc.h:1356 — MAX_WEAR = 19
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


# DUPL-007 — canonical affect_loc_name lives at mud/commands/affects.py:affect_loc_name
# (ROM-faithful: APPLY_SPELL_AFFECT → "none" per src/handler.c:2718-2775). The
# divergent copy formerly here (mapped APPLY_SPELL_AFFECT → "spell affect") was
# unused; removed in 2.9.30.


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


def wear_bit_name(wear_flags: int) -> str:
    """
    Convert wear flags bitvector to flag names.

    ROM C: handler.c:3062-3110 (wear_bit_name)

    Args:
        wear_flags: Wear flags bitvector

    Returns:
        Space-separated flag names, or "none" if 0
    """
    from mud.models.constants import WearFlag as WF

    if wear_flags == 0:
        return "none"

    flags = []
    for flag in WF:
        if wear_flags & flag:
            flags.append(flag.name.lower())

    return " ".join(flags) if flags else f"unknown({wear_flags})"


def extra_bit_name(extra_flags: int) -> str:
    """
    Convert extra flags bitvector to flag names.

    ROM C: handler.c:3112-3190 (extra_bit_name)

    Args:
        extra_flags: Extra flags bitvector

    Returns:
        Space-separated flag names, or "none" if 0
    """
    from mud.models.constants import ExtraFlag as EF

    if extra_flags == 0:
        return "none"

    flags = []
    for flag in EF:
        if extra_flags & flag:
            flags.append(flag.name.lower())

    return " ".join(flags) if flags else f"unknown({extra_flags})"


def imm_bit_name(imm_flags: int) -> str:
    """
    Convert immune/resist/vuln flags to flag names.

    ROM C: handler.c:2899-2975 (uses IRV_NAMES for immune, resist, vulnerable)

    Args:
        imm_flags: Immune/resist/vuln flags bitvector

    Returns:
        Space-separated flag names, or "none" if 0
    """
    from mud.models.constants import ImmFlag as IF
    from mud.models.constants import ResFlag as RF
    from mud.models.constants import VulnFlag as VF

    if imm_flags == 0:
        return "none"

    flags = []
    for flag_set in (IF, RF, VF):
        for flag in flag_set:
            if imm_flags & flag and flag not in flags:
                flags.append(flag.name.lower())

    return " ".join(flags) if flags else f"unknown({imm_flags})"


def off_bit_name(off_flags: int) -> str:
    """
    Convert offensive flags to flag names.

    ROM C: handler.c:3193-3227 (off_bit_name)

    Args:
        off_flags: Offensive flags bitvector

    Returns:
        Space-separated flag names, or "none" if 0
    """
    from mud.models.constants import OffFlag as OF

    if off_flags == 0:
        return "none"

    flags = []
    for flag in OF:
        if off_flags & flag:
            flags.append(flag.name.lower())

    return " ".join(flags) if flags else f"unknown({off_flags})"


def form_bit_name(form_flags: int) -> str:
    """
    Convert form flags to flag names.

    ROM C: handler.c:3229-3267 (form_bit_name)

    Args:
        form_flags: Form flags bitvector

    Returns:
        Space-separated flag names, or "none" if 0
    """
    from mud.models.constants import FormFlag as FF

    if form_flags == 0:
        return "none"

    flags = []
    for flag in FF:
        if form_flags & flag:
            flags.append(flag.name.lower())

    return " ".join(flags) if flags else f"unknown({form_flags})"


def part_bit_name(part_flags: int) -> str:
    """
    Convert body-part flags to flag names.

    ROM C: handler.c:3269-3312 (part_bit_name)

    Args:
        part_flags: Body-part flags bitvector

    Returns:
        Space-separated flag names, or "none" if 0
    """
    from mud.models.constants import PartFlag as PF

    if part_flags == 0:
        return "none"

    flags = []
    for flag in PF:
        if part_flags & flag:
            flags.append(flag.name.lower())

    return " ".join(flags) if flags else f"unknown({part_flags})"


def weapon_bit_name(weapon_flags: int) -> str:
    """
    Convert weapon flags to flag names.

    ROM C: handler.c (weapon_bit_name)

    Args:
        weapon_flags: Weapon flags bitvector

    Returns:
        Space-separated flag names, or "none" if 0
    """
    from mud.models.constants import WeaponFlag as WF

    if weapon_flags == 0:
        return "none"

    flags = []
    for flag in WF:
        if weapon_flags & flag:
            flags.append(flag.name.lower())

    return " ".join(flags) if flags else f"unknown({weapon_flags})"


def cont_bit_name(cont_flags: int) -> str:
    """
    Convert container flags to flag names.

    ROM C: handler.c (cont_bit_name)

    Args:
        cont_flags: Container flags bitvector

    Returns:
        Space-separated flag names, or "none" if 0
    """
    from mud.models.constants import ContainerFlag as CF

    if cont_flags == 0:
        return "none"

    flags = []
    for flag in CF:
        if cont_flags & flag:
            flags.append(flag.name.lower())

    return " ".join(flags) if flags else f"unknown({cont_flags})"


def size_name(size_val: int) -> str:
    """Convert size enum value to ROM name string."""
    from mud.models.constants import Size

    try:
        return Size(size_val).name.lower()
    except ValueError:
        return "unknown"


def position_name(pos_val: int) -> str:
    """Convert position enum value to ROM name string."""
    from mud.models.constants import Position

    try:
        return Position(pos_val).name.lower()
    except ValueError:
        return "unknown"


def sex_name(sex_val: int) -> str:
    """Convert sex enum value to ROM name string.

    ROM C: sex_table indexed lookup.
    """
    from mud.models.constants import Sex

    try:
        return Sex(sex_val).name.lower()
    except ValueError:
        return "none"


def race_name(race_val: int | str) -> str:
    """Convert player race ids to ROM-visible race names."""
    if isinstance(race_val, str):
        return race_val.lower()

    from mud.models.races import PC_RACE_TABLE

    if 0 <= race_val < len(PC_RACE_TABLE):
        return PC_RACE_TABLE[race_val].name.lower()
    return f"unknown({race_val})"


def class_name(class_val: int | str) -> str:
    """Convert class to ROM name string."""
    if isinstance(class_val, str):
        return class_val.lower()

    from mud.models.classes import CLASS_TABLE

    if 0 <= class_val < len(CLASS_TABLE):
        return CLASS_TABLE[class_val].name.lower()
    return "mobile"
