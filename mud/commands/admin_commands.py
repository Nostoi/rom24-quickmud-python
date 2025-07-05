from mud.models.character import Character
from mud.registry import room_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.net.session import SESSIONS
from mud.commands.decorators import admin_only


@admin_only
def cmd_who(char: Character, args: str) -> str:
    lines = ["Online Players:"]
    for sess in SESSIONS.values():
        c = sess.character
        room_vnum = c.room.vnum if getattr(c, "room", None) else "?"
        lines.append(f" - {c.name} in room {room_vnum}")
    return "\n".join(lines)


@admin_only
def cmd_teleport(char: Character, args: str) -> str:
    if not args.isdigit() or int(args) not in room_registry:
        return "Invalid room."
    target = room_registry[int(args)]
    if char.room:
        char.room.remove_character(char)
    target.add_character(char)
    return f"Teleported to room {args}"


@admin_only
def cmd_spawn(char: Character, args: str) -> str:
    if not args.isdigit():
        return "Invalid vnum."
    mob = spawn_mob(int(args))
    if not mob:
        return "NPC not found."
    if not char.room:
        return "Nowhere to spawn."
    char.room.add_mob(mob)
    return f"Spawned {mob.name}."
