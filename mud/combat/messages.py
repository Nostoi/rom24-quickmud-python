"""ROM dam_message severity and broadcast helpers."""

from __future__ import annotations

from dataclasses import dataclass

from mud.math.c_compat import c_div
from mud.models.constants import ATTACK_TABLE, DamageType, Sex

TYPE_HIT = 1000
MAX_DAMAGE_MESSAGE = len(ATTACK_TABLE)


@dataclass(frozen=True)
class DamageMessages:
    """Container for ROM-style attacker/victim/room combat strings."""

    attacker: str | None
    victim: str | None
    room: str | None
    self_inflicted: bool = False


# Severity tiers mirror src/fight.c:dam_message percent thresholds.
_DAMAGE_TIERS: tuple[tuple[int, str, str], ...] = (
    (5, "scratch", "scratches"),
    (10, "graze", "grazes"),
    (15, "hit", "hits"),
    (20, "injure", "injures"),
    (25, "wound", "wounds"),
    (30, "maul", "mauls"),
    (35, "decimate", "decimates"),
    (40, "devastate", "devastates"),
    (45, "maim", "maims"),
    (50, "MUTILATE", "MUTILATES"),
    (55, "DISEMBOWEL", "DISEMBOWELS"),
    (60, "DISMEMBER", "DISMEMBERS"),
    (65, "MASSACRE", "MASSACRES"),
    (70, "MANGLE", "MANGLES"),
    (75, "*** DEMOLISH ***", "*** DEMOLISHES ***"),
    (80, "*** DEVASTATE ***", "*** DEVASTATES ***"),
    (85, "=== OBLITERATE ===", "=== OBLITERATES ==="),
    (90, ">>> ANNIHILATE <<<", ">>> ANNIHILATES <<<"),
    (95, "<<< ERADICATE >>>", "<<< ERADICATES >>>"),
)


def _safe_name(character: object) -> str:
    name = getattr(character, "name", None)
    if not name:
        return "Someone"
    return str(name)


def _reflexive_pronoun(character: object) -> str:
    try:
        sex = Sex(getattr(character, "sex", Sex.NONE))
    except ValueError:
        sex = Sex.NONE
    if sex == Sex.MALE:
        return "himself"
    if sex == Sex.FEMALE:
        return "herself"
    if sex == Sex.NONE:
        return "itself"
    return "themselves"


def _possessive_pronoun(character: object) -> str:
    try:
        sex = Sex(getattr(character, "sex", Sex.NONE))
    except ValueError:
        sex = Sex.NONE
    if sex == Sex.MALE:
        return "his"
    if sex == Sex.FEMALE:
        return "her"
    if sex == Sex.NONE:
        return "its"
    return "their"


def _severity_terms(damage: int, victim: object) -> tuple[str, str, int]:
    if damage <= 0:
        return "miss", "misses", 0
    max_hit = getattr(victim, "max_hit", 0) or 0
    divisor = max(1, int(max_hit))
    dam_percent = c_div(int(damage) * 100, divisor)
    for threshold, vs, vp in _DAMAGE_TIERS:
        if dam_percent <= threshold:
            return vs, vp, dam_percent
    return "do UNSPEAKABLE things to", "does UNSPEAKABLE things to", dam_percent


def _resolve_attack_noun(dt: int | str | None) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, str):
        stripped = dt.strip()
        return stripped or None
    if isinstance(dt, DamageType):
        dt = int(dt)
    if isinstance(dt, int):
        if dt == TYPE_HIT:
            return None
        if dt >= TYPE_HIT:
            idx = dt - TYPE_HIT
            if 0 <= idx < len(ATTACK_TABLE):
                noun = ATTACK_TABLE[idx].noun
                return noun or "hit"
            return "hit"
    return None


def dam_message(
    attacker: object,
    victim: object,
    damage: int,
    dt: int | str | None,
    immune: bool = False,
) -> DamageMessages:
    """Return ROM-style dam_message strings for the participants."""

    if attacker is None or victim is None:
        return DamageMessages(None, None, None, False)

    vs, vp, percent = _severity_terms(max(0, int(damage)), victim)
    punct = "." if percent <= 45 else "!"

    attacker_name = _safe_name(attacker)
    victim_name = _safe_name(victim)
    attack = _resolve_attack_noun(dt)
    self_inflicted = attacker is victim

    if attack is None and immune:
        attack = "attack"

    if int(percent) <= 0 and not immune:
        # Mirror ROM miss output
        if self_inflicted:
            room_msg = f"{{3{attacker_name} {vp} {_reflexive_pronoun(attacker)}{punct}{{x"
            attacker_msg = f"{{2You {vs} yourself{punct}{{x"
            return DamageMessages(attacker_msg, None, room_msg, True)
        room_msg = f"{{3{attacker_name} {vp} {victim_name}{punct}{{x"
        attacker_msg = f"{{2You {vs} {victim_name}{punct}{{x"
        victim_msg = f"{{4{attacker_name} {vp} you{punct}{{x"
        return DamageMessages(attacker_msg, victim_msg, room_msg, False)

    if immune:
        if self_inflicted:
            poss = _possessive_pronoun(attacker)
            room_msg = f"{{3{attacker_name} is unaffected by {poss} own {attack}.{{x"
            attacker_msg = "{2Luckily, you are immune to that.{x"
            return DamageMessages(attacker_msg, None, room_msg, True)
        room_msg = f"{{3{victim_name} is unaffected by {attacker_name}'s {attack}!{{x"
        attacker_msg = f"{{2{victim_name} is unaffected by your {attack}!{{x"
        victim_msg = f"{{4{attacker_name}'s {attack} is powerless against you.{{x"
        return DamageMessages(attacker_msg, victim_msg, room_msg, False)

    if attack is None:
        if self_inflicted:
            room_msg = f"{{3{attacker_name} {vp} {_reflexive_pronoun(attacker)}{punct}{{x"
            attacker_msg = f"{{2You {vs} yourself{punct}{{x"
            return DamageMessages(attacker_msg, None, room_msg, True)
        room_msg = f"{{3{attacker_name} {vp} {victim_name}{punct}{{x"
        attacker_msg = f"{{2You {vs} {victim_name}{punct}{{x"
        victim_msg = f"{{4{attacker_name} {vp} you{punct}{{x"
        return DamageMessages(attacker_msg, victim_msg, room_msg, False)

    if self_inflicted:
        poss = _possessive_pronoun(attacker)
        room_msg = f"{{3{attacker_name}'s {attack} {vp} {_reflexive_pronoun(attacker)}{punct}{{x"
        attacker_msg = f"{{2Your {attack} {vp} you{punct}{{x"
        return DamageMessages(attacker_msg, None, room_msg, True)

    room_msg = f"{{3{attacker_name}'s {attack} {vp} {victim_name}{punct}{{x"
    attacker_msg = f"{{2Your {attack} {vp} {victim_name}{punct}{{x"
    victim_msg = f"{{4{attacker_name}'s {attack} {vp} you{punct}{{x"
    return DamageMessages(attacker_msg, victim_msg, room_msg, False)


__all__: tuple[str, ...] = ("DamageMessages", "TYPE_HIT", "MAX_DAMAGE_MESSAGE", "dam_message")
