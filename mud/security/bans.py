"""ROM-style site and account ban registry with flag-aware matching."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag
from pathlib import Path
from typing import Iterable, List, Optional, Set


class BanFlag(IntFlag):
    """Bit flags mirroring ROM's BAN_* definitions (letters A–F)."""

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
    """In-memory representation of a ROM ban row."""

    pattern: str
    flags: BanFlag
    level: int = 0

    def matches(self, host: str) -> bool:
        candidate = host.strip().lower()
        if not self.pattern:
            return False
        if (self.flags & BanFlag.PREFIX) and (self.flags & BanFlag.SUFFIX):
            return self.pattern in candidate
        if self.flags & BanFlag.PREFIX:
            return candidate.endswith(self.pattern)
        if self.flags & BanFlag.SUFFIX:
            return candidate.startswith(self.pattern)
        return candidate == self.pattern

    def to_pattern(self) -> str:
        text = self.pattern
        if self.flags & BanFlag.PREFIX:
            text = f"*{text}"
        if self.flags & BanFlag.SUFFIX:
            text = f"{text}*"
        return text


_ban_entries: List[BanEntry] = []
_banned_accounts: Set[str] = set()

# Default storage location, mirroring ROM's BAN_FILE semantics.
BANS_FILE = Path("data/bans.txt")


def clear_all_bans() -> None:
    _ban_entries.clear()
    _banned_accounts.clear()


def _parse_host_pattern(host: str) -> tuple[str, BanFlag]:
    value = host.strip().lower()
    flags = BanFlag(0)
    if value.startswith("*"):
        flags |= BanFlag.PREFIX
        value = value[1:]
    if value.endswith("*"):
        flags |= BanFlag.SUFFIX
        value = value[:-1]
    return value.strip(), flags


def _store_entry(pattern: str, flags: BanFlag, level: int) -> None:
    if not pattern:
        return
    prefix_suffix = flags & (BanFlag.PREFIX | BanFlag.SUFFIX)
    for entry in _ban_entries:
        if (
            entry.pattern == pattern
            and (entry.flags & (BanFlag.PREFIX | BanFlag.SUFFIX)) == prefix_suffix
        ):
            entry.flags |= flags
            if level:
                entry.level = max(entry.level, level)
            return
    _ban_entries.insert(0, BanEntry(pattern=pattern, flags=flags, level=level))


def add_banned_host(
    host: str,
    *,
    flags: Optional[Iterable[BanFlag] | BanFlag] = None,
    level: int = 0,
) -> None:
    pattern, wildcard_flags = _parse_host_pattern(host)
    combined = BanFlag(0)
    if flags is None:
        combined = BanFlag.ALL
    else:
        if isinstance(flags, BanFlag):
            combined = flags
        else:
            for flag in flags:
                combined |= BanFlag(flag)
    combined |= wildcard_flags
    combined |= BanFlag.PERMANENT
    _store_entry(pattern, combined, level)


def remove_banned_host(host: str) -> None:
    pattern, wildcard_flags = _parse_host_pattern(host)
    prefix_suffix = wildcard_flags & (BanFlag.PREFIX | BanFlag.SUFFIX)
    if not pattern:
        return
    remaining: List[BanEntry] = []
    for entry in _ban_entries:
        if entry.pattern == pattern and (
            entry.flags & (BanFlag.PREFIX | BanFlag.SUFFIX)
        ) == prefix_suffix:
            continue
        remaining.append(entry)
    _ban_entries[:] = remaining


def is_host_banned(host: str | None, ban_type: BanFlag = BanFlag.ALL) -> bool:
    if not host:
        return False
    for entry in _ban_entries:
        if not entry.flags & ban_type:
            continue
        if entry.matches(host):
            return True
    return False


def get_ban_entries() -> List[BanEntry]:
    return list(_ban_entries)


def add_banned_account(username: str) -> None:
    _banned_accounts.add(username.strip().lower())


def remove_banned_account(username: str) -> None:
    _banned_accounts.discard(username.strip().lower())


def is_account_banned(username: str | None) -> bool:
    if not username:
        return False
    return username.strip().lower() in _banned_accounts


def _flags_to_string(flags: BanFlag) -> str:
    letters: list[str] = []
    for flag in (BanFlag.SUFFIX, BanFlag.PREFIX, BanFlag.NEWBIES, BanFlag.ALL, BanFlag.PERMIT, BanFlag.PERMANENT):
        if flags & flag:
            letters.append(_FLAG_TO_LETTER[flag])
    return "".join(letters)


def _flags_from_string(text: str) -> BanFlag:
    result = BanFlag(0)
    for char in text.strip().upper():
        flag = _LETTER_TO_FLAG.get(char)
        if flag is not None:
            result |= flag
    return result


def save_bans_file(path: Path | str | None = None) -> None:
    target = Path(path) if path else BANS_FILE
    persistent = [entry for entry in _ban_entries if entry.flags & BanFlag.PERMANENT]
    if not persistent:
        try:
            if target.exists():
                target.unlink()
        except OSError:
            pass
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fp:
        for entry in persistent:
            flags = _flags_to_string(entry.flags)
            fp.write(f"{entry.pattern:<20} {entry.level:2d} {flags}\n")


def load_bans_file(path: Path | str | None = None) -> int:
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
            try:
                level = int(parts[1])
            except ValueError:
                level = 0
            flags = _flags_from_string(parts[2])
            if not flags:
                continue
            _store_entry(pattern, flags, level)
            count += 1
    return count
