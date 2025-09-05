from __future__ import annotations
import asyncio

from mud.account import load_character, save_character
from mud.account.account_service import (
    create_account,
    create_character,
    list_characters,
    login,
)
from mud.commands import process_command
from mud.models.character import character_registry
from mud.net.session import Session, SESSIONS
from mud.net.protocol import send_to_char


async def handle_connection(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    addr = writer.get_extra_info("peername")
    session = None
    char = None
    char_name = ""

    try:
        writer.write(b"Welcome to PythonMUD\r\n")
        writer.write(b"Username:\r\n")
        await writer.drain()

        name_data = await reader.readline()
        if not name_data:
            return
        username = name_data.decode().strip()

        writer.write(b"Password:\r\n")
        await writer.drain()
        pwd_data = await reader.readline()
        if not pwd_data:
            return
        password = pwd_data.decode().strip()

        account = login(username, password)
        if not account:
            if create_account(username, password):
                account = login(username, password)
                writer.write(b"Account created.\r\n")
            else:
                writer.write(b"Invalid login.\r\n")
                await writer.drain()
                return

        chars = list_characters(account)
        if chars:
            writer.write(
                f"Choose character ({', '.join(chars)}):\r\n".encode()
            )
            await writer.drain()
            name_data = await reader.readline()
            if not name_data:
                return
            char_name = name_data.decode().strip()
            if char_name not in chars:
                writer.write(b"Unknown character.\r\n")
                await writer.drain()
                return
        else:
            writer.write(b"Character name:\r\n")
            await writer.drain()
            name_data = await reader.readline()
            if not name_data:
                return
            char_name = name_data.decode().strip()
            if not create_character(account, char_name):
                writer.write(b"Failed to create character.\r\n")
                await writer.drain()
                return

        try:
            char = load_character(username, char_name)
        except Exception as e:
            print(f"[ERROR] Failed to load character {char_name}: {e}")
            char = None

        if not char:
            writer.write(b"Could not load character.\r\n")
            await writer.drain()
            return

        if char.room:
            try:
                char.room.add_character(char)
            except Exception as e:
                print(f"[ERROR] Failed to add character to room: {e}")

        character_registry.append(char)
        char.connection = writer

        session = Session(
            name=char.name or "",
            character=char,
            reader=reader,
            writer=writer,
        )
        if char.name:
            SESSIONS[char.name] = session
        print(f"[CONNECT] {addr} as {char.name}")

        # Send initial room description and prompt
        try:
            if char and char.room:
                response = process_command(char, "look")
                await send_to_char(char, response)
            else:
                await send_to_char(char, "You are floating in a void...")
        except Exception as e:
            print(f"[ERROR] Failed to send initial look: {e}")
            await send_to_char(char, "Welcome to the world!")

        # Main command loop with error handling
        while True:
            try:
                writer.write(b"> ")
                await writer.drain()
                data = await reader.readline()
                if not data:
                    break
                command = data.decode().strip()
                if not command:
                    continue

                try:
                    response = process_command(char, command)
                    await send_to_char(char, response)
                except Exception as e:
                    err_msg = (
                        "[ERROR] Command processing failed for "
                        f"'{command}': {e}"
                    )
                    print(err_msg)
                    fail_msg = (
                        "Sorry, there was an error processing that command."
                    )
                    await send_to_char(char, fail_msg)

                # flush broadcast messages queued on character
                while char and char.messages:
                    try:
                        msg = char.messages.pop(0)
                        await send_to_char(char, msg)
                    except Exception as e:
                        print(f"[ERROR] Failed to send message: {e}")
                        break

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ERROR] Connection loop error for {char_name}: {e}")
                break

    except Exception as e:
        print(f"[ERROR] Connection handler error for {addr}: {e}")
    finally:
        # Cleanup with error handling
        try:
            if char:
                save_character(char)
        except Exception as e:
            print(f"[ERROR] Failed to save character: {e}")

        try:
            if char and char.room:
                char.room.remove_character(char)
        except Exception as e:
            print(f"[ERROR] Failed to remove character from room: {e}")

        if session and char_name and char_name in SESSIONS:
            SESSIONS.pop(char_name, None)

        try:
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f"[ERROR] Failed to close connection: {e}")

        print(f"[DISCONNECT] {addr} as {char_name or 'unknown'}")
