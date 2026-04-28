"""
Set/string commands - set, mset, oset, rset, sset, string.

ROM Reference: src/act_wiz.c
"""
from __future__ import annotations

from mud.models.character import Character
from mud.commands.imm_commands import get_trust, get_char_world
from mud.utils.text import smash_tilde


def do_set(char: Character, args: str) -> str:
    """
    Set attributes on characters, objects, or rooms.

    ROM Reference: src/act_wiz.c do_set (lines 3233-3275)

    Dispatches to do_mset/do_sset/do_oset/do_rset based on first argument.
    """
    if not args or not args.strip():
        return ("Syntax:\n\r"
                "  set mob       <name> <field> <value>\n\r"
                "  set character <name> <field> <value>\n\r"
                "  set obj       <name> <field> <value>\n\r"
                "  set room      <room> <field> <value>\n\r"
                "  set skill     <name> <spell or skill> <value>\n\r")

    parts = args.strip().split(None, 1)
    first_arg = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    if first_arg.startswith("mobile") or first_arg.startswith("character"):
        return do_mset(char, rest)

    if first_arg.startswith("skill") or first_arg.startswith("spell"):
        return do_sset(char, rest)

    if first_arg.startswith("object"):
        return do_oset(char, rest)

    if first_arg.startswith("room"):
        return do_rset(char, rest)

    return do_set(char, "")


