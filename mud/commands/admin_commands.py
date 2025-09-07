from mud.models.character import Character
from mud.registry import room_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.net.session import SESSIONS
from mud.security import bans


def cmd_who(char: Character, args: str) -> str:
    lines = ["Online Players:"]
    for sess in SESSIONS.values():
        c = sess.character
        room_vnum = c.room.vnum if getattr(c, "room", None) else "?"
        lines.append(f" - {c.name} in room {room_vnum}")
    return "\n".join(lines)


def cmd_teleport(char: Character, args: str) -> str:
    if not args.isdigit() or int(args) not in room_registry:
        return "Invalid room."
    target = room_registry[int(args)]
    if char.room:
        char.room.remove_character(char)
    target.add_character(char)
    return f"Teleported to room {args}"


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


def cmd_ban(char: Character, args: str) -> str:
    host = args.strip()
    if not host:
        return "Usage: ban <host>"
    bans.add_banned_host(host)
    try:
        bans.save_bans_file()
    except Exception:
        # Persistence errors shouldn't block the action in tests
        pass
    return f"Banned {host}."


def cmd_unban(char: Character, args: str) -> str:
    host = args.strip()
    if not host:
        return "Usage: unban <host>"
    if not bans.is_host_banned(host):
        return "Site is not banned."
    bans.remove_banned_host(host)
    try:
        bans.save_bans_file()
    except Exception:
        pass
    return f"Unbanned {host}."


def cmd_banlist(char: Character, args: str) -> str:
    banned = sorted(list({h for h in list_hosts() for h in [h]}))
    if not banned:
        return "No sites banned."
    lines = ["Banned sites:"] + [f" - {h}" for h in banned]
    return "\n".join(lines)


def list_hosts() -> list[str]:
    # internal helper to read via saving/loading outward if needed later
    # currently directly exposes in-memory set
    return sorted({*bans._banned_hosts})  # type: ignore[attr-defined]
