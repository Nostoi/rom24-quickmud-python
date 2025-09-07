from __future__ import annotations

from dataclasses import dataclass

from .json_io import JsonDataclass


@dataclass
class SocialJson(JsonDataclass):
    """Social command messages matching ``schemas/social.schema.json``."""

    name: str
    char_no_arg: str = ""
    others_no_arg: str = ""
    char_found: str = ""
    others_found: str = ""
    vict_found: str = ""
    not_found: str = ""
    char_auto: str = ""
    others_auto: str = ""
