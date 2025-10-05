from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Iterable
from typing import TYPE_CHECKING

from mud.account import (
    LoginFailureReason,
    account_exists,
    create_account,
    create_character,
    get_creation_classes,
    get_creation_races,
    get_hometown_choices,
    get_race_archetype,
    get_weapon_choices,
    is_account_active,
    is_valid_account_name,
    list_characters,
    load_character,
    login_with_host,
    lookup_creation_class,
    lookup_creation_race,
    lookup_hometown,
    lookup_weapon_choice,
    release_account,
    roll_creation_stats,
    sanitize_account_name,
    save_character,
)
from mud.account.account_service import CreationSelection
from mud.commands import process_command
from mud.db.models import PlayerAccount
from mud.loaders.help_loader import help_greeting
from mud.models.constants import PlayerFlag, Sex
from mud.net.ansi import render_ansi
from mud.net.protocol import send_to_char
from mud.net.session import SESSIONS, Session
from mud.skills.groups import list_groups
from mud.security import bans
from mud.security.bans import BanFlag

STAT_LABELS = ("Str", "Int", "Wis", "Dex", "Con")

TELNET_IAC = 255
TELNET_WILL = 251
TELNET_WONT = 252
TELNET_DO = 253
TELNET_DONT = 254
TELNET_SB = 250
TELNET_GA = 249
TELNET_SE = 240
TELNET_TELOPT_ECHO = 1
TELNET_TELOPT_SUPPRESS_GA = 3

MAX_INPUT_LENGTH = 256
SPAM_REPEAT_THRESHOLD = 25


if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.account.account_service import ClassType, PcRaceType


class TelnetStream:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader = reader
        self.writer = writer
        self._buffer = bytearray()
        self._echo_enabled = True
        self._pushback: deque[int] = deque()
        self.ansi_enabled = True

    def set_ansi(self, enabled: bool) -> None:
        self.ansi_enabled = bool(enabled)

    def _render(self, message: str) -> str:
        return render_ansi(message, self.ansi_enabled)

    def _queue(self, data: bytes) -> None:
        if data:
            self._buffer.extend(data)

    async def flush(self) -> None:
        if not self._buffer:
            return
        self.writer.write(bytes(self._buffer))
        await self.writer.drain()
        self._buffer.clear()

    async def _send_option(self, command: int, option: int) -> None:
        await self.flush()
        self.writer.write(bytes([TELNET_IAC, command, option]))
        await self.writer.drain()

    async def negotiate(self) -> None:
        await self.enable_echo()
        await self._send_option(TELNET_DO, TELNET_TELOPT_SUPPRESS_GA)
        await self._send_option(TELNET_WILL, TELNET_TELOPT_SUPPRESS_GA)

    async def disable_echo(self) -> None:
        if self._echo_enabled:
            await self._send_option(TELNET_WILL, TELNET_TELOPT_ECHO)
            self._echo_enabled = False

    async def enable_echo(self) -> None:
        if not self._echo_enabled:
            await self._send_option(TELNET_WONT, TELNET_TELOPT_ECHO)
            self._echo_enabled = True
        elif self._echo_enabled:
            # ensure initial negotiation sends explicit state
            await self._send_option(TELNET_WONT, TELNET_TELOPT_ECHO)

    async def send_text(self, message: str, *, newline: bool = False) -> None:
        rendered = self._render(message)
        data = rendered.encode()
        if newline and not data.endswith(b"\r\n"):
            data += b"\r\n"
        self._queue(data)
        await self.flush()

    async def send_line(self, message: str) -> None:
        await self.send_text(message, newline=True)

    async def send_prompt(self, prompt: str) -> None:
        await self.flush()
        data = prompt.encode()
        self.writer.write(data + bytes([TELNET_IAC, TELNET_GA]))
        await self.writer.drain()

    async def _read_byte(self) -> int | None:
        if self._pushback:
            return self._pushback.popleft()
        data = await self.reader.read(1)
        if not data:
            return None
        return data[0]

    def _push_byte(self, value: int) -> None:
        self._pushback.appendleft(value)

    async def readline(self, *, max_length: int = MAX_INPUT_LENGTH) -> str | None:
        buffer = bytearray()
        too_long = False

        while True:
            byte = await self._read_byte()
            if byte is None:
                if not buffer:
                    return None
                break

            if byte == TELNET_IAC:
                command = await self._read_byte()
                if command is None:
                    return None
                if command in (TELNET_DO, TELNET_DONT, TELNET_WILL, TELNET_WONT):
                    await self._read_byte()
                    continue
                if command == TELNET_SB:
                    while True:
                        sub_byte = await self._read_byte()
                        if sub_byte is None:
                            return None
                        if sub_byte == TELNET_IAC:
                            end_byte = await self._read_byte()
                            if end_byte is None:
                                return None
                            if end_byte == TELNET_SE:
                                break
                    continue
                if command == TELNET_IAC:
                    if not too_long:
                        if len(buffer) >= max_length - 2:
                            too_long = True
                            await self.send_line("Line too long.")
                            continue
                        buffer.append(TELNET_IAC)
                    continue
                continue

            if byte in (10, 13):  # LF, CR
                if byte == 13:
                    follow = await self.reader.read(1)
                    if follow:
                        next_byte = follow[0]
                        if next_byte != 10:
                            self._push_byte(next_byte)
                break

            if byte in (8, 127):  # Backspace or delete
                if not too_long and buffer:
                    buffer.pop()
                continue

            if byte < 32 or byte > 126:
                continue

            if not too_long:
                if len(buffer) >= max_length - 2:
                    too_long = True
                    await self.send_line("Line too long.")
                    continue
                buffer.append(byte)

        return buffer.decode(errors="ignore") if buffer else ""

    async def close(self) -> None:
        await self.flush()
        self.writer.close()
        await self.writer.wait_closed()


