from types import SimpleNamespace

import mud.persistence as persistence
from mud.commands.dispatcher import process_command
from mud.models.character import Character, character_registry
from mud.models.constants import Sex, LEVEL_IMMORTAL
import mud.net.connection as net_connection
from mud.net.connection import announce_wiznet_login, announce_wiznet_logout
from mud.wiznet import WiznetFlag, wiznet


ROM_NEWLINE = "\n\r"


def setup_function(_):
    character_registry.clear()


def _connected_character(**kwargs) -> Character:
    character = Character(**kwargs)
    character.desc = SimpleNamespace()
    return character


def _wiznet_payload(text: str, *, prefix: bool = False) -> str:
    prefix_token = "{Z--> " if prefix else "{Z"
    return prefix_token + text + ROM_NEWLINE + "{x"


def test_wiznet_flag_values():
    expected = {
        "WIZ_ON": 0x00000001,
        "WIZ_TICKS": 0x00000002,
        "WIZ_LOGINS": 0x00000004,
        "WIZ_SITES": 0x00000008,
        "WIZ_LINKS": 0x00000010,
        "WIZ_DEATHS": 0x00000020,
        "WIZ_RESETS": 0x00000040,
        "WIZ_MOBDEATHS": 0x00000080,
        "WIZ_FLAGS": 0x00000100,
        "WIZ_PENALTIES": 0x00000200,
        "WIZ_SACCING": 0x00000400,
        "WIZ_LEVELS": 0x00000800,
        "WIZ_SECURE": 0x00001000,
        "WIZ_SWITCHES": 0x00002000,
        "WIZ_SNOOPS": 0x00004000,
        "WIZ_RESTORE": 0x00008000,
        "WIZ_LOAD": 0x00010000,
        "WIZ_NEWBIE": 0x00020000,
        "WIZ_PREFIX": 0x00040000,  # Newly added
        "WIZ_SPAM": 0x00080000,  # Moved from 0x00040000
        "WIZ_DEBUG": 0x00100000,  # Moved from 0x00080000
        "WIZ_MEMORY": 0x00200000,
        "WIZ_SKILLS": 0x00400000,
        "WIZ_TESTING": 0x00800000,
    }
    for name, value in expected.items():
        assert getattr(WiznetFlag, name).value == value


