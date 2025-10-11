import asyncio
from types import SimpleNamespace

from mud.loaders.help_loader import load_help_file
from mud.net.connection import _send_login_motd


class FakeTelnet:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.ansi_enabled = True

    async def send_line(self, message: str) -> None:
        self.messages.append(message)

    async def flush(self) -> None:
        return


def _make_character(name: str, *, immortal: bool = False):
    connection = FakeTelnet()
    if immortal:
        immortal_attr = lambda: True  # noqa: E731
    else:
        immortal_attr = False
    return SimpleNamespace(
        name=name,
        connection=connection,
        ansi_enabled=True,
        trust=0 if not immortal else 60,
        level=60 if immortal else 1,
        is_immortal=immortal_attr,
    )


def test_send_login_motd_for_mortal() -> None:
    load_help_file("data/help.json")
    char = _make_character("Nova")

    asyncio.run(_send_login_motd(char))

    assert len(char.connection.messages) == 1
    motd = char.connection.messages[0]
    assert "You are responsible for knowing the rules" in motd
    assert motd.endswith("[Hit Return to continue]")


def test_send_login_motd_for_immortal() -> None:
    load_help_file("data/help.json")
    char = _make_character("Zeus", immortal=True)

    asyncio.run(_send_login_motd(char))

    assert len(char.connection.messages) == 2
    imotd, motd = char.connection.messages
    assert "Welcome Immortal!" in imotd
    assert imotd.endswith("[Hit Return to continue]")
    assert "You are responsible for knowing the rules" in motd
