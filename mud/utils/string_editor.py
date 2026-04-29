"""Port of ROM `src/string.c` editor helpers (STRING-001..012).

The descriptor-state setters (`string_edit`, `string_append`) and the
input dispatcher (`string_add`) live alongside the pure utilities here.
Descriptor plumbing is provided by `mud/olc/editor_state.py`
(OLC-INFRA-001).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mud.utils.text import smash_tilde

_log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mud.olc.editor_state import StringEdit


def merc_getline(string: str) -> tuple[str, str]:
    """Read one ``\\n``-terminated line; return ``(rest, line)``.

    Mirrors ROM ``merc_getline`` (src/string.c:647-674). When ``\\n`` is
    followed by ``\\r``, both are consumed (the ROM canonical line-ending
    pair). The terminator is not included in the returned line.
    """

    nl = string.find("\n")
    if nl == -1:
        return "", string
    line = string[:nl]
    rest_start = nl + 1
    if rest_start < len(string) and string[rest_start] == "\r":
        rest_start += 1
    return string[rest_start:], line


def first_arg(argument: str, lower: bool = False) -> tuple[str, str]:
    """Quote/paren-aware single-arg parser.

    Mirrors ROM ``first_arg`` (src/string.c:468-508). Returns
    ``(rest, word)`` — the remainder of *argument* (with leading spaces
    stripped) and the parsed first word.

    Recognized quote characters: ``'``, ``"``, ``%`` (each pairs with
    itself); ``(`` pairs with ``)``. Quoted words may contain spaces.
    Unterminated quotes consume the rest of the input.

    When ``lower`` is True (ROM ``fCase``), the parsed word is
    lowercased; otherwise its case is preserved.
    """

    i = 0
    n = len(argument)
    while i < n and argument[i] == " ":
        i += 1

    end_char = " "
    if i < n and argument[i] in ("'", '"', "%", "("):
        if argument[i] == "(":
            end_char = ")"
        else:
            end_char = argument[i]
        i += 1

    chars: list[str] = []
    while i < n:
        c = argument[i]
        if c == end_char:
            i += 1
            break
        chars.append(c.lower() if lower else c)
        i += 1

    while i < n and argument[i] == " ":
        i += 1

    return argument[i:], "".join(chars)


def string_proper(argument: str) -> str:
    """Uppercase the first character of each space-delimited word.

    Mirrors ROM ``string_proper`` (src/string.c:551-572). Differs from
    ``str.title()``: ROM only uppercases the boundary character — the
    rest of each word is left as-is.
    """

    chars = list(argument)
    i = 0
    n = len(chars)
    while i < n:
        if chars[i] != " ":
            chars[i] = chars[i].upper()
            while i < n and chars[i] != " ":
                i += 1
        else:
            i += 1
    return "".join(chars)


def string_unpad(argument: str) -> str:
    """Trim leading and trailing spaces (only spaces, not all whitespace).

    Mirrors ROM ``string_unpad`` (src/string.c:516-543). Used by
    `aedit_builder` when normalizing area-name input.
    """

    return argument.strip(" ")


def numlines(string: str) -> str:
    """Format string as line-numbered listing (``%2d. <line>\n\r``).

    Mirrors ROM ``numlines`` (src/string.c:676-692). Returns a string where
    each line from the input is prefixed with its 1-indexed line number in
    ``%2d`` format (right-aligned 2-char width), followed by a period and
    the line content, with ``\n\r`` appended to each line.

    Used by ``.s`` dot-command and `string_append` greeting.
    """

    if not string:
        return ""

    lines: list[str] = []
    line_num = 1
    rest = string

    while rest:
        rest, line = merc_getline(rest)
        lines.append(f"{line_num:2d}. {line}\n\r")
        line_num += 1

    return "".join(lines)


def string_linedel(string: str, line: int) -> str:
    """Remove the 1-indexed line N from the string.

    Mirrors ROM ``string_linedel`` (src/string.c:574-605). Removes the
    line at position *line* (1-indexed). Out-of-range line numbers are
    a no-op. Line endings (``\n\r``) are preserved throughout.

    Used by ``.ld`` dot-command.
    """

    if line < 1:
        return string

    buf: list[str] = []
    cnt = 1
    i = 0

    while i < len(string):
        c = string[i]

        if cnt != line:
            buf.append(c)

        if c == "\n":
            if i + 1 < len(string) and string[i + 1] == "\r":
                if cnt != line:
                    buf.append(string[i + 1])
                i += 1
            cnt += 1

        i += 1

    return "".join(buf)


def string_lineadd(string: str, newstr: str, line: int) -> str:
    """Insert newstr as the 1-indexed line N.

    Mirrors ROM ``string_lineadd`` (src/string.c:607-645). Inserts
    *newstr* as the line at position *line* (1-indexed). The inserted
    line gets a ``\n\r`` suffix.

    Used by ``.li`` and ``.lr`` dot-commands.
    """

    buf: list[str] = []
    cnt = 1
    done = False
    i = 0

    # Iterate through string; continue past end if insertion hasn't happened yet
    # and we've reached the target line number
    while i < len(string):
        # Check if we should insert at this line number
        if cnt == line and not done:
            buf.append(newstr)
            buf.append("\n\r")
            cnt += 1
            done = True

        c = string[i]
        buf.append(c)

        if c == "\n":
            if i + 1 < len(string) and string[i + 1] == "\r":
                buf.append(string[i + 1])
                i += 1
            cnt += 1

        i += 1

    # After exhausting the string, if insertion hasn't happened and we've
    # reached the target line, insert now (for appending past the end)
    if cnt == line and not done:
        buf.append(newstr)
        buf.append("\n\r")

    return "".join(buf)


def string_replace(orig: str, old: str, new: str) -> str:
    """Replace the FIRST occurrence of `old` substring with `new`.

    Mirrors ROM ``string_replace`` (src/string.c:95-112). Replaces only
    the first occurrence of *old* within *orig*. If *old* is not found,
    returns *orig* unchanged.

    Used by `string_add::.r` dot-command (STRING-004) and `aedit_builder`.
    """

    if not old or old not in orig:
        return orig

    # Find the index of the first occurrence
    idx = orig.find(old)
    if idx == -1:
        return orig

    # Replace: prefix + new + suffix (skipping the old substring)
    return orig[:idx] + new + orig[idx + len(old) :]


def format_string(string: str) -> str:  # mirrors ROM src/string.c:299-451
    """Word-wrap *string* to 77 columns with sentence capitalization.

    Two-phase implementation mirroring ROM's char-by-char state machine:

    Phase 1 (src/string.c:311-400) — tokenize and normalize:
      - Collapse \\n, \\r, and runs of spaces to a single space (leading
        whitespace at buffer position 0 is silently dropped).
      - After ``.``/``?``/``!`` emit two spaces and set the capitalize flag;
        if the punctuation is immediately followed by ``"`` consume it too,
        emitting ``<punct>"  `` (four chars total).
      - When ``)`` follows ``<punct><space><space>`` rebalance the parens:
        replace the two trailing spaces with ``)`` and one space.
      - Any other char is appended; if the capitalize flag is set, emit the
        uppercase form and clear the flag.

    Phase 2 (src/string.c:407-447) — wrap at 77 columns:
      - While remaining text is ≥ 77 chars: search backward from column 73
        (first wrap) or 76 (subsequent wraps) for a space; break there and
        emit ``\\n\\r``.
      - If no space is found (word > 77 chars): emit a ``bug`` log, break at
        column 75 with a ``-\\n\\r`` fallback.
      - Append the final segment and ensure the output ends with ``\\n\\r``.
    """
    # ------------------------------------------------------------------ #
    # Phase 1 — normalize whitespace, punctuation, capitalization          #
    # mirrors ROM src/string.c:311-400                                     #
    # ------------------------------------------------------------------ #
    buf: list[str] = []
    cap = True  # ROM: bool cap = TRUE
    rdesc = 0
    n = len(string)

    while rdesc < n:
        c = string[rdesc]

        if c == "\n":  # mirrors ROM src/string.c:313-320
            # Treat \n as a space; but only if buf is non-empty and last != ' '
            if buf and buf[-1] != " ":
                buf.append(" ")

        elif c == "\r":  # mirrors ROM src/string.c:321 (else if (*rdesc=='\r');)
            pass  # silently skip

        elif c == " ":  # mirrors ROM src/string.c:322-329
            if buf and buf[-1] != " ":
                buf.append(" ")
            # at i==0 (buf empty) leading space is simply dropped

        elif c == ")":  # mirrors ROM src/string.c:330-346
            # Paren rebalance: if buf ends in '<punct><space><space>' rewrite
            if (
                len(buf) >= 3
                and buf[-1] == " "
                and buf[-2] == " "
                and buf[-3] in (".", "?", "!")
            ):
                # Replace the two trailing spaces: buf[-2]= ')', buf[-1]= ' ', append ' '
                buf[-2] = ")"
                buf[-1] = " "
                buf.append(" ")
            else:
                buf.append(c)

        elif c in (".", "?", "!"):  # mirrors ROM src/string.c:347-388
            # Check if buf already ends in '<punct><space><space>' (consecutive sentence-end)
            if (
                len(buf) >= 3
                and buf[-1] == " "
                and buf[-2] == " "
                and buf[-3] in (".", "?", "!")
            ):
                # Overwrite the earlier trailing punct with new one
                buf[-3] = c
                # Check if next char is '"'
                if rdesc + 1 < n and string[rdesc + 1] == '"':
                    buf[-2] = '"'
                    buf[-1] = " "
                    buf.append(" ")
                    rdesc += 1  # consume the '"'
                # else the two spaces stay as-is (already present)
            else:
                buf.append(c)
                if rdesc + 1 < n and string[rdesc + 1] == '"':
                    buf.append('"')
                    buf.append(" ")
                    buf.append(" ")
                    rdesc += 1  # consume the '"'
                else:
                    buf.append(" ")
                    buf.append(" ")
            cap = True  # mirrors ROM src/string.c:387

        else:  # mirrors ROM src/string.c:389-398
            if cap:
                cap = False
                buf.append(c.upper())
            else:
                buf.append(c)

        rdesc += 1

    xbuf2 = "".join(buf)

    # ------------------------------------------------------------------ #
    # Phase 2 — word-wrap at 77 columns                                   #
    # mirrors ROM src/string.c:407-447                                     #
    # ------------------------------------------------------------------ #
    result: list[str] = []
    pos = 0  # current read position in xbuf2
    first_wrap = True  # ROM: xbuf[0] ? → subsequent wraps use col 76, first uses col 73

    while True:
        remaining = xbuf2[pos:]

        # ROM: for (i=0; i<77; i++) { if (!*(rdesc+i)) break; }
        # Count chars up to 77; if we hit end before 77, no more wrapping.
        chunk_len = 0
        for chunk_len in range(77):
            if chunk_len >= len(remaining):
                break
        else:
            chunk_len = 77  # all 77 chars exist → need to check if we wrap

        if chunk_len < 77:
            # Fewer than 77 chars remain → done with wrapping
            break

        # ROM: i = (xbuf[0] ? 76 : 73) — first wrap scans from 73, rest from 76
        scan_from = 73 if first_wrap else 76  # mirrors ROM src/string.c:418

        # Search backward from scan_from for a space
        space_at = -1
        for i in range(scan_from, 0, -1):
            if i < len(remaining) and remaining[i] == " ":
                space_at = i
                break

        if space_at > 0:  # mirrors ROM src/string.c:423-431
            result.append(remaining[:space_at])
            result.append("\n\r")
            pos += space_at + 1
            # Skip leading spaces on new line (ROM: while (*rdesc==' ') rdesc++)
            while pos < len(xbuf2) and xbuf2[pos] == " ":
                pos += 1
            first_wrap = False
        else:  # mirrors ROM src/string.c:432-438: no space found — mid-word break
            _log.warning("format_string: no spaces")  # mirrors ROM bug("No spaces", 0)
            result.append(remaining[:75])
            result.append("-\n\r")
            pos += 76
            first_wrap = False

    # Append remaining tail (mirrors ROM src/string.c:445-447)
    tail = xbuf2[pos:]

    # ROM trailing-trim (src/string.c:441-444): strip trailing spaces/\n/\r from tail
    # (the i-decrement loop; in practice usually a no-op for normal text)
    tail = tail.rstrip(" \n\r")

    result.append(tail)

    xbuf_final = "".join(result)

    # Ensure output ends with \n\r (mirrors ROM src/string.c:446-447)
    if not xbuf_final or xbuf_final[-2:] != "\n\r":
        xbuf_final += "\n\r"

    return xbuf_final


def string_edit(string_edit_obj: StringEdit) -> str:
    """Enter EDIT mode: clear buffer and return the editor banner.

    Mirrors ROM ``string_edit`` (src/string.c:38-57). Initializes the
    `StringEdit` object with an empty buffer and returns the editor
    banner (4 lines) that should be sent to the connection. The banner
    tells the user how to use the editor.

    The *string_edit_obj* parameter is modified in-place: buffer set to
    empty string, max_length and on_commit preserved.

    Used by OLC builders: `aedit_builder` (edit description), `redit`
    (edit-description), `medit` (edit-description).
    """

    # Clear the buffer (ROM: if (*pString == NULL) str_dup(""); else **pString = '\0')
    string_edit_obj.buffer = ""

    # Return the banner (4 lines, each ends with \n\r)
    banner = (
        "-========- Entering EDIT Mode -=========-\n\r"
        "    Type .h on a new line for help\n\r"
        " Terminate with a ~ or @ on a blank line.\n\r"
        "-=======================================-\n\r"
    )
    return banner


def string_add(session: object, raw_line: str) -> str | None:  # mirrors ROM src/string.c:121-286
    """Per-line OLC editor input dispatcher (STRING-004).

    Called by the game loop whenever ``session.string_edit`` is not None
    (mirrors ROM ``desc->pString != NULL`` routing in ``src/comm.c:833-847``).

    Return value convention:
      - ``None``   — line was silently absorbed (normal append).
      - ``str``    — message to send back to the player.

    ROM deviation (line 128 vs 230): ROM smashes tildes *before* checking for
    the ``~`` terminator, making ``~`` dead code at runtime (it becomes ``-``).
    Python port checks the terminator *before* smashing so both ``~`` and ``@``
    work as documented in the ``.h`` help text.  The deviation is intentional
    and noted here.
    """
    se = session.string_edit  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # Terminator check FIRST (before smash_tilde) — pragmatic deviation   #
    # ROM src/string.c:128 smashes tildes, then 230 checks for '~'; that  #
    # makes '~' dead code.  We reverse the order so both '~' and '@' work. #
    # ------------------------------------------------------------------ #
    if raw_line in ("~", "@"):  # mirrors ROM src/string.c:230
        # Call on_commit if present (mirrors ROM *ch->desc->pString = NULL after mprog hook)
        if se.on_commit is not None:
            se.on_commit(se.buffer)
        session.string_edit = None  # type: ignore[attr-defined]
        return None

    # mirrors ROM src/string.c:128 — smash tildes for file safety
    argument = smash_tilde(raw_line)

    # ------------------------------------------------------------------ #
    # Dot-command branch — mirrors ROM src/string.c:130-228                #
    # ------------------------------------------------------------------ #
    if argument.startswith("."):
        # Parse: arg1 = the dot-cmd (e.g. ".c"), arg2 = first quoted/bare
        # word, tmparg3 = raw remainder after arg2, arg3 = first word of
        # remainder (only used by .r).  Mirrors ROM lines 137-140.
        rest_after_cmd, arg1 = first_arg(argument)
        rest_after_arg2, arg2 = first_arg(rest_after_cmd)
        tmparg3 = rest_after_arg2  # raw remainder — used by .li / .lr
        _rest_after_arg3, _arg3 = first_arg(rest_after_arg2)

        if arg1.lower() == ".c":  # mirrors ROM src/string.c:142-148
            se.buffer = ""
            return "String cleared.\n\r"

        if arg1.lower() == ".s":  # mirrors ROM src/string.c:150-155
            return "String so far:\n\r" + numlines(se.buffer)

        if arg1.lower() == ".r":  # mirrors ROM src/string.c:157-171
            if not arg2:
                return 'usage:  .r "old string" "new string"\n\r'
            se.buffer = string_replace(se.buffer, arg2, _arg3)
            return f"'{arg2}' replaced with '{_arg3}'.\n\r"

        if arg1.lower() == ".f":  # mirrors ROM src/string.c:173-178
            se.buffer = format_string(se.buffer)
            return "String formatted.\n\r"

        if arg1.lower() == ".ld":  # mirrors ROM src/string.c:180-186
            se.buffer = string_linedel(se.buffer, int(arg2) if arg2 else 0)
            return "Line deleted.\n\r"

        if arg1.lower() == ".li":  # mirrors ROM src/string.c:188-193
            # tmparg3 is the raw remainder — multi-word text preserved
            se.buffer = string_lineadd(se.buffer, tmparg3, int(arg2) if arg2 else 0)
            return "Line inserted.\n\r"

        if arg1.lower() == ".lr":  # mirrors ROM src/string.c:196-204
            line_num = int(arg2) if arg2 else 0
            se.buffer = string_linedel(se.buffer, line_num)
            se.buffer = string_lineadd(se.buffer, tmparg3, line_num)
            return "Line replaced.\n\r"

        if arg1.lower() == ".h":  # mirrors ROM src/string.c:206-224
            return (
                "Sedit help (commands on blank line):   \n\r"
                ".r 'old' 'new'   - replace a substring \n\r"
                "                   (requires '', \"\") \n\r"
                ".h               - get help (this info)\n\r"
                ".s               - show string so far  \n\r"
                ".f               - (word wrap) string  \n\r"
                ".c               - clear string so far \n\r"
                ".ld <num>        - delete line number <num>\n\r"
                ".li <num> <str>  - insert <str> at line <num>\n\r"
                ".lr <num> <str>  - replace line <num> with <str>\n\r"
                "@                - end string          \n\r"
            )

        # mirrors ROM src/string.c:226-227
        return "SEdit:  Invalid dot command.\n\r"

    # ------------------------------------------------------------------ #
    # Length cap — mirrors ROM src/string.c:266-273                       #
    # ROM: strlen(*pString) + strlen(argument) >= MAX_STRING_LENGTH - 4   #
    # Python: len(buffer) + len(argument) >= se.max_length                #
    # (max_length defaults to 4604 = MAX_STRING_LENGTH - 4 already)       #
    # On overflow: force exit from editor without calling on_commit.       #
    # ------------------------------------------------------------------ #
    if len(se.buffer) + len(argument) >= se.max_length:
        session.string_edit = None  # type: ignore[attr-defined]  # mirrors ROM line 271
        return "String too long, last line skipped.\n\r"

    # ------------------------------------------------------------------ #
    # Normal append — mirrors ROM src/string.c:281-284                    #
    # strcat(buf, argument); strcat(buf, "\n\r")                          #
    # ------------------------------------------------------------------ #
    se.buffer = se.buffer + argument + "\n\r"
    return None


def string_append(string_edit_obj: StringEdit, current: str) -> str:
    """Enter APPEND mode: preserve buffer and return banner + line listing.

    Mirrors ROM ``string_append`` (src/string.c:66-86). Initializes the
    `StringEdit` object with the provided *current* string (preserving
    it, unlike EDIT mode which clears) and returns the editor banner
    (4 lines) followed by the line-numbered listing (via `numlines`).

    The *string_edit_obj* parameter is modified in-place: buffer set to
    *current*, max_length and on_commit preserved.

    Used by every OLC description builder that needs to append to
    existing text (aedit, redit, medit, oedit, etc.).
    """

    # Preserve the buffer (ROM: if (*pString == NULL) str_dup(""); else keep as-is)
    string_edit_obj.buffer = current or ""

    # Return the banner (4 lines) followed by the numlines listing
    banner = (
        "-=======- Entering APPEND Mode -========-\n\r"
        "    Type .h on a new line for help\n\r"
        " Terminate with a ~ or @ on a blank line.\n\r"
        "-=======================================-\n\r"
    )
    listing = numlines(string_edit_obj.buffer)
    return banner + listing
