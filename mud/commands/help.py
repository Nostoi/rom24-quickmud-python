from __future__ import annotations

import logging
from collections.abc import Iterable

from mud.admin_logging.admin import log_orphan_help_request
from mud.models.character import Character
from mud.models.constants import MAX_CMD_LEN
from mud.models.help import HelpEntry, help_registry

_logger = logging.getLogger(__name__)

ROM_HELP_SEPARATOR = "\n============================================================\n\n"


def _get_trust(ch: Character) -> int:
    return ch.trust if ch.trust > 0 else ch.level


def _visible_level(entry: HelpEntry) -> int:
    """Mirror ROM help level decoding where negative values map to trust levels."""

    return -entry.level - 1 if entry.level < 0 else entry.level


def _iter_unique_entries(entries: Iterable[HelpEntry]) -> Iterable[HelpEntry]:
    seen: set[int] = set()
    for entry in entries:
        key = id(entry)
        if key in seen:
            continue
        seen.add(key)
        yield entry


def _is_keyword_match(term: str, entry: HelpEntry) -> bool:
    if not term:
        return False

    term_lower = term.lower()
    keywords = [keyword.lower() for keyword in entry.keywords]

    # Full-string prefix match mirrors the first str_prefix check in ROM's is_name.
    if any(keyword.startswith(term_lower) for keyword in keywords):
        return True

    parts = term_lower.split()
    if not parts:
        return False

    for part in parts:
        if not any(keyword.startswith(part) for keyword in keywords):
            return False
    return True


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

    return "\n".join(lines)


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


def do_help(ch: Character, args: str) -> str:
    topic = " ".join(args.strip().split())
    if not topic:
        topic = "summary"

    topic_lower = topic.lower()
    trust = _get_trust(ch)

    entry = help_registry.get(topic_lower)
    blocked_entry = None
    matches: list[HelpEntry] = []
    seen_entries: set[int] = set()

    def _add_entry(candidate: HelpEntry) -> None:
        key = id(candidate)
        if key in seen_entries:
            return
        seen_entries.add(key)
        matches.append(candidate)

    if entry:
        if _visible_level(entry) <= trust:
            _add_entry(entry)
        else:
            blocked_entry = entry

    for candidate in _iter_unique_entries(help_registry.values()):
        if candidate is entry:
            continue
        if not _is_keyword_match(topic, candidate):
            continue
        if _visible_level(candidate) > trust:
            if blocked_entry is None:
                blocked_entry = candidate
            continue
        _add_entry(candidate)

    if matches:
        chunks: list[str] = []
        for candidate in matches:
            sections: list[str] = []
            if candidate.level >= 0 and topic_lower != "imotd":
                sections.append(" ".join(candidate.keywords))
            text = candidate.text
            if text.startswith("."):
                text = text[1:]
            sections.append(text)
            chunks.append("\n".join(sections))
        return ROM_HELP_SEPARATOR.join(chunks)

    if blocked_entry is None:
        command_help = _generate_command_help(topic)
        if command_help:
            return command_help

    if blocked_entry is None:
        suggestions = _suggest_command_topics(topic)
        if suggestions:
            suggestion_text = ", ".join(suggestions)
            return f"No help on that word. Try: {suggestion_text}"

    message = "No help on that word."
    if topic:
        requester = getattr(ch, "name", "?") or "?"
        if len(topic) > MAX_CMD_LEN:
            trimmed = topic[: MAX_CMD_LEN - 1]
            _logger.warning(
                "Excessive help request length: %s requested %s.",
                requester,
                trimmed,
            )
            return message + "\nThat was rude!"
        try:
            log_orphan_help_request(ch, topic)
        except OSError:
            _logger.exception("Failed to record orphaned help request for %s", requester)
    return message
