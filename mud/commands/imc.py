from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any, Optional

from mud.imc import (
    IMCCHAN_LOG,
    IMC_HISTORY_LIMIT,
    IMCChannel,
    IMCHelp,
    IMCState,
    imc_enabled,
    maybe_open_socket,
    send_channel_message,
    update_channel_flags,
)
from mud.models.constants import Sex
from mud.models.social import Social, expand_placeholders, social_registry

_PERMISSION_LEVELS: list[tuple[str, int]] = [
    ("Notset", 0),
    ("None", 1),
    ("Mort", 2),
    ("Imm", 3),
    ("Admin", 4),
    ("Imp", 5),
]

_PERMISSION_BY_NAME: dict[str, tuple[str, int]] = {name.lower(): (name, rank) for name, rank in _PERMISSION_LEVELS}

_PERMISSION_BY_RANK: dict[int, str] = {rank: name for name, rank in _PERMISSION_LEVELS}

_MIN_VISIBLE_PERMISSION = _PERMISSION_BY_NAME["mort"][1]


def do_imc(char: Any, args: str) -> str:
    """IMC command stub.

    - Disabled (default): returns a gated message.
    - Enabled: returns basic help/usage; no sockets opened here.
    """
    if not imc_enabled():
        return "IMC is disabled. Set IMC_ENABLED=true to enable."

    try:
        state = maybe_open_socket()
    except (FileNotFoundError, ValueError) as exc:
        return f"IMC configuration error: {exc}"

    if not state:
        return "IMC is enabled but configuration is unavailable."

    tokens = args.split() if args else []
    if not tokens:
        return _format_help_summary(char, state)

    command = tokens[0].lower()
    if command in {"help", "?"}:
        topic = " ".join(tokens[1:]).strip()
        if not topic:
            return _format_help_summary(char, state)
        entry = state.helps.get(topic.lower())
        if not entry:
            return f"No IMC help entry named '{topic}'."
        header = entry.name
        if entry.permission:
            header = f"{header} ({entry.permission})"
        return "\n".join(filter(None, [header, entry.text]))

    return "IMC stub: command not implemented."


def _format_help_summary(char: Any, state: IMCState) -> str:
    topics_by_permission = _group_topics_by_permission(state.helps.values())
    if not topics_by_permission:
        return "IMC is enabled. No IMC help entries are available."

    max_permission = _character_permission_rank(char)

    lines: list[str] = [
        "Help is available for the following commands.",
        "---------------------------------------------",
        "",
    ]

    has_topics = False
    for name, rank in _PERMISSION_LEVELS:
        if rank < _MIN_VISIBLE_PERMISSION or rank > max_permission:
            continue

        topics = topics_by_permission.get(name, [])
        lines.append(f"{name} helps:")
        if topics:
            has_topics = True
            lines.extend(_render_columns(topics))
        lines.append("")

    if not has_topics:
        return "IMC is enabled. No IMC help entries are available."

    while lines and lines[-1] == "":
        lines.pop()

    lines.extend(
        [
            "",
            "For information about a specific command, see imchelp <command>.",
        ]
    )

    return "\n".join(lines)


def _group_topics_by_permission(entries: Iterable[IMCHelp]) -> dict[str, list[str]]:
    seen = set()
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for entry in entries:
        name = entry.name.strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        perm_name, _ = _normalize_permission(entry.permission)
        grouped[perm_name].append(name)

    for topics in grouped.values():
        topics.sort(key=str.lower)

    return grouped


def _normalize_permission(value: str | None) -> tuple[str, int]:
    if not value:
        return _PERMISSION_BY_NAME["mort"]

    stripped = value.strip()
    lower = stripped.lower()
    if lower in _PERMISSION_BY_NAME:
        return _PERMISSION_BY_NAME[lower]

    if stripped.isdigit():
        rank = int(stripped)
        if rank in _PERMISSION_BY_RANK:
            name = _PERMISSION_BY_RANK[rank]
            return name, rank

    return _PERMISSION_BY_NAME["mort"]


def _character_permission_rank(char: Any) -> int:
    explicit = getattr(char, "imc_permission", None)
    if isinstance(explicit, str):
        _, rank = _normalize_permission(explicit)
        return max(rank, _MIN_VISIBLE_PERMISSION)
    if isinstance(explicit, int):
        return max(explicit, _MIN_VISIBLE_PERMISSION)

    pcdata = getattr(char, "pcdata", None)
    security = getattr(pcdata, "security", 0) if pcdata else 0
    if isinstance(security, int) and security >= 9:
        return _PERMISSION_BY_NAME["admin"][1]

    if getattr(char, "is_admin", False):
        return _PERMISSION_BY_NAME["admin"][1]

    is_immortal = getattr(char, "is_immortal", None)
    if callable(is_immortal):
        try:
            if is_immortal():
                return _PERMISSION_BY_NAME["imm"][1]
        except Exception:
            pass

    return _MIN_VISIBLE_PERMISSION


def _render_columns(topics: Iterable[str]) -> list[str]:
    columns: list[str] = []
    row: list[str] = []
    for topic in topics:
        row.append(f"{topic:<15}")
        if len(row) == 6:
            columns.append("".join(row).rstrip())
            row = []

    if row:
        columns.append("".join(row).rstrip())

    return columns


