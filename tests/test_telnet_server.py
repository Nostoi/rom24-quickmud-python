import asyncio
from contextlib import suppress
from dataclasses import replace
from types import SimpleNamespace

import pytest

from mud.account import clear_active_accounts, create_character, login
from mud.commands.admin_commands import cmd_telnetga
from mud.config import (
    get_qmconfig,
    set_ansicolor,
    set_ansiprompt,
    set_ip_address,
    set_telnetga,
)
from mud.db.models import Base, PlayerAccount
from mud.db.session import SessionLocal, engine
from mud.security.hash_utils import hash_password
from mud.net.connection import (
    SPAM_REPEAT_THRESHOLD,
    TelnetStream,
    _apply_qmconfig_telnetga,
    _read_player_command,
)
from mud.net.session import Session
from mud.net.telnet_server import create_server
from mud.models.character import Character
from mud.models.constants import CommFlag

TELNET_IAC = 255
TELNET_WILL = 251
TELNET_WONT = 252
TELNET_DO = 253
TELNET_GA = 249
TELNET_TELOPT_ECHO = 1
TELNET_TELOPT_SUPPRESS_GA = 3


async def negotiate_ansi_prompt(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, reply: bytes = b""
) -> tuple[bytes, bytes]:
    prompt = await asyncio.wait_for(
        reader.readuntil(b"Do you want ANSI? (Y/n) "),
        timeout=5,
    )
    payload = reply.strip() if reply else b""
    writer.write(payload + b"\r\n")
    await writer.drain()
    greeting = await asyncio.wait_for(reader.readuntil(b"Account: "), timeout=5)
    return prompt, greeting


def setup_module(module):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@pytest.fixture
def qmconfig_snapshot():
    snapshot = replace(get_qmconfig())
    try:
        yield snapshot
    finally:
        set_ansiprompt(snapshot.ansiprompt)
        set_ansicolor(snapshot.ansicolor)
        set_telnetga(snapshot.telnetga)
        set_ip_address(snapshot.ip_address)


class MemoryTransport(asyncio.Transport):
    def __init__(self) -> None:
        super().__init__()
        self.buffer = bytearray()
        self._closing = False

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    def is_closing(self) -> bool:
        return self._closing

    def close(self) -> None:
        self._closing = True


async def _make_telnet_stream() -> tuple[TelnetStream, MemoryTransport, asyncio.StreamReaderProtocol]:
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    transport = MemoryTransport()
    protocol.connection_made(transport)
    writer = asyncio.StreamWriter(transport, protocol, reader, loop)
    return TelnetStream(reader, writer), transport, protocol


@pytest.mark.telnet
def test_telnet_stream_preserves_rom_newline():
    async def run() -> None:
        stream, transport, _ = await _make_telnet_stream()
        try:
            await stream.send_text("Prompt\n\r", newline=False)
            assert transport.buffer.endswith(b"Prompt\n\r")

            transport.buffer.clear()

            await stream.send_text("Prompt", newline=True)
            assert transport.buffer.endswith(b"Prompt\n\r")

            transport.buffer.clear()

            await stream.send_text("Prompt\r\n", newline=True)
            assert transport.buffer.endswith(b"Prompt\n\r")

            transport.buffer.clear()

            await stream.send_text("Prompt\n\r", newline=True)
            assert transport.buffer.endswith(b"Prompt\n\r")
        finally:
            transport.close()

    asyncio.run(run())


@pytest.mark.telnet
def test_telnet_stream_normalizes_embedded_crlf():
    async def run() -> None:
        stream, transport, _ = await _make_telnet_stream()
        try:
            await stream.send_text("Line1\r\nLine2\r\nLine3", newline=False)
            assert transport.buffer == b"Line1\n\rLine2\n\rLine3"
        finally:
            transport.close()

    asyncio.run(run())


