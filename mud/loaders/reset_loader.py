from collections.abc import Iterator

from mud.models.room_json import ResetJson

from .base_loader import BaseTokenizer


def _iter_reset_numbers(tokens: list[str]) -> Iterator[int]:
    """Yield integer tokens until a comment marker is reached."""

    for token in tokens:
        if token.startswith("*"):
            break
        try:
            yield int(token)
        except ValueError:
            continue


def load_resets(tokenizer: BaseTokenizer, area):
    """Parse reset lines using ROM load_resets semantics."""

    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        if line == "S":
            break
        if line == "$" or line.startswith("#"):
            # allow outer loader to handle following sections
            tokenizer.index -= 1
            break
        parts = line.split()
        if not parts:
            continue
        command = parts[0][0].upper()
        if command == "S":
            break

        numbers = list(_iter_reset_numbers(parts[1:]))
        if not numbers:
            area.resets.append(ResetJson(command=command))
            continue

        number_iter = iter(numbers)
        next(number_iter, None)  # Skip if_flag
        arg1 = next(number_iter, 0)
        arg2 = next(number_iter, 0)
        if command in {"G", "R"}:
            arg3 = 0
        else:
            arg3 = next(number_iter, 0)
        arg4 = next(number_iter, 0) if command in {"P", "M"} else 0

        reset = ResetJson(command=command, arg1=arg1, arg2=arg2, arg3=arg3, arg4=arg4)
        area.resets.append(reset)
