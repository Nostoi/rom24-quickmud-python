from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Iterable
from types import SimpleNamespace
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
from mud.commands.inventory import give_school_outfit
from mud.commands.help import do_help
from mud.config import get_qmconfig
from mud.db.models import PlayerAccount
from mud.loaders import help_loader
from mud.logging import log_game_event
from mud.models.constants import CommFlag, PlayerFlag, Sex, ROOM_VNUM_LIMBO
from mud.net.ansi import render_ansi
from mud.net.protocol import send_to_char
from mud.net.session import SESSIONS, Session
from mud.wiznet import WiznetFlag, wiznet
from mud.skills.groups import get_group, list_groups
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

RECONNECT_MESSAGE = "Reconnecting. Type replay to see missed tells."


if TYPE_CHECKING:
    from mud.models.character import Character
    from mud.account.account_service import ClassType, PcRaceType


def _format_three_column_table(entries: Iterable[tuple[str, str]]) -> list[str]:
    cells = [f"{name:<18} {value:<5}" for name, value in entries]
    lines: list[str] = []
    for index in range(0, len(cells), 3):
        segment = cells[index : index + 3]
        lines.append(" ".join(segment).rstrip())
    return lines


def _format_name_columns(names: Iterable[str], *, width: int = 20) -> list[str]:
    cells = [f"{name:<{width}}" for name in names]
    lines: list[str] = []
    for index in range(0, len(cells), 3):
        segment = cells[index : index + 3]
        lines.append(" ".join(segment).rstrip())
    return lines


def _effective_trust(char: "Character") -> int:
    """Mirror ROM's ``get_trust`` helper for wiznet broadcasts."""

    trust = getattr(char, "trust", 0)
    return trust if trust > 0 else getattr(char, "level", 0)


def _sanitize_host(host: str | None, *, placeholder: str | None = None) -> str | None:
    """Return a trimmed host string or a placeholder when resolution fails."""

    if not host:
        return placeholder
    cleaned = host.strip()
    return cleaned or placeholder


def announce_wiznet_login(char: "Character", host: str | None = None) -> None:
    """Broadcast a WIZ_LOGINS notice when *char* enters the game."""

    if not getattr(char, "name", None):
        return

    wiznet(
        "$N has left real life behind.",
        char,
        None,
        WiznetFlag.WIZ_LOGINS,
        WiznetFlag.WIZ_SITES,
        _effective_trust(char),
    )

    host_display = _sanitize_host(host, placeholder="(unknown)")
    site_message = f"{char.name}@{host_display} has connected."
    log_game_event(site_message)

    wiznet(
        site_message,
        None,
        None,
        WiznetFlag.WIZ_SITES,
        None,
        _effective_trust(char),
    )


def announce_wiznet_logout(char: "Character") -> None:
    """Broadcast a WIZ_LOGINS notice when *char* leaves the game."""

    if not getattr(char, "name", None):
        return

    log_game_event(f"{char.name} has quit.")

    wiznet(
        "$N rejoins the real world.",
        char,
        None,
        WiznetFlag.WIZ_LOGINS,
        None,
        _effective_trust(char),
    )


def announce_wiznet_new_player(
    name: str,
    host: str | None = None,
    *,
    trust_level: int = 1,
    sex: Sex | int | None = None,
) -> None:
    """Broadcast WIZ_NEWBIE and WIZ_SITES notices for a freshly created player.

    Mirrors ROM's ``nanny.c`` flow by alerting immortals that a new character
    has just completed creation, including the originating host when available.
    """

    normalized = name.strip()
    if not normalized:
        return

    placeholder = SimpleNamespace(name=normalized, sex=sex)

    wiznet(
        "Newbie alert!  $N sighted.",
        placeholder,
        None,
        WiznetFlag.WIZ_NEWBIE,
        None,
        0,
    )

    sanitized_host = _sanitize_host(host, placeholder="(unknown)")
    site_message = f"{normalized}@{sanitized_host} new player."
    log_game_event(site_message)

    wiznet(
        site_message,
        None,
        None,
        WiznetFlag.WIZ_SITES,
        None,
        max(trust_level, 0),
    )


def _broadcast_reconnect_notifications(char: "Character", host: str | None = None) -> None:
    """Notify the room and wiznet listeners about a successful reconnect."""

    name = getattr(char, "name", None)
    if not name:
        return

    room = getattr(char, "room", None)
    if room is not None:
        room.broadcast(f"{name} has reconnected.", exclude=char)

    host_candidate = host
    if host_candidate is None:
        session = getattr(char, "desc", None)
        if session is not None:
            host_candidate = getattr(getattr(session, "connection", None), "peer_host", None)
    if host_candidate is None:
        host_candidate = getattr(getattr(char, "connection", None), "peer_host", None)
    host_display = _sanitize_host(host_candidate, placeholder="(unknown)")
    log_game_event(f"{name}@{host_display} reconnected.")

    wiznet(
        "$N groks the fullness of $S link.",
        char,
        None,
        WiznetFlag.WIZ_LINKS,
        None,
        0,
    )


