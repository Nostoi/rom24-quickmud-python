# Session Status — 2026-06-12 — INV-046 PHANTOM-REGISTRY fully closed (✅ ENFORCED)

## Current State

- **Active focus**: INV-046 (PHANTOM-REGISTRY) — ✅ ENFORCED (all families 1, 2, Layer-A, 3a, 3b closed)
- **Last completed**: INV-046 family 3b — all phantom stat-table aliases rewired to real backing structures; Layer-A guard extended to all 13 phantom names (v2.14.21)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_INV046_FAMILY_3B.md](SESSION_SUMMARY_2026-06-12_INV046_FAMILY_3B.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.21 |
| Tests | 5655 passed / 4 skipped |
| INV-046 family 3b tests | 11 / 11 passing |
| INV-046 status | ✅ ENFORCED — phantom-registry bug class fully closed + grep-guarded |
| Active focus | Cross-file invariants pass (per-file audit tracker exhausted) |

## Next Intended Task

INV-046 is fully closed; the phantom-registry bug class is locked by the Layer-A guard
(`tests/test_phantom_registry_convention.py`, all 13 phantom names). Pick up the cross-file
invariants pass:

1. **File WIZ-051** in `docs/parity/ACT_WIZ_C_AUDIT.md` — `find_location` in `imm_commands.py`
   falls back to `get_obj_world` for object vnums but the world-object fallback is missing — then
   close it via `/rom-gap-closer`.
2. **Diagnose the two xdist flakes** — `test_ac_clamping_for_negative_values` and
   `test_hpcnt_fires_exactly_once_per_violence_tick` flaked under `-n auto` in an earlier session
   (did not recur this session). Isolate with `-n0`, reproduce with `-n auto`.
3. Resume probing for the next cross-file invariant: mob memory (`src/fight.c` ATTACK_BACK / hunt),
   `weather_update` message fan-out order, `update_handler` pulse cadence vs the Python tick
   scheduler. Use the probe-then-scope method (read ROM C contract → read Python equivalent →
   one failing test), file as the next free INV-NNN or close as a single gap.

**Process reminder:** after every phantom-class / list-walk fix, re-grep the whole `mud/` tree
before trusting a hand-built site inventory — family 3a's inventory missed 2 sites that the
family-3b post-fix re-grep caught.
