from mud.models.obj import ObjIndex
from mud.registry import obj_registry
from .base_loader import BaseTokenizer


def load_objects(tokenizer: BaseTokenizer, area):
    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        if line.startswith('#'):
            if line == '#0' or line.startswith('#$'):
                break
            vnum = int(line[1:])
            name = tokenizer.next_line().rstrip('~')
            short_descr = tokenizer.next_line().rstrip('~')
            desc = tokenizer.read_string_tilde()
            extra = tokenizer.read_string_tilde()
            obj = ObjIndex(vnum=vnum, name=name, short_descr=short_descr, description=desc, material=extra, area=area)
            obj_registry[vnum] = obj
        elif line == '$':
            break