def test_wiznet_broadcast_filtering():
    imm = _connected_character(
        name="Imm",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    mortal = _connected_character(
        name="Mort",
        is_admin=False,
        is_npc=False,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    character_registry.extend([imm, mortal])

    wiznet("Test message", WiznetFlag.WIZ_ON)

    assert _wiznet_payload("Test message") in imm.messages
    assert mortal.messages == []


def test_wiznet_broadcast_ignores_npcs():
    immortal_pc = _connected_character(
        name="ImmPC",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    immortal_npc = _connected_character(
        name="ImmNPC",
        is_admin=True,
        is_npc=True,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    character_registry.extend([immortal_pc, immortal_npc])

    wiznet("NPCs should not hear this", WiznetFlag.WIZ_ON)

    assert _wiznet_payload("NPCs should not hear this") in immortal_pc.messages
    assert immortal_npc.messages == []


def test_wiznet_broadcasts_include_rom_newline():
    imm = _connected_character(
        name="Imm",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_TICKS),
    )
    character_registry.append(imm)

    wiznet("Tick message", WiznetFlag.WIZ_TICKS)

    assert imm.messages
    message = imm.messages[0]
    assert message.count(ROM_NEWLINE) == 1
    newline_index = message.index(ROM_NEWLINE)
    assert message.endswith("{x")
    assert message[newline_index : newline_index + len(ROM_NEWLINE)] == ROM_NEWLINE


def test_wiznet_broadcast_color_reset_order():
    listener = _connected_character(
        name="Order", is_admin=True, is_npc=False, level=LEVEL_IMMORTAL
    )
    listener.wiznet = int(WiznetFlag.WIZ_ON)
    character_registry.append(listener)

    wiznet("ordering check", WiznetFlag.WIZ_ON)

    assert listener.messages
    message = listener.messages[-1]
    newline_index = message.index(ROM_NEWLINE)
    assert message.startswith("{Z")
    assert message.endswith("{x")
    assert message[newline_index + len(ROM_NEWLINE):] == "{x"


def test_wiznet_command_toggles_flag():
    imm = _connected_character(name="Imm", is_admin=True, is_npc=False, level=LEVEL_IMMORTAL)
    character_registry.append(imm)
    result = process_command(imm, "wiznet")
    assert imm.wiznet & int(WiznetFlag.WIZ_ON)
    assert "welcome to wiznet" in result.lower()


def test_wiznet_command_trailing_newlines():
    imm = _connected_character(name="Imm", is_admin=True, is_npc=False, level=60)
    character_registry.append(imm)

    responses = [
        process_command(imm, "wiznet"),
        process_command(imm, "wiznet"),
        process_command(imm, "wiznet on"),
        process_command(imm, "wiznet off"),
        process_command(imm, "wiznet status"),
        process_command(imm, "wiznet show"),
        process_command(imm, "wiznet ticks"),
        process_command(imm, "wiznet ticks"),
        process_command(imm, "wiznet mystery"),
    ]

    for response in responses:
        assert response.endswith(ROM_NEWLINE)


def test_wiznet_persistence(tmp_path):
    # Persist wiznet flags and ensure round-trip retains bitfield.
    persistence.PLAYERS_DIR = tmp_path
    from mud.world import initialize_world

    initialize_world("area/area.lst")
    imm = _connected_character(name="Imm", is_admin=True, is_npc=False, level=LEVEL_IMMORTAL)
    # Set multiple flags
    imm.wiznet = int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_TICKS | WiznetFlag.WIZ_DEBUG)
    persistence.save_character(imm)
    loaded = persistence.load_character("Imm")
    assert loaded is not None
    assert loaded.wiznet & int(WiznetFlag.WIZ_ON)
    assert loaded.wiznet & int(WiznetFlag.WIZ_TICKS)
    assert loaded.wiznet & int(WiznetFlag.WIZ_DEBUG)


def test_wiznet_requires_specific_flag():
    # Immortal with WIZ_ON only should not receive WIZ_TICKS messages.
    imm = _connected_character(
        name="Imm",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    character_registry.append(imm)
    wiznet("tick", WiznetFlag.WIZ_TICKS)
    assert all("tick" not in msg for msg in imm.messages)

    # After subscribing to WIZ_TICKS, should receive.
    imm.wiznet |= int(WiznetFlag.WIZ_TICKS)
    wiznet("tick2", WiznetFlag.WIZ_TICKS)
    assert any(msg == _wiznet_payload("tick2") for msg in imm.messages)


def test_wiznet_secure_flag_gating():
    # Without WIZ_SECURE bit, immortal should not receive WIZ_SECURE messages
    imm = _connected_character(
        name="Imm",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    character_registry.append(imm)
    wiznet("secure", WiznetFlag.WIZ_SECURE)
    assert all("secure" not in msg for msg in imm.messages)

    # After subscribing to WIZ_SECURE, message should be delivered
    imm.wiznet |= int(WiznetFlag.WIZ_SECURE)
    wiznet("secure2", WiznetFlag.WIZ_SECURE)
    assert any(msg == _wiznet_payload("secure2") for msg in imm.messages)


def test_wiznet_status_command():
    imm = _connected_character(name="Imm", is_admin=True, is_npc=False, level=60)
    character_registry.append(imm)

    # Test status with WIZ_ON off
    result = process_command(imm, "wiznet status")
    assert "off" in result

    # Turn on wiznet and add some flags
    imm.wiznet = int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_TICKS | WiznetFlag.WIZ_DEATHS)
    result = process_command(imm, "wiznet status")
    assert "off" not in result
    assert "ticks" in result
    assert "deaths" in result


def test_wiznet_status_includes_on_when_enabled():
    imm = _connected_character(name="Imm", is_admin=True, is_npc=False, level=60)
    imm.wiznet = int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_TICKS)
    character_registry.append(imm)

    result = process_command(imm, "wiznet status")
    lines = result.split(ROM_NEWLINE)
    body = lines[1] if len(lines) > 1 else ""
    assert "on" in body.split()


def test_wiznet_show_command():
    imm = _connected_character(name="Imm", is_admin=True, is_npc=False, level=60)
    character_registry.append(imm)

    result = process_command(imm, "wiznet show")
    assert "available to you" in result
    assert "on" in result  # Should show available options
    assert "ticks" in result


def test_wiznet_individual_flag_toggle():
    imm = _connected_character(name="Imm", is_admin=True, is_npc=False, level=60)
    character_registry.append(imm)

    # Test turning on a flag
    result = process_command(imm, "wiznet ticks")
    assert "will now see ticks" in result.lower()
    assert imm.wiznet & int(WiznetFlag.WIZ_TICKS)

    # Test turning off the same flag
    result = process_command(imm, "wiznet ticks")
    assert "will no longer see ticks" in result.lower()
    assert not (imm.wiznet & int(WiznetFlag.WIZ_TICKS))


def test_wiznet_on_off_commands():
    imm = _connected_character(name="Imm", is_admin=True, is_npc=False, level=LEVEL_IMMORTAL)
    character_registry.append(imm)

    # Test explicit "on"
    result = process_command(imm, "wiznet on")
    assert "welcome to wiznet" in result.lower()
    assert imm.wiznet & int(WiznetFlag.WIZ_ON)

    # Test explicit "off"
    result = process_command(imm, "wiznet off")
    assert "signing off" in result.lower()
    assert not (imm.wiznet & int(WiznetFlag.WIZ_ON))


def test_wiznet_allows_level_immortals_without_admin_flag():
    immortal = _connected_character(name="Sage", level=LEVEL_IMMORTAL, is_admin=False, is_npc=False)
    character_registry.append(immortal)

    response = process_command(immortal, "wiznet")
    assert "welcome to wiznet" in response.lower()
    assert immortal.wiznet & int(WiznetFlag.WIZ_ON)

    wiznet("Test immortal access", WiznetFlag.WIZ_ON)
    assert _wiznet_payload("Test immortal access") in immortal.messages

    mortal = _connected_character(name="Peasant", level=10, is_npc=False)
    character_registry.append(mortal)
    assert process_command(mortal, "wiznet") == "Huh?"


def test_wiznet_prefix_formatting():
    imm_with_prefix = _connected_character(
        name="ImmPrefix",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_PREFIX),
    )
    imm_without_prefix = _connected_character(
        name="ImmPlain",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    character_registry.extend([imm_with_prefix, imm_without_prefix])

    wiznet("Test prefix", WiznetFlag.WIZ_ON)

    # Check that prefix character gets formatted message
    assert imm_with_prefix.messages == [_wiznet_payload("Test prefix", prefix=True)]
    # Check that non-prefix character gets color-wrapped message without arrow
    assert imm_without_prefix.messages == [_wiznet_payload("Test prefix")]


def test_wiznet_act_formatting():
    sender = _connected_character(name="Kestrel", sex=Sex.FEMALE)
    prefix_listener = _connected_character(
        name="ImmPrefix",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LINKS | WiznetFlag.WIZ_PREFIX),
    )
    plain_listener = _connected_character(
        name="ImmPlain",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LINKS),
    )
    character_registry.extend([prefix_listener, plain_listener])

    try:
        wiznet(
            "$N groks the fullness of $S link.",
            sender,
            None,
            WiznetFlag.WIZ_LINKS,
            None,
            0,
        )
        wiznet(
            "$N answers '$t'",
            sender,
            "Ready",
            WiznetFlag.WIZ_LINKS,
            None,
            0,
        )
    finally:
        character_registry.clear()

    assert prefix_listener.messages == [
        _wiznet_payload("Kestrel groks the fullness of her link.", prefix=True),
        _wiznet_payload("Kestrel answers 'Ready'", prefix=True),
    ]
    assert plain_listener.messages == [
        _wiznet_payload("Kestrel groks the fullness of her link."),
        _wiznet_payload("Kestrel answers 'Ready'"),
    ]


