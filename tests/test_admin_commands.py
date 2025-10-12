import pytest

from mud.commands.admin_commands import (
    cmd_allow,
    cmd_ban,
    cmd_deny,
    cmd_holylight,
    cmd_incognito,
    cmd_newlock,
    cmd_permban,
    cmd_wizlock,
)
from mud.models.character import Character, character_registry
from mud.models.constants import PlayerFlag, RoomFlag, Sex
from mud.models.room import Room
from mud.net.session import SESSIONS, Session
from mud.security import bans
from mud.security.bans import BanFlag
from mud.world.world_state import (
    is_newlock_enabled,
    is_wizlock_enabled,
    reset_lockdowns,
)
from mud.wiznet import WiznetFlag
from mud.world.vision import can_see_character


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


def test_wizlock_command_toggles_and_notifies():
    reset_lockdowns()
    admin = _make_admin(60)
    admin.name = "Admin"
    admin.is_admin = True
    watcher = _make_admin(60)
    watcher.name = "Watcher"
    watcher.is_admin = True
    watcher.wiznet = int(WiznetFlag.WIZ_ON)
    watcher.messages = []
    try:
        character_registry.extend([admin, watcher])
        assert cmd_wizlock(admin, "") == "Game wizlocked."
        assert is_wizlock_enabled()
        assert any("has wizlocked the game" in msg for msg in watcher.messages)
        watcher.messages.clear()
        assert cmd_wizlock(admin, "") == "Game un-wizlocked."
        assert not is_wizlock_enabled()
        assert any("removes wizlock" in msg for msg in watcher.messages)
    finally:
        reset_lockdowns()
        for ch in (admin, watcher):
            if ch in character_registry:
                character_registry.remove(ch)


def test_newlock_command_toggles_and_notifies():
    reset_lockdowns()
    admin = _make_admin(60)
    admin.name = "Admin"
    admin.is_admin = True
    watcher = _make_admin(60)
    watcher.name = "Watcher"
    watcher.is_admin = True
    watcher.wiznet = int(WiznetFlag.WIZ_ON)
    watcher.messages = []
    try:
        character_registry.extend([admin, watcher])
        assert cmd_newlock(admin, "") == "New characters have been locked out."
        assert is_newlock_enabled()
        assert any("locks out new characters" in msg for msg in watcher.messages)
        watcher.messages.clear()
        assert cmd_newlock(admin, "") == "Newlock removed."
        assert not is_newlock_enabled()
        assert any("allows new characters back in" in msg for msg in watcher.messages)
    finally:
        reset_lockdowns()
        for ch in (admin, watcher):
            if ch in character_registry:
                character_registry.remove(ch)


def test_incognito_command_toggles_and_announces():
    room = Room(vnum=42, name="Hidden Alcove")
    admin = _make_admin(60)
    admin.name = "Immortal"
    admin.is_admin = True
    admin.sex = int(Sex.MALE)
    watcher = _make_admin(60)
    watcher.name = "Watcher"
    watcher.is_admin = True
    watcher.messages = []
    watcher.sex = int(Sex.FEMALE)

    room.add_character(admin)
    room.add_character(watcher)

    try:
        # Default toggle cloaks to trust level
        watcher.messages.clear()
        response = cmd_incognito(admin, "")
        assert response == "You cloak your presence."
        assert admin.incog_level == admin.trust
        assert watcher.messages == ["Immortal cloaks his presence."]

        # Explicit level clamps and resets reply target
        watcher.messages.clear()
        admin.reply = watcher
        response = cmd_incognito(admin, "55")
        assert response == "You cloak your presence."
        assert admin.incog_level == 55
        assert admin.reply is None
        assert watcher.messages == ["Immortal cloaks his presence."]

        # Disallow invalid levels
        assert (
            cmd_incognito(admin, "1")
            == "Incog level must be between 2 and your level."
        )
        assert (
            cmd_incognito(admin, "999")
            == "Incog level must be between 2 and your level."
        )

        # Toggling without args removes the cloak and announces to the room
        watcher.messages.clear()
        response = cmd_incognito(admin, "")
        assert response == "You are no longer cloaked."
        assert admin.incog_level == 0
        assert watcher.messages == ["Immortal is no longer cloaked."]
    finally:
        room.remove_character(admin)
        room.remove_character(watcher)
        for ch in (admin, watcher):
            if ch in character_registry:
                character_registry.remove(ch)


def test_holylight_command_toggles_flag():
    room = Room(vnum=51, name="Gloom", room_flags=int(RoomFlag.ROOM_DARK), light=0)
    admin = _make_admin(60)
    admin.name = "Immortal"
    admin.is_admin = True
    admin.act = 0
    target = Character(name="Scout", is_npc=False, level=10, trust=10)

    room.add_character(admin)
    room.add_character(target)

    try:
        assert cmd_holylight(admin, "") == "Holy light mode on."
        assert admin.act & int(PlayerFlag.HOLYLIGHT)
        assert can_see_character(admin, target)

        assert cmd_holylight(admin, "") == "Holy light mode off."
        assert not admin.act & int(PlayerFlag.HOLYLIGHT)
        assert not can_see_character(admin, target)
    finally:
        room.remove_character(admin)
        room.remove_character(target)
