from __future__ import annotations

import json
import shlex
from pathlib import Path

from mud.models.area import Area
from mud.models.help import HelpEntry, help_registry, register_help
from mud.models.help_json import HelpJson

from .base_loader import BaseTokenizer


def load_help_file(path: str | Path) -> None:
    """Load help entries from ``path`` into ``help_registry``."""
    with open(path, encoding="utf-8") as fp:
        data = json.load(fp)
    help_registry.clear()
    for raw in data:
        entry = HelpEntry.from_json(HelpJson.from_dict(raw))
        register_help(entry)


def load_helps(tokenizer: BaseTokenizer, area: Area) -> None:
    """Parse a legacy ``#HELPS`` block into runtime help entries.

    Mirrors ROM's ``load_helps`` by reading a level integer followed by a
    tilde-terminated keyword string and a tilde-terminated help body for each
    entry until encountering the ``$`` sentinel.
    """

    while True:
        line = tokenizer.next_line()
        if line is None:
            raise ValueError("unexpected EOF within #HELPS section")

        parts = line.split(None, 1)
        if not parts:
            continue

        try:
            level = int(parts[0])
        except ValueError as exc:
            raise ValueError("invalid #HELPS entry: level must be an integer") from exc

        keywords_part = parts[1] if len(parts) > 1 else ""
        if keywords_part.endswith("~"):
            keywords_part = keywords_part[:-1]

        if keywords_part == "$":
            break

        keyword_tokens = shlex.split(keywords_part)
        if not keyword_tokens:
            raise ValueError("invalid #HELPS entry: missing keyword list")

        text = tokenizer.read_string_tilde()
        entry = HelpEntry(keywords=keyword_tokens, text=text, level=level)
        area.helps.append(entry)
        register_help(entry)
