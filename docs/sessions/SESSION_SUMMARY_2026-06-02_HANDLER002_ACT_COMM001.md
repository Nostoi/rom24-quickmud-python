# Session Summary — 2026-06-02 — HANDLER-002 + ACT_COMM-001 CLOSED

## Scope

Picked up from the prior session (2.12.59), which closed HANDLER-001 + INTERP-026
and left two documented gaps OPEN: **HANDLER-002** (`get_char_room` N.name
double-count) and **ACT_COMM-001** (`follow self` double "stop following"
message). Both were the SESSION_STATUS-recommended next tasks. This session
closed both — one gap, one failing-test-first commit each. Cross-file invariants
remains the active pass; both gaps are local single-function divergences.

## Outcomes

### `HANDLER-002` — ✅ FIXED (2.12.60 / `f0ed0091`)

- **Python**: `mud/world/char_find.py:get_char_room`
- **ROM C**: `src/handler.c:2205-2211` (single `is_name(arg, rch->name)` test;
  `if (++count == number)` advances once per occupant)
- **Gap**: `get_char_room` split the match across a name/short_descr block and a
  separate keyword block, each running `count += 1`, so an occupant matching
  both advanced `count` twice — `N.name` (N≥2) could resolve to the wrong
  occupant.
- **Fix**: ORed the three match sources into one predicate with a single
  `count += 1`.
- **Audit-row correction (mandatory, per AGENTS re-verify directive)**: the
  original HANDLER-002 row claimed the bug "fires for typical mobs whose keyword
  list repeats their name" and that `2.guard` returned the *first* guard. **That
  claim is false.** Empirically verified: real `Character` instances never carry
  a `.keywords` attribute (the JSON loader stores keyword lists in `.name`;
  spawned mobs have `hasattr(m, "keywords") == False`), so the keyword block was
  empty for every real occupant and the double-count **never fired in
  production** — `2.guard` already returned the second guard. This was a
  **latent** double-count in a ROM-divergent dead block, not a live divergence.
  Corrected the row to say so.
- **Tests**: `tests/integration/test_handler002_get_char_room_count_once.py`
  (1 test: forces the multi-field match via `.keywords`, asserts `1.guard`/bare
  `guard` → first and `2.guard` → second guard; honestly labeled a
  latent-invariant guard). Fails pre-fix (returns first guard for `2.guard`),
  passes post-fix.

### `ACT_COMM-001` — ✅ FIXED (2.12.61 / `eab2139e`)

- **Python**: `mud/commands/group_commands.py:do_follow`
- **ROM C**: `src/act_comm.c:1562-1571` (self-branch calls `stop_follower(ch)`
  and returns silently; `stop_follower` is the sole message emitter)
- **Gap**: `do_follow`'s self-branch called `stop_follower(char)` — which
  appends `"You stop following {master}."` to `char.messages` — **and then**
  returned a bare `"You stop following."` TO_CHAR string, so the actor saw the
  message twice (once named, once not).
- **Fix**: self-branch now returns `""` (silent), leaving `stop_follower` as the
  sole emitter to match ROM's silent return.
- **Tests**: `tests/integration/test_act_comm001_follow_self_single_message.py`
  (2 tests: `follow self` while following X → exactly one
  "You stop following bob."; no-master branch → "You already follow yourself."
  unchanged). Fails pre-fix (bare duplicate returned), passes post-fix.

## Out-of-scope gaps filed durably

- **ACT_COMM-002** (`docs/parity/ACT_COMM_C_AUDIT.md`, ❌ OPEN) — **sibling of
  ACT_COMM-001 in the NORMAL follow path.** `do_follow`'s success path returns
  `"You now follow {victim}."` *and* `add_follower` already appends the same line
  to `char.messages`; both channels reach a connected player (command-return at
  `connection.py:1989`, `char.messages` drain at `:2002-2008`), so the actor sees
  it **twice**. ROM `add_follower:1605` is the sole TO_CHAR emitter; `do_follow`
  returns void. **Empirically confirmed** this session (advisor's
  discriminating-channel check while closing ACT_COMM-001 predicted it). Fix:
  `do_follow` success path returns `""` — but existing tests assert the *return*
  value (`test_group_combat.py:162`, `test_shops.py:1365`), so it needs a focused
  test-first gap-closer (retarget those to `char.messages`), not an end-of-session
  rush. **Recommended top task for the next session.**
- **HANDLER-003** (`docs/parity/HANDLER_C_AUDIT.md`, ❌ OPEN) —
  `get_char_room`/`get_char_world` also match `short_descr`; ROM matches **only**
  `name` (via whole-word `is_name`, not substring). e.g. `look city` resolves
  "a city guard" in Python where ROM would not. Likely load-bearing for callers
  relying on the looser match — do not silently tighten. Surfaced while closing
  HANDLER-002.

## Files Modified

- `mud/world/char_find.py` — `get_char_room` combined match predicate (count once).
- `mud/commands/group_commands.py` — `do_follow` self-branch returns `""`.
- `tests/integration/test_handler002_get_char_room_count_once.py` — new (HANDLER-002).
- `tests/integration/test_act_comm001_follow_self_single_message.py` — new (ACT_COMM-001).
- `docs/parity/HANDLER_C_AUDIT.md` — HANDLER-002 → ✅ FIXED (+ corrected false claim); HANDLER-003 → ❌ OPEN (new).
- `docs/parity/ACT_COMM_C_AUDIT.md` — ACT_COMM-001 → ✅ FIXED; do_follow row + parity check flipped.
- `CHANGELOG.md` — two `Fixed` entries.
- `pyproject.toml` — 2.12.59 → 2.12.60 → 2.12.61.

## Test Status

- HANDLER-002 + ACT_COMM-001 area tests: green (incl. follow/handler/socials regression).
- Full suite: **5319 passed, 4 skipped** (`pytest`, parallel) — 3 new tests over the 5316 baseline.
- `ruff check` on all touched files: clean (repo-wide baseline already carries
  pre-existing UP037/etc. errors unrelated to this work).

## Next Steps

Cross-file invariants remains the active pass. Candidate next tasks:

1. **Close ACT_COMM-002** (recommended first) — `do_follow` success path returns
   `""`, leaving `add_follower` the sole emitter of "You now follow X."; retarget
   `test_group_combat.py:162` / `test_shops.py:1365` from the return value to
   `char.messages` and re-verify against ROM `act(TO_CHAR)`. Live user-facing
   double-message; trivial fix, modest test churn.
2. **Close HANDLER-003** — decide whether to mirror ROM's `name`-only whole-word
   `is_name` match (parity-faithful) in `get_char_room`/`get_char_world` and
   audit caller fallout, or document the `short_descr`/substring divergence as
   intentional. CRITICAL blast radius (15 callers) — sweep callers test-first.
3. **Probe a fresh cross-file candidate** — position transitions
   (`do_stand`/`do_sit`/`do_rest`/`do_sleep`/`do_wake`), group/follower chains,
   or mob trigger ordering. Method: read ROM C contract → read Python equivalent
   → one failing test → close as gap or file as next free INV-NNN.
