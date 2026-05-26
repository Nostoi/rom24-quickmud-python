# Session Status — 2026-05-26 — META_AUDIT_TAXONOMY + rom_api.py deletion (2.9.21)

## Current State

- **New parity-strategy layer**: `docs/parity/META_AUDIT_TAXONOMY.md`
  filed (8-class umbrella covering BROADCAST_COVERAGE,
  ARITHMETIC_BOUNDARY, GATE_CONSISTENCY, TRIGGER_CALL_SITE_MIGRATION,
  LIFECYCLE_STAGING, DUPLICATE_IMPLEMENTATIONS, PARALLEL_REPRESENTATIONS,
  MATH_AND_RNG_CHANNEL). First per-class plan filed:
  `docs/parity/plans/2026-05-26-audit-duplicate-implementations.md`.
- **First audit ran**: DUPLICATE_IMPLEMENTATIONS scan surfaced 67
  same-name same-primitive defs in `mud/` — 5× the spec's probe.
  After verification, the actionable ❌ list is ~5 real parity bugs +
  ~16 drift-risk cleanup rows. Audit doc (Task 4) still pending.
- **2.9.21** — `mud/rom_api.py` deleted. The audit surfaced it as
  its own meta-bug: a 690-line shadow API surface used only by
  `tests/test_rom_api.py` (16 tests) and one production import. Of
  its 30 functions, several were wrong stubs whose tests validated
  divergent behavior as if it were correct (`get_max_train` returned
  `min(21, 25)` while production used `handler.py:get_max_train`).
  Five months of CI passing while validating wrong code. Migrated
  the two real imports (`check_blind` → `mud/world/vision.py`,
  `recursive_clone` → `mud/models/object.py`) and deleted the file
  + its test suite.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.21 |
| Tests | 4716 passed, 4 skipped (full suite, 7m10s; lost 16 from deleted test_rom_api.py) |
| Cross-file invariants | 19 of ~20 budget; INV-001 … INV-019 ✅ ENFORCED |
| Meta-audit | 1 of 8 classes audited (DUPLICATE_IMPLEMENTATIONS; doc pending) |
| Branch | `master` (2.9.21 staged) |

## Next Intended Task

Finish the DUPLICATE_IMPLEMENTATIONS audit doc using the verified
classifications. The doc is now smaller and more actionable than the
plan anticipated:

- **5 real ❌** to burn down: `_send_to_char` (network-delivery skip),
  `_push_message` (double delivery), `_extract_obj` (wrong attribute +
  no recursion), `_check_improve` (triple-stub blocks skill
  improvement), `load_area_from_json` (divergent JSON schemas).
- **~16 ⚠️ cleanup** rows: functionally-identical duplicates needing
  consolidation, no current bug.
- **~7 ⚠️ DEAD-CODE** rows closed for free by the rom_api.py deletion.

After the audit doc commits, next move is either (a) burn-down session
for the 5 ❌ rows or (b) move on to the next audit class
(BROADCAST_COVERAGE or ARITHMETIC_BOUNDARY).

No push to origin without explicit per-cluster user approval.
2.9.21 push: AUTHORIZED for this commit.
