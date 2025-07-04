from __future__ import annotations
import asyncio

from mud.world.world_state import create_test_character
from mud.account import load_character, save_character
from mud.commands import process_command
from mud.net.session import Session, SESSIONS
from mud.net.protocol import send_to_char


async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    addr = writer.get_extra_info("peername")
    writer.write(b"Welcome to PythonMUD\r\n")
    writer.write(b"What is your name?\r\n")
    await writer.drain()

    name_data = await reader.readline()
    if not name_data:
        writer.close()
        await writer.wait_closed()
        return
    name = name_data.decode().strip() or "guest"

    char = load_character(name, name)
    if not char:
        char = create_test_character(name, 3001)
    elif char.room:
        char.room.add_character(char)
    char.connection = writer

    session = Session(name=name, character=char, reader=reader, writer=writer)
    SESSIONS[name] = session
    print(f"[CONNECT] {addr} as {name}")

    try:
        while True:
            writer.write(b"> ")
            await writer.drain()
            data = await reader.readline()
            if not data:
                break
            command = data.decode().strip()
            if not command:
                continue
            response = process_command(char, command)
            await send_to_char(char, response)
            # flush broadcast messages queued on character
            while char.messages:
                msg = char.messages.pop(0)
                await send_to_char(char, msg)
    finally:
        save_character(char)
        if char.room:
            char.room.remove_character(char)
        SESSIONS.pop(name, None)
        writer.close()
        await writer.wait_closed()
        print(f"[DISCONNECT] {addr} as {name}")
