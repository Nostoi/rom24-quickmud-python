# Session Summary — 2026-06-02 — README honesty pass + HANDLER-004 closed

## Scope

Two deliverables this session. First, a user-requested **README honesty pass**:
the README contradicted itself — the top framed the project as "trust rebuild in
progress" while the bottom "Project Completeness" section still claimed
"production-ready" with "100% behavioral parity," and four different test counts
(4,934 / 5,256 / 5,306 / 5,319) appeared across the file. Second, closing the
single remaining open parity gap, **HANDLER-004** (the SESSION_STATUS-recommended
next task): Python's `is_name` used a substring match rather than ROM's whole-word
`str_prefix` + all-parts rule. Picked up from the prior 2.12.64 session
(ACT_COMM-002 + HANDLER-003 + HANDLER-005). Cross-file invariants remains the
active pass. Both commits on `master` (local; not yet pushed).

## Outcomes

### README honesty pass — ✅ DONE (2.12.65 / `7689e971`)

- Resolved the production-ready vs trust-rebuild contradiction: the "Project
  Completeness" and "Quality Metrics" sections now match the honest top framing —
  feature-complete, green suite, in a **verification trust-rebuild phase**, not
  certified bug-free.
- Drew the key distinction the old text collapsed: *audit-process completion*
  (every applicable ROM C file has an audit document) vs *behavioral parity* (not
  yet certified — three prod bugs this year shipped against ≥95%-audited files).
- Unified the four conflicting test counts to the live run, bumped the version
  badge, added an "open parity gaps" note.

### `HANDLER-004` — ✅ FIXED (2.12.65 / `fc450d41`)

- **Python**: `mud/world/char_find.py:is_name`
- **ROM C**: `src/handler.c:932-969` (`is_name`) — each space-separated part of
  the arg must be a `str_prefix` (whole-word *prefix*) of some namelist word, and
  **all** parts must match.
- **Gap**: `is_name` used a substring test (`name_lower in word`) with no
  all-parts conjunction, so `is_name("uard","guard")` returned `True` (ROM:
  `FALSE`) and multi-word args like `"big guard"` failed to match `"guard big"`
  (ROM: `TRUE`).
- **Fix**: rewrote `is_name` to split the arg into parts, require each part to be
  a prefix of some namelist word, and gate the match on all parts matching —
  mirroring `src/handler.c:946-967`. Kept the full-arg prefix short-circuit for
  fidelity.
- **Impact**: `gitnexus_impact` rated this **CRITICAL** — 7 direct callers fanning
  out (d2/d3) to nearly every char/object-targeting command (tell, give, steal,
  murder, look, where, socials, OLC `redit`/`hedit` list filters, and
  `is_valid_character_name`). But ROM itself calls `is_name` at every one of those
  sites, so the tightening moves all callers *toward* parity. User approved
  "proceed test-first."
- **Tests**: `tests/integration/test_handler004_is_name_whole_word_prefix.py`
  (6 tests: substring rejection, prefix match, all-parts multi-word, one-unmatched
  part fails, per-part prefix-not-substring, empty inputs). 2 failed pre-fix for
  the expected reasons, all 6 pass post-fix. **Full suite: 5329 passed, 4 skipped
  — zero fallout** (no test relied on the looser substring behavior).

## Files Modified

- `README.md` — honesty pass (commit `7689e971`).
- `mud/world/char_find.py` — `is_name` rewritten to ROM whole-word `str_prefix` +
  all-parts logic.
- `tests/integration/test_handler004_is_name_whole_word_prefix.py` — new, 6 tests.
- `docs/parity/HANDLER_C_AUDIT.md` — HANDLER-004 row flipped ❌ OPEN → ✅ FIXED.
- `CHANGELOG.md` — added `Changed` (README) + `Fixed` (HANDLER-004) entries.
- `pyproject.toml` — 2.12.64 → 2.12.65.

## Test Status

- `tests/integration/test_handler004_is_name_whole_word_prefix.py` — 6/6 passing.
- Full suite: **5329 passed, 4 skipped** (`pytest`, ~152s parallel). Zero fallout
  from the CRITICAL-rated `is_name` change.

## Next Steps

**HANDLER-004 was the last open per-file gap; there are now no ⚠️ Partial /
❌ Not Audited rows and no open gap IDs.** Cross-file invariants is the sole active
pass. Probe a fresh candidate not yet covered by an INV row — recommended:
**position transitions** (`do_stand`/`do_sit`/`do_rest`/`do_sleep`/`do_wake`,
deterministic, no RNG) or **group/follower chain** ordering. Method: read the ROM
C contract → read the Python equivalent → write one failing test → close as a gap
(single commit) or file as the next free INV-NNN.

> **Push note:** 2.12.65 (commits `7689e971` + `fc450d41`) is committed locally on
> `master` but **NOT yet pushed** — awaiting user confirmation. GitNexus reindex
> kicked off after the commits.
