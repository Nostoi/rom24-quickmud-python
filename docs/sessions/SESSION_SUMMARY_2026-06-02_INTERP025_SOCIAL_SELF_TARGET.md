# Session Summary — 2026-06-02 — INTERP-025 self-targeted socials CLOSED (2.12.57)

## Scope

Picked up from `SESSION_STATUS.md` (post-INV-025 socials `$n` PERS close,
2.12.56). The prior session filed **INTERP-025** as Outstanding: self-targeted
socials were unreachable — `smile self` / `smile <ownname>` fell through to
"They aren't here." instead of `char_auto`/`others_auto`. Chose to close that
ready-scoped gap (finishing the socials thread) over an open-ended cross-file
probe. Verified the divergence against ROM C source directly before writing the
fix, then bounded scope with `gitnexus_impact`.

## Outcomes

### `INTERP-025` — ✅ FIXED (2.12.57)

- **Python**: `mud/commands/socials.py:perform_social` (victim search ~56-67)
- **ROM C**: `src/interp.c:630-645` (`do_social`), `src/handler.c:2194-2214`
  (`get_char_room`)
- **Gap**: self-targeted socials unreachable — the hand-rolled victim search did
  `if person is char: continue` and had no `"self"` keyword, so both
  `smile self` and `smile <ownname>` missed `victim == ch` and the
  `char_auto`/`others_auto` branch (`socials.py:94-97`) was dead code.
- **Fix**: socials-local. The search now maps `"self"` → `char` and the people
  loop no longer skips `char`, mirroring ROM `get_char_room` (returns `ch` for
  `"self"` at 2203-2204; people loop has no self-skip at 2205-2211). Both paths
  now reach `char_auto`/`others_auto`.
- **Scope decision**: deliberately **not** routed through the shared
  `mud/world/char_find.py:get_char_room`. That helper has its own self-by-name
  divergence (keeps the skip), and `gitnexus_impact` rated changing it
  **CRITICAL** (14 direct callers). Filed as **HANDLER-001** for a future
  per-caller sweep instead.
- **Tests**: new `tests/integration/test_interp025_social_self_target.py`
  (2 tests: `smile self` + `smile <ownname>` → actor "You smile at yourself.",
  room observer "Alice smiles at herself."); flipped
  `tests/integration/test_socials.py::test_social_targeting_self` from the
  bug-encoding not-found assertion to ROM-correct `["You smile at yourself."]`
  (AGENTS.md "test asserts behavior contradicting ROM C" case).

## Files Modified

- `mud/commands/socials.py` — `"self"` keyword + removed self-skip in the
  victim search.
- `tests/integration/test_interp025_social_self_target.py` — new enforcement test.
- `tests/integration/test_socials.py` — flipped `test_social_targeting_self`.
- `docs/parity/INTERP_C_AUDIT.md` — INTERP-025 row → ✅ FIXED; added INTERP-026.
- `docs/parity/HANDLER_C_AUDIT.md` — corrected the false-✅ `get_char_room`
  "Verified" row to ⚠️ Divergent; added the HANDLER-001 gap detail.
- `CHANGELOG.md` — `Fixed` entry for INTERP-025.
- `pyproject.toml` — 2.12.56 → 2.12.57 (patch: parity gap closure).

## Test Status

- `pytest tests/integration/test_socials.py test_inv025_socials_pers_sweep.py
  test_interp025_social_self_target.py test_interp_dispatcher.py` — 64/64.
- `ruff check` — clean on touched files.
- `gitnexus_detect_changes` — low risk, 0 affected processes; scope = `perform_social`
  + 2 test methods + the 4 docs.
- **Full suite**: `pytest` — **5310 passed, 4 skipped** (~114s), observed this
  session (was 5308 at 2.12.56; +2 from the new test).

## Outstanding (filed durably this session)

- **HANDLER-001** (`docs/parity/HANDLER_C_AUDIT.md`) — the shared
  `get_char_room` skips self-by-name (`char_find.py:51`); ROM does not
  (`src/handler.c:2205-2211`), so callers can't target self by own name
  (`follow <ownname>`, `look <ownname>`, `kill <ownname>` self-hit guard).
  CRITICAL blast radius (14 callers); each needs its ROM `victim == ch`
  handling re-checked before the skip is removed. ❌ OPEN.
- **INTERP-026** (`docs/parity/INTERP_C_AUDIT.md`) — socials' hand-rolled search
  bypasses `get_char_room`, so it lacks **`can_see` gating** (presence leak:
  `smile <invisible>` → "You smile at someone." where ROM returns NULL →
  "They aren't here." — INV-027 family) and **`N.name`** selection. Natural
  resolution: migrate `perform_social` to the shared `get_char_room` once
  HANDLER-001 lands, closing self + no-self-skip + can_see + N.name together.
  ❌ OPEN.

## Next Steps

Cross-file invariants is still the active pass. Either:
1. **Close HANDLER-001 + INTERP-026 together** — fix the shared `get_char_room`
   self-skip with a 14-caller `victim == ch` sweep, then migrate socials onto
   it (closes INTERP-026's can_see/N.name leak as a side effect). Test-first per
   the gap rows.
2. **Or probe a fresh cross-file candidate** — position transitions
   (`do_stand`/`do_sit`/`do_rest`/`do_sleep`/`do_wake`, the tightest/most
   deterministic), group/follower chains, or mob trigger ordering.

**Push note:** 2.12.49–57 are committed locally but NOT yet pushed; 2.12.48 is
the last on `master`.
