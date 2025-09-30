from __future__ import annotations

from collections.abc import Iterator

from mud.models.room_json import ResetJson
from mud.registry import mob_registry, obj_registry, room_registry

from .base_loader import BaseTokenizer


def _iter_reset_numbers(tokens: list[str]) -> Iterator[int]:
    """Yield integer tokens until a comment marker is reached."""

    for token in tokens:
        if token.startswith("*"):
            break
        try:
            yield int(token)
        except ValueError:
            continue


def load_resets(tokenizer: BaseTokenizer, area):
    """Parse reset lines using ROM load_resets semantics."""

    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        if line == "S":
            break
        if line == "$" or line.startswith("#"):
            # allow outer loader to handle following sections
            tokenizer.index -= 1
            break
        parts = line.split()
        if not parts:
            continue
        command = parts[0][0].upper()
        if command == "S":
            break

        numbers = list(_iter_reset_numbers(parts[1:]))
        if not numbers:
            area.resets.append(ResetJson(command=command))
            continue

        number_iter = iter(numbers)
        next(number_iter, None)  # Skip if_flag
        arg1 = next(number_iter, 0)
        arg2 = next(number_iter, 0)
        if command in {"G", "R"}:
            arg3 = 0
        else:
            arg3 = next(number_iter, 0)
        arg4 = next(number_iter, 0) if command in {"P", "M"} else 0

        reset = ResetJson(command=command, arg1=arg1, arg2=arg2, arg3=arg3, arg4=arg4)
        area.resets.append(reset)


def _validate_exit(reset: ResetJson) -> str | None:
    room_vnum = int(reset.arg1 or 0)
    direction = int(reset.arg2 or 0)
    room = room_registry.get(room_vnum)
    if room is None:
        return f"Reset D references missing room {room_vnum}"
    exits = getattr(room, "exits", []) or []
    if direction < 0 or direction >= len(exits):
        return f"Reset D has invalid direction {direction} for room {room_vnum}"
    exit_obj = exits[direction]
    if exit_obj is None:
        return f"Reset D points to missing exit at room {room_vnum} dir {direction}"
    return None


def validate_resets(area) -> list[str]:
    """Validate ROM reset sequencing using LastMob/LastObj tracking."""

    errors: list[str] = []

    min_vnum = int(getattr(area, "min_vnum", 0) or 0)
    max_vnum = int(getattr(area, "max_vnum", 0) or 0)

    def _is_local(vnum: int) -> bool:
        if min_vnum == 0 and max_vnum == 0:
            return True
        return min_vnum <= vnum <= max_vnum

    last_room_vnum: int | None = None
    last_mob_vnum: int | None = None
    last_obj_vnum: int | None = None

    for reset in area.resets:
        command = (reset.command or "").upper()
        if command == "M":
            room_vnum = int(reset.arg3 or 0)
            mob_vnum = int(reset.arg1 or 0)
            if mob_vnum not in mob_registry and _is_local(mob_vnum):
                errors.append(f"Reset M references missing mob {mob_vnum}")
            if room_vnum not in room_registry and _is_local(room_vnum):
                errors.append(f"Reset M references missing room {room_vnum}")
            last_room_vnum = room_vnum if room_vnum in room_registry else None
            last_mob_vnum = mob_vnum if mob_vnum in mob_registry else None
            last_obj_vnum = None
        elif command == "O":
            obj_vnum = int(reset.arg1 or 0)
            room_vnum = int(reset.arg3 or 0)
            if obj_vnum not in obj_registry and _is_local(obj_vnum):
                errors.append(f"Reset O references missing object {obj_vnum}")
            if room_vnum not in room_registry and _is_local(room_vnum):
                errors.append(f"Reset O references missing room {room_vnum}")
            last_room_vnum = room_vnum if room_vnum in room_registry else last_room_vnum
            last_obj_vnum = obj_vnum if obj_vnum in obj_registry else last_obj_vnum
        elif command == "P":
            obj_vnum = int(reset.arg1 or 0)
            container_vnum = int(reset.arg3 or 0)
            if obj_vnum not in obj_registry and _is_local(obj_vnum):
                errors.append(f"Reset P references missing object {obj_vnum}")
            target_vnum: int | None
            if container_vnum:
                target_vnum = container_vnum
            else:
                target_vnum = last_obj_vnum
            if not target_vnum or (
                target_vnum not in obj_registry and _is_local(int(target_vnum))
            ):
                errors.append(
                    f"Reset P has no container context for object {obj_vnum}"
                )
            last_obj_vnum = obj_vnum if obj_vnum in obj_registry else last_obj_vnum
        elif command in {"G", "E"}:
            obj_vnum = int(reset.arg1 or 0)
            if obj_vnum not in obj_registry and _is_local(obj_vnum):
                errors.append(f"Reset {command} references missing object {obj_vnum}")
            if last_mob_vnum is None or last_mob_vnum not in mob_registry:
                errors.append(
                    f"Reset {command} lacks LastMob context before object {obj_vnum}"
                )
            last_obj_vnum = obj_vnum if obj_vnum in obj_registry else last_obj_vnum
        elif command == "D":
            error = _validate_exit(reset)
            if error:
                errors.append(error)
            last_room_vnum = int(reset.arg1 or 0) if int(reset.arg1 or 0) in room_registry else last_room_vnum
            last_obj_vnum = None
        elif command == "R":
            room_vnum = int(reset.arg1 or 0)
            if room_vnum not in room_registry and _is_local(room_vnum):
                errors.append(f"Reset R references missing room {room_vnum}")
            last_room_vnum = room_vnum if room_vnum in room_registry else last_room_vnum
            last_obj_vnum = None
        else:
            # Unknown reset command: record but continue.
            errors.append(f"Reset {command} is not recognised for validation")

    return errors
