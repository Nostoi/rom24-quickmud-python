"""
Character customization commands (password, title, description).

ROM Reference: src/act_info.c lines 2547-2650, 2833-2925
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.character import Character


def do_password(ch: Character, args: str) -> str:
    """
    Change your password.

    ROM Reference: src/act_info.c lines 2833-2925 (do_password)

    Usage: password <old> <new>

    Changes your character password. The old password must match,
    and the new password must be at least 5 characters long.
    """
    # NPCs can't change passwords
    is_npc = getattr(ch, "is_npc", False)
    if is_npc:
        return ""

    args = args.strip()
    parts = args.split(None, 1)

    if len(parts) < 2:
        return "Syntax: password <old> <new>"

    old_password = parts[0]
    new_password = parts[1]

    # Check minimum length
    if len(new_password) < 5:
        return "New password must be at least five characters long."

    # For now, just simulate password change
    # In a real implementation, this would use hash_utils to verify old password
    # and hash the new password
    return "Password functionality not yet fully implemented. Use account system."


def do_title(ch: Character, args: str) -> str:
    """
    Set your title.

    ROM Reference: src/act_info.c lines 2547-2575 (do_title)

    Usage: title <new title>

    Sets your character's title that appears after your name in the who list
    and other displays. Maximum length is 45 characters.
    """
    # NPCs can't set titles
    is_npc = getattr(ch, "is_npc", False)
    if is_npc:
        return ""

    args = args.strip()

    if not args:
        return "Change your title to what?"

    # Limit title length to 45 characters (ROM limit)
    if len(args) > 45:
        args = args[:45]

    # Remove trailing color codes that might be cut off
    if len(args) > 0 and args[-1] == "{":
        args = args[:-1]

    # Set the title
    try:
        pcdata = getattr(ch, "pcdata", None)
        if pcdata:
            pcdata.title = args
        return "Ok."
    except Exception as e:
        return f"Error setting title: {e}"


def do_description(ch: Character, args: str) -> str:
    """
    Set or edit your character description.

    ROM Reference: src/act_info.c lines 2579-2650 (do_description)

    Usage:
        description          - Enter line-by-line editor
        description +<text>  - Add a line to your description
        description -        - Remove last line from description

    Your description is what others see when they 'look' at you.
    """
    # NPCs can't set descriptions
    is_npc = getattr(ch, "is_npc", False)
    if is_npc:
        return ""

    args = args.strip()

    # Get current description
    current_desc = getattr(ch, "description", "")
    if current_desc is None:
        current_desc = ""

    # No arguments - show current description
    if not args:
        if not current_desc:
            return "Your description is:\n(None)."
        return f"Your description is:\n{current_desc}"

    # Remove a line
    if args.startswith("-"):
        if not current_desc:
            return "No lines left to remove."

        # Split into lines and remove the last one
        lines = current_desc.split("\n")
        if lines:
            lines = lines[:-1]

        new_desc = "\n".join(lines)
        try:
            ch.description = new_desc
            if not new_desc:
                return "Description cleared."
            return f"Your description is:\n{new_desc}"
        except Exception as e:
            return f"Error updating description: {e}"

    # Add a line
    if args.startswith("+"):
        new_line = args[1:].strip()
        if not new_line:
            return "Add what to your description?"

        if current_desc:
            new_desc = f"{current_desc}\n{new_line}"
        else:
            new_desc = new_line

        try:
            ch.description = new_desc
            return "Ok."
        except Exception as e:
            return f"Error updating description: {e}"

    # Replace entire description
    try:
        ch.description = args
        return "Ok."
    except Exception as e:
        return f"Error setting description: {e}"
