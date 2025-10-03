import asyncio
from contextlib import suppress
from pathlib import Path

from mud.account.account_service import (
    LoginFailureReason,
    clear_active_accounts,
    create_account,
    create_character,
    list_characters,
    login,
    login_with_host,
    release_account,
)
from mud.db.models import Base, PlayerAccount
from mud.db.session import SessionLocal, engine
from mud.security import bans
from mud.security.bans import BanFlag
from mud.security.hash_utils import verify_password
from mud.world.world_state import reset_lockdowns, set_newlock, set_wizlock
from mud.net.telnet_server import create_server


def setup_module(module):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()


def test_illegal_name_rejected():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    async def run() -> None:
        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)
            await reader.readline()
            await reader.readuntil(b"Account: ")
            writer.write(b"self\n")
            await writer.drain()

            response = await asyncio.wait_for(
                reader.readuntil(b"Account: "),
                timeout=1,
            )
            assert b"Illegal name, try another." in response

            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
        finally:
            server.close()
            await server.wait_closed()
            server_task.cancel()
            with suppress(asyncio.CancelledError):
                await server_task

    asyncio.run(run())

    session = SessionLocal()
    try:
        assert session.query(PlayerAccount).filter_by(username="self").first() is None
    finally:
        session.close()


def test_account_create_and_login():
    assert create_account("alice", "secret")
    assert not create_account("alice", "other")

    account = login("alice", "secret")
    assert account is not None
    assert login("alice", "bad") is None

    # check hash format
    session = SessionLocal()
    db_acc = session.query(PlayerAccount).filter_by(username="alice").first()
    assert db_acc and ":" in db_acc.password_hash
    assert verify_password("secret", db_acc.password_hash)
    session.close()

    assert create_character(account, "Hero")
    account = login("alice", "secret")
    chars = list_characters(account)
    assert "Hero" in chars


def test_banned_account_cannot_login():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()

    assert create_account("bob", "pw")
    bans.add_banned_account("bob")
    # Direct login should be refused for banned account
    assert login("bob", "pw") is None


def test_banned_host_cannot_login():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("carol", "pw")
    bans.add_banned_host("203.0.113.9")
    # Host-aware login wrapper should reject banned host
    result = login_with_host("carol", "pw", "203.0.113.9")
    assert result.account is None
    assert result.failure is LoginFailureReason.HOST_BANNED
    # Non-banned host should allow login
    account = login_with_host("carol", "pw", "198.51.100.20").account
    assert account is not None
    release_account("carol")


def test_permanent_ban_survives_restart(tmp_path):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    bans.add_banned_host("203.0.113.9")
    original_file = bans.BANS_FILE
    path = tmp_path / "bans.txt"
    bans.BANS_FILE = path
    try:
        bans.save_bans_file()
        bans.clear_all_bans()

        async def run() -> None:
            server = await create_server(host="127.0.0.1", port=0)
            server.close()
            await server.wait_closed()

        asyncio.run(run())
    finally:
        bans.BANS_FILE = original_file

    assert bans.is_host_banned("203.0.113.9")


def test_ban_persistence_roundtrip(tmp_path):
    # Arrange
    bans.clear_all_bans()
    bans.add_banned_host("bad.example")
    bans.add_banned_host("203.0.113.9")
    path = tmp_path / "ban.txt"

    # Act: save → clear → load
    bans.save_bans_file(path)
    text = path.read_text()
    assert "bad.example" in text and "203.0.113.9" in text
    bans.clear_all_bans()
    loaded = bans.load_bans_file(path)

    # Assert
    assert loaded == 2
    assert bans.is_host_banned("bad.example")
    assert bans.is_host_banned("203.0.113.9")


def test_ban_persistence_includes_flags(tmp_path):
    bans.clear_all_bans()
    bans.add_banned_host("*wildcard*")
    bans.add_banned_host("allow.me", flags=BanFlag.PERMIT, level=50)
    bans.add_banned_host("*example.com", flags=BanFlag.NEWBIES, level=60)
    path = tmp_path / "ban.lst"

    bans.save_bans_file(path)

    expected = Path("tests/data/ban_sample.golden.txt").read_text()
    assert path.read_text() == expected


def test_ban_file_round_trip_levels(tmp_path):
    bans.clear_all_bans()
    bans.add_banned_host("*wildcard*")
    bans.add_banned_host("allow.me", flags=BanFlag.PERMIT, level=50)
    bans.add_banned_host("*example.com", flags=BanFlag.NEWBIES, level=60)
    path = tmp_path / "ban.lst"
    bans.save_bans_file(path)

    bans.clear_all_bans()
    loaded = bans.load_bans_file(path)

    assert loaded == 3
    entries = {entry.pattern: entry for entry in bans.get_ban_entries()}
    assert "wildcard" in entries and entries["wildcard"].level == 0
    assert entries["wildcard"].flags & BanFlag.SUFFIX
    assert entries["wildcard"].flags & BanFlag.PREFIX
    assert "allow.me" in entries and entries["allow.me"].level == 50
    assert entries["allow.me"].flags & BanFlag.PERMIT
    assert "example.com" in entries and entries["example.com"].level == 60
    assert entries["example.com"].flags & BanFlag.NEWBIES
    assert entries["example.com"].flags & BanFlag.PREFIX


