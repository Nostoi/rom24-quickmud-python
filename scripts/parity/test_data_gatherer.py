#!/usr/bin/env python3
"""
Test Data Gatherer for AGENT.md

Runs pytest for specific subsystems and extracts pass/fail metrics
to help update confidence scores with real test data.
"""

import glob
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Subsystem to test file mapping
SUBSYSTEM_TEST_MAP = {
    "combat": [
        "tests/test_combat*.py",
        "tests/test_weapon*.py",
        "tests/test_damage*.py",
        "tests/test_fighting_state.py",
    ],
    "skills_spells": [
        "tests/test_skills*.py",
        "tests/test_spells*.py",
        "tests/test_spell_*.py",
        "tests/test_skill_*.py",
        "tests/test_passive_skills*.py",
        "tests/test_practice.py",
        "tests/test_advancement.py",
    ],
    "affects_saves": [
        "tests/test_affects.py",
        "tests/test_defense_flags.py",
        "tests/test_damage_reduction*.py",
    ],
    "command_interpreter": [
        "tests/test_commands.py",
        "tests/test_command_abbrev.py",
    ],
    "socials": [
        "tests/test_social*.py",
    ],
    "channels": [
        "tests/test_communication.py",
    ],
    "wiznet_imm": [
        "tests/test_wiznet.py",
    ],
    "world_loader": [
        "tests/test_area*.py",
        "tests/test_world.py",
        "tests/test_load_midgaard.py",
        "tests/test_json_room*.py",
        "tests/test_json_model*.py",
        "tests/test_runtime_models.py",
    ],
    "resets": [
        "tests/test_reset*.py",
        "tests/test_spawning.py",
    ],
    "weather": [
        "tests/test_game_loop.py",
    ],
    "time_daynight": [
        "tests/test_time*.py",
    ],
    "movement_encumbrance": [
        "tests/test_movement*.py",
        "tests/test_encumbrance.py",
        "tests/test_enter_portal.py",
    ],
    "stats_position": [
        "tests/test_advancement.py",
    ],
    "shops_economy": [
        "tests/test_shop*.py",
        "tests/test_healer.py",
    ],
    "boards_notes": [
        "tests/test_boards.py",
    ],
    "help_system": [
        "tests/test_help*.py",
    ],
    "mob_programs": [
        "tests/test_mobprog*.py",
    ],
    "npc_spec_funs": [
        "tests/test_spec_funs*.py",
        "tests/test_specials*.py",
    ],
    "game_update_loop": [
        "tests/test_game_loop*.py",
    ],
    "persistence": [
        "tests/test_persistence.py",
        "tests/test_inventory_persistence.py",
        "tests/test_player_save*.py",
        "tests/test_time_persistence.py",
        "tests/test_db_seed.py",
    ],
    "login_account_nanny": [
        "tests/test_account*.py",
        "tests/test_connection_motd.py",
    ],
    "networking_telnet": [
        "tests/test_telnet*.py",
        "tests/test_networking*.py",
    ],
    "security_auth_bans": [
        "tests/test_bans.py",
        "tests/test_admin_commands.py",
        "tests/test_hash_utils.py",
    ],
    "logging_admin": [
        "tests/test_logging*.py",
    ],
    "olc_builders": [
        "tests/test_building.py",
        "tests/test_olc_*.py",
        "tests/test_builder_*.py",
    ],
    "area_format_loader": [
        "tests/test_area_loader.py",
        "tests/test_are_conversion.py",
        "tests/test_convert_are*.py",
        "tests/test_schema_validation.py",
    ],
    "imc_chat": [
        "tests/test_imc.py",
    ],
    "player_save_format": [
        "tests/test_player_save_format.py",
        "tests/test_persistence.py",
    ],
    "command_coverage": [
        "tests/test_command_parity.py",
    ],
}


def run_pytest(patterns: List[str], verbose: bool = False) -> Tuple[int, int, int, str]:
    """
    Run pytest with given file patterns.

    Returns:
        (passed, failed, total, output)
    """
    expanded: List[str] = []
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            expanded.extend(sorted(matches))
    if not expanded:
        return 0, 0, 0, f"NO_MATCH: {', '.join(patterns)}"
    cmd = ["pytest"] + expanded
    if verbose:
        cmd.append("-v")
    cmd.extend(["--tb=short", "-q"])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        output = result.stdout + result.stderr

        # Parse output for results
        # Look for: "N passed, M failed in X.XXs"
        match = re.search(r"(\d+) passed(?:, (\d+) failed)?", output)
        if match:
            passed = int(match.group(1))
            failed = int(match.group(2)) if match.group(2) else 0
            total = passed + failed
            return passed, failed, total, output

        # No tests collected
        if "no tests ran" in output.lower() or "collected 0 items" in output.lower():
            return 0, 0, 0, output

        # Collection errors
        if "error" in output.lower():
            return 0, 0, 0, output

        return 0, 0, 0, output

    except subprocess.TimeoutExpired:
        return 0, 0, 0, "TIMEOUT: Tests took >5 minutes"
    except Exception as e:
        return 0, 0, 0, f"ERROR: {e}"


