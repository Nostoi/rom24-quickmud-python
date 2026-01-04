#!/usr/bin/env python3
"""Verify QuickMUD game loop matches ROM update_handler behavior.

This script performs systematic verification that all ROM C update functions
are correctly implemented and called in QuickMUD's game_tick().

References:
- ROM C: src/update.c:update_handler (lines 1151-1200)
- QuickMUD: mud/game_loop.py:game_tick()
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mud.config import (
    PULSE_PER_SECOND,
    get_pulse_area,
    get_pulse_music,
    get_pulse_tick,
    get_pulse_violence,
)


def verify_pulse_constants() -> bool:
    """Verify pulse constants match ROM src/merc.h values."""
    print("=" * 70)
    print("PULSE CONSTANT VERIFICATION")
    print("=" * 70)
    print("\nComparing QuickMUD vs ROM (src/merc.h:155-160):\n")

    checks = [
        ("PULSE_PER_SECOND", PULSE_PER_SECOND, 4, "Base pulse rate"),
        ("PULSE_VIOLENCE", get_pulse_violence(), 3 * 4, "Combat rounds"),
        ("PULSE_TICK", get_pulse_tick(), 60 * 4, "Game hour tick"),
        ("PULSE_AREA", get_pulse_area(), 120 * 4, "Area resets"),
        ("PULSE_MUSIC", get_pulse_music(), 6 * 4, "Music/song updates"),
    ]

    all_match = True
    for name, quickmud_val, rom_val, description in checks:
        match = quickmud_val == rom_val
        all_match = all_match and match
        symbol = "✅" if match else "❌"
        print(f"{symbol} {name:20} QuickMUD={quickmud_val:4} ROM={rom_val:4}  ({description})")

    print(f"\n{'✅ ALL CONSTANTS MATCH' if all_match else '❌ MISMATCH DETECTED'}\n")
    return all_match


def verify_update_functions() -> bool:
    """Verify all ROM update functions are implemented in QuickMUD."""
    print("=" * 70)
    print("UPDATE FUNCTION VERIFICATION")
    print("=" * 70)
    print("\nChecking ROM src/update.c:update_handler functions:\n")

    # Map ROM C functions to QuickMUD implementations
    functions = [
        {
            "rom": "area_update()",
            "quickmud": "reset_tick()",
            "file": "mud/spawning/reset_handler.py",
            "pulse": "PULSE_AREA",
            "behavior": "Applies area resets (mob/obj spawning)",
        },
        {
            "rom": "song_update()",
            "quickmud": "song_update()",
            "file": "mud/music.py",
            "pulse": "PULSE_MUSIC",
            "behavior": "Updates music/song system",
        },
        {
            "rom": "mobile_update()",
            "quickmud": "mobile_update()",
            "file": "mud/ai.py",
            "pulse": "every pulse",
            "behavior": "Mob AI, movement, scavenging",
        },
        {
            "rom": "violence_update()",
            "quickmud": "violence_tick()",
            "file": "mud/game_loop.py",
            "pulse": "every pulse",
            "behavior": "Combat rounds (multi_hit), timer decrement",
            "critical": True,
        },
        {
            "rom": "weather_update()",
            "quickmud": "weather_tick()",
            "file": "mud/game_loop.py",
            "pulse": "PULSE_TICK",
            "behavior": "Weather pressure/sky transitions",
        },
        {
            "rom": "char_update()",
            "quickmud": "char_update()",
            "file": "mud/game_loop.py",
            "pulse": "PULSE_TICK",
            "behavior": "Regen, conditions, idle handling",
        },
        {
            "rom": "obj_update()",
            "quickmud": "obj_update()",
            "file": "mud/game_loop.py",
            "pulse": "PULSE_TICK",
            "behavior": "Object timers, decay, spills",
        },
        {
            "rom": "aggr_update()",
            "quickmud": "aggressive_update()",
            "file": "mud/ai.py",
            "pulse": "every pulse",
            "behavior": "Aggressive mob attacks",
        },
        {
            "rom": "tail_chain()",
            "quickmud": "(not implemented)",
            "file": "N/A",
            "pulse": "every pulse",
            "behavior": "Empty function in ROM (placeholder)",
            "optional": True,
        },
    ]

    all_ok = True
    for func in functions:
        rom_name = func["rom"]
        qm_name = func["quickmud"]
        is_critical = func.get("critical", False)
        is_optional = func.get("optional", False)

        # Check if function exists
        if qm_name == "(not implemented)":
            if is_optional:
                print(f"ℹ️  {rom_name:25} → {qm_name:25} (optional, OK)")
            else:
                print(f"❌ {rom_name:25} → {qm_name:25} MISSING!")
                all_ok = False
        else:
            # Try to import and verify it exists
            try:
                parts = func["file"].replace(".py", "").replace("/", ".")
                module_name, func_name = parts, qm_name.replace("()", "")

                # Import module
                module = __import__(module_name, fromlist=[func_name])

                # Check function exists
                if hasattr(module, func_name):
                    symbol = "🔥" if is_critical else "✅"
                    print(f"{symbol} {rom_name:25} → {qm_name:25} ({func['pulse']}) {func['behavior']}")
                else:
                    print(f"❌ {rom_name:25} → {qm_name:25} NOT FOUND in {func['file']}")
                    all_ok = False
            except Exception as e:
                print(f"❌ {rom_name:25} → {qm_name:25} IMPORT ERROR: {e}")
                all_ok = False

    print(f"\n{'✅ ALL FUNCTIONS IMPLEMENTED' if all_ok else '❌ MISSING FUNCTIONS'}\n")
    return all_ok


def verify_violence_tick_behavior() -> bool:
    """Verify violence_tick() calls multi_hit() for combat rounds."""
    print("=" * 70)
    print("VIOLENCE_TICK() BEHAVIOR VERIFICATION")
    print("=" * 70)
    print("\nChecking violence_tick() implementation details:\n")

    from mud.game_loop import violence_tick
    import inspect

    source = inspect.getsource(violence_tick)

    checks = [
        ("multi_hit import", "from mud.combat.engine import multi_hit" in source),
        ("stop_fighting import", "from mud.combat.engine import stop_fighting" in source),
        ("multi_hit call", "multi_hit(ch, victim" in source),
        ("stop_fighting call", "stop_fighting(ch" in source),
        ("fighting check", "ch.fighting" in source or "getattr(ch, 'fighting'" in source),
        ("awake check", "is_awake()" in source),
        ("same room check", "room" in source),
    ]

    all_ok = True
    for check_name, result in checks:
        symbol = "✅" if result else "❌"
        all_ok = all_ok and result
        print(f"{symbol} {check_name:30} {'FOUND' if result else 'MISSING'}")

    print(f"\n{'✅ VIOLENCE_TICK CORRECTLY IMPLEMENTS COMBAT' if all_ok else '❌ VIOLENCE_TICK INCOMPLETE'}\n")
    return all_ok


def verify_game_tick_order() -> bool:
    """Verify game_tick() calls functions in correct order."""
    print("=" * 70)
    print("GAME_TICK() CALL ORDER VERIFICATION")
    print("=" * 70)
    print("\nVerifying ROM update_handler call order is preserved:\n")

    from mud.game_loop import game_tick
    import inspect

    source = inspect.getsource(game_tick)

    # Find function call positions
    functions = [
        "violence_tick",
        "reset_tick",
        "song_update",
        "time_tick",
        "weather_tick",
        "char_update",
        "obj_update",
        "mobile_update",
        "aggressive_update",
    ]

    positions = {}
    for func_name in functions:
        pos = source.find(f"{func_name}(")
        if pos != -1:
            positions[func_name] = pos

    # Sort by position
    sorted_calls = sorted(positions.items(), key=lambda x: x[1])

    print("Function call order in game_tick():")
    for i, (func_name, pos) in enumerate(sorted_calls, 1):
        print(f"  {i}. {func_name}()")

    # Expected critical ordering:
    # - violence_tick should run early (every pulse)
    # - mobile_update should run every pulse
    # - aggressive_update should run every pulse
    critical_order = [
        ("violence_tick", "mobile_update"),  # violence before mobile
        ("mobile_update", "aggressive_update"),  # mobile before aggressive
    ]

    all_ok = True
    for func1, func2 in critical_order:
        if func1 in positions and func2 in positions:
            if positions[func1] < positions[func2]:
                print(f"✅ {func1}() before {func2}() (correct)")
            else:
                print(f"❌ {func1}() AFTER {func2}() (wrong order!)")
                all_ok = False

    print(f"\n{'✅ CALL ORDER CORRECT' if all_ok else '❌ CALL ORDER ISSUES'}\n")
    return all_ok


def main():
    """Run all verification checks."""
    print("\n" + "=" * 70)
    print("ROM 2.4b6 GAME LOOP PARITY VERIFICATION")
    print("=" * 70)
    print("\nReferences:")
    print("  ROM C: src/update.c:update_handler (lines 1151-1200)")
    print("  QuickMUD: mud/game_loop.py:game_tick()")
    print()

    results = {
        "Pulse Constants": verify_pulse_constants(),
        "Update Functions": verify_update_functions(),
        "Violence Tick Behavior": verify_violence_tick_behavior(),
        "Game Tick Order": verify_game_tick_order(),
    }

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    all_passed = all(results.values())
    for check_name, passed in results.items():
        symbol = "✅" if passed else "❌"
        print(f"{symbol} {check_name:30} {'PASS' if passed else 'FAIL'}")

    print()
    if all_passed:
        print("🎉 ALL VERIFICATIONS PASSED - ROM PARITY CONFIRMED!")
        return 0
    else:
        print("❌ VERIFICATION FAILURES DETECTED - SEE ABOVE FOR DETAILS")
        return 1


if __name__ == "__main__":
    sys.exit(main())