def _announce_login_or_reconnect(char: "Character", host: str | None, reconnecting: bool) -> bool:
    """Dispatch wiznet announcements for fresh logins or reconnects."""

    note_reminder = False
    if reconnecting:
        _broadcast_reconnect_notifications(char, host)
        pcdata = getattr(char, "pcdata", None)
        note_reminder = bool(getattr(pcdata, "in_progress", None))
    else:
        announce_wiznet_login(char, host)
    return note_reminder


def _stop_idling(char: "Character") -> None:
    """Mirror ROM's ``stop_idling`` to pull players out of limbo on input."""

    if char is None:
        return

    previous_room = getattr(char, "was_in_room", None)
    if previous_room is None:
        return

    current_room = getattr(char, "room", None)
    current_vnum = getattr(current_room, "vnum", None)
    if current_vnum != ROOM_VNUM_LIMBO:
        return

    destination = previous_room
    try:
        if current_room is not None:
            current_room.remove_character(char)
    except Exception:
        pass

    try:
        destination.add_character(char)
    except Exception:
        # If re-entry fails, leave the character parked in limbo and retain state.
        try:
            if current_room is not None:
                current_room.add_character(char)
        except Exception:
            pass
        return

    char.was_in_room = None
    try:
        char.timer = 0
    except Exception:
        pass

    name = getattr(char, "name", None) or "Someone"
    try:
        destination.broadcast(f"{name} has returned from the void.", exclude=char)
    except Exception:
        pass


class TelnetStream:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader = reader
        self.writer = writer
        self._buffer = bytearray()
        self._echo_enabled = True
        self._pushback: deque[int] = deque()
        self.ansi_enabled = True
        self.peer_host: str | None = None
        self._go_ahead_enabled = True

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
        normalized = rendered.replace("\r\n", "\n\r")
        data = normalized.encode()
        if newline:
            if data.endswith(b"\n\r"):
                pass
            elif data.endswith(b"\r\n"):
                data = data[:-2] + b"\n\r"
            elif data.endswith(b"\r"):
                data = data[:-1] + b"\n\r"
            elif data.endswith(b"\n"):
                data = data[:-1] + b"\n\r"
            else:
                data += b"\n\r"
        self._queue(data)
        await self.flush()

    async def send_line(self, message: str) -> None:
        await self.send_text(message, newline=True)

    def set_go_ahead_enabled(self, enabled: bool) -> None:
        self._go_ahead_enabled = bool(enabled)

    async def send_prompt(self, prompt: str, *, go_ahead: bool | None = None) -> None:
        await self.flush()
        data = prompt.encode()
        self.writer.write(data)
        use_ga = self._go_ahead_enabled if go_ahead is None else bool(go_ahead)
        if go_ahead is not None:
            self._go_ahead_enabled = use_ga
        if use_ga:
            self.writer.write(bytes([TELNET_IAC, TELNET_GA]))
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


async def _prompt(
    conn: TelnetStream, prompt: str, *, hide_input: bool = False, go_ahead: bool | None = None
) -> str | None:
    if hide_input:
        await conn.disable_echo()
    try:
        await conn.send_prompt(prompt, go_ahead=go_ahead)
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


def _is_new_player(char: "Character") -> bool:
    if getattr(char, "is_npc", False):
        return False
    try:
        level = int(getattr(char, "level", 0) or 0)
    except Exception:
        level = 0
    try:
        played = int(getattr(char, "played", 0) or 0)
    except Exception:
        played = 0
    return level <= 1 and played == 0


def _apply_qmconfig_telnetga(
    char: "Character",
    session: Session,
    connection: TelnetStream,
    *,
    default_enabled: bool,
    is_new_player: bool,
) -> None:
    if is_new_player:
        if default_enabled:
            char.set_comm_flag(CommFlag.TELNET_GA)
        else:
            char.clear_comm_flag(CommFlag.TELNET_GA)

    telnet_enabled = char.has_comm_flag(CommFlag.TELNET_GA)
    connection.set_go_ahead_enabled(telnet_enabled)
    session.go_ahead_enabled = telnet_enabled


def _has_permit_flag(char: "Character") -> bool:
    """Return ``True`` when *char* has the ROM PLR_PERMIT bit set."""

    act_flags = int(getattr(char, "act", 0) or 0)
    return bool(act_flags & int(PlayerFlag.PERMIT))


async def _send_help_greeting(conn: TelnetStream) -> None:
    greeting = help_loader.help_greeting
    if not greeting:
        return
    text = greeting[1:] if greeting.startswith(".") else greeting
    if not text:
        return
    if conn.ansi_enabled:
        # Ensure ANSI-capable clients receive an ANSI escape sequence in the greeting.
        text = "{x" + text
    await conn.send_text(text, newline=True)