def try_imc_command(char: Any, command: str, argument: str) -> Optional[str]:
    """Handle IMC channel-style commands when IMC is enabled."""

    if getattr(char, "is_npc", False):
        return None

    if not imc_enabled():
        return None

    try:
        state = maybe_open_socket()
    except (FileNotFoundError, ValueError):
        return "IMC is enabled but configuration is unavailable."

    if not state:
        return "IMC is enabled but configuration is unavailable."

    command_lower = command.lower()
    channel = next(
        (
            entry
            for entry in state.channels
            if entry.local_name.lower() == command_lower or entry.name.lower() == command_lower
        ),
        None,
    )
    if channel is None:
        return None

    required_level = channel.level or 0
    try:
        trust_value = int(getattr(char, "trust", getattr(char, "level", 0)) or 0)
    except (TypeError, ValueError):
        trust_value = 0
    perm_rank = _character_permission_rank(char)
    if trust_value < required_level and perm_rank < required_level:
        return None

    history_key = channel.local_name or channel.name
    history = state.channel_history.get(history_key, [])

    stripped_argument = argument.strip()

    if not stripped_argument:
        count = min(len(history), IMC_HISTORY_LIMIT)
        lines = [
            f"~cThe last {count} {history_key} messages:\r\n",
        ]
        for entry in history[-IMC_HISTORY_LIMIT:]:
            lines.append(f"{entry}\r\n")
        return "".join(lines)

    admin_rank = _PERMISSION_BY_NAME["admin"][1]
    if stripped_argument.lower() == "log" and perm_rank >= admin_rank:
        channel_name = channel.local_name or channel.name
        if channel.flags & IMCCHAN_LOG:
            updated_flags = channel.flags & ~IMCCHAN_LOG
            update_channel_flags(state, channel, updated_flags)
            return f"~GFile logging disabled for {channel_name}.\r\n"
        updated_flags = channel.flags | IMCCHAN_LOG
        update_channel_flags(state, channel, updated_flags)
        return f"~RFile logging enabled for {channel_name}, PLEASE don't forget to undo this when it isn't needed!\r\n"

    if not state.connection:
        return "IMC channel messaging is not available right now.\r\n"

    if not _character_listens_to_channel(char, history_key):
        return (
            f"You are not currently listening to {history_key}. "
            "Use the imclisten command to listen to this channel.\r\n"
        )

    payload = argument.lstrip()
    if payload.startswith("@"):
        social_argument = payload[1:].lstrip()
        social_result = _handle_channel_social(state, channel, char, social_argument)
        return social_result
    emote = 0
    if payload.startswith(","):
        payload = payload[1:].lstrip()
        emote = 1

    if not payload:
        return ""

    send_channel_message(state, channel, char, payload, emote)
    return ""


def _handle_channel_social(state: IMCState, channel: IMCChannel, char: Any, argument: str) -> str:
    if not argument:
        return ""

    social_name, remainder = _split_first_token(argument)
    if not social_name:
        return ""

    social = social_registry.get(social_name.lower())
    if social is None:
        return f"~YSocial ~W{social_name}~Y does not exist on this mud.\r\n"

    target_name = ""
    target_mud = ""
    if remainder:
        target_name, target_mud, error = _parse_social_target(remainder)
        if error:
            return error

    template, victim, error = _select_social_template(state, char, social, target_name, target_mud)
    if error:
        return error

    message = expand_placeholders(template, char, victim)
    send_channel_message(state, channel, char, message, 2)
    return ""


def _split_first_token(text: str) -> tuple[str, str]:
    parts = text.split(None, 1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def _parse_social_target(raw: str) -> tuple[str, str, Optional[str]]:
    if "@" not in raw:
        return "", "", "You need to specify a person@mud for a target.\r\n"
    person, mud = raw.split("@", 1)
    person = person.strip()
    mud = mud.strip()
    if not person or not mud:
        return "", "", "You need to specify a person@mud for a target.\r\n"
    return person, mud, None


def _select_social_template(
    state: IMCState,
    char: Any,
    social: Social,
    target_name: str,
    target_mud: str,
) -> tuple[str, Optional[Any], Optional[str]]:
    local_name = (state.config.get("LocalName") or "QuickMUD").lower()
    actor_name = getattr(char, "name", "")
    victim: Optional[Any] = None

    if target_name and target_mud:
        if target_name.lower() == actor_name.lower() and target_mud.lower() == local_name:
            template = social.others_auto
            if not template:
                display = social.name or ""
                return "", None, f"~YSocial ~W{display}~Y: Missing others_auto.\r\n"
            victim = SimpleNamespace(
                name=f"{target_name}@{target_mud}", sex=_resolve_remote_sex(state, target_name, target_mud)
            )
            return template, victim, None

        template = social.others_found
        if not template:
            display = social.name or ""
            return "", None, f"~YSocial ~W{display}~Y: Missing others_found.\r\n"
        victim = SimpleNamespace(
            name=f"{target_name}@{target_mud}", sex=_resolve_remote_sex(state, target_name, target_mud)
        )
        return template, victim, None

    template = social.others_no_arg
    if not template:
        display = social.name or ""
        return "", None, f"~YSocial ~W{display}~Y: Missing others_no_arg.\r\n"
    return template, None, None


def _resolve_remote_sex(state: IMCState, person: str, mud: str) -> Sex:
    key = f"{person}@{mud}".lower()
    entry = state.user_cache.get(key)
    if entry and entry.gender is not None:
        try:
            return Sex(entry.gender)
        except ValueError:
            pass
    return Sex.MALE


def _character_listens_to_channel(char: Any, channel_name: str) -> bool:
    if not channel_name:
        return True

    raw_listen = getattr(char, "imc_listen", None)
    if raw_listen is None:
        return False

    entries: set[str]
    if isinstance(raw_listen, str):
        entries = {token.lower() for token in raw_listen.split() if token}
    else:
        try:
            entries = {str(token).lower() for token in raw_listen if token}
        except TypeError:
            entries = {str(raw_listen).lower()}

    return channel_name.lower() in entries