def calculate_confidence(passed: int, total: int) -> float:
    """
    Calculate confidence score from test pass rate.

    100% pass → 0.95 (some integration risk remains)
    95-99% pass → 0.85
    90-94% pass → 0.75
    80-89% pass → 0.65
    70-79% pass → 0.55
    <70% pass → 0.40 or lower
    """
    if total == 0:
        return 0.20  # No tests = very low confidence

    pass_rate = passed / total

    if pass_rate == 1.0:
        return 0.95
    elif pass_rate >= 0.95:
        return 0.85
    elif pass_rate >= 0.90:
        return 0.75
    elif pass_rate >= 0.80:
        return 0.65
    elif pass_rate >= 0.70:
        return 0.55
    else:
        return max(0.20, pass_rate * 0.60)


def analyze_subsystem(subsystem: str, verbose: bool = False) -> Dict:
    """
    Run tests for a specific subsystem and return metrics.
    """
    if subsystem not in SUBSYSTEM_TEST_MAP:
        return {
            "subsystem": subsystem,
            "error": f"Unknown subsystem: {subsystem}",
        }

    patterns = SUBSYSTEM_TEST_MAP[subsystem]
    print(f"\n{'=' * 80}")
    print(f"Testing subsystem: {subsystem}")
    print(f"Test patterns: {', '.join(patterns)}")
    print(f"{'=' * 80}\n")

    passed, failed, total, output = run_pytest(patterns, verbose=verbose)
    confidence = calculate_confidence(passed, total)

    return {
        "subsystem": subsystem,
        "passed": passed,
        "failed": failed,
        "total": total,
        "pass_rate": passed / total if total > 0 else 0.0,
        "confidence": confidence,
        "timestamp": datetime.now().isoformat(),
        "output": output if verbose else output[-500:],  # Last 500 chars if not verbose
    }


def analyze_all_subsystems(verbose: bool = False) -> Dict[str, Dict]:
    """
    Run tests for all subsystems and return comprehensive metrics.
    """
    results = {}

    for subsystem in SUBSYSTEM_TEST_MAP.keys():
        result = analyze_subsystem(subsystem, verbose=verbose)
        results[subsystem] = result

        # Print summary
        if "error" in result:
            print(f"❌ {subsystem}: {result['error']}")
        else:
            print(
                f"{'✅' if result['passed'] == result['total'] else '⚠️'} "
                f"{subsystem}: {result['passed']}/{result['total']} tests passed "
                f"({result['pass_rate'] * 100:.1f}%) → confidence {result['confidence']:.2f}"
            )

    return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Gather test data for confidence scoring")
    parser.add_argument("subsystem", nargs="?", help="Specific subsystem to test (optional)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-o", "--output", help="Save results to JSON file")
    parser.add_argument("--all", action="store_true", help="Test all subsystems")

    args = parser.parse_args()

    if args.all or not args.subsystem:
        results = analyze_all_subsystems(verbose=args.verbose)

        # Print summary
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}\n")

        total_passed = sum(r.get("passed", 0) for r in results.values() if "error" not in r)
        total_tests = sum(r.get("total", 0) for r in results.values() if "error" not in r)
        avg_confidence = sum(r.get("confidence", 0) for r in results.values() if "error" not in r) / len(results)

        print(f"Total tests: {total_passed}/{total_tests} passed ({total_passed / total_tests * 100:.1f}%)")
        print(f"Average confidence: {avg_confidence:.2f}")
        print(f"\nSubsystems ≥0.80 confidence: {sum(1 for r in results.values() if r.get('confidence', 0) >= 0.80)}")
        print(f"Subsystems <0.80 confidence: {sum(1 for r in results.values() if r.get('confidence', 0) < 0.80)}")

    else:
        results = analyze_subsystem(args.subsystem, verbose=args.verbose)
        if "error" not in results:
            print(f"\n{'=' * 80}")
            print(f"Results for {args.subsystem}:")
            print(f"  Tests: {results['passed']}/{results['total']} passed ({results['pass_rate'] * 100:.1f}%)")
            print(f"  Confidence: {results['confidence']:.2f}")
            print(f"{'=' * 80}\n")

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
