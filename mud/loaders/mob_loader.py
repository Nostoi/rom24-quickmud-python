from mud.models.mob import MobIndex
from mud.registry import mob_registry
from .base_loader import BaseTokenizer


def load_mobiles(tokenizer: BaseTokenizer, area):
    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        if line.startswith('#'):
            if line == '#0' or line.startswith('#$'):
                break
            vnum = int(line[1:])
            player_name = tokenizer.next_line().rstrip('~')
            short_descr = tokenizer.next_line().rstrip('~')
            long_descr = tokenizer.read_string_tilde()
            desc = tokenizer.read_string_tilde()
            mob = MobIndex(vnum=vnum, player_name=player_name, short_descr=short_descr, long_descr=long_descr, description=desc, area=area)
            mob_registry[vnum] = mob
        elif line == '$':
            break
