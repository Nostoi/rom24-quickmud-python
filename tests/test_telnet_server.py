import asyncio
from contextlib import suppress

from mud.net.telnet_server import create_server


def test_telnet_server_handles_look_command():
    async def run():
        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)
            # greeting
            assert b"Welcome" in await reader.readline()
            await reader.readline()  # name prompt
            writer.write(b"Tester\n")
            await writer.drain()
            await reader.readuntil(b"> ")
            # issue a look command and expect room title in response
            writer.write(b"look\n")
            await writer.drain()
            output = await reader.readuntil(b"> ")
            text = output.decode()
            assert "The Temple Of Mota" in text or "Limbo" in text or "Void" in text
            writer.close()
            await writer.wait_closed()
        finally:
            server.close()
            await server.wait_closed()
            server_task.cancel()
            with suppress(asyncio.CancelledError):
                await server_task

    asyncio.run(run())
