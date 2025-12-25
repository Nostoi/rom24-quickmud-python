import asyncio

from mud.account import release_account
from mud.admin_logging.admin import toggle_log_all
from mud.config import (
    get_qmconfig,
    load_qmconfig,
    set_ansicolor,
    set_ansiprompt,
    set_telnetga,
)
from mud.models.character import Character, character_registry
from mud.models.constants import CommFlag, PlayerFlag, Sex
from mud.net.session import SESSIONS
from mud.account.account_manager import save_character as save_player_file
from mud.registry import room_registry
from mud.security import bans
from mud.security.bans import BanFlag, BanPermissionError
from mud.spawning.mob_spawner import spawn_mob
from mud.world.world_state import toggle_newlock, toggle_wizlock
from mud.wiznet import wiznet


ROM_NEWLINE = "\n\r"


def cmd_who(char: Character, args: str) -> str:
    lines = ["Online Players:"]
    for sess in SESSIONS.values():
        c = sess.character
        room_vnum = c.room.vnum if getattr(c, "room", None) else "?"
        lines.append(f" - {c.name} in room {room_vnum}")
    return "\n".join(lines)


def cmd_teleport(char: Character, args: str) -> str:
    if not args.isdigit() or int(args) not in room_registry:
        return "Invalid room."
    target = room_registry[int(args)]
    if char.room:
        char.room.remove_character(char)
    target.add_character(char)
    return f"Teleported to room {args}"


def cmd_spawn(char: Character, args: str) -> str:
    if not args.isdigit():
        return "Invalid vnum."
    mob = spawn_mob(int(args))
    if not mob:
        return "NPC not found."
    if not char.room:
        return "Nowhere to spawn."
    char.room.add_mob(mob)
    return f"Spawned {mob.name}."


def cmd_wizlock(char: Character, args: str) -> str:
    enabled = toggle_wizlock()
    if enabled:
        wiznet("$N has wizlocked the game.", char)
        return "Game wizlocked."
    wiznet("$N removes wizlock.", char)
    return "Game un-wizlocked."


def cmd_newlock(char: Character, args: str) -> str:
    enabled = toggle_newlock()
    if enabled:
        wiznet("$N locks out new characters.", char)
        return "New characters have been locked out."
    wiznet("$N allows new characters back in.", char)
    return "Newlock removed."


def cmd_telnetga(char: Character, args: str) -> str:
    """Toggle whether prompts append the telnet Go-Ahead control code."""

    if getattr(char, "is_npc", False):
        return ""

    if char.has_comm_flag(CommFlag.TELNET_GA):
        char.clear_comm_flag(CommFlag.TELNET_GA)
        _set_telnet_ga_state(char, False)
        return "Telnet GA removed."

    char.set_comm_flag(CommFlag.TELNET_GA)
    _set_telnet_ga_state(char, True)
    return "Telnet GA enabled."


def cmd_qmconfig(char: Character, args: str) -> str:
    if getattr(char, "is_npc", False):
        return ""

    stripped = args.strip()
    if not stripped:
        lines = [
            "Valid qmconfig options are:",
            "    show       (shows current status of toggles)",
            "    ansiprompt [on|off]",
            "    ansicolor  [on|off]",
            "    telnetga   [on|off]",
            "    read",
        ]
        return ROM_NEWLINE.join(lines) + ROM_NEWLINE

    tokens = stripped.split()
    option = tokens[0].lower()
    value = tokens[1].lower() if len(tokens) > 1 else ""

    def _matches_option(token: str, expected: str) -> bool:
        return _matches_toggle_prefix(token, expected)

    if _matches_option(option, "read"):
        load_qmconfig()
        return "Configuration reloaded from qmconfig.rc."

    if _matches_option(option, "show"):
        config = get_qmconfig()

        def _format(toggle: bool) -> str:
            return "{GON{x" if toggle else "{ROFF{x"

        lines = [
            f"ANSI prompt: {_format(config.ansiprompt)}",
            f"ANSI color : {_format(config.ansicolor)}",
            f"IP Address : {config.ip_address}",
            f"Telnet GA  : {_format(config.telnetga)}",
        ]
        return ROM_NEWLINE.join(lines) + ROM_NEWLINE

    def _is_truthy(token: str) -> bool:
        return _matches_toggle_prefix(token, "on")

    def _is_falsy(token: str) -> bool:
        return _matches_toggle_prefix(token, "off")

    if _matches_option(option, "ansiprompt"):
        if _is_truthy(value):
            set_ansiprompt(True)
            return "New logins will now get an ANSI color prompt." + ROM_NEWLINE
        if _is_falsy(value):
            set_ansiprompt(False)
            return "New logins will not get an ANSI color prompt." + ROM_NEWLINE
        return 'Valid arguments are "on" and "off".' + ROM_NEWLINE

    if _matches_option(option, "ansicolor"):
        if _is_truthy(value):
            set_ansicolor(True)
            return "New players will have color enabled." + ROM_NEWLINE
        if _is_falsy(value):
            set_ansicolor(False)
            return "New players will not have color enabled." + ROM_NEWLINE
        return 'Valid arguments are "on" and "off".' + ROM_NEWLINE

    if _matches_option(option, "telnetga"):
        if _is_truthy(value):
            set_telnetga(True)
            return "Telnet GA will be enabled for new players." + ROM_NEWLINE
        if _is_falsy(value):
            set_telnetga(False)
            return "Telnet GA will be disabled for new players." + ROM_NEWLINE
        return 'Valid arguments are "on" and "off".' + ROM_NEWLINE

    return "I have no clue what you are trying to do..." + ROM_NEWLINE