def _resolve_help_text(char: "Character", topic: str, *, limit_first: bool = False) -> str | None:
    try:
        text = do_help(char, topic, limit_results=limit_first)
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"[ERROR] Failed to load help topic '{topic}': {exc}")
        return None
    if not text:
        return None
    stripped = text.strip()
    if not stripped or stripped == "No help on that word.":
        return None
    return text


def _strip_motd_trailer(text: str) -> str:
    trailer = "[Hit Return to continue]"
    if trailer not in text:
        return text
    cleaned = text.replace(trailer, "")
    return cleaned.strip()


def _extract_motd_from_greeting() -> str | None:
    greeting = help_loader.help_greeting
    if not greeting:
        return None
    text = greeting[1:] if greeting.startswith(".") else greeting
    marker = "-1 MOTD~"
    if marker not in text:
        return None
    motd = text.split(marker, 1)[1]
    motd = _strip_motd_trailer(motd)
    return motd or None


async def _send_login_motd(char: "Character") -> None:
    topics: list[str] = ["motd"]
    is_immortal_attr = getattr(char, "is_immortal", False)
    immortal = False
    if callable(is_immortal_attr):
        try:
            immortal = bool(is_immortal_attr())
        except Exception:  # pragma: no cover - defensive guard
            immortal = False
    else:
        immortal = bool(is_immortal_attr)

    if immortal:
        topics.insert(0, "imotd")

    for topic in topics:
        text = _resolve_help_text(char, topic)
        if not text and topic == "motd":
            text = _extract_motd_from_greeting()
        if not text:
            continue
        text = _strip_motd_trailer(text)
        try:
            await send_to_char(char, text)
        except Exception as exc:  # pragma: no cover - defensive guard
            print(f"[ERROR] Failed to send help topic '{topic}' to {getattr(char, 'name', '?')}: {exc}")


def _should_send_newbie_help(char: "Character") -> bool:
    if getattr(char, "is_npc", True):
        return False
    try:
        if int(getattr(char, "level", 0) or 0) > 1:
            return False
    except Exception:
        return False
    return not bool(getattr(char, "newbie_help_seen", False))


async def _send_newbie_help(char: "Character") -> None:
    text = _resolve_help_text(char, "newbie info")
    if not text:
        return
    try:
        await send_to_char(char, "")
        await send_to_char(char, text)
        await send_to_char(char, "")
    finally:
        setattr(char, "newbie_help_seen", True)
        try:
            save_character(char)
        except Exception as exc:  # pragma: no cover - defensive guard
            print(f"[ERROR] Failed to persist newbie help flag for {getattr(char, 'name', '?')}: {exc}")


async def _read_player_command(conn: TelnetStream, session: Session) -> str | None:
    while True:
        line = await conn.readline()
        if line is None:
            return None

        command = line if line else " "
        original = command

        if session.show_buffer:
            stripped = original.strip().lower()
            if stripped in ("", "c"):
                has_more = await session.send_next_page()
                if not has_more:
                    return " "
                continue
            if stripped == "q":
                session.clear_paging()
                return " "
            session.clear_paging()

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


async def _disconnect_session(session: Session) -> "Character" | None:
    """Disconnect an existing session so a new descriptor can take over."""

    old_conn = getattr(session, "connection", None)
    old_char = getattr(session, "character", None)
    setattr(session, "_forced_disconnect", True)

    if old_conn is not None:
        try:
            await old_conn.send_line("Your link has been taken over.")
        except Exception:
            pass
        try:
            await old_conn.close()
        except Exception:
            pass

    if old_char is not None:
        name = getattr(old_char, "name", "") or "Someone"
        log_game_event(f"Closing link to {name}.")
        room = getattr(old_char, "room", None)
        if room is not None:
            try:
                room.broadcast(f"{name} has lost the link.", exclude=old_char)
            except Exception:
                pass
        try:
            old_char.connection = None
        except Exception:
            pass
        try:
            old_char.desc = None
        except Exception:
            pass
        try:
            wiznet(
                "Net death has claimed $N.",
                old_char,
                None,
                WiznetFlag.WIZ_LINKS,
                None,
                0,
            )
        except Exception:
            pass

    if session.name in SESSIONS:
        SESSIONS.pop(session.name, None)

    try:
        session.connection = None
    except Exception:
        pass
    try:
        session.character = None
    except Exception:
        pass

    return old_char


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


async def _run_account_login(conn: TelnetStream, host_for_ban: str | None) -> tuple[PlayerAccount, str, bool] | None:
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
                return result.account, username, bool(result.was_reconnect)

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
            return result.account, username, bool(result.was_reconnect)

        await _send_line(conn, "Login failed.")
        return None