def test_wiznet_act_uses_sender_pronouns():
    sender = _connected_character(
        name="Kestrel",
        sex=Sex.FEMALE,
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
    )
    listener = _connected_character(
        name="Watcher",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOGINS),
    )
    character_registry.append(listener)

    wiznet(
        "$n greets the staff. $e nods politely.",
        sender,
        None,
        WiznetFlag.WIZ_LOGINS,
        None,
        0,
    )

    assert listener.messages == [
        _wiznet_payload("Kestrel greets the staff. she nods politely.")
    ]


def test_wiznet_flag_skip_excludes_secure_listeners():
    sender = _connected_character(name="Archon", is_admin=True, is_npc=False, level=LEVEL_IMMORTAL)
    secure_listener = _connected_character(
        name="Sentinel",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        trust=LEVEL_IMMORTAL,
        wiznet=int(
            WiznetFlag.WIZ_ON
            | WiznetFlag.WIZ_LOAD
            | WiznetFlag.WIZ_SECURE
        ),
    )
    plain_listener = _connected_character(
        name="Chronicler",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        trust=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOAD),
    )

    character_registry.extend([secure_listener, plain_listener])

    try:
        wiznet(
            "$N loads $p.",
            sender,
            "ancient relic",
            WiznetFlag.WIZ_LOAD,
            WiznetFlag.WIZ_SECURE,
            LEVEL_IMMORTAL,
        )
    finally:
        character_registry.clear()

    assert secure_listener.messages == []
    assert plain_listener.messages == [_wiznet_payload("Archon loads ancient relic.")]


