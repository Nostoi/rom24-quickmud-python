# Session Status — 2026-06-19 — diff-harness non-mobprog widening + FINDING-034

## Current State

- **Active focus**: Cross-file / divergence-class sweep, **Layer C** (per-file
  audit tracker exhausted). Enumeration-independent `tools/diff_harness/`
  widening against the live ROM C oracle (`DIVERGENCE_CLASS_ROSTER.md`
  guardrail 3). This session widened the **non-mobprog command** frontier with
  container open/close/lock/unlock (OBJECT branch), `get all`/`drop all`, and
  `sacrifice` — and surfaced a real divergence on `wear all`.
- **Last completed** (this session, 4 commits, master, **not pushed**):
  - `a60fc400` v2.14.135 — container lock cycle (OBJECT branch), clean lock.
  - `2a02c8fe` v2.14.136 — `get all` / `drop all` bulk loops, clean lock.
  - `4764d454` v2.14.137 — `sacrifice` object-extraction lifecycle, clean lock.
  - `8215cd1d` v2.14.138 — `wear all` scenario surfaced **FINDING-034 /
    WEAR-012** (Python `_wear_all` skips lights/weapons/HOLD items ROM equips);
    filed durably, scenario committed `xfail(strict=True)`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_DIFF_HARNESS_CONTAINER_BULK_SACRIFICE_WEARALL.md](SESSION_SUMMARY_2026-06-19_DIFF_HARNESS_CONTAINER_BULK_SACRIFICE_WEARALL.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.138 |
| Tests | diff-harness generated: 23 passed, 1 xfailed (FINDING-034) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep (Layer C) |
| Open findings | **FINDING-034 / WEAR-012** (`wear all` skip — fix design recorded) |

## Next Intended Task

**Close WEAR-012 / FINDING-034 via `/rom-gap-closer`** (the session's surfaced
gap). The faithful fix extracts a shared `wear_obj(ch, obj, fReplace)` mirroring
`src/act_obj.c` and routes both `do_wear <item>` (`fReplace=True`) and
`_wear_all` (`fReplace=False`, skip occupied slots silently) through it — do NOT
loop `do_wear`, which force-replaces. When it lands,
`test_generated_wear_all_matches_live_c` auto-flips from xfail to pass. Then
resume non-mobprog widening (`wear all` dual-wield, `examine` MONEY/CORPSE,
`look in` closed container). Guardrail 3: a clean sweep = "known surface
locked," never "close to ROM parity." 4 commits not pushed; `git push` if
sharing (version/CHANGELOG already current).
