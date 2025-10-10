import asyncio
from contextlib import suppress
from types import SimpleNamespace

import pytest

from mud.account import clear_active_accounts, create_character, login
from mud.db.models import Base, PlayerAccount
from mud.db.session import SessionLocal, engine
from mud.security.hash_utils import hash_password
from mud.net.connection import SPAM_REPEAT_THRESHOLD, TelnetStream, _read_player_command
from mud.net.session import Session
from mud.net.telnet_server import create_server

TELNET_IAC = 255
TELNET_WILL = 251
TELNET_WONT = 252
TELNET_DO = 253
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
@pytest.mark.timeout(30)  # Add timeout to prevent hanging
def test_telnet_server_handles_look_command():
    async def run():
        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)
            assert b"Welcome" in await reader.readline()
            await reader.readuntil(b"Account: ")
            writer.write(b"Tester\n")
            await writer.drain()
            await reader.readuntil(b"Password: ")
            writer.write(b"pass\n")
            await writer.drain()
            await reader.readuntil(b"Character: ")
            writer.write(b"Tester\n")
            await writer.drain()
            await reader.readuntil(b"> ")
            # issue a look command and expect room title in response
            writer.write(b"look\n")
            await writer.drain()
            output = await reader.readuntil(b"> ")
            text = output.decode()
            assert "The Temple Of Mota" in text or "Limbo" in text or "Void" in text or "void" in text
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
def test_telnet_negotiates_iac_and_disables_echo():
    async def run():
        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)

            greeting = await reader.readuntil(b"Account: ")
            assert bytes([TELNET_IAC, TELNET_WONT, TELNET_TELOPT_ECHO]) in greeting
            assert bytes([TELNET_IAC, TELNET_DO, TELNET_TELOPT_SUPPRESS_GA]) in greeting

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
@pytest.mark.timeout(30)  # Add timeout to prevent hanging
def test_telnet_server_handles_multiple_connections():
    async def run():
        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            r1, w1 = await asyncio.open_connection(host, port)
            r2, w2 = await asyncio.open_connection(host, port)

            await r1.readline()
            await r1.readuntil(b"Account: ")
            w1.write(b"Alice\n")
            await w1.drain()
            await r1.readuntil(b"Password: ")
            w1.write(b"pw\n")
            await w1.drain()
            await r1.readuntil(b"Character: ")
            w1.write(b"Alice\n")
            await w1.drain()

            await r2.readline()
            await r2.readuntil(b"Account: ")
            w2.write(b"Bob\n")
            await w2.drain()
            await r2.readuntil(b"Password: ")
            w2.write(b"pw\n")
            await w2.drain()
            await r2.readuntil(b"Character: ")
            w2.write(b"Bob\n")
            await w2.drain()

            await asyncio.wait_for(r1.readuntil(b"> "), timeout=1)
            await asyncio.wait_for(r2.readuntil(b"> "), timeout=1)

            w1.write(b"say hi\n")
            await w1.drain()
            await asyncio.wait_for(
                r1.readuntil(b"> "),
                timeout=1,
            )  # flush own response

            msg = await asyncio.wait_for(r2.readuntil(b"\r\n"), timeout=1)
            assert b"Alice says, 'hi'" in msg

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
