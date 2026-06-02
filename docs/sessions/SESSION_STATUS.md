# Session Status — 2026-06-02 — HANDLER-002 + ACT_COMM-001 CLOSED (2.12.61)

## Current State

- **Active mode**: cross-file invariants. **HANDLER-002 and ACT_COMM-001 are now
  CLOSED** — the two open gaps the prior session (2.12.59) left as recommended
  next tasks.
- **This session — two commits (local, NOT pushed):**
  - **2.12.60 / `f0ed0091`** — **HANDLER-002**: combined `get_char_room`'s
    name/short_descr/keyword match sources into one predicate with a single
    `count += 1`, so `N.name` lookups advance count once per occupant
    (`src/handler.c:2205-2211`). **Empirically verified the double-count was
    latent, not live** — real `Character` instances never carry a `.keywords`
    attribute (the JSON loader stores keyword lists in `.name`), so the keyword
    block was dead and `2.guard` already returned the second guard. **Corrected
    the audit row's false "fires for typical mobs" claim.** New
    `tests/integration/test_handler002_get_char_room_count_once.py`.
  - **2.12.61 / `eab2139e`** — **ACT_COMM-001**: `do_follow`'s `follow self`
    branch returned a bare `"You stop following."` *in addition to* the named
    line `stop_follower` already delivers — the actor saw it twice. Self-branch
    now returns `""` (silent), matching ROM's silent return (`src/act_comm.c:
    1569-1570`); `stop_follower` is the sole emitter. New
    `tests/integration/test_act_comm001_follow_self_single_message.py`.
  - **Filed durably (out-of-scope, ❌ OPEN):**
    - **ACT_COMM-002** (`ACT_COMM_C_AUDIT.md`) — sibling of ACT_COMM-001 in the
      NORMAL follow path: `do_follow` returns "You now follow X." *and*
      `add_follower` appends it to `char.messages`; both reach a connected player,
      so the actor sees it twice. Empirically confirmed. Fix: `do_follow` success
      path returns `""` (test churn: `test_group_combat.py:162`,
      `test_shops.py:1365` assert the return value). **Recommended next task.**
    - **HANDLER-003** (`HANDLER_C_AUDIT.md`) — `get_char_room`/`get_char_world`
      also match `short_descr`; ROM matches **only** `name` (whole-word
      `is_name`, not substring). e.g. `look city` resolves "a city guard" in
      Python where ROM would not. Likely load-bearing for callers — do not
      silently tighten.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_HANDLER002_ACT_COMM001.md](SESSION_SUMMARY_2026-06-02_HANDLER002_ACT_COMM001.md)
  (prior: [GET_CHAR_ROOM_SELF_AND_SOCIALS_MIGRATION](SESSION_SUMMARY_2026-06-02_GET_CHAR_ROOM_SELF_AND_SOCIALS_MIGRATION.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.63 |
| Tests | **full suite green at 2.12.62: 5321 passed, 4 skipped** (`pytest`, ~132s parallel); HANDLER-003 caused zero caller fallout; new test + ACT_COMM-002 area suites green at 2.12.63 |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open gaps | **HANDLER-004** (Python `is_name` uses substring match, not ROM's whole-word `str_prefix`; `is_name("uard","guard")`→True vs ROM FALSE) — OPEN, filed this session. (HANDLER-003 CLOSED 2.12.63 / `defaf313`; ACT_COMM-002 CLOSED 2.12.62 / `9f73c6d3`.) |

## Next Intended Task

Cross-file invariants remains the active pass. Options:

1. **Close HANDLER-004** (recommended) — rewrite `mud/world/char_find.py:is_name`
   to mirror ROM's `one_argument` tokenization + `str_prefix` all-parts whole-word
   match (`src/handler.c:932-969`), replacing the current substring test. Then
   audit the other callers (`mob_cmds`, `build` ×3, `info`, `account_service`) for
   fallout — they rely on the looser substring behavior, so tighten test-first.
2. **Probe a fresh cross-file candidate** — position transitions
   (`do_stand`/`do_sit`/`do_rest`/`do_sleep`/`do_wake` — deterministic, no RNG),
   group/follower chains, or mob trigger ordering. Method: read ROM C contract →
   read Python equivalent → one failing test → close as gap or file as next free
   INV-NNN.

> **Push note:** everything through 2.12.48 is on `master`; **2.12.49–63** are
> committed locally but **NOT yet pushed**. CHANGELOG/version reflect 2.12.63.
> GitNexus reindex running in background after the HANDLER-003 commit.
