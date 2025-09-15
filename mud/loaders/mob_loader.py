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
            race = tokenizer.next_line().rstrip('~')
            
            # Parse act flags, affected flags, alignment, group
            act_line = tokenizer.next_line().split()
            act_flags = act_line[0] if len(act_line) > 0 else ''
            affected_by = act_line[1] if len(act_line) > 1 else ''
            alignment = int(act_line[2]) if len(act_line) > 2 and act_line[2].lstrip('-').isdigit() else 0
            group = int(act_line[3]) if len(act_line) > 3 and act_line[3].isdigit() else 0
            
            # Parse level, thac0, ac, hitnodice, hitdicenum, hitdicesides, manadice, damroll, damdice
            stats_line = tokenizer.next_line().split()
            level = int(stats_line[0]) if len(stats_line) > 0 and stats_line[0].isdigit() else 1
            thac0 = int(stats_line[1]) if len(stats_line) > 1 and stats_line[1].lstrip('-').isdigit() else 20
            ac = stats_line[2] if len(stats_line) > 2 else '1d1+0'
            hit_dice = stats_line[3] if len(stats_line) > 3 else '1d1+0'  
            mana_dice = stats_line[4] if len(stats_line) > 4 else '1d1+0'
            damage_dice = stats_line[5] if len(stats_line) > 5 else '1d4+0'
            damage_type = stats_line[6] if len(stats_line) > 6 else 'beating'
            
            # Parse armor class values
            ac_line = tokenizer.next_line().split()
            ac_pierce = int(ac_line[0]) if len(ac_line) > 0 and ac_line[0].lstrip('-').isdigit() else 0
            ac_bash = int(ac_line[1]) if len(ac_line) > 1 and ac_line[1].lstrip('-').isdigit() else 0
            ac_slash = int(ac_line[2]) if len(ac_line) > 2 and ac_line[2].lstrip('-').isdigit() else 0  
            ac_exotic = int(ac_line[3]) if len(ac_line) > 3 and ac_line[3].lstrip('-').isdigit() else 0
            
            # Parse off/imm/res/vuln flags
            flags_line = tokenizer.next_line().split()
            offensive = flags_line[0] if len(flags_line) > 0 else ''
            immune = flags_line[1] if len(flags_line) > 1 else ''
            resist = flags_line[2] if len(flags_line) > 2 else ''
            vuln = flags_line[3] if len(flags_line) > 3 else ''
            
            # Parse position, sex, wealth
            pos_line = tokenizer.next_line().split()
            start_pos = pos_line[0] if len(pos_line) > 0 else 'standing'
            default_pos = pos_line[1] if len(pos_line) > 1 else 'standing'
            sex = pos_line[2] if len(pos_line) > 2 else 'neutral'
            wealth = int(pos_line[3]) if len(pos_line) > 3 and pos_line[3].isdigit() else 0
            
            # Parse form/parts/size/material
            form_line = tokenizer.next_line().split()
            form = form_line[0] if len(form_line) > 0 else '0'
            parts = form_line[1] if len(form_line) > 1 else '0' 
            size = form_line[2] if len(form_line) > 2 else 'medium'
            material = form_line[3] if len(form_line) > 3 else '0'
            
            mob = MobIndex(
                vnum=vnum, 
                player_name=player_name, 
                short_descr=short_descr, 
                long_descr=long_descr, 
                description=desc, 
                race=race,
                act_flags=act_flags,
                affected_by=affected_by,
                alignment=alignment,
                group=group,
                level=level,
                thac0=thac0,
                ac=ac,
                hit_dice=hit_dice,
                mana_dice=mana_dice,
                damage_dice=damage_dice,
                damage_type=damage_type,
                ac_pierce=ac_pierce,
                ac_bash=ac_bash,
                ac_slash=ac_slash,
                ac_exotic=ac_exotic,
                offensive=offensive,
                immune=immune,
                resist=resist,
                vuln=vuln,
                start_pos=start_pos,
                default_pos=default_pos,
                sex=sex,
                wealth=wealth,
                form=form,
                parts=parts,
                size=size,
                material=material,
                area=area
            )
            mob_registry[vnum] = mob
        elif line == '$':
            break
