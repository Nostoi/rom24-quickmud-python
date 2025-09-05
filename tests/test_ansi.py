from mud.net.ansi import translate_ansi


def test_translate_ansi_replaces_tokens():
    assert translate_ansi("{rRed{x") == "\x1b[31mRed\x1b[0m"