@pytest.mark.telnet
def test_telnet_pagination_handles_rom_newline_pairs():
    async def run() -> None:
        stream, transport, _ = await _make_telnet_stream()
        try:
            pager = SimpleNamespace(lines=2)
            session = Session(
                name="Pager",
                character=pager,
                reader=stream.reader,
                connection=stream,
            )
            pager.desc = session

            text = "Line1\n\rLine2\n\rLine3\n\r"
            await session.start_paging(text, pager.lines)

            assert transport.buffer == b"Line1\n\rLine2\n\r[Hit Return to continue]\n\r"

            transport.buffer.clear()

            more = await session.send_next_page()
            assert more is False
            assert transport.buffer == b"Line3\n\r"
            assert session.show_buffer is None
        finally:
            transport.close()

    asyncio.run(run())


@pytest.mark.telnet
def test_telnet_pagination_normalizes_crlf():
    async def run() -> None:
        stream, transport, _ = await _make_telnet_stream()
        try:
            pager = SimpleNamespace(lines=2)
            session = Session(
                name="Pager",
                character=pager,
                reader=stream.reader,
                connection=stream,
            )
            pager.desc = session

            text = "Line1\r\nLine2\r\nLine3\r\n"
            await session.start_paging(text, pager.lines)

            assert transport.buffer == b"Line1\n\rLine2\n\r[Hit Return to continue]\n\r"

            transport.buffer.clear()

            more = await session.send_next_page()
            assert more is False
            assert transport.buffer == b"Line3\n\r"
            assert session.show_buffer is None
        finally:
            transport.close()

    asyncio.run(run())


@pytest.mark.telnet
@pytest.mark.timeout(30)
@pytest.mark.skipif(
    __import__("sys").platform == "darwin",
    reason="macOS asyncio/kqueue timeout handling is unreliable under pytest-timeout",
)
def test_telnet_server_handles_look_command():
    from mud.account.account_service import clear_active_accounts
    from mud.security.hash_utils import hash_password

    async def run():
        clear_active_accounts()
        session = SessionLocal()
        session.add(
            PlayerAccount(
                username="Looker",
                email="",
                password_hash=hash_password("pass"),
            )
        )
        session.commit()
        session.close()

        account = login("Looker", "pass")
        assert account is not None
        create_character(account, "Looker")

        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)
            await negotiate_ansi_prompt(reader, writer)
            writer.write(b"Looker\n")
            await writer.drain()
            await asyncio.wait_for(reader.readuntil(b"Password: "), timeout=5)
            writer.write(b"pass\n")
            await writer.drain()
            await asyncio.wait_for(reader.readuntil(b"Character: "), timeout=5)
            writer.write(b"Looker\n")
            await writer.drain()
            await asyncio.wait_for(reader.readuntil(b"> "), timeout=5)
            writer.write(b"look\n")
            await writer.drain()
            output = await asyncio.wait_for(reader.readuntil(b"> "), timeout=5)
            text = output.decode()
            assert len(text) > 10
            writer.close()
            await writer.wait_closed()
        finally:
            server.close()
            await server.wait_closed()
            server_task.cancel()
            with suppress(asyncio.CancelledError):
                await server_task

    asyncio.run(run())


