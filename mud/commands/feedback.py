"""
Player feedback commands (bug, idea, typo).

ROM Reference: src/act_info.c lines 100-160
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.character import Character


def _write_feedback(filename: str, ch: Character, args: str) -> str:
    """
    Write player feedback to a log file.

    ROM Reference: src/act_info.c do_bug/do_idea/do_typo pattern
    """
    args = args.strip()
    if not args:
        return f"Please include a description."

    # Create log directory if it doesn't exist
    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True)

    # Get character name
    char_name = getattr(ch, "name", "Unknown")
    char_level = getattr(ch, "level", 0)

    # Get room info if available
    room = getattr(ch, "room", None)
    room_vnum = getattr(room, "vnum", 0) if room else 0

    # Create log entry
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {char_name} (level {char_level}) in room {room_vnum}: {args}\n"

    # Write to file
    log_file = log_dir / filename
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        return f"Thank you, your feedback has been recorded."
    except Exception as e:
        return f"Error recording feedback: {e}"


def do_bug(ch: Character, args: str) -> str:
    """
    Report a bug.

    ROM Reference: src/act_info.c lines 100-120 (do_bug)

    Usage: bug <description>

    Records the bug report in log/bugs.txt with timestamp, character info,
    and location for later review by immortals.
    """
    return _write_feedback("bugs.txt", ch, args)


def do_idea(ch: Character, args: str) -> str:
    """
    Submit an idea for improvement.

    ROM Reference: src/act_info.c lines 120-140 (do_idea)

    Usage: idea <description>

    Records the idea in log/ideas.txt with timestamp, character info,
    and location for later review by immortals.
    """
    return _write_feedback("ideas.txt", ch, args)


def do_typo(ch: Character, args: str) -> str:
    """
    Report a typo in room descriptions or text.

    ROM Reference: src/act_info.c lines 140-160 (do_typo)

    Usage: typo <description>

    Records the typo report in log/typos.txt with timestamp, character info,
    and location for later review by builders.
    """
    return _write_feedback("typos.txt", ch, args)
