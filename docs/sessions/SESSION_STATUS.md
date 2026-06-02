# Session Status — 2026-06-02 — ACT_COMM-002 + HANDLER-003 + HANDLER-005 CLOSED (2.12.64)

## Current State

- **Active mode**: cross-file invariants. This session closed **ACT_COMM-002,
  HANDLER-003, and HANDLER-005** (the two open gaps the prior 2.12.61 session
  left, plus one advisor-surfaced divergence in the same function).
- **This session — five commits (pushed to `master`):**
  - **2.12.62 / `9f73c6d3`** + **`be5f4047`** — **ACT_COMM-002**: `do_follow`'s
    NORMAL success path returned `"You now follow X."` *and* `add_follower`
    appended the same line to `char.messages` — the actor saw it twice. Success
    path now returns `""` (matching ROM's void return, `src/act_comm.c:1586-1605`);
    `add_follower` is the sole emitter. Retargeted `test_group_combat.py:162` and
    `test_player_npc_interaction.py` from the return value to `char.messages`. New
    `tests/integration/test_act_comm002_follow_other_single_message.py`.
  - **2.12.63 / `defaf313`** — **HANDLER-003**: `get_char_room`/`get_char_world`
    substring-matched `short_descr`; ROM gates solely on `is_name(arg, name)`
    (keyword list, `src/handler.c:2207`/`:2237`). Both helpers now gate on
    `is_name(name, occupant.name)` only. **Zero caller fallout** (full suite). The
    shared `is_name` helper was left untouched (own callers). New
    `tests/integration/test_handler003_get_char_matches_name_only.py`.
  - **2.12.64 / HANDLER-005** — `get_char_world` omitted ROM's `wch->in_room ==
    NULL` skip (`src/handler.c:2236`); **live** since VISION-001 made roomless
    chars visible to `can_see_character`. Added the `ch.room is None` first-gate
    skip. New `tests/integration/test_handler005_get_char_world_skips_roomless.py`.
  - **Filed durably (out-of-scope, ❌ OPEN):**
    - **HANDLER-004** (`HANDLER_C_AUDIT.md`) — Python `is_name` uses a substring
      test (`name_lower in word`), not ROM's `str_prefix` whole-word match, and
      skips ROM's "all parts must match" rule. `is_name("uard","guard")`→`True`
      vs ROM `FALSE`. Tightening widens blast radius to its other callers
      (`mob_cmds`, `build`, `info`, `account_service`) — do test-first.
      **Recommended next task.**

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_ACT_COMM002_HANDLER_003_005.md](SESSION_SUMMARY_2026-06-02_ACT_COMM002_HANDLER_003_005.md)
  (prior: [HANDLER002_ACT_COMM001](SESSION_SUMMARY_2026-06-02_HANDLER002_ACT_COMM001.md)).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.64 |
| Tests | **full suite green at 2.12.64: 5323 passed, 4 skipped** (`pytest`, ~137s parallel); HANDLER-003 + HANDLER-005 caused zero caller fallout |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open gaps | **HANDLER-004** (Python `is_name` uses substring match, not ROM's whole-word `str_prefix`; `is_name("uard","guard")`→True vs ROM FALSE) — OPEN, filed this session. (HANDLER-005 CLOSED 2.12.64 / roomless world-lookup skip; HANDLER-003 CLOSED 2.12.63 / `defaf313`; ACT_COMM-002 CLOSED 2.12.62 / `9f73c6d3`.) |

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

> **Push note:** through **2.12.64** pushed to `master` 2026-06-02.
> CHANGELOG/version reflect 2.12.64. GitNexus reindex run after the push.
