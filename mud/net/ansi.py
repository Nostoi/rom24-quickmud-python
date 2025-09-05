"""ANSI color code translation for ROM-style tokens."""
from __future__ import annotations

ANSI_CODES: dict[str, str] = {
    "{x": "\x1b[0m",
    "{r": "\x1b[31m",
    "{g": "\x1b[32m",
    "{y": "\x1b[33m",
    "{b": "\x1b[34m",
    "{m": "\x1b[35m",
    "{c": "\x1b[36m",
    "{w": "\x1b[37m",
    "{R": "\x1b[1;31m",
    "{G": "\x1b[1;32m",
    "{Y": "\x1b[1;33m",
    "{B": "\x1b[1;34m",
    "{M": "\x1b[1;35m",
    "{C": "\x1b[1;36m",
    "{W": "\x1b[1;37m",
}


def translate_ansi(text: str) -> str:
    """Replace ROM color tokens with ANSI escape sequences."""
    for token, code in ANSI_CODES.items():
        text = text.replace(token, code)
    return text
