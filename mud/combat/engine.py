from __future__ import annotations

from mud.models.character import Character


def attack_round(attacker: Character, victim: Character) -> str:
    """Resolve a single attack round.

    Damage is computed from the attacker's `damroll` and applied to the
    victim's hit points.  If the victim dies, remove them from the room.
    """
    damage = max(1, attacker.damroll)
    victim.hit -= damage
    if victim.hit <= 0:
        victim.hit = 0
        if getattr(victim, "room", None):
            victim.room.broadcast(f"{victim.name} is DEAD!!!", exclude=victim)
            victim.room.remove_character(victim)
        return f"You kill {victim.name}."
    return f"You hit {victim.name} for {damage} damage."