def do_mset(char: Character, args: str) -> str:
    """
    Set attributes on a mobile/character.

    ROM Reference: src/act_wiz.c do_mset (lines 3355-3790)

    Usage: mset <name> <field> <value>

    Fields: str int wis dex con sex class level race group
            gold silver hp mana move prac align train thirst hunger drunk full
            security hours
    """
    smash = smash_tilde(args)
    parts = smash.split(None, 2)

    if len(parts) < 3 or not parts[0] or not parts[1] or not parts[2]:
        return ("Syntax:\n\r"
                "  set char <name> <field> <value>\n\r"
                "  Field being one of:\n\r"
                "    str int wis dex con sex class level\n\r"
                "    race group gold silver hp mana move prac\n\r"
                "    align train thirst hunger drunk full\n\r"
                "    security hours\n\r")

    target_name, field, value_str = parts[0], parts[1].lower(), parts[2]

    victim = get_char_world(char, target_name)
    if victim is None:
        return "They aren't here.\n\r"

    victim.zone = None

    value = int(value_str) if value_str.lstrip("-").isdigit() else -1

    from mud.models.constants import STAT_STR, STAT_INT, STAT_WIS, STAT_DEX, STAT_CON
    from mud.handler import get_max_train

    victim_name = getattr(victim, "name", "someone")

    if field == "str":
        max_stat = get_max_train(victim, STAT_STR)
        if value < 3 or value > max_stat:
            return f"Strength range is 3 to {max_stat}\n\r."
        victim.perm_stat[STAT_STR] = value
        return ""

    if field == "security":
        if getattr(char, "is_npc", False):
            return "NPC's can't set this value.\n\r"
        if getattr(victim, "is_npc", False):
            return "Not on NPC's.\n\r"
        ch_security = getattr(getattr(char, "pcdata", None), "security", 0)
        if value > ch_security or value < 0:
            if ch_security != 0:
                return f"Valid security is 0-{ch_security}.\n\r"
            else:
                return "Valid security is 0 only.\n\r"
        victim.pcdata.security = value
        return ""

    if field == "int":
        max_stat = get_max_train(victim, STAT_INT)
        if value < 3 or value > max_stat:
            return f"Intelligence range is 3 to {max_stat}.\n\r"
        victim.perm_stat[STAT_INT] = value
        return ""

    if field == "wis":
        max_stat = get_max_train(victim, STAT_WIS)
        if value < 3 or value > max_stat:
            return f"Wisdom range is 3 to {max_stat}.\n\r"
        victim.perm_stat[STAT_WIS] = value
        return ""

    if field == "dex":
        max_stat = get_max_train(victim, STAT_DEX)
        if value < 3 or value > max_stat:
            return f"Dexterity range is 3 to {max_stat}.\n\r"
        victim.perm_stat[STAT_DEX] = value
        return ""

    if field == "con":
        max_stat = get_max_train(victim, STAT_CON)
        if value < 3 or value > max_stat:
            return f"Constitution range is 3 to {max_stat}.\n\r"
        victim.perm_stat[STAT_CON] = value
        return ""

    if field.startswith("sex"):
        if value < 0 or value > 2:
            return "Sex range is 0 to 2.\n\r"
        victim.sex = value
        if not getattr(victim, "is_npc", False):
            victim.pcdata.true_sex = value
        return ""

    if field.startswith("class"):
        if getattr(victim, "is_npc", False):
            return "Mobiles have no class.\n\r"

        from mud.models.classes import CLASS_TABLE

        cls = None
        for c in CLASS_TABLE:
            if c.name.lower() == value_str.lower():
                cls = c
                break
            if c.name.lower().startswith(value_str.lower()):
                cls = c

        if cls is None:
            names = " ".join(c.name for c in CLASS_TABLE)
            return f"Possible classes are: {names}.\n\r"

        victim.class_num = CLASS_TABLE.index(cls)
        return ""

    if field.startswith("level"):
        if not getattr(victim, "is_npc", False):
            return "Not on PC's.\n\r"

        from mud.models.constants import MAX_LEVEL

        if value < 0 or value > MAX_LEVEL:
            return f"Level range is 0 to {MAX_LEVEL}.\n\r"
        victim.level = value
        return ""

    if field.startswith("gold"):
        victim.gold = value
        return ""

    if field.startswith("silver"):
        victim.silver = value
        return ""

    if field.startswith("hp"):
        if value < -10 or value > 30000:
            return "Hp range is -10 to 30,000 hit points.\n\r"
        victim.max_hit = value
        if not getattr(victim, "is_npc", False):
            victim.pcdata.perm_hit = value
        return ""

    if field.startswith("mana"):
        if value < 0 or value > 30000:
            return "Mana range is 0 to 30,000 mana points.\n\r"
        victim.max_mana = value
        if not getattr(victim, "is_npc", False):
            victim.pcdata.perm_mana = value
        return ""

    if field.startswith("move"):
        if value < 0 or value > 30000:
            return "Move range is 0 to 30,000 move points.\n\r"
        victim.max_move = value
        if not getattr(victim, "is_npc", False):
            victim.pcdata.perm_move = value
        return ""

    if field.startswith("prac"):
        if value < 0 or value > 250:
            return "Practice range is 0 to 250 sessions.\n\r"
        victim.practice = value
        return ""

    if field.startswith("train"):
        if value < 0 or value > 50:
            return "Training session range is 0 to 50 sessions.\n\r"
        victim.train = value
        return ""

    if field.startswith("align"):
        if value < -1000 or value > 1000:
            return "Alignment range is -1000 to 1000.\n\r"
        victim.alignment = value
        return ""

    if field.startswith("thirst"):
        if getattr(victim, "is_npc", False):
            return "Not on NPC's.\n\r"
        if value < -1 or value > 100:
            return "Thirst range is -1 to 100.\n\r"
        victim.pcdata.condition[2] = value
        return ""

    if field.startswith("drunk"):
        if getattr(victim, "is_npc", False):
            return "Not on NPC's.\n\r"
        if value < -1 or value > 100:
            return "Drunk range is -1 to 100.\n\r"
        victim.pcdata.condition[0] = value
        return ""

    if field.startswith("full"):
        if getattr(victim, "is_npc", False):
            return "Not on NPC's.\n\r"
        if value < -1 or value > 100:
            return "Full range is -1 to 100.\n\r"
        victim.pcdata.condition[1] = value
        return ""

    if field.startswith("hunger"):
        if getattr(victim, "is_npc", False):
            return "Not on NPC's.\n\r"
        if value < -1 or value > 100:
            return "Full range is -1 to 100.\n\r"
        victim.pcdata.condition[3] = value
        return ""

    if field.startswith("race"):
        from mud.models.races import RACE_TABLE, PC_RACE_TABLE

        race_found = None
        for r in RACE_TABLE:
            if r.name.lower() == value_str.lower():
                race_found = r
                break
            if r.name.lower().startswith(value_str.lower()):
                race_found = r
                break

        if race_found is None:
            return "That is not a valid race.\n\r"

        if not getattr(victim, "is_npc", False):
            pc_race_found = False
            for r in PC_RACE_TABLE:
                if r.name == race_found.name:
                    pc_race_found = True
                    break
            if not pc_race_found:
                return "That is not a valid player race.\n\r"

        victim.race = race_found.name
        return ""

    if field.startswith("group"):
        if not getattr(victim, "is_npc", False):
            return "Only on NPCs.\n\r"
        victim.group = value
        return ""

    if field.startswith("hours"):
        if getattr(victim, "is_npc", False):
            return "Not on NPC's.\n\r"
        if not value_str.lstrip("-").isdigit():
            return "Value must be numeric.\n\r"
        hours_val = int(value_str)
        if hours_val < 0 or hours_val > 999:
            return "Value must be between 0 and 999.\n\r"
        victim.played = hours_val * 3600
        return f"{victim_name}'s hours set to {hours_val}."

    return do_mset(char, "")