def test_wiznet_min_level_blocks_low_trust_listeners():
    high_trust = _connected_character(
        name="HighTrust",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOAD),
    )
    low_trust = _connected_character(
        name="LowTrust",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        trust=40,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOAD),
    )

    character_registry.extend([high_trust, low_trust])

    wiznet(
        "rare artifact arrives.",
        None,
        None,
        WiznetFlag.WIZ_LOAD,
        None,
        50,
    )

    assert high_trust.messages == [_wiznet_payload("rare artifact arrives.")]
    assert low_trust.messages == []

    character_registry.clear()


def test_wiznet_trust_allows_secure_options():
    trusted = _connected_character(
        name="Trusted",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    low_trust = _connected_character(
        name="Low",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    character_registry.extend([trusted, low_trust])

    # Elevated trust should expose secure option despite lower base level.
    show_output = process_command(trusted, "wiznet show")
    assert "secure" in show_output

    toggle_result = process_command(trusted, "wiznet secure")
    assert "will now see secure" in toggle_result.lower()
    assert trusted.wiznet & int(WiznetFlag.WIZ_SECURE)

    trusted.messages.clear()
    wiznet("secure notice", None, None, WiznetFlag.WIZ_SECURE, None, 60)
    assert trusted.messages == [_wiznet_payload("secure notice")]

    # Base level without additional trust should not see or toggle secure.
    show_low = process_command(low_trust, "wiznet show")
    assert "secure" not in show_low

    toggle_low = process_command(low_trust, "wiznet secure")
    assert toggle_low == "No such option." + ROM_NEWLINE
    wiznet("secure notice", None, None, WiznetFlag.WIZ_SECURE, None, 60)
    assert all("secure notice" not in msg for msg in low_trust.messages)


def test_wiznet_logins_channel_broadcasts():
    watcher = _connected_character(
        name="Watcher",
        is_admin=True,
        is_npc=False,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOGINS | WiznetFlag.WIZ_PREFIX),
    )
    skip_sites = _connected_character(
        name="Sites",
        is_admin=True,
        is_npc=False,
        level=60,
        trust=60,
        wiznet=int(
            WiznetFlag.WIZ_ON
            | WiznetFlag.WIZ_LOGINS
            | WiznetFlag.WIZ_SITES
            | WiznetFlag.WIZ_PREFIX
        ),
    )
    low_trust = _connected_character(
        name="Low",
        is_admin=True,
        is_npc=False,
        level=50,
        trust=50,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOGINS | WiznetFlag.WIZ_PREFIX),
    )
    logging_char = _connected_character(
        name="Artemis",
        level=60,
        trust=60,
        is_admin=True,
        is_npc=False,
    )

    character_registry.extend([watcher, skip_sites, low_trust, logging_char])

    announce_wiznet_login(logging_char, host="aurora.example")

    assert _wiznet_payload(
        "Artemis has left real life behind.", prefix=True
    ) in watcher.messages
    assert _wiznet_payload(
        "Artemis@aurora.example has connected.", prefix=True
    ) in skip_sites.messages
    assert not any("has left real life behind" in msg for msg in skip_sites.messages)
    assert low_trust.messages == []

    watcher.messages.clear()
    skip_sites.messages.clear()
    low_trust.messages.clear()

    announce_wiznet_logout(logging_char)

    assert _wiznet_payload(
        "Artemis rejoins the real world.", prefix=True
    ) in watcher.messages
    assert _wiznet_payload(
        "Artemis rejoins the real world.", prefix=True
    ) in skip_sites.messages
    assert low_trust.messages == []


