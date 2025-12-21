import asyncio
from types import SimpleNamespace

from mud.models.constants import PlayerFlag, ROOM_VNUM_LIMBO
from mud.models.room import Room
from mud.net import connection
from mud.net.connection import _read_player_command, _stop_idling
from mud.net.protocol import send_to_char
from mud.net.session import Session
from mud.registry import room_registry


def test_stop_idling_returns_character_to_previous_room():
    original_rooms = dict(room_registry)
    try:
        limbo_area = SimpleNamespace(empty=True, nplayer=0, age=0)
        home_area = SimpleNamespace(empty=True, nplayer=0, age=0)

        limbo = Room(vnum=ROOM_VNUM_LIMBO, area=limbo_area)
        home = Room(vnum=ROOM_VNUM_LIMBO + 1, area=home_area)

        room_registry.clear()
        room_registry[limbo.vnum] = limbo
        room_registry[home.vnum] = home

        watcher = SimpleNamespace(name="Watcher", is_npc=False, messages=[])
        home.add_character(watcher)

        player = SimpleNamespace(
            name="Hero",
            is_npc=False,
            messages=[],
            room=None,
            was_in_room=home,
            timer=13,
        )
        limbo.add_character(player)

        _stop_idling(player)

        assert player.room is home
        assert player.was_in_room is None
        assert player not in limbo.people
        assert watcher.messages[-1] == "Hero has returned from the void."
        assert player.timer == 0
    finally:
        room_registry.clear()
        room_registry.update(original_rooms)


class FakeConn:
    def __init__(self, responses: list[str], host: str | None = None) -> None:
        self._responses = responses
        self.sent_lines: list[str] = []
        self.sent_text: list[str] = []
        self.sent_prompts: list[str] = []
        self.peer_host = host
        self.ansi_enabled = True

    def queue_responses(self, responses: list[str]) -> None:
        self._responses.extend(responses)

    async def send_prompt(self, prompt: str, *, go_ahead: bool | None = None) -> None:
        self.sent_prompts.append(prompt)

    async def readline(self, *, max_length: int = 256) -> str | None:  # noqa: ARG002
        if not self._responses:
            return ""
        return self._responses.pop(0)

    async def disable_echo(self) -> None:  # noqa: D401 - testing stub
        return

    async def enable_echo(self) -> None:  # noqa: D401 - testing stub
        return

    async def send_text(self, message: str, *, newline: bool = False) -> None:
        payload = message + ("\n\r" if newline and not message.endswith("\n\r") else "")
        self.sent_text.append(payload)

    async def send_line(self, message: str) -> None:
        self.sent_lines.append(message)
        await self.send_text(message, newline=True)


def test_select_character_blocks_unpermitted_from_permit_host(monkeypatch):
    account = SimpleNamespace(characters=[SimpleNamespace(name="Squire", act=0)])
    fake_conn = FakeConn(["Squire"], host="permit.example")

    monkeypatch.setattr(
        connection,
        "load_character",
        lambda username, name: SimpleNamespace(name=name, act=0, messages=[]),
    )

    async def runner() -> tuple | None:
        connection.SESSIONS.clear()
        return await connection._select_character(
            fake_conn,
            account,
            "warden",
            permit_banned=True,
        )

    result = asyncio.run(runner())

    assert result is None
    assert "Your site has been banned from this mud." in fake_conn.sent_lines[-1]


def test_select_character_allows_permit_from_permit_host(monkeypatch):
    account = SimpleNamespace(characters=[SimpleNamespace(name="Guardian", act=int(PlayerFlag.PERMIT))])
    fake_conn = FakeConn(["Guardian"], host="permit.example")

    permitted_char = SimpleNamespace(
        name="Guardian",
        act=int(PlayerFlag.PERMIT),
        messages=[],
    )

    monkeypatch.setattr(
        connection,
        "load_character",
        lambda username, name: permitted_char,
    )

    async def runner() -> tuple | None:
        connection.SESSIONS.clear()
        return await connection._select_character(
            fake_conn,
            account,
            "warden",
            permit_banned=True,
        )

    result = asyncio.run(runner())

    assert result == (permitted_char, False)
    assert all("Your site has been banned from this mud." not in line for line in fake_conn.sent_lines)


