# Session Status — 2026-04-29 — `const.c` Audit Phases 1–3 (⚠️ Partial 80% — 4 CRITICAL combat/advancement gaps open)

## Current State

- **Active audit**: `const.c` (Phase 4 — per-gap closures pending).
- **Last completed**: `const.c` audit doc (`CONST-001`..`CONST-007` filed; tracker held at ⚠️ Partial 80% pending CRITICAL closures CONST-002..006 because they are behavioral combat/advancement divergences, per `AGENTS.md` "no deferring" rule).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-04-29_CONST_C_AUDIT_PHASES_1-3.md](SESSION_SUMMARY_2026-04-29_CONST_C_AUDIT_PHASES_1-3.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.47 |
| Tests | Last suite-of-record (music.c handoff): 1383 passed / 10 skipped / 1 pre-existing intermittent flake. This session is audit-doc-only — no code changes. |
| ROM C files audited | 18 / 43 (42%) ✅ Audited; 14 ⚠️ Partial (`const.c` audit-doc filed but row stays ⚠️ Partial pending CONST-002..006); 7 ❌ Not Audited; 4 N/A. |
| Active focus | `const.c` — 7 gaps open, CONST-002..006 (combat + advancement) blocking tracker flip. |

## Next Intended Task

**Recommended:** start the CONST combat-math triplet. The next `/rom-gap-closer` invocation should be `CONST-002` (`GET_HITROLL` / `str_app[STR].tohit`) — it pairs naturally with `CONST-003` (`GET_DAMROLL` / `str_app[STR].todam`) and `CONST-004` (`GET_AC` / `dex_app[DEX].defensive`) because all three need the same primitive: a ROM-faithful `str_app` + `dex_app` module plus `get_hitroll(ch)` / `get_damroll(ch)` / `get_ac(ch, type)` accessors. One closer per gap, one commit per gap, but the table-import infrastructure is shared.

After the triplet: `CONST-005` (port `con_app.hitp` and rewrite `advance_level` to roll `number_range(class.hp_min, class.hp_max) + con_app[CON].hitp` — verify `class_table.hp_min/hp_max` are ported on `mud/models/classes.py:ClassType` first), then `CONST-006` (`wis_app[WIS].practice` in `advance_level`).

`CONST-001` (`title_table`, 480 entries) is deferred to a dedicated `NANNY-009` session per the prior `SESSION_STATUS.md` plan. `CONST-007` (`weapon_table`) is deferred to the OLC audit (BIT-style).

For deferred `music.c` MINORs `MUSIC-005` / `MUSIC-006`, leave them parked — they depend on broader infrastructure work (descriptor-state plumbing through `broadcast_global`; per-viewer `$p` substitution via `act_format`) and should land alongside that infrastructure.

Run `/rom-gap-closer CONST-002` to start.