def test_reconnect_wiz_links_ignores_reconnect_trust_gate(monkeypatch):
    reconnecting = _connected_character(
        name="Hero",
        is_admin=True,
        is_npc=False,
        level=60,
        trust=60,
        sex=Sex.MALE,
    )
    broadcasted: list[str] = []
    reconnecting.connection = SimpleNamespace(peer_host="midgaard.example")
    reconnecting.desc = SimpleNamespace(connection=reconnecting.connection)
    reconnecting.room = SimpleNamespace(
        broadcast=lambda message, exclude=None: broadcasted.append(message)
    )

    high_listener = _connected_character(
        name="ImmHigh",
        is_admin=True,
        is_npc=False,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LINKS),
    )
    low_listener = _connected_character(
        name="ImmLow",
        is_admin=True,
        is_npc=False,
        level=40,
        trust=40,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LINKS),
    )
    uninterested = _connected_character(
        name="ImmPlain",
        is_admin=True,
        is_npc=False,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    high_listener.connection = SimpleNamespace()
    low_listener.connection = SimpleNamespace()
    uninterested.connection = SimpleNamespace()

    character_registry.extend([high_listener, low_listener, uninterested])

    logged: list[str] = []

    def _capture(message: str) -> str:
        logged.append(message)
        return message

    monkeypatch.setattr(net_connection, "log_game_event", _capture)

    try:
        net_connection._broadcast_reconnect_notifications(reconnecting)
    finally:
        character_registry.clear()

    expected = _wiznet_payload("Hero groks the fullness of his link.")
    assert broadcasted == ["Hero has reconnected."]
    assert high_listener.messages == [expected]
    assert low_listener.messages == [expected]
    assert uninterested.messages == []
    assert logged == ["Hero@midgaard.example reconnected."]


def test_wiz_sites_announces_successful_login(capsys):
    prefix_listener = _connected_character(
        name="Prefix",
        is_admin=True,
        is_npc=False,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES | WiznetFlag.WIZ_PREFIX),
    )
    plain_listener = _connected_character(
        name="Plain",
        is_admin=True,
        is_npc=False,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES),
    )
    uninterested = _connected_character(
        name="NoSites",
        is_admin=True,
        is_npc=False,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    low_trust = _connected_character(
        name="Low",
        is_admin=True,
        is_npc=False,
        level=50,
        trust=40,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES),
    )
    logging_char = _connected_character(
        name="Lyra",
        level=60,
        trust=60,
        is_admin=True,
        is_npc=False,
    )

    character_registry.extend(
        [prefix_listener, plain_listener, uninterested, low_trust, logging_char]
    )

    announce_wiznet_login(logging_char, host="academy.example")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Lyra@academy.example has connected." in captured.err

    assert plain_listener.messages == [
        _wiznet_payload("Lyra@academy.example has connected.")
    ]
    assert _wiznet_payload(
        "Lyra@academy.example has connected.", prefix=True
    ) in prefix_listener.messages
    assert all(
        "Lyra@academy.example has connected." not in msg
        for msg in uninterested.messages
    )
    assert low_trust.messages == []


def test_announce_wiznet_login_without_host_broadcasts_sites(capsys):
    prefix_listener = _connected_character(
        name="Prefix",
        is_admin=True,
        is_npc=False,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES | WiznetFlag.WIZ_PREFIX),
    )
    plain_listener = _connected_character(
        name="Plain",
        is_admin=True,
        is_npc=False,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES),
    )
    uninterested = _connected_character(
        name="NoSites",
        is_admin=True,
        is_npc=False,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    logging_char = _connected_character(
        name="Lyra",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        trust=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOGINS),
    )

    character_registry.extend(
        [prefix_listener, plain_listener, uninterested, logging_char]
    )

    announce_wiznet_login(logging_char, host="   ")

    captured = capsys.readouterr()
    assert captured.out == ""

    expected = _wiznet_payload("Lyra@(unknown) has connected.")
    assert plain_listener.messages == [expected]
    assert _wiznet_payload("Lyra@(unknown) has connected.", prefix=True) in prefix_listener.messages
    assert uninterested.messages == []


