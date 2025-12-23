"""
Player configuration commands - nofollow, nosummon, noloot, delete.

ROM Reference: src/act_info.c, src/act_comm.c
"""
from __future__ import annotations

from mud.models.character import Character


# Player act flags (PLR_*)
PLR_CANLOOT = 0x00008000
PLR_NOSUMMON = 0x00010000
PLR_NOFOLLOW = 0x00020000


def do_noloot(char: Character, args: str) -> str:
    """
    Toggle whether others can loot your corpse.
    
    ROM Reference: src/act_info.c do_noloot (lines 972-986)
    
    Usage: noloot
    """
    if getattr(char, "is_npc", False):
        return ""
    
    act_flags = getattr(char, "act", 0)
    
    if act_flags & PLR_CANLOOT:
        char.act = act_flags & ~PLR_CANLOOT
        return "Your corpse is now safe from thieves."
    else:
        char.act = act_flags | PLR_CANLOOT
        return "Your corpse may now be looted."


def do_nofollow(char: Character, args: str) -> str:
    """
    Toggle whether others can follow you.
    
    ROM Reference: src/act_info.c do_nofollow (lines 989-1004)
    
    Usage: nofollow
    
    Note: Enabling nofollow also stops all current followers.
    """
    if getattr(char, "is_npc", False):
        return ""
    
    act_flags = getattr(char, "act", 0)
    
    if act_flags & PLR_NOFOLLOW:
        char.act = act_flags & ~PLR_NOFOLLOW
        return "You now accept followers."
    else:
        char.act = act_flags | PLR_NOFOLLOW
        # Stop all followers
        _die_follower(char)
        return "You no longer accept followers."


def do_nosummon(char: Character, args: str) -> str:
    """
    Toggle whether you can be summoned.
    
    ROM Reference: src/act_info.c do_nosummon (lines 1007-1030)
    
    Usage: nosummon
    """
    is_npc = getattr(char, "is_npc", False)
    
    if is_npc:
        # NPCs use imm_flags
        imm_flags = getattr(char, "imm_flags", 0)
        IMM_SUMMON = 0x00000010
        
        if imm_flags & IMM_SUMMON:
            char.imm_flags = imm_flags & ~IMM_SUMMON
            return "You are no longer immune to summon."
        else:
            char.imm_flags = imm_flags | IMM_SUMMON
            return "You are now immune to summoning."
    else:
        act_flags = getattr(char, "act", 0)
        
        if act_flags & PLR_NOSUMMON:
            char.act = act_flags & ~PLR_NOSUMMON
            return "You are no longer immune to summon."
        else:
            char.act = act_flags | PLR_NOSUMMON
            return "You are now immune to summoning."


def do_delete(char: Character, args: str) -> str:
    """
    Delete your character permanently.
    
    ROM Reference: src/act_comm.c do_delete (lines 54-93)
    
    Usage:
    - delete         - Request deletion (first time)
    - delete         - Confirm deletion (second time)
    - delete <arg>   - Cancel deletion request
    
    WARNING: This command is irreversible!
    """
    if getattr(char, "is_npc", False):
        return ""
    
    pcdata = getattr(char, "pcdata", None)
    if pcdata is None:
        return ""
    
    confirm_delete = getattr(pcdata, "confirm_delete", False)
    
    if confirm_delete:
        # Already requested - check for confirm or cancel
        if args and args.strip():
            # Any argument cancels
            pcdata.confirm_delete = False
            return "Delete status removed."
        else:
            # Confirmed - delete the character
            char_name = getattr(char, "name", "Unknown")
            
            # Stop fighting
            if hasattr(char, "fighting") and char.fighting:
                char.fighting = None
            
            # Log out
            from mud.commands.session import do_quit
            do_quit(char, "")
            
            # Delete player file
            import os
            player_dir = "player"
            player_file = os.path.join(player_dir, f"{char_name.capitalize()}")
            if os.path.exists(player_file):
                try:
                    os.unlink(player_file)
                except OSError:
                    pass
            
            return ""  # Player is gone
    
    # First request
    if args and args.strip():
        return "Just type delete. No argument."
    
    pcdata.confirm_delete = True
    
    return ("Type delete again to confirm this command.\n"
            "WARNING: this command is irreversible.\n"
            "Typing delete with an argument will undo delete status.")


def do_delet(char: Character, args: str) -> str:
    """
    Typo guard for delete - prevents accidental deletion.
    
    ROM Reference: interp.c - delet is a separate command that does nothing
    
    Usage: delet
    """
    return "You must type the full command to delete yourself."


# Helper functions

def _die_follower(char: Character) -> None:
    """
    Stop all followers from following this character.
    
    ROM Reference: src/handler.c die_follower
    """
    # Stop anyone following this character
    from mud import registry
    
    # Check all characters
    for ch in getattr(registry, "char_list", []):
        master = getattr(ch, "master", None)
        if master is char:
            _stop_follower(ch)
    
    # Also check room
    room = getattr(char, "room", None)
    if room:
        for ch in getattr(room, "people", []):
            master = getattr(ch, "master", None)
            if master is char:
                _stop_follower(ch)


def _stop_follower(char: Character) -> None:
    """
    Stop a character from following their master.
    
    ROM Reference: src/handler.c stop_follower
    """
    master = getattr(char, "master", None)
    if master is None:
        return
    
    # Remove charm affect
    affected_by = getattr(char, "affected_by", 0)
    from mud.models.constants import AffectFlag
    if affected_by & AffectFlag.CHARM:
        char.affected_by = affected_by & ~AffectFlag.CHARM
    
    # Clear master/leader
    char.master = None
    char.leader = None
    
    master_name = getattr(master, "name", "someone")
    # Would send message but we don't have session context here
