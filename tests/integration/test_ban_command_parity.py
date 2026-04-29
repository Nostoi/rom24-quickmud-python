"""ROM ban.c parity tests for `_render_ban_listing`, `_apply_ban`, and `BanEntry.matches`.

Mirrors `src/ban.c` (ROM 2.4b6). One test per BAN-NNN gap.
"""

from __future__ import annotations

import pytest

from mud.commands.admin_commands import _apply_ban, _render_ban_listing
from mud.models.character import Character
from mud.security import bans
from mud.security.bans import BanEntry, BanFlag


@pytest.fixture(autouse=True)
def _reset_bans():
    bans.clear_all_bans()
    yield
    bans.clear_all_bans()


def _make_admin(name: str = "Admin", trust: int = 60) -> Character:
    char = Character(name=name)
    char.trust = trust
    char.level = trust
    char.is_admin = True
    return char


def test_banlist_level_column_left_aligned():
    """BAN-001 — ROM `_render_ban_listing` uses `%-3d` (left-aligned)."""
    bans.add_banned_host("foo.com*", flags=BanFlag.ALL, level=60, permanent=True)
    output = _render_ban_listing()
    # mirrors ROM src/ban.c:164 — "%-12s    %-3d  %-7s  %s"
    # "foo.com*" pattern → "foo.com" + suffix asterisk → printable "foo.com*" (8 chars)
    # Pattern column is 12 wide, then 4 spaces, then level 3 wide LEFT-aligned, then 2 spaces, then type 7 wide, then 2 spaces, then status.
    # Level "60" left-aligned in 3 chars → "60 " (trailing space).
    assert "60   all    " in output or "60   all" in output
    # Reject right-aligned " 60" with leading space before "all".
    assert " 60  all" not in output


def test_banlist_type_text_empty_when_no_type_bits():
    """BAN-002 — ROM emits empty type-text when NEWBIES/PERMIT/ALL all clear."""
    # Construct an entry with only PREFIX set (no type bit). ROM ban_site
    # cannot create this directly, but load_bans/manual entries can.
    bans.clear_all_bans()
    bans._ban_entries.append(
        BanEntry(pattern="weird", flags=BanFlag.PREFIX | BanFlag.PERMANENT, level=60)
    )
    output = _render_ban_listing()
    # mirrors ROM src/ban.c:166-168 — when none of NEWBIES/PERMIT/ALL is set, "" is printed
    # In Python listing, the column should not say "all".
    # Find the data line for "weird".
    data_line = next(line for line in output.splitlines() if "weird" in line)
    assert " all " not in data_line and not data_line.rstrip().endswith("all")


def test_apply_ban_accepts_single_letter_type_abbreviation():
    """BAN-003 — ROM accepts `a`/`n`/`p` via str_prefix(arg2, "all"/"newbies"/"permit")."""
    char = _make_admin()
    # mirrors ROM src/ban.c:180-191 — `str_prefix(arg2, "newbies")` returns 0 for arg2="n"
    result = _apply_ban(char, "evil.com n", permanent=False)
    assert "has been banned" in result
    entries = bans.get_ban_entries()
    assert len(entries) == 1
    assert entries[0].flags & BanFlag.NEWBIES, f"expected NEWBIES bit, got {entries[0].flags!r}"


def test_check_ban_skips_entries_without_prefix_or_suffix():
    """BAN-004 — ROM `check_ban` only matches entries with PREFIX or SUFFIX flag set."""
    bans.clear_all_bans()
    # mirrors ROM src/ban.c:104-132 — entries lacking both PREFIX and SUFFIX never match
    bans._ban_entries.append(
        BanEntry(pattern="exact.host", flags=BanFlag.ALL | BanFlag.PERMANENT, level=60)
    )
    assert bans.is_host_banned("exact.host", BanFlag.ALL) is False
