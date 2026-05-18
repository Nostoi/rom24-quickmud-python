# 2026-05-17 — do_time ROM-source-first verification

## Goal
Verify and close the remaining `do_time` parity/coverage gaps against ROM `src/act_info.c`, then update tests and trackers with evidence.

## Source of truth
- ROM C: `src/act_info.c` (`do_time`)
- Python: `mud/commands/info.py` (`do_time`)
- Coverage tracker: `docs/parity/INTEGRATION_TEST_COVERAGE_TRACKER.md`
- Session pointer: `docs/sessions/SESSION_STATUS.md`

## Steps
1. Read ROM `do_time` and note exact formatting, ordinal rules, and boot/system time lines.
2. Read Python `do_time` and compare behavior line-by-line.
3. Run focused `do_time` integration tests to establish current failures.
4. Fix Python behavior to match ROM exactly, or fix stale tests if Python is already correct.
5. Re-run focused tests, then update coverage/session docs.
