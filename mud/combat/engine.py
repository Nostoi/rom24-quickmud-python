from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position
from mud.utils import rng_mm


def attack_round(attacker: Character, victim: Character) -> str:
    """Resolve a single attack round.

    The attacker attempts to hit the victim.  Hit chance is derived from a
    base 50% modified by the attacker's ``hitroll``.  Successful hits apply
    ``damroll`` damage.  Living combatants are placed into FIGHTING position.
    If the victim dies, they are removed from the room and their position set
    to ``DEAD``.
    """

    attacker.position = Position.FIGHTING
    victim.position = Position.FIGHTING

    to_hit = 50 + attacker.hitroll
    # Use ROM-compatible RNG percent roll.
    if rng_mm.number_percent() > to_hit:
        return f"You miss {victim.name}."

    damage = max(1, attacker.damroll)
    victim.hit -= damage
    if victim.hit <= 0:
        victim.hit = 0
        victim.position = Position.DEAD
        attacker.position = Position.STANDING
        if getattr(victim, "room", None):
            victim.room.broadcast(f"{victim.name} is DEAD!!!", exclude=victim)
            victim.room.remove_character(victim)
        return f"You kill {victim.name}."
    return f"You hit {victim.name} for {damage} damage."
