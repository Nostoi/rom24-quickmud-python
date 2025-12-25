import asyncio
import json
from contextlib import suppress
from pathlib import Path
from socket import socket as Socket
from types import SimpleNamespace
from typing import Sequence, cast

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

import mud.net.connection as net_connection

from mud.account import (
    load_character as load_player_character,
    save_character as save_player_character,
)
from mud.account.account_service import (
    LoginFailureReason,
    CreationSelection,
    clear_active_accounts,
    create_account,
    create_character,
    finalize_creation_stats,
    get_creation_classes,
    get_creation_races,
    get_race_archetype,
    list_characters,
    login,
    login_with_host,
    lookup_creation_class,
    lookup_creation_race,
    release_account,
)
from mud.db.models import Base, Character, PlayerAccount
from mud.db.session import SessionLocal, engine
from mud.skills.groups import get_group
from mud.models.constants import (
    CommFlag,
    DEFAULT_PAGE_LINES,
    OBJ_VNUM_MAP,
    OBJ_VNUM_SCHOOL_BANNER,
    OBJ_VNUM_SCHOOL_DAGGER,
    OBJ_VNUM_SCHOOL_MACE,
    OBJ_VNUM_SCHOOL_SHIELD,
    OBJ_VNUM_SCHOOL_SWORD,
    OBJ_VNUM_SCHOOL_VEST,
    ROOM_VNUM_LIMBO,
    ROOM_VNUM_SCHOOL,
    ActFlag,
    AffectFlag,
    ImmFlag,
    OffFlag,
    PartFlag,
    PlayerFlag,
    ResFlag,
    Sex,
    Size,
    Stat,
    VulnFlag,
)
from mud.models.character import (
    Character as RuntimeCharacter,
    _decode_creation_skills,
    character_registry,
)
from mud.models.room import Room
from mud.net.connection import (
    RECONNECT_MESSAGE,
    _announce_login_or_reconnect,
    _broadcast_reconnect_notifications,
)
from mud.net.session import SESSIONS
from mud.net.telnet_server import create_server
from mud.security import bans
from mud.world import initialize_world
from mud.commands.inventory import give_school_outfit
from mud.security.bans import BanFlag
from mud.security.hash_utils import verify_password
from mud.world.world_state import reset_lockdowns, set_newlock, set_wizlock
from mud.wiznet import WiznetFlag

TELNET_IAC = 255
TELNET_WILL = 251
TELNET_WONT = 252
TELNET_DO = 253
TELNET_DONT = 254
TELNET_GA = 249
TELNET_TELOPT_ECHO = 1


def strip_telnet(data: bytes) -> bytes:
    """Remove telnet protocol sequences from data."""
    result = bytearray()
    i = 0
    while i < len(data):
        if data[i] == TELNET_IAC and i + 1 < len(data):
            cmd = data[i + 1]
            if cmd in (TELNET_WILL, TELNET_WONT, TELNET_DO, TELNET_DONT) and i + 2 < len(data):
                i += 3
            elif cmd == TELNET_GA:
                i += 2
            elif cmd == TELNET_IAC:
                result.append(TELNET_IAC)
                i += 2
            else:
                i += 2
        else:
            result.append(data[i])
            i += 1
    return bytes(result)


async def negotiate_ansi(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, reply: bytes = b""
) -> tuple[bytes, bytes]:
    prompt = await asyncio.wait_for(reader.readuntil(b"Do you want ANSI? (Y/n) "), timeout=5)
    response = reply.strip() if reply else b""
    payload = response + b"\r\n" if response else b"\r\n"
    writer.write(payload)
    await writer.drain()
    greeting = await asyncio.wait_for(reader.readuntil(b"Account: "), timeout=5)
    return prompt, greeting


class _MemoryTransport(asyncio.Transport):
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


async def _make_telnet_stream() -> tuple[net_connection.TelnetStream, _MemoryTransport, asyncio.StreamReaderProtocol]:
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    transport = _MemoryTransport()
    protocol.connection_made(transport)
    writer = asyncio.StreamWriter(transport, protocol, reader, loop)
    return net_connection.TelnetStream(reader, writer), transport, protocol


async def _shutdown_server(server: asyncio.AbstractServer, server_task: asyncio.Task) -> None:
    server.close()
    with suppress(asyncio.TimeoutError):
        await asyncio.wait_for(server.wait_closed(), timeout=2)

    server_task.cancel()
    with suppress(asyncio.CancelledError, asyncio.TimeoutError):
        await asyncio.wait_for(server_task, timeout=2)


def setup_module(module):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()


def test_create_account_defaults_blank_email():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("rookie", "secret")

    session = SessionLocal()
    try:
        record = session.query(PlayerAccount).filter_by(username="rookie").first()
        assert record is not None
        assert record.email == ""
    finally:
        session.close()


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
        host, port = _server_address(server)
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)

            prompt, greeting = await negotiate_ansi(reader, writer)
            assert prompt.endswith(b"(Y/n) ")
            assert b"THIS IS A MUD" in greeting.upper()
            assert b"\x1b[" in greeting

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

            await asyncio.wait_for(reader.readuntil(b"Account created."), timeout=5)

            await asyncio.wait_for(reader.readuntil(b"Character: "), timeout=5)
            writer.write(b"Nova\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Creating new character 'Nova'."), timeout=5)
            await asyncio.wait_for(reader.readuntil(b"(Y/N) "), timeout=5)
            writer.write(b"y\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Available races: Human, Elf, Dwarf, Giant"), timeout=5)
            await asyncio.wait_for(reader.readuntil(b"Choose your race: "), timeout=5)
            writer.write(b"elf\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Sex (M/F): "), timeout=5)
            writer.write(b"F\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Available classes: Mage, Cleric, Thief, Warrior"), timeout=5)
            await asyncio.wait_for(reader.readuntil(b"Choose your class: "), timeout=5)
            writer.write(b"mage\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"You may be good, neutral, or evil."), timeout=5)
            await asyncio.wait_for(reader.readuntil(b"Which alignment (G/N/E)? "), timeout=5)
            writer.write(b"g\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Do you wish to customize this character?"), timeout=5)
            await asyncio.wait_for(reader.readuntil(b"Customize (Y/N)? "), timeout=5)
            writer.write(b"n\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Rolled stats: "), timeout=5)
            stats_line = await asyncio.wait_for(reader.readline(), timeout=5)
            stats_holder["rolled"] = b"Rolled stats: " + stats_line
            await asyncio.wait_for(reader.readuntil(b"(K to keep, R to reroll): "), timeout=5)
            writer.write(b"k\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"(Y/N) "), timeout=5)
            writer.write(b"y\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Starting weapons: "), timeout=5)
            await asyncio.wait_for(reader.readuntil(b"Choose your starting weapon: "), timeout=5)
            writer.write(b"dagger\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Character created!"), timeout=5)
            look_blob = await asyncio.wait_for(reader.readuntil(b"> "), timeout=5)
            assert b"Merc Mud School" in look_blob or b"You are floating in a void" in look_blob

            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
        finally:
            await _shutdown_server(server, server_task)

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
        assert created.creation_points >= 0
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
        assert created.practice >= 0
        assert created.train >= 0
    finally:
        session.close()


