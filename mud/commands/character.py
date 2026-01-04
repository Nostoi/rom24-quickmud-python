"""
Character customization commands (password, title, description).

ROM Reference: src/act_info.c lines 2547-2650, 2833-2925
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.account.account_manager import save_character
from mud.security.hash_utils import hash_password, verify_password
from mud.utils.text import smash_tilde

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

    # Gap 1 (P0 - CRITICAL): Password verification (ROM src/act_info.c:2890-2895)
    pcdata = getattr(ch, "pcdata", None)
    if not pcdata:
        return "Error: No character data."

    current_pwd = getattr(pcdata, "pwd", None)
    if not current_pwd:
        return "Error: No password set."

    if not verify_password(old_password, current_pwd):
        # ROM C: 10-second WAIT_STATE penalty (40 pulses * 0.25s = 10s)
        ch.wait = 40
        return "Wrong password. Wait 10 seconds."

    # Gap 1 (P1): Check minimum length (ROM src/act_info.c:2897-2904)
    if len(new_password) < 5:
        return "New password must be at least five characters long."

    # Gap 2 (P0 - CRITICAL): Hash new password (ROM src/act_info.c:2905)
    new_hashed = hash_password(new_password)

    # Gap 3 (P1 - IMPORTANT): Tilde validation (ROM src/act_info.c:2906-2912)
    # ROM C uses tilde as record delimiter in player files
    if "~" in new_hashed:
        return "New password not acceptable, try again."

    # Update password in memory
    pcdata.pwd = new_hashed

    # Gap 4 (P0 - CRITICAL): Save character to disk (ROM src/act_info.c:2916)
    try:
        save_character(ch)
    except Exception as e:
        # Revert password change on save failure
        pcdata.pwd = current_pwd
        return f"Error saving password: {e}"

    return "Ok."


def set_title(ch: Character, title: str) -> None:
    """
    Set character title with automatic spacing.

    ROM Reference: src/act_info.c lines 2520-2543 (set_title helper)

    Automatically adds a leading space unless the title starts with
    punctuation (., ,, !, ?). This ensures titles display correctly
    after character names.
    """
    is_npc = getattr(ch, "is_npc", False)
    if is_npc:
        return

    pcdata = getattr(ch, "pcdata", None)
    if not pcdata:
        return

    if title and title[0] not in (".", ",", "!", "?"):
        pcdata.title = " " + title
    else:
        pcdata.title = title


def do_title(ch: Character, args: str) -> str:
    """
    Set your title.

    ROM Reference: src/act_info.c lines 2547-2575 (do_title)

    Usage: title <new title>

    Sets your character's title that appears after your name in the who list
    and other displays. Maximum length is 45 characters.
    """
    is_npc = getattr(ch, "is_npc", False)
    if is_npc:
        return ""

    if len(args) > 45:
        args = args[:45]

    i = len(args)
    if i > 1 and args[i - 1] == "{" and args[i - 2] != "{":
        args = args[: i - 1]

    if not args.strip():
        return "Change your title to what?"

    args = smash_tilde(args)
    set_title(ch, args)
    return "Ok."


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
    is_npc = getattr(ch, "is_npc", False)
    if is_npc:
        return ""

    args = args.strip()

    current_desc = getattr(ch, "description", "")
    if current_desc is None:
        current_desc = ""

    if not args:
        if not current_desc:
            return "Your description is:\n(None)."
        return f"Your description is:\n{current_desc}"

    args = smash_tilde(args)

    if args.startswith("-"):
        if not current_desc:
            return "No lines left to remove."

        lines = [line for line in current_desc.split("\n") if line]
        if not lines:
            ch.description = ""
            return "Description cleared."

        lines = lines[:-1]

        if not lines:
            ch.description = ""
            return "Description cleared."

        new_desc = "\n".join(lines) + "\n"
        ch.description = new_desc
        return f"Your description is:\n{new_desc}"

    if args.startswith("+"):
        new_line = args[1:].strip()
        if not new_line:
            return "Add what to your description?"

        if current_desc:
            new_desc = f"{current_desc}\n{new_line}"
        else:
            new_desc = new_line

        if len(new_desc) >= 1024:
            return "Description too long."

        ch.description = new_desc
        return f"Your description is:\n{new_desc}"

    if len(args) >= 1024:
        return "Description too long."

    ch.description = args
    return f"Your description is:\n{args}"