async def _prompt_for_race(conn: TelnetStream, help_character: object | None = None) -> "PcRaceType" | None:
    races = get_creation_races()
    await _send_line(conn, "Available races: " + ", ".join(race.name.title() for race in races))
    await _send_line(conn, "What is your race? (help for more information)")
    helper = help_character or SimpleNamespace(name="", trust=0, level=0, is_npc=False, room=None)
    while True:
        response = await _prompt(conn, "Choose your race: ")
        if response is None:
            return None
        stripped = response.strip()
        if not stripped:
            continue
        parts = stripped.split(None, 1)
        command = parts[0].lower()
        if command == "help":
            topic = parts[1].strip() if len(parts) > 1 else "race help"
            text = _resolve_help_text(helper, topic, limit_first=True)
            if text:
                page = text.rstrip("\r\n")
                await _send(conn, page + "\r\n")
            else:
                await _send_line(conn, "No help on that word.")
            continue
        race = lookup_creation_race(stripped)
        if race is not None:
            return race
        await _send_line(conn, "That's not a valid race.")


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


async def _run_customization_menu(
    conn: TelnetStream,
    selection: CreationSelection,
    helper_char: object | None = None,
) -> CreationSelection | None:
    async def _send_customization_costs() -> None:
        group_entries = [(name, str(cost)) for name, cost in selection.available_groups()]
        skill_entries = [(name, str(cost)) for name, cost in selection.available_skills()]

        if group_entries:
            for line in _format_three_column_table([("group", "cp")] * 3):
                await _send_line(conn, line)
            for line in _format_three_column_table(group_entries):
                await _send_line(conn, line)
        else:
            await _send_line(conn, "No additional groups are available.")

        if group_entries and skill_entries:
            await _send_line(conn, "")

        if skill_entries:
            for line in _format_three_column_table([("skill", "cp")] * 3):
                await _send_line(conn, line)
            for line in _format_three_column_table(skill_entries):
                await _send_line(conn, line)
        else:
            await _send_line(conn, "No additional skills are available.")

        await _send_line(conn, f"Creation points: {selection.creation_points}")
        await _send_line(conn, f"Experience per level: {selection.experience_per_level()}")

    helper = helper_char or SimpleNamespace(name="", trust=0, level=0, is_npc=False, room=None)

    menu_choice_help = _resolve_help_text(helper, "menu choice", limit_first=True)

    async def _send_menu_choice_help(*, fallback: bool = False) -> None:
        if menu_choice_help:
            await _send(conn, menu_choice_help.rstrip("\r\n") + "\r\n")
        elif fallback:
            await _send_line(conn, "Choice (add,drop,list,help)?")

    await _send_line(conn, "")
    header_text = _resolve_help_text(helper, "group header", limit_first=True)
    if header_text:
        await _send(conn, header_text.rstrip("\r\n") + "\r\n")
    await _send_customization_costs()
    await _send_line(conn, "")

    groups = selection.group_names()
    if groups:
        await _send_line(conn, "You already have the following groups: " + ", ".join(groups))
    await _send_line(
        conn,
        "Type 'list', 'learned', 'add <group>', 'drop <group>', 'info <group>', 'premise', or 'done'.",
    )
    await _send_menu_choice_help(fallback=True)

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
        if command == "learn" and argument.lower().startswith("ed"):
            command = "learned"

        if command in {"done", "finish"}:
            minimum = selection.minimum_creation_points()
            if selection.creation_points < minimum:
                needed = minimum - selection.creation_points
                await _send_line(
                    conn,
                    f"You must select at least {minimum} creation points (need {needed} more).",
                )
                await _send_menu_choice_help(fallback=True)
                continue
            await _send_line(conn, f"Creation points: {selection.creation_points}")
            await _send_line(conn, f"Experience per level: {selection.experience_per_level()}")
            return selection

        if command == "list":
            await _send_customization_costs()
            await _send_menu_choice_help(fallback=True)
            continue

        if command == "learned":
            learned_groups = selection.learned_groups()
            learned_skills = selection.learned_skills()

            if learned_groups:
                for line in _format_three_column_table([("group", "cp")] * 3):
                    await _send_line(conn, line)
                for line in _format_three_column_table([(name, str(cost)) for name, cost in learned_groups]):
                    await _send_line(conn, line)
            else:
                await _send_line(conn, "You haven't purchased any groups yet.")

            if learned_groups and learned_skills:
                await _send_line(conn, "")

            if learned_skills:
                for line in _format_three_column_table([("skill", "cp")] * 3):
                    await _send_line(conn, line)
                for line in _format_three_column_table([(name, str(cost)) for name, cost in learned_skills]):
                    await _send_line(conn, line)
            else:
                await _send_line(conn, "You haven't purchased any skills yet.")

            await _send_line(conn, f"Creation points: {selection.creation_points}")
            await _send_line(conn, f"Experience per level: {selection.experience_per_level()}")
            await _send_menu_choice_help(fallback=True)
            continue

        if command == "add":
            if not argument:
                await _send_line(conn, "You must provide a skill or group name to add.")
                await _send_menu_choice_help(fallback=True)
                continue
            if selection.has_group(argument):
                await _send_line(conn, "You already know that group.")
                await _send_menu_choice_help(fallback=True)
                continue
            if selection.has_skill(argument):
                await _send_line(conn, "You already know that skill.")
                await _send_menu_choice_help(fallback=True)
                continue

            group_cost = selection.cost_for_group(argument)
            if group_cost is not None:
                if group_cost > 0 and selection.creation_points + group_cost > selection.maximum_creation_points():
                    await _send_line(conn, "You cannot take more than 300 creation points.")
                    await _send_menu_choice_help(fallback=True)
                    continue
                if selection.add_group(argument, deduct=True):
                    await _send_line(
                        conn,
                        f"{selection.display_group_name(argument)} group added.",
                    )
                    await _send_line(conn, f"Creation points: {selection.creation_points}")
                    await _send_line(conn, f"Experience per level: {selection.experience_per_level()}")
                    await _send_menu_choice_help(fallback=True)
                    continue
                await _send_line(conn, "Unable to add that group.")
                await _send_menu_choice_help(fallback=True)
                continue

            skill_cost = selection.cost_for_skill(argument)
            if skill_cost is not None:
                if skill_cost > 0 and selection.creation_points + skill_cost > selection.maximum_creation_points():
                    await _send_line(conn, "You cannot take more than 300 creation points.")
                    await _send_menu_choice_help(fallback=True)
                    continue
                if selection.add_skill(argument):
                    await _send_line(
                        conn,
                        f"{selection.display_skill_name(argument)} skill added.",
                    )
                    await _send_line(conn, f"Creation points: {selection.creation_points}")
                    await _send_line(conn, f"Experience per level: {selection.experience_per_level()}")
                    await _send_menu_choice_help(fallback=True)
                    continue
                await _send_line(conn, "Unable to add that skill.")
                await _send_menu_choice_help(fallback=True)
                continue

            await _send_line(conn, "No skills or groups by that name.")
            await _send_menu_choice_help(fallback=True)
            continue

        if command == "drop":
            if not argument:
                await _send_line(conn, "You must provide a group name to drop.")
                await _send_menu_choice_help(fallback=True)
                continue
            if selection.drop_group(argument):
                await _send_line(conn, "Group dropped.")
                await _send_line(conn, f"Creation points: {selection.creation_points}")
                await _send_line(conn, f"Experience per level: {selection.experience_per_level()}")
                await _send_menu_choice_help(fallback=True)
                continue
            if selection.drop_skill(argument):
                await _send_line(conn, "Skill dropped.")
                await _send_line(conn, f"Creation points: {selection.creation_points}")
                await _send_line(conn, f"Experience per level: {selection.experience_per_level()}")
                await _send_menu_choice_help(fallback=True)
                continue
            await _send_line(conn, "You haven't bought any such skill or group.")
            await _send_menu_choice_help(fallback=True)
            continue

        if command == "info":
            topic = argument.strip().lower()
            if not topic:
                await _send_line(conn, "Usage: info <group>")
                await _send_menu_choice_help(fallback=True)
                continue
            if topic == "all":
                for line in _format_name_columns(group.name for group in list_groups()):
                    await _send_line(conn, line)
                await _send_menu_choice_help(fallback=True)
                continue
            group = get_group(argument)
            if group is None:
                await _send_line(conn, "No group of that name exists.")
                await _send_menu_choice_help(fallback=True)
                continue
            if group.skills:
                await _send_line(conn, f"Group members for {group.name}:")
                for line in _format_name_columns(group.skills):
                    await _send_line(conn, line)
            else:
                await _send_line(conn, "That group has no additional skills.")
            await _send_menu_choice_help(fallback=True)
            continue

        if command == "premise":
            text = _resolve_help_text(helper, "premise", limit_first=True)
            if text:
                await _send(conn, text.rstrip("\r\n") + "\r\n")
            else:
                await _send_line(conn, "No help on that word.")
            await _send_menu_choice_help(fallback=True)
            continue

        if command == "help":
            topic = argument.strip() or "group help"
            text = _resolve_help_text(helper, topic, limit_first=True)
            if text:
                await _send(conn, text.rstrip("\r\n") + "\r\n")
            else:
                await _send_line(conn, "No help on that word.")
            await _send_menu_choice_help(fallback=True)
            continue

        await _send_line(
            conn,
            "Choices are: list, learned, add <group>, drop <group>, info <group>, premise, help, and done.",
        )
        await _send_menu_choice_help(fallback=True)


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
    *,
    permit_banned: bool = False,
    newbie_banned: bool = False,
) -> bool:
    sanitized = sanitize_account_name(name)
    if not is_valid_account_name(sanitized):
        await _send_line(conn, "Illegal character name, try another.")
        return False

    if permit_banned:
        await _send_line(conn, "Your site has been banned from this mud.")
        return False

    if newbie_banned:
        await _send_line(conn, "New players are not allowed from your site.")
        return False

    display = sanitized.capitalize()
    preview_character = SimpleNamespace(
        name=display,
        trust=0,
        level=0,
        is_npc=False,
        room=None,
    )
    await _send_line(conn, f"Creating new character '{display}'.")
    confirm = await _prompt_yes_no(conn, f"Is '{display}' correct? (Y/N) ")
    if confirm is None:
        return False
    if not confirm:
        return False

    race = await _prompt_for_race(conn, preview_character)
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
        result = await _run_customization_menu(conn, selection, preview_character)
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
        creation_skills=selection.skill_names(),
        train=selection.train_value(),
    )
    if not success:
        await _send_line(conn, "Unable to create that character. That name may already be taken.")
        return False

    announce_wiznet_new_player(
        display,
        conn.peer_host,
        trust_level=1,
        sex=sex,
    )
    await _send_line(conn, "Character created!")
    return True


