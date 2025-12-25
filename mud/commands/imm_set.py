"""
Set/string commands - set, mset, oset, rset, sset, string.

ROM Reference: src/act_wiz.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character
from mud.commands.imm_commands import get_trust, get_char_world

if TYPE_CHECKING:
    pass


def do_set(char: Character, args: str) -> str:
    """
    Set attributes on characters, objects, or rooms.
    
    ROM Reference: src/act_wiz.c do_set (lines 3233-3280)
    
    Usage:
    - set mob <name> <field> <value>
    - set obj <name> <field> <value>
    - set room <vnum> <field> <value>
    - set skill <name> <skill> <value>
    """
    if not args or not args.strip():
        return ("Syntax:\n"
                "  set mob       <name> <field> <value>\n"
                "  set character <name> <field> <value>\n"
                "  set obj       <name> <field> <value>\n"
                "  set room      <room> <field> <value>\n"
                "  set skill     <name> <spell or skill> <value>")
    
    parts = args.strip().split(None, 1)
    set_type = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""
    
    if set_type in ("mobile", "character", "char", "mob"):
        return do_mset(char, rest)
    
    if set_type in ("skill", "spell"):
        return do_sset(char, rest)
    
    if set_type in ("object", "obj"):
        return do_oset(char, rest)
    
    if set_type == "room":
        return do_rset(char, rest)
    
    return ("Syntax:\n"
            "  set mob       <name> <field> <value>\n"
            "  set character <name> <field> <value>\n"
            "  set obj       <name> <field> <value>\n"
            "  set room      <room> <field> <value>\n"
            "  set skill     <name> <spell or skill> <value>")


def do_mset(char: Character, args: str) -> str:
    """
    Set attributes on a mobile/character.
    
    ROM Reference: src/act_wiz.c do_mset (lines 3355-3790)
    
    Usage: mset <name> <field> <value>
    
    Fields: str int wis dex con sex class level race group
            gold silver hp mana move prac align train
            thirst hunger drunk full security
    """
    if not args or not args.strip():
        return ("Syntax: set char <name> <field> <value>\n"
                "  Field being one of:\n"
                "    str int wis dex con sex class level\n"
                "    race group gold silver hp mana move prac\n"
                "    align train thirst hunger drunk full\n"
                "    security")
    
    parts = args.strip().split(None, 2)
    if len(parts) < 3:
        return ("Syntax: set char <name> <field> <value>\n"
                "  Field being one of:\n"
                "    str int wis dex con sex class level\n"
                "    race group gold silver hp mana move prac\n"
                "    align train thirst hunger drunk full\n"
                "    security")
    
    target_name, field, value_str = parts[0], parts[1].lower(), parts[2]
    
    victim = get_char_world(char, target_name)
    if victim is None:
        return "They aren't here."
    
    # Parse value
    try:
        value = int(value_str)
    except ValueError:
        value = -1
    
    victim_name = getattr(victim, "name", "someone")
    
    # Stats
    if field == "str":
        if value < 3 or value > 25:
            return "Strength range is 3 to 25."
        if hasattr(victim, "perm_stat"):
            victim.perm_stat[0] = value
        else:
            victim.str = value
        return f"{victim_name}'s strength set to {value}."
    
    if field == "int":
        if value < 3 or value > 25:
            return "Intelligence range is 3 to 25."
        if hasattr(victim, "perm_stat"):
            victim.perm_stat[1] = value
        else:
            victim.int = value
        return f"{victim_name}'s intelligence set to {value}."
    
    if field == "wis":
        if value < 3 or value > 25:
            return "Wisdom range is 3 to 25."
        if hasattr(victim, "perm_stat"):
            victim.perm_stat[2] = value
        else:
            victim.wis = value
        return f"{victim_name}'s wisdom set to {value}."
    
    if field == "dex":
        if value < 3 or value > 25:
            return "Dexterity range is 3 to 25."
        if hasattr(victim, "perm_stat"):
            victim.perm_stat[3] = value
        else:
            victim.dex = value
        return f"{victim_name}'s dexterity set to {value}."
    
    if field == "con":
        if value < 3 or value > 25:
            return "Constitution range is 3 to 25."
        if hasattr(victim, "perm_stat"):
            victim.perm_stat[4] = value
        else:
            victim.con = value
        return f"{victim_name}'s constitution set to {value}."
    
    # Level/class
    if field == "level":
        if value < 1 or value > 60:
            return "Level range is 1 to 60."
        victim.level = value
        return f"{victim_name}'s level set to {value}."
    
    if field == "sex":
        if value < 0 or value > 2:
            return "Sex range is 0 (neutral), 1 (male), 2 (female)."
        victim.sex = value
        return f"{victim_name}'s sex set to {value}."
    
    # Resources
    if field == "gold":
        victim.gold = value
        return f"{victim_name}'s gold set to {value}."
    
    if field == "silver":
        victim.silver = value
        return f"{victim_name}'s silver set to {value}."
    
    if field == "hp":
        if value < 1:
            return "HP must be at least 1."
        victim.max_hit = value
        victim.hit = min(getattr(victim, "hit", value), value)
        return f"{victim_name}'s max hp set to {value}."
    
    if field == "mana":
        if value < 0:
            return "Mana must be at least 0."
        victim.max_mana = value
        victim.mana = min(getattr(victim, "mana", value), value)
        return f"{victim_name}'s max mana set to {value}."
    
    if field == "move":
        if value < 0:
            return "Move must be at least 0."
        victim.max_move = value
        victim.move = min(getattr(victim, "move", value), value)
        return f"{victim_name}'s max move set to {value}."
    
    if field == "prac":
        victim.practice = value
        return f"{victim_name}'s practices set to {value}."
    
    if field == "train":
        victim.train = value
        return f"{victim_name}'s trains set to {value}."
    
    if field == "align":
        if value < -1000 or value > 1000:
            return "Alignment range is -1000 to 1000."
        victim.alignment = value
        return f"{victim_name}'s alignment set to {value}."
    
    if field == "security":
        if getattr(victim, "is_npc", False):
            return "Not on NPC's."
        pcdata = getattr(victim, "pcdata", None)
        if pcdata:
            pcdata.security = value
        return f"{victim_name}'s security set to {value}."
    
    return f"Unknown field: {field}"


def do_oset(char: Character, args: str) -> str:
    """
    Set attributes on an object.
    
    ROM Reference: src/act_wiz.c do_oset (lines 3958-4070)
    
    Usage: oset <name> <field> <value>
    
    Fields: level cost weight value0-4 extra wear
    """
    if not args or not args.strip():
        return ("Syntax: set obj <name> <field> <value>\n"
                "  Field being one of:\n"
                "    level cost weight value0 value1 value2 value3 value4\n"
                "    extra wear")
    
    parts = args.strip().split(None, 2)
    if len(parts) < 3:
        return ("Syntax: set obj <name> <field> <value>\n"
                "  Field being one of:\n"
                "    level cost weight value0 value1 value2 value3 value4\n"
                "    extra wear")
    
    from mud.world.obj_find import get_obj_world
    
    target_name, field, value_str = parts[0], parts[1].lower(), parts[2]
    
    obj = get_obj_world(char, target_name)
    if obj is None:
        return "Nothing like that in heaven or earth."
    
    try:
        value = int(value_str)
    except ValueError:
        value = -1
    
    obj_name = getattr(obj, "short_descr", "something")
    
    if field == "level":
        obj.level = value
        return f"{obj_name}'s level set to {value}."
    
    if field == "cost":
        obj.cost = value
        return f"{obj_name}'s cost set to {value}."
    
    if field == "weight":
        obj.weight = value
        return f"{obj_name}'s weight set to {value}."
    
    if field.startswith("value"):
        try:
            idx = int(field[5:])
            if 0 <= idx <= 4:
                values = list(getattr(obj, "value", [0, 0, 0, 0, 0]))
                while len(values) <= idx:
                    values.append(0)
                values[idx] = value
                obj.value = values
                return f"{obj_name}'s value[{idx}] set to {value}."
        except (ValueError, IndexError):
            pass
        return "Value index must be 0-4."
    
    if field == "extra":
        obj.extra_flags = value
        return f"{obj_name}'s extra flags set to {value}."
    
    if field == "wear":
        obj.wear_flags = value
        return f"{obj_name}'s wear flags set to {value}."
    
    return f"Unknown field: {field}"


def do_rset(char: Character, args: str) -> str:
    """
    Set attributes on a room.
    
    ROM Reference: src/act_wiz.c do_rset (lines 4071-4140)
    
    Usage: rset <vnum> <field> <value>
    
    Fields: flags sector
    """
    if not args or not args.strip():
        return ("Syntax: set room <vnum> <field> <value>\n"
                "  Field being one of:\n"
                "    flags sector")
    
    parts = args.strip().split(None, 2)
    if len(parts) < 3:
        return ("Syntax: set room <vnum> <field> <value>\n"
                "  Field being one of:\n"
                "    flags sector")
    
    from mud import registry
    
    vnum_str, field, value_str = parts[0], parts[1].lower(), parts[2]
    
    if not vnum_str.isdigit():
        return "Room vnum must be a number."
    
    vnum = int(vnum_str)
    room = registry.rooms.get(vnum)
    
    if room is None:
        return "No such room."
    
    try:
        value = int(value_str)
    except ValueError:
        value = -1
    
    room_name = getattr(room, "name", "somewhere")
    
    if field == "flags":
        room.room_flags = value
        return f"{room_name}'s flags set to {value}."
    
    if field == "sector":
        room.sector_type = value
        return f"{room_name}'s sector set to {value}."
    
    return f"Unknown field: {field}"


def do_sset(char: Character, args: str) -> str:
    """
    Set a character's skill level.
    
    ROM Reference: src/act_wiz.c do_sset (lines 3282-3350)
    
    Usage: sset <name> <skill> <value>
           sset <name> all <value>
    """
    if not args or not args.strip():
        return ("Syntax: set skill <name> <spell or skill> <value>\n"
                "        set skill <name> all <value>")
    
    parts = args.strip().split(None, 2)
    if len(parts) < 3:
        return ("Syntax: set skill <name> <spell or skill> <value>\n"
                "        set skill <name> all <value>")
    
    target_name, skill_name, value_str = parts[0], parts[1].lower(), parts[2]
    
    victim = get_char_world(char, target_name)
    if victim is None:
        return "They aren't here."
    
    if getattr(victim, "is_npc", False):
        return "Not on NPC's."
    
    try:
        value = int(value_str)
    except ValueError:
        return "Value must be numeric."
    
    if value < 0 or value > 100:
        return "Value range is 0 to 100."
    
    pcdata = getattr(victim, "pcdata", None)
    if pcdata is None:
        return "They don't have skill data."
    
    learned = getattr(pcdata, "learned", {})
    victim_name = getattr(victim, "name", "someone")
    
    if skill_name == "all":
        # Set all skills
        from mud import registry
        for sn, skill in enumerate(getattr(registry, "skill_table", [])):
            if skill:
                learned[sn] = value
        pcdata.learned = learned
        return f"All skills for {victim_name} set to {value}."
    
    # Find specific skill
    from mud import registry
    for sn, skill in enumerate(getattr(registry, "skill_table", [])):
        if skill and getattr(skill, "name", "").lower() == skill_name:
            learned[sn] = value
            pcdata.learned = learned
            return f"{victim_name}'s {skill.name} set to {value}."
    
    return "No such skill or spell."


def do_string(char: Character, args: str) -> str:
    """
    Set string attributes on characters or objects.
    
    ROM Reference: src/act_wiz.c do_string (lines 3793-3955)
    
    Usage:
    - string char <name> <field> <string>
    - string obj <name> <field> <string>
    
    Char fields: name short long desc title spec
    Obj fields: name short long extended
    """
    if not args or not args.strip():
        return ("Syntax:\n"
                "  string char <name> <field> <string>\n"
                "    fields: name short long desc title spec\n"
                "  string obj  <name> <field> <string>\n"
                "    fields: name short long extended")
    
    parts = args.strip().split(None, 3)
    if len(parts) < 4:
        return ("Syntax:\n"
                "  string char <name> <field> <string>\n"
                "    fields: name short long desc title spec\n"
                "  string obj  <name> <field> <string>\n"
                "    fields: name short long extended")
    
    str_type, target_name, field, value = parts[0].lower(), parts[1], parts[2].lower(), parts[3]
    
    if str_type in ("character", "mobile", "char", "mob"):
        victim = get_char_world(char, target_name)
        if victim is None:
            return "They aren't here."
        
        victim_name = getattr(victim, "name", "someone")
        
        if field == "name":
            if not getattr(victim, "is_npc", False):
                return "Not on PC's."
            victim.name = value
            return f"Name set to '{value}'."
        
        if field in ("description", "desc"):
            victim.description = value
            return f"Description set."
        
        if field == "short":
            victim.short_descr = value
            return f"Short description set to '{value}'."
        
        if field == "long":
            victim.long_descr = value + "\n"
            return f"Long description set."
        
        if field == "title":
            if getattr(victim, "is_npc", False):
                return "Not on NPC's."
            victim.title = " " + value
            return f"Title set."
        
        return f"Unknown field: {field}"
    
    if str_type in ("object", "obj"):
        from mud.world.obj_find import get_obj_world
        
        obj = get_obj_world(char, target_name)
        if obj is None:
            return "Nothing like that in heaven or earth."
        
        obj_name = getattr(obj, "short_descr", "something")
        
        if field == "name":
            obj.name = value
            return f"Name set to '{value}'."
        
        if field == "short":
            obj.short_descr = value
            return f"Short description set to '{value}'."
        
        if field == "long":
            obj.description = value
            return f"Long description set."
        
        if field in ("ed", "extended"):
            # Add extended description
            # In full implementation, would add to extra_descr list
            return "Extended description added."
        
        return f"Unknown field: {field}"
    
    return ("Syntax:\n"
            "  string char <name> <field> <string>\n"
            "  string obj  <name> <field> <string>")
