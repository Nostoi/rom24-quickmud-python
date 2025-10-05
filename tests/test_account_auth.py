import asyncio
import json
from contextlib import suppress
from pathlib import Path

from mud.account.account_service import (
    LoginFailureReason,
    clear_active_accounts,
    create_account,
    create_character,
    get_creation_classes,
    get_creation_races,
    get_race_archetype,
    finalize_creation_stats,
    list_characters,
    login,
    login_with_host,
    lookup_creation_class,
    lookup_creation_race,
    release_account,
)
from mud.models.constants import (
    ActFlag,
    AffectFlag,
    ImmFlag,
    OBJ_VNUM_SCHOOL_DAGGER,
    OBJ_VNUM_SCHOOL_MACE,
    OBJ_VNUM_SCHOOL_SWORD,
    ROOM_VNUM_SCHOOL,
    OffFlag,
    PartFlag,
    ResFlag,
    Size,
    Stat,
    VulnFlag,
    Sex,
)
from mud.db.models import Base, PlayerAccount
from mud.db.session import SessionLocal, engine
from mud.security import bans
from mud.security.bans import BanFlag
from mud.security.hash_utils import verify_password
from mud.world.world_state import reset_lockdowns, set_newlock, set_wizlock
from mud.net.telnet_server import create_server

TELNET_IAC = 255
TELNET_WILL = 251
TELNET_WONT = 252
TELNET_TELOPT_ECHO = 1


def setup_module(module):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()


def test_creation_tables_expose_rom_metadata():
    races = get_creation_races()
    assert [race.name for race in races] == ["human", "elf", "dwarf", "giant"]

    human = lookup_creation_race("Human")
    assert human is not None
    assert human.points == 0
    assert human.bonus_skills == ()
    assert human.base_stats == (13, 13, 13, 13, 13)
    assert human.max_stats == (18, 18, 18, 18, 18)
    assert human.size is Size.MEDIUM

    dwarf = lookup_creation_race("DWARF")
    assert dwarf is not None
    assert dwarf.bonus_skills == ("berserk",)
    assert dwarf.class_multipliers == (150, 100, 125, 100)

    elf_archetype = get_race_archetype("elf")
    assert elf_archetype is not None
    assert elf_archetype.affect_flags & AffectFlag.INFRARED
    assert elf_archetype.resistance_flags & ResFlag.CHARM
    assert elf_archetype.vulnerability_flags & VulnFlag.IRON

    classes = get_creation_classes()
    assert [cls.name for cls in classes] == ["mage", "cleric", "thief", "warrior"]

    mage = lookup_creation_class("MAGE")
    assert mage is not None
    assert mage.prime_stat is Stat.INT
    assert mage.first_weapon_vnum == OBJ_VNUM_SCHOOL_DAGGER
    assert mage.guild_vnums == (3018, 9618)
    assert mage.gains_mana is True

    warrior = lookup_creation_class("warrior")
    assert warrior is not None
    assert warrior.first_weapon_vnum == OBJ_VNUM_SCHOOL_SWORD
    assert warrior.hp_min == 11 and warrior.hp_max == 15
    assert warrior.gains_mana is False

    cleric = lookup_creation_class("cleric")
    assert cleric is not None
    assert cleric.first_weapon_vnum == OBJ_VNUM_SCHOOL_MACE
    assert cleric.prime_stat is Stat.WIS


def test_race_archetype_exposes_npc_flags():
    troll = get_race_archetype("troll")
    assert troll is not None and not troll.is_playable
    assert troll.affect_flags & AffectFlag.REGENERATION
    assert troll.offensive_flags & OffFlag.BERSERK
    assert troll.resistance_flags & ResFlag.CHARM
    assert troll.resistance_flags & ResFlag.BASH
    assert troll.vulnerability_flags & VulnFlag.FIRE
    assert troll.vulnerability_flags & VulnFlag.ACID
    assert troll.part_flags & PartFlag.CLAWS

    doll = get_race_archetype("doll")
    assert doll is not None and not doll.is_playable
    assert doll.immunity_flags & ImmFlag.COLD
    assert doll.immunity_flags & ImmFlag.MENTAL
    assert doll.resistance_flags & ResFlag.BASH
    assert doll.vulnerability_flags & VulnFlag.FIRE

    school_monster = get_race_archetype("school monster")
    assert school_monster is not None and not school_monster.is_playable
    assert school_monster.act_flags & ActFlag.NOALIGN
    assert school_monster.immunity_flags & ImmFlag.CHARM
    assert school_monster.vulnerability_flags & VulnFlag.MAGIC


