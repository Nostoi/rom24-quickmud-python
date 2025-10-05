"""ROM-style site and account ban registry with flag-aware matching."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntFlag
from pathlib import Path


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


_ban_entries: list[BanEntry] = []
_banned_accounts: set[str] = set()

# Default storage locations, mirroring ROM's BAN_FILE semantics.
BANS_FILE = Path("data/bans.txt")
ACCOUNT_BANS_FILE = Path("data/bans_accounts.txt")


def _resolve_path(path: Path | str | None, *, account: bool = False) -> Path:
    if path is None:
        return ACCOUNT_BANS_FILE if account else BANS_FILE
    base = Path(path)
    if not account:
        return base
    suffix = base.suffix or ""
    stem = base.stem if suffix else base.name
    account_name = f"{stem}_accounts{suffix}"
    return base.with_name(account_name)


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


def _store_entry(pattern: str, flags: BanFlag, level: int, *, replace_existing: bool) -> None:
    """Store a ban entry, mirroring ROM insertion order semantics."""

    if not pattern:
        return

    prefix_suffix = flags & (BanFlag.PREFIX | BanFlag.SUFFIX)

    if replace_existing:
        existing_level = level
        retained: list[BanEntry] = []
        for entry in _ban_entries:
            if entry.pattern != pattern:
                retained.append(entry)
                continue
            existing_level = max(existing_level, entry.level)
        if not level and existing_level:
            level = existing_level
        _ban_entries[:] = retained
        entry = BanEntry(pattern=pattern, flags=flags, level=level)
        _ban_entries.insert(0, entry)
        return
    else:
        for entry in _ban_entries:
            if entry.pattern == pattern and (entry.flags & (BanFlag.PREFIX | BanFlag.SUFFIX)) == prefix_suffix:
                entry.flags = flags
                if level:
                    entry.level = level
                return

    _ban_entries.append(BanEntry(pattern=pattern, flags=flags, level=level))


class BanPermissionError(RuntimeError):
    """Raised when attempting to change a higher-trust ban entry."""


def _ensure_can_modify(pattern: str, trust_level: int | None) -> None:
    if trust_level is None:
        return
    for entry in _ban_entries:
        if entry.pattern == pattern and entry.level > trust_level:
            raise BanPermissionError("insufficient trust to modify ban")


def add_banned_host(
    host: str,
    *,
    flags: Iterable[BanFlag] | BanFlag | None = None,
    level: int = 0,
    permanent: bool = True,
    trust_level: int | None = None,
) -> None:
    pattern, wildcard_flags = _parse_host_pattern(host)
    if not pattern:
        return

    _ensure_can_modify(pattern, trust_level)

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
    if permanent:
        combined |= BanFlag.PERMANENT
    if not level and trust_level:
        level = trust_level
    _store_entry(pattern, combined, level, replace_existing=True)


def remove_banned_host(host: str, *, trust_level: int | None = None) -> bool:
    pattern, _ = _parse_host_pattern(host)
    if not pattern:
        return False
    _ensure_can_modify(pattern, trust_level)
    before = len(_ban_entries)
    _ban_entries[:] = [entry for entry in _ban_entries if entry.pattern != pattern]
    return len(_ban_entries) != before


def is_host_banned(host: str | None, ban_type: BanFlag = BanFlag.ALL) -> bool:
    if not host:
        return False
    for entry in _ban_entries:
        if not entry.flags & ban_type:
            continue
        if entry.matches(host):
            return True
    return False


def get_ban_entries() -> list[BanEntry]:
    return list(_ban_entries)


def add_banned_account(username: str) -> None:
    _banned_accounts.add(username.strip().lower())


def remove_banned_account(username: str) -> None:
    _banned_accounts.discard(username.strip().lower())


def is_account_banned(username: str | None) -> bool:
    if not username:
        return False
    return username.strip().lower() in _banned_accounts


def get_banned_accounts() -> list[str]:
    return sorted(_banned_accounts)


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


def save_account_bans_file(path: Path | str | None = None) -> None:
    target = _resolve_path(path, account=True)
    if not _banned_accounts:
        try:
            if target.exists():
                target.unlink()
        except OSError:
            pass
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fp:
        for username in sorted(_banned_accounts):
            fp.write(f"{username}\n")


def load_account_bans_file(path: Path | str | None = None) -> int:
    target = _resolve_path(path, account=True)
    _banned_accounts.clear()
    if not target.exists():
        return 0
    count = 0
    with target.open("r", encoding="utf-8") as fp:
        for raw in fp:
            username = raw.strip().lower()
            if not username:
                continue
            _banned_accounts.add(username)
            count += 1
    return count


def save_bans_file(path: Path | str | None = None) -> None:
    target = _resolve_path(path)
    persistent = [entry for entry in _ban_entries if entry.flags & BanFlag.PERMANENT]
    save_account_bans_file(path)
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
    target = _resolve_path(path)
    if not target.exists():
        load_account_bans_file(path)
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
            if not flags or not (flags & BanFlag.PERMANENT):
                continue
            _store_entry(pattern, flags, level, replace_existing=False)
            count += 1
    load_account_bans_file(path)
    return count