def do_sset(char: Character, args: str) -> str:
    """
    Set a character's skill level.

    ROM Reference: src/act_wiz.c do_sset (lines 3278-3352)

    Usage: sset <name> <skill> <value>
           sset <name> all <value>
    """
    parts = args.strip().split(None, 2)

    if len(parts) < 3 or not parts[0] or not parts[1] or not parts[2]:
        return ("Syntax:\n\r"
                "  set skill <name> <spell or skill> <value>\n\r"
                "  set skill <name> all <value>\n\r"
                "   (use the name of the skill, not the number)\n\r")

    target_name, skill_name, value_str = parts[0], parts[1].lower(), parts[2]

    victim = get_char_world(char, target_name)
    if victim is None:
        return "They aren't here.\n\r"

    if getattr(victim, "is_npc", False):
        return "Not on NPC's.\n\r"

    if not value_str.lstrip("-").isdigit():
        return "Value must be numeric.\n\r"

    value = int(value_str)
    if value < 0 or value > 100:
        return "Value range is 0 to 100.\n\r"

    pcdata = getattr(victim, "pcdata", None)
    if pcdata is None:
        return "They don't have skill data.\n\r"

    learned = getattr(pcdata, "learned", {})

    if skill_name == "all":
        from mud import registry
        skill_table = getattr(registry, "skill_table", [])
        for sn, skill in enumerate(skill_table):
            if skill and getattr(skill, "name", None):
                learned[sn] = value
        pcdata.learned = learned
        return ""

    from mud import registry
    skill_table = getattr(registry, "skill_table", [])

    for sn, skill in enumerate(skill_table):
        if skill and getattr(skill, "name", None):
            if skill.name.lower() == skill_name or skill.name.lower().startswith(skill_name):
                learned[sn] = value
                pcdata.learned = learned
                return ""

    return "No such skill or spell.\n\r"


def do_oset(char: Character, args: str) -> str:
    """
    Set attributes on an object.

    ROM Reference: src/act_wiz.c do_oset (lines 3958-4067)

    Usage: oset <name> <field> <value>

    Fields: value0-4 (v0-v4), extra, wear, level, weight, cost, timer
    """
    smash = smash_tilde(args)
    parts = smash.split(None, 2)

    if len(parts) < 3 or not parts[0] or not parts[1] or not parts[2]:
        return ("Syntax:\n\r"
                "  set obj <object> <field> <value>\n\r"
                "  Field being one of:\n\r"
                "    value0 value1 value2 value3 value4 (v1-v4)\n\r"
                "    extra wear level weight cost timer\n\r")

    target_name, field, value_str = parts[0], parts[1].lower(), parts[2]

    from mud.world.obj_find import get_obj_world
    obj = get_obj_world(char, target_name)
    if obj is None:
        return "Nothing like that in heaven or earth.\n\r"

    value = int(value_str) if value_str.lstrip("-").isdigit() else -1

    if field in ("value0", "v0"):
        obj.value[0] = min(50, value)
        return ""

    if field in ("value1", "v1"):
        obj.value[1] = value
        return ""

    if field in ("value2", "v2"):
        obj.value[2] = value
        return ""

    if field in ("value3", "v3"):
        obj.value[3] = value
        return ""

    if field in ("value4", "v4"):
        obj.value[4] = value
        return ""

    if field.startswith("extra"):
        obj.extra_flags = value
        return ""

    if field.startswith("wear"):
        obj.wear_flags = value
        return ""

    if field.startswith("level"):
        obj.level = value
        return ""

    if field.startswith("weight"):
        obj.weight = value
        return ""

    if field.startswith("cost"):
        obj.cost = value
        return ""

    if field.startswith("timer"):
        obj.timer = value
        return ""

    return do_oset(char, "")


