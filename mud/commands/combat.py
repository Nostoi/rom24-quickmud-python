from mud import mobprog
from mud.combat import attack_round, multi_hit
from mud.combat.engine import stop_fighting
from mud.models.character import Character


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


def do_surrender(char: Character, args: str) -> str:
    opponent = getattr(char, "fighting", None)
    if opponent is None:
        return "But you're not fighting!"

    stop_fighting(char, True)
    if getattr(opponent, "fighting", None) is char:
        opponent.fighting = None

    if not getattr(char, "is_npc", False) and getattr(opponent, "is_npc", False):
        if not mobprog.mp_surr_trigger(opponent, char):
            multi_hit(opponent, char)

    return "You surrender."
