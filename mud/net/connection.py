from __future__ import annotations
import asyncio

from mud.world.world_state import create_test_character
from mud.account import load_character, save_character
from mud.commands import process_command
from mud.net.session import Session, SESSIONS
from mud.net.protocol import send_to_char


async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    addr = writer.get_extra_info("peername")
    session = None
    char = None
    
    try:
        writer.write(b"Welcome to PythonMUD\r\n")
        writer.write(b"What is your name?\r\n")
        await writer.drain()

        name_data = await reader.readline()
        if not name_data:
            return
        name = name_data.decode().strip() or "guest"

        # Gracefully handle character loading errors
        try:
            char = load_character(name, name)
        except Exception as e:
            print(f"[ERROR] Failed to load character {name}: {e}")
            char = None
        
        if not char:
            try:
                char = create_test_character(name, 3001)
            except Exception as e:
                print(f"[ERROR] Failed to create character {name}: {e}")
                writer.write(b"Sorry, there was an error creating your character. Please try again later.\r\n")
                await writer.drain()
                return
        else:
            # Only add to room if this is a loaded character (create_test_character already does this)
            if char and char.room:
                try:
                    char.room.add_character(char)
                except Exception as e:
                    print(f"[ERROR] Failed to add character to room: {e}")
        
        char.connection = writer

        session = Session(name=name, character=char, reader=reader, writer=writer)
        SESSIONS[name] = session
        print(f"[CONNECT] {addr} as {name}")

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
                    print(f"[ERROR] Command processing failed for '{command}': {e}")
                    await send_to_char(char, "Sorry, there was an error processing that command.")
                
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
                print(f"[ERROR] Connection loop error for {name}: {e}")
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
            
        if session and name in SESSIONS:
            SESSIONS.pop(name, None)
            
        try:
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f"[ERROR] Failed to close connection: {e}")
            
        print(f"[DISCONNECT] {addr} as {name if 'name' in locals() else 'unknown'}")