def do_rset(char: Character, args: str) -> str:
    """
    Set attributes on a room.

    ROM Reference: src/act_wiz.c do_rset (lines 4071-4136)

    Usage: rset <vnum> <field> <value>

    Fields: flags sector
    """
    smash = smash_tilde(args)
    parts = smash.split(None, 2)

    if len(parts) < 3 or not parts[0] or not parts[1] or not parts[2]:
        return ("Syntax:\n\r"
                "  set room <location> <field> <value>\n\r"
                "  Field being one of:\n\r"
                "    flags sector\n\r")

    location_name, field, value_str = parts[0], parts[1].lower(), parts[2]

    from mud.commands.imm_commands import find_location, _is_room_owner, _room_is_private
    from mud.models.constants import MAX_LEVEL

    location = find_location(char, location_name)
    if location is None:
        return "No such location.\n\r"

    if not _is_room_owner(char, location) and char.room is not location and _room_is_private(location) and get_trust(char) < MAX_LEVEL:
        return "That room is private right now.\n\r"

    if not value_str.lstrip("-").isdigit():
        return "Value must be numeric.\n\r"

    value = int(value_str)

    if field.startswith("flags"):
        location.room_flags = value
        return ""

    if field.startswith("sector"):
        location.sector_type = value
        return ""

    return do_rset(char, "")


def do_string(char: Character, args: str) -> str:
    """
    Set string attributes on characters or objects.

    ROM Reference: src/act_wiz.c do_string (lines 3793-3954)

    Usage:
    - string char <name> <field> <string>
    - string obj <name> <field> <string>

    Char fields: name short long desc title spec
    Obj fields: name short long extended
    """
    smash = smash_tilde(args)
    parts = smash.split(None, 3)

    if len(parts) < 4 or not parts[0] or not parts[1] or not parts[2] or not parts[3]:
        return ("Syntax:\n\r"
                "  string char <name> <field> <string>\n\r"
                "    fields: name short long desc title spec\n\r"
                "  string obj  <name> <field> <string>\n\r"
                "    fields: name short long extended\n\r")

    str_type, target_name, field, value = parts[0].lower(), parts[1], parts[2].lower(), parts[3]

    if str_type.startswith("character") or str_type.startswith("mobile"):
        victim = get_char_world(char, target_name)
        if victim is None:
            return "They aren't here.\n\r"

        victim.zone = None

        if field.startswith("name"):
            if not getattr(victim, "is_npc", False):
                return "Not on PC's.\n\r"
            victim.name = value
            return ""

        if field.startswith("description"):
            victim.description = value
            return ""

        if field.startswith("short"):
            victim.short_descr = value
            return ""

        if field.startswith("long"):
            victim.long_descr = value + "\n\r"
            return ""

        if field.startswith("title"):
            if getattr(victim, "is_npc", False):
                return "Not on NPC's.\n\r"

            from mud.commands.character import set_title
            set_title(victim, value)
            return ""

        if field.startswith("spec"):
            if not getattr(victim, "is_npc", False):
                return "Not on PC's.\n\r"

            from mud.spec_funs import get_spec_fun

            fn = get_spec_fun(value)
            if fn is None:
                return "No such spec fun.\n\r"

            victim.spec_fun = value.lower()
            return ""

    if str_type.startswith("object"):
        from mud.world.obj_find import get_obj_world

        obj = get_obj_world(char, target_name)
        if obj is None:
            return "Nothing like that in heaven or earth.\n\r"

        if field.startswith("name"):
            obj.name = value
            return ""

        if field.startswith("short"):
            obj.short_descr = value
            return ""

        if field.startswith("long"):
            obj.description = value
            return ""

        if field.startswith("ed") or field.startswith("extended"):
            ext_parts = value.split(None, 1)
            if len(ext_parts) < 2:
                return "Syntax: oset <object> ed <keyword> <string>\n\r"

            keyword = ext_parts[0]
            description = ext_parts[1] + "\n\r"

            extra_descr = {"keyword": keyword, "description": description}
            if not hasattr(obj, "extra_descr") or obj.extra_descr is None:
                obj.extra_descr = []
            obj.extra_descr.append(extra_descr)
            return ""

    return do_string(char, "")
