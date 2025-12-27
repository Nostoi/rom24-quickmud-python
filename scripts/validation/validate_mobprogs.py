#!/usr/bin/env python3
"""
Validate MobProgs in ROM area files for QuickMUD parity testing.

Usage:
    python3 scripts/validate_mobprogs.py area/*.are
    python3 scripts/validate_mobprogs.py area/midgaard.are --verbose
    python3 scripts/validate_mobprogs.py area/*.are --test-execute
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mud.loaders.area_loader import load_area_file
from mud.mobprog import Trigger, register_program_code, run_prog
from mud.models.character import Character, character_registry


def validate_area_mobprogs(area_file: Path, verbose: bool = False, test_execute: bool = False) -> dict:
    """
    Validate all MobProgs in an area file.
    
    Returns:
        dict with validation results
    """
    results = {
        "area": area_file.name,
        "total_mobs": 0,
        "programmed_mobs": 0,
        "total_programs": 0,
        "valid_programs": 0,
        "invalid_programs": 0,
        "errors": [],
        "warnings": [],
        "movement_progs": 0,  # Track programs with movement commands
    }
    
    try:
        # Load area file
        if verbose:
            print(f"\n📂 Loading {area_file.name}...")
        
        area = load_area_file(str(area_file))
        
        # Find all mobs with programs
        programmed_mobs = []
        for vnum, mob_idx in character_registry.items():
            results["total_mobs"] += 1
            if hasattr(mob_idx, "mob_programs") and mob_idx.mob_programs:
                programmed_mobs.append((vnum, mob_idx))
                results["programmed_mobs"] += 1
        
        if verbose:
            print(f"   Found {results['programmed_mobs']} mobs with programs (out of {results['total_mobs']} total)")
        
        # Validate each program
        for vnum, mob_idx in programmed_mobs:
            if verbose:
                print(f"\n   🤖 Mob {vnum}: {mob_idx.name}")
            
            for prog in mob_idx.mob_programs:
                results["total_programs"] += 1
                
                # Check 1: Valid trigger type
                valid_trigger = False
                try:
                    trigger = Trigger(prog.trig_type)
                    valid_trigger = True
                    if verbose:
                        print(f"      ✅ Program {prog.vnum}: {trigger.name} trigger")
                except ValueError:
                    results["errors"].append(
                        f"Mob {vnum} program {prog.vnum}: Invalid trigger type {prog.trig_type}"
                    )
                    results["invalid_programs"] += 1
                    if verbose:
                        print(f"      ❌ Program {prog.vnum}: INVALID trigger type {prog.trig_type}")
                    continue
                
                # Check 2: Non-empty code
                if not prog.code or not prog.code.strip():
                    results["warnings"].append(
                        f"Mob {vnum} program {prog.vnum}: Empty code block"
                    )
                    if verbose:
                        print(f"      ⚠️  Program {prog.vnum}: Empty code")
                
                # Check 3: Code syntax (basic check for if/endif pairing)
                code_lines = prog.code.strip().split("\n")
                if_count = sum(1 for line in code_lines if line.strip().startswith("if "))
                endif_count = sum(1 for line in code_lines if line.strip() == "endif")
                if if_count != endif_count:
                    results["warnings"].append(
                        f"Mob {vnum} program {prog.vnum}: Unmatched if/endif ({if_count} ifs, {endif_count} endifs)"
                    )
                    if verbose:
                        print(f"      ⚠️  Program {prog.vnum}: Unmatched if/endif")
                
                # Check 4: Mob movement commands validation
                movement_commands = ["mob goto", "mpgoto", "mob transfer", "mptransfer"]
                has_movement = any(cmd in prog.code.lower() for cmd in movement_commands)
                if has_movement:
                    results["movement_progs"] += 1
                    # Check if movement commands have valid room vnums (digits)
                    for line in code_lines:
                        line_lower = line.strip().lower()
                        if "mob goto" in line_lower or "mpgoto" in line_lower:
                            # Extract potential room vnum
                            parts = line.strip().split()
                            if len(parts) >= 3:  # e.g., "mob goto 3001"
                                potential_vnum = parts[-1]
                                if not potential_vnum.isdigit() and not potential_vnum.startswith("$"):
                                    results["warnings"].append(
                                        f"Mob {vnum} program {prog.vnum}: mpgoto with non-numeric/non-variable target: {potential_vnum}"
                                    )
                                    if verbose:
                                        print(f"      ⚠️  Program {prog.vnum}: Suspicious mpgoto target")
                
                # Check 5: Test execution (smoke test)
                if test_execute and valid_trigger:
                    try:
                        # Create test mob instance
                        mob = Character.from_index(mob_idx)
                        mob.name = mob_idx.name  # Ensure name is set
                        
                        # Try to execute (won't do anything without actor, but tests parsing)
                        execution_results = run_prog(
                            mob,
                            trigger,
                            actor=None,
                            phrase=prog.trig_phrase or "test",
                        )
                        
                        if verbose:
                            print(f"      ✅ Program {prog.vnum}: Executes without crash ({len(execution_results)} actions)")
                        
                        results["valid_programs"] += 1
                        
                    except Exception as e:
                        results["errors"].append(
                            f"Mob {vnum} program {prog.vnum}: Execution error: {e}"
                        )
                        results["invalid_programs"] += 1
                        if verbose:
                            print(f"      ❌ Program {prog.vnum}: CRASH on execution: {e}")
                else:
                    # Without execution test, count valid trigger as valid program
                    if valid_trigger:
                        results["valid_programs"] += 1
        
    except Exception as e:
        results["errors"].append(f"Failed to load area: {e}")
        if verbose:
            print(f"   ❌ Error loading area: {e}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Validate MobProgs in ROM area files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s area/*.are
  %(prog)s area/midgaard.are --verbose
  %(prog)s area/*.are --test-execute --verbose
        """,
    )
    parser.add_argument("area_files", nargs="+", type=Path, help="Area files to validate")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "-t", "--test-execute", action="store_true", help="Test execute programs (smoke test)"
    )
    
    args = parser.parse_args()
    
    # Validate each area file
    all_results = []
    for area_file in args.area_files:
        if not area_file.exists():
            print(f"❌ File not found: {area_file}")
            continue
        
        results = validate_area_mobprogs(area_file, args.verbose, args.test_execute)
        all_results.append(results)
    
    # Summary report
    print("\n" + "=" * 80)
    print("📊 MOBPROG VALIDATION SUMMARY")
    print("=" * 80)
    
    total_areas = len(all_results)
    total_mobs = sum(r["total_mobs"] for r in all_results)
    total_programmed = sum(r["programmed_mobs"] for r in all_results)
    total_programs = sum(r["total_programs"] for r in all_results)
    total_valid = sum(r["valid_programs"] for r in all_results)
    total_invalid = sum(r["invalid_programs"] for r in all_results)
    total_errors = sum(len(r["errors"]) for r in all_results)
    total_movement = sum(r["movement_progs"] for r in all_results)
    
    print(f"\nAreas Scanned:      {total_areas}")
    print(f"Total Mobs:         {total_mobs}")
    if total_mobs > 0:
        print(f"Programmed Mobs:    {total_programmed} ({total_programmed/total_mobs*100:.1f}%)")
    else:
        print(f"Programmed Mobs:    {total_programmed}")
    print(f"Total Programs:     {total_programs}")
    if total_programs > 0:
        print(f"Valid Programs:     {total_valid} ({total_valid/total_programs*100:.1f}%)")
        print(f"Movement Programs:  {total_movement} ({total_movement/total_programs*100:.1f}%)")
    else:
        print(f"Valid Programs:     {total_valid}")
        print(f"Movement Programs:  {total_movement}")
    print(f"Invalid Programs:   {total_invalid}")
    print(f"Errors:             {total_errors}")
    print(f"Warnings:           {total_warnings}")
    
    # Per-area breakdown
    if args.verbose or total_areas > 1:
        print("\n" + "-" * 80)
        print("Per-Area Breakdown:")
        print("-" * 80)
        for r in all_results:
            status = "✅" if r["invalid_programs"] == 0 and not r["errors"] else "⚠️"
            print(f"{status} {r['area']:30} {r['programmed_mobs']:3} mobs, {r['total_programs']:3} progs, {r['valid_programs']:3} valid")
    
    # Error details
    if total_errors > 0:
        print("\n" + "-" * 80)
        print("❌ ERRORS:")
        print("-" * 80)
        for r in all_results:
            if r["errors"]:
                print(f"\n{r['area']}:")
                for error in r["errors"]:
                    print(f"  - {error}")
    
    # Warning details
    if total_warnings > 0 and args.verbose:
        print("\n" + "-" * 80)
        print("⚠️  WARNINGS:")
        print("-" * 80)
        for r in all_results:
            if r["warnings"]:
                print(f"\n{r['area']}:")
                for warning in r["warnings"]:
                    print(f"  - {warning}")
    
    # Exit code
    if total_invalid > 0 or total_errors > 0:
        print("\n❌ Validation FAILED")
        return 1
    else:
        print("\n✅ Validation PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
