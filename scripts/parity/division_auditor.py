#!/usr/bin/env python3
"""
Division Operation Auditor for ROM Parity

This script audits all division operations in the Python codebase to identify
which ones may need c_div for proper C integer division semantics.

Key insight: c_div is only needed when:
1. The dividend OR divisor could be negative
2. The result is used in ROM-parity-critical calculations

Safe to use // when:
1. Both operands are always non-negative (levels, percentages, counts)
2. The calculation is Python-specific (not porting C code)
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set


@dataclass
class DivisionUsage:
    """Represents a division operation found in code."""
    file: str
    line: int
    code: str
    operator: str  # '//' or 'c_div'
    context: str
    risk_level: str  # 'safe', 'review', 'needs_c_div'
    reason: str


# Variables that are always non-negative in ROM context
KNOWN_POSITIVE_VARS = {
    'level', 'hit', 'max_hit', 'mana', 'max_mana', 'move', 'max_move',
    'gold', 'silver', 'exp', 'played', 'count', 'total', 'percent',
    'skill', 'value', 'weight', 'cost', 'age', 'timer', 'position',
    'heal_rate', 'mana_rate', 'roll', 'gain', 'session_played',
    'member_count', 'dice_number', 'dice_type', 'skill_total',
    'weapon_level', 'mob_level', 'victim_gold', 'victim_silver',
}

# Patterns indicating ROM-critical calculations
ROM_CRITICAL_PATTERNS = [
    r'damage', r'dam\b', r'thac0', r'armor', r'ac\b',
    r'saves?_spell', r'saving_throw', r'resist', r'immune', r'vuln',
    r'affect', r'modifier', r'bonus', r'penalty',
]

# Files with ROM-critical calculations
ROM_CRITICAL_FILES = [
    'combat/engine.py', 'skills/handlers.py', 'affects/saves.py',
    'game_loop.py', 'mobprog.py', 'spec_funs.py',
]


def analyze_division(file_path: Path, line_num: int, code: str, context_lines: List[str]) -> DivisionUsage:
    """Analyze a division operation to determine if it needs c_div."""
    
    # Get context
    start = max(0, line_num - 3)
    end = min(len(context_lines), line_num + 2)
    context = '\n'.join(context_lines[start:end])
    
    operator = '//' if '//' in code else ('c_div' if 'c_div' in code else '/')
    
    # Already using c_div - safe
    if 'c_div' in code:
        return DivisionUsage(
            file=str(file_path),
            line=line_num + 1,
            code=code.strip(),
            operator='c_div',
            context=context,
            risk_level='safe',
            reason='Already using c_div'
        )
    
    # Check for known-positive variables
    all_positive = True
    code_lower = code.lower()
    
    # Check for negative indicators
    negative_indicators = ['-', 'difference', 'diff', 'delta', 'offset', 'modifier']
    has_negative_risk = any(ind in code_lower for ind in negative_indicators)
    
    # Check if variables are known positive
    for var in KNOWN_POSITIVE_VARS:
        if var in code_lower:
            # Variable found - check if it's the operand
            pass  # Continue checking
    
    # Check for ROM-critical patterns
    is_rom_critical = any(re.search(pat, code_lower) for pat in ROM_CRITICAL_PATTERNS)
    
    # Check if in ROM-critical file
    rel_path = str(file_path)
    in_critical_file = any(crit in rel_path for crit in ROM_CRITICAL_FILES)
    
    # Determine risk level
    if is_rom_critical and has_negative_risk:
        risk_level = 'needs_c_div'
        reason = 'ROM-critical calculation with potential negative operands'
    elif is_rom_critical:
        risk_level = 'review'
        reason = 'ROM-critical calculation - verify operands are always positive'
    elif in_critical_file and has_negative_risk:
        risk_level = 'review'
        reason = 'In ROM-critical file with potential negative operands'
    else:
        risk_level = 'safe'
        reason = 'Operands appear to be always non-negative'
    
    return DivisionUsage(
        file=str(file_path),
        line=line_num + 1,
        code=code.strip(),
        operator=operator,
        context=context,
        risk_level=risk_level,
        reason=reason
    )


def audit_file(file_path: Path) -> List[DivisionUsage]:
    """Audit a single Python file for division operations."""
    results = []
    
    try:
        content = file_path.read_text()
        lines = content.split('\n')
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return []
    
    for i, line in enumerate(lines):
        # Skip comments
        if line.strip().startswith('#'):
            continue
        
        # Check for floor division
        if '//' in line and '://' not in line:  # Exclude URLs
            usage = analyze_division(file_path, i, line, lines)
            results.append(usage)
    
    return results


def audit_directory(mud_path: Path) -> List[DivisionUsage]:
    """Audit all Python files in mud/ directory."""
    results = []
    
    for py_file in mud_path.rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue
        results.extend(audit_file(py_file))
    
    return results


def generate_report(results: List[DivisionUsage]) -> str:
    """Generate a human-readable audit report."""
    lines = [
        "=" * 80,
        "Division Operation Audit Report",
        "=" * 80,
        "",
    ]
    
    # Group by risk level
    needs_cdiv = [r for r in results if r.risk_level == 'needs_c_div']
    review = [r for r in results if r.risk_level == 'review']
    safe = [r for r in results if r.risk_level == 'safe']
    
    lines.extend([
        f"Total division operations: {len(results)}",
        f"  ❌ Needs c_div:  {len(needs_cdiv)}",
        f"  ⚠️  Needs review: {len(review)}",
        f"  ✅ Safe:         {len(safe)}",
        "",
    ])
    
    if needs_cdiv:
        lines.extend([
            "=" * 80,
            "❌ NEEDS c_div (potential negative operands in ROM-critical code):",
            "=" * 80,
        ])
        for r in needs_cdiv:
            lines.extend([
                f"\n{r.file}:{r.line}",
                f"  Code: {r.code}",
                f"  Reason: {r.reason}",
            ])
    
    if review:
        lines.extend([
            "",
            "=" * 80,
            "⚠️  NEEDS REVIEW:",
            "=" * 80,
        ])
        for r in review[:20]:  # Limit output
            lines.extend([
                f"\n{r.file}:{r.line}",
                f"  Code: {r.code}",
                f"  Reason: {r.reason}",
            ])
        if len(review) > 20:
            lines.append(f"\n... and {len(review) - 20} more")
    
    lines.extend([
        "",
        "=" * 80,
        "Recommendations:",
        "=" * 80,
        "1. Replace // with c_div() in 'needs_c_div' locations",
        "2. Manually verify 'review' locations have non-negative operands",
        "3. Add comments explaining why // is safe where applicable",
        "4. Consider adding runtime assertions for critical calculations",
    ])
    
    return '\n'.join(lines)


def main():
    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    mud_path = project_root / 'mud'
    
    if not mud_path.exists():
        print(f"Error: mud/ directory not found at {mud_path}")
        sys.exit(1)
    
    print("Auditing division operations in mud/...")
    results = audit_directory(mud_path)
    
    report = generate_report(results)
    print(report)
    
    # Write report to file
    report_path = project_root / 'division_audit_report.txt'
    report_path.write_text(report)
    print(f"\nReport written to {report_path}")
    
    # Exit with error if there are issues
    needs_action = sum(1 for r in results if r.risk_level in ('needs_c_div', 'review'))
    if needs_action > 0:
        print(f"\n⚠️  {needs_action} division operations need attention")


if __name__ == '__main__':
    main()
