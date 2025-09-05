from mud.models.character import Character


def cmd_redit(char: Character, args: str) -> str:
    """Edit the current room's fields."""
    if not char.room:
        return "You are nowhere."
    parts = args.split(maxsplit=1)
    if len(parts) != 2:
        return "Usage: @redit name|desc <value>"
    field, value = parts
    if field == "name":
        char.room.name = value
        return f"Room name set to {value}"
    if field in {"desc", "description"}:
        char.room.description = value
        return "Room description updated."
    return "Invalid field."
