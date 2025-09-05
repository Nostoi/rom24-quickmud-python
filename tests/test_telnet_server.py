import asyncio
from contextlib import suppress

from mud.db.models import Base
from mud.db.session import engine
from mud.net.telnet_server import create_server


def setup_module(module):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_telnet_server_handles_look_command():
    async def run():
        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)
            # greeting and login
            assert b"Welcome" in await reader.readline()
            await reader.readline()  # username prompt
            writer.write(b"Tester\n")
            await writer.drain()
            await reader.readline()  # password prompt
            writer.write(b"secret\n")
            await writer.drain()
            await reader.readline()  # character name prompt
            writer.write(b"Tester\n")
            await writer.drain()
            await reader.readuntil(b"> ")
            # issue a look command and expect room title in response
            writer.write(b"look\n")
            await writer.drain()
            output = await reader.readuntil(b"> ")
            text = output.decode()
            assert (
                "The Temple Of Mota" in text
                or "Limbo" in text
                or "Void" in text
            )
            writer.close()
            await writer.wait_closed()
        finally:
            server.close()
            await server.wait_closed()
            server_task.cancel()
            with suppress(asyncio.CancelledError):
                await server_task

    asyncio.run(run())


def test_telnet_server_handles_multiple_connections():
    async def run():
        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            r1, w1 = await asyncio.open_connection(host, port)
            r2, w2 = await asyncio.open_connection(host, port)

            # greetings and login
            await r1.readline()
            await r1.readline()
            w1.write(b"Alice\n")
            await w1.drain()
            await r1.readline()
            w1.write(b"pw\n")
            await w1.drain()
            await r1.readline()
            w1.write(b"Alice\n")
            await w1.drain()

            await r2.readline()
            await r2.readline()
            w2.write(b"Bob\n")
            await w2.drain()
            await r2.readline()
            w2.write(b"pw\n")
            await w2.drain()
            await r2.readline()
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
