"""
Immortal wizard commands - load, purge, restore, slay.

ROM Reference: src/act_wiz.c, src/fight.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character
from mud.commands.imm_commands import get_trust, get_char_world, get_char_room, MAX_LEVEL

if TYPE_CHECKING:
    pass


def do_load(char: Character, args: str) -> str:
    """
    Load a mobile or object into the game.
    
    ROM Reference: src/act_wiz.c do_load (lines 2459-2486)
    
    Usage:
    - load mob <vnum>          - Load a mobile
    - load obj <vnum> [level]  - Load an object
    """
    # mirrors ROM src/act_wiz.c:2465-2470
    if not args or not args.strip():
        return ("Syntax:\n\r"
                "  load mob <vnum>\n\r"
                "  load obj <vnum> <level>\n\r")

    parts = args.strip().split()
    load_type = parts[0].lower()

    if load_type in ("mob", "char"):
        if len(parts) < 2:
            return "Syntax: load mob <vnum>.\n\r"
        return do_mload(char, parts[1])

    if load_type == "obj":
        if len(parts) < 2:
            return "Syntax: load obj <vnum> <level>.\n\r"
        level_arg = parts[2] if len(parts) > 2 else None
        return do_oload(char, parts[1], level_arg)

    # mirrors ROM src/act_wiz.c:2484-2486
    return do_load(char, "")


def do_mload(char: Character, vnum_arg: str) -> str:
    """
    Load a mobile by vnum.
    
    ROM Reference: src/act_wiz.c do_mload (lines 2489-2517)
    """
    # mirrors ROM src/act_wiz.c:2498-2501
    if not vnum_arg or not vnum_arg.isdigit():
        return "Syntax: load mob <vnum>.\n\r"

    vnum = int(vnum_arg)

    from mud import registry

    # mirrors ROM src/act_wiz.c:2504-2507
    mob_index = getattr(registry, "mob_prototypes", {}).get(vnum)
    if mob_index is None:
        return "No mob has that vnum.\n\r"

    # Create the mobile
    from mud.spawning.mob_spawner import spawn_mob
    victim = spawn_mob(vnum)

    if victim is None:
        return "No mob has that vnum.\n\r"

    # Place in room
    room = getattr(char, "room", None)
    if room:
        victim.room = room
        people = getattr(room, "people", None)
        if people is None:
            room.people = []
        room.people.append(victim)

    # mirrors ROM src/act_wiz.c:2512-2515
    _send_to_char(char, "Ok.\n\r")
    from mud.wiznet import wiznet, WiznetFlag
    victim_short = getattr(victim, "short_descr", "something")
    wiznet(f"$N loads {victim_short}.", char, None, WiznetFlag.WIZ_LOAD, WiznetFlag.WIZ_SECURE, get_trust(char))
    return "Ok.\n\r"


def do_oload(char: Character, vnum_arg: str, level_arg: str | None = None) -> str:
    """
    Load an object by vnum.
    
    ROM Reference: src/act_wiz.c do_oload (lines 2521-2570)
    """
    # mirrors ROM src/act_wiz.c:2531-2534
    if not vnum_arg or not vnum_arg.isdigit():
        return "Syntax: load obj <vnum> <level>.\n\r"

    vnum = int(vnum_arg)
    # mirrors ROM src/act_wiz.c:2537 — default level is trust
    level = get_trust(char)

    if level_arg:
        # mirrors ROM src/act_wiz.c:2539-2552
        if not level_arg.isdigit():
            return "Syntax: load obj <vnum> <level>.\n\r"
        level = int(level_arg)
        if level < 0 or level > get_trust(char):
            return "Level must be be between 0 and your level.\n\r"

    from mud import registry

    # mirrors ROM src/act_wiz.c:2555-2558
    obj_index = getattr(registry, "obj_prototypes", {}).get(vnum)
    if obj_index is None:
        return "No object has that vnum.\n\r"

    # Create the object
    from mud.spawning.obj_spawner import spawn_obj
    obj = spawn_obj(vnum, level)

    if obj is None:
        return "No object has that vnum.\n\r"

    # mirrors ROM src/act_wiz.c:2562-2565
    wear_flags = getattr(obj, "wear_flags", 0)
    if not hasattr(obj, "wear_flags"):
        proto = getattr(obj, "prototype", None)
        if proto:
            wear_flags = getattr(proto, "wear_flags", 0)

    ITEM_TAKE = 1
    if wear_flags & ITEM_TAKE:
        carrying = getattr(char, "inventory", None)
        if carrying is None:
            char.inventory = []
        char.inventory.append(obj)
        obj.carried_by = char
    else:
        room = getattr(char, "room", None)
        if room:
            contents = getattr(room, "contents", None)
            if contents is None:
                room.contents = []
            room.contents.append(obj)
            obj.in_room = room

    # mirrors ROM src/act_wiz.c:2566-2568
    from mud.wiznet import wiznet, WiznetFlag
    wiznet("$N loads $p.", char, obj, WiznetFlag.WIZ_LOAD, WiznetFlag.WIZ_SECURE, get_trust(char))
    return "Ok.\n\r"


def do_purge(char: Character, args: str) -> str:
    """
    Purge mobiles and objects from a room, or a specific target.
    
    ROM Reference: src/act_wiz.c do_purge (lines 2574-2648)
    
    Usage:
    - purge           - Purge all mobs/objects in room
    - purge <target>  - Purge specific mob or player (kicks them)
    """
    room = getattr(char, "room", None)
    if not room:
        return "You're not in a room.\n\r"

    if not args or not args.strip():
        # mirrors ROM src/act_wiz.c:2584-2607 — purge room
        ACT_NOPURGE = 0x00002000
        ITEM_NOPURGE = 0x00000040

        people = list(getattr(room, "people", []))
        for victim in people:
            if victim is char:
                continue
            if not getattr(victim, "is_npc", False):
                continue
            act_flags = getattr(victim, "act", 0)
            if act_flags & ACT_NOPURGE:
                continue
            _extract_char(victim)

        contents = list(getattr(room, "contents", []))
        for obj in contents:
            extra_flags = getattr(obj, "extra_flags", 0)
            if extra_flags & ITEM_NOPURGE:
                continue
            _extract_obj(obj)

        return "Ok.\n\r"

    # Purge specific target
    target_name = args.strip().split()[0]
    # mirrors ROM src/act_wiz.c:2610-2613
    victim = get_char_world(char, target_name)

    if victim is None:
        return "They aren't here.\n\r"

    if not getattr(victim, "is_npc", False):
        # mirrors ROM src/act_wiz.c:2619-2622
        if victim is char:
            return "Ho ho ho.\n\r"

        # mirrors ROM src/act_wiz.c:2625-2631
        if get_trust(char) <= get_trust(victim):
            _send_to_char(victim, f"{getattr(char, 'name', 'Someone')} tried to purge you!\n\r")
            return "Maybe that wasn't a good idea...\n\r"

        _extract_char(victim)
        return "Ok.\n\r"

    # Purge NPC — mirrors ROM src/act_wiz.c:2645-2647
    _extract_char(victim)
    return "Ok.\n\r"


def do_restore(char: Character, args: str) -> str:
    """
    Restore a character to full health/mana/move and remove afflictions.
    
    ROM Reference: src/act_wiz.c do_restore (lines 2785-2869)
    
    Usage:
    - restore         - Restore everyone in room
    - restore room    - Restore everyone in room
    - restore <char>  - Restore specific character
    - restore all     - Restore all online players (MAX_LEVEL - 1 required)
    """
    # mirrors ROM src/act_wiz.c:2792-2817
    if not args or not args.strip() or args.strip().lower() == "room":
        room = getattr(char, "room", None)
        if not room:
            return "You're not in a room.\n\r"

        for victim in list(getattr(room, "people", [])):
            _restore_char(victim)
            _send_to_char(victim, f"{getattr(char, 'name', 'Someone')} has restored you.\n\r")

        from mud.wiznet import wiznet, WiznetFlag
        wiznet(f"$N restored room {getattr(room, 'vnum', 0)}.", char, None, WiznetFlag.WIZ_RESTORE, WiznetFlag.WIZ_SECURE, get_trust(char))

        return "Room restored.\n\r"

    arg = args.strip().lower()

    # mirrors ROM src/act_wiz.c:2820-2845
    if arg == "all":
        if get_trust(char) < MAX_LEVEL - 1:
            return "Not at your level!\n\r"

        from mud import registry
        descriptor_list = getattr(registry, "descriptor_list", [])
        if descriptor_list:
            for desc in descriptor_list:
                victim = getattr(desc, "character", None)
                if victim is None or getattr(victim, "is_npc", False):
                    continue
                _restore_char(victim)
                _send_to_char(victim, f"{getattr(char, 'name', 'Someone')} has restored you.\n\r")
        else:
            for player in getattr(registry, "players", {}).values():
                if not getattr(player, "is_npc", False):
                    _restore_char(player)
                    _send_to_char(player, f"{getattr(char, 'name', 'Someone')} has restored you.\n\r")

        return "All active players restored.\n\r"

    # mirrors ROM src/act_wiz.c:2848-2868
    victim = get_char_world(char, args.strip())
    if victim is None:
        return "They aren't here.\n\r"

    _restore_char(victim)
    _send_to_char(victim, f"{getattr(char, 'name', 'Someone')} has restored you.\n\r")

    from mud.wiznet import wiznet, WiznetFlag
    victim_name = getattr(victim, "short_descr", None) if getattr(victim, "is_npc", False) else getattr(victim, "name", "someone")
    wiznet(f"$N restored {victim_name}", char, None, WiznetFlag.WIZ_RESTORE, WiznetFlag.WIZ_SECURE, get_trust(char))

    return "Ok.\n\r"


def do_slay(char: Character, args: str) -> str:
    """
    Instantly kill a target.
    
    ROM Reference: src/fight.c do_slay (lines 3252-3290)
    
    Usage: slay <target>
    """
    if not args or not args.strip():
        return "Slay whom?"
    
    target_name = args.strip().split()[0]
    victim = get_char_room(char, target_name)
    
    if victim is None:
        return "They aren't here."
    
    if victim is char:
        return "Suicide is a mortal sin."
    
    # Check trust for players
    if not getattr(victim, "is_npc", False):
        if getattr(victim, "level", 1) >= get_trust(char):
            return "You failed."
    
    # Slay the victim
    victim_name = getattr(victim, "name", "someone")
    
    # Extract/kill the victim
    _extract_char(victim)
    
    return f"You slay {victim_name} in cold blood!"


def do_sla(char: Character, args: str) -> str:
    """
    Typo guard for slay - prevents accidental slaying.
    
    ROM Reference: interp.c - sla is a separate command that does nothing
    """
    return "If you want to SLAY, spell it out."


# Helper functions

def _restore_char(char: Character) -> None:
    """Fully restore a character."""
    # Strip negative affects — mirrors ROM affect_strip calls
    # (In full implementation, would strip plague, poison, blindness, sleep, curse)
    
    # Restore stats
    char.hit = getattr(char, "max_hit", 100)
    char.mana = getattr(char, "max_mana", 100)
    char.move = getattr(char, "max_move", 100)
    
    # Update position
    from mud.models.constants import Position
    if getattr(char, "position", Position.STANDING) < Position.STANDING:
        char.position = Position.STANDING


def _extract_char(char: Character) -> None:
    """Remove character from the game."""
    # Stop fighting
    if getattr(char, "fighting", None):
        char.fighting = None
    
    # Remove from room
    room = getattr(char, "room", None)
    if room:
        people = getattr(room, "people", [])
        if char in people:
            people.remove(char)
    
    # Remove from global list
    from mud import registry
    char_list = getattr(registry, "char_list", [])
    if char in char_list:
        char_list.remove(char)
    
    char.room = None


def _extract_obj(obj) -> None:
    """Remove object from the game."""
    room = getattr(obj, "in_room", None)
    if room:
        contents = getattr(room, "contents", [])
        if obj in contents:
            contents.remove(obj)
    
    carrier = getattr(obj, "carried_by", None)
    if carrier:
        carrying = getattr(carrier, "carrying", [])
        if obj in carrying:
            carrying.remove(obj)
    
    container = getattr(obj, "in_obj", None)
    if container:
        contains = getattr(container, "contains", [])
        if obj in contains:
            contains.remove(obj)
    
    obj.in_room = None
    obj.carried_by = None
    obj.in_obj = None


def _send_to_char(char: Character, message: str) -> None:
    """Send message to character."""
    if not hasattr(char, "output_buffer"):
        char.output_buffer = []
    char.output_buffer.append(message)