async def _select_character(
    conn: TelnetStream,
    account: PlayerAccount,
    username: str,
    *,
    permit_banned: bool = False,
    newbie_banned: bool = False,
) -> tuple["Character", bool] | None:
    permit_bit = int(PlayerFlag.PERMIT)
    while True:
        all_characters = list_characters(account)
        characters = list_characters(account, require_act_flags=permit_bit) if permit_banned else all_characters

        if permit_banned and not characters:
            await _send_line(conn, "Your site has been banned from this mud.")
            return None

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
        if permit_banned and chosen_name is None:
            all_lookup = {entry.lower(): entry for entry in all_characters}
            if candidate.lower() in all_lookup:
                await _send_line(conn, "Your site has been banned from this mud.")
                return None

        if chosen_name is None:
            created = await _run_character_creation_flow(
                conn,
                account,
                candidate,
                permit_banned=permit_banned,
                newbie_banned=newbie_banned,
            )
            if not created:
                continue
            chosen_name = sanitize_account_name(candidate).capitalize()

        existing_session = SESSIONS.get(chosen_name)
        if existing_session:
            active_connection = getattr(existing_session, "connection", None)
            if active_connection is not None:
                decision = await _prompt_yes_no(
                    conn,
                    f"That character is already playing. Reconnect? (Y/N) ",
                )
                if decision is None:
                    return None
                if not decision:
                    await _send_line(conn, "Ok, please choose another character.")
                    continue

            transferred_char = await _disconnect_session(existing_session)
            if transferred_char is not None:
                if permit_banned and not _has_permit_flag(transferred_char):
                    await _send_line(conn, "Your site has been banned from this mud.")
                    return None
                return transferred_char, True

            if active_connection is not None:
                await _send_line(conn, "Reconnect attempt failed.")
                continue

        char = load_character(username, chosen_name)
        if char:
            if permit_banned and not _has_permit_flag(char):
                await _send_line(conn, "Your site has been banned from this mud.")
                return None
            return char, False
        await _send_line(conn, "Failed to load that character. Please try again.")


