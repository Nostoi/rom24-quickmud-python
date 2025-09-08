from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Tuple

from mud.models.player_json import PlayerJson


def _letters_to_bits(spec: str) -> int:
    """Map a compact ROM letter-spec (e.g., "QT" or "NOP") to a bitmask.

    Supports 'A'..'Z' → bits 0..25. Extended pairs like 'aa' not required for
    this conversion but can be added later.
    """
    bits = 0
    for ch in spec.strip():
        if 'A' <= ch <= 'Z':
            bits |= 1 << (ord(ch) - ord('A'))
    return bits


def _parse_hmv(tokens: list[str]) -> Tuple[int, int, int, int, int, int]:
    # HMV <hit> <max_hit> <mana> <max_mana> <move> <max_move>
    vals = [int(t) for t in tokens]
    while len(vals) < 6:
        vals.append(0)
    return vals[0], vals[1], vals[2], vals[3], vals[4], vals[5]


def convert_player(path: str | Path) -> PlayerJson:
    name = ""
    level = 0
    room_vnum = None
    hit = max_hit = mana = max_mana = move = max_move = 0
    plr_flags = 0
    comm_flags = 0

    lines = Path(path).read_text(encoding="latin-1").splitlines()
    # Validate header/footer sentinels
    nonempty = [ln.strip() for ln in lines if ln.strip()]
    if not nonempty or nonempty[0] != "#PLAYER":
        raise ValueError("invalid player file: missing #PLAYER header")
    if "#END" not in nonempty:
        raise ValueError("invalid player file: missing #END footer")

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("Name "):
            name = line.split(" ", 1)[1].rstrip("~")
        elif line.startswith("Levl "):
            try:
                level = int(line.split()[1])
            except Exception as e:
                raise ValueError("invalid Levl field") from e
        elif line.startswith("Room "):
            try:
                room_vnum = int(line.split()[1])
            except Exception as e:
                raise ValueError("invalid Room field") from e
        elif line.startswith("HMV "):
            vals = line.split()[1:]
            if len(vals) != 6:
                raise ValueError("invalid HMV field: expected 6 integers")
            hit, max_hit, mana, max_mana, move, max_move = _parse_hmv(vals)
        elif line.startswith("Act "):
            spec = line.split()[1]
            if not spec.isalpha() or not spec.isupper():
                raise ValueError("invalid Act flags: expected A..Z letters")
            plr_flags = _letters_to_bits(spec)
        elif line.startswith("Comm "):
            spec = line.split()[1]
            if not spec.isalpha() or not spec.isupper():
                raise ValueError("invalid Comm flags: expected A..Z letters")
            comm_flags = _letters_to_bits(spec)

    return PlayerJson(
        name=name,
        level=level,
        hit=hit,
        max_hit=max_hit,
        mana=mana,
        max_mana=max_mana,
        move=move,
        max_move=max_move,
        gold=0,
        silver=0,
        exp=0,
        position=0,
        room_vnum=room_vnum,
        inventory=[],
        equipment={},
        plr_flags=plr_flags,
        comm_flags=comm_flags,
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
