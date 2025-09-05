from __future__ import annotations

from dataclasses import dataclass

from .social_json import SocialJson


@dataclass
class Social:
    """Runtime representation of a social command."""

    name: str
    char_no_arg: str = ""
    others_no_arg: str = ""
    char_found: str = ""
    others_found: str = ""
    vict_found: str = ""
    char_auto: str = ""
    others_auto: str = ""

    @classmethod
    def from_json(cls, data: SocialJson) -> "Social":
        return cls(**data.to_dict())
