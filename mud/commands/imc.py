from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from mud.imc import IMCHelp, IMCState, imc_enabled, maybe_open_socket

_PERMISSION_LEVELS: list[tuple[str, int]] = [
    ("Notset", 0),
    ("None", 1),
    ("Mort", 2),
    ("Imm", 3),
    ("Admin", 4),
    ("Imp", 5),
]

_PERMISSION_BY_NAME: dict[str, tuple[str, int]] = {
    name.lower(): (name, rank) for name, rank in _PERMISSION_LEVELS
}

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
