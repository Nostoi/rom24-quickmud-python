"""ROM dam_message severity and broadcast helpers."""

from __future__ import annotations

from dataclasses import dataclass

from mud.math.c_compat import c_div
from mud.models.constants import ATTACK_TABLE, DamageType, Sex
from mud.world.vision import pers

TYPE_HIT = 1000
MAX_DAMAGE_MESSAGE = len(ATTACK_TABLE)


@dataclass(frozen=True)
class DamageMessages:
    """Container for ROM-style attacker/victim/room combat templates.

    Each field is a `.format()`-ready template containing `{attacker}`
    and/or `{victim}` placeholders. Use `render_for(template,
    attacker, victim, observer)` to substitute ROM `PERS()`-rendered
    names per recipient — mirrors ROM's `act()` macro which evaluates
    `PERS(ch, looker)` and `PERS(victim, looker)` independently for
    each observer (DAMMSG-001/002/003).

    ROM colour codes `{3...{x` / `{2...{x` / `{4...{x` are escaped as
    `{{3}}` etc. in the template literals so `str.format()` leaves
    them intact for the ANSI translation layer.
    """

    attacker: str | None
    victim: str | None
    room: str | None
    self_inflicted: bool = False


def render_for(
    template: str | None,
    attacker: object,
    victim: object,
    observer: object | None,
) -> str | None:
    """Substitute `{attacker}` / `{victim}` placeholders through PERS.

    Mirrors ROM's `act()` macro — `$n` resolves through `PERS(ch,
    looker)` and `$N` through `PERS(victim, looker)`. The observer
    is the recipient of the message; for TO_NOTVICT this is iterated
    per room occupant, for TO_CHAR this is the attacker, for TO_VICT
    this is the victim.
    """
    if template is None:
        return None
    return template.format(
        attacker=pers(attacker, observer),
        victim=pers(victim, observer),
    )


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
    # ROM src/fight.c:dam_message divides damage*100/victim->max_hit raw (SIGFPE if 0).
    # Python floor kept as deliberate divergence — see docs/divergences/UB_DIVISORS.md
    # (NPC victim with degenerate hit_dice can spawn with max_hit == 0).
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

    attack = _resolve_attack_noun(dt)
    self_inflicted = attacker is victim

    if attack is None and immune:
        attack = "attack"

    # Templates use `{{attacker}}` / `{{victim}}` placeholders that
    # `render_for()` substitutes per-recipient through ROM PERS().
    # ROM colour codes (`{3...{x` etc.) are doubled so str.format()
    # leaves them intact (DAMMSG-001/002/003).
    if int(percent) <= 0 and not immune:
        # Mirror ROM miss output
        if self_inflicted:
            room_msg = "{{3{attacker} " + vp + " " + _reflexive_pronoun(attacker) + punct + "{{x"
            attacker_msg = "{{2You " + vs + " yourself" + punct + "{{x"
            return DamageMessages(attacker_msg, None, room_msg, True)
        room_msg = "{{3{attacker} " + vp + " {victim}" + punct + "{{x"
        attacker_msg = "{{2You " + vs + " {victim}" + punct + "{{x"
        victim_msg = "{{4{attacker} " + vp + " you" + punct + "{{x"
        return DamageMessages(attacker_msg, victim_msg, room_msg, False)

    if immune:
        if self_inflicted:
            poss = _possessive_pronoun(attacker)
            room_msg = "{{3{attacker} is unaffected by " + poss + " own " + attack + ".{{x"
            attacker_msg = "{{2Luckily, you are immune to that.{{x"
            return DamageMessages(attacker_msg, None, room_msg, True)
        room_msg = "{{3{victim} is unaffected by {attacker}'s " + attack + "!{{x"
        attacker_msg = "{{2{victim} is unaffected by your " + attack + "!{{x"
        victim_msg = "{{4{attacker}'s " + attack + " is powerless against you.{{x"
        return DamageMessages(attacker_msg, victim_msg, room_msg, False)

    if attack is None:
        if self_inflicted:
            room_msg = "{{3{attacker} " + vp + " " + _reflexive_pronoun(attacker) + punct + "{{x"
            attacker_msg = "{{2You " + vs + " yourself" + punct + "{{x"
            return DamageMessages(attacker_msg, None, room_msg, True)
        room_msg = "{{3{attacker} " + vp + " {victim}" + punct + "{{x"
        attacker_msg = "{{2You " + vs + " {victim}" + punct + "{{x"
        victim_msg = "{{4{attacker} " + vp + " you" + punct + "{{x"
        return DamageMessages(attacker_msg, victim_msg, room_msg, False)

    if self_inflicted:
        poss = _possessive_pronoun(attacker)
        room_msg = "{{3{attacker}'s " + attack + " " + vp + " " + _reflexive_pronoun(attacker) + punct + "{{x"
        attacker_msg = "{{2Your " + attack + " " + vp + " you" + punct + "{{x"
        return DamageMessages(attacker_msg, None, room_msg, True)

    room_msg = "{{3{attacker}'s " + attack + " " + vp + " {victim}" + punct + "{{x"
    attacker_msg = "{{2Your " + attack + " " + vp + " {victim}" + punct + "{{x"
    victim_msg = "{{4{attacker}'s " + attack + " " + vp + " you" + punct + "{{x"
    return DamageMessages(attacker_msg, victim_msg, room_msg, False)


__all__: tuple[str, ...] = (
    "DamageMessages",
    "TYPE_HIT",
    "MAX_DAMAGE_MESSAGE",
    "dam_message",
    "render_for",
)