def test_show_string_paginates_output():
    fake_conn = FakeConn([])
    char = SimpleNamespace(
        name="Pager",
        lines=2,
        ansi_enabled=True,
        connection=fake_conn,
        messages=[],
        act=0,
    )
    session = Session(name="Pager", character=char, reader=None, connection=fake_conn)
    char.desc = session

    long_text = "Line1\r\nLine2\r\nLine3\r\nLine4\r\nLine5\r\n"

    asyncio.run(send_to_char(char, long_text))

    assert fake_conn.sent_text[0] == "Line1\n\rLine2\n\r"
    assert fake_conn.sent_text[1] == "[Hit Return to continue]\n\r"
    assert fake_conn.sent_lines[-1] == "[Hit Return to continue]"
    assert session.show_buffer is not None

    more = asyncio.run(session.send_next_page())
    assert more is True
    assert fake_conn.sent_text[2] == "Line3\n\rLine4\n\r"
    assert fake_conn.sent_text[3] == "[Hit Return to continue]\n\r"
    assert fake_conn.sent_lines[-1] == "[Hit Return to continue]"
    assert session.show_buffer is not None

    more = asyncio.run(session.send_next_page())
    assert more is False
    assert fake_conn.sent_text[-1] == "Line5\n\r"
    assert session.show_buffer is None

    fake_conn.sent_text.clear()
    fake_conn.sent_lines.clear()
    asyncio.run(send_to_char(char, long_text))
    fake_conn.queue_responses(["look"])
    result = asyncio.run(_read_player_command(fake_conn, session))
    assert result == "look"
    assert session.show_buffer is None


def test_send_to_char_accepts_iterables():
    fake_conn = FakeConn([])
    char = SimpleNamespace(
        name="Lister",
        lines=0,
        ansi_enabled=True,
        connection=fake_conn,
        messages=[],
        act=0,
    )

    asyncio.run(send_to_char(char, ["Alpha", "Beta"]))
    assert "Alpha" in fake_conn.sent_lines[-1] and "Beta" in fake_conn.sent_lines[-1]
    assert "Alpha" in fake_conn.sent_text[-1] and "Beta" in fake_conn.sent_text[-1]

    fake_conn2 = FakeConn([])
    char2 = SimpleNamespace(
        name="Pager",
        lines=2,
        ansi_enabled=True,
        connection=fake_conn2,
        messages=[],
        act=0,
    )
    session2 = Session(name="Pager", character=char2, reader=None, connection=fake_conn2)
    char2.desc = session2

    generator_message = (segment for segment in ("One", "Two", "Three"))
    asyncio.run(send_to_char(char2, generator_message))

    assert fake_conn2.sent_text[0] == "One\n\rTwo\n\r"
    assert fake_conn2.sent_lines[-1] == "[Hit Return to continue]"
    assert session2.show_buffer is not None


def test_motd_uses_session_paging(monkeypatch):
    sample_text = "Line1\r\nLine2\r\nLine3\r\nLine4\r\n"

    monkeypatch.setattr(
        connection,
        "_resolve_help_text",
        lambda ch, topic, limit_first=False: sample_text,
    )

    no_page_conn = FakeConn([])
    mortal = SimpleNamespace(
        name="Reader",
        lines=0,
        ansi_enabled=True,
        connection=no_page_conn,
        messages=[],
        act=0,
        is_immortal=lambda: False,
    )
    mortal.desc = Session(name="Reader", character=mortal, reader=None, connection=no_page_conn)

    asyncio.run(connection._send_login_motd(mortal))

    assert all("[Hit Return to continue]" not in payload for payload in no_page_conn.sent_text)

    paged_conn = FakeConn([])
    paged = SimpleNamespace(
        name="Pager",
        lines=2,
        ansi_enabled=True,
        connection=paged_conn,
        messages=[],
        act=0,
        is_immortal=lambda: False,
    )
    paged_session = Session(name="Pager", character=paged, reader=None, connection=paged_conn)
    paged.desc = paged_session

    asyncio.run(connection._send_login_motd(paged))

    assert paged_conn.sent_text[0] == "Line1\n\rLine2\n\r"
    assert paged_conn.sent_text[1] == "[Hit Return to continue]\n\r"
    assert paged_session.show_buffer is not None

    asyncio.run(paged_session.send_next_page())

    assert paged_conn.sent_text[-1] == "Line3\n\rLine4\n\r"
    assert paged_session.show_buffer is None


def test_format_three_column_table_groups_entries():
    entries = [("alpha", "1"), ("beta", "2"), ("gamma", "3"), ("delta", "4")]
    lines = connection._format_three_column_table(entries)
    assert lines[0] == "alpha              1     beta               2     gamma              3"
    assert lines[1] == "delta              4"


def test_format_name_columns_wraps_three_names():
    rows = connection._format_name_columns(["Alpha", "Beta", "Gamma", "Delta"], width=8)
    assert rows[0] == "Alpha    Beta     Gamma"
    assert rows[1] == "Delta"
