from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_help_are(path: Path) -> list[dict]:
    """Parse a ROM #HELPS section from an .are file into JSON entries.

    Preserves help text exactly (including spacing and newlines).
    Each entry is a dict with: level:int, keywords:list[str], text:str.
    """
    entries: list[dict] = []
    in_helps = False
    level: int | None = None
    keywords: list[str] | None = None
    buf: list[str] = []

    def flush_current() -> None:
        nonlocal level, keywords, buf
        if level is None or keywords is None:
            return
        text = "\n".join(buf)
        entries.append({
            "level": level,
            "keywords": keywords,
            "text": text,
        })
        level, keywords, buf = None, None, []

    with path.open("r", encoding="utf-8", errors="ignore") as fp:
        for raw in fp:
            line = raw.rstrip("\n")
            if not in_helps:
                if line.strip() == "#HELPS":
                    in_helps = True
                continue

            # End of helps section sentinel: `0 $~`
            if line.strip() == "0 $~":
                flush_current()
                break

            # New entry header: "<level> <keywords>~"
            if level is None and line.strip():
                # Some areas may have spacing/tabs before values; split once.
                try:
                    lvl_part, rest = line.strip().split(" ", 1)
                except ValueError:
                    # Malformed header; skip gracefully
                    continue
                # Header may end with trailing '~'
                rest = rest.rstrip()
                if rest.endswith("~"):
                    rest = rest[:-1]
                try:
                    level = int(lvl_part)
                except ValueError:
                    # Not a numeric level; skip
                    level = None
                    continue
                # Keywords are space-separated tokens
                keywords = [tok for tok in rest.split() if tok]
                buf = []
                continue

            # Inside help text body; a line with only '~' terminates the entry
            if level is not None:
                if line.strip() == "~":
                    flush_current()
                else:
                    buf.append(line)

    return entries


def main() -> None:
    ap = argparse.ArgumentParser(description="Convert ROM help.are #HELPS to JSON")
    ap.add_argument("infile", type=Path, help="Path to area/help.are")
    ap.add_argument("outfile", type=Path, help="Output JSON path")
    args = ap.parse_args()

    entries = parse_help_are(args.infile)
    args.outfile.parent.mkdir(parents=True, exist_ok=True)
    with args.outfile.open("w", encoding="utf-8") as fp:
        json.dump(entries, fp, ensure_ascii=False, indent=2)


if __name__ == "__main__":  # pragma: no cover
    main()