async def _send(conn: TelnetStream, message: str) -> None:
    await conn.send_text(message)


async def _send_line(conn: TelnetStream, message: str) -> None:
    await conn.send_line(message)


async def _prompt(conn: TelnetStream, prompt: str, *, hide_input: bool = False) -> str | None:
    if hide_input:
        await conn.disable_echo()
    try:
        await conn.send_prompt(prompt)
        data = await conn.readline()
    finally:
        if hide_input:
            await conn.enable_echo()
            await conn.send_line("")
    if data is None:
        return None
    return data.strip()


async def _prompt_ansi_preference(conn: TelnetStream) -> tuple[bool, bool] | None:
    while True:
        response = await _prompt(conn, "Do you want ANSI? (Y/n) ")
        if response is None:
            return None
        lowered = response.lower()
        if not lowered:
            return conn.ansi_enabled, False
        if lowered.startswith("y"):
            return True, True
        if lowered.startswith("n"):
            return False, True
        await _send_line(conn, "Please answer Y or N.")


def _apply_colour_preference(char: Character, enabled: bool) -> None:
    """Synchronize ``char`` ANSI state with PLR_COLOUR bit."""

    colour_bit = int(PlayerFlag.COLOUR)
    act_flags = int(getattr(char, "act", 0))
    if enabled:
        act_flags |= colour_bit
    else:
        act_flags &= ~colour_bit
    char.act = act_flags
    char.ansi_enabled = bool(enabled)


async def _send_help_greeting(conn: TelnetStream) -> None:
    if not help_greeting:
        return
    text = help_greeting[1:] if help_greeting.startswith(".") else help_greeting
    if not text:
        return
    await conn.send_text(text, newline=True)


async def _read_player_command(conn: TelnetStream, session: Session) -> str | None:
    line = await conn.readline()
    if line is None:
        return None

    command = line if line else " "
    original = command

    should_track = len(original) > 1 or (original and original[0] == "!")
    if should_track:
        if original != "!" and original != session.last_command:
            session.repeat_count = 0
        else:
            session.repeat_count += 1
            if session.repeat_count >= SPAM_REPEAT_THRESHOLD:
                await conn.send_line("*** PUT A LID ON IT!!! ***")
                session.repeat_count = 0

    if original == "!":
        return session.last_command or ""

    if original.strip():
        session.last_command = original
    return command


async def _prompt_yes_no(conn: TelnetStream, prompt: str) -> bool | None:
    while True:
        response = await _prompt(conn, prompt)
        if response is None:
            return None
        lowered = response.lower()
        if lowered.startswith("y"):
            return True
        if lowered.startswith("n"):
            return False
        await _send_line(conn, "Please answer Y or N.")


