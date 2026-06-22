# Session Status — 2026-06-22 — Prompt-after-tick (INV-053) + net-death link-dead (class 14)

## Current State

- **Active focus**: Cross-file invariants / divergence-class roster (the
  enumeration-of-structural-divergences pass). Class 14 just closed.
- **Last completed**:
  - **INV-053** (PROMPT-AFTER-TICK-OUTPUT) — the prompt's HP/mana/move now
    refreshes after tick-generated output (combat rounds, a spell from a
    mob/mobprog on an idle PC), mirroring ROM `process_output`
    (`src/comm.c:868-883`, `1376-1377`). Silent idle regen still emits no prompt
    (ROM-correct). Commit `8baa7662`.
  - **Divergence-class 14 CLOSED** (net-death link-dead lifecycle) — a genuine
    socket drop now keeps the char in the world link-dead (ROM `close_socket`,
    `src/comm.c:1075-1093`): lost-link broadcast + `WIZ_LINKS` wiznet, descriptor
    detached, char kept in room + registry, idled by `char_update`
    (void@12/autoquit@30) and attackable while away. A returning player rebinds
    to that same instance (`check_reconnect`, gated behind the normal password).
    Explicit `quit` / idle-autoquit still fully extract. Commits `8aab0cef`
    (rebind machinery, inert) + `3681c40b` (linger + reconnect, CLOSED).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-22_PROMPT_TICK_AND_LINKDEAD.md](SESSION_SUMMARY_2026-06-22_PROMPT_TICK_AND_LINKDEAD.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.211 |
| Tests | Full suite: 6034 passed, 4 skipped; `ruff check` clean |
| Cross-file invariants | INV-053 added (✅ ENFORCED); INV-009 mechanism updated |
| Divergence classes | Class 14 (Connection/session lifecycle) ✅ CLOSED |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class roster |

## Next Intended Task

Class 14 is closed and the suite is green at 2.14.211. Pick up either:

- **Optional class-14 hardening** — a per-name disconnect/login lock to remove
  the same-event-loop-tick reconnect race documented in the roster class-14 row.
  Low priority: production clients back off ≥1 s, so the race is test-only and
  already neutralized (reconnect tests issue an explicit `quit`).
- **Continue the active pass** — cross-file invariants probe-then-scope or
  differential-harness widening. The death-lifecycle probes flagged by the
  earlier 2026-06-22 session remain open: `PLR_AUTOSAC` after NPC death (the ROM
  branch that refuses autosac when AUTOLOOT left treasure), and `PLR_AUTOSPLIT`
  after grouped rewards.

Note: the GitNexus MCP server disconnected during this session; the CLI reindex
(`npx gitnexus analyze --skip-agents-md`) was re-run. If `gitnexus_*` MCP tools
are needed next session, confirm the server is back up first.
