from __future__ import annotations

import json
from pathlib import Path

from mud.models.social import Social, register_social
from mud.models.social_json import SocialJson


def load_socials(path: str) -> None:
    """Load socials from a JSON file into the registry."""
    with open(Path(path), encoding="utf-8") as f:
        data = json.load(f)
    for entry in data:
        sj = SocialJson(**entry)
        register_social(Social.from_json(sj))