async def _prompt_new_password(conn: TelnetStream) -> str | None:
    while True:
        password = await _prompt(conn, "New password: ", hide_input=True)
        if password is None:
            return None
        if len(password) < 5:
            await _send_line(conn, "Password must be at least five characters long.")
            continue
        confirm = await _prompt(conn, "Confirm password: ", hide_input=True)
        if confirm is None:
            return None
        if password != confirm:
            await _send_line(conn, "Passwords don't match.")
            continue
        return password


def _format_stats(stats: Iterable[int]) -> str:
    return ", ".join(f"{label} {value}" for label, value in zip(STAT_LABELS, stats, strict=True))


async def _run_account_login(conn: TelnetStream, host_for_ban: str | None) -> tuple[PlayerAccount, str] | None:
    while True:
        submitted = await _prompt(conn, "Account: ")
        if submitted is None:
            return None
        username = sanitize_account_name(submitted)
        if not username:
            continue
        if not is_valid_account_name(username):
            await _send_line(conn, "Illegal name, try another.")
            continue

        if account_exists(username):
            allow_reconnect = False
            if is_account_active(username):
                decision = await _prompt_yes_no(conn, "This account is already playing. Reconnect? (Y/N) ")
                if decision is None:
                    return None
                if not decision:
                    await _send_line(conn, "Ok, please choose another account.")
                    continue
                allow_reconnect = True

            password = await _prompt(conn, "Password: ", hide_input=True)
            if password is None:
                return None
            result = login_with_host(username, password, host_for_ban, allow_reconnect=allow_reconnect)
            if result.account:
                return result.account, username

            reason = result.failure
            if reason is LoginFailureReason.DUPLICATE_SESSION:
                await _send_line(conn, "Ok, please choose another account.")
                continue
            if reason is LoginFailureReason.BAD_CREDENTIALS:
                message = "Reconnect failed." if allow_reconnect else "Wrong password."
                await _send_line(conn, message)
                continue
            if reason is LoginFailureReason.WIZLOCK:
                await _send_line(conn, "The game is wizlocked.")
                return None
            if reason is LoginFailureReason.NEWLOCK:
                await _send_line(conn, "The game is newlocked.")
                return None
            if reason is LoginFailureReason.ACCOUNT_BANNED:
                await _send_line(conn, "You are denied access.")
                return None
            if reason is LoginFailureReason.HOST_BANNED:
                await _send_line(conn, "Your site has been banned from this mud.")
                return None
            if reason is LoginFailureReason.HOST_NEWBIES:
                await _send_line(conn, "New players are not allowed from your site.")
                return None
            await _send_line(conn, "Login failed.")
            continue

        precheck = login_with_host(username, "", host_for_ban)
        failure = precheck.failure
        if failure and failure is not LoginFailureReason.UNKNOWN_ACCOUNT:
            if failure is LoginFailureReason.NEWLOCK:
                await _send_line(conn, "The game is newlocked.")
            elif failure is LoginFailureReason.WIZLOCK:
                await _send_line(conn, "The game is wizlocked.")
            elif failure is LoginFailureReason.HOST_BANNED:
                await _send_line(conn, "Your site has been banned from this mud.")
            elif failure is LoginFailureReason.HOST_NEWBIES:
                await _send_line(conn, "New players are not allowed from your site.")
            elif failure is LoginFailureReason.ACCOUNT_BANNED:
                await _send_line(conn, "You are denied access.")
            else:
                await _send_line(conn, "Account creation is unavailable right now.")
            return None

        confirm = await _prompt_yes_no(conn, f"Create new account '{username.capitalize()}'? (Y/N) ")
        if confirm is None:
            return None
        if not confirm:
            await _send_line(conn, "Ok, please choose another account.")
            continue

        password = await _prompt_new_password(conn)
        if password is None:
            return None
        if not create_account(username, password):
            await _send_line(conn, "Account creation failed.")
            continue

        result = login_with_host(username, password, host_for_ban)
        if result.account:
            await _send_line(conn, "Account created.")
            return result.account, username

        await _send_line(conn, "Login failed.")
        return None


