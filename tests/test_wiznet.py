from mud.wiznet import WiznetFlag, wiznet
from mud.models.character import Character, character_registry
from mud.commands.dispatcher import process_command


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