def test_new_player_receives_motd():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    async def run() -> None:
        server = await create_server(host="127.0.0.1", port=0)
        host, port = _server_address(server)
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)

            _, greeting = await negotiate_ansi(reader, writer)
            assert b"\x1b[" in greeting

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
            await asyncio.wait_for(reader.readuntil(b"Account created."), timeout=5)

            await asyncio.wait_for(reader.readuntil(b"Character: "), timeout=5)
            writer.write(b"Nova\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Creating new character 'Nova'."), timeout=5)
            await asyncio.wait_for(reader.readuntil(b"(Y/N) "), timeout=5)
            writer.write(b"y\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Choose your race: "), timeout=5)
            writer.write(b"human\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Sex (M/F): "), timeout=5)
            writer.write(b"M\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Choose your class: "), timeout=5)
            writer.write(b"warrior\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Which alignment (G/N/E)? "), timeout=5)
            writer.write(b"n\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Customize (Y/N)? "), timeout=5)
            writer.write(b"n\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"(K to keep, R to reroll): "), timeout=5)
            writer.write(b"k\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"(Y/N) "), timeout=5)
            writer.write(b"y\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Choose your starting weapon: "), timeout=5)
            writer.write(b"sword\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Character created!"), timeout=5)

            look_blob = await asyncio.wait_for(reader.readuntil(b"> "), timeout=5)
            assert (
                b"Merc Mud School" in look_blob
                or b"You are floating in a void" in look_blob
                or b"motd" in look_blob.lower()
            )

            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
        finally:
            await _shutdown_server(server, server_task)

    asyncio.run(run())


def test_immortal_receives_imotd():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("archon", "secret")
    account = login("archon", "secret")
    assert account is not None
    assert create_character(account, "Zeus")

    session = SessionLocal()
    try:
        db_char = session.query(PlayerAccount).filter_by(username="archon").first()
        assert db_char is not None and db_char.characters
        record = db_char.characters[0]
        record.level = 60
        record.trust = 60
        session.commit()
    finally:
        session.close()

    async def run() -> None:
        server = await create_server(host="127.0.0.1", port=0)
        host, port = _server_address(server)
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)

            _, greeting = await negotiate_ansi(reader, writer)
            assert b"\x1b[" in greeting

            writer.write(b"archon\r\n")
            await writer.drain()

            await asyncio.wait_for(reader.readuntil(b"Password: "), timeout=5)
            writer.write(b"secret\r\n")
            await writer.drain()

            selection_prompt = await asyncio.wait_for(reader.readuntil(b"Character: "), timeout=5)
            assert b"Zeus" in selection_prompt
            writer.write(b"Zeus\r\n")
            await writer.drain()

            look_blob = await asyncio.wait_for(reader.readuntil(b"> "), timeout=10)
            assert b"Merc Mud School" in look_blob or b"You are floating in a void" in look_blob or b"Zeus" in look_blob

            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
        finally:
            await _shutdown_server(server, server_task)

    asyncio.run(run())


def test_creation_race_help(monkeypatch: pytest.MonkeyPatch) -> None:
    prompts: list[str] = []
    sent_lines: list[str] = []
    sent_pages: list[str] = []
    help_calls: list[tuple[object, str]] = []

    responses = iter(["help", "help human", "human"])

    async def fake_prompt(conn, prompt, *, hide_input=False):
        del hide_input
        prompts.append(prompt)
        try:
            return next(responses)
        except StopIteration:
            return None

    async def fake_send_line(conn, message):
        sent_lines.append(message)

    async def fake_send(conn, message):
        sent_pages.append(message)

    def fake_do_help(char, topic, *, limit_results=False):
        help_calls.append((char, topic))
        mapping = {
            "race help": "Race overview text",
            "human": "Human details",
        }
        return mapping.get(topic, "")

    helper = SimpleNamespace(name="Lyra", trust=0, level=0, is_npc=False, room=None)

    monkeypatch.setattr(net_connection, "_prompt", fake_prompt)
    monkeypatch.setattr(net_connection, "_send_line", fake_send_line)
    monkeypatch.setattr(net_connection, "_send", fake_send)
    monkeypatch.setattr(net_connection, "do_help", fake_do_help)

    async def run() -> None:
        race = await net_connection._prompt_for_race(object(), helper)
        assert race is not None
        assert race.name == "human"

    asyncio.run(run())

    assert prompts == ["Choose your race: ", "Choose your race: ", "Choose your race: "]
    assert sent_lines[:2] == [
        "Available races: " + ", ".join(r.name.title() for r in get_creation_races()),
        "What is your race? (help for more information)",
    ]
    assert sent_pages == ["Race overview text\r\n", "Human details\r\n"]
    assert help_calls == [(helper, "race help"), (helper, "human")]


def test_creation_prompts_include_alignment_and_groups(monkeypatch: pytest.MonkeyPatch):
    prompts: list[str] = []
    yes_no_prompts: list[str] = []
    sent_lines: list[str] = []
    sent_pages: list[str] = []
    selections: list[CreationSelection] = []

    responses = iter(["e", "add weaponsmaster", "add shield block", "done"])

    async def fake_prompt(conn, prompt, *, hide_input=False):
        del conn, hide_input
        prompts.append(prompt)
        try:
            return next(responses)
        except StopIteration:
            return "done"

    async def fake_prompt_yes_no(conn, prompt):
        del conn
        yes_no_prompts.append(prompt)
        return True

    async def fake_send_line(conn, message):
        del conn
        sent_lines.append(message)

    async def fake_send(conn, message):
        del conn
        sent_pages.append(message)

    def fake_do_help(char, topic, *, limit_results=False):
        del char, limit_results
        if topic.lower() == "group header":
            return "Group header text\r\n"
        return ""

    monkeypatch.setattr(net_connection, "_prompt", fake_prompt)
    monkeypatch.setattr(net_connection, "_prompt_yes_no", fake_prompt_yes_no)
    monkeypatch.setattr(net_connection, "_send_line", fake_send_line)
    monkeypatch.setattr(net_connection, "_send", fake_send)
    monkeypatch.setattr(net_connection, "do_help", fake_do_help)

    async def run() -> None:
        conn, transport, protocol = await _make_telnet_stream()
        selection = CreationSelection(get_creation_races()[0], get_creation_classes()[0])
        selections.append(selection)
        try:
            alignment = await net_connection._prompt_for_alignment(conn)
            assert alignment == -750
            customize = await net_connection._prompt_customization_choice(conn)
            assert customize is True
            result = await net_connection._run_customization_menu(conn, selection)
            assert result is selection
        finally:
            transport.close()
            protocol.connection_lost(None)

    asyncio.run(run())

    assert prompts[:4] == [
        "Which alignment (G/N/E)? ",
        "Customization> ",
        "Customization> ",
        "Customization> ",
    ]
    assert yes_no_prompts == ["Customize (Y/N)? "]

    normalized_lines = [line for line in sent_lines if line]
    assert "You may be good, neutral, or evil." in normalized_lines
    assert any(line.startswith("Creation points: ") for line in normalized_lines)
    assert "Creation points: 40" in normalized_lines
    assert "Creation points: 46" in normalized_lines
    assert "Experience per level: 1000" in normalized_lines
    assert "Experience per level: 1300" in normalized_lines
    assert any("Type 'list', 'learned', 'add <group>'" in line for line in normalized_lines)
    assert any("You already have the following groups" in line for line in normalized_lines)

    assert any("Group header text" in entry for entry in sent_pages)

    assert selections, "selection should be captured"
    final_selection = selections[0]
    assert final_selection.creation_points == 46
    assert final_selection.has_group("weaponsmaster")
    assert final_selection.has_skill("shield block")