async def _prompt_for_race(conn: TelnetStream) -> "PcRaceType" | None:
    races = get_creation_races()
    await _send_line(conn, "Available races: " + ", ".join(race.name.title() for race in races))
    while True:
        response = await _prompt(conn, "Choose your race: ")
        if response is None:
            return None
        race = lookup_creation_race(response)
        if race is not None:
            return race
        await _send_line(conn, "That is not a valid race.")


async def _prompt_for_sex(conn: TelnetStream) -> Sex | None:
    while True:
        response = await _prompt(conn, "Sex (M/F): ")
        if response is None:
            return None
        lowered = response.lower()
        if lowered.startswith("m"):
            return Sex.MALE
        if lowered.startswith("f"):
            return Sex.FEMALE
        await _send_line(conn, "Please enter M or F.")


async def _prompt_for_class(conn: TelnetStream) -> "ClassType" | None:
    classes = get_creation_classes()
    await _send_line(conn, "Available classes: " + ", ".join(cls.name.title() for cls in classes))
    while True:
        response = await _prompt(conn, "Choose your class: ")
        if response is None:
            return None
        class_type = lookup_creation_class(response)
        if class_type is not None:
            return class_type
        await _send_line(conn, "That's not a valid class.")


async def _prompt_for_alignment(conn: TelnetStream) -> int | None:
    await _send_line(conn, "")
    await _send_line(conn, "You may be good, neutral, or evil.")
    while True:
        response = await _prompt(conn, "Which alignment (G/N/E)? ")
        if response is None:
            return None
        lowered = response.strip().lower()
        if lowered.startswith("g"):
            return 750
        if lowered.startswith("n"):
            return 0
        if lowered.startswith("e"):
            return -750
        await _send_line(conn, "That's not a valid alignment.")


async def _prompt_customization_choice(conn: TelnetStream) -> bool | None:
    await _send_line(conn, "")
    await _send_line(conn, "Do you wish to customize this character?")
    await _send_line(
        conn,
        "Customization takes time, but allows a wider range of skills and abilities.",
    )
    return await _prompt_yes_no(conn, "Customize (Y/N)? ")


async def _run_customization_menu(conn: TelnetStream, selection: CreationSelection) -> CreationSelection | None:
    await _send_line(conn, "")
    groups = selection.group_names()
    if groups:
        await _send_line(conn, "You already have the following groups: " + ", ".join(groups))
    await _send_line(
        conn,
        "Type 'list' to see costs, 'add <group>' to learn a group, or 'done' when finished.",
    )

    while True:
        response = await _prompt(conn, "Customization> ")
        if response is None:
            return None
        stripped = response.strip()
        if not stripped:
            continue
        parts = stripped.split(None, 1)
        command = parts[0].lower()
        argument = parts[1] if len(parts) > 1 else ""

        if command in {"done", "finish"}:
            minimum = selection.minimum_creation_points()
            if selection.creation_points < minimum:
                needed = minimum - selection.creation_points
                await _send_line(
                    conn,
                    f"You must select at least {minimum} creation points (need {needed} more).",
                )
                continue
            await _send_line(conn, f"Creation points: {selection.creation_points}")
            return selection

        if command == "list":
            await _send_line(conn, "Available groups:")
            for group in list_groups():
                cost = selection.cost_for_group(group.name)
                if cost is None:
                    continue
                status = "known" if selection.has_group(group.name) else f"{cost} points"
                await _send_line(conn, f"  {group.name} ({status})")
            continue

        if command == "add":
            if not argument:
                await _send_line(conn, "You must provide a group name to add.")
                continue
            if selection.add_group(argument, deduct=True):
                await _send_line(conn, f"{argument.strip().title()} group added.")
                await _send_line(conn, f"Creation points: {selection.creation_points}")
                continue
            if selection.has_group(argument):
                await _send_line(conn, "You already know that group.")
                continue
            cost = selection.cost_for_group(argument)
            if cost is None:
                await _send_line(conn, "That group is not available to your class.")
            else:
                await _send_line(conn, "Unable to add that group.")
            continue

        if command == "help":
            await _send_line(conn, "Commands: list, add <group>, done.")
            continue

        await _send_line(conn, "Choices are: list, add <group>, help, and done.")


