"""
Immortal search/info commands - vnum, mfind, ofind, mwhere, owhere, sockets, memory, clone, stat.

ROM Reference: src/act_wiz.c, src/db.c
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.commands.imm_commands import (
    MAX_LEVEL,
    _is_room_owner,
    _room_is_private,
    find_location,
    get_char_world,
    get_trust,
)
from mud.handler import (
    act_bit_name,
    affect_bit_name,
    affect_loc_name,
    comm_bit_name,
    cont_bit_name,
    extra_bit_name,
    form_bit_name,
    imm_bit_name,
    item_name,
    off_bit_name,
    part_bit_name,
    weapon_bit_name,
    wear_bit_name,
)
from mud.models.character import Character
from mud.models.constants import (
    AC_BASH,
    AC_EXOTIC,
    AC_PIERCE,
    AC_SLASH,
    ItemType,
    WeaponType,
)

if TYPE_CHECKING:
    pass


def do_vnum(char: Character, args: str) -> str:
    """
    Find vnum of a mob, object, or skill by name.

    ROM Reference: src/act_wiz.c do_vnum (lines 1746-1790)

    Usage:
    - vnum obj <name>    - Find object vnums
    - vnum mob <name>    - Find mobile vnums
    - vnum skill <name>  - Find skill/spell
    """
    if not args or not args.strip():
        return "Syntax:\n  vnum obj <name>\n  vnum mob <name>\n  vnum skill <skill or spell>"

    parts = args.strip().split(None, 1)
    search_type = parts[0].lower()
    search_name = parts[1] if len(parts) > 1 else ""

    if search_type == "obj":
        return do_ofind(char, search_name)

    if search_type in ("mob", "char"):
        return do_mfind(char, search_name)

    if search_type in ("skill", "spell"):
        return do_slookup(char, search_name)

    # Default: search both
    mob_result = do_mfind(char, args)
    obj_result = do_ofind(char, args)

    results = []
    if mob_result and "No mobiles" not in mob_result:
        results.append(mob_result)
    if obj_result and "No objects" not in obj_result:
        results.append(obj_result)

    return "\n".join(results) if results else "Nothing found."


def do_mfind(char: Character, args: str) -> str:
    """
    Find mobile prototypes by name.

    ROM Reference: src/act_wiz.c do_mfind (lines 1792-1840)

    Usage: mfind <name>
    """
    if not args or not args.strip():
        return "Find whom?"

    search_name = args.strip().lower()

    from mud import registry

    lines = []
    for vnum, mob in sorted(registry.mob_prototypes.items()):
        mob_name = (getattr(mob, "name", None) or "").lower()
        short_desc = (getattr(mob, "short_descr", None) or "").lower()

        if search_name in mob_name or search_name in short_desc:
            display_name = getattr(mob, "short_descr", mob_name)
            lines.append(f"[{vnum:5d}] {display_name}")

    if not lines:
        return "No mobiles by that name."

    return "\n".join(lines[:50])  # Limit output


def do_ofind(char: Character, args: str) -> str:
    """
    Find object prototypes by name.

    ROM Reference: src/act_wiz.c do_ofind (lines 1842-1885)

    Usage: ofind <name>
    """
    if not args or not args.strip():
        return "Find what?"

    search_name = args.strip().lower()

    from mud import registry

    lines = []
    for vnum, obj in sorted(registry.obj_prototypes.items()):
        obj_name = (getattr(obj, "name", None) or "").lower()
        short_desc = (getattr(obj, "short_descr", None) or "").lower()

        if search_name in obj_name or search_name in short_desc:
            display_name = getattr(obj, "short_descr", obj_name)
            lines.append(f"[{vnum:5d}] {display_name}")

    if not lines:
        return "No objects by that name."

    return "\n".join(lines[:50])  # Limit output


def do_slookup(char: Character, args: str) -> str:
    # mirrors ROM src/act_wiz.c:3191-3229
    arg = args.strip()
    if not arg:
        return "Lookup which skill or spell?\n\r"

    from mud import registry

    skill_table = getattr(registry, "skill_table", [])

    if arg.lower() == "all":
        lines = []
        for sn, skill in enumerate(skill_table):
            skill_name = getattr(skill, "name", None)
            if skill_name is None:
                break
            slot = getattr(skill, "slot", 0)
            lines.append(f"Sn: {sn:3d}  Slot: {slot:3d}  Skill/spell: '{skill_name}'\n\r")
        return "".join(lines)

    # mirrors ROM: prefix match on skill names
    arg_lower = arg.lower()
    for sn, skill in enumerate(skill_table):
        skill_name = getattr(skill, "name", None)
        if skill_name is None:
            break
        if skill_name.lower().startswith(arg_lower):
            slot = getattr(skill, "slot", 0)
            return f"Sn: {sn:3d}  Slot: {slot:3d}  Skill/spell: '{skill_name}'\n\r"

    return "No such skill or spell.\n\r"


def do_owhere(char: Character, args: str) -> str:
    """
    Find objects in the world by name.

    ROM Reference: src/act_wiz.c do_owhere (lines 1886-1948)

    Usage: owhere <object name>
    """
    if not args or not args.strip():
        return "Find what?"

    search_name = args.strip().lower()

    from mud import registry

    lines = []
    count = 0
    max_found = 200

    for obj in getattr(registry, "object_list", []):
        obj_name = (getattr(obj, "name", None) or "").lower()
        if search_name not in obj_name:
            continue

        count += 1
        if count > max_found:
            break

        # Find the outermost container
        in_obj = obj
        while getattr(in_obj, "in_obj", None):
            in_obj = in_obj.in_obj

        obj_short = getattr(obj, "short_descr", "something")

        # Determine location
        carrier = getattr(in_obj, "carried_by", None)
        if carrier:
            carrier_room = getattr(carrier, "room", None)
            carrier_name = getattr(carrier, "name", "someone")
            if carrier_room:
                room_vnum = getattr(carrier_room, "vnum", 0)
                lines.append(f"{count:3d}) {obj_short} is carried by {carrier_name} [Room {room_vnum}]")
            else:
                lines.append(f"{count:3d}) {obj_short} is carried by {carrier_name}")
        elif getattr(in_obj, "in_room", None):
            room = in_obj.in_room
            room_name = getattr(room, "name", "somewhere")
            room_vnum = getattr(room, "vnum", 0)
            lines.append(f"{count:3d}) {obj_short} is in {room_name} [Room {room_vnum}]")
        else:
            lines.append(f"{count:3d}) {obj_short} is somewhere")

    if not lines:
        return "Nothing like that in heaven or earth."

    return "\n".join(lines)


def do_mwhere(char: Character, args: str) -> str:
    """
    Find mobiles/players in the world by name or show all players.

    ROM Reference: src/act_wiz.c do_mwhere (lines 1950-2020)

    Usage:
    - mwhere           - Show all connected players
    - mwhere <name>    - Find mobs/players by name
    """
    from mud import registry

    if not args or not args.strip():
        # Show all connected players
        lines = []
        count = 0

        for player in getattr(registry, "players", {}).values():
            room = getattr(player, "room", None)
            if room:
                count += 1
                player_name = getattr(player, "name", "someone")
                room_name = getattr(room, "name", "somewhere")
                room_vnum = getattr(room, "vnum", 0)
                lines.append(f"{count:3d}) {player_name} is in {room_name} [{room_vnum}]")

        if not lines:
            return "No players found."

        return "\n".join(lines)

    # Search by name
    search_name = args.strip().lower()
    lines = []
    count = 0

    for ch in getattr(registry, "char_list", []):
        ch_name = (getattr(ch, "name", None) or "").lower()
        room = getattr(ch, "room", None)

        if search_name in ch_name and room:
            count += 1
            is_npc = getattr(ch, "is_npc", False)

            if is_npc:
                proto = getattr(ch, "prototype", None)
                vnum = getattr(proto, "vnum", 0) if proto else 0
            else:
                vnum = 0

            ch_display = getattr(ch, "name", "someone")
            room_name = getattr(room, "name", "somewhere")
            room_vnum = getattr(room, "vnum", 0)

            lines.append(f"{count:3d}) [{vnum:5d}] {ch_display:<28s} [{room_vnum:5d}] {room_name}")

    if not lines:
        return "Nothing like that in heaven or earth."

    return "\n".join(lines[:100])  # Limit output


def do_sockets(char: Character, args: str) -> str:
    # mirrors ROM src/act_wiz.c:4140-4176
    filter_name = args.strip() if args else ""
    filter_lower = filter_name.lower() if filter_name else ""

    from mud import registry

    lines = []
    count = 0

    for desc in getattr(registry, "descriptor_list", []):
        character = getattr(desc, "character", None)
        if character is None:
            continue

        # mirrors ROM: can_see check and name filter
        if filter_lower:
            char_name = (getattr(character, "name", None) or "").lower()
            orig_name = ""
            original = getattr(desc, "original", None)
            if original:
                orig_name = (getattr(original, "name", None) or "").lower()
            if filter_lower not in char_name and (not orig_name or filter_lower not in orig_name):
                continue

        count += 1
        desc_num = getattr(desc, "descriptor", 0)
        connected = getattr(desc, "connected", 0)
        host = getattr(desc, "host", "unknown")
        original = getattr(desc, "original", None)
        display_name = getattr(original, "name", None) or getattr(character, "name", "none")

        lines.append(f"[{desc_num:3d} {connected:2d}] {display_name}@{host}\n\r")

    if count == 0:
        return "No one by that name is connected.\n\r"

    lines.append(f"{count} user{'s' if count != 1 else ''}\n\r")
    return "".join(lines)


def do_memory(char: Character, args: str) -> str:
    """
    Show memory usage statistics.

    ROM Reference: src/db.c do_memory (lines 3289-3330)

    Usage: memory
    """
    from mud import registry

    lines = []

    # Count various entities
    num_areas = len(getattr(registry, "areas", []))
    num_rooms = len(getattr(registry, "rooms", {}))
    num_mobs = len(getattr(registry, "mob_prototypes", {}))
    num_objs = len(getattr(registry, "obj_prototypes", {}))
    num_helps = len(getattr(registry, "helps", {}))
    num_socials = len(getattr(registry, "social_registry", {}).socials if hasattr(registry, "social_registry") else {})
    num_chars = len(getattr(registry, "char_list", []))

    lines.append(f"Areas   {num_areas:5d}")
    lines.append(f"Rooms   {num_rooms:5d}")
    lines.append(f"Mobs    {num_mobs:5d}")
    lines.append(f"(in use){num_chars:5d}")
    lines.append(f"Objs    {num_objs:5d}")
    lines.append(f"Helps   {num_helps:5d}")
    lines.append(f"Socials {num_socials:5d}")

    return "\n".join(lines)


def do_clone(char: Character, args: str) -> str:
    """
    Clone a mobile or object.

    ROM Reference: src/act_wiz.c do_clone (lines 2338-2455)

    Usage:
    - clone object <item>   - Clone an object
    - clone mobile <mob>    - Clone a mobile
    - clone <target>        - Clone object or mobile
    """
    # mirrors ROM src/act_wiz.c:2349
    if not args or not args.strip():
        return "Clone what?\n\r"

    parts = args.strip().split(None, 1)
    first_arg = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    from mud.commands.imm_commands import get_char_room
    from mud.world.obj_find import get_obj_here

    mob = None
    obj = None

    # mirrors ROM src/act_wiz.c:2353-2383
    if first_arg == "object":
        obj = get_obj_here(char, rest)
        if obj is None:
            return "You don't see that here.\n\r"
    elif first_arg in ("mobile", "character"):
        mob = get_char_room(char, rest)
        if mob is None:
            return "You don't see that here.\n\r"
    else:
        mob = get_char_room(char, args.strip())
        obj = get_obj_here(char, args.strip())
        if mob is None and obj is None:
            return "You don't see that here.\n\r"

    # Clone object — mirrors ROM src/act_wiz.c:2386-2409
    if obj is not None:
        from mud.spawning.obj_spawner import spawn_obj

        proto = getattr(obj, "prototype", None)
        if proto is None:
            proto = obj

        vnum = getattr(proto, "vnum", 0)
        clone = spawn_obj(vnum)

        if clone is None:
            return "Your powers are not great enough for such a task.\n\r"

        for attr in ("short_descr", "description", "name", "level", "cost", "weight"):
            if hasattr(obj, attr):
                setattr(clone, attr, getattr(obj, attr))

        # mirrors ROM src/act_wiz.c:2399-2402
        carrier = getattr(obj, "carried_by", None)
        if carrier is not None:
            carrying = getattr(char, "inventory", None)
            if carrying is None:
                char.inventory = []
            char.inventory.append(clone)
            clone.carried_by = char
        else:
            room = getattr(char, "room", None)
            if room:
                contents = getattr(room, "contents", None)
                if contents is None:
                    room.contents = []
                room.contents.append(clone)
                clone.in_room = room

        from mud.wiznet import wiznet, WiznetFlag
        wiznet("$N clones $p.", char, clone, WiznetFlag.WIZ_LOAD, WiznetFlag.WIZ_SECURE, get_trust(char))
        return "You clone $p.\n\r"

    # Clone mobile — mirrors ROM src/act_wiz.c:2411-2454
    if mob is not None:
        if not getattr(mob, "is_npc", False):
            return "You can only clone mobiles.\n\r"

        # mirrors ROM src/act_wiz.c:2423-2432 — trust check
        mob_level = getattr(mob, "level", 0)
        from mud.models.constants import LEVEL_AVATAR, LEVEL_DEMI, LEVEL_IMMORTAL, LEVEL_GOD
        if (mob_level > 20 and get_trust(char) < LEVEL_GOD) or \
           (mob_level > 10 and get_trust(char) < LEVEL_IMMORTAL) or \
           (mob_level > 5 and get_trust(char) < LEVEL_DEMI) or \
           (mob_level > 0 and get_trust(char) < LEVEL_AVATAR):
            return "Your powers are not great enough for such a task.\n\r"

        from mud.spawning.mob_spawner import spawn_mob

        proto = getattr(mob, "prototype", None)
        if proto is None:
            proto = mob

        vnum = getattr(proto, "vnum", 0)
        clone = spawn_mob(vnum)

        if clone is None:
            return "Your powers are not great enough for such a task.\n\r"

        room = getattr(char, "room", None)
        if room:
            clone.room = room
            people = getattr(room, "people", None)
            if people is None:
                room.people = []
            room.people.append(clone)

        from mud.wiznet import wiznet, WiznetFlag
        clone_short = getattr(clone, "short_descr", "something")
        wiznet(f"$N clones {clone_short}.", char, None, WiznetFlag.WIZ_LOAD, WiznetFlag.WIZ_SECURE, get_trust(char))
        return "You clone $N.\n\r"

    return "Clone what?\n\r"


def do_stat(char: Character, args: str) -> str:
    """
    Show detailed statistics on a mob, object, or room.

    ROM Reference: src/act_wiz.c:1059-1120

    Dispatches to do_rstat, do_ostat, or do_mstat based on arg prefix,
    or auto-detects by searching world for matching object/character/room.
    """
    arg = args.strip()
    if not arg:
        return "Syntax:\n\r  stat <name>\n\r  stat obj <name>\n\r  stat mob <name>\n\r  stat room <number>\n\r"

    parts = arg.split(None, 1)
    keyword = parts[0].lower()
    remainder = parts[1] if len(parts) > 1 else ""

    if keyword == "room":
        return do_rstat(char, remainder)

    if keyword == "obj":
        return do_ostat(char, remainder)

    if keyword in ("char", "mob"):
        return do_mstat(char, remainder)

    # mirroring ROM src/act_wiz.c:1098-1118 — auto-detect
    from mud.world.obj_find import get_obj_world

    obj = get_obj_world(char, arg)
    if obj is not None:
        return do_ostat(char, arg)

    victim = get_char_world(char, arg)
    if victim is not None:
        return do_mstat(char, arg)

    location = find_location(char, arg)
    if location is not None:
        return do_rstat(char, arg)

    return "Nothing by that name found anywhere.\n\r"


def do_rstat(char: Character, args: str) -> str:
    """
    Show detailed room statistics.

    ROM Reference: src/act_wiz.c:1122-1215

    If no arg, stats current room. Otherwise finds room by vnum or character name.
    Private rooms require ownership or IMPLEMENTOR trust.
    """
    arg = args.strip()

    if not arg:
        location = getattr(char, "room", None)
    else:
        location = find_location(char, arg)

    if location is None:
        return "No such location.\n\r"

    if (
        not _is_room_owner(char, location)
        and getattr(char, "room", None) is not location
        and _room_is_private(location)
        and get_trust(char) < MAX_LEVEL
    ):
        return "That room is private right now.\n\r"

    buf = ""
    area = getattr(location, "area", None)
    area_name = getattr(area, "name", "") if area else ""
    buf += f"Name: '{location.name or ''}'\n\rArea: '{area_name}'\n\r"
    buf += f"Vnum: {location.vnum}  Sector: {int(getattr(location, 'sector_type', 0))}  Light: {int(getattr(location, 'light', 0))}  Healing: {int(getattr(location, 'heal_rate', 100))}  Mana: {int(getattr(location, 'mana_rate', 100))}\n\r"
    buf += f"Room flags: {int(getattr(location, 'room_flags', 0))}.\n\rDescription:\n\r{location.description or ''}"
    if not (location.description or "").endswith("\n\r"):
        buf += "\n\r"

    extra_descr = getattr(location, "extra_descr", None)
    if extra_descr:
        buf += "Extra description keywords: '"
        keywords = []
        for ed in extra_descr:
            kw = (
                getattr(ed, "keyword", "")
                if hasattr(ed, "keyword")
                else ed.get("keyword", "")
                if isinstance(ed, dict)
                else ""
            )
            if kw:
                keywords.append(kw)
        buf += " ".join(keywords)
        buf += "'.\n\r"

    buf += "Characters:"
    for rch in getattr(location, "people", []):
        from mud.world.vision import can_see_character

        if can_see_character(char, rch):
            name = getattr(rch, "name", "?")
            buf += f" {name.split()[0] if name else '?'}"
    buf += ".\n\rObjects:  "
    for obj in getattr(location, "contents", []):
        name = getattr(obj, "name", "?")
        buf += f" {name.split()[0] if name else '?'}"
    buf += ".\n\r"

    for door in range(6):
        exits = getattr(location, "exits", [])
        exit_obj = exits[door] if exits and door < len(exits) else None
        if exit_obj is not None:
            to_room = getattr(exit_obj, "to_room", None)
            to_vnum = getattr(to_room, "vnum", -1) if to_room else -1
            key = getattr(exit_obj, "key", 0) if hasattr(exit_obj, "key") else 0
            exit_info = getattr(exit_obj, "exit_info", 0)
            keyword = getattr(exit_obj, "keyword", "")
            desc = getattr(exit_obj, "description", "") or "(none).\n\r"
            buf += f"Door: {door}.  To: {to_vnum}.  Key: {key}.  Exit flags: {exit_info}.\n\rKeyword: '{keyword}'.  Description: {desc}"

    return buf


def do_ostat(char: Character, args: str) -> str:
    """
    Show detailed object statistics.

    ROM Reference: src/act_wiz.c:1219-1538

    Uses get_obj_world to find object by name anywhere.
    """
    from mud.skills.handlers import _skill_name_from_value
    from mud.world.obj_find import get_obj_world

    arg = args.strip()
    if not arg:
        return "Stat what?\n\r"

    obj = get_obj_world(char, arg)
    if obj is None:
        return "Nothing like that in hell, earth, or heaven.\n\r"

    buf = ""
    name = getattr(obj, "name", "")
    buf += f"Name(s): {name}\n\r"

    proto = getattr(obj, "prototype", None) if hasattr(obj, "prototype") else getattr(obj, "pIndexData", None)
    obj_vnum = getattr(proto, "vnum", 0) if proto else 0
    new_format = getattr(proto, "new_format", False) if proto else False
    reset_num = getattr(proto, "reset_num", 0) if proto else 0
    item_type_val = int(getattr(obj, "item_type", 0))
    buf += f"Vnum: {obj_vnum}  Format: {'new' if new_format else 'old'}  Type: {item_name(item_type_val)}  Resets: {reset_num}\n\r"

    short_descr = getattr(obj, "short_descr", "")
    description = getattr(obj, "description", "")
    buf += f"Short description: {short_descr}\n\rLong description: {description}\n\r"

    wear_flags_val = int(getattr(obj, "wear_flags", 0))
    extra_flags_val = int(getattr(obj, "extra_flags", 0))
    buf += f"Wear bits: {wear_bit_name(wear_flags_val)}\n\rExtra bits: {extra_bit_name(extra_flags_val)}\n\r"

    obj_number = 1
    obj_weight = int(getattr(obj, "weight", 0))
    true_weight = obj_weight
    buf += f"Number: 1/{obj_number}  Weight: {obj_weight}/{obj_weight}/{true_weight} (10th pounds)\n\r"

    obj_level = int(getattr(obj, "level", 0))
    obj_cost = int(getattr(obj, "cost", 0))
    obj_condition = int(getattr(obj, "condition", 0))
    obj_timer = int(getattr(obj, "timer", 0))
    buf += f"Level: {obj_level}  Cost: {obj_cost}  Condition: {obj_condition}  Timer: {obj_timer}\n\r"

    obj_in_room = getattr(obj, "in_room", None)
    in_room_vnum = getattr(obj_in_room, "vnum", 0) if obj_in_room else 0
    obj_in_obj = getattr(obj, "in_obj", None)
    in_obj_name = getattr(obj_in_obj, "short_descr", "(none)") if obj_in_obj else "(none)"
    carried_by = getattr(obj, "carried_by", None)
    carried_name = getattr(carried_by, "name", "someone") if carried_by else "(none)"
    if carried_by:
        from mud.world.vision import can_see_character

        if not can_see_character(char, carried_by):
            carried_name = "someone"
    wear_loc = int(getattr(obj, "wear_loc", -1))
    buf += f"In room: {in_room_vnum}  In object: {in_obj_name}  Carried by: {carried_name}  Wear_loc: {wear_loc}\n\r"

    values = getattr(obj, "value", [0, 0, 0, 0, 0])
    if not isinstance(values, list | tuple):
        values = [0, 0, 0, 0, 0]
    values = list(values) + [0] * (5 - len(values))
    buf += f"Values: {values[0]} {values[1]} {values[2]} {values[3]} {values[4]}\n\r"

    it = (
        ItemType(item_type_val)
        if isinstance(item_type_val, int) and item_type_val in [e.value for e in ItemType]
        else None
    )

    if it == ItemType.SCROLL or it == ItemType.POTION or it == ItemType.PILL:
        buf += f"Level {values[0]} spells of:"
        for idx in (1, 2, 3, 4):
            sn = values[idx]
            skill_name = _skill_name_from_value(sn)
            if skill_name:
                buf += f" '{skill_name}'"
        buf += ".\n\r"

    elif it == ItemType.WAND or it == ItemType.STAFF:
        buf += f"Has {values[1]}({values[2]}) charges of level {values[0]}"
        sn = values[3]
        skill_name = _skill_name_from_value(sn)
        if skill_name:
            buf += f" '{skill_name}'"
        buf += ".\n\r"

    elif it == ItemType.DRINK_CON:
        from mud.models.constants import LIQUID_TABLE

        liq_idx = values[2]
        if 0 <= liq_idx < len(LIQUID_TABLE):
            liq = LIQUID_TABLE[liq_idx]
            buf += f"It holds {liq.color}-{liq.name}.\n\r"

    elif it == ItemType.WEAPON:
        weapon_names = {
            WeaponType.EXOTIC: "exotic",
            WeaponType.SWORD: "sword",
            WeaponType.DAGGER: "dagger",
            WeaponType.SPEAR: "spear/staff",
            WeaponType.MACE: "mace/club",
            WeaponType.AXE: "axe",
            WeaponType.FLAIL: "flail",
            WeaponType.WHIP: "whip",
            WeaponType.POLEARM: "polearm",
        }
        buf += f"Weapon type is {weapon_names.get(WeaponType(values[0]), 'unknown')}\n\r"
        if new_format:
            avg = (1 + values[2]) * values[1] // 2
            buf += f"Damage is {values[1]}d{values[2]} (average {avg})\n\r"
        else:
            avg = (values[1] + values[2]) // 2
            buf += f"Damage is {values[1]} to {values[2]} (average {avg})\n\r"

        from mud.models.constants import ATTACK_TABLE

        attack_name = "undefined"
        if 0 < values[3] < len(ATTACK_TABLE):
            noun = ATTACK_TABLE[values[3]].noun
            if noun:
                attack_name = noun
        buf += f"Damage noun is {attack_name}.\n\r"

        if values[4]:
            buf += f"Weapons flags: {weapon_bit_name(values[4])}\n\r"

    elif it == ItemType.ARMOR:
        buf += f"Armor class is {values[0]} pierce, {values[1]} bash, {values[2]} slash, and {values[3]} vs. magic\n\r"

    elif it == ItemType.CONTAINER:
        buf += f"Capacity: {values[0]}#  Maximum weight: {values[3]}#  flags: {cont_bit_name(values[1])}\n\r"
        if values[4] != 100:
            buf += f"Weight multiplier: {values[4]}%\n\r"

    obj_extra_descr = getattr(obj, "extra_descr", None)
    proto_extra_descr = getattr(proto, "extra_descr", None) if proto else None
    if obj_extra_descr or proto_extra_descr:
        buf += "Extra description keywords: '"
        for ed in obj_extra_descr or []:
            kw = (
                getattr(ed, "keyword", "")
                if hasattr(ed, "keyword")
                else ed.get("keyword", "")
                if isinstance(ed, dict)
                else ""
            )
            if kw:
                buf += f"{kw} "
        for ed in proto_extra_descr or []:
            kw = (
                getattr(ed, "keyword", "")
                if hasattr(ed, "keyword")
                else ed.get("keyword", "")
                if isinstance(ed, dict)
                else ""
            )
            if kw:
                buf += f"{kw} "
        buf = buf.rstrip() + "'\n\r"

    obj_affected = getattr(obj, "affected", None)
    if obj_affected:
        for paf in obj_affected:
            paf_location = getattr(paf, "location", 0)
            paf_modifier = getattr(paf, "modifier", 0)
            paf_level = getattr(paf, "level", 0)
            paf_duration = getattr(paf, "duration", -1)
            paf_bitvector = getattr(paf, "bitvector", 0)
            paf_where = getattr(paf, "where", 0)

            buf += f"Affects {affect_loc_name(paf_location)} by {paf_modifier}, level {paf_level}"
            if paf_duration > -1:
                buf += f", {paf_duration} hours.\n\r"
            else:
                buf += ".\n\r"

            if paf_bitvector:
                _TO_AFFECTS = 0
                _TO_WEAPON = -1
                _TO_OBJECT = 1
                _TO_IMMUNE = 2
                _TO_RESIST = 3
                _TO_VULN = 4
                if paf_where == _TO_AFFECTS:
                    buf += f"Adds {affect_bit_name(paf_bitvector)} affect.\n"
                elif paf_where == _TO_WEAPON:
                    buf += f"Adds {weapon_bit_name(paf_bitvector)} weapon flags.\n"
                elif paf_where == _TO_OBJECT:
                    buf += f"Adds {extra_bit_name(paf_bitvector)} object flag.\n"
                elif paf_where == _TO_IMMUNE:
                    buf += f"Adds immunity to {imm_bit_name(paf_bitvector)}.\n"
                elif paf_where == _TO_RESIST:
                    buf += f"Adds resistance to {imm_bit_name(paf_bitvector)}.\n\r"
                elif paf_where == _TO_VULN:
                    buf += f"Adds vulnerability to {imm_bit_name(paf_bitvector)}.\n\r"
                else:
                    buf += f"Unknown bit {paf_where}: {paf_bitvector}\n\r"

    if not getattr(obj, "enchanted", False):
        proto_affected = getattr(proto, "affected", None) if proto else None
        if proto_affected:
            for paf in proto_affected:
                paf_location = getattr(paf, "location", 0)
                paf_modifier = getattr(paf, "modifier", 0)
                paf_level = getattr(paf, "level", 0)
                paf_bitvector = getattr(paf, "bitvector", 0)
                paf_where = getattr(paf, "where", 0)

                buf += f"Affects {affect_loc_name(paf_location)} by {paf_modifier}, level {paf_level}.\n\r"

                if paf_bitvector:
                    _TO_AFFECTS = 0
                    _TO_WEAPON = -1
                    _TO_OBJECT = 1
                    _TO_IMMUNE = 2
                    _TO_RESIST = 3
                    _TO_VULN = 4
                    if paf_where == _TO_AFFECTS:
                        buf += f"Adds {affect_bit_name(paf_bitvector)} affect.\n"
                    elif paf_where == _TO_OBJECT:
                        buf += f"Adds {extra_bit_name(paf_bitvector)} object flag.\n"
                    elif paf_where == _TO_IMMUNE:
                        buf += f"Adds immunity to {imm_bit_name(paf_bitvector)}.\n"
                    elif paf_where == _TO_RESIST:
                        buf += f"Adds resistance to {imm_bit_name(paf_bitvector)}.\n\r"
                    elif paf_where == _TO_VULN:
                        buf += f"Adds vulnerability to {imm_bit_name(paf_bitvector)}.\n\r"
                    else:
                        buf += f"Unknown bit {paf_where}: {paf_bitvector}\n\r"

    return buf


def do_mstat(char: Character, args: str) -> str:
    """
    Show detailed mobile/character statistics.

    ROM Reference: src/act_wiz.c:1543-1742
    """
    from mud.handler import sex_name
    from mud.models.classes import CLASS_TABLE

    arg = args.strip()
    if not arg:
        return "Stat whom?\n\r"

    victim = get_char_world(char, arg)
    if victim is None:
        return "They aren't here.\n\r"

    buf = ""
    buf += f"Name: {getattr(victim, 'name', '')}\n\r"

    is_npc = getattr(victim, "is_npc", False)
    if is_npc:
        proto = (
            getattr(victim, "prototype", None) if hasattr(victim, "prototype") else getattr(victim, "pIndexData", None)
        )
        vnum = getattr(proto, "vnum", 0) if proto else 0
        new_format = getattr(proto, "new_format", False) if proto else False
        fmt = "new" if new_format else "old"
    else:
        vnum = 0
        fmt = "pc"

    race_val = getattr(victim, "race", 0)
    if isinstance(race_val, str):
        race_name = race_val.lower()
    elif isinstance(race_val, int):
        from mud.models.races import RACE_TABLE

        if 0 <= race_val < len(RACE_TABLE):
            race_name = getattr(RACE_TABLE[race_val], "name", str(race_val)).lower()
        else:
            race_name = str(race_val)
    else:
        race_name = str(race_val).lower()

    group_val = int(getattr(victim, "group", 0)) if is_npc else 0
    sex_val = int(getattr(victim, "sex", 0))
    room_vnum = getattr(getattr(victim, "room", None), "vnum", 0) if getattr(victim, "room", None) else 0

    buf += f"Vnum: {vnum}  Format: {fmt}  Race: {race_name}  Group: {group_val}  Sex: {sex_name(sex_val)}  Room: {room_vnum}\n\r"

    if is_npc:
        proto2 = (
            getattr(victim, "prototype", None) if hasattr(victim, "prototype") else getattr(victim, "pIndexData", None)
        )
        count = getattr(proto2, "count", 0) if proto2 else 0
        killed = getattr(proto2, "killed", 0) if proto2 else 0
        buf += f"Count: {count}  Killed: {killed}\n\r"

    perm_stat = getattr(victim, "perm_stat", [0] * 5)
    if isinstance(perm_stat, dict):
        perm_stat = [perm_stat.get(i, 0) for i in range(5)]

    from mud.models.constants import Stat

    stat_str = int(perm_stat[Stat.STR]) if Stat.STR < len(perm_stat) else 0
    cur_str = victim.get_curr_stat(Stat.STR) if hasattr(victim, "get_curr_stat") else stat_str
    stat_int = int(perm_stat[Stat.INT]) if Stat.INT < len(perm_stat) else 0
    cur_int = victim.get_curr_stat(Stat.INT) if hasattr(victim, "get_curr_stat") else stat_int
    stat_wis = int(perm_stat[Stat.WIS]) if Stat.WIS < len(perm_stat) else 0
    cur_wis = victim.get_curr_stat(Stat.WIS) if hasattr(victim, "get_curr_stat") else stat_wis
    stat_dex = int(perm_stat[Stat.DEX]) if Stat.DEX < len(perm_stat) else 0
    cur_dex = victim.get_curr_stat(Stat.DEX) if hasattr(victim, "get_curr_stat") else stat_dex
    stat_con = int(perm_stat[Stat.CON]) if Stat.CON < len(perm_stat) else 0
    cur_con = victim.get_curr_stat(Stat.CON) if hasattr(victim, "get_curr_stat") else stat_con

    if cur_str is None:
        cur_str = stat_str
    if cur_int is None:
        cur_int = stat_int
    if cur_wis is None:
        cur_wis = stat_wis
    if cur_dex is None:
        cur_dex = stat_dex
    if cur_con is None:
        cur_con = stat_con

    buf += f"Str: {stat_str}({cur_str})  Int: {stat_int}({cur_int})  Wis: {stat_wis}({cur_wis})  Dex: {stat_dex}({cur_dex})  Con: {stat_con}({cur_con})\n\r"

    hit = int(getattr(victim, "hit", 0))
    max_hit = int(getattr(victim, "max_hit", 0))
    mana = int(getattr(victim, "mana", 0))
    max_mana = int(getattr(victim, "max_mana", 0))
    move = int(getattr(victim, "move", 0))
    max_move = int(getattr(victim, "max_move", 0))
    practice = 0 if is_npc else int(getattr(victim, "practice", 0))
    buf += f"Hp: {hit}/{max_hit}  Mana: {mana}/{max_mana}  Move: {move}/{max_move}  Practices: {practice}\n\r"

    level = int(getattr(victim, "level", 1))
    if is_npc:
        class_name = "mobile"
    else:
        ch_class = getattr(victim, "ch_class", 0)
        if isinstance(ch_class, str):
            class_name = ch_class.lower()
        elif isinstance(ch_class, int) and 0 <= ch_class < len(CLASS_TABLE):
            class_name = CLASS_TABLE[ch_class].name.lower()
        else:
            class_name = str(ch_class).lower()

    alignment = int(getattr(victim, "alignment", 0))
    gold = int(getattr(victim, "gold", 0))
    silver = int(getattr(victim, "silver", 0))
    exp = int(getattr(victim, "exp", 0))
    buf += f"Lv: {level}  Class: {class_name}  Align: {alignment}  Gold: {gold}  Silver: {silver}  Exp: {exp}\n\r"

    # ROM src/act_wiz.c:1612-1613 prints GET_AC for each AC type (dex_app applied if IS_AWAKE).
    from mud.math.stat_apps import get_ac

    ac_pierce = get_ac(victim, AC_PIERCE)
    ac_bash = get_ac(victim, AC_BASH)
    ac_slash = get_ac(victim, AC_SLASH)
    ac_exotic = get_ac(victim, AC_EXOTIC)
    buf += f"Armor: pierce: {ac_pierce}  bash: {ac_bash}  slash: {ac_slash}  magic: {ac_exotic}\n\r"

    hitroll = int(getattr(victim, "hitroll", 0))
    damroll = int(getattr(victim, "damroll", 0))
    saving_throw = int(getattr(victim, "saving_throw", 0))
    size_val = int(getattr(victim, "size", 0))
    pos_val = int(getattr(victim, "position", 8))
    wimpy = int(getattr(victim, "wimpy", 0))

    from mud.handler import position_name, size_name

    buf += f"Hit: {hitroll}  Dam: {damroll}  Saves: {saving_throw}  Size: {size_name(size_val)}  Position: {position_name(pos_val)}  Wimpy: {wimpy}\n\r"

    if is_npc:
        proto3 = (
            getattr(victim, "prototype", None) if hasattr(victim, "prototype") else getattr(victim, "pIndexData", None)
        )
        if proto3 and getattr(proto3, "new_format", False):
            damage = getattr(victim, "damage", (0, 0))
            if isinstance(damage, list | tuple) and len(damage) >= 2:
                dice_num = damage[0]
                dice_type = damage[1]
            else:
                dice_num = dice_type = 0
            dam_type = int(getattr(victim, "dam_type", 0))
            from mud.models.constants import ATTACK_TABLE

            dam_noun = "hit"
            if 0 < dam_type < len(ATTACK_TABLE):
                noun = ATTACK_TABLE[dam_type].noun
                if noun:
                    dam_noun = noun
            buf += f"Damage: {dice_num}d{dice_type}  Message:  {dam_noun}\n\r"

    fighting = getattr(victim, "fighting", None)
    fighting_name = getattr(fighting, "name", "(none)") if fighting else "(none)"
    buf += f"Fighting: {fighting_name}\n\r"

    if not is_npc:
        pcdata = getattr(victim, "pcdata", None)
        if pcdata is not None:
            condition = getattr(pcdata, "condition", None)
            if condition is not None:
                thirst = int(condition[0]) if len(condition) > 0 else 0
                hunger = int(condition[1]) if len(condition) > 1 else 0
                full = int(condition[2]) if len(condition) > 2 else 0
                drunk = int(condition[3]) if len(condition) > 3 else 0
                buf += f"Thirst: {thirst}  Hunger: {hunger}  Full: {full}  Drunk: {drunk}\n\r"

    carry_number = int(getattr(victim, "carry_number", 0))
    carry_weight = int(getattr(victim, "carry_weight", 0))
    buf += f"Carry number: {carry_number}  Carry weight: {carry_weight // 10}\n\r"

    if not is_npc:
        age = 17
        played = 0
        last_level = 0
        timer = int(getattr(victim, "timer", 0))
        buf += f"Age: {age}  Played: {played}  Last Level: {last_level}  Timer: {timer}\n\r"

    act_flags_val = int(getattr(victim, "act", 0))
    buf += f"Act: {act_bit_name(act_flags_val)}\n\r"

    comm_flags = int(getattr(victim, "comm", 0))
    if comm_flags:
        buf += f"Comm: {comm_bit_name(comm_flags)}\n\r"

    if is_npc:
        off_flags = int(getattr(victim, "off_flags", 0))
        if off_flags:
            buf += f"Offense: {off_bit_name(off_flags)}\n\r"

    imm_flags = int(getattr(victim, "imm_flags", 0))
    if imm_flags:
        buf += f"Immune: {imm_bit_name(imm_flags)}\n\r"

    res_flags = int(getattr(victim, "res_flags", 0))
    if res_flags:
        buf += f"Resist: {imm_bit_name(res_flags)}\n\r"

    vuln_flags = int(getattr(victim, "vuln_flags", 0))
    if vuln_flags:
        buf += f"Vulnerable: {imm_bit_name(vuln_flags)}\n\r"

    form_val = int(getattr(victim, "form", 0))
    parts_val = int(getattr(victim, "parts", 0))
    buf += f"Form: {form_bit_name(form_val)}\n\rParts: {part_bit_name(parts_val)}\n\r"

    affected_by = int(getattr(victim, "affected_by", 0))
    if affected_by:
        buf += f"Affected by {affect_bit_name(affected_by)}\n\r"

    master = getattr(victim, "master", None)
    leader = getattr(victim, "leader", None)
    pet = getattr(victim, "pet", None)
    master_name = getattr(master, "name", "(none)") if master else "(none)"
    leader_name = getattr(leader, "name", "(none)") if leader else "(none)"
    pet_name = getattr(pet, "name", "(none)") if pet else "(none)"
    buf += f"Master: {master_name}  Leader: {leader_name}  Pet: {pet_name}\n\r"

    if not is_npc:
        pcdata2 = getattr(victim, "pcdata", None)
        if pcdata2 is not None:
            security = int(getattr(pcdata2, "security", 0))
            buf += f"Security: {security}.\n\r"

    short_descr = getattr(victim, "short_descr", "")
    long_descr = getattr(victim, "long_descr", "")
    long_display = long_descr if long_descr else "(none)\n\r"
    buf += f"Short description: {short_descr}\n\rLong  description: {long_display}"

    if is_npc:
        spec_fun = getattr(victim, "spec_fun", None)
        if spec_fun:
            sp_name = getattr(spec_fun, "__name__", str(spec_fun)) if callable(spec_fun) else str(spec_fun)
            if sp_name:
                buf += f"Mobile has special procedure {sp_name}.\n\r"

    victim_affected = getattr(victim, "affected", None)
    if victim_affected:
        for paf in victim_affected:
            paf_type = getattr(paf, "type", 0)
            paf_location = getattr(paf, "location", 0)
            paf_modifier = getattr(paf, "modifier", 0)
            paf_duration = getattr(paf, "duration", 0)
            paf_bitvector = getattr(paf, "bitvector", 0)
            paf_level = getattr(paf, "level", 0)

            type_name = str(paf_type) if isinstance(paf_type, str) else f"sn#{paf_type}"
            buf += f"Spell: '{type_name}' modifies {affect_loc_name(paf_location)} by {paf_modifier} for {paf_duration} hours with bits {affect_bit_name(paf_bitvector)}, level {paf_level}.\n\r"

    return buf
