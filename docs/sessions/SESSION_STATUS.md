# Session Status — 2026-05-28 — Equipment-key canonicalization + convention guards (2.9.87)

## Current State

- **Last completed**: **Equipment-key canonicalization** (the INV-028 followup)
  ✅ CLOSED (2.9.87). `Character.equipment` is now keyed strictly by
  `int(WearLocation.X)` on every path (new `canonical_wear_slot` resolver applied
  at `equip_object`, `from_orm` restore, and `serializers._slot_to_wear_loc`;
  all readers use the int key; INV-028 per-reader LIGHT shims removed). Fixed two
  real bugs (newbie war-banner light uncounted in room lighting; do_wear shield
  invisible to the combat shield check) and one latent bug (`compare.py` read the
  non-existent `char.equipped` attr). Added two grep-guards
  (`test_equipment_key_convention.py`, `test_attribute_convention.py`) + matching
  pre-commit hooks; reworded the AGENTS.md integer-math rule; filed CLEANUP-001
  (hex flag literals); added CLAUDE.md meta-rules.
- **Active focus**: cross-file invariants pass remains the active mode (per-file
  audit tracker has no Partial/Not-Audited rows). INV-028 is fully closed
  including its broad followup.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-28_EQUIPMENT_KEY_CANONICALIZATION.md](SESSION_SUMMARY_2026-05-28_EQUIPMENT_KEY_CANONICALIZATION.md)
  (predecessor:
  [SESSION_SUMMARY_2026-05-27_INV_028_LIGHT_SLOT.md](SESSION_SUMMARY_2026-05-27_INV_028_LIGHT_SLOT.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.87 |
| Tests | **Full suite: 4894 passed, 4 skipped, 0 failed** in 512s. |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75%. |
| Cross-file invariants | 24 ENFORCED; INV-028 + its broad followup fully closed. |
| Branch | `master` — 3 commits ahead of `origin/master` (3f3570d6 fix, 70f0d87d chore, b1f6d791 docs). Not pushed. |

## Next Intended Task

1. **Push approval** — 3 commits ahead of `origin/master` shipping 2.9.87.
   Verify with `git log origin/master..HEAD`. Not pushed (awaiting approval).
2. **CLEANUP-001** — migrate the ~41 hardcoded hex flag literals to enum
   references (per-site `merc.h` verification), file-by-file. See
   `docs/parity/ROM_PARITY_FEATURE_TRACKER.md`.
3. **`_wear_all` light handling** — `wear all` won't equip a light; ROM's
   `wear all` → `wear_obj` → WEAR_LIGHT would. Minor adjacent gap.
4. **ARITH triage remaining (7 ❌ MISSING)**: ARITH-004, 017/018/019, 114,
   206/207, 208.
5. **GitNexus read-only DB** — `gitnexus_impact`/`detect_changes`/reindex
   unavailable; fix DB perms/lock outside the session.
6. **Pre-existing flake** `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
