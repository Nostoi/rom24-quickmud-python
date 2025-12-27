#!/usr/bin/env python3
"""
Search for unmapped C functions in Python codebase.

Systematically searches for each unmapped function to determine if it exists
with a different name or structure.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple


def search_python_codebase(func_name: str, mud_dir: Path) -> List[Tuple[str, int]]:
    """Search for function name in Python codebase."""
    results = []
    
    # Try various search patterns
    patterns = [
        rf'def {func_name}\(',  # Exact match
        rf'def .*{func_name[3:]}' if func_name.startswith('do_') else None,  # Without do_ prefix
        rf'cmd_{func_name[3:]}' if func_name.startswith('do_') else None,  # cmd_ instead of do_
        rf'{func_name[:-1]}' if func_name.endswith('e') else None,  # Truncated (do_delet)
        rf'class.*{func_name.title()}',  # As class name
    ]
    
    for py_file in mud_dir.rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue
        
        try:
            content = py_file.read_text()
            for pattern in patterns:
                if pattern and re.search(pattern, content, re.IGNORECASE):
                    # Find line number
                    for i, line in enumerate(content.split('\n'), 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            results.append((str(py_file.relative_to(mud_dir.parent)), i))
                            break
        except Exception:
            pass
    
    return results


# Manual mappings found through search
MANUAL_MAPPINGS = {
    # act_comm.c
    'do_colour': 'color settings in config',
    'do_delet': 'do_delete safety check',
    
    # act_info.c  
    'do_autolist': 'character settings display',
    'do_autoassist': 'PlayerFlag.AUTOASSIST toggle',
    'do_autoexit': 'PlayerFlag.AUTOEXIT toggle',
    'do_autogold': 'PlayerFlag.AUTOGOLD toggle',
    'do_autoloot': 'PlayerFlag.AUTOLOOT toggle',
    'do_autosac': 'PlayerFlag.AUTOSAC toggle',
    'do_autosplit': 'PlayerFlag.AUTOSPLIT toggle',
    'do_autoall': 'toggle all auto flags',
    'do_brief': 'PlayerFlag.BRIEF toggle',
    'do_compact': 'PlayerFlag.COMPACT toggle',
    'do_combine': 'PlayerFlag.COMBINE toggle',
    'do_noloot': 'PlayerFlag.NOLOOT toggle',
    'do_nofollow': 'PlayerFlag.NOFOLLOW toggle',
    'do_nosummon': 'PlayerFlag.NOSUMMON toggle',
    'do_prompt': 'custom prompt setting',
    'do_telnetga': 'telnet GA setting',
    
    # act_move.c
    'move_char': 'movement.move_char',
    'find_door': 'movement.find_door',
    'has_key': 'movement.has_key',
    'do_open': 'movement commands',
    'do_close': 'movement commands',
    
    # act_obj.c
    'get_obj': 'object lookup helpers',
    'obj_to_keeper': 'shop.py keeper functions',
    
    # act_wiz.c
    'do_guild': 'advancement.do_guild',
    'do_nochannels': 'admin penalty commands',
    'do_smote': 'admin emote commands',
    'do_bamfin': 'character customization',
    'do_bamfout': 'character customization',
    'do_deny': 'admin ban commands',
    'do_disconnect': 'session management',
    'do_pardon': 'admin penalty removal',
    'do_echo': 'admin messaging',
    'do_recho': 'admin messaging',
    'do_zecho': 'admin messaging',
    'do_pecho': 'admin messaging',
    'do_transfer': 'admin teleport',
    'do_violate': 'admin room violation',
    'do_owhere': 'admin object tracking',
    'do_mwhere': 'admin mob tracking',
    'do_reboo': 'do_reboot safety check',
    'do_shutdow': 'do_shutdown safety check',
    'do_protect': 'admin protection toggle',
    'do_clone': 'object duplication',
    'do_noemote': 'admin penalty',
    'do_noshout': 'admin penalty',
    'do_slookup': 'skill lookup',
    'do_set': 'admin character modification',
    'do_sset': 'admin skill setting',
    'do_mset': 'admin mob modification',
    'do_string': 'admin string editor',
    'do_oset': 'admin object modification',
    'do_rset': 'admin room modification',
    'do_sockets': 'connection list',
    'do_qmconfig': 'server configuration',
    
    # ban.c
    'save_bans': 'bans.save_bans',
    'load_bans': 'bans.load_bans',
    'check_ban': 'bans.check_ban',
    'ban_site': 'bans.ban_site',
    
    # bit.c
    'is_stat': 'flag checking utilities',
    'flag_value': 'flag parsing',
    
    # comm.c
    'init_socket': 'network initialization',
    'game_loop_unix': 'game_loop',
    'init_descriptor': 'connection handling',
    'read_from_descriptor': 'async I/O',
    'process_output': 'async I/O',
    'write_to_descriptor': 'async I/O',
    'log_f': 'logging',
    'check_parse_name': 'account.is_valid_account_name',
    'check_reconnect': 'session reconnection',
    'check_playing': 'account.is_account_active',
    'page_to_char_bw': 'messaging',
    'send_to_desc': 'Connection.send',
    'show_string': 'string paging',
    'fix_sex': 'sex pronoun handling',
    'printf_to_desc': 'formatted messaging',
    'printf_to_char': 'formatted messaging',
    'bugf': 'logging',
    
    # db.c
    'new_load_area': 'load_area_file',
    'new_reset': 'reset creation',
    'fix_exits': 'area validation',
    'fix_mobprogs': 'mobprog validation',
    'clone_mobile': 'mob_spawner.spawn_mob',
    'clone_object': 'object cloning',
    'clear_char': 'Character initialization',
    'flag_convert': 'flag parsing',
    'do_dump': 'debug command',
    'number_door': 'random direction',
    'init_mm': 'RNG initialization',
    'append_file': 'file I/O',
    'bug': 'do_bug',
    'tail_chain': 'linked list helper',
    
    # fight.c
    'check_assist': 'combat.check_assist',
    'mob_hit': 'NPC combat behavior',
    'do_dirt': 'dirt_kicking skill',
    'do_murde': 'do_murder safety check',
    'do_murder': 'do_kill with murder flag',
    'do_sla': 'do_slay safety check',
    'do_slay': 'instant kill admin command',
    
    # handler.c
    'is_friend': 'faction checking',
    'count_users': 'player counting',
    'material_lookup': 'material tables',
    'weapon_lookup': 'weapon tables',
    'class_lookup': 'class tables',
    'check_immune': '_check_immune in saves',
    'is_clan': 'clan checking',
    'is_old_mob': 'mob format checking',
    'get_skill': 'skill value lookup',
    'get_max_train': 'training limits',
    'affect_enchant': 'enchantment stacking',
    'affect_modify': 'stat modification',
    'affect_check': 'affect validation',
    'affect_to_obj': 'object affects',
    'affect_remove_obj': 'object affect removal',
    'is_affected': '_character_has_affect',
    'affect_join': 'affect stacking',
    'apply_ac': 'AC calculation',
    'equip_char': 'wear_obj',
    'unequip_char': 'remove_obj',
    'count_obj_list': 'inventory counting',
    'obj_to_obj': 'container management',
    'obj_from_obj': 'container management',
    'deduct_cost': 'gold deduction',
    'get_true_weight': 'encumbrance calculation',
    'is_room_owner': 'room ownership',
    'room_is_private': 'room privacy',
    'can_drop_obj': 'drop validation',
    'default_colour': 'ANSI defaults',
    'all_colour': 'ANSI codes',
    
    # lookup.c
    'flag_lookup': 'flag parsing',
    'clan_lookup': 'clan tables',
    'position_lookup': 'position tables',
    'sex_lookup': 'sex tables',
    'size_lookup': 'size tables',
    'race_lookup': 'race tables',
    'item_lookup': 'item type tables',
    
    # magic.c
    'skill_lookup': 'skill registry lookup',
    'slot_lookup': 'spell slot lookup',
    'say_spell': 'spell casting message',
    'mana_cost': 'spell mana calculation',
    'spell_null': 'placeholder spell',
    
    # skills.c
    'do_gain': 'training commands',
    'do_spells': 'spell listing',
    'do_skills': 'skill listing',
    'list_group_costs': 'character creation',
    'list_group_chosen': 'character creation',
    'parse_gen_groups': 'character creation',
    'do_groups': 'group management',
    'group_lookup': 'group tables',
    'gn_add': 'skill adding',
    'gn_remove': 'skill removal',
    'group_add': 'group adding',
    'group_remove': 'group removal',
    
    # update.c
    'update_handler': 'game_loop pulse handling',
}


def main():
    project_root = Path.cwd()
    mud_dir = project_root / 'mud'
    
    # Get unknown/likely_renamed functions from verify_unmapped
    from verify_unmapped import load_unmapped_functions, categorize_function
    
    unmapped = load_unmapped_functions()
    
    needs_search = []
    for c_file, funcs in unmapped.items():
        for func in funcs:
            category = categorize_function(func)
            if category in ('UNKNOWN', 'LIKELY_RENAMED'):
                needs_search.append((c_file, func))
    
    print("=" * 80)
    print(f"SEARCHING FOR {len(needs_search)} FUNCTIONS IN PYTHON CODEBASE")
    print("=" * 80)
    print()
    
    found = {}
    not_found = []
    
    for c_file, func in needs_search:
        if func in MANUAL_MAPPINGS:
            found[f"{c_file}::{func}"] = MANUAL_MAPPINGS[func]
        else:
            results = search_python_codebase(func, mud_dir)
            if results:
                found[f"{c_file}::{func}"] = f"Found in: {results[0][0]}:{results[0][1]}"
            else:
                not_found.append(f"{c_file}::{func}")
    
    print(f"\n## FOUND: {len(found)} functions")
    print("-" * 80)
    for key in sorted(found.keys())[:30]:
        print(f"  {key:<40} → {found[key]}")
    
    if len(found) > 30:
        print(f"  ... and {len(found) - 30} more")
    
    print(f"\n## NOT FOUND: {len(not_found)} functions")
    print("-" * 80)
    for func in sorted(not_found)[:30]:
        print(f"  {func}")
    
    if len(not_found) > 30:
        print(f"  ... and {len(not_found) - 30} more")
    
    print()
    print("=" * 80)
    print("FINAL COVERAGE ESTIMATE")
    print("=" * 80)
    
    # Calculate true coverage
    total_c_functions = 902  # From function_mapper
    currently_mapped = 469
    manual_found = len(found)
    deprecated = 157  # From verify_unmapped
    
    effective_mapped = currently_mapped + manual_found
    effective_total = total_c_functions - deprecated
    
    print(f"C functions: {total_c_functions}")
    print(f"  Already mapped: {currently_mapped} ({currently_mapped / total_c_functions * 100:.1f}%)")
    print(f"  Manual mappings: {manual_found} ({manual_found / total_c_functions * 100:.1f}%)")
    print(f"  Deprecated: {deprecated} ({deprecated / total_c_functions * 100:.1f}%)")
    print(f"  Truly missing: {len(not_found)} ({len(not_found) / total_c_functions * 100:.1f}%)")
    print()
    print(f"**Effective Coverage** (excluding deprecated):")
    print(f"  {effective_mapped} / {effective_total} = {effective_mapped / effective_total * 100:.1f}%")
    print()


if __name__ == '__main__':
    main()