async def _prompt_for_stats(conn: TelnetStream, race: "PcRaceType") -> list[int] | None:
    while True:
        stats = roll_creation_stats(race)
        await _send_line(conn, "Rolled stats: " + _format_stats(stats))
        while True:
            choice = await _prompt(conn, "Keep these stats? (K to keep, R to reroll): ")
            if choice is None:
                return None
            lowered = choice.lower()
            if lowered.startswith("k"):
                return stats
            if lowered.startswith("r"):
                break
            await _send_line(conn, "Please type K to keep or R to reroll.")


async def _prompt_for_hometown(conn: TelnetStream) -> int | None:
    options = get_hometown_choices()
    if not options:
        return None
    if len(options) == 1:
        label, vnum = options[0]
        while True:
            decision = await _prompt_yes_no(conn, f"Your hometown will be {label}. Accept? (Y/N) ")
            if decision is None:
                return None
            if decision:
                return vnum
            await _send_line(conn, f"{label} is currently the only available hometown.")
    else:
        await _send_line(
            conn,
            "Available hometowns: " + ", ".join(name for name, _ in options),
        )
        while True:
            response = await _prompt(conn, "Choose your hometown: ")
            if response is None:
                return None
            selected_vnum = lookup_hometown(response)
            if selected_vnum is not None:
                return selected_vnum
            await _send_line(conn, "That is not a valid hometown.")
    return None


async def _prompt_for_weapon(conn: TelnetStream, class_type: "ClassType") -> int | None:
    choices = get_weapon_choices(class_type)
    await _send_line(conn, "Starting weapons: " + ", ".join(choice.title() for choice in choices))
    normalized = {choice.lower(): choice for choice in choices}
    while True:
        response = await _prompt(conn, "Choose your starting weapon: ")
        if response is None:
            return None
        key = response.strip().lower()
        if key in normalized:
            vnum = lookup_weapon_choice(key)
            if vnum is not None:
                return vnum
        await _send_line(conn, "That is not a valid weapon choice.")


async def _run_character_creation_flow(
    conn: TelnetStream,
    account: PlayerAccount,
    name: str,
) -> bool:
    sanitized = sanitize_account_name(name)
    if not is_valid_account_name(sanitized):
        await _send_line(conn, "Illegal character name, try another.")
        return False

    display = sanitized.capitalize()
    await _send_line(conn, f"Creating new character '{display}'.")
    confirm = await _prompt_yes_no(conn, f"Is '{display}' correct? (Y/N) ")
    if confirm is None:
        return False
    if not confirm:
        return False

    race = await _prompt_for_race(conn)
    if race is None:
        return False
    sex = await _prompt_for_sex(conn)
    if sex is None:
        return False
    class_type = await _prompt_for_class(conn)
    if class_type is None:
        return False
    alignment_value = await _prompt_for_alignment(conn)
    if alignment_value is None:
        return False

    selection = CreationSelection(race, class_type)
    customize = await _prompt_customization_choice(conn)
    if customize is None:
        return False
    if customize:
        result = await _run_customization_menu(conn, selection)
        if result is None:
            return False
        selection = result
    else:
        selection.apply_default_group()

    stats = await _prompt_for_stats(conn, race)
    if stats is None:
        return False
    hometown = await _prompt_for_hometown(conn)
    if hometown is None:
        return False
    weapon_vnum = await _prompt_for_weapon(conn, class_type)
    if weapon_vnum is None:
        return False

    success = create_character(
        account,
        sanitized,
        race=race,
        class_type=class_type,
        race_archetype=get_race_archetype(race.name),
        sex=sex,
        hometown_vnum=hometown,
        perm_stats=stats,
        alignment=alignment_value,
        default_weapon_vnum=weapon_vnum,
        creation_points=selection.creation_points,
        creation_groups=selection.group_names(),
        train=selection.train_value(),
    )
    if not success:
        await _send_line(conn, "Unable to create that character. Please choose another name.")
        return False

    await _send_line(conn, "Character created!")
    return True


