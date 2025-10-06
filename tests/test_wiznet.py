import mud.persistence as persistence
from mud.commands.dispatcher import process_command
from mud.models.character import Character, character_registry
from mud.models.constants import Sex
from mud.net.connection import announce_wiznet_login, announce_wiznet_logout
from mud.wiznet import WiznetFlag, wiznet


def setup_function(_):
    character_registry.clear()


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
    imm = Character(name="Imm", is_admin=True, wiznet=int(WiznetFlag.WIZ_ON))
    mortal = Character(name="Mort", is_admin=False, wiznet=int(WiznetFlag.WIZ_ON))
    character_registry.extend([imm, mortal])

    wiznet("Test message", WiznetFlag.WIZ_ON)

    assert "{ZTest message{x" in imm.messages
    assert mortal.messages == []


def test_wiznet_command_toggles_flag():
    imm = Character(name="Imm", is_admin=True)
    character_registry.append(imm)
    result = process_command(imm, "wiznet")
    assert imm.wiznet & int(WiznetFlag.WIZ_ON)
    assert "welcome to wiznet" in result.lower()


def test_wiznet_persistence(tmp_path):
    # Persist wiznet flags and ensure round-trip retains bitfield.
    persistence.PLAYERS_DIR = tmp_path
    from mud.world import initialize_world

    initialize_world("area/area.lst")
    imm = Character(name="Imm", is_admin=True)
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
    imm = Character(name="Imm", is_admin=True, wiznet=int(WiznetFlag.WIZ_ON))
    character_registry.append(imm)
    wiznet("tick", WiznetFlag.WIZ_TICKS)
    assert all("tick" not in msg for msg in imm.messages)

    # After subscribing to WIZ_TICKS, should receive.
    imm.wiznet |= int(WiznetFlag.WIZ_TICKS)
    wiznet("tick2", WiznetFlag.WIZ_TICKS)
    assert any(msg == "{Ztick2{x" for msg in imm.messages)


def test_wiznet_secure_flag_gating():
    # Without WIZ_SECURE bit, immortal should not receive WIZ_SECURE messages
    imm = Character(name="Imm", is_admin=True, wiznet=int(WiznetFlag.WIZ_ON))
    character_registry.append(imm)
    wiznet("secure", WiznetFlag.WIZ_SECURE)
    assert all("secure" not in msg for msg in imm.messages)

    # After subscribing to WIZ_SECURE, message should be delivered
    imm.wiznet |= int(WiznetFlag.WIZ_SECURE)
    wiznet("secure2", WiznetFlag.WIZ_SECURE)
    assert any(msg == "{Zsecure2{x" for msg in imm.messages)


def test_wiznet_status_command():
    imm = Character(name="Imm", is_admin=True, level=60)
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


def test_wiznet_show_command():
    imm = Character(name="Imm", is_admin=True, level=60)
    character_registry.append(imm)

    result = process_command(imm, "wiznet show")
    assert "available to you" in result
    assert "on" in result  # Should show available options
    assert "ticks" in result


def test_wiznet_individual_flag_toggle():
    imm = Character(name="Imm", is_admin=True, level=60)
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
    imm = Character(name="Imm", is_admin=True)
    character_registry.append(imm)

    # Test explicit "on"
    result = process_command(imm, "wiznet on")
    assert "welcome to wiznet" in result.lower()
    assert imm.wiznet & int(WiznetFlag.WIZ_ON)

    # Test explicit "off"
    result = process_command(imm, "wiznet off")
    assert "signing off" in result.lower()
    assert not (imm.wiznet & int(WiznetFlag.WIZ_ON))


def test_wiznet_prefix_formatting():
    imm_with_prefix = Character(name="ImmPrefix", is_admin=True, wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_PREFIX))
    imm_without_prefix = Character(name="ImmPlain", is_admin=True, wiznet=int(WiznetFlag.WIZ_ON))
    character_registry.extend([imm_with_prefix, imm_without_prefix])

    wiznet("Test prefix", WiznetFlag.WIZ_ON)

    # Check that prefix character gets formatted message
    assert imm_with_prefix.messages == ["{Z--> Test prefix{x"]
    # Check that non-prefix character gets color-wrapped message without arrow
    assert imm_without_prefix.messages == ["{ZTest prefix{x"]


