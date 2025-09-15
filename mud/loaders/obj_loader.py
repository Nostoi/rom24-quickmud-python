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
            
            # Parse item type and extra flags
            type_flags_line = tokenizer.next_line().split()
            item_type = type_flags_line[0] if len(type_flags_line) > 0 else 'trash'
            extra_flags = type_flags_line[1] if len(type_flags_line) > 1 else ''
            wear_flags = type_flags_line[2] if len(type_flags_line) > 2 else ''
            
            # Parse values
            values_line = tokenizer.next_line().split()
            value0 = int(values_line[0]) if len(values_line) > 0 and values_line[0].lstrip('-').isdigit() else 0
            value1 = int(values_line[1]) if len(values_line) > 1 and values_line[1].lstrip('-').isdigit() else 0
            value2 = int(values_line[2]) if len(values_line) > 2 and values_line[2].lstrip('-').isdigit() else 0
            value3 = int(values_line[3]) if len(values_line) > 3 and values_line[3].lstrip('-').isdigit() else 0
            value4 = int(values_line[4]) if len(values_line) > 4 and values_line[4].lstrip('-').isdigit() else 0
            
            # Parse weight, cost, condition
            weight_cost = tokenizer.next_line().split()
            weight = int(weight_cost[0]) if len(weight_cost) > 0 and weight_cost[0].isdigit() else 0
            cost = int(weight_cost[1]) if len(weight_cost) > 1 and weight_cost[1].isdigit() else 0
            condition = weight_cost[2] if len(weight_cost) > 2 else 'P'
            
            obj = ObjIndex(
                vnum=vnum,
                name=name,
                short_descr=short_descr,
                description=desc,
                material=extra,
                item_type=item_type,
                extra_flags=extra_flags,
                wear_flags=wear_flags,
                value=[value0, value1, value2, value3, value4],
                weight=weight,
                cost=cost,
                condition=condition,
                area=area,
            )
            obj_registry[vnum] = obj
            
            # Process extra descriptions and affects
            while True:
                peek = tokenizer.peek_line()
                if peek is None or peek.startswith('#') or peek == '$':
                    break
                if peek.startswith('E'):
                    tokenizer.next_line()  # consume 'E'
                    keyword = tokenizer.next_line().rstrip('~')
                    descr = tokenizer.read_string_tilde()
                    obj.extra_descr.append({'keyword': keyword, 'description': descr})
                elif peek.startswith('A'):
                    tokenizer.next_line()  # consume 'A'
                    affect_line = tokenizer.next_line().split()
                    location = int(affect_line[0]) if len(affect_line) > 0 and affect_line[0].lstrip('-').isdigit() else 0
                    modifier = int(affect_line[1]) if len(affect_line) > 1 and affect_line[1].lstrip('-').isdigit() else 0
                    obj.affects.append({'location': location, 'modifier': modifier})
                else:
                    break
        elif line == '$':
            break
