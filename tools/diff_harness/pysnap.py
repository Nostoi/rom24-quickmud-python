"""Build a StepSnap from live Python engine state over a declared watch-set."""

from __future__ import annotations

from mud.math.stat_apps import get_ac, get_damroll, get_hitroll
from mud.models.constants import Position
from tools.diff_harness.schema import CharSnap, RoomSnap, StepSnap


def _obj_vnum(obj: object) -> int | None:
    proto = getattr(obj, "prototype", None)
    return getattr(proto, "vnum", None)


def _affect_names(char: object) -> list[str]:
    names: list[str] = []
    for aff in getattr(char, "affected", []) or []:
        name = getattr(aff, "spell_name", None) or getattr(aff, "name", None)
        if name:
            names.append(str(name))
    return names


def _affect_flag_names(char: object) -> list[str]:
    from mud.models.constants import AffectFlag

    bits = int(getattr(char, "affected_by", 0) or 0)
    return [f.name for f in AffectFlag if f.value and (bits & int(f.value))]


def _char_snap(key: str, char: object) -> CharSnap:
    room = getattr(char, "room", None)
    fighting = getattr(char, "fighting", None)
    pos = getattr(char, "position", None)
    pos_name = pos.name if isinstance(pos, Position) else str(Position(int(pos)).name)
    inventory = [v for v in (_obj_vnum(o) for o in getattr(char, "inventory", []) or []) if v is not None]
    equipment = {
        str(int(slot)): v
        for slot, o in (getattr(char, "equipment", {}) or {}).items()
        if o is not None and (v := _obj_vnum(o)) is not None
    }
    return CharSnap(
        key=key,
        room=getattr(room, "vnum", None),
        position=pos_name,
        hp=int(getattr(char, "hit", 0)),
        max_hp=int(getattr(char, "max_hit", 0)),
        mana=int(getattr(char, "mana", 0)),
        move=int(getattr(char, "move", 0)),
        level=int(getattr(char, "level", 0)),
        align=int(getattr(char, "alignment", 0)),
        gold=int(getattr(char, "gold", 0)),
        fighting=getattr(fighting, "name", None),
        eff_hitroll=int(get_hitroll(char)),
        eff_damroll=int(get_damroll(char)),
        eff_ac=[int(get_ac(char, i)) for i in range(4)],
        affects=_affect_names(char),
        affect_flags=_affect_flag_names(char),
        inventory=inventory,
        equipment=equipment,
    )


def _person_key(person: object) -> str:
    # Mirror the C shim's char_key (diffmain.c): the snapshot key is the first
    # whitespace-delimited word of ROM's ch->name. ROM create_mobile copies the
    # mob keyword list (MobIndex.player_name) into ch->name, so a mob keys on its
    # keyword ("healer"), not its display short_descr ("the healer"). A PC keys on
    # its own name. MobInstance.name holds the display string, so reach through to
    # the prototype's player_name for mobs.
    proto = getattr(person, "prototype", None)
    rom_name = getattr(proto, "player_name", None) or getattr(person, "name", "") or ""
    words = rom_name.split()
    return words[0] if words else ""


def _room_snap(room: object) -> RoomSnap:
    people = [_person_key(p) for p in getattr(room, "people", []) or []]
    contents = [v for v in (_obj_vnum(o) for o in getattr(room, "contents", []) or []) if v is not None]
    return RoomSnap(vnum=int(getattr(room, "vnum", -1)), people=people, contents=contents)


def snapshot_python(
    step: int,
    command: str,
    chars_by_name: dict[str, object],
    rooms_by_vnum: dict[int, object],
    output: list[str],
) -> StepSnap:
    return StepSnap(
        step=step,
        command=command,
        chars=[_char_snap(k, c) for k, c in chars_by_name.items()],
        rooms=[_room_snap(r) for r in rooms_by_vnum.values()],
        output=list(output),
    )