def test_wiznet_act_formatting():
    sender = Character(name="Kestrel", sex=Sex.FEMALE)
    prefix_listener = Character(
        name="ImmPrefix",
        is_admin=True,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LINKS | WiznetFlag.WIZ_PREFIX),
    )
    plain_listener = Character(
        name="ImmPlain",
        is_admin=True,
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
        "{Z--> Kestrel groks the fullness of her link.{x",
        "{Z--> Kestrel answers 'Ready'{x",
    ]
    assert plain_listener.messages == [
        "{ZKestrel groks the fullness of her link.{x",
        "{ZKestrel answers 'Ready'{x",
    ]


def test_wiznet_trust_allows_secure_options():
    trusted = Character(
        name="Trusted",
        is_admin=True,
        level=50,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    low_trust = Character(
        name="Low",
        is_admin=True,
        level=50,
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
    assert trusted.messages == ["{Zsecure notice{x"]

    # Base level without additional trust should not see or toggle secure.
    show_low = process_command(low_trust, "wiznet show")
    assert "secure" not in show_low

    toggle_low = process_command(low_trust, "wiznet secure")
    assert toggle_low == "No such option."
    wiznet("secure notice", None, None, WiznetFlag.WIZ_SECURE, None, 60)
    assert all("secure notice" not in msg for msg in low_trust.messages)


def test_wiznet_logins_channel_broadcasts():
    watcher = Character(
        name="Watcher",
        is_admin=True,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOGINS | WiznetFlag.WIZ_PREFIX),
    )
    skip_sites = Character(
        name="Sites",
        is_admin=True,
        level=60,
        trust=60,
        wiznet=int(
            WiznetFlag.WIZ_ON
            | WiznetFlag.WIZ_LOGINS
            | WiznetFlag.WIZ_SITES
            | WiznetFlag.WIZ_PREFIX
        ),
    )
    low_trust = Character(
        name="Low",
        is_admin=True,
        level=50,
        trust=50,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOGINS | WiznetFlag.WIZ_PREFIX),
    )
    logging_char = Character(name="Artemis", level=60, trust=60, is_admin=True)

    character_registry.extend([watcher, skip_sites, low_trust, logging_char])

    announce_wiznet_login(logging_char, host="aurora.example")

    assert "{Z--> Artemis has left real life behind.{x" in watcher.messages
    assert any("{Z--> Artemis@aurora.example has connected.{x" in msg for msg in skip_sites.messages)
    assert not any("has left real life behind" in msg for msg in skip_sites.messages)
    assert low_trust.messages == []

    watcher.messages.clear()
    skip_sites.messages.clear()
    low_trust.messages.clear()

    announce_wiznet_logout(logging_char)

    assert "{Z--> Artemis rejoins the real world.{x" in watcher.messages
    assert "{Z--> Artemis rejoins the real world.{x" in skip_sites.messages
    assert low_trust.messages == []


def test_wiz_sites_announces_successful_login(capsys):
    prefix_listener = Character(
        name="Prefix",
        is_admin=True,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES | WiznetFlag.WIZ_PREFIX),
    )
    plain_listener = Character(
        name="Plain",
        is_admin=True,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES),
    )
    uninterested = Character(
        name="NoSites",
        is_admin=True,
        level=60,
        trust=60,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    low_trust = Character(
        name="Low",
        is_admin=True,
        level=50,
        trust=40,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES),
    )
    logging_char = Character(name="Lyra", level=60, trust=60, is_admin=True)

    character_registry.extend(
        [prefix_listener, plain_listener, uninterested, low_trust, logging_char]
    )

    announce_wiznet_login(logging_char, host="academy.example")

    out = capsys.readouterr().out
    assert "Lyra@academy.example has connected." in out

    assert plain_listener.messages == ["{ZLyra@academy.example has connected.{x"]
    assert any(
        "{Z--> Lyra@academy.example has connected.{x" in msg
        for msg in prefix_listener.messages
    )
    assert all(
        "Lyra@academy.example has connected." not in msg
        for msg in uninterested.messages
    )
    assert low_trust.messages == []
