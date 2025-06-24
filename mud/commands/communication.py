from mud.models.character import Character


def do_say(char: Character, args: str) -> str:
    if not args:
        return "Say what?"
    message = f"{char.name} says, '{args}'"
    if char.room:
        char.room.broadcast(message, exclude=char)
    return f"You say, '{args}'"
