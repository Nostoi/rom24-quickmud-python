#!/usr/bin/env python3
"""
Manual verification helper for unmapped C functions.

This script systematically reviews unmapped functions and categorizes them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

# Load the unmapped functions from FUNCTION_MAPPING.md
def load_unmapped_functions() -> Dict[str, List[str]]:
    """Load unmapped functions from FUNCTION_MAPPING.md."""
    mapping_file = Path("FUNCTION_MAPPING.md")
    if not mapping_file.exists():
        print("Error: FUNCTION_MAPPING.md not found. Run function_mapper.py first.")
        return {}
    
    content = mapping_file.read_text()
    unmapped_section = content.split("UNMAPPED FUNCTIONS")[1].split("ANALYSIS SUMMARY")[0]
    
    unmapped_by_file = {}
    current_file = None
    
    for line in unmapped_section.split('\n'):
        if line.startswith('## '):
            current_file = line.strip('## ').strip()
            unmapped_by_file[current_file] = []
        elif line.strip() and current_file and not line.startswith(('-', '=', 'These')):
            # Extract function name from "  funcname (line 123)"
            match = re.match(r'\s+(\w+)\s+\(line', line)
            if match:
                unmapped_by_file[current_file].append(match.group(1))
    
    return unmapped_by_file


# Categorize functions by type
DEPRECATED_PATTERNS = [
    # Memory management (Python handles automatically)
    r'free_.*',
    r'.*_mem.*',
    r'get_.*_id',
    
    # Old formats/compatibility
    r'.*_old_.*',
    r'convert_.*',
    r'gettimeofday',
    r'random',
    r'srandom',
    
    # IMC (not implemented)
    r'imc.*',
    
    # File I/O helpers (Pythonic alternatives)
    r'fread_.*',
    r'fwrite_.*',
    r'smash_.*',
    
    # String utilities (Python built-ins)
    r'str_cmp',
    r'str_prefix',
    r'str_infix',
    r'str_suffix',
    
    # Buffer management (async I/O handles)
    r'.*_buffer',
    r'bust_a_prompt',
]

NOT_IMPLEMENTED_PATTERNS = [
    # OLC commands
    r'.*edit',
    r'do_asave',
    r'save_.*',
    r'show_.*',
    
    # Advanced admin commands
    r'do_copyover',
    r'copyover_.*',
    r'do_switch',
    r'do_return',
    r'do_snoop',
    
    # Character creation (different architecture)
    r'nanny',
    r'handle_con_.*',
    
    # Board system (simplified)
    r'.*_note.*',
    r'.*_board.*',
]

LIKELY_RENAMED_PATTERNS = [
    # Position/movement
    r'do_sit',
    r'do_rest',
    r'do_wake',
    r'do_sleep',
    
    # Info/inspection
    r'show_.*',
    r'check_.*',
    r'get_.*',
    
    # Object manipulation
    r'do_put',
    r'do_fill',
    r'do_pour',
    r'do_give',
    
    # Communication
    r'do_channels',
    r'do_replay',
    
    # Combat
    r'do_dirt',
    r'do_murde',
    r'do_murder',
    r'do_sla',
    r'do_slay',
]


def categorize_function(func_name: str) -> str:
    """Categorize an unmapped function."""
    for pattern in DEPRECATED_PATTERNS:
        if re.match(pattern, func_name):
            return "DEPRECATED"
    
    for pattern in NOT_IMPLEMENTED_PATTERNS:
        if re.match(pattern, func_name):
            return "NOT_IMPLEMENTED"
    
    for pattern in LIKELY_RENAMED_PATTERNS:
        if re.match(pattern, func_name):
            return "LIKELY_RENAMED"
    
    return "UNKNOWN"


def main():
    unmapped = load_unmapped_functions()
    
    if not unmapped:
        print("No unmapped functions found or FUNCTION_MAPPING.md not available.")
        return
    
    # Categorize all functions
    categorized = {
        "DEPRECATED": [],
        "NOT_IMPLEMENTED": [],
        "LIKELY_RENAMED": [],
        "UNKNOWN": [],
    }
    
    for c_file, funcs in unmapped.items():
        for func in funcs:
            category = categorize_function(func)
            categorized[category].append(f"{c_file}::{func}")
    
    # Print report
    print("=" * 80)
    print("UNMAPPED FUNCTION CATEGORIZATION REPORT")
    print("=" * 80)
    print()
    
    total_unmapped = sum(len(v) for v in categorized.values())
    
    for category, funcs in categorized.items():
        count = len(funcs)
        percentage = (count / total_unmapped * 100) if total_unmapped else 0
        
        print(f"\n## {category}: {count} functions ({percentage:.1f}%)")
        print("-" * 80)
        
        if category == "LIKELY_RENAMED":
            print("\n**ACTION NEEDED**: Search Python codebase for these functions")
            print()
        elif category == "NOT_IMPLEMENTED":
            print("\n**ACTION NEEDED**: Implement or document as intentionally excluded")
            print()
        elif category == "DEPRECATED":
            print("\n**NO ACTION**: These functions are deprecated or have Python equivalents")
            print()
        
        # Show first 20 examples
        for func in sorted(funcs)[:20]:
            print(f"  {func}")
        
        if count > 20:
            print(f"  ... and {count - 20} more")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total unmapped: {total_unmapped}")
    print(f"  Deprecated (can ignore): {len(categorized['DEPRECATED'])}")
    print(f"  Not implemented (need to decide): {len(categorized['NOT_IMPLEMENTED'])}")
    print(f"  Likely renamed (need to find): {len(categorized['LIKELY_RENAMED'])}")
    print(f"  Unknown (need manual review): {len(categorized['UNKNOWN'])}")
    print()
    
    # Estimate true coverage
    ignore_count = len(categorized['DEPRECATED'])
    actual_missing = total_unmapped - ignore_count
    
    print(f"Effective coverage (ignoring deprecated):")
    print(f"  Can be ignored: {ignore_count} functions")
    print(f"  Truly need review: {actual_missing} functions")
    print()


if __name__ == '__main__':
    main()
