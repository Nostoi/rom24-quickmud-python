from mud.logging.admin import toggle_log_all
from mud.models.character import Character, character_registry
from mud.net.session import SESSIONS
from mud.registry import room_registry
from mud.security import bans
from mud.security.bans import BanFlag, BanPermissionError
from mud.spawning.mob_spawner import spawn_mob


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


def _get_trust(char: Character) -> int:
    trust = int(getattr(char, "trust", 0) or 0)
    level = int(getattr(char, "level", 0) or 0)
    return trust if trust > 0 else level


def _render_ban_listing() -> str:
    entries = bans.get_ban_entries()
    if not entries:
        return "No sites banned at this time."
    lines = ["Banned sites  level  type     status"]
    for entry in entries:
        pattern = entry.to_pattern()
        if entry.flags & BanFlag.NEWBIES:
            type_text = "newbies"
        elif entry.flags & BanFlag.PERMIT:
            type_text = "permit"
        else:
            type_text = "all"
        status = "perm" if entry.flags & BanFlag.PERMANENT else "temp"
        lines.append(f"{pattern:<12}    {entry.level:3d}  {type_text:<7}  {status}")
    return "\n".join(lines)


def _apply_ban(char: Character, args: str, *, permanent: bool) -> str:
    stripped = args.strip()
    if not stripped:
        return _render_ban_listing()

    parts = stripped.split()
    host_token = parts[0]
    type_token = parts[1].lower() if len(parts) > 1 else "all"

    if type_token.startswith("all"):
        ban_type = BanFlag.ALL
    elif type_token.startswith("newbies"):
        ban_type = BanFlag.NEWBIES
    elif type_token.startswith("permit"):
        ban_type = BanFlag.PERMIT
    else:
        return "Acceptable ban types are all, newbies, and permit."

    host = host_token.strip()
    prefix = host.startswith("*")
    suffix = host.endswith("*")
    core = host[1:] if prefix else host
    if suffix and core:
        core = core[:-1]
    core = core.strip()
    if not core:
        return "You have to ban SOMETHING."

    trust = _get_trust(char)
    try:
        bans.add_banned_host(
            host,
            flags=ban_type,
            level=trust,
            permanent=permanent,
            trust_level=trust,
        )
    except BanPermissionError:
        return "That ban was set by a higher power."

    try:
        bans.save_bans_file()
    except Exception:
        pass
    return f"{core} has been banned."


def cmd_ban(char: Character, args: str) -> str:
    return _apply_ban(char, args, permanent=False)


def cmd_permban(char: Character, args: str) -> str:
    return _apply_ban(char, args, permanent=True)


def cmd_allow(char: Character, args: str) -> str:
    target = args.strip().lower()
    if not target:
        return "Remove which site from the ban list?"

    trust = _get_trust(char)
    try:
        removed = bans.remove_banned_host(target, trust_level=trust)
    except BanPermissionError:
        return "You are not powerful enough to lift that ban."

    if not removed:
        return "Site is not banned."

    try:
        bans.save_bans_file()
    except Exception:
        pass
    return f"Ban on {target} lifted."


def cmd_unban(char: Character, args: str) -> str:
    # Maintain legacy alias while ROM exposes `allow`.
    return cmd_allow(char, args)


def cmd_banlist(char: Character, args: str) -> str:
    return _render_ban_listing()


def cmd_log(char: Character, args: str) -> str:
    arg = args.strip()
    if not arg:
        return "Log whom?"
    target_name, *_rest = arg.split(maxsplit=1)
    if target_name.lower() == "all":
        enabled = toggle_log_all()
        return "Log ALL on." if enabled else "Log ALL off."
    lowered = target_name.lower()
    target = next(
        (
            candidate
            for candidate in character_registry
            if candidate.name and candidate.name.lower().startswith(lowered)
        ),
        None,
    )
    if target is None:
        return "They aren't here."
    if getattr(target, "is_npc", False):
        return "Not on NPC's."
    target.log_commands = not getattr(target, "log_commands", False)
    return "LOG set." if target.log_commands else "LOG removed."


def list_hosts() -> list[str]:
    """Deprecated helper kept for backward compatibility in tests."""
    return sorted(entry.to_pattern() for entry in bans.get_ban_entries())
