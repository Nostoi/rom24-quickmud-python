from __future__ import annotations

import json
from pathlib import Path

"""Convert ROM social.are to JSON matching schemas/social.schema.json.

Rules:
- Each social consists of a name line (optionally followed by two ints)
  and up to 8 message lines in the order documented in doc/command.txt.
- A line consisting of a single "$" denotes an empty string for that field.
- A line consisting of a single "#" terminates the current social early;
  remaining fields default to empty strings.
"""

FIELDS = [
    "char_no_arg",
    "others_no_arg",
    "char_found",
    "others_found",
    "vict_found",
    "not_found",
    "char_auto",
    "others_auto",
]


def parse_socials(text: str) -> list[dict[str, str]]:
    lines = [ln.rstrip("\n") for ln in text.splitlines()]
    out: list[dict[str, str]] = []
    i = 0
    # skip header
    while i < len(lines) and not lines[i].startswith("#SOCIALS"):
        i += 1
    if i < len(lines) and lines[i].startswith("#SOCIALS"):
        i += 1
    # parse entries
    while i < len(lines):
        # skip blank lines
        while i < len(lines) and lines[i].strip() == "":
            i += 1
        if i >= len(lines):
            break
        # name line or terminator
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue
        # name may be followed by integers; take first token as name
        name = line.split()[0]
        i += 1
        entry: dict[str, str] = {"name": name}
        # read up to 8 fields
        remaining = len(FIELDS)
        for field in FIELDS:
            if i >= len(lines):
                entry[field] = ""
                continue
            val = lines[i]
            i += 1
            if val == "#":
                # early terminator: fill the rest with empty
                entry[field] = ""
                for rest in FIELDS[FIELDS.index(field) + 1 :]:
                    entry[rest] = ""
                break
            if val == "$":
                entry[field] = ""
            else:
                entry[field] = val
            remaining -= 1
        out.append(entry)
    return out


def convert(in_path: str | Path, out_path: str | Path) -> None:
    text = Path(in_path).read_text(encoding="utf-8")
    data = parse_socials(text)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser(description="Convert ROM social.are to JSON")
    ap.add_argument("infile", help="Path to area/social.are")
    ap.add_argument("outfile", help="Output JSON path")
    args = ap.parse_args()
    convert(args.infile, args.outfile)