async def _select_character(
    conn: TelnetStream,
    account: PlayerAccount,
    username: str,
) -> "Character" | None:
    while True:
        characters = list_characters(account)
        if characters:
            await _send_line(conn, "Characters: " + ", ".join(characters))
        response = await _prompt(conn, "Character: ")
        if response is None:
            return None
        candidate = response.strip()
        if not candidate:
            continue

        lookup = {entry.lower(): entry for entry in characters}
        chosen_name = lookup.get(candidate.lower())
        if chosen_name is None:
            created = await _run_character_creation_flow(conn, account, candidate)
            if not created:
                continue
            chosen_name = sanitize_account_name(candidate).capitalize()

        char = load_character(username, chosen_name)
        if char:
            return char
        await _send_line(conn, "Failed to load that character. Please try again.")


async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    addr = writer.get_extra_info("peername")
    host_for_ban = addr[0] if isinstance(addr, tuple) and addr else None
    session = None
    char = None
    account: PlayerAccount | None = None
    username = ""
    conn = TelnetStream(reader, writer)

    try:
        if host_for_ban and bans.is_host_banned(host_for_ban, BanFlag.ALL):
            await conn.send_line("Your site has been banned from this mud.")
            return

        await conn.negotiate()
        ansi_result = await _prompt_ansi_preference(conn)
        if ansi_result is None:
            return
        ansi_preference, ansi_explicit = ansi_result
        conn.set_ansi(ansi_preference)
        await _send_help_greeting(conn)

        login_result = await _run_account_login(conn, host_for_ban)
        if not login_result:
            return
        account, username = login_result

        char = await _select_character(conn, account, username)
        if char is None:
            return

        saved_colour = bool(int(getattr(char, "act", 0)) & int(PlayerFlag.COLOUR))
        desired_colour = ansi_preference if ansi_explicit else saved_colour
        _apply_colour_preference(char, desired_colour)
        conn.set_ansi(char.ansi_enabled)

        if char.room:
            try:
                char.room.add_character(char)
            except Exception as exc:
                print(f"[ERROR] Failed to add character to room: {exc}")

        char.connection = conn
        char.account_name = username
        session = Session(
            name=char.name or "",
            character=char,
            reader=reader,
            connection=conn,
            account_name=username,
            ansi_enabled=conn.ansi_enabled,
        )
        SESSIONS[session.name] = session
        char.desc = session
        print(f"[CONNECT] {addr} as {session.name}")

        try:
            if char.room:
                response = process_command(char, "look")
                await send_to_char(char, response)
            else:
                await send_to_char(char, "You are floating in a void...")
        except Exception as exc:
            print(f"[ERROR] Failed to send initial look: {exc}")
            await send_to_char(char, "Welcome to the world!")

        while True:
            try:
                await conn.send_prompt("> ")
                command = await _read_player_command(conn, session)
                if command is None:
                    break
                if not command.strip():
                    continue

                try:
                    response = process_command(char, command)
                    await send_to_char(char, response)
                except Exception as exc:
                    print(f"[ERROR] Command processing failed for '{command}': {exc}")
                    await send_to_char(
                        char,
                        "Sorry, there was an error processing that command.",
                    )

                while char and char.messages:
                    try:
                        msg = char.messages.pop(0)
                        await send_to_char(char, msg)
                    except Exception as exc:
                        print(f"[ERROR] Failed to send message: {exc}")
                        break

            except asyncio.CancelledError:
                break
            except Exception as exc:
                print(f"[ERROR] Connection loop error for {session.name if session else 'unknown'}: {exc}")
                break

    except Exception as exc:
        print(f"[ERROR] Connection handler error for {addr}: {exc}")
    finally:
        try:
            if char:
                save_character(char)
        except Exception as exc:
            print(f"[ERROR] Failed to save character: {exc}")

        try:
            if char and char.room:
                char.room.remove_character(char)
        except Exception as exc:
            print(f"[ERROR] Failed to remove character from room: {exc}")

        if session and session.name in SESSIONS:
            SESSIONS.pop(session.name, None)

        if char:
            char.desc = None
            try:
                char.account_name = ""
            except Exception:
                pass
            if getattr(char, "connection", None) is conn:
                char.connection = None

        if username:
            release_account(username)

        try:
            await conn.close()
        except Exception as exc:
            print(f"[ERROR] Failed to close connection: {exc}")

        print(f"[DISCONNECT] {addr} as {session.name if session else 'unknown'}")
