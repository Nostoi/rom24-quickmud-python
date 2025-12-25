#!/usr/bin/env python3
"""
Enhanced Parity Analyzer for ROM 2.4 C to Python Port

This script provides comprehensive parity verification between the C source
(src/*.c) and Python implementation (mud/*.py) beyond what test_data_gatherer.py offers.

Gap Analysis Addressed:
1. Formula extraction and comparison
2. Function-level coverage mapping
3. Constant/table verification
4. Numeric edge case identification
5. State machine coverage analysis

Usage:
    python scripts/parity_analyzer.py --all
    python scripts/parity_analyzer.py --functions fight.c
    python scripts/parity_analyzer.py --constants
    python scripts/parity_analyzer.py --formulas
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class CFunction:
    """Represents a C function extracted from source."""
    name: str
    file: str
    line_start: int
    line_end: int
    return_type: str
    params: str
    body_snippet: str = ""
    has_python_equivalent: bool = False
    python_file: Optional[str] = None
    python_function: Optional[str] = None


@dataclass
class Formula:
    """Represents a calculation formula found in code."""
    expression: str
    file: str
    line: int
    language: str  # 'c' or 'python'
    context: str  # surrounding code
    variables: List[str] = field(default_factory=list)


@dataclass
class Constant:
    """Represents a constant/define from C or Python."""
    name: str
    value: str
    file: str
    line: int
    language: str


@dataclass
class ParityReport:
    """Comprehensive parity analysis report."""
    timestamp: str
    functions_analyzed: int = 0
    functions_matched: int = 0
    functions_missing: List[str] = field(default_factory=list)
    formulas_found: int = 0
    formulas_verified: int = 0
    constants_matched: int = 0
    constants_mismatched: List[Tuple[str, str, str]] = field(default_factory=list)
    edge_cases_identified: List[str] = field(default_factory=list)
    coverage_gaps: List[str] = field(default_factory=list)


class CSourceParser:
    """Parses C source files to extract functions, formulas, and constants."""
    
    # ROM-specific function patterns we care about
    CRITICAL_FUNCTIONS = {
        "fight.c": [
            "violence_update", "multi_hit", "one_hit", "damage", 
            "check_parry", "check_dodge", "check_shield_block",
            "raw_kill", "death_cry", "make_corpse", "group_gain",
            "xp_compute", "dam_message", "disarm"
        ],
        "magic.c": [
            "spell_*",  # All spell handlers
            "say_spell", "obj_cast_spell", "saves_spell"
        ],
        "skills.c": [
            "do_*",  # All skill commands
            "check_improve"
        ],
        "update.c": [
            "gain_hit", "gain_mana", "gain_move", 
            "char_update", "obj_update", "aggr_update",
            "violence_update", "weather_update", "area_update"
        ],
        "db.c": [
            "number_mm", "number_range", "number_percent", 
            "number_bits", "number_fuzzy", "dice",
            "reset_room", "reset_area"
        ],
        "handler.c": [
            "affect_to_char", "affect_remove", "affect_strip",
            "char_from_room", "char_to_room", "obj_to_char", "obj_from_char"
        ]
    }
    
    # Patterns for formula detection
    FORMULA_PATTERNS = [
        r'(\w+)\s*=\s*([^;]+(?:\+|\-|\*|\/|%)[^;]+);',  # Arithmetic assignments
        r'if\s*\(\s*([^)]+(?:>|<|>=|<=|==|!=)[^)]+)\)',  # Comparisons
        r'number_range\s*\([^)]+\)',  # RNG calls
        r'dice\s*\([^)]+\)',  # Dice rolls
        r'URANGE\s*\([^)]+\)',  # Clamping
    ]
    
    def __init__(self, src_path: Path):
        self.src_path = src_path
        self.functions: Dict[str, List[CFunction]] = defaultdict(list)
        self.formulas: List[Formula] = []
        self.constants: List[Constant] = []
        
    def parse_all(self) -> None:
        """Parse all C source files."""
        for c_file in self.src_path.glob("*.c"):
            self.parse_file(c_file)
        for h_file in self.src_path.glob("*.h"):
            self.parse_header(h_file)
            
    def parse_file(self, filepath: Path) -> None:
        """Parse a single C source file."""
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"Warning: Could not read {filepath}: {e}")
            return
            
        filename = filepath.name
        lines = content.split('\n')
        
        # Extract functions
        self._extract_functions(filename, content, lines)
        
        # Extract formulas
        self._extract_formulas(filename, content, lines)
        
    def parse_header(self, filepath: Path) -> None:
        """Parse a C header file for constants/defines."""
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return
            
        filename = filepath.name
        lines = content.split('\n')
        
        # Extract #define constants
        define_pattern = re.compile(r'#define\s+(\w+)\s+(.+)')
        for i, line in enumerate(lines, 1):
            match = define_pattern.match(line.strip())
            if match:
                self.constants.append(Constant(
                    name=match.group(1),
                    value=match.group(2).strip(),
                    file=filename,
                    line=i,
                    language="c"
                ))
                
    def _extract_functions(self, filename: str, content: str, lines: List[str]) -> None:
        """Extract function definitions from C source."""
        # Pattern for C function definitions
        func_pattern = re.compile(
            r'^(\w+(?:\s*\*)?)\s+(\w+)\s*\(([^)]*)\)\s*\{',
            re.MULTILINE
        )
        
        for match in func_pattern.finditer(content):
            return_type = match.group(1)
            func_name = match.group(2)
            params = match.group(3)
            
            # Find line number
            line_start = content[:match.start()].count('\n') + 1
            
            # Find closing brace (simplified - doesn't handle nested braces perfectly)
            brace_count = 1
            pos = match.end()
            while pos < len(content) and brace_count > 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1
            line_end = content[:pos].count('\n') + 1
            
            # Extract body snippet (first 10 lines)
            body_start = match.end()
            body_lines = content[body_start:pos].split('\n')[:10]
            body_snippet = '\n'.join(body_lines)
            
            self.functions[filename].append(CFunction(
                name=func_name,
                file=filename,
                line_start=line_start,
                line_end=line_end,
                return_type=return_type,
                params=params,
                body_snippet=body_snippet
            ))
            
    def _extract_formulas(self, filename: str, content: str, lines: List[str]) -> None:
        """Extract calculation formulas from C source."""
        for pattern_str in self.FORMULA_PATTERNS:
            pattern = re.compile(pattern_str)
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                
                # Get context (surrounding lines)
                start_line = max(0, line_num - 2)
                end_line = min(len(lines), line_num + 2)
                context = '\n'.join(lines[start_line:end_line])
                
                # Extract variable names from the formula
                var_pattern = re.compile(r'\b([a-zA-Z_]\w*)\b')
                variables = list(set(var_pattern.findall(match.group(0))))
                
                self.formulas.append(Formula(
                    expression=match.group(0),
                    file=filename,
                    line=line_num,
                    language="c",
                    context=context,
                    variables=variables
                ))


class PythonSourceParser:
    """Parses Python source files for parity comparison."""
    
    def __init__(self, mud_path: Path):
        self.mud_path = mud_path
        self.functions: Dict[str, List[str]] = defaultdict(list)
        self.formulas: List[Formula] = []
        self.constants: List[Constant] = []
        
    def parse_all(self) -> None:
        """Parse all Python source files in mud/."""
        for py_file in self.mud_path.rglob("*.py"):
            self.parse_file(py_file)
            
    def parse_file(self, filepath: Path) -> None:
        """Parse a single Python file."""
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            return
            
        rel_path = str(filepath.relative_to(self.mud_path.parent))
        lines = content.split('\n')
        
        # Extract function definitions
        func_pattern = re.compile(r'^(?:async\s+)?def\s+(\w+)\s*\(', re.MULTILINE)
        for match in func_pattern.finditer(content):
            self.functions[rel_path].append(match.group(1))
            
        # Extract formulas (arithmetic in Python)
        formula_patterns = [
            r'(\w+)\s*=\s*([^#\n]+(?:\+|\-|\*|\/|\/\/|%)[^#\n]+)',  # Arithmetic
            r'c_div\s*\([^)]+\)',  # C-compat division
            r'c_mod\s*\([^)]+\)',  # C-compat modulo
            r'rng_mm\.\w+\s*\([^)]+\)',  # ROM RNG calls
        ]
        
        for pattern_str in formula_patterns:
            pattern = re.compile(pattern_str)
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                self.formulas.append(Formula(
                    expression=match.group(0),
                    file=rel_path,
                    line=line_num,
                    language="python",
                    context=lines[max(0, line_num-2):min(len(lines), line_num+2)]
                ))
                
        # Extract constants (UPPER_CASE assignments)
        const_pattern = re.compile(r'^([A-Z][A-Z0-9_]+)\s*=\s*(.+)', re.MULTILINE)
        for match in const_pattern.finditer(content):
            self.constants.append(Constant(
                name=match.group(1),
                value=match.group(2).strip(),
                file=rel_path,
                line=content[:match.start()].count('\n') + 1,
                language="python"
            ))


class ParityAnalyzer:
    """Main analyzer that compares C and Python implementations."""
    
    # Known mappings from C files to Python files
    FILE_MAPPINGS = {
        "fight.c": ["mud/combat/engine.py"],
        "magic.c": ["mud/skills/handlers.py"],
        "magic2.c": ["mud/skills/handlers.py"],
        "skills.c": ["mud/skills/handlers.py", "mud/skills/registry.py"],
        "update.c": ["mud/game_loop.py"],
        "db.c": ["mud/loaders/area_loader.py", "mud/spawning/reset_handler.py", "mud/utils.py"],
        "handler.c": ["mud/affects/saves.py", "mud/models/character.py"],
        "act_move.c": ["mud/world/movement.py", "mud/commands/movement.py"],
        "act_comm.c": ["mud/commands/communication.py"],
        "act_obj.c": ["mud/commands/inventory.py", "mud/commands/shop.py"],
        "act_wiz.c": ["mud/wiznet.py", "mud/commands/admin_commands.py"],
        "mob_prog.c": ["mud/mobprog.py"],
        "mob_cmds.c": ["mud/mob_cmds.py"],
        "olc_save.c": ["mud/olc/save.py"],
        "special.c": ["mud/spec_funs.py"],
        "save.c": ["mud/persistence.py"],
        "effects.c": ["mud/affects/saves.py"],
        "tables.c": ["mud/models/constants.py"],
        "const.c": ["mud/models/constants.py"],
    }
    
    # Known function name mappings (C name -> Python name)
    FUNCTION_MAPPINGS = {
        "do_recall": "spell_recall",
        "spell_acid_blast": "acid_blast",
        "check_improve": "_check_improve",
        "saves_spell": "saves_spell",
        "number_range": "number_range",
        "number_percent": "number_percent",
        "number_mm": "number_mm",
        "dice": "dice",
    }
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.c_parser = CSourceParser(project_root / "src")
        self.py_parser = PythonSourceParser(project_root / "mud")
        self.report = ParityReport(timestamp=datetime.now().isoformat())
        
    def analyze_all(self) -> ParityReport:
        """Run comprehensive parity analysis."""
        print("Parsing C source files...")
        self.c_parser.parse_all()
        
        print("Parsing Python source files...")
        self.py_parser.parse_all()
        
        print("\nAnalyzing function coverage...")
        self._analyze_function_coverage()
        
        print("Analyzing formula parity...")
        self._analyze_formula_parity()
        
        print("Analyzing constant parity...")
        self._analyze_constant_parity()
        
        print("Identifying edge cases...")
        self._identify_edge_cases()
        
        return self.report
        
    def _analyze_function_coverage(self) -> None:
        """Compare C functions to Python implementations."""
        for c_file, funcs in self.c_parser.functions.items():
            py_files = self.FILE_MAPPINGS.get(c_file, [])
            
            for func in funcs:
                self.report.functions_analyzed += 1
                
                # Check if this is a critical function we should track
                is_critical = False
                for pattern in self.c_parser.CRITICAL_FUNCTIONS.get(c_file, []):
                    if pattern.endswith("*"):
                        if func.name.startswith(pattern[:-1]):
                            is_critical = True
                            break
                    elif func.name == pattern:
                        is_critical = True
                        break
                
                # Look for Python equivalent
                py_name = self.FUNCTION_MAPPINGS.get(func.name, func.name)
                found = False
                
                for py_file in py_files:
                    if py_file in self.py_parser.functions:
                        if py_name in self.py_parser.functions[py_file]:
                            found = True
                            func.has_python_equivalent = True
                            func.python_file = py_file
                            func.python_function = py_name
                            break
                        # Also check for snake_case conversion
                        snake_name = self._to_snake_case(func.name)
                        if snake_name in self.py_parser.functions[py_file]:
                            found = True
                            func.has_python_equivalent = True
                            func.python_file = py_file
                            func.python_function = snake_name
                            break
                            
                if found:
                    self.report.functions_matched += 1
                elif is_critical:
                    self.report.functions_missing.append(f"{c_file}:{func.name}")
                    
    def _analyze_formula_parity(self) -> None:
        """Compare calculation formulas between C and Python."""
        self.report.formulas_found = len(self.c_parser.formulas) + len(self.py_parser.formulas)
        
        # Look for ROM-specific formulas that must match
        critical_formulas = [
            "number_range",
            "number_percent",
            "dice",
            "URANGE",
            "saves_spell",
            "get_skill",
        ]
        
        for formula in self.c_parser.formulas:
            for crit in critical_formulas:
                if crit in formula.expression:
                    # Check if there's a corresponding Python formula
                    py_matches = [
                        f for f in self.py_parser.formulas
                        if crit.lower() in f.expression.lower() or 
                           crit.replace("_", "") in f.expression.lower()
                    ]
                    if py_matches:
                        self.report.formulas_verified += 1
                    else:
                        self.report.coverage_gaps.append(
                            f"C formula '{formula.expression}' in {formula.file}:{formula.line} "
                            f"may be missing Python equivalent"
                        )
                        
    def _analyze_constant_parity(self) -> None:
        """Compare constants between C and Python."""
        c_constants = {c.name: c for c in self.c_parser.constants}
        py_constants = {c.name: c for c in self.py_parser.constants}
        
        # Critical constants that must match
        critical_constants = [
            "PULSE_VIOLENCE", "PULSE_TICK", "PULSE_PER_SECOND",
            "MAX_LEVEL", "LEVEL_HERO", "LEVEL_IMMORTAL",
            "WEAR_NONE", "WEAR_FINGER_L", "WEAR_FINGER_R",
            "AFF_BLIND", "AFF_INVISIBLE", "AFF_DETECT_EVIL",
            "ACT_IS_NPC", "ACT_SENTINEL", "ACT_AGGRESSIVE",
            "STAT_STR", "STAT_INT", "STAT_WIS", "STAT_DEX", "STAT_CON",
        ]
        
        for const_name in critical_constants:
            if const_name in c_constants:
                if const_name in py_constants:
                    # Compare values (simplified - doesn't handle expressions)
                    c_val = c_constants[const_name].value
                    py_val = py_constants[const_name].value
                    if c_val != py_val:
                        # Check if they're numerically equivalent
                        try:
                            if int(c_val, 0) != int(py_val, 0):
                                self.report.constants_mismatched.append(
                                    (const_name, c_val, py_val)
                                )
                            else:
                                self.report.constants_matched += 1
                        except ValueError:
                            # Can't compare, might be expression
                            pass
                    else:
                        self.report.constants_matched += 1
                else:
                    self.report.coverage_gaps.append(
                        f"C constant {const_name} not found in Python"
                    )
                    
    def _identify_edge_cases(self) -> None:
        """Identify potential edge cases that need testing."""
        edge_cases = []
        
        # Look for C division that might differ from Python
        for formula in self.c_parser.formulas:
            expr = formula.expression
            
            # Integer division edge cases
            if "/" in expr and "c_div" not in expr:
                if any(neg in expr for neg in ["-", "victim", "damage", "level"]):
                    edge_cases.append(
                        f"Potential C/Python division difference: {formula.file}:{formula.line} "
                        f"'{expr}' - verify negative number handling"
                    )
                    
            # Modulo edge cases
            if "%" in expr:
                edge_cases.append(
                    f"Modulo operation: {formula.file}:{formula.line} "
                    f"'{expr}' - verify uses c_mod for negative operands"
                )
                
            # Bit operations
            if "|" in expr or "&" in expr or "<<" in expr or ">>" in expr:
                edge_cases.append(
                    f"Bit operation: {formula.file}:{formula.line} "
                    f"'{expr}' - verify bit width (32-bit C vs 64-bit Python)"
                )
                
        self.report.edge_cases_identified = edge_cases[:20]  # Limit output
        
    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase or UPPER_CASE to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        
    def generate_report(self) -> str:
        """Generate a human-readable report."""
        r = self.report
        lines = [
            "=" * 80,
            "ROM 2.4 C to Python Parity Analysis Report",
            f"Generated: {r.timestamp}",
            "=" * 80,
            "",
            "## Function Coverage",
            f"  Functions analyzed: {r.functions_analyzed}",
            f"  Functions matched:  {r.functions_matched}",
            f"  Match rate:         {r.functions_matched/max(1,r.functions_analyzed)*100:.1f}%",
            "",
        ]
        
        if r.functions_missing:
            lines.append("  Missing critical functions:")
            for f in r.functions_missing[:20]:
                lines.append(f"    - {f}")
            if len(r.functions_missing) > 20:
                lines.append(f"    ... and {len(r.functions_missing)-20} more")
        lines.append("")
        
        lines.extend([
            "## Formula Analysis",
            f"  Formulas found:    {r.formulas_found}",
            f"  Formulas verified: {r.formulas_verified}",
            "",
            "## Constants",
            f"  Constants matched:    {r.constants_matched}",
            f"  Constants mismatched: {len(r.constants_mismatched)}",
        ])
        
        if r.constants_mismatched:
            lines.append("  Mismatches:")
            for name, c_val, py_val in r.constants_mismatched:
                lines.append(f"    - {name}: C={c_val}, Python={py_val}")
        lines.append("")
        
        if r.edge_cases_identified:
            lines.extend([
                "## Edge Cases Identified (need testing)",
            ])
            for ec in r.edge_cases_identified:
                lines.append(f"  - {ec}")
            lines.append("")
            
        if r.coverage_gaps:
            lines.extend([
                "## Coverage Gaps",
            ])
            for gap in r.coverage_gaps[:20]:
                lines.append(f"  - {gap}")
            if len(r.coverage_gaps) > 20:
                lines.append(f"  ... and {len(r.coverage_gaps)-20} more")
        lines.append("")
        
        lines.extend([
            "=" * 80,
            "Recommendations:",
            "1. Add differential tests for missing critical functions",
            "2. Verify edge cases with seeded RNG comparison",
            "3. Add golden file tests for constant values",
            "4. Run C binary alongside Python for behavioral comparison",
            "=" * 80,
        ])
        
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ROM Parity Analyzer")
    parser.add_argument("--all", action="store_true", help="Run full analysis")
    parser.add_argument("--functions", type=str, help="Analyze specific C file")
    parser.add_argument("--constants", action="store_true", help="Analyze constants only")
    parser.add_argument("--formulas", action="store_true", help="Analyze formulas only")
    parser.add_argument("--output", "-o", type=str, help="Output file for report")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    if not (project_root / "src").exists():
        print(f"Error: C source directory not found at {project_root / 'src'}")
        sys.exit(1)
        
    if not (project_root / "mud").exists():
        print(f"Error: Python source directory not found at {project_root / 'mud'}")
        sys.exit(1)
        
    analyzer = ParityAnalyzer(project_root)
    report = analyzer.analyze_all()
    
    if args.json:
        output = json.dumps({
            "timestamp": report.timestamp,
            "functions_analyzed": report.functions_analyzed,
            "functions_matched": report.functions_matched,
            "functions_missing": report.functions_missing,
            "formulas_found": report.formulas_found,
            "formulas_verified": report.formulas_verified,
            "constants_matched": report.constants_matched,
            "constants_mismatched": report.constants_mismatched,
            "edge_cases": report.edge_cases_identified,
            "coverage_gaps": report.coverage_gaps,
        }, indent=2)
    else:
        output = analyzer.generate_report()
        
    if args.output:
        Path(args.output).write_text(output)
        print(f"Report written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
