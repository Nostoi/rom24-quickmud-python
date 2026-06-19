# Session Status — 2026-06-19 — DELETE-002 (do_delete staff wiznet broadcasts)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). This session closed **DELETE-002** — `do_delete` emitted neither
  of ROM's two staff `wiznet` lines, so immortals got no notice on
  self-deletion.
- **Last completed** (this session, 1 commit):
  - **DELETE-002 ✅ FIXED** (2.14.130, `d6fc8c53`) — added both ROM `wiznet`
    calls to `do_delete`: `"$N is contemplating deletion."` on the request pass
    (`min_level = get_trust(ch)`, `src/act_comm.c:92`) and `"$N turns $Mself into
    line noise."` on the confirm pass (`min_level = 0`, `:62`), fired before the
    `do_quit` + `delete_character` tail to match ROM's broadcast-before-unlink
    ordering. Routed through the existing `mud.wiznet.wiznet` chokepoint
    (act-format `$N`/`$M`, single-delivery via `push_message`) — INV-001-clean.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_DELETE-002_WIZNET_BROADCASTS.md](SESSION_SUMMARY_2026-06-19_DELETE-002_WIZNET_BROADCASTS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.130 |
| Tests | `tests/test_wiznet.py` + `tests/test_account_auth.py` green (92 passed); full suite not re-run this session |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants — DELETE-002 closed (do_delete staff wiznet) |

## Next Intended Task

Pick up the remaining open follow-ups: **INV-050 bool-retirement** (still GATED
on the `is_safe_spell`-vs-ROM standalone audit, `src/fight.c:1126-1218`),
`mud/entrypoint.py` dead code, and the `do_yell` hand-rolled-XOR tidy-up. The
higher-yield enumeration-independent lever per
`docs/parity/DIVERGENCE_CLASS_ROSTER.md` is the Hypothesis state-machine →
diff_harness widening (Class 11 / Phase C).