def test_ban_file_round_trip_preserves_order(tmp_path):
    bans.clear_all_bans()
    bans.add_banned_host("first.example")
    bans.add_banned_host("second.example")
    path = tmp_path / "ban.lst"

    bans.save_bans_file(path)
    original = path.read_text()

    bans.clear_all_bans()
    bans.load_bans_file(path)
    bans.save_bans_file(path)

    assert path.read_text() == original
    assert [entry.pattern for entry in bans.get_ban_entries()] == [
        "second.example",
        "first.example",
    ]


def test_remove_banned_host_ignores_wildcard_markers():
    bans.clear_all_bans()
    bans.add_banned_host("*example.com")
    assert bans.is_host_banned("foo.example.com")
    bans.remove_banned_host("example.com")
    assert not bans.is_host_banned("foo.example.com")


def test_ban_prefix_suffix_types():
    bans.clear_all_bans()
    bans.add_banned_host("*example.com")
    assert bans.is_host_banned("foo.example.com")
    assert not bans.is_host_banned("example.org")

    bans.clear_all_bans()
    bans.add_banned_host("example.*")
    assert bans.is_host_banned("example.net")
    assert not bans.is_host_banned("demoexample.net")

    bans.clear_all_bans()
    bans.add_banned_host("*malicious*")
    assert bans.is_host_banned("verymalicioushost.net")
    assert not bans.is_host_banned("innocent.net")


def test_wizlock_blocks_mortals():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("mortal", "pw")
    account = login_with_host("mortal", "pw", None).account
    assert account is not None
    release_account("mortal")

    set_wizlock(True)
    try:
        blocked = login_with_host("mortal", "pw", None)
        assert blocked.account is None
        assert blocked.failure is LoginFailureReason.WIZLOCK

        assert create_account("immortal", "pw")
        session = SessionLocal()
        try:
            imm = session.query(PlayerAccount).filter_by(username="immortal").first()
            assert imm is not None
            imm.is_admin = True
            session.commit()
        finally:
            session.close()

        admin = login_with_host("immortal", "pw", None).account
        assert admin is not None
    finally:
        release_account("immortal")
        set_wizlock(False)


def test_newlock_blocks_new_accounts():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("elder", "pw")
    account = login_with_host("elder", "pw", None).account
    assert account is not None
    release_account("elder")

    set_newlock(True)
    try:
        account = login_with_host("elder", "pw", None).account
        assert account is not None
        release_account("elder")

        blocked = login_with_host("brand", "pw", None)
        assert blocked.account is None
        assert blocked.failure is LoginFailureReason.NEWLOCK
        
        async def run_connection_check() -> None:
            server = await create_server(host="127.0.0.1", port=0)
            host, port = server.sockets[0].getsockname()
            server_task = asyncio.create_task(server.serve_forever())
            try:
                set_newlock(True)
                reader, writer = await asyncio.open_connection(host, port)
                await reader.readline()
                await reader.readuntil(b"Account: ")
                writer.write(b"brand\n")
                await writer.drain()
                await reader.readuntil(b"Password: ")
                writer.write(b"pw\n")
                await writer.drain()

                message = await asyncio.wait_for(reader.readline(), timeout=1)
                assert b"The game is newlocked." in message

                writer.close()
                with suppress(Exception):
                    await writer.wait_closed()
            finally:
                server.close()
                await server.wait_closed()
                server_task.cancel()
                with suppress(asyncio.CancelledError):
                    await server_task

        asyncio.run(run_connection_check())

        session = SessionLocal()
        try:
            assert session.query(PlayerAccount).filter_by(username="brand").first() is None
        finally:
            session.close()

        assert not create_account("brand", "pw")
    finally:
        set_newlock(False)
        clear_active_accounts()


def test_duplicate_login_requires_reconnect_consent():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("dup", "pw")
    first = login_with_host("dup", "pw", None).account
    assert first is not None
    blocked = login_with_host("dup", "pw", None)
    assert blocked.account is None
    assert blocked.failure is LoginFailureReason.DUPLICATE_SESSION

    reconnect = login_with_host("dup", "pw", None, allow_reconnect=True).account
    assert reconnect is not None
    release_account("dup")


def test_newbie_permit_enforcement():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("elder", "pw")

    bans.add_banned_host("blocked.example", flags=BanFlag.NEWBIES)
    account = login_with_host("elder", "pw", "blocked.example").account
    assert account is not None
    release_account("elder")
    blocked = login_with_host("fresh", "pw", "blocked.example")
    assert blocked.account is None
    assert blocked.failure is LoginFailureReason.HOST_NEWBIES
    session = SessionLocal()
    try:
        assert session.query(PlayerAccount).filter_by(username="fresh").first() is None
    finally:
        session.close()

    bans.clear_all_bans()
    bans.add_banned_host("locked.example", flags=BanFlag.ALL)
    locked = login_with_host("elder", "pw", "locked.example")
    assert locked.account is None
    assert locked.failure is LoginFailureReason.HOST_BANNED

    bans.add_banned_host("locked.example", flags=BanFlag.PERMIT)
    account = login_with_host("elder", "pw", "locked.example").account
    assert account is not None
    release_account("elder")
