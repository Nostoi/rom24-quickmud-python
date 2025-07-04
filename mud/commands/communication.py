from mud.models.character import Character
from mud.net.protocol import broadcast_room


def do_say(char: Character, args: str) -> str:
    if not args:
        return "Say what?"
    message = f"{char.name} says, '{args}'"
    if char.room:
        char.room.broadcast(message, exclude=char)
        broadcast_room(char.room, message, exclude=char)
    return f"You say, '{args}'"
