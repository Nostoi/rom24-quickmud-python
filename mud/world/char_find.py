"""
Character finding utilities - find characters by name.

ROM Reference: src/handler.c get_char_room, get_char_world, etc.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.character import Character


def get_char_room(char: "Character", name: str) -> "Character | None":
    """
    Find a character in the same room by name.
    
    ROM Reference: src/handler.c get_char_room
    
    Supports:
    - Direct name match
    - N.name format (e.g., "2.guard" for second guard)
    - Partial name matching
    """
    if not name:
        return None
    
    room = getattr(char, "room", None)
    if not room:
        return None
    
    # Parse N.name format
    count = 0
    target_count = 1
    
    if "." in name:
        parts = name.split(".", 1)
        try:
            target_count = int(parts[0])
            name = parts[1]
        except ValueError:
            pass  # Not a number, use full name
    
    name_lower = name.lower()
    
    # Search room occupants
    for occupant in getattr(room, "people", []):
        # Don't match self
        if occupant is char:
            continue
        
        # Check visibility
        from mud.world.vision import can_see_character
        if not can_see_character(char, occupant):
            continue
        
        # Check name match
        occupant_name = getattr(occupant, "name", "").lower()
        occupant_short = (getattr(occupant, "short_descr", "") or "").lower()
        
        # Check for keyword match in name or short_descr
        if name_lower in occupant_name or name_lower in occupant_short:
            count += 1
            if count == target_count:
                return occupant
        
        # Also check aliases/keywords if present
        keywords = getattr(occupant, "keywords", "") or ""
        if name_lower in keywords.lower():
            count += 1
            if count == target_count:
                return occupant
    
    return None


def get_char_world(char: "Character", name: str) -> "Character | None":
    """
    Find a character anywhere in the world by name.
    
    ROM Reference: src/handler.c get_char_world
    """
    from mud.models.character import character_registry
    
    if not name:
        return None
    
    # Parse N.name format
    count = 0
    target_count = 1
    
    if "." in name:
        parts = name.split(".", 1)
        try:
            target_count = int(parts[0])
            name = parts[1]
        except ValueError:
            pass
    
    name_lower = name.lower()
    
    # Search all characters
    for ch in character_registry.values():
        # Check visibility
        from mud.world.vision import can_see_character
        if not can_see_character(char, ch):
            continue
        
        ch_name = getattr(ch, "name", "").lower()
        ch_short = (getattr(ch, "short_descr", "") or "").lower()
        
        if name_lower in ch_name or name_lower in ch_short:
            count += 1
            if count == target_count:
                return ch
    
    return None


def is_name(name: str, name_list: str) -> bool:
    """
    Check if name matches any word in name_list.
    
    ROM Reference: src/handler.c is_name
    """
    if not name or not name_list:
        return False
    
    name_lower = name.lower()
    for word in name_list.lower().split():
        if name_lower in word or word.startswith(name_lower):
            return True
    
    return False