@pytest.mark.telnet
def test_telnetga_command_toggles_go_ahead():
    async def run():
        stream, transport, protocol = await _make_telnet_stream()
        char = Character(name="Tester", is_npc=False)
        session = Session(
            name="Tester",
            character=char,
            reader=stream.reader,
            connection=stream,
        )
        char.desc = session

        char.clear_comm_flag(CommFlag.TELNET_GA)
        session.go_ahead_enabled = False
        stream.set_go_ahead_enabled(False)

        transport.buffer.clear()
        await stream.send_prompt("> ", go_ahead=session.go_ahead_enabled)
        assert transport.buffer == b"> "

        enable_message = cmd_telnetga(char, "")
        assert enable_message == "Telnet GA enabled."
        assert char.has_comm_flag(CommFlag.TELNET_GA)
        assert session.go_ahead_enabled is True

        transport.buffer.clear()
        await stream.send_prompt("> ", go_ahead=session.go_ahead_enabled)
        assert transport.buffer[:-2] == b"> "
        assert transport.buffer[-2:] == bytes([TELNET_IAC, TELNET_GA])

        disable_message = cmd_telnetga(char, "")
        assert disable_message == "Telnet GA removed."
        assert not char.has_comm_flag(CommFlag.TELNET_GA)
        assert session.go_ahead_enabled is False

        transport.buffer.clear()
        await stream.send_prompt("> ", go_ahead=session.go_ahead_enabled)
        assert transport.buffer == b"> "

        transport.close()
        protocol.connection_lost(None)

    asyncio.run(run())


def test_qmconfig_telnetga_default_applied(qmconfig_snapshot):
    async def run():
        stream, transport, protocol = await _make_telnet_stream()
        try:
            char = Character(name="Newbie", level=1, played=0)
            session = Session(
                name="Newbie",
                character=char,
                reader=stream.reader,
                connection=stream,
            )
            char.desc = session

            set_telnetga(True)
            set_ansiprompt(True)
            set_ansicolor(True)
            _apply_qmconfig_telnetga(
                char,
                session,
                stream,
                default_enabled=get_qmconfig().telnetga,
                is_new_player=True,
            )
            assert char.has_comm_flag(CommFlag.TELNET_GA)

            transport.buffer.clear()
            await stream.send_prompt("> ", go_ahead=session.go_ahead_enabled)
            assert transport.buffer.endswith(bytes([TELNET_IAC, TELNET_GA]))

            set_telnetga(False)
            _apply_qmconfig_telnetga(
                char,
                session,
                stream,
                default_enabled=get_qmconfig().telnetga,
                is_new_player=True,
            )
            assert not char.has_comm_flag(CommFlag.TELNET_GA)

            transport.buffer.clear()
            await stream.send_prompt("> ", go_ahead=session.go_ahead_enabled)
            assert transport.buffer == b"> "
        finally:
            transport.close()
            protocol.connection_lost(None)

    asyncio.run(run())


def test_qmconfig_ip_address_controls_bind_host(qmconfig_snapshot):
    async def run():
        set_ip_address("127.0.0.1")
        server = await create_server(port=0)
        try:
            host, _ = server.sockets[0].getsockname()
            assert host == "127.0.0.1"
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(run())


@pytest.mark.telnet
@pytest.mark.timeout(30)
def test_telnet_negotiates_iac_and_disables_echo():
    async def run():
        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)

            # First, negotiate ANSI prompt
            ansi_prompt, greeting = await negotiate_ansi_prompt(reader, writer)
            # The telnet sequences should be in the initial data before ANSI prompt
            combined = ansi_prompt + greeting
            assert bytes([TELNET_IAC, TELNET_WONT, TELNET_TELOPT_ECHO]) in combined
            assert bytes([TELNET_IAC, TELNET_DO, TELNET_TELOPT_SUPPRESS_GA]) in combined

            writer.write(b"negotiator\r\n")
            await writer.drain()
            await reader.readuntil(b"(Y/N) ")
            writer.write(b"y\r\n")
            await writer.drain()

            password_prompt = await reader.readuntil(b"New password: ")
            assert bytes([TELNET_IAC, TELNET_WILL, TELNET_TELOPT_ECHO]) in password_prompt

            writer.write(b"secret\r\n")
            await writer.drain()

            confirm_prompt = await reader.readuntil(b"Confirm password: ")
            assert bytes([TELNET_IAC, TELNET_WONT, TELNET_TELOPT_ECHO]) in confirm_prompt
            assert bytes([TELNET_IAC, TELNET_WILL, TELNET_TELOPT_ECHO]) in confirm_prompt
            assert b"secret" not in confirm_prompt

            writer.write(b"secret\r\n")
            await writer.drain()

            created = await reader.readuntil(b"Account created.")
            assert bytes([TELNET_IAC, TELNET_WONT, TELNET_TELOPT_ECHO]) in created

            writer.close()
            await writer.wait_closed()
        finally:
            server.close()
            await server.wait_closed()
            server_task.cancel()
            with suppress(asyncio.CancelledError):
                await server_task

    asyncio.run(run())


