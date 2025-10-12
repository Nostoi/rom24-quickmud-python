from __future__ import annotations

"""Text helpers that mirror ROM's string formatting utilities."""


def format_rom_string(text: str | None) -> str:
    """Apply ROM's format_string rules to builder-edited descriptions."""
    if not text:
        return ""

    raw = text
    xbuf: list[str] = []
    cap = True
    idx = 0
    length = len(raw)

    while idx < length:
        ch = raw[idx]
        next_char = raw[idx + 1] if idx + 1 < length else None

        if ch == "\r":
            idx += 1
            continue
        if ch == "\n":
            if xbuf and xbuf[-1] != " ":
                xbuf.append(" ")
            idx += 1
            continue
        if ch == " ":
            if xbuf and xbuf[-1] != " ":
                xbuf.append(" ")
            idx += 1
            continue
        if ch == ")":
            if (
                len(xbuf) >= 3
                and xbuf[-1] == " "
                and xbuf[-2] == " "
                and xbuf[-3] in ".?!"
            ):
                xbuf[-2] = ")"
                xbuf[-1] = " "
                xbuf.append(" ")
            else:
                xbuf.append(")")
            idx += 1
            continue
        if ch in ".?!":
            skip_quote = False
            if (
                len(xbuf) >= 3
                and xbuf[-1] == " "
                and xbuf[-2] == " "
                and xbuf[-3] in ".?!"
            ):
                xbuf[-2] = ch
                if next_char != '"':
                    xbuf[-1] = " "
                    xbuf.append(" ")
                else:
                    xbuf[-1] = '"'
                    xbuf.append(" ")
                    xbuf.append(" ")
                    skip_quote = True
            else:
                xbuf.append(ch)
                if next_char != '"':
                    xbuf.append(" ")
                    xbuf.append(" ")
                else:
                    xbuf.append('"')
                    xbuf.append(" ")
                    xbuf.append(" ")
                    skip_quote = True
            cap = True
            idx += 1
            if skip_quote:
                idx += 1
            continue

        xbuf.append(raw[idx].upper() if cap else raw[idx])
        cap = False
        idx += 1

    collapsed = "".join(xbuf).strip()
    if not collapsed:
        return ""

    lines: list[str] = []
    remainder = collapsed
    first_line = True
    while len(remainder) > 77:
        limit = 73 if first_line else 76
        break_at = None
        search_limit = min(limit, len(remainder) - 1)
        for pos in range(search_limit, 0, -1):
            if remainder[pos] == " ":
                break_at = pos
                break
        if break_at is not None:
            lines.append(remainder[:break_at])
            remainder = remainder[break_at + 1 :].lstrip(" ")
        else:
            lines.append(remainder[:76] + "-")
            remainder = remainder[76:]
        first_line = False

    remainder = remainder.rstrip(" \n\r")
    if remainder:
        lines.append(remainder)

    formatted = "\n".join(lines)
    if not formatted.endswith("\n"):
        formatted += "\n"
    return formatted
