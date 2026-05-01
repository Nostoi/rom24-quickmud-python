"""ANSI color code translation for ROM-style tokens."""

from __future__ import annotations

import re

# mirrors ROM `colour()` at src/comm.c:2391-2739. The standard 8-colour table
# (lowercase) plus bright variants (uppercase) are basic letter→\x1b[...]
# mappings; the trailing entries cover the ROM "specials" at
# src/comm.c:2714-2728: {D = dark grey, {* = bell, {/ = newline, {- = tilde,
# {{ = literal brace.
#
# Numeric codes mirror ROM per-player colour fields (src/comm.c:2487-2545).
# Defaults match _DEFAULT_PC_COLOUR_TABLE in mud/models/character.py.
ANSI_CODES: dict[str, str] = {
    # Standard letters
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
    "{D": "\x1b[1;30m",
    # ROM per-player colour fields (numeric codes)
    "{1": "\x1b[31m",       # fight_death  (NORMAL, RED)
    "{2": "\x1b[32m",       # fight_yhit   (NORMAL, GREEN)
    "{3": "\x1b[33m",       # fight_ohit   (NORMAL, YELLOW)
    "{4": "\x1b[31m",       # fight_thit   (NORMAL, RED)
    "{5": "\x1b[37m",       # fight_skill  (NORMAL, WHITE)
    "{6": "\x1b[32m",       # say          (NORMAL, GREEN)
    "{7": "\x1b[32m",       # tell         (NORMAL, GREEN)
    "{8": "\x1b[32m",       # reply        (NORMAL, GREEN)
    "{9": "\x1b[1;35m",     # gossip_text  (BRIGHT, MAGENTA)
    # Specials
    "{*": "\x07",
    "{/": "\n\r",
    "{-": "~",
    "{{": "{",
}


_TOKEN_PAIR_RE = re.compile(r"\{(.)")


def translate_ansi(text: str) -> str:
    """Replace ROM color tokens with ANSI escape sequences.

    Single-pass left-to-right so `{{` resolves before adjacent letters can
    be re-matched (e.g. `brace{{here` must produce `brace{here`, not have
    the inner `{h` consumed as a colour token).
    """

    def repl(match: re.Match[str]) -> str:
        token = match.group(0)
        code = ANSI_CODES.get(token)
        if code is not None:
            return code
        # Unknown token — ROM `colour()` returns "" for unmapped chars.
        return ""

    return _TOKEN_PAIR_RE.sub(repl, text)


def strip_ansi(text: str) -> str:
    """Remove ROM color tokens, returning plain text for non-ANSI clients.

    Mirrors ROM `send_to_char` non-colour branch (src/comm.c:1995-2007),
    which eats both characters of any `{X` pair (including unknown tokens
    and `{{`).
    """

    return _TOKEN_PAIR_RE.sub("", text)


def render_ansi(text: str, enabled: bool) -> str:
    """Render text based on whether ANSI color codes are enabled."""
    return translate_ansi(text) if enabled else strip_ansi(text)
