# Session Summary — 2026-05-14 — special.c audit reconciled

## Scope

The subsystem tracker still listed `special.c` as not audited. That claim was
checked against the existing per-file audit, the live Python spec-function
implementation, and the current test coverage.

## What was found

- `docs/parity/SPECIAL_C_AUDIT.md` already maps all ROM `special.c` functions
- the audit doc already records the gameplay-visible gap closures
- the spec-function implementation in `mud/spec_funs.py` already covers the ROM
  special procedures named in `src/special.c`
- the existing verification slice is green

The open tracker row was stale, not a live parity gap.

## Changes made

- Updated `docs/parity/SPECIAL_C_AUDIT.md` status/closure sections
- Replaced the stale `special.c` subsystem tracker row in
  `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- Updated `docs/sessions/SESSION_STATUS.md`

## Verification

- `./venv/bin/python -m pytest -q tests/test_spec_funs.py tests/test_spec_fun_behaviors.py tests/test_healer.py`

## Outcome

`special.c` is now recorded accurately as audited. No production code change
was required.

## Next task

Move to `healer.c`, which is now the next real open non-deferred row in the
subsystem tracker.
