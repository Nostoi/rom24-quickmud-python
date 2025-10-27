"""Runtime logging helpers that mirror ROM's `log_string`."""

from __future__ import annotations

import sys
import time


def log_game_event(message: str) -> str:
    """Write *message* to stderr with a ROM-style timestamp and return it.

    ROM's ``log_string`` prepends ``ctime(current_time)`` to the payload and
    prints to stderr. The Python port mirrors that behaviour so staff can audit
    gameplay milestones such as level gains.
    """

    timestamp = time.ctime().rstrip()
    entry = f"{timestamp} :: {message}"
    sys.stderr.write(entry + "\n")
    return entry
