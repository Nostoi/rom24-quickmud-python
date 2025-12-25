from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from mud.models.player_json import PlayerJson

ROM_RACE_TO_ID = {
    "human": 0,
    "elf": 1,
    "dwarf": 2,
    "giant": 3,
}


def _letters_to_bits(spec: str) -> int:
    """Map ROM `print_flags` output (A..Z, a..f, or ``0``) to an int bitmask."""

    cleaned = spec.strip()
    if cleaned == "0":
        return 0

    bits = 0
    for ch in cleaned:
        if "A" <= ch <= "Z":
            bits |= 1 << (ord(ch) - ord("A"))
        elif "a" <= ch <= "z":
            bits |= 1 << (26 + ord(ch) - ord("a"))
        else:
            raise ValueError(f"invalid flag specifier: {ch!r}")
    return bits


def _parse_hmv(tokens: list[str]) -> tuple[int, int, int, int, int, int]:
    # HMV <hit> <max_hit> <mana> <max_mana> <move> <max_move>
    vals = [int(t) for t in tokens]
    while len(vals) < 6:
        vals.append(0)
    return vals[0], vals[1], vals[2], vals[3], vals[4], vals[5]


def convert_player(path: str | Path) -> PlayerJson:
    name = ""
    level = 0
    race = 0
    ch_class = 0
    sex = 0
    trust = 0
    security = 0
    room_vnum = None
    hit = max_hit = mana = max_mana = move = max_move = 0
    perm_hit = perm_mana = perm_move = 0
    practice = train = saving_throw = alignment = 0
    hitroll = damroll = wimpy = 0
    points = true_sex = last_level = 0
    gold = silver = exp = 0
    position = 0
    plr_flags = 0
    affected_by = 0
    comm_flags = 0
    wiznet_flags = 0
    conditions = [0, 48, 48, 48]
    armor = [0, 0, 0, 0]
    perm_stat = [0, 0, 0, 0, 0]
    mod_stat = [0, 0, 0, 0, 0]

    lines = Path(path).read_text(encoding="latin-1").splitlines()
    # Validate header/footer sentinels
    nonempty = [ln.strip() for ln in lines if ln.strip()]
    if not nonempty or nonempty[0] != "#PLAYER":
        raise ValueError("invalid player file: missing #PLAYER header")
    if "#END" not in nonempty:
        raise ValueError("invalid player file: missing #END footer")

    # Track whether we're in the #PLAYER section or an #O (object) section
    in_player_section = False
    in_object_section = False

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        # Track section transitions
        if line == "#PLAYER":
            in_player_section = True
            in_object_section = False
            continue
        elif line == "#O":
            in_player_section = False
            in_object_section = True
            continue
        elif line == "#END":
            in_player_section = False
            in_object_section = False
            continue
        elif line == "End":
            # End of current subsection; if we were in object section, stay out
            # until we see another #PLAYER (unlikely) or continue to #END
            if in_object_section:
                in_object_section = False
            continue

        # Skip all content in object sections - we only care about player data
        if in_object_section:
            continue

        if line.startswith("Name "):
            name = line.split(" ", 1)[1].rstrip("~")
        elif line.startswith("Levl "):
            try:
                level = int(line.split()[1])
            except Exception as e:
                raise ValueError("invalid Levl field") from e
        elif line.startswith("Race "):
            race_name = line.split(" ", 1)[1].rstrip("~").lower()
            if race_name in ROM_RACE_TO_ID:
                race = ROM_RACE_TO_ID[race_name]
            else:
                raise ValueError(f"unknown Race value: {race_name}")
        elif line.startswith("Sex "):
            sex = int(line.split()[1])
        elif line.startswith("Cla "):
            ch_class = int(line.split()[1])
        elif line.startswith("Room "):
            try:
                room_vnum = int(line.split()[1])
            except Exception as e:
                raise ValueError("invalid Room field") from e
        elif line.startswith("Tru "):
            trust = int(line.split()[1])
        elif line.startswith("Sec "):
            security = int(line.split()[1])
        elif line.startswith("HMV "):
            vals = line.split()[1:]
            if len(vals) != 6:
                raise ValueError("invalid HMV field: expected 6 integers")
            hit, max_hit, mana, max_mana, move, max_move = _parse_hmv(vals)
        elif line.startswith("Gold "):
            gold = int(line.split()[1])
        elif line.startswith("Silv "):
            silver = int(line.split()[1])
        elif line.startswith("Exp "):
            exp = int(line.split()[1])
        elif line.startswith("Act "):
            spec = line.split()[1]
            try:
                plr_flags = _letters_to_bits(spec)
            except ValueError as exc:
                raise ValueError("invalid Act flags: expected ROM print_flags letters or 0") from exc
        elif line.startswith("AfBy "):
            spec = line.split()[1]
            try:
                affected_by = _letters_to_bits(spec)
            except ValueError as exc:
                raise ValueError("invalid AfBy flags: expected ROM print_flags letters or 0") from exc
        elif line.startswith("Comm "):
            spec = line.split()[1]
            try:
                comm_flags = _letters_to_bits(spec)
            except ValueError as exc:
                raise ValueError("invalid Comm flags: expected ROM print_flags letters or 0") from exc
        elif line.startswith("Wizn "):
            spec = line.split()[1]
            try:
                wiznet_flags = _letters_to_bits(spec)
            except ValueError as exc:
                raise ValueError("invalid Wizn flags: expected ROM print_flags letters or 0") from exc
        elif line.startswith("Cnd "):
            vals = line.split()[1:]
            if len(vals) != 4:
                raise ValueError("invalid Cnd field: expected 4 integers")
            try:
                conditions = [int(v) for v in vals]
            except ValueError as exc:
                raise ValueError("invalid Cnd field: expected integer values") from exc
        elif line.startswith("Cond ") or line.startswith("Condition "):
            vals = line.split()[1:]
            if len(vals) != 3:
                raise ValueError("invalid Cond field: expected 3 integers")
            try:
                parsed = [int(v) for v in vals]
            except ValueError as exc:
                raise ValueError("invalid Cond field: expected integer values") from exc
            for idx, value in enumerate(parsed):
                conditions[idx] = value
        elif line.startswith("Pos "):
            position = int(line.split()[1])
        elif line.startswith("Prac "):
            practice = int(line.split()[1])
        elif line.startswith("Trai "):
            train = int(line.split()[1])
        elif line.startswith("Save "):
            saving_throw = int(line.split()[1])
        elif line.startswith("Alig "):
            alignment = int(line.split()[1])
        elif line.startswith("Hit "):
            hitroll = int(line.split()[1])
        elif line.startswith("Dam "):
            damroll = int(line.split()[1])
        elif line.startswith("ACs "):
            vals = [int(v) for v in line.split()[1:5]]
            if len(vals) != 4:
                raise ValueError("invalid ACs field: expected 4 integers")
            armor = vals
        elif line.startswith("Wimp "):
            wimpy = int(line.split()[1])
        elif line.startswith("Attr "):
            vals = [int(v) for v in line.split()[1:6]]
            if len(vals) != 5:
                raise ValueError("invalid Attr field: expected 5 integers")
            perm_stat = vals
        elif line.startswith("AMod "):
            vals = [int(v) for v in line.split()[1:6]]
            if len(vals) != 5:
                raise ValueError("invalid AMod field: expected 5 integers")
            mod_stat = vals
        elif line.startswith("Pnts "):
            points = int(line.split()[1])
        elif line.startswith("TSex "):
            true_sex = int(line.split()[1])
        elif line.startswith("LLev "):
            last_level = int(line.split()[1])
        elif line.startswith("HMVP "):
            vals = line.split()[1:]
            if len(vals) != 3:
                raise ValueError("invalid HMVP field: expected 3 integers")
            perm_hit, perm_mana, perm_move = (int(v) for v in vals)

    return PlayerJson(
        name=name,
        level=level,
        race=race,
        ch_class=ch_class,
        sex=sex,
        trust=trust,
        security=security,
        hit=hit,
        max_hit=max_hit,
        mana=mana,
        max_mana=max_mana,
        move=move,
        max_move=max_move,
        perm_hit=perm_hit,
        perm_mana=perm_mana,
        perm_move=perm_move,
        gold=gold,
        silver=silver,
        exp=exp,
        practice=practice,
        train=train,
        saving_throw=saving_throw,
        alignment=alignment,
        hitroll=hitroll,
        damroll=damroll,
        wimpy=wimpy,
        points=points,
        true_sex=true_sex,
        last_level=last_level,
        position=position,
        room_vnum=room_vnum,
        conditions=conditions,
        armor=armor,
        perm_stat=perm_stat,
        mod_stat=mod_stat,
        inventory=[],
        equipment={},
        plr_flags=plr_flags,
        affected_by=affected_by,
        comm_flags=comm_flags,
        wiznet=wiznet_flags,
    )


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Convert ROM player file to JSON")
    parser.add_argument("input", help="Path to legacy player file")
    args = parser.parse_args()
    pj = convert_player(args.input)
    print(json.dumps(asdict(pj), indent=2))


if __name__ == "__main__":
    main()