async def handle_connection_with_stream(
    conn: TelnetStream,
    host_for_ban: str | None = None,
    connection_type: str = "Telnet",
) -> None:
    """
    Handle a connection using a pre-created stream object (TelnetStream or SSHStream).
    
    This function is used by SSH and other connection types that create their own
    stream wrapper before calling the connection handler.
    
    Args:
        conn: Pre-created TelnetStream or SSHStream object
        host_for_ban: IP address for ban checking (optional)
        connection_type: Type of connection for logging (default: "Telnet")
    """
    session = None
    char = None
    account: PlayerAccount | None = None
    username = ""
    
    # Set peer host if not already set
    if host_for_ban and not conn.peer_host:
        conn.peer_host = host_for_ban
    
    permit_banned = bool(host_for_ban and bans.is_host_banned(host_for_ban, BanFlag.PERMIT))
    newbie_banned = bool(host_for_ban and bans.is_host_banned(host_for_ban, BanFlag.NEWBIES))
    qmconfig = get_qmconfig()

    try:
        if host_for_ban and bans.is_host_banned(host_for_ban, BanFlag.ALL):
            await conn.send_line("Your site has been banned from this mud.")
            return

        await conn.negotiate()
        if qmconfig.ansiprompt:
            ansi_result = await _prompt_ansi_preference(conn)
            if ansi_result is None:
                return
            ansi_preference, ansi_explicit = ansi_result
        else:
            ansi_preference = qmconfig.ansicolor
            ansi_explicit = False
        conn.set_ansi(ansi_preference)
        await _send_help_greeting(conn)

        login_result = await _run_account_login(conn, host_for_ban)
        if not login_result:
            return
        account, username, was_reconnect = login_result

        selection = await _select_character(
            conn,
            account,
            username,
            permit_banned=permit_banned,
            newbie_banned=newbie_banned,
        )
        if selection is None:
            return

        char, forced_reconnect = selection
        reconnecting = bool(was_reconnect or forced_reconnect)
        is_new_player = not bool(char.level)
        
        if char is None:
            return

        # Only save if this is truly a new character creation
        if is_new_player and not reconnecting:
            if account.id:
                char.account_id = account.id
                char.account_name = username
            try:
                save_character(char)
            except Exception as exc:
                print(f"[ERROR] Failed to save newly created character: {exc}")

        char.connection = conn
        char.desc = conn
        
        # Create a mock StreamReader for SSH connections (Session requires it but SSH doesn't use it)
        mock_reader = asyncio.StreamReader()
        
        session = Session(
            name=char.name or "",
            character=char,
            reader=mock_reader,
            connection=conn,
            account_name=username,
            ansi_enabled=conn.ansi_enabled,
        )
        SESSIONS[char.name] = session
        
        # Give starting outfit if new player
        outfit_message: str | None = None
        if is_new_player and give_school_outfit(char):
            outfit_message = "You have been equipped by Mota."

        print(f"[{connection_type}] {char.name} entered the game")
        
        # Send welcome messages
        try:
            if outfit_message:
                await send_to_char(char, outfit_message)
            if not reconnecting:
                await _send_login_motd(char)
                if _should_send_newbie_help(char):
                    await _send_newbie_help(char)
        except Exception as exc:
            print(f"[ERROR] Failed to send MOTD for {session.name}: {exc}")

        try:
            if reconnecting:
                await send_to_char(char, RECONNECT_MESSAGE)
            note_reminder = _announce_login_or_reconnect(char, host_for_ban, reconnecting)
            if reconnecting and note_reminder:
                await send_to_char(
                    char,
                    "You have a note in progress. Type NWRITE to continue it.",
                )
        except Exception as exc:
            print(f"[ERROR] Failed to announce wiznet login for {session.name}: {exc}")

        # Send initial room look
        try:
            if char.room:
                response = process_command(char, "look")
                await send_to_char(char, response)
            else:
                await send_to_char(char, "You are floating in a void...")
        except Exception as exc:
            print(f"[ERROR] Failed to send initial look: {exc}")
            await send_to_char(char, "Welcome to the world!")

        # Main game loop
        while True:
            try:
                await conn.send_prompt("> ", go_ahead=session.go_ahead_enabled)
                command = await _read_player_command(conn, session)
                if command is None:
                    break
                _stop_idling(char)
                if not command.strip():
                    continue

                try:
                    response = process_command(char, command)
                    await send_to_char(char, response)
                    
                    # Check if player requested quit
                    if getattr(char, "_quit_requested", False):
                        break
                        
                except Exception as exc:
                    print(f"[ERROR] Command processing failed for '{command}': {exc}")
                    await send_to_char(
                        char,
                        "Sorry, there was an error processing that command.",
                    )

            except asyncio.CancelledError:
                break
            except Exception as exc:
                print(f"[ERROR] Connection loop error for {session.name if session else 'unknown'}: {exc}")
                break

    except Exception as exc:
        print(f"[ERROR] {connection_type} connection handler error: {exc}")
    finally:
        forced_disconnect = bool(session and getattr(session, "_forced_disconnect", False))
        try:
            if char and not forced_disconnect:
                announce_wiznet_logout(char)
        except Exception as exc:
            print(f"[ERROR] Failed to announce wiznet logout for {session.name if session else 'unknown'}: {exc}")

        try:
            if char and not forced_disconnect:
                save_character(char)
        except Exception as exc:
            print(f"[ERROR] Failed to save character: {exc}")

        try:
            if char and char.room and not forced_disconnect:
                char.room.remove_character(char)
        except Exception as exc:
            print(f"[ERROR] Failed to remove character from room: {exc}")

        if session and not forced_disconnect and session.name in SESSIONS:
            SESSIONS.pop(session.name, None)

        if char:
            if not forced_disconnect:
                char.desc = None
                try:
                    char.account_name = ""
                except Exception:
                    pass
                if getattr(char, "connection", None) is conn:
                    char.connection = None

        if username and not forced_disconnect:
            release_account(username)

        try:
            await conn.close()
        except Exception as exc:
            print(f"[ERROR] Failed to close connection: {exc}")

        print(f"[{connection_type} DISCONNECT] {session.name if session else 'unknown'}")


