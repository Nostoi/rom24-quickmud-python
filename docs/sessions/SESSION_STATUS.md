# Session Status — 2026-06-02 — HANDLER-001 + INTERP-026 CLOSED (2.12.59)

## Current State

- **Active mode**: cross-file invariants. **HANDLER-001 and INTERP-026 are now
  CLOSED** — the two open gaps the prior session (2.12.57) recommended as Track 1.
- **This session — two commits (local, NOT pushed):**
  - **2.12.58 / `aa9cf1c1`** — **HANDLER-001**: removed the self-skip in the
    shared `get_char_room` (`char_find.py`) so `<cmd> <ownname>` resolves to self,
    mirroring ROM (`src/handler.c:2194-2214`: no self-skip; `can_see(ch,ch)`
    short-circuits TRUE). **Full 14-caller ROM-C ⇄ Python sweep** — no
    compensating guards needed; only `do_steal`'s substring self pre-check removed
    (the `victim==ch` guard subsumes it). New
    `tests/integration/test_handler001_get_char_room_self.py`; 4 collision-prone
    NPC-interaction tests retargeted "test"→"mob".
  - **2.12.59 / `fc94e15c`** — **INTERP-026**: migrated `perform_social`'s victim
    search onto the shared `get_char_room` (now self-correct), closing the
    `can_see` presence leak (`smile <invisible>` → "They aren't here.") + N.name
    (`2.guard`) and deleting the hand-rolled `startswith` loop. New
    `tests/integration/test_interp026_social_can_see_and_nname.py`.
  - **Filed durably (out-of-scope, ❌ OPEN):** **HANDLER-002**
    (`HANDLER_C_AUDIT.md`) — `get_char_room` double-counts an occupant when
    name+keywords both match, mis-selecting `N.name`. **ACT_COMM-001**
    (`ACT_COMM_C_AUDIT.md`) — `follow self` emits a double "stop following"
    message (corrected that row's stale ✅).

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_GET_CHAR_ROOM_SELF_AND_SOCIALS_MIGRATION.md](SESSION_SUMMARY_2026-06-02_GET_CHAR_ROOM_SELF_AND_SOCIALS_MIGRATION.md)
  (prior: [INTERP025_SOCIAL_SELF_TARGET](SESSION_SUMMARY_2026-06-02_INTERP025_SOCIAL_SELF_TARGET.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.59 |
| Tests | **full suite green: 5316 passed, 4 skipped** (`pytest`, ~127s parallel) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open gaps | **HANDLER-002** (`get_char_room` N.name double-count) + **ACT_COMM-001** (`follow self` double message) — both filed this session, OPEN. |

## Next Intended Task

Cross-file invariants remains the active pass. Options:

1. **Close HANDLER-002** — single-helper fix in `char_find.py:get_char_room`:
   count at most once per occupant (combine name/short/keyword into one
   `is_name`-style predicate). Test-first: two mobs sharing name+keyword;
   `2.<name>` selects the second. Same fix applies to `get_char_world`.
2. **Close ACT_COMM-001** — drop the bare `return "You stop following."` in
   `do_follow`'s `victim is char` branch (return `""`); `stop_follower` is the
   sole ROM emitter. Test-first: `follow self` while following X → exactly one
   "You stop following X." (no bare duplicate).
3. **Or probe a fresh cross-file candidate** — position transitions
   (`do_stand`/`do_sit`/`do_rest`/`do_sleep`/`do_wake` — deterministic, no RNG),
   group/follower chains, or mob trigger ordering. Method: read ROM C contract →
   read Python equivalent → one failing test → close as gap or file as next free
   INV-NNN.

> **Push note:** everything through 2.12.48 is on `master`; **2.12.49–59** are
> committed locally but **NOT yet pushed**. README/CHANGELOG/version all reflect
> 2.12.59. GitNexus reindex completed after the last commit (index fresh at
> `fc94e15c`).