def test_announce_wiznet_login_includes_logging_immortal(capsys):
    logging_char = _connected_character(
        name="Lyra",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        trust=LEVEL_IMMORTAL,
        wiznet=int(
            WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOGINS | WiznetFlag.WIZ_SITES
        ),
    )
    fellow_listener = _connected_character(
        name="Watcher",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        trust=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES),
    )

    character_registry.extend([logging_char, fellow_listener])

    announce_wiznet_login(logging_char, host=None)

    captured = capsys.readouterr()
    assert captured.out == ""

    expected = _wiznet_payload("Lyra@(unknown) has connected.")
    assert expected in logging_char.messages
    assert expected in fellow_listener.messages


def test_announce_wiznet_login_logs_connection(monkeypatch):
    captured: list[str] = []

    def _capture(message: str) -> None:
        captured.append(message)

    monkeypatch.setattr(net_connection, "log_game_event", _capture)

    logging_char = _connected_character(
        name="Artemis",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOGINS),
    )

    announce_wiznet_login(logging_char, host="aurora.example")

    assert captured == ["Artemis@aurora.example has connected."]


def test_announce_wiznet_login_without_extra_stdout(capsys):
    logging_char = _connected_character(
        name="Lyra",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        trust=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOGINS | WiznetFlag.WIZ_SITES),
    )
    site_listener = _connected_character(
        name="Watcher",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        trust=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES),
    )
    newbie_listener = _connected_character(
        name="Greeter",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        trust=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_NEWBIE | WiznetFlag.WIZ_SITES),
    )

    character_registry.extend([logging_char, site_listener, newbie_listener])

    announce_wiznet_login(logging_char, host="aurora.example")

    login_capture = capsys.readouterr()
    assert login_capture.out == ""
    assert "Lyra@aurora.example has connected." in login_capture.err

    site_payload = _wiznet_payload("Lyra@aurora.example has connected.")
    assert site_payload in site_listener.messages
    assert site_payload in newbie_listener.messages

    net_connection.announce_wiznet_new_player(
        "Nova", host="nebula.example", trust_level=LEVEL_IMMORTAL, sex=Sex.FEMALE
    )

    new_capture = capsys.readouterr()
    assert new_capture.out == ""
    assert "Nova@nebula.example new player." in new_capture.err

    newbie_payload = _wiznet_payload("Newbie alert!  Nova sighted.")
    assert newbie_payload in newbie_listener.messages
    site_new_payload = _wiznet_payload("Nova@nebula.example new player.")
    assert site_new_payload in site_listener.messages


def test_announce_wiznet_logout_logs_quit(monkeypatch):
    captured: list[str] = []

    def _capture(message: str) -> None:
        captured.append(message)

    monkeypatch.setattr(net_connection, "log_game_event", _capture)

    logging_char = _connected_character(
        name="Artemis",
        is_admin=True,
        is_npc=False,
        level=LEVEL_IMMORTAL,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOGINS),
    )

    announce_wiznet_logout(logging_char)

    assert captured == ["Artemis has quit."]


def test_announce_wiznet_new_player_logs_creation(monkeypatch):
    captured: list[str] = []

    def _capture(message: str) -> None:
        captured.append(message)

    monkeypatch.setattr(net_connection, "log_game_event", _capture)

    net_connection.announce_wiznet_new_player(
        "Lyra", host="academy.example", trust_level=1, sex=Sex.FEMALE
    )

    assert captured == ["Lyra@academy.example new player."]



def test_announce_wiznet_new_player_without_host_broadcasts_sites(capsys):
    prefix_listener = _connected_character(
        name="Prefix",
        is_admin=True,
        is_npc=False,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES | WiznetFlag.WIZ_PREFIX),
    )
    plain_listener = _connected_character(
        name="Plain",
        is_admin=True,
        is_npc=False,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES),
    )
    character_registry.extend([prefix_listener, plain_listener])

    net_connection.announce_wiznet_new_player(
        "Lyra", host="   ", trust_level=1, sex=Sex.FEMALE
    )

    captured = capsys.readouterr()
    assert captured.out == ""

    expected = _wiznet_payload("Lyra@(unknown) new player.")
    assert plain_listener.messages == [expected]
    assert _wiznet_payload("Lyra@(unknown) new player.", prefix=True) in prefix_listener.messages