@pytest.mark.telnet
@pytest.mark.timeout(30)
def test_telnet_server_handles_multiple_connections():
    from mud.account.account_service import create_account, clear_active_accounts
    from mud.world.world_state import reset_lockdowns
    from mud.security import bans

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("Alice", "pw")
    alice_account = login("Alice", "pw")
    assert alice_account is not None
    assert create_character(alice_account, "Alice")

    assert create_account("Bob", "pw")
    bob_account = login("Bob", "pw")
    assert bob_account is not None
    assert create_character(bob_account, "Bob")

    async def run():
        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            r1, w1 = await asyncio.open_connection(host, port)
            r2, w2 = await asyncio.open_connection(host, port)

            await negotiate_ansi_prompt(r1, w1)
            w1.write(b"Alice\n")
            await w1.drain()
            await r1.readuntil(b"Password: ")
            w1.write(b"pw\n")
            await w1.drain()
            await r1.readuntil(b"Character: ")
            w1.write(b"Alice\n")
            await w1.drain()

            await negotiate_ansi_prompt(r2, w2)
            w2.write(b"Bob\n")
            await w2.drain()
            await r2.readuntil(b"Password: ")
            w2.write(b"pw\n")
            await w2.drain()
            await r2.readuntil(b"Character: ")
            w2.write(b"Bob\n")
            await w2.drain()

            await asyncio.wait_for(r1.readuntil(b"> "), timeout=5)
            await asyncio.wait_for(r2.readuntil(b"> "), timeout=5)

            w1.write(b"look\n")
            await w1.drain()
            look1 = await asyncio.wait_for(r1.readuntil(b"> "), timeout=5)
            assert len(look1) > 10

            w2.write(b"look\n")
            await w2.drain()
            look2 = await asyncio.wait_for(r2.readuntil(b"> "), timeout=5)
            assert len(look2) > 10

            w1.close()
            await w1.wait_closed()
            w2.close()
            await w2.wait_closed()
        finally:
            server.close()
            await server.wait_closed()
            server_task.cancel()
            with suppress(asyncio.CancelledError):
                await server_task

    asyncio.run(run())


