# Session Status — 2026-05-28 — room_registry xdist isolation leak (2.9.91)

## Current State

- **Active mode**: cross-file / remaining-documented-gap pass (the per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows — all 40 audit-bound ROM C
  files ✅, 3 N/A). This session was **test-infra**, not parity: it pinned and
  fixed the long-standing intermittent xdist isolation flake the last two
  handoffs flagged as the highest-value cleanup.
- **Last completed**:
  - **`room_registry` xdist isolation leak** ✅ FIXED (2.9.91) — the intermittent
    `AttributeError` at `reset_handler.py:178` in
    `test_group_combat::test_group_xp_split_between_members` was caused by
    `tests/integration/test_flee_moves_character.py:59` setting the **real
    registered** room 3001's `.exits` to a dict (`{"north": {...}}`, to exercise
    `do_flee`'s dict branch) after `initialize_world()`, and never restoring it.
    The leaked dict-shaped exits + populated registries persisted across the
    xdist worker; a later `game_tick()` area-reset hit
    `_restore_exit_states`, where `enumerate(dict)` yields the string key and
    `"north".exit_info = 0` raised. Fixed with an autouse snapshot/restore
    fixture for `room_registry`/`area_registry` in the flee file. Verified:
    stashed baseline reproduces the failure (1 failed); with the fix the full
    suite is green 6/6 parallel runs. Commit `5396c067`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-28_ROOM_REGISTRY_ISOLATION_LEAK.md](SESSION_SUMMARY_2026-05-28_ROOM_REGISTRY_ISOLATION_LEAK.md)
  (predecessor:
  [SESSION_SUMMARY_2026-05-28_FIGHT_018_DAM_MESSAGE_ACT_TRIGGER.md](SESSION_SUMMARY_2026-05-28_FIGHT_018_DAM_MESSAGE_ACT_TRIGGER.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.91 |
| Tests | **4898 passed, 4 skipped, 0 failed** — parallel by default (`-n auto --dist loadscope`), ~81–116s. Verified green across 6 consecutive full runs. The `room_registry` isolation flake is **fixed** (was intermittent at HEAD: stashed baseline = 1 failed). Total test count stable at 4902. |
| ROM C files audited | 40 / 43 ✅ (3 N/A: recycle/mem/imc). Per-file audit queue drained. `fight.c` ~95% in the top tracker (historical broader-sweep debt; FIGHT-001..018 all closed). |
| Cross-file invariants | 24 ENFORCED. INV-025 act()-dispatch follow-up partly extended (combat `dam_message` covered; non-combat `_push_message`/`broadcast_room` still open). |
| Branch | `master` — **3 commits ahead** of `origin/master` (`dbcd5735` FIGHT-017 / 2.9.89, `f2bd9723` FIGHT-018 / 2.9.90, `5396c067` room_registry leak / 2.9.91). Not pushed. |

## Next Intended Task

1. **Push approval** — 3 commits ahead of `origin/master` shipping 2.9.89 +
   2.9.90 + 2.9.91. Awaiting approval.
2. **INV-025 non-combat narration sweep** (optional, ad-hoc) — the
   `_push_message` / `broadcast_room` surface for non-combat ROM `act()` lines
   that should feed `mp_act_trigger_room`. One callsite per commit, each gated on
   whether the ROM site carries a `MOBtrigger = FALSE` wrap.
3. **INV-layer systematization** (optional, discussed this session, not yet
   filed) — make cross-file invariant discovery systematic rather than
   judgment-driven: static call-site enumeration (GitNexus call graph / `ast`)
   to build a guarantee × call-site coverage matrix, an always-on `game_tick`
   invariant-assertion checker (so the existing ~4900 tests double as INV
   probes), Hypothesis stateful testing over the command dispatcher, and —
   highest ceiling — differential testing against the compiled `src/` C engine
   (uniquely viable here: the Mitchell-Moore RNG and C integer math are already
   bit-matched, removing the usual nondeterminism blocker). Suggested first step
   is the always-on invariant checker (highest leverage-per-effort).
4. **Broader `initialize_world()` leak** (low severity, see latest summary
   "Outstanding") — 49 integration files leak a populated (but structurally
   valid) world; only the flee test corrupted a room. A conftest-level fix must
   avoid wiping the 3 module-scoped-world fixture files.
5. **GitNexus** — MCP query path read-only this session; on-disk graph stale
   (`last indexed: 2272b2e`). Re-run `npx gitnexus analyze --skip-agents-md`
   once the DB lock clears.