def test_customization_menu_shows_group_header_and_costs(monkeypatch: pytest.MonkeyPatch):
    async def run() -> None:
        conn, transport, protocol = await _make_telnet_stream()
        selection = CreationSelection(get_creation_races()[0], get_creation_classes()[0])

        def fake_do_help(char, topic, *, limit_results=False):
            del char, limit_results
            if topic.lower() == "group header":
                return "Group header text\r\n"
            return ""

        monkeypatch.setattr(net_connection, "do_help", fake_do_help)

        try:
            menu_task = asyncio.create_task(net_connection._run_customization_menu(conn, selection))
            await asyncio.sleep(0)

            initial = transport.buffer.decode(errors="ignore")
            assert "Group header text" in initial
            assert "group              cp" in initial.lower()
            assert "skill              cp" in initial.lower()
            assert "Creation points: 0" in initial
            assert "Experience per level: 1000" in initial
            assert "Type 'list', 'learned', 'add <group>', 'drop <group>'" in initial

            menu_task.cancel()
            with suppress(asyncio.CancelledError):
                await menu_task
        finally:
            transport.close()
            protocol.connection_lost(None)

    asyncio.run(run())


def test_customization_menu_repeats_menu_choice_help(monkeypatch: pytest.MonkeyPatch):
    async def run() -> None:
        conn, transport, protocol = await _make_telnet_stream()
        selection = CreationSelection(get_creation_races()[0], get_creation_classes()[0])

        def fake_do_help(char, topic, *, limit_results: bool = False):
            del char, limit_results
            lowered = topic.lower()
            if lowered == "group header":
                return "Group header text\r\n"
            if lowered == "menu choice":
                return "Menu choice text\r\n"
            return ""

        monkeypatch.setattr(net_connection, "do_help", fake_do_help)

        try:
            menu_task = asyncio.create_task(net_connection._run_customization_menu(conn, selection))
            await asyncio.sleep(0)

            initial = transport.buffer.decode(errors="ignore")
            assert initial.count("Menu choice text") >= 1

            transport.buffer.clear()
            protocol.data_received(b"list\r\n")
            await asyncio.sleep(0)
            list_output = transport.buffer.decode(errors="ignore")
            assert "Menu choice text" in list_output

            transport.buffer.clear()
            protocol.data_received(b"help\r\n")
            await asyncio.sleep(0)
            help_output = transport.buffer.decode(errors="ignore")
            assert "Menu choice text" in help_output
        finally:
            menu_task.cancel()
            with suppress(asyncio.CancelledError):
                await menu_task
            transport.close()
            protocol.connection_lost(None)

    asyncio.run(run())


def test_customization_requires_forty_creation_points():
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

    async def make_telnet_stream() -> tuple[net_connection.TelnetStream, MemoryTransport, asyncio.StreamReaderProtocol]:
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        transport = MemoryTransport()
        protocol.connection_made(transport)
        writer = asyncio.StreamWriter(transport, protocol, reader, loop)
        return net_connection.TelnetStream(reader, writer), transport, protocol

    async def run() -> None:
        conn, transport, protocol = await make_telnet_stream()
        selection = CreationSelection(get_creation_races()[0], get_creation_classes()[0])

        menu_task = asyncio.create_task(net_connection._run_customization_menu(conn, selection))
        await asyncio.sleep(0)

        initial_output = transport.buffer.decode(errors="ignore")
        assert "Customization> " in initial_output

        transport.buffer.clear()
        protocol.data_received(b"done\r\n")
        await asyncio.sleep(0)
        insufficient = transport.buffer.decode(errors="ignore")
        assert "You must select at least" in insufficient
        assert "Customization> " in insufficient

        transport.buffer.clear()
        protocol.data_received(b"add creation\r\n")
        await asyncio.sleep(0)
        added_small = transport.buffer.decode(errors="ignore")
        assert "creation group added." in added_small.lower()
        assert "Creation points: 4" in added_small
        assert "Experience per level: 1000" in added_small
        assert "Customization> " in added_small

        transport.buffer.clear()
        protocol.data_received(b"done\r\n")
        await asyncio.sleep(0)
        still_short = transport.buffer.decode(errors="ignore")
        assert "You must select at least" in still_short
        assert "need 36 more" in still_short
        assert "Customization> " in still_short

        transport.buffer.clear()
        protocol.data_received(b"add weaponsmaster\r\n")
        await asyncio.sleep(0)
        added_default = transport.buffer.decode(errors="ignore")
        assert "weaponsmaster group added." in added_default.lower()
        assert "Creation points: 44" in added_default
        assert "Experience per level: 1200" in added_default
        assert "Customization> " in added_default

        transport.buffer.clear()
        protocol.data_received(b"done\r\n")
        result = await asyncio.wait_for(menu_task, timeout=1)
        final_output = transport.buffer.decode(errors="ignore")
        assert "Creation points: 44" in final_output
        assert "Experience per level: 1200" in final_output
        assert result is selection
        assert result.creation_points == 44
        assert result.minimum_creation_points() == 40

        transport.close()
        protocol.connection_lost(None)

    asyncio.run(run())


def test_customization_menu_supports_drop_and_info():
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

    async def make_telnet_stream() -> tuple[net_connection.TelnetStream, MemoryTransport, asyncio.StreamReaderProtocol]:
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        transport = MemoryTransport()
        protocol.connection_made(transport)
        writer = asyncio.StreamWriter(transport, protocol, reader, loop)
        return net_connection.TelnetStream(reader, writer), transport, protocol

    async def run() -> None:
        conn, transport, protocol = await make_telnet_stream()
        selection = CreationSelection(get_creation_races()[0], get_creation_classes()[0])

        skill_name, skill_cost = next(
            (name, cost) for name, cost in selection.available_skills() if name.lower() == "shield block"
        )
        group_name, group_cost = next(
            (name, cost) for name, cost in selection.available_groups() if name.lower() == "creation"
        )
        group_members = get_group(group_name).skills

        menu_task = asyncio.create_task(net_connection._run_customization_menu(conn, selection))
        await asyncio.sleep(0)

        initial = transport.buffer.decode(errors="ignore")
        assert "Type 'list', 'learned', 'add <group>', 'drop <group>', 'info <group>', 'premise', or 'done'." in initial

        transport.buffer.clear()
        protocol.data_received(b"list\r\n")
        await asyncio.sleep(0)
        listing = transport.buffer.decode(errors="ignore")
        assert "group              cp    group              cp    group              cp" in listing
        assert "skill              cp    skill              cp    skill              cp" in listing
        assert group_name.lower() in listing.lower()
        assert skill_name.lower() in listing.lower()
        assert "Creation points: 0" in listing
        assert "Experience per level: 1000" in listing

        transport.buffer.clear()
        protocol.data_received(f"add {skill_name.title()}\r\n".encode())
        await asyncio.sleep(0)
        skill_added = transport.buffer.decode(errors="ignore")
        skill_points = selection.creation_points
        skill_xp = selection.experience_per_level()
        assert skill_points == skill_cost
        assert f"{skill_name.lower()} skill added." in skill_added.lower()
        assert f"Creation points: {skill_points}" in skill_added
        assert f"Experience per level: {skill_xp}" in skill_added

        transport.buffer.clear()
        protocol.data_received(f"add {group_name.lower()}\r\n".encode())
        await asyncio.sleep(0)
        group_added = transport.buffer.decode(errors="ignore")
        group_points = selection.creation_points
        group_xp = selection.experience_per_level()
        assert group_points == skill_cost + group_cost
        assert f"{group_name.lower()} group added." in group_added.lower()
        assert f"Creation points: {group_points}" in group_added
        assert f"Experience per level: {group_xp}" in group_added

        transport.buffer.clear()
        protocol.data_received(f"info {group_name}\r\n".encode())
        await asyncio.sleep(0)
        info_output = transport.buffer.decode(errors="ignore")
        assert f"Group members for {group_name}" in info_output
        assert group_members
        assert group_members[0].split()[0].lower() in info_output.lower()

        transport.buffer.clear()
        protocol.data_received(b"learned\r\n")
        await asyncio.sleep(0)
        learned = transport.buffer.decode(errors="ignore")
        assert "group              cp    group              cp    group              cp" in learned
        assert group_name.lower() in learned.lower()
        assert "skill              cp    skill              cp    skill              cp" in learned
        assert skill_name.lower() in learned.lower()
        assert f"Creation points: {group_points}" in learned
        assert f"Experience per level: {group_xp}" in learned

        transport.buffer.clear()
        protocol.data_received(f"drop {skill_name.upper()}\r\n".encode())
        await asyncio.sleep(0)
        dropped_skill = transport.buffer.decode(errors="ignore")
        skill_removed_points = selection.creation_points
        skill_removed_xp = selection.experience_per_level()
        assert "Skill dropped." in dropped_skill
        assert f"Creation points: {skill_removed_points}" in dropped_skill
        assert f"Experience per level: {skill_removed_xp}" in dropped_skill

        transport.buffer.clear()
        protocol.data_received(f"drop {group_name}\r\n".encode())
        await asyncio.sleep(0)
        dropped_group = transport.buffer.decode(errors="ignore")
        assert "Group dropped." in dropped_group
        assert "Creation points: 0" in dropped_group
        assert "Experience per level: 1000" in dropped_group

        transport.buffer.clear()
        protocol.data_received(b"list\r\n")
        await asyncio.sleep(0)
        after_drop_listing = transport.buffer.decode(errors="ignore")
        assert "group              cp    group              cp    group              cp" in after_drop_listing
        assert group_name.lower() in after_drop_listing.lower()
        assert skill_name.lower() in after_drop_listing.lower()

        transport.buffer.clear()
        protocol.data_received(b"premise\r\n")
        await asyncio.sleep(0)
        premise = transport.buffer.decode(errors="ignore")
        assert "No help on that word." in premise

        selection.creation_points = selection.maximum_creation_points()
        transport.buffer.clear()
        protocol.data_received(f"add {skill_name}\r\n".encode())
        await asyncio.sleep(0)
        capped = transport.buffer.decode(errors="ignore")
        assert "You cannot take more than 300 creation points." in capped

        menu_task.cancel()
        with suppress(asyncio.CancelledError):
            await menu_task

        transport.close()
        protocol.connection_lost(None)

    asyncio.run(run())


