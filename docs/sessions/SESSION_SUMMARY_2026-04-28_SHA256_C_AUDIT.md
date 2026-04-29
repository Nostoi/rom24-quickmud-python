# Session Summary — 2026-04-28 — `sha256.c` parity audit

## Scope

Picked up after `ban.c` reached ✅ AUDITED. Selected `sha256.c` (P3, listed in tracker as ⚠️ Partial 100% "Uses Python hashlib") as the smallest contained next target. The Python implementation already delegates SHA-256 to stdlib `hashlib` and uses PBKDF2-HMAC-SHA256 + random salt for password storage; the audit's purpose was to formalize that finding, document the deliberate security divergence, and flip the tracker row.

Earlier candidates evaluated and skipped:
- `bit.c` (claimed 90% but the 3 ROM functions `flag_value`/`flag_string`/`is_stat` are OLC string↔bit helpers — Python OLC subsystem is only stubs, so a real audit is blocked on the OLC port).
- `string.c` (multi-hundred-line OLC string editor, also OLC-bound; not contained).

## Outcomes

### `sha256.c` — ✅ AUDITED (100%)

- **ROM C**: `src/sha256.c` (336 lines, 4 public functions + SHA-256 primitives).
- **Python**: `mud/security/hash_utils.py` (delegates to `hashlib`).
- **Finding**: The SHA-256 primitive (Init/Update/Final/Transform/Pad and the be32 helpers, ROM 41-318) is provided by Python's `hashlib.sha256`, which is byte-for-byte equivalent (RFC 6234 / FIPS 180-4 standard).
- **Deliberate divergence**: ROM's `sha256_crypt` (lines 320-336) is plain unsalted single-round SHA-256, hex-encoded — vulnerable to rainbow tables and trivially brute-forceable. QuickMUD instead uses **PBKDF2-HMAC-SHA256** with a **16-byte random salt** and **100 000 rounds**, stored as `salt_hex:hash_hex`. Documented as a security upgrade with no observable gameplay parity surface (account credentials are internal; QuickMUD does not load original ROM 2.4b6 pfiles).
- **Gaps**: None.

## Files Modified

- `docs/parity/SHA256_C_AUDIT.md` — created. Phase 1 inventory (10 ROM symbols → Python counterparts), Phase 2 verification (SHA-256 primitive equivalence + sha256_crypt → PBKDF2 divergence rationale), Phase 3 empty gap table, Phase 5 completion summary.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `sha256.c` row flipped ⚠️ Partial → ✅ AUDITED; per-file status block updated; overall summary refreshed from "42% Audited (18 audited, 16 partial, 5 not audited, 4 N/A)" to "58% Audited (25 audited, 8 partial, 7 not audited, 4 N/A)".
- `CHANGELOG.md` — `[Unreleased]` → new `Changed` entry documenting the sha256.c audit and the deliberate `sha256_crypt` → PBKDF2 divergence.
- `pyproject.toml` — `2.6.20` → `2.6.21`.

## Test Status

- `pytest tests/test_hash_utils.py -q` — 1/1 passing.
- No code changes; existing tests cover hash uniqueness (per-call salt), round-trip verification, and rejection of malformed stored hashes. Account-auth integration tests (`tests/test_account_auth.py`, `tests/integration/test_do_password_command.py`) cover the full login/password-change flow via the same helpers.

## Next Steps

Tracker is now 25/43 audited. Remaining ⚠️ Partial / ❌ Not Audited candidates:

1. **Deferred NANNY trio** — NANNY-008 (pet follows owner on login), NANNY-009 (title_table + first-login set_title), NANNY-010 (CON_BREAK_CONNECT iterate-all-descriptors). Each needs its own architectural-scope session.
2. **Mid-sized P3 utility files** — `flags.c` (75%), `lookup.c` (65%), `tables.c` (70%), `const.c` (80%). All contained but require porting work where Python doesn't have direct equivalents.
3. **OLC cluster** (P2 ❌ Not Audited) — `olc.c`, `olc_act.c`, `olc_save.c`, `olc_mpcode.c`, `hedit.c`. Multi-session block; would unblock `bit.c` and `string.c` audits.
4. **`board.c`** (P2 35%) — boards subsystem, scope between OLC and ban.c.
