from __future__ import annotations

from mud.models.character import Character


def _find_healer(char: Character) -> object | None:
    """Find a healer NPC in the room.

    Heuristic: a mob whose prototype has spec_fun == 'spec_healer',
    or any room occupant with an attribute `is_healer` truthy.
    """
    for mob in getattr(char.room, "people", []):
        if getattr(mob, "is_healer", False):
            return mob
        proto = getattr(mob, "prototype", None)
        if proto:
            spec = getattr(proto, "spec_fun", "") or ""
            if spec.lower() == "spec_healer":
                return mob
    return None


PRICE_GOLD = {
    "light": 10,  # ROM healer.c:88: cost = 1000 (10 gold)
    "serious": 16,  # ROM healer.c:96: cost = 1600 (16 gold) - NOTE: Display says 15g but actual cost is 16g!
    "critical": 25,  # ROM healer.c:104: cost = 2500 (25 gold)
    "heal": 50,  # ROM healer.c:112: cost = 5000 (50 gold)
    "blindness": 20,  # ROM healer.c:120: cost = 2000 (20 gold)
    "disease": 15,  # ROM healer.c:128: cost = 1500 (15 gold)
    "poison": 25,  # ROM healer.c:136: cost = 2500 (25 gold)
    "uncurse": 50,  # ROM healer.c:144: cost = 5000 (50 gold)
    "refresh": 5,  # ROM healer.c:161: cost = 500 (5 gold)
    "mana": 10,  # ROM healer.c:152: cost = 1000 (10 gold)
}


def do_heal(char: Character, args: str = "") -> str:
    healer = _find_healer(char)
    if not healer:
        return "You can't do that here."

    arg = (args or "").strip().lower()
    if not arg:
        # Minimal price list in ROM spirit
        items = "; ".join(f"{k} {v} gold" for k, v in PRICE_GOLD.items())
        return f"Healer offers: {items}"

    # Normalize common aliases
    if arg.startswith("critic"):
        arg = "critical"
    if arg.startswith("uncurse") or arg == "curse":
        arg = "uncurse"

    if arg not in PRICE_GOLD:
        return "Type heal for a list of spells."

    cost = PRICE_GOLD[arg]
    if char.gold < cost:
        return "You do not have enough gold for my services."

    char.gold -= cost

    # Apply simple effects sufficient for parity tests
    if arg == "refresh":
        char.move = min(char.max_move, max(char.move, char.max_move))
        return "You feel refreshed."
    if arg == "heal":
        char.hit = min(char.max_hit, max(char.hit, char.max_hit))
        return "Your wounds mend."
    if arg == "mana":
        char.mana = min(char.max_mana, char.mana + 10)
        return "A warm glow passes through you."
    if arg in ("light", "serious", "critical"):
        inc = {"light": 10, "serious": 20, "critical": 30}[arg]
        char.hit = min(char.max_hit, char.hit + inc)
        return "You feel better."
    # For status cures, just acknowledge.
    return "You feel cleansed."