def test_create_character_persists_creation_skills():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("artisan", "secret")
    account = login("artisan", "secret")
    assert account is not None

    assert create_character(
        account,
        "Crafter",
        creation_groups=("rom basics", "mage basics"),
        creation_skills=("Shield Block", "  flail  ", "shield block"),
    )

    session = SessionLocal()
    try:
        record = session.query(Character).filter_by(name="Crafter").first()
        assert record is not None
        stored_skills = json.loads(record.creation_skills)
        assert stored_skills == ["shield block", "flail"]
        assert _decode_creation_skills(record.creation_skills) == ("shield block", "flail")
    finally:
        session.close()


def test_new_character_starts_with_recall():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("traveler", "secret")
    account = login("traveler", "secret")
    assert account is not None

    assert create_character(account, "Nomad")

    char = load_player_character("traveler", "Nomad")
    assert char is not None
    skills = getattr(char, "skills", {})
    assert skills.get("recall") == 50


def test_new_character_defaults_to_nosummon():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("beacon", "secret")
    account = login("beacon", "secret")
    assert account is not None

    assert create_character(account, "Anchor")

    char = load_player_character("beacon", "Anchor")
    assert char is not None
    assert int(getattr(char, "act", 0)) & int(PlayerFlag.NOSUMMON)


def test_new_character_persists_true_sex():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("gender", "secret")
    account = login("gender", "secret")
    assert account is not None

    assert create_character(account, "Queen", sex=Sex.FEMALE)

    char = load_player_character("gender", "Queen")
    assert char is not None
    pcdata = getattr(char, "pcdata", None)
    assert pcdata is not None
    assert pcdata.true_sex == int(Sex.FEMALE)
    assert char.sex == int(Sex.FEMALE)

    pcdata.true_sex = int(Sex.MALE)
    char.sex = int(Sex.MALE)
    char.room = Room(vnum=ROOM_VNUM_LIMBO, name="Limbo", description="")
    char.was_in_room = Room(vnum=ROOM_VNUM_SCHOOL, name="The School", description="")
    save_player_character(char)

    session = SessionLocal()
    try:
        stored = session.query(Character).filter_by(name="Queen").first()
        assert stored is not None
        assert stored.room_vnum == ROOM_VNUM_SCHOOL
    finally:
        session.close()

    reloaded = load_player_character("gender", "Queen")
    assert reloaded is not None
    reloaded_pcdata = getattr(reloaded, "pcdata", None)
    assert reloaded_pcdata is not None
    assert reloaded_pcdata.true_sex == int(Sex.MALE)
    assert reloaded.sex == int(Sex.MALE)


