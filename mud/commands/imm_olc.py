"""
OLC (Online Creation) commands - resets, alist, edit.

ROM Reference: src/olc.c
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.character import Character
from mud.commands.imm_commands import get_trust, LEVEL_IMMORTAL

if TYPE_CHECKING:
    pass


def do_resets(char: Character, args: str) -> str:
    """
    View or modify room resets.
    
    ROM Reference: src/olc.c do_resets (lines 1232-1476)
    
    Usage:
    - resets                       - Display resets in current room
    - resets <num> delete          - Delete reset
    - resets <num> mob <vnum>      - Add mob reset
    - resets <num> obj <vnum>      - Add obj reset
    """
    room = getattr(char, "room", None)
    if not room:
        return "You're not in a room."
    
    # Check builder security
    area = getattr(room, "area", None)
    if area:
        if not _is_builder(char, area):
            return "Resets: Invalid security for editing this area."
    
    if not args or not args.strip():
        # Display resets
        resets = getattr(room, "resets", [])
        if not resets:
            return "No resets in this room."
        
        lines = ["Resets: M = mobile, R = room, O = object, P = pet, S = shopkeeper"]
        for i, reset in enumerate(resets, 1):
            reset_cmd = getattr(reset, "command", "?")
            arg1 = getattr(reset, "arg1", 0)
            arg2 = getattr(reset, "arg2", 0)
            arg3 = getattr(reset, "arg3", 0)
            lines.append(f"  [{i:2d}] {reset_cmd} {arg1:5d} {arg2:3d} {arg3:5d}")
        
        return "\n".join(lines)
    
    parts = args.strip().split()
    
    if len(parts) >= 2 and parts[0].isdigit():
        idx = int(parts[0])
        action = parts[1].lower()
        
        if action == "delete":
            resets = getattr(room, "resets", [])
            if idx < 1 or idx > len(resets):
                return "Reset not found."
            
            resets.pop(idx - 1)
            return "Reset deleted."
        
        if action == "mob" and len(parts) >= 3:
            if not parts[2].isdigit():
                return "Mob vnum must be a number."
            
            from mud import registry
            vnum = int(parts[2])
            
            if vnum not in registry.mob_prototypes:
                return "No mobile has that vnum."
            
            # Add reset (simplified)
            resets = getattr(room, "resets", None)
            if resets is None:
                room.resets = []
                resets = room.resets
            
            # Create reset entry
            from types import SimpleNamespace
            reset = SimpleNamespace(command='M', arg1=vnum, arg2=1, arg3=room.vnum)
            resets.insert(idx - 1 if idx > 0 else len(resets), reset)
            
            return f"Mobile reset added at position {idx}."
        
        if action == "obj" and len(parts) >= 3:
            if not parts[2].isdigit():
                return "Object vnum must be a number."
            
            from mud import registry
            vnum = int(parts[2])
            
            if vnum not in registry.obj_prototypes:
                return "No object has that vnum."
            
            # Add reset
            resets = getattr(room, "resets", None)
            if resets is None:
                room.resets = []
                resets = room.resets
            
            from types import SimpleNamespace
            reset = SimpleNamespace(command='O', arg1=vnum, arg2=0, arg3=room.vnum)
            resets.insert(idx - 1 if idx > 0 else len(resets), reset)
            
            return f"Object reset added at position {idx}."
    
    return ("Syntax:\n"
            "  resets                       - Display resets\n"
            "  resets <num> delete          - Delete reset\n"
            "  resets <num> mob <vnum>      - Add mob reset\n"
            "  resets <num> obj <vnum>      - Add obj reset")


def do_alist(char: Character, args: str) -> str:
    """
    List all areas with their details.
    
    ROM Reference: src/olc.c do_alist (lines 1478-1510)
    
    Usage: alist
    """
    if getattr(char, "is_npc", False):
        return ""
    
    from mud import registry
    
    lines = [f"[{'Num':>3s}] [{'Area Name':<27s}] ({'lvnum':>5s}-{'uvnum':>5s}) [{'Filename':<10s}] {'Sec':>3s} [{'Builders':<10s}]"]
    
    for i, area in enumerate(getattr(registry, "areas", []), 1):
        name = getattr(area, "name", "Unknown")[:27]
        min_vnum = getattr(area, "min_vnum", 0)
        max_vnum = getattr(area, "max_vnum", 0)
        filename = getattr(area, "filename", "")[:10]
        security = getattr(area, "security", 0)
        builders = getattr(area, "builders", "")[:10]
        
        lines.append(f"[{i:3d}] {name:<29s} ({min_vnum:>5d}-{max_vnum:>5d}) {filename:<12s} [{security}] [{builders:<10s}]")
    
    return "\n".join(lines)


def do_edit(char: Character, args: str) -> str:
    """
    General edit command router.
    
    ROM Reference: src/olc.c
    
    Usage:
    - edit room [vnum]      - Edit a room
    - edit mob <vnum>       - Edit a mobile
    - edit obj <vnum>       - Edit an object
    - edit area [vnum]      - Edit an area
    """
    if not args or not args.strip():
        return ("Syntax:\n"
                "  edit room [vnum]      - Edit a room\n"
                "  edit mob <vnum>       - Edit a mobile\n"
                "  edit obj <vnum>       - Edit an object\n"
                "  edit area [vnum]      - Edit an area")
    
    parts = args.strip().split()
    edit_type = parts[0].lower()
    vnum_arg = parts[1] if len(parts) > 1 else None
    
    if edit_type == "room":
        if vnum_arg and vnum_arg.isdigit():
            return f"Entering room editor for vnum {vnum_arg}."
        room = getattr(char, "room", None)
        if room:
            return f"Entering room editor for vnum {getattr(room, 'vnum', 0)}."
        return "You're not in a room."
    
    if edit_type in ("mob", "mobile"):
        if not vnum_arg or not vnum_arg.isdigit():
            return "Syntax: edit mob <vnum>"
        return f"Entering mobile editor for vnum {vnum_arg}."
    
    if edit_type in ("obj", "object"):
        if not vnum_arg or not vnum_arg.isdigit():
            return "Syntax: edit obj <vnum>"
        return f"Entering object editor for vnum {vnum_arg}."
    
    if edit_type == "area":
        if vnum_arg and vnum_arg.isdigit():
            return f"Entering area editor for area {vnum_arg}."
        room = getattr(char, "room", None)
        if room:
            area = getattr(room, "area", None)
            if area:
                return f"Entering area editor for '{getattr(area, 'name', 'Unknown')}'."
        return "You're not in an area."
    
    return ("Syntax:\n"
            "  edit room [vnum]      - Edit a room\n"
            "  edit mob <vnum>       - Edit a mobile\n"
            "  edit obj <vnum>       - Edit an object\n"
            "  edit area [vnum]      - Edit an area")


def do_mpedit(char: Character, args: str) -> str:
    """
    Edit mob programs.
    
    ROM Reference: src/olc.c
    
    Usage: mpedit <vnum>
    """
    if not args or not args.strip():
        return "Syntax: mpedit <vnum>"
    
    vnum_arg = args.strip().split()[0]
    
    if not vnum_arg.isdigit():
        return "Vnum must be numeric."
    
    from mud import registry
    vnum = int(vnum_arg)
    
    if vnum not in registry.mob_prototypes:
        return "No mobile has that vnum."
    
    return f"Entering mobprog editor for mobile vnum {vnum}."


# Helper function

def _is_builder(char: Character, area) -> bool:
    """Check if character can build in an area."""
    # Implementers can build anywhere
    if get_trust(char) >= 60:
        return True
    
    # Check builder list
    builders = getattr(area, "builders", "")
    char_name = getattr(char, "name", "")
    
    if char_name.lower() in builders.lower():
        return True
    
    # Check security
    pcdata = getattr(char, "pcdata", None)
    if pcdata:
        char_security = getattr(pcdata, "security", 0)
        area_security = getattr(area, "security", 9)
        return char_security >= area_security
    
    return False
