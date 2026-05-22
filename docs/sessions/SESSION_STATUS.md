# Session Status — 2026-05-22 — `nanny.c` creation transcript and retry parity

## Current State

- **Active audit**: `nanny.c` trust-rebuild (Plan Task 4 — re-audit `nanny.c` / `save.c` session boundaries against the live telnet/websocket path, not helper-only fixtures).
- **Last completed**:
  - **Slice 1** (commit `8a747af`): restored ROM-exact happy-path new-character creation prompts (`"New character."`, password prompts, race/sex/class/weapon prompts) and fixed greeting/MOTD leak before `Name:`.
  - **Slice 2** (commit `cc04b85`): closed `NANNY-RETRY-001..006` — every invalid-entry retry wording and the customization-menu transcript now matches `src/nanny.c:460-657` exactly. Added 6 transcript-parity tests.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-22_NANNY_CREATION_TRANSCRIPT_AND_RETRY_PARITY.md](SESSION_SUMMARY_2026-05-22_NANNY_CREATION_TRANSCRIPT_AND_RETRY_PARITY.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.32 |
| Tests | **4599 passed, 4 skipped** (full suite, ~6m 44s) |
| Targeted creation/login band | **96 passed, 1 skipped** |
| `nanny.c` audit | 100% gap rows ✅ (NANNY-001..014 + NANNY-RETRY-001..006) |
| Ruff on touched files | clean (no new errors vs baseline) |
| GitNexus index | **stale** — last indexed at `0dd803e`; re-run `npx gitnexus analyze --skip-agents-md` |

## Next Intended Task

Continue the `nanny.c` / `save.c` trust rebuild on the post-login session
boundaries (Plan Task 4 remaining bullets):

1. DB row state after a completed creation — exercise the live websocket/telnet
   path, then assert the persisted character record matches the ROM-derived
   defaults (race / class / alignment / title / hp-mana-move / equipped
   outfit).
2. Post-login `logon` semantics and first-command output after reconnect —
   verify `score`, `look`, and prompt rendering match ROM on the runtime
   path, not helper paths.
3. Save → reload → retained state on real server paths.

Operational follow-ups before pushing:

- Add `log/orphaned_helps.txt` (runtime-generated noise) to `.gitignore` in a
  small repo-hygiene commit.
- Re-run `npx gitnexus analyze --skip-agents-md` so `gitnexus_impact` /
  `gitnexus_detect_changes` reflect commits `8a747af` and `cc04b85`.
