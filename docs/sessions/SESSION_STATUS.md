# Session Status — 2026-05-30 — Test Flake Fix and Invariant Probe

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Test stabilization (2.11.54)** — `test_combat_death.py` xdist flake
    fixed: added `number_bits(5)` monkeypatch to 11 `attack_round`-using
    tests that lacked it (root cause: FIGHT-019 THAC0 model uses
    `number_bits(5)` for hit rolls, not `number_percent`).
  - **Invariant probe**: `add_follower` ROM contract (Python diverges
    defensively; not a parity bug) and `Character.pet` type annotation
    (should be `MobInstance | None`; noted for future type hygiene).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-30_TEST_FLAKE_FIX_AND_INV_PROBE.md](SESSION_SUMMARY_2026-05-30_TEST_FLAKE_FIX_AND_INV_PROBE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.54 |
| Tests | 23/23 `test_combat_death.py` (previously flaky) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Active focus | Cross-file invariants — continue probe/close cycle |

## Next Intended Task

Continue cross-file invariants as the primary pass. Probed areas:
- `add_follower` / `Character.pet` — no gap filed (defensive divergence +
  type hygiene, not parity bugs).
- Remaining candidate areas for probing: NPC shop PCHAR flag integrity,
  area reset `nplayer` accounting (INV-010 covers room-people side;
  area-level decrement on PC death/quit is tested), or per-spell
  handler Object branches (bless/curse/poison/etc.).

Carried-open items: `test_backstab_uses_position_and_weapon` xdist flake
(not `number_bits`-related); `Character.pet` type annotation hygiene
(`Character | None` → `MobInstance | None`); per-spell handler Object
branches.

## Commit / push state

- Working tree: clean (all changes included in the 2.11.54 commit).