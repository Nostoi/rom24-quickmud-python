from mud.models.character import Character
from mud.combat import attack_round


def do_kill(char: Character, args: str) -> str:
    if not args:
        return "Kill whom?"
    target_name = args.lower()
    if not getattr(char, "room", None):
        return "You are nowhere."
    for victim in list(char.room.people):
        if victim is char:
            continue
        if victim.name and target_name in victim.name.lower():
            return attack_round(char, victim)
    return "They aren't here."