async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    addr = writer.get_extra_info("peername")
    host_for_ban: str | None = None
    if isinstance(addr, tuple) and addr:
        host_candidate = addr[0]
        host_for_ban = host_candidate if isinstance(host_candidate, str) else None
    elif isinstance(addr, str):
        host_for_ban = addr
    session = None
    char = None
    account: PlayerAccount | None = None
    username = ""
    conn = TelnetStream(reader, writer)
    conn.peer_host = host_for_ban
    permit_banned = bool(host_for_ban and bans.is_host_banned(host_for_ban, BanFlag.PERMIT))
    newbie_banned = bool(host_for_ban and bans.is_host_banned(host_for_ban, BanFlag.NEWBIES))
    qmconfig = get_qmconfig()

    try:
        if host_for_ban and bans.is_host_banned(host_for_ban, BanFlag.ALL):
            await conn.send_line("Your site has been banned from this mud.")
            return

        await conn.negotiate()
        if qmconfig.ansiprompt:
            ansi_result = await _prompt_ansi_preference(conn)
            if ansi_result is None:
                return
            ansi_preference, ansi_explicit = ansi_result
        else:
            ansi_preference = qmconfig.ansicolor
            ansi_explicit = False
        conn.set_ansi(ansi_preference)
        await _send_help_greeting(conn)

        login_result = await _run_account_login(conn, host_for_ban)
        if not login_result:
            return
        account, username, was_reconnect = login_result

        selection = await _select_character(
            conn,
            account,
            username,
            permit_banned=permit_banned,
            newbie_banned=newbie_banned,
        )
        if selection is None:
            return

        char, forced_reconnect = selection
        reconnecting = bool(was_reconnect or forced_reconnect)

        is_new_player = _is_new_player(char)
        saved_colour = bool(int(getattr(char, "act", 0)) & int(PlayerFlag.COLOUR))
        desired_colour = ansi_preference if ansi_explicit else (qmconfig.ansicolor if is_new_player else saved_colour)
        _apply_colour_preference(char, desired_colour)
        conn.set_ansi(char.ansi_enabled)

        if char.room:
            try:
                char.room.add_character(char)
            except Exception as exc:
                print(f"[ERROR] Failed to add character to room: {exc}")

        char.connection = conn
        char.account_name = username
        if reconnecting:
            try:
                char.timer = 0
            except Exception:
                pass
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
        outfit_message: str | None = None
        if is_new_player and give_school_outfit(char):
            outfit_message = "You have been equipped by Mota."

        _apply_qmconfig_telnetga(
            char,
            session,
            conn,
            default_enabled=qmconfig.telnetga,
            is_new_player=is_new_player,
        )
        print(f"[CONNECT] {addr} as {session.name}")

        try:
            if outfit_message:
                await send_to_char(char, outfit_message)
            if not reconnecting:
                await _send_login_motd(char)
                if _should_send_newbie_help(char):
                    await _send_newbie_help(char)
        except Exception as exc:
            print(f"[ERROR] Failed to send MOTD for {session.name}: {exc}")

        try:
            if reconnecting:
                await send_to_char(char, RECONNECT_MESSAGE)
            note_reminder = _announce_login_or_reconnect(char, host_for_ban, reconnecting)
            if reconnecting and note_reminder:
                await send_to_char(
                    char,
                    "You have a note in progress. Type NWRITE to continue it.",
                )
        except Exception as exc:
            print(f"[ERROR] Failed to announce wiznet login for {session.name}: {exc}")

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
                await conn.send_prompt("> ", go_ahead=session.go_ahead_enabled)
                command = await _read_player_command(conn, session)
                if command is None:
                    break
                _stop_idling(char)
                if not command.strip():
                    continue

                try:
                    response = process_command(char, command)
                    await send_to_char(char, response)
                    
                    # Check if player requested quit
                    if getattr(char, "_quit_requested", False):
                        break
                        
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
        forced_disconnect = bool(session and getattr(session, "_forced_disconnect", False))
        try:
            if char and not forced_disconnect:
                announce_wiznet_logout(char)
        except Exception as exc:
            print(f"[ERROR] Failed to announce wiznet logout for {session.name if session else 'unknown'}: {exc}")

        try:
            if char and not forced_disconnect:
                save_character(char)
        except Exception as exc:
            print(f"[ERROR] Failed to save character: {exc}")

        try:
            if char and char.room and not forced_disconnect:
                char.room.remove_character(char)
        except Exception as exc:
            print(f"[ERROR] Failed to remove character from room: {exc}")

        if session and not forced_disconnect and session.name in SESSIONS:
            SESSIONS.pop(session.name, None)

        if char:
            if not forced_disconnect:
                char.desc = None
                try:
                    char.account_name = ""
                except Exception:
                    pass
                if getattr(char, "connection", None) is conn:
                    char.connection = None

        if username and not forced_disconnect:
            release_account(username)

        try:
            await conn.close()
        except Exception as exc:
            print(f"[ERROR] Failed to close connection: {exc}")

        print(f"[DISCONNECT] {addr} as {session.name if session else 'unknown'}")