def _get_trust(char: Character) -> int:
    trust = int(getattr(char, "trust", 0) or 0)
    level = int(getattr(char, "level", 0) or 0)
    return trust if trust > 0 else level


def _set_telnet_ga_state(char: Character, enabled: bool) -> None:
    """Synchronize COMM_TELNET_GA between the player session and descriptor."""

    session = getattr(char, "desc", None)
    connection = getattr(session, "connection", None)
    if connection is not None and hasattr(connection, "set_go_ahead_enabled"):
        connection.set_go_ahead_enabled(enabled)
    if session is not None and hasattr(session, "go_ahead_enabled"):
        session.go_ahead_enabled = bool(enabled)


def _matches_toggle_prefix(value: str, expected: str) -> bool:
    """Return ``True`` when *value* is a ROM-style prefix for *expected*."""

    lowered = value.lower()
    return expected.startswith(lowered)


def _resolve_display_name(char: Character) -> str:
    name = getattr(char, "name", None)
    if name:
        return str(name)
    short_descr = getattr(char, "short_descr", None)
    if short_descr:
        return str(short_descr)
    return "Someone"


def _possessive_pronoun(char: Character) -> str:
    sex_raw = getattr(char, "sex", None)
    sex: Sex | None
    if isinstance(sex_raw, Sex):
        sex = sex_raw
    else:
        try:
            sex = Sex(int(sex_raw))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            sex = None
    if sex == Sex.MALE:
        return "his"
    if sex == Sex.FEMALE:
        return "her"
    if sex == Sex.NONE:
        return "its"
    return "their"


def _broadcast_incog_message(char: Character, template: str) -> None:
    room = getattr(char, "room", None)
    if room is None:
        return
    message = template.format(
        name=_resolve_display_name(char),
        poss=_possessive_pronoun(char),
    )
    room.broadcast(message, exclude=char)


def _render_ban_listing() -> str:
    entries = bans.get_ban_entries()
    if not entries:
        return "No sites banned at this time." + ROM_NEWLINE
    lines = ["Banned sites  level  type     status"]
    for entry in entries:
        pattern = entry.to_pattern()
        if entry.flags & BanFlag.NEWBIES:
            type_text = "newbies"
        elif entry.flags & BanFlag.PERMIT:
            type_text = "permit"
        else:
            type_text = "all"
        status = "perm" if entry.flags & BanFlag.PERMANENT else "temp"
        lines.append(f"{pattern:<12}    {entry.level:3d}  {type_text:<7}  {status}")
    return ROM_NEWLINE.join(lines) + ROM_NEWLINE


def _apply_ban(char: Character, args: str, *, permanent: bool) -> str:
    stripped = args.strip()
    if not stripped:
        return _render_ban_listing()

    parts = stripped.split()
    host_token = parts[0]
    type_token = parts[1].lower() if len(parts) > 1 else "all"

    if type_token.startswith("all"):
        ban_type = BanFlag.ALL
    elif type_token.startswith("newbies"):
        ban_type = BanFlag.NEWBIES
    elif type_token.startswith("permit"):
        ban_type = BanFlag.PERMIT
    else:
        return "Acceptable ban types are all, newbies, and permit." + ROM_NEWLINE

    host = host_token.strip()
    prefix = host.startswith("*")
    suffix = host.endswith("*")
    core = host[1:] if prefix else host
    if suffix and core:
        core = core[:-1]
    core = core.strip()
    if not core:
        return "You have to ban SOMETHING." + ROM_NEWLINE

    trust = _get_trust(char)
    try:
        bans.add_banned_host(
            host,
            flags=ban_type,
            level=trust,
            permanent=permanent,
            trust_level=trust,
        )
    except BanPermissionError:
        return "That ban was set by a higher power." + ROM_NEWLINE

    try:
        bans.save_bans_file()
    except Exception:
        pass
    return f"{core} has been banned." + ROM_NEWLINE


def cmd_ban(char: Character, args: str) -> str:
    return _apply_ban(char, args, permanent=False)


def cmd_permban(char: Character, args: str) -> str:
    return _apply_ban(char, args, permanent=True)