def test_existing_database_gains_true_sex_column(tmp_path, monkeypatch):
    legacy_db = tmp_path / "legacy.db"
    legacy_engine = create_engine(f"sqlite:///{legacy_db}")

    with legacy_engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE player_accounts (
                id INTEGER PRIMARY KEY,
                username VARCHAR NOT NULL,
                email VARCHAR DEFAULT '',
                password_hash VARCHAR NOT NULL,
                is_admin INTEGER DEFAULT 0
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE characters (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL UNIQUE,
                level INTEGER,
                hp INTEGER,
                room_vnum INTEGER,
                race INTEGER,
                ch_class INTEGER,
                sex INTEGER,
                alignment INTEGER,
                act INTEGER,
                hometown_vnum INTEGER,
                perm_stats VARCHAR,
                size INTEGER,
                form INTEGER,
                parts INTEGER,
                imm_flags INTEGER,
                res_flags INTEGER,
                vuln_flags INTEGER,
                practice INTEGER,
                train INTEGER,
                default_weapon_vnum INTEGER,
                newbie_help_seen INTEGER,
                creation_points INTEGER,
                creation_groups VARCHAR,
                creation_skills VARCHAR,
                player_id INTEGER,
                FOREIGN KEY(player_id) REFERENCES player_accounts(id)
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE object_instances (
                id INTEGER PRIMARY KEY,
                prototype_vnum INTEGER,
                location VARCHAR,
                character_id INTEGER,
                FOREIGN KEY(character_id) REFERENCES characters(id)
            )
            """
        )
        conn.exec_driver_sql(
            "INSERT INTO player_accounts (id, username, email, password_hash, is_admin) "
            "VALUES (1, 'legacy', '', 'hash', 0)"
        )
        conn.exec_driver_sql(
            "INSERT INTO characters (id, name, level, hp, room_vnum, race, ch_class, sex, alignment, act, hometown_vnum, perm_stats, size, form, parts, imm_flags, res_flags, vuln_flags, practice, train, default_weapon_vnum, newbie_help_seen, creation_points, creation_groups, creation_skills, player_id) "
            "VALUES (1, 'Legacy', 1, 100, 0, 0, 0, 2, 0, 0, 0, '[]', 0, 0, 0, 0, 0, 0, 5, 3, 0, 0, 40, '[]', '[]', 1)"
        )

    legacy_session_factory = sessionmaker(bind=legacy_engine)

    from mud.db import session as db_session
    from mud.account import account_manager

    monkeypatch.setattr(db_session, "engine", legacy_engine, raising=False)
    monkeypatch.setattr(db_session, "SessionLocal", legacy_session_factory, raising=False)
    monkeypatch.setattr(account_manager, "SessionLocal", legacy_session_factory, raising=False)

    from mud.db import migrations

    monkeypatch.setattr(migrations, "engine", legacy_engine, raising=False)

    migrations.run_migrations()

    inspector = inspect(legacy_engine)
    columns = {column["name"] for column in inspector.get_columns("characters")}
    assert "true_sex" in columns

    loaded = account_manager.load_character("legacy", "Legacy")
    assert loaded is not None
    pcdata = getattr(loaded, "pcdata", None)
    assert pcdata is not None
    assert pcdata.true_sex == int(Sex.FEMALE)
    assert loaded.sex == int(Sex.FEMALE)


def test_new_character_defaults_prompt_and_comm():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("status", "secret")
    account = login("status", "secret")
    assert account is not None

    assert create_character(account, "Ticker")

    char = load_player_character("status", "Ticker")
    assert char is not None
    assert getattr(char, "prompt", None) == "<%hhp %mm %vmv> "
    comm_value = int(getattr(char, "comm", 0))
    assert comm_value & int(CommFlag.PROMPT)
    assert comm_value & int(CommFlag.COMBINE)


def test_new_character_defaults_conditions():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("ration", "secret")
    account = login("ration", "secret")
    assert account is not None

    assert create_character(account, "Forager")

    char = load_player_character("ration", "Forager")
    assert char is not None
    pcdata = getattr(char, "pcdata", None)
    assert pcdata is not None
    assert pcdata.condition == [0, 48, 48, 48]


def test_new_character_defaults_page_length():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("pager", "secret")
    account = login("pager", "secret")
    assert account is not None

    assert create_character(account, "Scroll")

    char = load_player_character("pager", "Scroll")
    assert char is not None
    assert getattr(char, "lines", None) == DEFAULT_PAGE_LINES


def test_new_character_seeds_creation_groups_and_skills():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("heft", "secret")
    account = login("heft", "secret")
    assert account is not None

    warrior_class = next(entry for entry in get_creation_classes() if entry.name.lower() == "warrior")
    human_race = next(race for race in get_creation_races() if race.name.lower() == "human")

    assert create_character(
        account,
        "Veteran",
        race=human_race,
        class_type=warrior_class,
        creation_groups=("rom basics", "warrior basics", "warrior default"),
        creation_skills=("bash",),
        default_weapon_vnum=OBJ_VNUM_SCHOOL_SWORD,
    )

    char = load_player_character("heft", "Veteran")
    assert char is not None
    pcdata = getattr(char, "pcdata", None)
    assert pcdata is not None

    assert pcdata.points == char.creation_points
    assert {"rom basics", "warrior basics", "warrior default"} <= set(pcdata.group_known)
    assert "weaponsmaster" in pcdata.group_known
    assert char.skills.get("bash") == 1
    assert char.skills.get("sword") == 40
    assert char.skills.get("recall") == 50
    assert pcdata.learned == char.skills


def test_new_character_receives_starting_outfit():
    initialize_world("area/area.lst")

    newbie = RuntimeCharacter(name="Newbie", level=1)
    newbie.is_npc = False
    newbie.inventory.clear()
    newbie.equipment.clear()
    newbie.default_weapon_vnum = OBJ_VNUM_SCHOOL_SWORD

    provided = give_school_outfit(newbie)
    assert provided is True

    assert {"light", "body", "wield", "shield"} <= set(newbie.equipment.keys())

    wielded = newbie.equipment["wield"]
    assert getattr(getattr(wielded, "prototype", None), "vnum", None) in {
        OBJ_VNUM_SCHOOL_SWORD,
        newbie.default_weapon_vnum,
    }

    assert any(getattr(getattr(obj, "prototype", None), "vnum", None) == OBJ_VNUM_MAP for obj in newbie.inventory)

    assert give_school_outfit(newbie) is False


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
        host, port = _server_address(server)
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)

            prompt, greeting = await negotiate_ansi(reader, writer)
            combined = prompt + greeting
            assert bytes([TELNET_IAC, TELNET_WONT, TELNET_TELOPT_ECHO]) in combined

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
            await _shutdown_server(server, server_task)

    asyncio.run(run())


def test_ansi_prompt_negotiates_preference():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    async def run() -> None:
        server = await create_server(host="127.0.0.1", port=0)
        host, port = _server_address(server)
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)

            prompt, greeting = await negotiate_ansi(reader, writer)
            assert prompt.endswith(b"(Y/n) ")
            assert b"{W" not in greeting
            assert b"\x1b[" in greeting
            assert b"THIS IS A MUD" in greeting.upper()

            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
        finally:
            await _shutdown_server(server, server_task)

    asyncio.run(run())


def test_illegal_name_rejected():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    async def run() -> None:
        server = await create_server(host="127.0.0.1", port=0)
        host, port = _server_address(server)
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)
            await negotiate_ansi(reader, writer)
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
            await _shutdown_server(server, server_task)

    asyncio.run(run())

    session = SessionLocal()
    try:
        assert session.query(PlayerAccount).filter_by(username="self").first() is None
    finally:
        session.close()


def test_help_greeting_respects_ansi_choice():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("ansiuser", "secret")
    account = login("ansiuser", "secret")
    assert account is not None
    assert create_character(account, "Ansi")
    release_account("ansiuser")

    async def run() -> None:
        server = await create_server(host="127.0.0.1", port=0)
        host, port = _server_address(server)
        server_task = asyncio.create_task(server.serve_forever())
        try:
            # ANSI-enabled login
            reader, writer = await asyncio.open_connection(host, port)
            _, greeting_on = await negotiate_ansi(reader, writer)
            assert b"\x1b[" in greeting_on
            assert b"{W" not in greeting_on
            assert b"THIS IS A MUD" in greeting_on.upper()

            writer.write(b"ansiuser\r\n")
            await writer.drain()
            await reader.readuntil(b"Password: ")
            writer.write(b"secret\r\n")
            await writer.drain()
            await reader.readuntil(b"Character: ")
            writer.write(b"Ansi\r\n")
            await writer.drain()
            await reader.readuntil(b"> ")
            session = SESSIONS.get("Ansi")
            assert session is not None
            assert session.character.ansi_enabled is True

            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
            release_account("ansiuser")

            # ANSI-disabled login
            reader, writer = await asyncio.open_connection(host, port)
            _, greeting_off = await negotiate_ansi(reader, writer, reply=b"n")
            assert b"\x1b[" not in greeting_off
            assert b"{" not in greeting_off
            assert b"THIS IS A MUD" in greeting_off.upper()

            writer.write(b"ansiuser\r\n")
            await writer.drain()
            await reader.readuntil(b"Password: ")
            writer.write(b"secret\r\n")
            await writer.drain()
            await reader.readuntil(b"Character: ")
            writer.write(b"Ansi\r\n")
            await writer.drain()
            await reader.readuntil(b"> ")
            session = SESSIONS.get("Ansi")
            assert session is not None
            assert session.character.ansi_enabled is False

            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
            release_account("ansiuser")
        finally:
            await _shutdown_server(server, server_task)

    asyncio.run(run())


def test_ansi_preference_persists_between_sessions():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("ansiuser", "secret")
    account = login("ansiuser", "secret")
    assert account is not None
    assert create_character(account, "Ansi")
    release_account("ansiuser")

    async def run() -> None:
        server = await create_server(host="127.0.0.1", port=0)
        host, port = _server_address(server)
        server_task = asyncio.create_task(server.serve_forever())
        try:
            reader, writer = await asyncio.open_connection(host, port)
            _, greeting_off = await negotiate_ansi(reader, writer, reply=b"n")
            assert b"\x1b[" not in greeting_off

            writer.write(b"ansiuser\r\n")
            await writer.drain()
            await reader.readuntil(b"Password: ")
            writer.write(b"secret\r\n")
            await writer.drain()
            await reader.readuntil(b"Character: ")
            writer.write(b"Ansi\r\n")
            await writer.drain()
            await reader.readuntil(b"> ")
            session = SESSIONS.get("Ansi")
            assert session is not None
            assert session.character.ansi_enabled is False
            assert session.connection.ansi_enabled is False
            assert session.character.act & int(PlayerFlag.COLOUR) == 0

            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
            release_account("ansiuser")

            player_state = load_player_character("ansiuser", "Ansi")
            assert player_state is not None
            assert player_state.act & int(PlayerFlag.COLOUR) == 0
            assert getattr(player_state, "ansi_enabled", True) is False

            reader, writer = await asyncio.open_connection(host, port)
            await negotiate_ansi(reader, writer, reply=b"n")
            writer.write(b"ansiuser\r\n")
            await writer.drain()
            await reader.readuntil(b"Password: ")
            writer.write(b"secret\r\n")
            await writer.drain()
            await reader.readuntil(b"Character: ")
            writer.write(b"Ansi\r\n")
            await writer.drain()
            await reader.readuntil(b"> ")
            session = SESSIONS.get("Ansi")
            assert session is not None
            assert session.character.ansi_enabled is False
            assert session.connection.ansi_enabled is False
            assert session.character.act & int(PlayerFlag.COLOUR) == 0

            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
            release_account("ansiuser")
        finally:
            await _shutdown_server(server, server_task)

    asyncio.run(run())


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


def test_password_echo_suppressed():
    class DummyWriter:
        def __init__(self) -> None:
            self.writes: list[bytes] = []
            self.closed = False

        def write(self, data: bytes) -> None:
            self.writes.append(bytes(data))

        async def drain(self) -> None:  # pragma: no cover - behavioural stub
            return None

        def close(self) -> None:  # pragma: no cover - behavioural stub
            self.closed = True

        async def wait_closed(self) -> None:  # pragma: no cover - behavioural stub
            return None

    async def run() -> None:
        reader = asyncio.StreamReader()
        writer = DummyWriter()
        conn = net_connection.TelnetStream(reader, writer)

        reader.feed_data(b"secret\r\n")
        reader.feed_eof()

        result = await net_connection._prompt(conn, "Password: ", hide_input=True)

        assert result == "secret"
        assert (
            bytes(
                [
                    net_connection.TELNET_IAC,
                    net_connection.TELNET_WILL,
                    net_connection.TELNET_TELOPT_ECHO,
                ]
            )
            in writer.writes
        )
        assert (
            bytes(
                [
                    net_connection.TELNET_IAC,
                    net_connection.TELNET_WONT,
                    net_connection.TELNET_TELOPT_ECHO,
                ]
            )
            in writer.writes
        )

    asyncio.run(run())


def test_new_player_triggers_wiznet_newbie_alert(monkeypatch):
    import mud.net.connection as net_connection

    previous_registry = list(character_registry)
    character_registry.clear()
    try:

        async def run_test():
            newbie_listener = RuntimeCharacter(
                name="ImmNewbie",
                is_admin=True,
                is_npc=False,
                level=60,
                trust=60,
                wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_NEWBIE | WiznetFlag.WIZ_PREFIX),
            )
            site_listener = RuntimeCharacter(
                name="SiteWatcher",
                is_admin=True,
                is_npc=False,
                level=60,
                trust=60,
                wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES | WiznetFlag.WIZ_PREFIX),
            )
            plain_listener = RuntimeCharacter(
                name="PlainSite",
                is_admin=True,
                is_npc=False,
                level=60,
                trust=60,
                wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES),
            )
            low_trust_listener = RuntimeCharacter(
                name="LowTrust",
                is_admin=True,
                is_npc=False,
                level=50,
                trust=40,
                wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_SITES),
            )
            character_registry.extend(
                [
                    newbie_listener,
                    site_listener,
                    plain_listener,
                    low_trust_listener,
                ]
            )

            recorded_calls: list[tuple[str, str | None, int]] = []
            real_announce = net_connection.announce_wiznet_new_player

            def tracking_announce(
                name: str,
                host: str | None = None,
                *,
                trust_level: int = 1,
                sex: Sex | int | None = None,
            ) -> None:
                recorded_calls.append((name, host, trust_level))
                real_announce(name, host, trust_level=trust_level, sex=sex)

            monkeypatch.setattr(net_connection, "announce_wiznet_new_player", tracking_announce)

            created_names: list[str] = []

            def fake_create_character(account, name, **kwargs):
                created_names.append(name)
                return True

            monkeypatch.setattr(net_connection, "create_character", fake_create_character)

            async def fake_prompt_yes_no(conn, prompt):
                return True

            async def fake_prompt_for_race(conn, *_args):
                return get_creation_races()[0]

            async def fake_prompt_for_sex(conn):
                return Sex.FEMALE

            async def fake_prompt_for_class(conn):
                return get_creation_classes()[0]

            async def fake_prompt_for_alignment(conn):
                return 750

            async def fake_prompt_customization_choice(conn):
                return False

            async def fake_prompt_for_stats(conn, race):
                return [13, 13, 13, 13, 13]

            async def fake_prompt_for_hometown(conn):
                return ROOM_VNUM_SCHOOL

            async def fake_prompt_for_weapon(conn, class_type):
                return OBJ_VNUM_SCHOOL_DAGGER

            async def fake_send_line(conn, message):
                return None

            monkeypatch.setattr(net_connection, "_prompt_yes_no", fake_prompt_yes_no)
            monkeypatch.setattr(net_connection, "_prompt_for_race", fake_prompt_for_race)
            monkeypatch.setattr(net_connection, "_prompt_for_sex", fake_prompt_for_sex)
            monkeypatch.setattr(net_connection, "_prompt_for_class", fake_prompt_for_class)
            monkeypatch.setattr(net_connection, "_prompt_for_alignment", fake_prompt_for_alignment)
            monkeypatch.setattr(
                net_connection,
                "_prompt_customization_choice",
                fake_prompt_customization_choice,
            )
            monkeypatch.setattr(net_connection, "_prompt_for_stats", fake_prompt_for_stats)
            monkeypatch.setattr(net_connection, "_prompt_for_hometown", fake_prompt_for_hometown)
            monkeypatch.setattr(net_connection, "_prompt_for_weapon", fake_prompt_for_weapon)
            monkeypatch.setattr(net_connection, "_send_line", fake_send_line)

            dummy_conn = SimpleNamespace(peer_host="academy.example")
            dummy_account = SimpleNamespace(id=1)

            result = await net_connection._run_character_creation_flow(dummy_conn, dummy_account, "Nova")

            assert result is True
            assert created_names == ["Nova"]
            assert recorded_calls == [("Nova", "academy.example", 1)]
            assert any("{Z--> Newbie alert!  Nova sighted." in msg for msg in newbie_listener.messages)
            assert any("{Z--> Nova@academy.example new player." in msg for msg in site_listener.messages)
            assert any("{ZNova@academy.example new player." in msg for msg in plain_listener.messages)
            assert any("{ZNova@academy.example new player." in msg for msg in low_trust_listener.messages)

        asyncio.run(run_test())
    finally:
        character_registry.clear()
        character_registry.extend(previous_registry)


def test_newbie_banned_blocks_character_creation(monkeypatch):
    messages: list[str] = []

    async def fake_send_line(conn, message):  # noqa: ARG001 - testing hook
        messages.append(message)

    async def fail_async_prompt(*_args, **_kwargs):  # noqa: D401
        raise AssertionError("async prompts should not run when newbie banned")

    monkeypatch.setattr(net_connection, "_send_line", fake_send_line)
    monkeypatch.setattr(net_connection, "_prompt_yes_no", fail_async_prompt)
    monkeypatch.setattr(net_connection, "_prompt_for_race", fail_async_prompt)
    monkeypatch.setattr(net_connection, "_prompt_for_sex", fail_async_prompt)
    monkeypatch.setattr(net_connection, "_prompt_for_class", fail_async_prompt)
    monkeypatch.setattr(net_connection, "_prompt_for_alignment", fail_async_prompt)
    monkeypatch.setattr(net_connection, "_prompt_customization_choice", fail_async_prompt)
    monkeypatch.setattr(net_connection, "_prompt_for_stats", fail_async_prompt)
    monkeypatch.setattr(net_connection, "_prompt_for_hometown", fail_async_prompt)
    monkeypatch.setattr(net_connection, "_prompt_for_weapon", fail_async_prompt)

    created: list[str] = []

    def fake_create_character(account, name, **_kwargs):  # noqa: ARG001
        created.append(name)
        return SimpleNamespace(name=name)

    monkeypatch.setattr(net_connection, "create_character", fake_create_character)

    async def run_test() -> bool:
        dummy_conn = SimpleNamespace(peer_host="blocked.example")
        dummy_account = SimpleNamespace(id=1)
        return await net_connection._run_character_creation_flow(
            dummy_conn,
            dummy_account,
            "Nova",
            newbie_banned=True,
        )

    result = asyncio.run(run_test())

    assert result is False
    assert created == []
    assert messages == ["New players are not allowed from your site."]


def test_select_character_blocks_newbie_creation_when_banned(monkeypatch):
    responses = iter(["Newbie", "Guardian"])
    prompts: list[str] = []
    messages: list[str] = []
    creation_calls: list[tuple[str, bool]] = []

    async def fake_prompt(conn, prompt, *, hide_input: bool = False):  # noqa: ARG001
        prompts.append(prompt)
        try:
            return next(responses)
        except StopIteration:
            raise AssertionError("No more responses queued")

    async def fake_send_line(conn, message):  # noqa: ARG001 - testing hook
        messages.append(message)

    async def fake_creation_flow(
        conn,  # noqa: ARG001 - signature compatibility
        account,
        name,
        *,
        permit_banned: bool = False,  # noqa: ARG001
        newbie_banned: bool = False,
    ) -> bool:
        creation_calls.append((name, newbie_banned))
        messages.append("New players are not allowed from your site.")
        return False

    def fake_list_characters(account, require_act_flags=None):  # noqa: ARG001
        return ["Guardian"]

    def fake_load_character(username, name):  # noqa: ARG001
        if name == "Guardian":
            return SimpleNamespace(name=name)
        return None

    async def fail_yes_no(*_args, **_kwargs):  # noqa: D401 - should not trigger
        raise AssertionError("unexpected reconnect prompt during newbie ban test")

    monkeypatch.setattr(net_connection, "_prompt", fake_prompt)
    monkeypatch.setattr(net_connection, "_send_line", fake_send_line)
    monkeypatch.setattr(
        net_connection,
        "_run_character_creation_flow",
        fake_creation_flow,
    )
    monkeypatch.setattr(net_connection, "list_characters", fake_list_characters)
    monkeypatch.setattr(net_connection, "_prompt_yes_no", fail_yes_no)
    monkeypatch.setattr(net_connection, "load_character", fake_load_character)

    async def run_test():
        net_connection.SESSIONS.clear()
        dummy_conn = SimpleNamespace()
        account = SimpleNamespace()
        result = await net_connection._select_character(
            dummy_conn,
            account,
            "warden",
            permit_banned=False,
            newbie_banned=True,
        )
        return result

    character, forced = asyncio.run(run_test())

    assert forced is False
    assert character.name == "Guardian"
    assert prompts.count("Character: ") == 2
    assert creation_calls == [("Newbie", True)]
    assert messages.count("New players are not allowed from your site.") == 1


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


def test_banned_host_disconnects_before_greeting():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()
    SESSIONS.clear()

    async def run() -> None:
        server = await create_server(host="127.0.0.1", port=0)
        host, port = _server_address(server)
        server_task = asyncio.create_task(server.serve_forever())
        # Add ban AFTER create_server (which clears bans during world init)
        bans.add_banned_host("127.0.0.1")
        try:
            reader, writer = await asyncio.open_connection(host, port)
            chunks = []
            while True:
                try:
                    chunk = await asyncio.wait_for(reader.read(1024), timeout=2)
                    if not chunk:
                        break
                    chunks.append(chunk)
                except asyncio.TimeoutError:
                    break
            data = b"".join(chunks)
            assert b"Your site has been banned from this mud." in data
            assert b"Do you want ANSI?" not in data
            assert b"Account:" not in data
            writer.close()
            await writer.wait_closed()
        finally:
            await _shutdown_server(server, server_task)

    asyncio.run(run())
    assert not SESSIONS
    bans.clear_all_bans()


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

        assert create_account("testadmin", "pw")
        session = SessionLocal()
        try:
            imm = session.query(PlayerAccount).filter_by(username="testadmin").first()
            assert imm is not None
            imm.is_admin = True
            session.commit()
        finally:
            session.close()

        admin = login_with_host("testadmin", "pw", None).account
        assert admin is not None
    finally:
        release_account("testadmin")
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
            host, port = _server_address(server)
            server_task = asyncio.create_task(server.serve_forever())
            try:
                set_newlock(True)
                reader, writer = await asyncio.open_connection(host, port)
                await negotiate_ansi(reader, writer)
                writer.write(b"brand\n")
                await writer.drain()

                # When newlock is enabled and account doesn't exist,
                # server rejects BEFORE asking for password
                chunks = []
                while True:
                    try:
                        chunk = await asyncio.wait_for(reader.read(1024), timeout=2)
                        if not chunk:
                            break
                        chunks.append(chunk)
                    except asyncio.TimeoutError:
                        break
                data = b"".join(chunks)
                assert b"The game is newlocked." in data

                writer.close()
                with suppress(Exception):
                    await writer.wait_closed()
            finally:
                await _shutdown_server(server, server_task)

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
    assert blocked.was_reconnect is False

    reconnect = login_with_host("dup", "pw", None, allow_reconnect=True)
    assert reconnect.account is not None
    assert reconnect.was_reconnect is True
    release_account("dup")


def test_reconnect_announces_wiz_links(monkeypatch):
    character_registry.clear()

    room = Room(vnum=42, name="Limbo")
    reconnecting = RuntimeCharacter(
        name="Hero",
        is_npc=False,
        trust=60,
        level=50,
        sex=Sex.MALE,
    )
    room.add_character(reconnecting)

    watcher = RuntimeCharacter(name="Watcher", is_npc=False)
    room.add_character(watcher)

    imm_receives = RuntimeCharacter(
        name="ImmHigh",
        is_admin=True,
        is_npc=False,
        trust=60,
        level=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LINKS),
    )
    imm_blocked = RuntimeCharacter(
        name="ImmLow",
        is_admin=True,
        is_npc=False,
        trust=50,
        level=50,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LINKS),
    )
    imm_plain = RuntimeCharacter(
        name="ImmPlain",
        is_admin=True,
        is_npc=False,
        trust=60,
        level=60,
        wiznet=int(WiznetFlag.WIZ_ON),
    )
    imm_receives.connection = SimpleNamespace()
    imm_blocked.connection = SimpleNamespace()
    imm_plain.connection = SimpleNamespace()
    reconnecting.connection = SimpleNamespace(peer_host="midgaard.example")
    character_registry.extend([imm_receives, imm_blocked, imm_plain])

    logged: list[str] = []

    def _capture_log(message: str) -> str:
        logged.append(message)
        return message

    monkeypatch.setattr(net_connection, "log_game_event", _capture_log)

    try:
        _broadcast_reconnect_notifications(reconnecting)
    finally:
        character_registry.clear()

    assert any("Hero has reconnected." in msg for msg in watcher.messages)
    expected = "{ZHero groks the fullness of his link.\n\r{x"
    assert imm_receives.messages == [expected]
    assert imm_blocked.messages == [expected]
    assert all("groks" not in msg for msg in imm_plain.messages)
    assert RECONNECT_MESSAGE == "Reconnecting. Type replay to see missed tells."
    assert logged == ["Hero@midgaard.example reconnected."]

    watcher.messages.clear()
    imm_receives.messages.clear()
    imm_blocked.messages.clear()
    imm_plain.messages.clear()
    logged.clear()

    reconnecting.connection.peer_host = None

    character_registry.extend([imm_receives, imm_blocked, imm_plain])
    try:
        _broadcast_reconnect_notifications(reconnecting)
    finally:
        character_registry.clear()

    assert any("Hero has reconnected." in msg for msg in watcher.messages)
    assert logged == ["Hero@(unknown) reconnected."]
    assert imm_receives.messages == [expected]
    assert imm_blocked.messages == [expected]


def test_reconnect_skips_login_announcements(monkeypatch):
    character_registry.clear()

    reconnecting = RuntimeCharacter(
        name="Hero",
        is_npc=False,
        trust=60,
        level=50,
        sex=Sex.MALE,
    )
    reconnecting.connection = SimpleNamespace(peer_host="midgaard.example")

    link_listener = RuntimeCharacter(
        name="LinkImm",
        is_admin=True,
        is_npc=False,
        trust=60,
        level=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LINKS),
    )
    login_listener = RuntimeCharacter(
        name="LoginImm",
        is_admin=True,
        is_npc=False,
        trust=60,
        level=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LOGINS),
    )
    link_listener.connection = SimpleNamespace()
    login_listener.connection = SimpleNamespace()

    character_registry.extend([link_listener, login_listener])

    login_called = False

    def _capture_login(*_args, **_kwargs) -> None:
        nonlocal login_called
        login_called = True

    monkeypatch.setattr(net_connection, "announce_wiznet_login", _capture_login)

    try:
        reminder = _announce_login_or_reconnect(reconnecting, "midgaard.example", reconnecting=True)
    finally:
        character_registry.clear()

    assert not login_called
    assert link_listener.messages == ["{ZHero groks the fullness of his link.\n\r{x"]
    assert login_listener.messages == []
    assert reminder is False


def test_reconnect_announces_note_reminder(monkeypatch):
    character_registry.clear()

    reconnecting = RuntimeCharacter(
        name="Hero",
        is_npc=False,
        trust=60,
        level=50,
        sex=Sex.MALE,
    )
    reconnecting.connection = SimpleNamespace(peer_host="midgaard.example")
    reconnecting.pcdata = SimpleNamespace(in_progress="draft")

    link_listener = RuntimeCharacter(
        name="LinkImm",
        is_admin=True,
        is_npc=False,
        trust=60,
        level=60,
        wiznet=int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_LINKS),
    )
    link_listener.connection = SimpleNamespace()

    character_registry.append(link_listener)

    login_called = False

    def _capture_login(*_args, **_kwargs) -> None:
        nonlocal login_called
        login_called = True

    monkeypatch.setattr(net_connection, "announce_wiznet_login", _capture_login)

    try:
        reminder = _announce_login_or_reconnect(reconnecting, "midgaard.example", reconnecting=True)
    finally:
        character_registry.clear()

    assert reminder is True
    assert not login_called
    assert link_listener.messages == ["{ZHero groks the fullness of his link.\n\r{x"]


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


def test_ban_permit_requires_permit_flag():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("warden", "pw")

    session = SessionLocal()
    try:
        account = session.query(PlayerAccount).filter_by(username="warden").first()
        assert account is not None
        assert create_character(account, "Guardian")
    finally:
        session.close()

    bans.add_banned_host("permit.example", flags=BanFlag.PERMIT)

    blocked = login_with_host("warden", "pw", "permit.example")
    assert blocked.account is None
    assert blocked.failure is LoginFailureReason.HOST_BANNED

    session = SessionLocal()
    try:
        character = session.query(Character).filter_by(name="Guardian").first()
        assert character is not None
        character.act = int(character.act or 0) | int(PlayerFlag.PERMIT)
        session.commit()
    finally:
        session.close()

    permitted = login_with_host("warden", "pw", "permit.example")
    assert permitted.account is not None
    release_account("warden")


def test_character_selection_filters_permit_hosts():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()

    assert create_account("warden", "pw")

    session = SessionLocal()
    try:
        account = session.query(PlayerAccount).filter_by(username="warden").first()
        assert account is not None
        assert create_character(account, "Guardian")
        assert create_character(account, "Rogue")
    finally:
        session.close()

    session = SessionLocal()
    try:
        guardian = session.query(Character).filter_by(name="Guardian").first()
        rogue = session.query(Character).filter_by(name="Rogue").first()
        assert guardian is not None and rogue is not None
        guardian.act = int(PlayerFlag.PERMIT)
        session.commit()
    finally:
        session.close()

    bans.add_banned_host("127.0.0.1", flags=BanFlag.PERMIT)

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

    async def make_telnet_stream() -> tuple[
        net_connection.TelnetStream, "MemoryTransport", asyncio.StreamReaderProtocol
    ]:
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        transport = MemoryTransport()
        protocol.connection_made(transport)
        writer = asyncio.StreamWriter(transport, protocol, reader, loop)
        return net_connection.TelnetStream(reader, writer), transport, protocol

    async def run() -> None:
        permit_login = login_with_host("warden", "pw", "127.0.0.1")
        assert permit_login.account is not None
        account = permit_login.account

        conn, transport, protocol = await make_telnet_stream()
        selection_task = asyncio.create_task(
            net_connection._select_character(
                conn,
                account,
                "warden",
                permit_banned=True,
            )
        )
        await asyncio.sleep(0)
        listing_output = transport.buffer.decode(errors="ignore")
        assert "Characters: Guardian" in listing_output
        assert "Rogue" not in listing_output
        transport.buffer.clear()

        protocol.data_received(b"Guardian\r\n")
        char, forced = await asyncio.wait_for(selection_task, timeout=1)
        assert forced is False
        assert char.name == "Guardian"

        conn2, transport2, protocol2 = await make_telnet_stream()
        denied_task = asyncio.create_task(
            net_connection._select_character(
                conn2,
                account,
                "warden",
                permit_banned=True,
            )
        )
        await asyncio.sleep(0)
        transport2.buffer.clear()
        protocol2.data_received(b"Rogue\r\n")
        denied = await asyncio.wait_for(denied_task, timeout=1)
        assert denied is None
        ban_output = transport2.buffer.decode(errors="ignore")
        assert "Your site has been banned from this mud." in ban_output

    asyncio.run(run())

    release_account("warden")
    bans.clear_all_bans()


def _server_address(server: asyncio.AbstractServer) -> tuple[str, int]:
    sockets = cast(Sequence[Socket], getattr(server, "sockets", ()))
    if not sockets:
        raise RuntimeError("Server missing sockets")
    addr = sockets[0].getsockname()
    if isinstance(addr, tuple) and len(addr) >= 2:
        host = str(addr[0])
        port = int(addr[1])
        return host, port
    raise RuntimeError("Unsupported socket address")
