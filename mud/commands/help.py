from __future__ import annotations

import logging
from collections.abc import Iterable

from mud.admin_logging.admin import log_orphan_help_request
from mud.models.character import Character
from mud.models.constants import MAX_CMD_LEN
from mud.models.help import HelpEntry, help_registry

_logger = logging.getLogger(__name__)


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


def do_help(ch: Character, args: str) -> str:
    topic = " ".join(args.strip().split())
    if not topic:
        topic = "summary"

    # Direct lookup first for the common path.
    entry = help_registry.get(topic.lower())
    if entry and _visible_level(entry) <= _get_trust(ch):
        return entry.text

    for candidate in _iter_unique_entries(help_registry.values()):
        if _visible_level(candidate) > _get_trust(ch):
            continue
        if _is_keyword_match(topic, candidate):
            return candidate.text

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
