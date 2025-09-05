import asyncio
from contextlib import suppress

from mud.db.models import Base, PlayerAccount, Character
from mud.db.session import engine, SessionLocal
from mud.net.telnet_server import create_server


def setup_module(module):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_login_creates_account_and_character():
    async def run():
        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)
            await reader.readline()  # welcome
            await reader.readline()  # username prompt
            writer.write(b"alice\n")
            await writer.drain()
            await reader.readline()  # password prompt
            writer.write(b"secret\n")
            await writer.drain()
            await reader.readline()  # character name prompt
            writer.write(b"Hero\n")
            await writer.drain()
            await reader.readuntil(b"> ")
            writer.close()
            await writer.wait_closed()
        finally:
            server.close()
            await server.wait_closed()
            server_task.cancel()
            with suppress(asyncio.CancelledError):
                await server_task

    asyncio.run(run())

    session = SessionLocal()
    account = session.query(PlayerAccount).filter_by(username="alice").first()
    assert account is not None
    char = session.query(Character).filter_by(name="Hero").first()
    assert char is not None
    session.close()