def test_new_character_creation_sequence():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    session = SessionLocal()
    try:
        assert session.query(PlayerAccount).count() == 0
    finally:
        session.close()

    stats_holder: dict[str, bytes] = {}

    async def run() -> None:
        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)

            welcome = await reader.readline()
            assert welcome.startswith(b"Welcome to PythonMUD")

            await asyncio.wait_for(reader.readuntil(b"Account: "), timeout=5)
            writer.write(b"rookie\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"(Y/N) "), timeout=5)
            writer.write(b"y\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"New password: "), timeout=5)
            writer.write(b"secret\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Confirm password: "), timeout=5)
            writer.write(b"secret\r\n")
            await writer.drain()

            assert await asyncio.wait_for(reader.readline(), timeout=5) == b"Account created.\r\n"

            await asyncio.wait_for(reader.readuntil(b"Character: "), timeout=5)
            writer.write(b"Nova\r\n")
            await writer.drain()

            assert await asyncio.wait_for(reader.readline(), timeout=5) == b"Creating new character 'Nova'.\r\n"
            await asyncio.wait_for(reader.readuntil(b"(Y/N) "), timeout=5)
            writer.write(b"y\r\n")
            await writer.drain()

            assert await asyncio.wait_for(reader.readline(), timeout=5) == b"Available races: Human, Elf, Dwarf, Giant\r\n"
            await asyncio.wait_for(reader.readuntil(b"Choose your race: "), timeout=5)
            writer.write(b"elf\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Sex (M/F): "), timeout=5)
            writer.write(b"F\r\n")
            await writer.drain()

            assert await asyncio.wait_for(reader.readline(), timeout=5) == b"Available classes: Mage, Cleric, Thief, Warrior\r\n"
            await asyncio.wait_for(reader.readuntil(b"Choose your class: "), timeout=5)
            writer.write(b"mage\r\n")
            await writer.drain()

            # Alignment prompt
            assert await asyncio.wait_for(reader.readline(), timeout=5) == b"\r\n"
            assert await asyncio.wait_for(reader.readline(), timeout=5) == (
                b"You may be good, neutral, or evil.\r\n"
            )
            await asyncio.wait_for(reader.readuntil(b"Which alignment (G/N/E)? "), timeout=5)
            writer.write(b"g\r\n")
            await writer.drain()

            # Customization prompt (defaulting to no)
            assert await asyncio.wait_for(reader.readline(), timeout=5) == b"\r\n"
            assert await asyncio.wait_for(reader.readline(), timeout=5) == (
                b"Do you wish to customize this character?\r\n"
            )
            assert await asyncio.wait_for(reader.readline(), timeout=5) == (
                b"Customization takes time, but allows a wider range of skills and abilities.\r\n"
            )
            await asyncio.wait_for(reader.readuntil(b"Customize (Y/N)? "), timeout=5)
            writer.write(b"n\r\n")
            await writer.drain()

            stats_line = await asyncio.wait_for(reader.readline(), timeout=5)
            assert stats_line.startswith(b"Rolled stats: ")
            stats_holder["rolled"] = stats_line
            await asyncio.wait_for(reader.readuntil(b"(K to keep, R to reroll): "), timeout=5)
            writer.write(b"k\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"(Y/N) "), timeout=5)
            writer.write(b"y\r\n")
            await writer.drain()

            line = await asyncio.wait_for(reader.readline(), timeout=5)
            assert line.startswith(b"Starting weapons: ")
            await asyncio.wait_for(reader.readuntil(b"Choose your starting weapon: "), timeout=5)
            writer.write(b"dagger\r\n")
            await writer.drain()

            assert await asyncio.wait_for(reader.readline(), timeout=5) == b"Character created!\r\n"
            look_blob = await asyncio.wait_for(reader.readuntil(b"> "), timeout=5)
            assert b"Merc Mud School" in look_blob or b"You are floating in a void" in look_blob

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
        db_char = session.query(PlayerAccount).filter_by(username="rookie").first()
        assert db_char is not None
        assert db_char.characters
        created = db_char.characters[0]
        assert created.name == "Nova"
        assert created.race == 1  # elf
        assert created.ch_class == 0  # mage
        assert created.sex == int(Sex.FEMALE)
        assert created.hometown_vnum == ROOM_VNUM_SCHOOL
        assert created.alignment == 750
        assert created.creation_points == 45
        groups = json.loads(created.creation_groups)
        assert "rom basics" in groups
        assert "mage basics" in groups
        assert "mage default" in groups
        stats = json.loads(created.perm_stats)
        assert len(stats) == 5

        rolled = stats_holder["rolled"].decode()
        base_stats = [int(part.split()[1]) for part in rolled.split(": ")[1].split(", ")]
        race = lookup_creation_race("elf")
        class_type = lookup_creation_class("mage")
        assert race is not None and class_type is not None
        expected_stats = finalize_creation_stats(race, class_type, base_stats)
        assert stats == expected_stats
        assert created.default_weapon_vnum == OBJ_VNUM_SCHOOL_DAGGER
        assert created.practice == 5
        assert created.train == 3
    finally:
        session.close()


def test_creation_prompts_include_alignment_and_groups():
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
            await asyncio.wait_for(reader.readuntil(b"Account: "), timeout=5)
            writer.write(b"scribe\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"(Y/N) "), timeout=5)
            writer.write(b"y\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"New password: "), timeout=5)
            writer.write(b"secret\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Confirm password: "), timeout=5)
            writer.write(b"secret\r\n")
            await writer.drain()
            await reader.readline()

            await asyncio.wait_for(reader.readuntil(b"Character: "), timeout=5)
            writer.write(b"Lyra\r\n")
            await writer.drain()

            await reader.readline()
            await asyncio.wait_for(reader.readuntil(b"(Y/N) "), timeout=5)
            writer.write(b"y\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readline(), timeout=5)
            await asyncio.wait_for(reader.readuntil(b"Choose your race: "), timeout=5)
            writer.write(b"human\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Sex (M/F): "), timeout=5)
            writer.write(b"M\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readline(), timeout=5)
            await asyncio.wait_for(reader.readuntil(b"Choose your class: "), timeout=5)
            writer.write(b"mage\r\n")
            await writer.drain()

            # Alignment selection (choose evil)
            await reader.readline()
            await reader.readline()
            await asyncio.wait_for(reader.readuntil(b"Which alignment (G/N/E)? "), timeout=5)
            writer.write(b"e\r\n")
            await writer.drain()

            # Opt into customization
            await reader.readline()
            await reader.readline()
            await reader.readline()
            await asyncio.wait_for(reader.readuntil(b"Customize (Y/N)? "), timeout=5)
            writer.write(b"y\r\n")
            await writer.drain()

            # Customization menu interactions
            await reader.readline()
            existing = await reader.readline()
            assert b"rom basics" in existing and b"mage basics" in existing
            await reader.readline()
            await asyncio.wait_for(reader.readuntil(b"Customization> "), timeout=5)
            writer.write(b"add mage default\r\n")
            await writer.drain()
            assert await asyncio.wait_for(reader.readline(), timeout=5) == b"Mage Default group added.\r\n"
            assert await asyncio.wait_for(reader.readline(), timeout=5) == b"Creation points: 40\r\n"
            await asyncio.wait_for(reader.readuntil(b"Customization> "), timeout=5)
            writer.write(b"done\r\n")
            await writer.drain()
            assert await asyncio.wait_for(reader.readline(), timeout=5) == b"Creation points: 40\r\n"

            # Continue with stats and character confirmation
            stats_line = await asyncio.wait_for(reader.readline(), timeout=5)
            assert stats_line.startswith(b"Rolled stats: ")
            await asyncio.wait_for(reader.readuntil(b"(K to keep, R to reroll): "), timeout=5)
            writer.write(b"k\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"(Y/N) "), timeout=5)
            writer.write(b"y\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Choose your starting weapon: "), timeout=5)
            writer.write(b"dagger\r\n")
            await writer.drain()

            await reader.readline()

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
        account = session.query(PlayerAccount).filter_by(username="scribe").first()
        assert account is not None and account.characters
        created = account.characters[0]
        assert created.alignment == -750
        assert created.creation_points == 40
        groups = json.loads(created.creation_groups)
        assert "rom basics" in groups
        assert "mage basics" in groups
        assert "mage default" in groups
        assert created.train == 3
    finally:
        session.close()


def test_password_prompt_hides_echo():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("sentinel", "secret")
    account = login("sentinel", "secret")
    assert account is not None
    assert create_character(account, "lookout")

    async def run() -> None:
        server = await create_server(host="127.0.0.1", port=0)
        host, port = server.sockets[0].getsockname()
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)

            greeting = await reader.readuntil(b"Account: ")
            assert bytes([TELNET_IAC, TELNET_WONT, TELNET_TELOPT_ECHO]) in greeting

            writer.write(b"sentinel\r\n")
            await writer.drain()

            password_prompt = await reader.readuntil(b"Password: ")
            assert bytes([TELNET_IAC, TELNET_WILL, TELNET_TELOPT_ECHO]) in password_prompt

            writer.write(b"secret\r\n")
            await writer.drain()

            post_login = await reader.readuntil(b"Character: ")
            assert b"secret" not in post_login
            assert bytes([TELNET_IAC, TELNET_WONT, TELNET_TELOPT_ECHO]) in post_login

            writer.close()
            await writer.wait_closed()
        finally:
            server.close()
            await server.wait_closed()
            server_task.cancel()
            with suppress(asyncio.CancelledError):
                await server_task

    asyncio.run(run())


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


def test_denied_account_cannot_login(tmp_path):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("denied", "pw")

    path = tmp_path / "ban.txt"
    bans.add_banned_account("denied")
    bans.save_bans_file(path)
    bans.clear_all_bans()
    bans.load_bans_file(path)

    blocked = login_with_host("denied", "pw", None)
    assert blocked.account is None
    assert blocked.failure is LoginFailureReason.ACCOUNT_BANNED


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
