from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence

from mud.admin_logging.admin import log_orphan_help_request
from mud.models.character import Character
from mud.models.constants import MAX_CMD_LEN
from mud.models.help import HelpEntry, help_entries, help_registry

_logger = logging.getLogger(__name__)

ROM_HELP_SEPARATOR = "\r\n============================================================\r\n\r\n"


def _ensure_crlf(text: str) -> str:
    """Normalise *text* to use CRLF line endings like ROM."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", "\r\n")


def _rom_lines(lines: Sequence[str]) -> str:
    """Return *lines* joined with ROM CRLF termination on each entry."""

    segments: list[str] = []
    for line in lines:
        formatted = _ensure_crlf(line)
        if not formatted.endswith("\r\n"):
            formatted = f"{formatted}\r\n"
        segments.append(formatted)
    return "".join(segments)


def _log_orphan_request(ch: Character, topic: str) -> bool:
    """Return True if *topic* was logged or ignored, False when rebuked."""

    if not topic:
        return True

    requester = getattr(ch, "name", "?") or "?"
    if len(topic) > MAX_CMD_LEN:
        trimmed = topic[: MAX_CMD_LEN - 1]
        _logger.warning(
            "Excessive help request length: %s requested %s.",
            requester,
            trimmed,
        )
        return False

    try:
        log_orphan_help_request(ch, topic)
    except OSError:
        _logger.exception("Failed to record orphaned help request for %s", requester)
    return True


def _normalize_topic(raw: str) -> str:
    """Mirror ROM ``one_argument`` handling for quoted phrases."""

    tokens: list[str] = []
    length = len(raw)
    index = 0
    while index < length:
        while index < length and raw[index].isspace():
            index += 1
        if index >= length:
            break
        char = raw[index]
        if char in {'"', "'", '%'}:
            terminator = char
            index += 1
        elif char == "(":
            terminator = ")"
            index += 1
        else:
            terminator = None
        token_chars: list[str] = []
        while index < length:
            current = raw[index]
            if terminator:
                if current == terminator:
                    index += 1
                    break
            else:
                if current.isspace():
                    break
            token_chars.append(current)
            index += 1
        if token_chars:
            tokens.append("".join(token_chars))
        while index < length and raw[index].isspace():
            index += 1
    return " ".join(tokens)


def _get_trust(ch: Character) -> int:
    return ch.trust if ch.trust > 0 else ch.level


def _visible_level(entry: HelpEntry) -> int:
    """Mirror ROM help level decoding where negative values map to trust levels."""

    return -entry.level - 1 if entry.level < 0 else entry.level


def _is_keyword_match(term: str, entry: HelpEntry) -> bool:
    if not term:
        return False

    term_lower = term.lower().strip()
    if not term_lower:
        return False

    parts = [segment for segment in term_lower.split() if segment]
    for raw_keyword in entry.keywords:
        tokens = [segment for segment in raw_keyword.lower().split() if segment]
        if not tokens:
            continue

        if any(token.startswith(term_lower) for token in tokens):
            return True

        if parts and all(any(token.startswith(part) for token in tokens) for part in parts):
            return True

    return False


def _generate_command_help(term: str) -> str | None:
    if not term:
        return None

    from mud.commands.dispatcher import COMMANDS, resolve_command

    lookup = term.lower()
    command = resolve_command(lookup)
    if command is None or (command.name != lookup and lookup not in command.aliases):
        for candidate in COMMANDS:
            if lookup in candidate.aliases:
                command = candidate
                break
    if command is None:
        return None

    aliases = ", ".join(command.aliases) if command.aliases else "None"
    position = command.min_position.name.replace("_", " ").title()
    restriction = "Immortal-only command." if command.admin_only else "Available to mortals."

    lines = [
        f"Command: {command.name}",
        f"Aliases: {aliases}",
        f"Minimum position: {position}",
        restriction,
    ]

    if command.name == "cast":
        lines.append("Usage: cast '<spell>' [target]")
        lines.append("Casting a learned spell consumes mana based on the spell level.")

    return _rom_lines(lines)


def _suggest_command_topics(term: str) -> list[str]:
    if not term:
        return []

    from mud.commands.dispatcher import COMMANDS

    lookup = term.lower()
    suggestions: list[str] = []
    for command in COMMANDS:
        if command.name.startswith(lookup) or any(alias.startswith(lookup) for alias in command.aliases):
            suggestions.append(command.name)

    if not suggestions and len(lookup) > 1:
        prefix = lookup[:2]
        suggestions = [cmd.name for cmd in COMMANDS if cmd.name.startswith(prefix)]

    seen: set[str] = set()
    ordered: list[str] = []
    for name in suggestions:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered[:5]


def do_help(ch: Character, args: str, *, limit_results: bool = False) -> str:
    topic = _normalize_topic(args)
    if not topic:
        topic = "summary"

    topic_lower = topic.lower()
    trust = _get_trust(ch)

    bucket = help_registry.get(topic_lower, [])
    blocked_entry = None
    matches: list[HelpEntry] = []
    seen_entries: set[int] = set()

    def _add_entry(candidate: HelpEntry) -> None:
        key = id(candidate)
        if key in seen_entries:
            return
        seen_entries.add(key)
        matches.append(candidate)

    def _consider(candidate: HelpEntry) -> None:
        nonlocal blocked_entry

        if not _is_keyword_match(topic, candidate):
            return

        if _visible_level(candidate) <= trust:
            _add_entry(candidate)
            return

        if blocked_entry is None:
            blocked_entry = candidate

    for candidate in bucket:
        _consider(candidate)

    for candidate in help_entries:
        _consider(candidate)

    if matches:
        if limit_results:
            matches = matches[:1]
        chunks: list[str] = []
        for candidate in matches:
            sections: list[str] = []
            if candidate.level >= 0 and topic_lower != "imotd":
                sections.append(" ".join(candidate.keywords))
            text = candidate.text
            if text.startswith("."):
                text = text[1:]
            sections.append(text)
            chunk = "\n".join(sections)
            chunks.append(_ensure_crlf(chunk))
        return ROM_HELP_SEPARATOR.join(chunks)

    if blocked_entry is None:
        command_help = _generate_command_help(topic)
        if command_help:
            if not _log_orphan_request(ch, topic):
                return _rom_lines(["No help on that word.", "That was rude!"])
            return command_help

    if blocked_entry is None:
        suggestions = _suggest_command_topics(topic)
        if suggestions:
            if not _log_orphan_request(ch, topic):
                return _rom_lines(["No help on that word.", "That was rude!"])
            suggestion_text = ", ".join(suggestions)
            return _rom_lines(["No help on that word.", f"Try: {suggestion_text}"])

    lines = ["No help on that word."]
    if topic:
        if not _log_orphan_request(ch, topic):
            lines.append("That was rude!")
            return _rom_lines(lines)
    return _rom_lines(lines)
