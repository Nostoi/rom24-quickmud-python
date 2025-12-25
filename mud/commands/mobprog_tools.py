"""Immortal utilities for inspecting mob programs."""

from __future__ import annotations

from typing import Iterable

from mud.models.character import Character, character_registry
from mud.models.mob import MobIndex, MobProgram
from mud.mobprog import format_trigger_flag

ROM_NEWLINE = "\n\r"


def _match_name(entity: object, token: str) -> bool:
    if not token:
        return False
    name = getattr(entity, "name", None)
    if isinstance(name, str) and name.strip():
        return name.lower().startswith(token.lower())
    prototype = getattr(entity, "prototype", None)
    if prototype is None:
        return False
    for attr in ("player_name", "short_descr"):
        value = getattr(prototype, attr, None)
        if isinstance(value, str) and value.strip():
            return value.lower().startswith(token.lower())
    return False


def _find_character(token: str) -> Character | None:
    if not token:
        return None
    lowered = token.lower()
    for candidate in list(character_registry):
        if _match_name(candidate, lowered):
            return candidate
    return None


def _resolve_programs(victim: Character) -> list[MobProgram]:
    programs: list[MobProgram] = []
    proto = getattr(victim, "prototype", None)
    if proto is not None:
        programs.extend(list(getattr(proto, "mprogs", []) or []))
    programs.extend(list(getattr(victim, "mob_programs", []) or []))
    seen: set[int] = set()
    unique: list[MobProgram] = []
    for program in programs:
        if program is None:
            continue
        ident = id(program)
        if ident in seen:
            continue
        seen.add(ident)
        unique.append(program)
    return unique


def _format_target_name(target: object | None) -> str:
    if target is None:
        return "No target"
    name = getattr(target, "name", None)
    if isinstance(name, str) and name.strip():
        return name
    return "No target"


def _format_mobile_header(victim: Character, proto: MobIndex | None) -> str:
    vnum = getattr(proto, "vnum", getattr(victim, "vnum", 0)) or 0
    short_descr = None
    for attr in ("short_descr", "player_name", "name"):
        value = getattr(proto, attr, None) if proto is not None else getattr(victim, attr, None)
        if isinstance(value, str) and value.strip():
            short_descr = value.strip()
            break
    if not short_descr:
        short_descr = "(no short description)"
    return f"Mobile #{vnum:<6d} [{short_descr}]"


def _format_delay_line(victim: Character) -> str:
    try:
        delay = int(getattr(victim, "mprog_delay", 0) or 0)
    except (TypeError, ValueError):
        delay = 0
    target = getattr(victim, "mprog_target", None)
    return f"Delay   {delay:<6d} [{_format_target_name(target)}]"


def _format_programs(programs: Iterable[MobProgram]) -> list[str]:
    lines: list[str] = []
    for index, program in enumerate(programs, start=1):
        trig = format_trigger_flag(getattr(program, "trig_type", 0)) or ""
        phrase = getattr(program, "trig_phrase", "") or ""
        vnum = getattr(program, "vnum", 0) or 0
        lines.append(f"[{index:2d}] Trigger [{trig:<8}] Program [{vnum:4d}] Phrase [{phrase}]")
    return lines


def do_mpstat(char: Character, args: str) -> str:
    """Inspect a mobile's registered mob programs (ROM ``mpstat``)."""

    target_name = (args or "").strip()
    if not target_name:
        return "Mpstat whom?" + ROM_NEWLINE

    victim = _find_character(target_name)
    if victim is None:
        return "No such creature." + ROM_NEWLINE

    if not getattr(victim, "is_npc", False):
        return "That is not a mobile." + ROM_NEWLINE

    proto = getattr(victim, "prototype", None)
    header = _format_mobile_header(victim, proto)
    delay_line = _format_delay_line(victim)

    programs = _resolve_programs(victim)
    if not programs:
        return ROM_NEWLINE.join([header, delay_line, "[No programs set]"]) + ROM_NEWLINE

    body = _format_programs(programs)
    return ROM_NEWLINE.join([header, delay_line, *body]) + ROM_NEWLINE


def do_mpdump(char: Character, args: str) -> str:
    """Display mob program code by vnum (ROM ``mpdump``).

    Mirrors ROM src/mob_cmds.c:do_mpdump - displays the actual program code
    for debugging and inspection purposes.

    Usage: mpdump <vnum>
    """
    vnum_str = (args or "").strip()
    if not vnum_str:
        return "Syntax: mpdump <program vnum>" + ROM_NEWLINE

    try:
        vnum = int(vnum_str)
    except ValueError:
        return "Invalid vnum - must be a number." + ROM_NEWLINE

    # Search all loaded mobs for a program with this vnum
    found_program: MobProgram | None = None
    for character in list(character_registry):
        if not getattr(character, "is_npc", False):
            continue
        programs = _resolve_programs(character)
        for program in programs:
            if getattr(program, "vnum", 0) == vnum:
                found_program = program
                break
        if found_program:
            break

    if found_program is None:
        return "No such MOBprogram." + ROM_NEWLINE

    code = getattr(found_program, "code", None) or ""
    if not code.strip():
        return f"Program {vnum} has no code." + ROM_NEWLINE

    # Return the code with proper line endings
    return code.rstrip() + ROM_NEWLINE
