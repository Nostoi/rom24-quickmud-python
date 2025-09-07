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


# placeholder registry to track loaded socials
social_registry: dict[str, Social] = {}


def register_social(social: Social) -> None:
    """Register a social by its lowercase name."""
    social_registry[social.name.lower()] = social


# START socials
def expand_placeholders(message: str, actor: object, victim: object | None = None) -> str:
    """Replace basic ROM placeholders in social messages."""
    result = message.replace("$n", getattr(actor, "name", ""))
    if victim is not None:
        result = result.replace("$N", getattr(victim, "name", ""))
    return result
# END socials
