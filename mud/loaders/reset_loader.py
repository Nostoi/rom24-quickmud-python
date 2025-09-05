from .base_loader import BaseTokenizer
from mud.models.room_json import ResetJson


def load_resets(tokenizer: BaseTokenizer, area):
    """Parse reset lines and store them on the area."""
    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        if line == 'S':
            continue
        if line == '$' or line.startswith('#'):
            # allow outer loader to handle following sections
            tokenizer.index -= 1
            break
        parts = line.split()
        if not parts:
            continue
        cmd = parts[0]
        try:
            nums = [int(p) for p in parts[1:] if p.lstrip('-').isdigit()]
        except ValueError:
            continue
        # pad to four integers
        while len(nums) < 4:
            nums.append(0)
        reset = ResetJson(command=cmd, arg1=nums[0], arg2=nums[1], arg3=nums[2], arg4=nums[3])
        area.resets.append(reset)