def cmd_allow(char: Character, args: str) -> str:
    target = args.strip().lower()
    if not target:
        return "Remove which site from the ban list?" + ROM_NEWLINE

    if "*" in target:
        return "Site is not banned." + ROM_NEWLINE

    trust = _get_trust(char)
    try:
        removed = bans.remove_banned_host(target, trust_level=trust)
    except BanPermissionError:
        return "You are not powerful enough to lift that ban." + ROM_NEWLINE

    if not removed:
        return "Site is not banned." + ROM_NEWLINE

    try:
        bans.save_bans_file()
    except Exception:
        pass
    return f"Ban on {target} lifted." + ROM_NEWLINE


def cmd_unban(char: Character, args: str) -> str:
    # Maintain legacy alias while ROM exposes `allow`.
    return cmd_allow(char, args)


def cmd_banlist(char: Character, args: str) -> str:
    return _render_ban_listing()


def cmd_log(char: Character, args: str) -> str:
    arg = args.strip()
    if not arg:
        return "Log whom?"
    target_name, *_rest = arg.split(maxsplit=1)
    if target_name.lower() == "all":
        enabled = toggle_log_all()
        return "Log ALL on." if enabled else "Log ALL off."
    lowered = target_name.lower()
    target = next(
        (
            candidate
            for candidate in character_registry
            if candidate.name and candidate.name.lower().startswith(lowered)
        ),
        None,
    )
    if target is None:
        return "They aren't here."
    if getattr(target, "is_npc", False):
        return "Not on NPC's."
    target.log_commands = not getattr(target, "log_commands", False)
    return "LOG set." if target.log_commands else "LOG removed."


def cmd_incognito(char: Character, args: str) -> str:
    if getattr(char, "is_npc", False):
        return "Huh?"

    trust = _get_trust(char)
    token = args.strip().split(maxsplit=1)[0] if args.strip() else ""

    if not token:
        if getattr(char, "incog_level", 0):
            char.incog_level = 0
            _broadcast_incog_message(char, "{name} is no longer cloaked.")
            return "You are no longer cloaked."
        char.incog_level = trust
        _broadcast_incog_message(char, "{name} cloaks {poss} presence.")
        return "You cloak your presence."

    try:
        level = int(token)
    except ValueError:
        level = 0

    if level < 2 or level > trust:
        return "Incog level must be between 2 and your level."

    char.reply = None
    char.incog_level = level
    _broadcast_incog_message(char, "{name} cloaks {poss} presence.")
    return "You cloak your presence."


def cmd_holylight(char: Character, args: str) -> str:
    if getattr(char, "is_npc", False):
        return "Huh?"

    current = int(getattr(char, "act", 0) or 0)
    flag = int(PlayerFlag.HOLYLIGHT)

    if current & flag:
        char.act = current & ~flag
        return "Holy light mode off."

    char.act = current | flag
    return "Holy light mode on."


def list_hosts() -> list[str]:
    """Deprecated helper kept for backward compatibility in tests."""
    return sorted(entry.to_pattern() for entry in bans.get_ban_entries())


def _schedule_coro(coro) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
    else:
        loop.create_task(coro)


async def _notify_and_disconnect(target: Character, message: str) -> None:
    session = next((sess for sess in SESSIONS.values() if sess.character is target), None)
    connection = getattr(target, "connection", None)
    if session and session.connection is not None:
        connection = session.connection
    if connection:
        try:
            await connection.send_line(message)
        except Exception:
            pass
        try:
            await connection.close()
        except Exception:
            pass


def cmd_deny(char: Character, args: str) -> str:
    target_token = args.strip()
    if not target_token:
        return "Deny whom?"

    lowered = target_token.lower()
    target = next(
        (
            candidate
            for candidate in character_registry
            if candidate.name and candidate.name.lower().startswith(lowered)
        ),
        None,
    )
    if target is None:
        return "They aren't here."
    if getattr(target, "is_npc", False):
        return "Not on NPC's."

    actor_trust = _get_trust(char)
    target_trust = _get_trust(target)
    if target_trust >= actor_trust and target is not char:
        return "You failed."

    session = next((sess for sess in SESSIONS.values() if sess.character is target), None)
    account_name = None
    if session and getattr(session, "account_name", None):
        account_name = session.account_name
    elif getattr(target, "account_name", None):
        account_name = target.account_name
    if not account_name:
        return "They aren't here."

    deny_bit = int(PlayerFlag.DENY)
    already_denied = bool(getattr(target, "act", 0) & deny_bit)
    if already_denied:
        target.act &= ~deny_bit
        target.messages.append("You are granted access again.")
        bans.remove_banned_account(account_name)
        response = "DENY removed."
    else:
        target.act |= deny_bit
        target.messages.append("You are denied access!")
        bans.add_banned_account(account_name)
        response = "DENY set."
        if session:
            SESSIONS.pop(session.name, None)
        release_account(account_name)
        _schedule_coro(_notify_and_disconnect(target, "You are denied access."))

    try:
        save_player_file(target)
    except Exception:
        pass
    try:
        bans.save_bans_file()
    except Exception:
        pass
    return response
