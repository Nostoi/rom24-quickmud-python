"""Loader for ROM #MOBPROGS sections."""

from mud.mobprog import register_program_code

from .base_loader import BaseTokenizer


def load_mobprogs(tokenizer: BaseTokenizer, area) -> None:
    """Load mob program scripts and register their code."""

    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        if line == "$":
            break
        if not line.startswith("#"):
            continue
        if line == "#0":
            break
        try:
            vnum = int(line[1:])
        except ValueError:
            continue
        code = tokenizer.read_string_tilde().rstrip("\n")
        register_program_code(vnum, code)
