import asyncio
from contextlib import suppress

from mud.db.models import Base
from mud.db.session import engine
from mud.net.telnet_server import create_server


def setup_module(module):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_scripted_session_runs_basic_commands():
    async def run():
        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)
            # greeting and login handshake
            assert b"Welcome" in await reader.readline()
            await reader.readline()  # username prompt
            writer.write(b"Tester\n")
            await writer.drain()
            await reader.readline()  # password prompt
            writer.write(b"secret\n")
            await writer.drain()
            await reader.readline()  # character prompt
            writer.write(b"Tester\n")
            await writer.drain()
            await reader.readuntil(b"> ")  # initial prompt

            # look at the starting room
            writer.write(b"look\n")
            await writer.drain()
            text = (await reader.readuntil(b"> ")).decode()
            assert (
                "Temple Of Mota" in text
                or "Limbo" in text
                or "Void" in text
            )

            # move north and confirm the new room title
            writer.write(b"north\n")
            await writer.drain()
            text = (await reader.readuntil(b"> ")).decode()
            assert "Altar" in text or "Temple" in text

            # say something and ensure it echoes back
            writer.write(b"say hi\n")
            await writer.drain()
            text = (await reader.readuntil(b"> ")).decode()
            assert "Tester says, 'hi'" in text

            writer.close()
            await writer.wait_closed()
        finally:
            server.close()
            await server.wait_closed()
            server_task.cancel()
            with suppress(asyncio.CancelledError):
                await server_task

    asyncio.run(run())
