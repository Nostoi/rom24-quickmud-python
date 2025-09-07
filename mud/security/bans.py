"""Simple ban registry for site/account bans (Phase 1).

This module provides in-memory helpers to enforce ROM-style bans at login.
Persistence and full ROM format will be added in a follow-up task.
"""

from __future__ import annotations

from pathlib import Path
from typing import Set

_banned_hosts: Set[str] = set()
_banned_accounts: Set[str] = set()

# Default storage location, mirroring ROM's BAN_FILE semantics.
BANS_FILE = Path("data/bans.txt")


def clear_all_bans() -> None:
    _banned_hosts.clear()
    _banned_accounts.clear()


def add_banned_host(host: str) -> None:
    _banned_hosts.add(host.strip().lower())


def remove_banned_host(host: str) -> None:
    _banned_hosts.discard(host.strip().lower())


def is_host_banned(host: str | None) -> bool:
    if not host:
        return False
    return host.strip().lower() in _banned_hosts


def add_banned_account(username: str) -> None:
    _banned_accounts.add(username.strip().lower())


def remove_banned_account(username: str) -> None:
    _banned_accounts.discard(username.strip().lower())


def is_account_banned(username: str | None) -> bool:
    if not username:
        return False
    return username.strip().lower() in _banned_accounts


# --- ROM-compatible persistence (minimal) ---

# ROM uses letter flags A.. for bit positions; for bans we need:
# BAN_ALL = D, BAN_PERMANENT = F. We emit "DF" for permanent site-wide bans.
_ROM_FLAG_ALL = "D"
_ROM_FLAG_PERM = "F"


def _flags_to_string() -> str:
    # For now, we only persist permanent, all-site bans.
    return _ROM_FLAG_ALL + _ROM_FLAG_PERM


def save_bans_file(path: Path | str | None = None) -> None:
    """Write permanent site bans to file in ROM format.

    Format per ROM src/ban.c save_bans():
        "%-20s %-2d %s\n" → name, level, flags-as-letters
    We don't track setter level yet; write level 0.
    """
    target = Path(path) if path else BANS_FILE
    if not _banned_hosts:
        # Mirror ROM behavior: delete file if no permanent bans remain.
        try:
            if target.exists():
                target.unlink()
        except OSError:
            pass
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fp:
        for host in sorted(_banned_hosts):
            name = host
            level = 0
            flags = _flags_to_string()
            fp.write(f"{name:<20} {level:2d} {flags}\n")


def load_bans_file(path: Path | str | None = None) -> int:
    """Load bans from ROM-format file into memory; returns count loaded."""
    target = Path(path) if path else BANS_FILE
    if not target.exists():
        return 0
    count = 0
    with target.open("r", encoding="utf-8") as fp:
        for raw in fp:
            line = raw.strip()
            if not line:
                continue
            # Expect: name(<20 padded>) <level> <flags>
            parts = line.split()
            if len(parts) < 3:
                continue
            name = parts[0]
            # level = parts[1]  # unused here
            flags = parts[2]
            # Only import entries that include permanent+all flags
            if _ROM_FLAG_PERM in flags:
                _banned_hosts.add(name.lower())
                count += 1
    return count
