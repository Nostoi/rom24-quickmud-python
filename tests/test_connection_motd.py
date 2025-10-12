import asyncio
from types import SimpleNamespace

import mud.net.connection as connection
from mud.loaders.help_loader import load_help_file
from mud.net.session import Session


class FakeTelnet:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.ansi_enabled = True

    async def send_line(self, message: str) -> None:
        self.messages.append(message)

    async def flush(self) -> None:
        return


def _make_character(name: str, *, immortal: bool = False):
    telnet = FakeTelnet()
    if immortal:
        immortal_attr = lambda: True  # noqa: E731
    else:
        immortal_attr = False
    return SimpleNamespace(
        name=name,
        connection=telnet,
        ansi_enabled=True,
        trust=0 if not immortal else 60,
        level=60 if immortal else 1,
        is_immortal=immortal_attr,
        newbie_help_seen=False,
        is_npc=False,
    )


def test_send_login_motd_for_mortal() -> None:
    load_help_file("data/help.json")
    char = _make_character("Nova")

    asyncio.run(connection._send_login_motd(char))

    assert len(char.connection.messages) == 1
    motd = char.connection.messages[0]
    assert "You are responsible for knowing the rules" in motd
    assert "[Hit Return to continue]" not in motd


def test_send_login_motd_for_immortal() -> None:
    load_help_file("data/help.json")
    char = _make_character("Zeus", immortal=True)

    asyncio.run(connection._send_login_motd(char))

    assert len(char.connection.messages) == 2
    imotd, motd = char.connection.messages
    assert "Welcome Immortal!" in imotd
    assert "You are responsible for knowing the rules" in motd
    assert all("[Hit Return to continue]" not in message for message in (imotd, motd))


def test_should_send_newbie_help_checks_state() -> None:
    fresh = SimpleNamespace(is_npc=False, level=1, newbie_help_seen=False)
    assert connection._should_send_newbie_help(fresh) is True

    fresh.newbie_help_seen = True
    assert connection._should_send_newbie_help(fresh) is False

    fresh.newbie_help_seen = False
    fresh.level = 2
    assert connection._should_send_newbie_help(fresh) is False

    fresh.level = 1
    fresh.is_npc = True
    assert connection._should_send_newbie_help(fresh) is False


def test_send_newbie_help_sets_flag_and_persists(monkeypatch) -> None:
    load_help_file("data/help.json")

    telnet = FakeTelnet()
    char = SimpleNamespace(
        name="Nova",
        connection=telnet,
        ansi_enabled=True,
        trust=0,
        level=1,
        is_immortal=lambda: False,
        newbie_help_seen=False,
        is_npc=False,
        messages=[],
    )
    session = Session(name="Nova", character=char, reader=None, connection=telnet)
    char.desc = session

    saved: dict[str, bool] = {}

    def _mock_save_character(updated) -> None:
        saved["called"] = True
        assert updated is char

    monkeypatch.setattr(connection, "save_character", _mock_save_character)

    asyncio.run(connection._send_newbie_help(char))

    assert saved.get("called") is True
    assert char.newbie_help_seen is True
    assert any("Ah! Another mortal" in payload for payload in telnet.messages)
