import pytest

from mud.commands.admin_commands import (
    cmd_allow,
    cmd_ban,
    cmd_deny,
    cmd_permban,
)
from mud.models.character import Character, character_registry
from mud.models.constants import PlayerFlag
from mud.net.session import SESSIONS, Session
from mud.security import bans
from mud.security.bans import BanFlag


@pytest.fixture(autouse=True)
def clear_bans():
    bans.clear_all_bans()
    yield
    bans.clear_all_bans()


def _make_admin(level: int) -> Character:
    return Character(name="Imm", is_npc=False, level=level, trust=level)


def test_ban_lists_entries_and_sets_newbie_flag():
    admin = _make_admin(60)

    assert cmd_ban(admin, "") == "No sites banned at this time."

    response = cmd_ban(admin, "*midgaard newbies")
    assert response == "midgaard has been banned."

    entries = bans.get_ban_entries()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.pattern == "midgaard"
    assert entry.flags & BanFlag.NEWBIES
    assert not entry.flags & BanFlag.PERMANENT

    listing = cmd_ban(admin, "")
    assert "Banned sites  level  type     status" in listing
    assert "*midgaard" in listing
    assert "newbies" in listing
    assert listing.endswith("temp")


def test_ban_listing_orders_new_entries_first():
    admin = _make_admin(60)

    cmd_ban(admin, "first all")
    cmd_ban(admin, "second all")

    entries = bans.get_ban_entries()
    assert [entry.pattern for entry in entries[:2]] == ["second", "first"]

    listing = cmd_ban(admin, "")
    lines = listing.splitlines()
    assert lines[1].lstrip().startswith("second")
    assert lines[2].lstrip().startswith("first")


def test_permban_and_allow_enforce_trust():
    high = _make_admin(60)
    low = _make_admin(50)

    response = cmd_permban(high, "locked.example all")
    assert response == "locked.example has been banned."

    entries = bans.get_ban_entries()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.flags & BanFlag.PERMANENT
    assert entry.level == 60

    assert cmd_ban(low, "locked.example") == "That ban was set by a higher power."

    assert (
        cmd_allow(low, "locked.example")
        == "You are not powerful enough to lift that ban."
    )

    assert cmd_allow(high, "locked.example") == "Ban on locked.example lifted."
    assert not bans.get_ban_entries()

    assert cmd_allow(high, "unknown.example") == "Site is not banned."


class DummyConnection:
    def __init__(self):
        self.sent: list[str] = []
        self.closed = False

    async def send_line(self, message: str) -> None:
        self.sent.append(message)

    async def close(self) -> None:
        self.closed = True


def test_deny_sets_plr_deny_and_kicks():
    admin = _make_admin(60)
    target = Character(name="Trouble", is_npc=False, level=10, trust=10)
    target.messages = []
    target.act = 0
    target.account_name = "trouble"
    character_registry.append(target)

    conn = DummyConnection()
    target.connection = conn
    session = Session(
        name=target.name or "",
        character=target,
        reader=None,  # type: ignore[arg-type]
        connection=conn,  # type: ignore[arg-type]
        account_name="trouble",
    )
    SESSIONS[session.name] = session

    try:
        response = cmd_deny(admin, "Trouble")
        assert response == "DENY set."
        assert target.act & int(PlayerFlag.DENY)
        assert "You are denied access!" in target.messages
        assert conn.closed
        assert bans.is_account_banned("trouble")

        response = cmd_deny(admin, "Trouble")
        assert response == "DENY removed."
        assert not target.act & int(PlayerFlag.DENY)
        assert any(
            msg == "You are granted access again." for msg in target.messages
        )
        assert not bans.is_account_banned("trouble")
    finally:
        SESSIONS.pop(session.name, None)
        if target in character_registry:
            character_registry.remove(target)
