# Session Status — 2026-06-15 — Tick-aggression regression-prevention trio

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). The two reported tick symptoms (aggressive mobs not attacking;
  friendly mobs not casting) were closed earlier today (FIGHT-077 + SPEC-017,
  v2.14.115). This session landed the **regression-prevention package**:
  FIGHT-077 is now diff_harness-locked (C-oracle, negative-control-proven);
  SPEC-017 has a Layer-A grep-guard + AGENTS.md doc rule but **no C-oracle
  scenario yet** — the `aggression_onset` combat path routes through
  `engine.py:_push_message`, not `spec_funs.py`, so a dedicated adept-healing
  spec-fun scenario is still owed (see Next Intended Task).
- **Last completed** (this session, all three deliverables of the authorized
  package):
  - **(a) Layer-A grep-guard** (v2.14.116, commit 5e7ca15c) —
    `tests/test_message_delivery_convention.py` forbids `<entity>.messages.append`
    / `getattr(x, "messages")` bypasses outside the `push_message` chokepoint
    (7 legitimate + 14 frozen INV-001 debt entries, self-cleaning orphan check).
  - **(c) AGENTS.md doc rule** (v2.14.116, commit 5e7ca15c) — Message Delivery
    section cites the guard.
  - **(b) diff_harness `aggression_onset` scenario** (plumbing v2.14.117 commit
    55134261; **fixture corrected to a load-bearing guard in v2.14.118**) —
    mloads AGGRESSIVE mob **2302** (Cave Dweller, **L15**) into an idle **L1**
    PC's room, runs one `__aggr_update` pulse; committed C golden shows the mob
    proactively attacking (PC → `FIGHTING`, hp 20→13, "The Cave Dweller's pierce
    decimates you."). New `__aggr_update` step-handlers in both engines (C shim →
    `aggr_update()`, Python → `aggressive_update`). Python replay matches the C
    oracle exactly. **Negative control verified**: re-adding the deleted
    `is_safe` level-gate makes the replay diverge (mob fails to attack) — the
    earlier L1-mob/L5-PC fixture never tripped the gate and locked nothing.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-15_TICK_AGGRESSION_REGRESSION_PREVENTION.md](SESSION_SUMMARY_2026-06-15_TICK_AGGRESSION_REGRESSION_PREVENTION.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.118 |
| Tests | 5812 passed (v2.14.115 baseline) + diff_harness 68 passed (41 scenarios incl. aggression_onset) + message-delivery guard green |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants pass — FIGHT-077 diff-locked; SPEC-017 doc+Layer-A guarded (C-oracle scenario owed) |

## Next Intended Task

Regression-prevention trio complete (FIGHT-077 diff-locked; SPEC-017 doc +
Layer-A guarded). Open follow-ups, in priority order:

0. **SPEC-017 spec-fun diff_harness scenario (owed)** — author an adept-healing
   scenario (mload the cage-room friendly caster, pulse its spec-fun) so the
   replay exercises `spec_funs.py:_append_message → push_message`. The
   `aggression_onset` scenario does NOT cover this (combat damage routes through
   `engine.py:_push_message`), so reverting SPEC-017 currently passes the diff
   suite — SPEC-017 has only a Layer-A guard + doc rule, no C-oracle lock.
1. **INV-001 debt burndown** — migrate the 14 frozen `_INV001_DEBT` sites in
   `tests/test_message_delivery_convention.py` to `push_message`, one clean
   ROM-confirmed TDD fix per site, deleting its allowlist line. Candidates:
   `thief_skills.py:253`, `connection.py:766/787`, `dispatcher.py:1201`,
   `communication.py:29`, `magic_items.py:319`, `skills/handlers.py` (4 sites),
   `skills/registry.py` cluster.
2. **Vestigial dual-channel in `process_weapon_special_attacks`**
   (`mud/combat/engine.py`) — latent INV-001 footgun; not yet a stable ID.
3. **DELETE-002 🔄 OPEN** — `do_delete` lacks ROM's wiznet self-deletion
   broadcast (`src/act_comm.c`).
4. **STEAL-015 🔄 OPEN** — steal skill-handler has no `is_safe` gate.
5. **INV-050 bool-retirement** — gated on the `is_safe_spell`-vs-ROM audit
   (`safety.py:is_safe_spell` vs `src/fight.c:1126-1218`).
6. **`mud/entrypoint.py`** dead code (`prompt_account_creation` / `prompt_login`,
   no callers) — hygiene-pass removal candidate.

Beyond these, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield open
lever remains the **Hypothesis state-machine → diff_harness widening** (Class 11
/ Phase C), enumeration-independent (guardrail 3).
