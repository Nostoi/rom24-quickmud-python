"""
Player configuration commands - nofollow, nosummon, noloot, delete.

ROM Reference: src/act_info.c, src/act_comm.c
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import DefenseBit, PlayerFlag

# Player act flags (PLR_*) — derive from the canonical IntFlag enum, never a
# hardcoded hex bit (AGENTS.md ROM Parity Rules; guarded by
# tests/test_flag_hex_convention.py).
PLR_CANLOOT = int(PlayerFlag.CANLOOT)
PLR_NOSUMMON = int(PlayerFlag.NOSUMMON)
PLR_NOFOLLOW = int(PlayerFlag.NOFOLLOW)


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
        IMM_SUMMON = int(DefenseBit.SUMMON)  # mirroring ROM src/merc.h IMM_SUMMON (A = 1<<0)

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

            # DELETE-002 — ROM src/act_comm.c:62 broadcasts the confirm pass to
            # staff BEFORE the quit + unlink (`wiznet("$N turns $Mself into line
            # noise.", ch, NULL, 0, 0, 0)`). Fire it here while `char` is still
            # valid; flag=0/flag_skip=0/min_level=0 → every WIZ_ON immortal sees it.
            from mud.wiznet import wiznet

            wiznet("$N turns $Mself into line noise.", char, None, None, None, 0)

            # Stop fighting
            if hasattr(char, "fighting") and char.fighting:
                char.fighting = None

            # Log out — ROM do_function(ch, &do_quit, "") (saves, then unlink).
            from mud.commands.session import do_quit

            do_quit(char, "")

            # Delete the character. DB-canonical (INV-008): the player's state +
            # auth live in the `characters` DB row, so deletion removes that row
            # — the faithful equivalent of ROM's `unlink(strsave)` on the pfile.
            # The old code unlinked a path that was never written ("player/Name",
            # capitalized, no extension), so the row survived and the character
            # stayed loginable after delete-delete. DELETE-001.
            from mud.account.account_manager import delete_character

            delete_character(char_name)

            return ""  # Player is gone

    # First request
    if args and args.strip():
        return "Just type delete. No argument."

    pcdata.confirm_delete = True

    # DELETE-002 — ROM src/act_comm.c:92 broadcasts the request pass to staff at
    # the deleter's own trust level (`wiznet("$N is contemplating deletion.", ch,
    # NULL, 0, 0, get_trust(ch))`) — only immortals trusted >= the deleter see it.
    from mud.commands.imm_commands import get_trust
    from mud.wiznet import wiznet

    wiznet("$N is contemplating deletion.", char, None, None, None, get_trust(char))

    return (
        "Type delete again to confirm this command.\n"
        "WARNING: this command is irreversible.\n"
        "Typing delete with an argument will undo delete status."
    )


def do_delet(char: Character, args: str) -> str:
    """
    Typo guard for delete - prevents accidental deletion.

    ROM Reference: interp.c - delet is a separate command that does nothing

    Usage: delet
    """
    return "You must type the full command to delete yourself."


# Helper functions


def _die_follower(char: Character) -> None:
    """Stop all followers from following this character.

    Delegates to the canonical ``mud.characters.follow.die_follower``
    (mirroring ROM src/act_comm.c:1658-1680, a char_list walk). INV-046: the
    old duplicate walked a phantom registry attribute plus the same room
    only, leaving cross-room followers attached.
    """
    from mud.characters.follow import die_follower

    die_follower(char)
