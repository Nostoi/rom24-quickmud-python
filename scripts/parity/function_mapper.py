#!/usr/bin/env python3
"""
Comprehensive C→Python Function Mapper for ROM Parity

This script creates a detailed mapping of ROM 2.4b C functions to Python
equivalents, using intelligent heuristics to find renamed functions.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set


@dataclass
class FunctionInfo:
    """Information about a function."""
    name: str
    file: str
    line: int
    signature: str = ""


# Common C→Python naming patterns
NAMING_PATTERNS = [
    # ROM C → Python patterns
    (r'do_(\w+)', r'\1'),  # do_recall → recall
    (r'spell_(\w+)', r'\1'),  # spell_acid_blast → acid_blast
    (r'cmd_(\w+)', r'do_\1'),  # cmd_look → do_look
    (r'spec_(\w+)', r'spec_\1'),  # spec_mayor → spec_mayor (same)
    (r'_(\w+)', r'\1'),  # _send_to_char → send_to_char
    (r'(\w+)_update', r'\1_update'),  # weather_update → weather_update (same)
]

# Known C→Python equivalents (explicit mappings)
KNOWN_MAPPINGS = {
    # handler.c
    'affect_to_char': 'Character.add_affect',
    'affect_remove': 'Character.remove_affect',
    'affect_strip': 'Character.remove_affect',
    'char_from_room': 'Room.remove_character',
    'char_to_room': 'Room.add_character',
    'obj_to_char': 'Character.inventory.append',
    'obj_from_char': 'Character.inventory.remove',
    'obj_to_room': 'Room.add_object',
    'obj_from_room': 'Room.contents.remove',
    'get_obj_carry': '_find_obj_inventory',
    'get_obj_wear': 'Character.get_equipped',
    'get_obj_here': 'Room.find_object',
    'is_name': '_is_name_match',
    'is_exact_name': '_is_name_match',
    'is_full_name': '_is_name_match',
    'reset_char': 'Character initialization',
    'get_age': 'Character age calculation',
    'extract_char': 'extract_char (combat)',
    'extract_obj': '_extract_runtime_object',
    'get_obj_weight': '_get_obj_weight',
    'can_see': '_can_see',
    'can_see_obj': '_can_see_object',
    
    # fight.c
    'multi_hit': 'multi_hit',
    'one_hit': 'attack_round',
    'damage': 'apply_damage',
    'violence_update': 'combat_tick (in game_loop)',
    'raw_kill': 'raw_kill (in combat/engine.py)',
    'death_cry': 'death_cry',
    'make_corpse': 'make_corpse',
    'group_gain': 'group_gain',
    'dam_message': 'dam_message',
    'disarm': 'disarm',
    'check_parry': 'check_parry',
    'check_dodge': 'check_dodge',
    'check_shield_block': 'check_shield_block',
    'is_safe': 'is_safe',
    'is_safe_spell': '_is_safe_spell',
    
    # update.c
    'weather_update': 'weather_update (in game_loop.py)',
    'aggr_update': 'aggr_update (in game_loop.py)',
    'area_update': 'area_update (in game_loop.py)',
    'char_update': 'char_update (in game_loop.py)',
    'obj_update': 'obj_update (in game_loop.py)',
    'affect_update': 'affect_update (in game_loop.py)',
    'room_update': 'room_update (in game_loop.py)',
    'mobile_update': 'mobile_update',
    
    # db.c
    'boot_db': 'load_all_areas',
    'load_area': 'load_area_file',
    'load_mobiles': 'load_mobiles',
    'load_objects': 'load_objects',
    'load_rooms': 'load_rooms',
    'load_resets': 'load_resets',
    'load_shops': 'load_shops',
    'load_specials': 'load_specials',
    'assign_area_vnum': 'Area initialization',
    'reset_area': 'reset_area',
    'reset_room': 'reset_room',
    
    # save.c
    'save_char_obj': 'save_character',
    'load_char_obj': 'load_character',
    'fwrite_char': 'save_character',
    'fread_char': 'load_character',
    
    # comm.c
    'send_to_char': '_send_to_char / Character.send',
    'act': 'act (messaging system)',
    'act_new': 'act (messaging system)',
    'write_to_buffer': 'Connection.send',
    'close_socket': 'Connection.close',
    'page_to_char': 'page_to_char',
    
    # magic.c
    'obj_cast_spell': 'obj_cast_spell',
    'spell_list': 'SKILL_HANDLERS registry',
    
    # interp.c
    'interpret': 'command_interpreter',
    'command_table': 'COMMAND_TABLE',
    'check_social': 'check_social',
    'is_number': 'is_number',
    'number_argument': 'number_argument',
    
    # special.c (spec_funs)
    'special_proc': 'spec_fun registry',
    
    # act_comm.c - Communication commands
    'do_channels': 'do_channels',
    'do_deaf': 'do_deaf',
    'do_quiet': 'do_quiet',
    'do_afk': 'do_afk',
    'do_replay': 'do_replay',
    'do_pmote': 'do_pmote',
    'do_rent': 'do_quit (rent removed)',
    'do_follow': 'do_follow',
    'die_follower': 'stop_follower',
    'do_order': 'do_order',
    'do_group': 'do_group',
    'do_split': 'do_split',
    'do_gtell': 'do_gtell',
    'do_delete': 'character deletion in account service',
    
    # act_info.c - Information commands
    'show_char_to_char': 'show_char_to_char',
    'do_look': 'do_look',
    'do_read': 'do_read',
    'do_examine': 'do_examine',
    'do_scroll': 'do_scroll',
    'do_socials': 'do_socials',
    'do_motd': 'do_motd',
    'do_rules': 'do_rules',
    'do_worth': 'do_worth',
    'do_score': 'do_score',
    'do_affects': 'do_affects',
    'do_who': 'do_who',
    'do_whois': 'do_whois',
    'do_count': 'do_count',
    'do_compare': 'do_compare',
    'set_title': 'do_title',
    'do_wimpy': 'do_wimpy',
    
    # act_move.c - Movement commands
    'move_char': 'move_char',
    'find_door': 'find_door',
    'do_open': 'do_open',
    'do_close': 'do_close',
    'do_lock': 'do_lock',
    'do_unlock': 'do_unlock',
    'do_pick': 'pick_lock skill',
    'do_north': 'do_north',
    'do_south': 'do_south',
    'do_east': 'do_east',
    'do_west': 'do_west',
    'do_up': 'do_up',
    'do_down': 'do_down',
    'do_sit': 'do_sit',
    'do_rest': 'do_rest',
    'do_sleep': 'do_sleep',
    'do_wake': 'do_wake',
    'do_stand': 'do_stand',
    
    # act_obj.c - Object commands
    'get_obj': 'get_obj',
    'do_get': 'do_get',
    'do_put': 'do_put',
    'do_drop': 'do_drop',
    'do_give': 'do_give',
    'do_fill': 'do_fill',
    'do_pour': 'do_pour',
    'do_wear': 'do_wear',
    'do_remove': 'do_remove',
    'do_sacrifice': 'do_sacrifice',
    'do_quaff': 'do_quaff',
    'wear_obj': 'wear_obj',
    'remove_obj': 'remove_obj',
    
    # act_wiz.c - Wizard commands
    'do_goto': 'cmd_teleport',
    'do_at': 'do_at',
    'do_transfer': 'do_transfer',
    'do_stat': 'do_stat',
    'do_rstat': 'do_rstat',
    'do_ostat': 'do_ostat',
    'do_mstat': 'do_mstat',
    'do_vnum': 'do_vnum',
    'do_mfind': 'do_mfind',
    'do_ofind': 'do_ofind',
    'do_mload': 'cmd_spawn',
    'do_oload': 'do_oload',
    'do_purge': 'do_purge',
    'do_advance': 'do_advance',
    'do_trust': 'do_trust',
    'do_force': 'do_force',
    'do_freeze': 'do_freeze',
    'do_ban': 'ban commands in security/bans.py',
    'do_allow': 'ban commands in security/bans.py',
    'do_wizlock': 'toggle_wizlock',
    'do_newlock': 'toggle_newlock',
    'do_peace': 'do_peace',
    'do_echo': 'do_echo',
    'do_recho': 'do_recho',
    'do_shutdown': 'do_shutdown',
    'do_reboot': 'do_reboot',
    'do_log': 'toggle_log_all',
    'do_holylight': 'do_holylight',
    'do_incognito': 'do_incognito',
    
    # nanny.c - Character creation
    'nanny': 'account creation/login flow',
    'check_parse_name': 'name validation',
    'check_reconnect': 'reconnection handling',
    'check_playing': 'multi-play checking',
    
    # Other utilities
    'colour': 'ANSI color system',
    'colourconv': 'ANSI color conversion',
    'bug': 'do_bug',
    'log_string': 'logging system',
    'is_number': 'args parsing',
    'number_argument': 'args parsing',
    'one_argument': 'args parsing',
}



def extract_c_functions(src_dir: Path) -> Dict[str, List[FunctionInfo]]:
    """Extract all function definitions from ROM C source."""
    functions = defaultdict(list)
    
    if not src_dir.exists():
        print(f"Warning: C source directory not found: {src_dir}")
        return {}
    
    # Pattern to match C function definitions
    func_pattern = re.compile(
        r'^(?:static\s+)?(?:const\s+)?'  # Optional static/const
        r'(?:void|int|bool|char|long|short|CHAR_DATA|OBJ_DATA|ROOM_INDEX_DATA|AREA_DATA|[A-Z_]+\s*\*?)\s+'  # Return type
        r'(\w+)\s*'  # Function name (captured)
        r'\([^)]*\)',  # Parameters
        re.MULTILINE
    )
    
    for c_file in src_dir.glob('*.c'):
        try:
            content = c_file.read_text(errors='ignore')
            for match in func_pattern.finditer(content):
                func_name = match.group(1)
                # Skip common false positives
                if func_name in ('if', 'for', 'while', 'switch', 'return'):
                    continue
                    
                line_num = content[:match.start()].count('\n') + 1
                functions[c_file.stem].append(FunctionInfo(
                    name=func_name,
                    file=c_file.stem,
                    line=line_num,
                    signature=match.group(0)
                ))
        except Exception as e:
            print(f"Warning: Could not parse {c_file}: {e}")
    
    return functions


def extract_python_functions(mud_dir: Path) -> Dict[str, FunctionInfo]:
    """Extract all function/method definitions from Python source."""
    functions = {}
    
    for py_file in mud_dir.rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue
            
        try:
            content = py_file.read_text()
            # Match function definitions
            for match in re.finditer(r'^(?:    )?def (\w+)\(', content, re.MULTILINE):
                func_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1
                rel_path = py_file.relative_to(mud_dir.parent)
                
                functions[func_name] = FunctionInfo(
                    name=func_name,
                    file=str(rel_path),
                    line=line_num
                )
        except Exception as e:
            print(f"Warning: Could not parse {py_file}: {e}")
    
    return functions


def find_python_equivalent(c_func: str, py_functions: Dict[str, FunctionInfo]) -> str | None:
    """Find Python equivalent using naming patterns and heuristics."""
    
    # Check explicit mapping first
    if c_func in KNOWN_MAPPINGS:
        return KNOWN_MAPPINGS[c_func]
    
    # Check exact match
    if c_func in py_functions:
        return c_func
    
    # Try naming patterns
    for c_pattern, py_pattern in NAMING_PATTERNS:
        match = re.match(c_pattern, c_func)
        if match:
            py_name = re.sub(c_pattern, py_pattern, c_func)
            if py_name in py_functions:
                return py_name
    
    # Check substring matches (might be class method)
    c_lower = c_func.lower()
    for py_func in py_functions:
        if c_lower in py_func.lower() or py_func.lower() in c_lower:
            # Similarity check - at least 70% match
            common = len(set(c_lower) & set(py_func.lower()))
            if common / max(len(c_lower), len(py_func.lower())) >= 0.7:
                return py_func
    
    return None


def generate_mapping_report(
    c_functions: Dict[str, List[FunctionInfo]],
    py_functions: Dict[str, FunctionInfo],
    output_path: Path
) -> None:
    """Generate comprehensive C→Python function mapping report."""
    
    # Categorize functions
    mapped = {}
    unmapped = []
    total_c_funcs = sum(len(funcs) for funcs in c_functions.values())
    
    for c_file, funcs in sorted(c_functions.items()):
        for func in funcs:
            py_equiv = find_python_equivalent(func.name, py_functions)
            if py_equiv:
                mapped[f"{c_file}.c:{func.name}"] = py_equiv
            else:
                unmapped.append(f"{c_file}.c:{func.name} (line {func.line})")
    
    # Generate report
    lines = [
        "=" * 80,
        "ROM 2.4b C to Python Function Mapping",
        f"Generated: {Path.cwd()}",
        "=" * 80,
        "",
        f"Total C functions analyzed: {total_c_funcs}",
        f"Mapped functions: {len(mapped)} ({len(mapped) * 100 // total_c_funcs}%)",
        f"Unmapped functions: {len(unmapped)} ({len(unmapped) * 100 // total_c_funcs}%)",
        "",
        "=" * 80,
        "MAPPED FUNCTIONS (C → Python)",
        "=" * 80,
        "",
    ]
    
    # Group by C file
    by_file = defaultdict(list)
    for c_func, py_func in sorted(mapped.items()):
        c_file = c_func.split(':')[0]
        by_file[c_file].append((c_func.split(':')[1], py_func))
    
    for c_file in sorted(by_file.keys()):
        lines.append(f"\n## {c_file}")
        lines.append("-" * 80)
        for c_name, py_name in by_file[c_file]:
            lines.append(f"  {c_name:<30} → {py_name}")
    
    lines.extend([
        "",
        "",
        "=" * 80,
        "UNMAPPED FUNCTIONS (Need Verification)",
        "=" * 80,
        "",
        "These functions may be:",
        "  1. Not yet implemented in Python",
        "  2. Renamed with no obvious pattern",
        "  3. Merged into other functions",
        "  4. Deprecated/unused in ROM 2.4b",
        "",
    ])
    
    # Group unmapped by file
    unmapped_by_file = defaultdict(list)
    for entry in unmapped:
        parts = entry.split(':')
        c_file = parts[0]
        rest = ':'.join(parts[1:])
        unmapped_by_file[c_file].append(rest)
    
    for c_file in sorted(unmapped_by_file.keys()):
        lines.append(f"\n## {c_file}")
        lines.append("-" * 80)
        for func in unmapped_by_file[c_file]:
            lines.append(f"  {func}")
    
    lines.extend([
        "",
        "",
        "=" * 80,
        "ANALYSIS SUMMARY",
        "=" * 80,
        "",
        f"Coverage: {len(mapped) / total_c_funcs * 100:.1f}%",
        "",
        "Next Steps:",
        "1. Review unmapped functions to verify they're truly missing",
        "2. Add explicit mappings for renamed functions to KNOWN_MAPPINGS",
        "3. Implement missing critical functions",
        "4. Mark deprecated functions that don't need implementation",
        "",
    ])
    
    report = '\n'.join(lines)
    output_path.write_text(report)
    print(report)
    print(f"\nMapping report written to {output_path}")


def main():
    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    src_dir = project_root / 'src'
    mud_dir = project_root / 'mud'
    
    if not mud_dir.exists():
        print(f"Error: mud/ directory not found at {mud_dir}")
        sys.exit(1)
    
    print("Extracting C functions from src/...")
    c_functions = extract_c_functions(src_dir)
    
    print(f"Found {sum(len(f) for f in c_functions.values())} C functions")
    
    print("\nExtracting Python functions from mud/...")
    py_functions = extract_python_functions(mud_dir)
    
    print(f"Found {len(py_functions)} Python functions")
    
    print("\nGenerating mapping report...")
    output_path = project_root / 'FUNCTION_MAPPING.md'
    generate_mapping_report(c_functions, py_functions, output_path)


if __name__ == '__main__':
    main()
