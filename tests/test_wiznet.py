from mud.wiznet import WiznetFlag, wiznet
from mud.models.character import Character, character_registry
from mud.commands.dispatcher import process_command
import mud.persistence as persistence


def setup_function(_):
    character_registry.clear()


def test_wiznet_flag_values():
    expected = {
        'WIZ_ON': 0x00000001,
        'WIZ_TICKS': 0x00000002,
        'WIZ_LOGINS': 0x00000004,
        'WIZ_SITES': 0x00000008,
        'WIZ_LINKS': 0x00000010,
        'WIZ_DEATHS': 0x00000020,
        'WIZ_RESETS': 0x00000040,
        'WIZ_MOBDEATHS': 0x00000080,
        'WIZ_FLAGS': 0x00000100,
        'WIZ_PENALTIES': 0x00000200,
        'WIZ_SACCING': 0x00000400,
        'WIZ_LEVELS': 0x00000800,
        'WIZ_SECURE': 0x00001000,
        'WIZ_SWITCHES': 0x00002000,
        'WIZ_SNOOPS': 0x00004000,
        'WIZ_RESTORE': 0x00008000,
        'WIZ_LOAD': 0x00010000,
        'WIZ_NEWBIE': 0x00020000,
        'WIZ_SPAM': 0x00040000,
        'WIZ_DEBUG': 0x00080000,
        'WIZ_MEMORY': 0x00100000,
        'WIZ_SKILLS': 0x00200000,
        'WIZ_TESTING': 0x00400000,
    }
    for name, value in expected.items():
        assert getattr(WiznetFlag, name).value == value


def test_wiznet_broadcast_filtering():
    imm = Character(name="Imm", is_admin=True, wiznet=int(WiznetFlag.WIZ_ON))
    mortal = Character(name="Mort", is_admin=False, wiznet=int(WiznetFlag.WIZ_ON))
    character_registry.extend([imm, mortal])

    wiznet("Test message", WiznetFlag.WIZ_ON)

    assert "Test message" in imm.messages
    assert "Test message" not in mortal.messages


def test_wiznet_command_toggles_flag():
    imm = Character(name="Imm", is_admin=True)
    character_registry.append(imm)
    result = process_command(imm, "wiznet")
    assert imm.wiznet & int(WiznetFlag.WIZ_ON)
    assert "wiznet is now on" in result.lower()


def test_wiznet_persistence(tmp_path):
    # Persist wiznet flags and ensure round-trip retains bitfield.
    persistence.PLAYERS_DIR = tmp_path
    from mud.world import initialize_world

    initialize_world('area/area.lst')
    imm = Character(name="Imm", is_admin=True)
    # Set multiple flags
    imm.wiznet = int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_TICKS | WiznetFlag.WIZ_DEBUG)
    persistence.save_character(imm)
    loaded = persistence.load_character('Imm')
    assert loaded is not None
    assert loaded.wiznet & int(WiznetFlag.WIZ_ON)
    assert loaded.wiznet & int(WiznetFlag.WIZ_TICKS)
    assert loaded.wiznet & int(WiznetFlag.WIZ_DEBUG)


def test_wiznet_requires_specific_flag():
    # Immortal with WIZ_ON only should not receive WIZ_TICKS messages.
    imm = Character(name="Imm", is_admin=True, wiznet=int(WiznetFlag.WIZ_ON))
    character_registry.append(imm)
    wiznet("tick", WiznetFlag.WIZ_TICKS)
    assert "tick" not in imm.messages

    # After subscribing to WIZ_TICKS, should receive.
    imm.wiznet |= int(WiznetFlag.WIZ_TICKS)
    wiznet("tick2", WiznetFlag.WIZ_TICKS)
    assert "tick2" in imm.messages


def test_wiznet_secure_flag_gating():
    # Without WIZ_SECURE bit, immortal should not receive WIZ_SECURE messages
    imm = Character(name="Imm", is_admin=True, wiznet=int(WiznetFlag.WIZ_ON))
    character_registry.append(imm)
    wiznet("secure", WiznetFlag.WIZ_SECURE)
    assert "secure" not in imm.messages

    # After subscribing to WIZ_SECURE, message should be delivered
    imm.wiznet |= int(WiznetFlag.WIZ_SECURE)
    wiznet("secure2", WiznetFlag.WIZ_SECURE)
    assert "secure2" in imm.messages
