from dataclasses import replace

import pytest

from mud.commands.admin_commands import (
    cmd_allow,
    cmd_ban,
    cmd_deny,
    cmd_holylight,
    cmd_incognito,
    cmd_newlock,
    cmd_permban,
    cmd_banlist,
    cmd_qmconfig,
    cmd_wizlock,
)
from mud.config import (
    config_path,
    get_qmconfig,
    load_qmconfig,
    set_ansicolor,
    set_ansiprompt,
    set_config_path,
    set_ip_address,
    set_telnetga,
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


ROM_NEWLINE = "\n\r"


@pytest.fixture(autouse=True)
def clear_bans():
    bans.clear_all_bans()
    yield
    bans.clear_all_bans()


@pytest.fixture
def restore_qmconfig():
    snapshot = replace(get_qmconfig())
    original_path = config_path()
    try:
        yield
    finally:
        set_config_path(original_path)
        set_ansiprompt(snapshot.ansiprompt)
        set_ansicolor(snapshot.ansicolor)
        set_telnetga(snapshot.telnetga)
        set_ip_address(snapshot.ip_address)


def _make_admin(level: int) -> Character:
    return Character(name="Imm", is_npc=False, level=level, trust=level)


def test_qmconfig_toggles_update_runtime(tmp_path, restore_qmconfig):
    admin = _make_admin(60)
    config_file = tmp_path / "qmconfig.rc"
    config_file.write_text(
        "Ansiprompt 0\nAnsicolor 1\nTelnetga 0\n",
        encoding="utf-8",
    )

    set_config_path(config_file)
    set_ansiprompt(True)
    set_ansicolor(False)
    set_telnetga(True)

    help_text = cmd_qmconfig(admin, "")
    assert "Valid qmconfig options" in help_text
    assert help_text.endswith(ROM_NEWLINE)

    response = cmd_qmconfig(admin, "ansiprompt off")
    assert response == "New logins will not get an ANSI color prompt." + ROM_NEWLINE
    assert get_qmconfig().ansiprompt is False

    response = cmd_qmconfig(admin, "ansicolor on")
    assert response == "New players will have color enabled." + ROM_NEWLINE
    assert get_qmconfig().ansicolor is True

    response = cmd_qmconfig(admin, "telnetga off")
    assert response == "Telnet GA will be disabled for new players." + ROM_NEWLINE
    assert get_qmconfig().telnetga is False

    show_output = cmd_qmconfig(admin, "show")
    assert "ANSI prompt: {ROFF{x" in show_output
    assert "ANSI color : {GON{x" in show_output
    assert "Telnet GA  : {ROFF{x" in show_output
    assert show_output.endswith(ROM_NEWLINE)

    cmd_qmconfig(admin, "ansiprompt on")
    cmd_qmconfig(admin, "ansicolor off")
    cmd_qmconfig(admin, "telnetga on")

    response = cmd_qmconfig(admin, "read")
    assert response == "Configuration reloaded from qmconfig.rc."
    reloaded = get_qmconfig()
    assert reloaded.ansiprompt is False
    assert reloaded.ansicolor is True
    assert reloaded.telnetga is False

    invalid = cmd_qmconfig(admin, "ansiprompt maybe")
    assert invalid == 'Valid arguments are "on" and "off".' + ROM_NEWLINE


def test_qmconfig_toggle_messages_include_newline(restore_qmconfig):
    admin = _make_admin(60)

    responses = []

    set_ansiprompt(False)
    responses.append(cmd_qmconfig(admin, "ansiprompt on"))
    set_ansiprompt(True)
    responses.append(cmd_qmconfig(admin, "ansiprompt off"))

    set_ansicolor(False)
    responses.append(cmd_qmconfig(admin, "ansicolor on"))
    set_ansicolor(True)
    responses.append(cmd_qmconfig(admin, "ansicolor off"))

    set_telnetga(False)
    responses.append(cmd_qmconfig(admin, "telnetga on"))
    set_telnetga(True)
    responses.append(cmd_qmconfig(admin, "telnetga off"))

    responses.append(cmd_qmconfig(admin, "ansiprompt maybe"))

    for response in responses:
        assert response.endswith(ROM_NEWLINE)


def test_qmconfig_abbreviations(tmp_path, restore_qmconfig):
    admin = _make_admin(60)
    config_file = tmp_path / "qmconfig.rc"
    config_file.write_text(
        "Ansiprompt 0\nAnsicolor 1\nTelnetga 1\n",
        encoding="utf-8",
    )

    set_config_path(config_file)
    set_ansiprompt(False)
    set_ansicolor(True)
    set_telnetga(True)

    response = cmd_qmconfig(admin, "ansiprompt o")
    assert response == "New logins will now get an ANSI color prompt." + ROM_NEWLINE
    assert get_qmconfig().ansiprompt is True

    response = cmd_qmconfig(admin, "ansicolor of")
    assert response == "New players will not have color enabled." + ROM_NEWLINE
    assert get_qmconfig().ansicolor is False

    response = cmd_qmconfig(admin, "ansicolor")
    assert response == "New players will have color enabled." + ROM_NEWLINE
    assert get_qmconfig().ansicolor is True

    invalid = cmd_qmconfig(admin, "telnetga nope")
    assert invalid == 'Valid arguments are "on" and "off".' + ROM_NEWLINE
    assert get_qmconfig().telnetga is True

    response = cmd_qmconfig(admin, "telnetga Of")
    assert response == "Telnet GA will be disabled for new players." + ROM_NEWLINE
    assert get_qmconfig().telnetga is False


def test_qmconfig_option_abbreviations(tmp_path, restore_qmconfig):
    admin = _make_admin(60)
    config_file = tmp_path / "qmconfig.rc"
    config_file.write_text(
        "Ansiprompt 0\nAnsicolor 1\nTelnetga 0\n",
        encoding="utf-8",
    )

    set_config_path(config_file)
    set_ansiprompt(True)
    set_ansicolor(False)
    set_telnetga(True)

    show_output = cmd_qmconfig(admin, "sh")
    assert "ANSI prompt" in show_output

    response = cmd_qmconfig(admin, "ansi off")
    assert response == "New logins will not get an ANSI color prompt." + ROM_NEWLINE
    assert get_qmconfig().ansiprompt is False

    response = cmd_qmconfig(admin, "ansic on")
    assert response == "New players will have color enabled." + ROM_NEWLINE
    assert get_qmconfig().ansicolor is True

    response = cmd_qmconfig(admin, "te off")
    assert response == "Telnet GA will be disabled for new players." + ROM_NEWLINE
    assert get_qmconfig().telnetga is False

    reload = cmd_qmconfig(admin, "r")
    assert reload == "Configuration reloaded from qmconfig.rc."
    reloaded = get_qmconfig()
    assert reloaded.ansiprompt is False
    assert reloaded.ansicolor is True
    assert reloaded.telnetga is False

    invalid = cmd_qmconfig(admin, "mystery on")
    assert invalid == "I have no clue what you are trying to do..." + ROM_NEWLINE


def test_qmconfig_rejects_non_rom_synonyms(restore_qmconfig):
    admin = _make_admin(60)

    set_ansiprompt(False)
    invalid_yes = cmd_qmconfig(admin, "ansiprompt yes")
    assert invalid_yes == 'Valid arguments are "on" and "off".' + ROM_NEWLINE
    assert get_qmconfig().ansiprompt is False

    set_ansicolor(True)
    invalid_true = cmd_qmconfig(admin, "ansicolor true")
    assert invalid_true == 'Valid arguments are "on" and "off".' + ROM_NEWLINE
    assert get_qmconfig().ansicolor is True

    set_telnetga(True)
    invalid_numeric = cmd_qmconfig(admin, "telnetga 0")
    assert invalid_numeric == 'Valid arguments are "on" and "off".' + ROM_NEWLINE
    assert get_qmconfig().telnetga is True


def test_qmconfig_loader_stops_at_end_marker(tmp_path, restore_qmconfig):
    config_file = tmp_path / "qmconfig.rc"
    config_file.write_text(
        "Ansicolor 0\nEND\nAnsicolor 1\n",
        encoding="utf-8",
    )

    set_config_path(config_file)
    set_ansicolor(True)

    load_qmconfig()

    assert get_qmconfig().ansicolor is False


def test_qmconfig_loader_ignores_trailing_after_end(tmp_path, restore_qmconfig):
    config_file = tmp_path / "qmconfig.rc"
    config_file.write_text(
        "Ansiprompt 0\nEND   * trailing comment\nTelnetga 0\n",
        encoding="utf-8",
    )

    set_config_path(config_file)
    set_ansiprompt(True)
    set_telnetga(True)

    load_qmconfig()

    config = get_qmconfig()
    assert config.ansiprompt is False
    assert config.telnetga is True


def test_qmconfig_loader_accepts_nonzero_numeric_truthy(tmp_path, restore_qmconfig):
    config_file = tmp_path / "qmconfig.rc"
    config_file.write_text(
        "Ansiprompt 0\nAnsicolor 2\nTelnetga -1\nEND\n",
        encoding="utf-8",
    )

    set_config_path(config_file)
    set_ansiprompt(True)
    set_ansicolor(False)
    set_telnetga(False)

    load_qmconfig()

    config = get_qmconfig()
    assert config.ansiprompt is False
    assert config.ansicolor is True
    assert config.telnetga is True


def test_qmconfig_loader_handles_inline_comment_markers(tmp_path, restore_qmconfig):
    config_file = tmp_path / "qmconfig.rc"
    config_file.write_text(
        "Ansicolor 1# enable default colour\nTelnetga 0* disable ga\nAnsiprompt 0# prefer plain prompt\n",
        encoding="utf-8",
    )

    set_config_path(config_file)
    set_ansicolor(False)
    set_telnetga(True)
    set_ansiprompt(True)

    load_qmconfig()

    config = get_qmconfig()
    assert config.ansicolor is True
    assert config.telnetga is False
    assert config.ansiprompt is False


def test_ban_lists_entries_and_sets_newbie_flag():
    admin = _make_admin(60)

    assert cmd_ban(admin, "") == "No sites banned at this time." + ROM_NEWLINE

    response = cmd_ban(admin, "*midgaard newbies")
    assert response == "midgaard has been banned." + ROM_NEWLINE

    entries = bans.get_ban_entries()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.pattern == "midgaard"
    assert entry.flags & BanFlag.NEWBIES
    assert not entry.flags & BanFlag.PERMANENT

    listing = cmd_ban(admin, "")
    assert listing.endswith(ROM_NEWLINE)
    assert "Banned sites  level  type     status" in listing
    assert "*midgaard" in listing
    assert "newbies" in listing
    assert "temp" in listing


def test_ban_listing_orders_new_entries_first():
    admin = _make_admin(60)

    cmd_ban(admin, "first all")
    cmd_ban(admin, "second all")

    entries = bans.get_ban_entries()
    assert [entry.pattern for entry in entries[:2]] == ["second", "first"]

    listing = cmd_ban(admin, "")
    assert listing.endswith(ROM_NEWLINE)
    lines = [line for line in listing.split(ROM_NEWLINE) if line]
    assert lines[1].lstrip().startswith("second")
    assert lines[2].lstrip().startswith("first")


def test_ban_listing_uses_rom_newline():
    admin = _make_admin(60)

    cmd_ban(admin, "alpha all")
    cmd_permban(admin, "beta permit")

    listing = cmd_ban(admin, "")
    assert listing.endswith(ROM_NEWLINE)
    assert "\n" in listing and "\r" in listing
    assert "\n" not in listing.replace(ROM_NEWLINE, "")

    alias = cmd_banlist(admin, "")
    assert alias == listing

    segments = listing.split(ROM_NEWLINE)
    # Trailing ROM_NEWLINE yields final empty segment
    assert segments[-1] == ""
    for segment in segments[:-1]:
        assert segment


def test_ban_command_responses_use_rom_newline():
    admin = _make_admin(60)

    invalid = cmd_ban(admin, "example invalid")
    assert invalid == "Acceptable ban types are all, newbies, and permit." + ROM_NEWLINE

    missing = cmd_allow(admin, "")
    assert missing == "Remove which site from the ban list?" + ROM_NEWLINE

    cmd_ban(admin, "target all")
    unknown = cmd_allow(admin, "unknown.example")
    assert unknown == "Site is not banned." + ROM_NEWLINE


def test_allow_requires_canonical_host_token():
    admin = _make_admin(60)

    cmd_ban(admin, "*midgaard all")

    wildcard = cmd_allow(admin, "*midgaard")
    assert wildcard == "Site is not banned." + ROM_NEWLINE

    lifted = cmd_allow(admin, "midgaard")
    assert lifted == "Ban on midgaard lifted." + ROM_NEWLINE


def test_permban_and_allow_enforce_trust():
    high = _make_admin(60)
    low = _make_admin(50)

    response = cmd_permban(high, "locked.example all")
    assert response == "locked.example has been banned." + ROM_NEWLINE

    entries = bans.get_ban_entries()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.flags & BanFlag.PERMANENT
    assert entry.level == 60

    assert (
        cmd_ban(low, "locked.example")
        == "That ban was set by a higher power." + ROM_NEWLINE
    )

    assert (
        cmd_allow(low, "locked.example")
        == "You are not powerful enough to lift that ban." + ROM_NEWLINE
    )

    assert (
        cmd_allow(high, "locked.example")
        == "Ban on locked.example lifted." + ROM_NEWLINE
    )
    assert not bans.get_ban_entries()

    assert cmd_allow(high, "unknown.example") == "Site is not banned." + ROM_NEWLINE


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