@pytest.mark.telnet
@pytest.mark.timeout(30)
def test_telnet_break_connect_prompts_and_reconnects():
    async def run():
        clear_active_accounts()
        session = SessionLocal()
        session.add(
            PlayerAccount(
                username="Breaker",
                email="",
                password_hash=hash_password("pw"),
            )
        )
        session.commit()
        session.close()

        account = login("Breaker", "pw")
        assert account is not None
        create_character(account, "Breaker")

        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            r1, w1 = await asyncio.open_connection(host, port)
            await negotiate_ansi_prompt(r1, w1)
            w1.write(b"Breaker\n")
            await w1.drain()
            await asyncio.wait_for(r1.readuntil(b"Password: "), timeout=5)
            w1.write(b"pw\n")
            await w1.drain()
            await asyncio.wait_for(r1.readuntil(b"Character: "), timeout=5)
            w1.write(b"Breaker\n")
            await w1.drain()
            await asyncio.wait_for(r1.readuntil(b"> "), timeout=5)

            r2, w2 = await asyncio.open_connection(host, port)
            await negotiate_ansi_prompt(r2, w2)
            w2.write(b"Breaker\n")
            await w2.drain()
            account_reconnect = await asyncio.wait_for(
                r2.readuntil(b"Reconnect? (Y/N) "),
                timeout=5,
            )
            assert b"already playing" in account_reconnect
            w2.write(b"y\n")
            await w2.drain()
            await asyncio.wait_for(r2.readuntil(b"Password: "), timeout=5)
            w2.write(b"pw\n")
            await w2.drain()
            await asyncio.wait_for(r2.readuntil(b"Character: "), timeout=5)
            w2.write(b"Breaker\n")
            await w2.drain()

            reconnect_prompt = await asyncio.wait_for(r2.readuntil(b"? "), timeout=5)
            assert b"Reconnect" in reconnect_prompt

            w2.write(b"y\n")
            await w2.drain()

            takeover_notice = await asyncio.wait_for(r1.readline(), timeout=5)
            assert b"taken over" in takeover_notice.lower()

            reconnect_line = await asyncio.wait_for(r2.readline(), timeout=5)
            assert b"Reconnecting" in reconnect_line
            look_chunk = await asyncio.wait_for(r2.readuntil(b"> "), timeout=5)
            assert look_chunk.endswith(b"> ")

            w2.write(b"look\n")
            await w2.drain()
            await asyncio.wait_for(r2.readuntil(b"> "), timeout=5)

            w2.close()
            await w2.wait_closed()
        finally:
            server.close()
            await server.wait_closed()
            server_task.cancel()
            with suppress(asyncio.CancelledError):
                await server_task

    asyncio.run(run())


@pytest.mark.telnet
def test_backspace_editing_preserves_input():
    async def run():
        stream, transport, protocol = await _make_telnet_stream()

        stream.reader.feed_data(b"say hellox\b\r\n")
        result = await stream.readline()
        assert result == "say hello"

        stream.reader.feed_data(b"say hellox\x7f\r\n")
        result_delete = await stream.readline()
        assert result_delete == "say hello"

        transport.close()
        protocol.connection_lost(None)

    asyncio.run(run())


@pytest.mark.telnet
def test_excessive_repeats_trigger_spam_warning():
    async def run():
        stream, transport, protocol = await _make_telnet_stream()
        dummy_char = SimpleNamespace()
        session = Session(
            name="Tester",
            character=dummy_char,
            reader=stream.reader,
            connection=stream,
        )

        spam_warning = b"*** PUT A LID ON IT!!! ***"

        for _ in range(SPAM_REPEAT_THRESHOLD):
            stream.reader.feed_data(b"say hi\r\n")
            command = await _read_player_command(stream, session)
            assert command == "say hi"

        assert spam_warning not in transport.buffer

        transport.buffer.clear()
        stream.reader.feed_data(b"say hi\r\n")
        command = await _read_player_command(stream, session)
        assert command == "say hi"
        assert spam_warning in transport.buffer

        transport.buffer.clear()
        stream.reader.feed_data(b"say hi\r\n")
        await _read_player_command(stream, session)
        assert spam_warning not in transport.buffer

        transport.close()
        protocol.connection_lost(None)

    asyncio.run(run())


@pytest.mark.telnet
def test_repeat_command_after_blank_line_uses_last_non_empty():
    async def run():
        stream, transport, protocol = await _make_telnet_stream()
        dummy_char = SimpleNamespace()
        session = Session(
            name="Tester",
            character=dummy_char,
            reader=stream.reader,
            connection=stream,
        )

        stream.reader.feed_data(b"say hi\r\n")
        first = await _read_player_command(stream, session)
        assert first == "say hi"
        assert session.last_command == "say hi"

        stream.reader.feed_data(b"\r\n")
        blank = await _read_player_command(stream, session)
        assert blank == " "
        assert session.last_command == "say hi"

        stream.reader.feed_data(b"!\r\n")
        repeated = await _read_player_command(stream, session)
        assert repeated == "say hi"

        transport.close()
        protocol.connection_lost(None)

    asyncio.run(run())
