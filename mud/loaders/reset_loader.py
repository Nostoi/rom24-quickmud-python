from mud.models.room import Reset
from .base_loader import BaseTokenizer


def load_resets(tokenizer: BaseTokenizer, area):
    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        if line == 'S':
            continue
        if line == '$':
            break
        parts = line.split()
        if len(parts) < 5:
            continue
        cmd = parts[0]
        try:
            nums = [int(p) for p in parts[1:5]]
        except ValueError:
            continue
        reset = Reset(command=cmd, arg1=nums[0], arg2=nums[1], arg3=nums[2], arg4=nums[3])
        # resets currently ignored
        pass
