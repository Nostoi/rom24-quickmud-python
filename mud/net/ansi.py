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
    "{h": "\x1b[36m",
    "{H": "\x1b[1;36m",
}


def translate_ansi(text: str) -> str:
    """Replace ROM color tokens with ANSI escape sequences."""
    for token, code in ANSI_CODES.items():
        text = text.replace(token, code)
    return text


def strip_ansi(text: str) -> str:
    """Remove ROM color tokens, returning plain text for non-ANSI clients."""
    for token in ANSI_CODES.keys():
        text = text.replace(token, "")
    return text.replace("{{", "{")


def render_ansi(text: str, enabled: bool) -> str:
    """Render text based on whether ANSI color codes are enabled."""
    return translate_ansi(text) if enabled else strip_ansi(text)
