"""
Immortal search/info commands - vnum, mfind, ofind, mwhere, owhere, sockets, memory, clone.

ROM Reference: src/act_wiz.c, src/db.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character
from mud.commands.imm_commands import get_trust, get_char_room

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
        return ("Syntax:\n"
                "  vnum obj <name>\n"
                "  vnum mob <name>\n"
                "  vnum skill <skill or spell>")
    
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
        mob_name = getattr(mob, "name", "").lower()
        short_desc = getattr(mob, "short_descr", "").lower()
        
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
        obj_name = getattr(obj, "name", "").lower()
        short_desc = getattr(obj, "short_descr", "").lower()
        
        if search_name in obj_name or search_name in short_desc:
            display_name = getattr(obj, "short_descr", obj_name)
            lines.append(f"[{vnum:5d}] {display_name}")
    
    if not lines:
        return "No objects by that name."
    
    return "\n".join(lines[:50])  # Limit output


def do_slookup(char: Character, args: str) -> str:
    """
    Find a skill or spell by name.
    
    ROM Reference: src/act_wiz.c do_slookup
    
    Usage: slookup <skill/spell name>
    """
    if not args or not args.strip():
        return "Lookup what skill?"
    
    search_name = args.strip().lower()
    
    from mud import registry
    
    lines = []
    for sn, skill in enumerate(getattr(registry, "skill_table", [])):
        skill_name = getattr(skill, "name", "").lower()
        if search_name in skill_name:
            lines.append(f"Sn: {sn:3d}  Skill/spell: '{skill.name}'")
    
    if not lines:
        return "No skill or spell by that name."
    
    return "\n".join(lines)


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
        obj_name = getattr(obj, "name", "").lower()
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
        ch_name = getattr(ch, "name", "").lower()
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
    """
    Show connected sockets/players.
    
    ROM Reference: src/act_wiz.c do_sockets (lines 4140-4182)
    
    Usage:
    - sockets          - Show all connections
    - sockets <name>   - Show specific player
    """
    from mud import registry
    
    filter_name = args.strip().lower() if args else ""
    
    lines = []
    count = 0
    
    for desc in getattr(registry, "descriptor_list", []):
        character = getattr(desc, "character", None)
        original = getattr(desc, "original", None)
        
        if character is None:
            continue
        
        char_name = getattr(character, "name", "none")
        
        # Apply name filter
        if filter_name:
            if filter_name not in char_name.lower():
                if original and filter_name not in getattr(original, "name", "").lower():
                    continue
        
        count += 1
        desc_num = getattr(desc, "descriptor", 0)
        connected = getattr(desc, "connected", 0)
        host = getattr(desc, "host", "unknown")
        
        display_name = getattr(original, "name", char_name) if original else char_name
        
        lines.append(f"[{desc_num:3d} {connected:2d}] {display_name}@{host}")
    
    if not lines:
        return "No one by that name is connected."
    
    lines.append(f"{count} user{'s' if count != 1 else ''}")
    return "\n".join(lines)


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
    
    ROM Reference: src/act_wiz.c do_clone (lines 2338-2458)
    
    Usage:
    - clone object <item>   - Clone an object
    - clone mobile <mob>    - Clone a mobile
    - clone <target>        - Clone object or mobile
    """
    if not args or not args.strip():
        return "Clone what?"
    
    parts = args.strip().split(None, 1)
    first_arg = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""
    
    from mud.commands.imm_commands import get_char_room
    from mud.world.obj_find import get_obj_here
    
    mob = None
    obj = None
    
    if first_arg == "object":
        obj = get_obj_here(char, rest)
        if obj is None:
            return "You don't see that here."
    elif first_arg in ("mobile", "character"):
        mob = get_char_room(char, rest)
        if mob is None:
            return "You don't see that here."
    else:
        # Try both
        mob = get_char_room(char, args.strip())
        obj = get_obj_here(char, args.strip())
        if mob is None and obj is None:
            return "You don't see that here."
    
    # Clone object
    if obj is not None:
        from mud.spawning.obj_spawner import spawn_obj
        
        proto = getattr(obj, "prototype", None)
        if proto is None:
            return "That object cannot be cloned."
        
        vnum = getattr(proto, "vnum", 0)
        clone = spawn_obj(vnum)
        
        if clone is None:
            return "Failed to clone object."
        
        # Copy properties
        for attr in ("short_descr", "description", "name", "level", "cost", "weight"):
            if hasattr(obj, attr):
                setattr(clone, attr, getattr(obj, attr))
        
        # Place in inventory
        carrying = getattr(char, "carrying", None)
        if carrying is None:
            char.carrying = []
        char.carrying.append(clone)
        clone.carried_by = char
        
        clone_name = getattr(clone, "short_descr", "something")
        return f"You clone {clone_name}."
    
    # Clone mobile
    if mob is not None:
        if not getattr(mob, "is_npc", False):
            return "You can only clone mobiles."
        
        from mud.spawning.mob_spawner import spawn_mob
        
        proto = getattr(mob, "prototype", None)
        if proto is None:
            return "That mobile cannot be cloned."
        
        vnum = getattr(proto, "vnum", 0)
        clone = spawn_mob(vnum)
        
        if clone is None:
            return "Failed to clone mobile."
        
        # Place in room
        room = getattr(char, "room", None)
        if room:
            clone.room = room
            people = getattr(room, "people", None)
            if people is None:
                room.people = []
            room.people.append(clone)
        
        clone_name = getattr(clone, "short_descr", "something")
        return f"You clone {clone_name}."
    
    return "Clone what?"


