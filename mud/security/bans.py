"""ROM-style ban registry supporting prefix/suffix and flag semantics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag
from pathlib import Path
from typing import List, Set


class BanFlag(IntFlag):
    """Bit flags mirroring ROM's BAN_* letter mapping (A..F)."""

    SUFFIX = 1 << 0  # A
    PREFIX = 1 << 1  # B
    NEWBIES = 1 << 2  # C
    ALL = 1 << 3  # D
    PERMIT = 1 << 4  # E
    PERMANENT = 1 << 5  # F


_FLAG_TO_LETTER = {
    BanFlag.SUFFIX: "A",
    BanFlag.PREFIX: "B",
    BanFlag.NEWBIES: "C",
    BanFlag.ALL: "D",
    BanFlag.PERMIT: "E",
    BanFlag.PERMANENT: "F",
}
_LETTER_TO_FLAG = {letter: flag for flag, letter in _FLAG_TO_LETTER.items()}


@dataclass
class BanEntry:
    pattern: str
    flags: BanFlag
    level: int = 0

    def matches(self, host: str) -> bool:
        host_l = host.lower()
        if not self.pattern:
            return False
        prefix = bool(self.flags & BanFlag.PREFIX)
        suffix = bool(self.flags & BanFlag.SUFFIX)
        if prefix and suffix:
            return self.pattern in host_l
        if prefix:
            return host_l.endswith(self.pattern)
        if suffix:
            return host_l.startswith(self.pattern)
        return host_l == self.pattern


_ban_entries: List[BanEntry] = []
_banned_accounts: Set[str] = set()

# Default storage location, mirroring ROM's BAN_FILE semantics.
BANS_FILE = Path("data/bans.txt")

_DEFAULT_ENTRY_FLAGS = BanFlag.ALL | BanFlag.PERMANENT


def _parse_host_pattern(raw: str | None) -> tuple[str, BanFlag]:
    text = (raw or "").strip().lower()
    flags = BanFlag(0)
    if text.startswith("*"):
        flags |= BanFlag.PREFIX
        text = text[1:]
    if text.endswith("*"):
        flags |= BanFlag.SUFFIX
        text = text[:-1]
    return text, flags


def clear_all_bans() -> None:
    _ban_entries.clear()
    _banned_accounts.clear()


def add_banned_host(host: str, *, flags: BanFlag | None = None, level: int = 0) -> None:
    pattern, pattern_flags = _parse_host_pattern(host)
    if not pattern:
        return
    entry_flags = (flags | BanFlag.PERMANENT) if flags is not None else _DEFAULT_ENTRY_FLAGS
    entry_flags |= pattern_flags
    _ban_entries[:] = [
        entry
        for entry in _ban_entries
        if not (entry.pattern == pattern and entry.flags == entry_flags)
    ]
    _ban_entries.append(BanEntry(pattern=pattern, flags=entry_flags, level=level))


def remove_banned_host(host: str) -> None:
    pattern, _ = _parse_host_pattern(host)
    if not pattern:
        return
    _ban_entries[:] = [entry for entry in _ban_entries if entry.pattern != pattern]


def is_host_banned(host: str | None, ban_type: BanFlag = BanFlag.ALL) -> bool:
    if not host:
        return False
    host_norm = host.strip().lower()
    for entry in _ban_entries:
        if not entry.flags & ban_type:
            continue
        if entry.matches(host_norm):
            return True
    return False


def add_banned_account(username: str) -> None:
    _banned_accounts.add(username.strip().lower())


def remove_banned_account(username: str) -> None:
    _banned_accounts.discard(username.strip().lower())


def is_account_banned(username: str | None) -> bool:
    if not username:
        return False
    return username.strip().lower() in _banned_accounts


def _flags_to_string(flags: BanFlag) -> str:
    return "".join(letter for flag, letter in _FLAG_TO_LETTER.items() if flags & flag)


def _string_to_flags(text: str) -> BanFlag:
    flags = BanFlag(0)
    for letter in text:
        flag = _LETTER_TO_FLAG.get(letter.upper())
        if flag:
            flags |= flag
    return flags


def save_bans_file(path: Path | str | None = None) -> None:
    """Write permanent site bans to file in ROM format."""

    target = Path(path) if path else BANS_FILE
    entries = [entry for entry in _ban_entries if entry.flags & BanFlag.PERMANENT]
    if not entries:
        try:
            if target.exists():
                target.unlink()
        except OSError:
            pass
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fp:
        for entry in sorted(entries, key=lambda e: e.pattern):
            flags = _flags_to_string(entry.flags)
            fp.write(f"{entry.pattern:<20} {entry.level:2d} {flags}\n")


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
            parts = line.split()
            if len(parts) < 3:
                continue
            pattern = parts[0].lower()
            level = 0
            try:
                level = int(parts[1])
            except ValueError:
                pass
            flags = _string_to_flags(parts[2])
            if not pattern:
                continue
            _ban_entries.append(BanEntry(pattern=pattern, flags=flags, level=level))
            count += 1
    return count
