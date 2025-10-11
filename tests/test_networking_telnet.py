import asyncio
from types import SimpleNamespace

from mud.models.constants import PlayerFlag, ROOM_VNUM_LIMBO
from mud.models.room import Room
from mud.net import connection
from mud.net.connection import _stop_idling
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
        self.sent_prompts: list[str] = []
        self.peer_host = host
        self.ansi_enabled = True

    async def send_prompt(self, prompt: str) -> None:
        self.sent_prompts.append(prompt)

    async def readline(self, *, max_length: int = 256) -> str | None:  # noqa: ARG002
        if not self._responses:
            return ""
        return self._responses.pop(0)

    async def disable_echo(self) -> None:  # noqa: D401 - testing stub
        return

    async def enable_echo(self) -> None:  # noqa: D401 - testing stub
        return

    async def send_line(self, message: str) -> None:
        self.sent_lines.append(message)


def test_select_character_blocks_unpermitted_from_permit_host(monkeypatch):
    account = SimpleNamespace(characters=[SimpleNamespace(name="Squire")])
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
    account = SimpleNamespace(characters=[SimpleNamespace(name="Guardian")])
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
    assert all(
        "Your site has been banned from this mud." not in line for line in fake_conn.sent_lines
    )
