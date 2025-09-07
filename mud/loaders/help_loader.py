from __future__ import annotations

import json
from pathlib import Path

from mud.models.help import HelpEntry, register_help, help_registry
from mud.models.help_json import HelpJson


def load_help_file(path: str | Path) -> None:
    """Load help entries from ``path`` into ``help_registry``."""
    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    help_registry.clear()
    for raw in data:
        entry = HelpEntry.from_json(HelpJson.from_dict(raw))
        register_help(entry)
