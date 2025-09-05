from mud.models.character import Character
from mud.skills.registry import skill_registry


def do_practice(char: Character, args: str) -> str:
    if not args:
        return f"You have {char.practice} practice sessions left."
    if char.practice <= 0:
        return "You have no practice sessions left."
    skill_name = args.lower()
    if skill_name not in skill_registry.skills:
        return "You can't practice that."
    current = char.skills.get(skill_name, 0)
    if current >= 75:
        return f"You are already learned at {skill_name}."
    char.practice -= 1
    char.skills[skill_name] = min(current + 25, 75)
    return f"You practice {skill_name}."


def do_train(char: Character, args: str) -> str:
    if not args:
        return f"You have {char.train} training sessions left."
    if char.train <= 0:
        return "You have no training sessions left."
    stat = args.lower()
    if stat not in {"hp", "mana", "move"}:
        return "Train what?"
    if stat == "hp":
        char.max_hit += 10
    elif stat == "mana":
        char.max_mana += 10
    else:
        char.max_move += 10
    char.train -= 1
    return f"You train your {stat}."
