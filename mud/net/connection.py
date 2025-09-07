from __future__ import annotations
import asyncio

from mud.account import (
    load_character,
    save_character,
    create_account,
    login_with_host,
    list_characters,
    create_character,
)
from mud.commands import process_command
from mud.net.session import Session, SESSIONS
from mud.net.protocol import send_to_char


async def handle_connection(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    addr = writer.get_extra_info("peername")
    host_for_ban = None
    if isinstance(addr, tuple) and addr:
        host_for_ban = addr[0]
    session = None
    char = None
    account = None
    username = ""

    try:
        writer.write(b"Welcome to PythonMUD\r\n")
        await writer.drain()

        # Account login / creation
        while not account:
            writer.write(b"Account: ")
            await writer.drain()
            name_data = await reader.readline()
            if not name_data:
                return
            username = name_data.decode().strip()
            writer.write(b"Password: ")
            await writer.drain()
            pwd_data = await reader.readline()
            if not pwd_data:
                return
            password = pwd_data.decode().strip()
            # Enforce site/account bans at login time
            account = login_with_host(username, password, host_for_ban)
            if not account:
                if create_account(username, password):
                    account = login_with_host(username, password, host_for_ban)
                else:
                    writer.write(b"Login failed.\r\n")
                    await writer.drain()

        # Character selection / creation
        chars = list_characters(account)
        if chars:
            writer.write(
                ("Characters: " + ", ".join(chars) + "\r\n").encode()
            )
        writer.write(b"Character: ")
        await writer.drain()
        char_data = await reader.readline()
        if not char_data:
            return
        char_name = char_data.decode().strip()
        if char_name not in chars:
            create_character(account, char_name)
        try:
            char = load_character(username, char_name)
        except Exception as e:
            print(f"[ERROR] Failed to load character {char_name}: {e}")
            return
        if char and char.room:
            try:
                char.room.add_character(char)
            except Exception as e:
                print(f"[ERROR] Failed to add character to room: {e}")

        char.connection = writer

        session = Session(
            name=char.name or "",
            character=char,
            reader=reader,
            writer=writer,
        )
        SESSIONS[session.name] = session
        print(f"[CONNECT] {addr} as {session.name}")

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
                    print(
                        "[ERROR] Command processing failed for "
                        f"'{command}': {e}"
                    )
                    await send_to_char(
                        char,
                        "Sorry, there was an error processing that "
                        "command.",
                    )

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
                print(
                    "[ERROR] Connection loop error for "
                    f"{session.name if session else 'unknown'}: {e}"
                )
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

        if session and session.name in SESSIONS:
            SESSIONS.pop(session.name, None)

        try:
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f"[ERROR] Failed to close connection: {e}")

        print(
            f"[DISCONNECT] {addr} as {session.name if session else 'unknown'}"
        )