def do_stat(char: Character, args: str) -> str:
    """
    Show detailed statistics on a mob, object, or room.
    
    ROM Reference: src/act_wiz.c do_stat (lines 1059-1200)
    
    Usage:
    - stat mob <name>   - Stat a mobile
    - stat obj <name>   - Stat an object
    - stat room         - Stat current room
    - stat <target>     - Auto-detect type
    """
    if not args or not args.strip():
        # Default to room
        return do_stat_room(char)
    
    parts = args.strip().split(None, 1)
    stat_type = parts[0].lower()
    target = parts[1] if len(parts) > 1 else ""
    
    if stat_type == "room":
        return do_stat_room(char)
    
    if stat_type in ("mob", "char"):
        return do_stat_mob(char, target)
    
    if stat_type == "obj":
        return do_stat_obj(char, target)
    
    # Try to find target automatically
    from mud.commands.imm_commands import get_char_room
    from mud.world.obj_find import get_obj_here
    
    mob = get_char_room(char, args.strip())
    if mob:
        return do_stat_mob(char, args.strip())
    
    obj = get_obj_here(char, args.strip())
    if obj:
        return do_stat_obj(char, args.strip())
    
    return "Nothing by that name found."


def do_stat_room(char: Character) -> str:
    """Stat the current room."""
    room = getattr(char, "room", None)
    if not room:
        return "You're not in a room."
    
    lines = []
    lines.append(f"Name: [{getattr(room, 'name', 'Unknown')}]")
    lines.append(f"Vnum: [{getattr(room, 'vnum', 0)}]")
    
    area = getattr(room, "area", None)
    if area:
        lines.append(f"Area: [{getattr(area, 'name', 'Unknown')}]")
    
    lines.append(f"Sector: [{getattr(room, 'sector_type', 0)}]")
    lines.append(f"Flags: [{getattr(room, 'room_flags', 0)}]")
    
    # Exits
    exits = []
    for direction in ["north", "east", "south", "west", "up", "down"]:
        exit_data = getattr(room, direction, None)
        if exit_data:
            to_room = getattr(exit_data, "to_room", None)
            if to_room:
                to_vnum = getattr(to_room, "vnum", 0)
                exits.append(f"{direction[0].upper()}:{to_vnum}")
    
    if exits:
        lines.append(f"Exits: [{' '.join(exits)}]")
    
    # People
    people = getattr(room, "people", [])
    if people:
        names = [getattr(p, "name", "?") for p in people[:5]]
        lines.append(f"People: [{', '.join(names)}]")
    
    return "\n".join(lines)


def do_stat_mob(char: Character, name: str) -> str:
    """Stat a mobile."""
    from mud.commands.imm_commands import get_char_room
    
    if not name:
        return "Stat which mob?"
    
    victim = get_char_room(char, name)
    if victim is None:
        return "They aren't here."
    
    lines = []
    lines.append(f"Name: [{getattr(victim, 'name', 'Unknown')}]")
    
    is_npc = getattr(victim, "is_npc", False)
    if is_npc:
        proto = getattr(victim, "prototype", None)
        vnum = getattr(proto, "vnum", 0) if proto else 0
        lines.append(f"Vnum: [{vnum}]")
    else:
        lines.append("Type: [Player]")
    
    lines.append(f"Level: [{getattr(victim, 'level', 1)}]  Trust: [{get_trust(victim)}]")
    lines.append(f"Race: [{getattr(victim, 'race', 'human')}]  Class: [{getattr(victim, 'char_class', 'none')}]")
    lines.append(f"Sex: [{getattr(victim, 'sex', 0)}]  Room: [{getattr(getattr(victim, 'room', None), 'vnum', 0)}]")
    
    lines.append(f"Hp: [{getattr(victim, 'hit', 0)}/{getattr(victim, 'max_hit', 0)}]  "
                 f"Mana: [{getattr(victim, 'mana', 0)}/{getattr(victim, 'max_mana', 0)}]  "
                 f"Move: [{getattr(victim, 'move', 0)}/{getattr(victim, 'max_move', 0)}]")
    
    lines.append(f"Gold: [{getattr(victim, 'gold', 0)}]  Silver: [{getattr(victim, 'silver', 0)}]")
    lines.append(f"Hitroll: [{getattr(victim, 'hitroll', 0)}]  Damroll: [{getattr(victim, 'damroll', 0)}]")
    lines.append(f"Armor: [{getattr(victim, 'armor', [0,0,0,0])}]")
    
    return "\n".join(lines)


def do_stat_obj(char: Character, name: str) -> str:
    """Stat an object."""
    from mud.world.obj_find import get_obj_here
    
    if not name:
        return "Stat which object?"
    
    obj = get_obj_here(char, name)
    if obj is None:
        return "You don't see that here."
    
    lines = []
    lines.append(f"Name: [{getattr(obj, 'name', 'Unknown')}]")
    lines.append(f"Short: [{getattr(obj, 'short_descr', '')}]")
    
    proto = getattr(obj, "prototype", None)
    vnum = getattr(proto, "vnum", 0) if proto else 0
    lines.append(f"Vnum: [{vnum}]  Type: [{getattr(obj, 'item_type', 0)}]")
    
    lines.append(f"Level: [{getattr(obj, 'level', 0)}]  Wear: [{getattr(obj, 'wear_loc', -1)}]")
    lines.append(f"Weight: [{getattr(obj, 'weight', 0)}]  Cost: [{getattr(obj, 'cost', 0)}]")
    lines.append(f"Values: [{getattr(obj, 'value', [0,0,0,0,0])}]")
    lines.append(f"Extra flags: [{getattr(obj, 'extra_flags', 0)}]")
    lines.append(f"Wear flags: [{getattr(obj, 'wear_flags', 0)}]")
    
    return "\n".join(lines)
