# Session Status — 2026-04-28 — `sha256.c` parity audit (✅ 100% AUDITED)

## Current State

- **Active audit**: `sha256.c` — ✅ AUDITED at 100%. No gaps. Deliberate `sha256_crypt` → PBKDF2 divergence documented in `docs/parity/SHA256_C_AUDIT.md`.
- **Last completed**: `sha256.c` audit doc written; tracker row + per-file status block + overall summary updated; CHANGELOG `Changed` entry; version bumped to 2.6.21.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-28_SHA256_C_AUDIT.md](SESSION_SUMMARY_2026-04-28_SHA256_C_AUDIT.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.21 |
| Tests | `tests/test_hash_utils.py` 1/1 passing; no code changes this session |
| ROM C files audited | 25 / 43 (sha256.c newly AUDITED) |
| Active focus | `sha256.c` ✅ 100%; previous session closed `ban.c` (BAN-001..004) |

## Next Intended Task

Pick the next ⚠️ Partial / ❌ Not Audited file from `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`. Top candidates:

1. **Deferred NANNY trio** — NANNY-008 (pet follows owner on login), NANNY-009 (title_table + first-login set_title), NANNY-010 (CON_BREAK_CONNECT iterate-all-descriptors). Each needs its own focused session due to scope (async refactor / data porting / descriptor-list iteration).
2. **Mid-sized P3 utility files** — `flags.c` (75%), `lookup.c` (65%), `tables.c` (70%), `const.c` (80%). Contained but require porting work.
3. **OLC cluster** — `olc.c`, `olc_act.c`, `olc_save.c`, `olc_mpcode.c`, `hedit.c` — would unblock `bit.c` and `string.c` audits.
4. **`board.c`** (P2 35%) — boards subsystem; mid-scope.
