# Session Status — 2026-06-10 — Follow Helpers Dedup (2.13.82)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **`group_commands.py` stale follow-helper dedup** — deleted local
    `add_follower`/`stop_follower` redefinitions from
    `mud/commands/group_commands.py`; both now imported from the canonical
    `mud.characters.follow`. The local `stop_follower` only bit-cleared `affected_by`
    without calling `remove_spell_effect("charm person")` (diverging from ROM
    `affect_strip`); the local `add_follower` silently returned early on any
    non-None master. Charm-strip path unreachable via `do_follow` (charmed chars
    blocked by guard), so filed as a dedup rather than a new INV.
  - **`tests/test_follow_canonical.py`** — Layer-A grep-guard (2 tests): bans
    local redefinitions of both helpers in `group_commands.py` and asserts the
    canonical import.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_FOLLOW_HELPERS_DEDUP.md](SESSION_SUMMARY_2026-06-10_FOLLOW_HELPERS_DEDUP.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.82 |
| Tests | 5548 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 26 enforced (next free ID: INV-042) |
| Diff-harness scenarios | 40 scenarios, 67 C-oracle tests passing, 0 skipped, 0 xfailed |
| FINDINGS.md highest ID | FINDING-033 (✅ RESOLVED — all findings resolved) |

## Next Intended Task

Cross-file invariants remains the active pass.

1. **Affect-tick contracts** — ROM `src/update.c:762-786` duration-decay loop.
   The RNG short-circuit evaluation order (GL-026) and LIFO expiry-message rule
   (only last-of-type emits `msg_off`) deserve cross-INV enforcement tests even
   though the Python implementation already looks correct. Probe method: ROM C
   contract → Python `mud/affects/engine.py` → one failing test → INV-042 or gap-
   closer commit.

2. **Position-transition edges** — `update_pos` after `stop_fighting`; Python
   already matches ROM but no cross-INV lock exists.

3. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.
