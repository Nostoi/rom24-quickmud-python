from __future__ import annotations

from dataclasses import dataclass

from .social_json import SocialJson
from mud.models.constants import Sex


@dataclass
class Social:
    """Runtime representation of a social command."""

    name: str
    char_no_arg: str = ""
    others_no_arg: str = ""
    char_found: str = ""
    others_found: str = ""
    vict_found: str = ""
    not_found: str = ""
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
    def subj(sex: Sex | object) -> str:
        if isinstance(sex, Sex):
            return {Sex.MALE: "he", Sex.FEMALE: "she", Sex.NONE: "it"}.get(sex, "they")
        return "they"

    def obj(sex: Sex | object) -> str:
        if isinstance(sex, Sex):
            return {Sex.MALE: "him", Sex.FEMALE: "her", Sex.NONE: "it"}.get(sex, "them")
        return "them"

    def poss(sex: Sex | object) -> str:
        if isinstance(sex, Sex):
            return {Sex.MALE: "his", Sex.FEMALE: "her", Sex.NONE: "its"}.get(sex, "their")
        return "their"

    # Names
    result = message.replace("$n", getattr(actor, "name", ""))
    if victim is not None:
        result = result.replace("$N", getattr(victim, "name", ""))

    # Actor pronouns: replace $mself before $m to avoid overlap
    asex = getattr(actor, "sex", None)
    result = result.replace(
        "$mself",
        {Sex.MALE: "himself", Sex.FEMALE: "herself", Sex.NONE: "itself"}.get(asex, "themselves"),
    )
    result = result.replace("$e", subj(asex))
    result = result.replace("$m", obj(asex))
    result = result.replace("$s", poss(asex))

    # Victim pronouns: $E $M $S
    if victim is not None:
        vsex = getattr(victim, "sex", None)
        result = result.replace("$E", subj(vsex))
        result = result.replace("$M", obj(vsex))
        result = result.replace("$S", poss(vsex))

    return result
# END socials
