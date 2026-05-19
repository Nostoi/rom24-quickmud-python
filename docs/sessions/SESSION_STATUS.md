# Session Status — 2026-05-19 — wiznet descriptor-path parity hardened

## Current State

- **`wiznet` descriptor-path parity is hardened.**
- Root cause: order-dependent networking tests left a live `descriptor_list`, which exposed that `mud/wiznet.py` enforced the ROM immortal/NPC gate only on the character-registry fallback path, not on the real descriptor path.
- `mud/wiznet.py` now mirrors `src/act_wiz.c:171-194` on both paths:
  - descriptor-path delivery requires an immortal/admin recipient
  - NPC recipients are rejected
- `tests/test_wiznet.py` now registers descriptor-backed listeners explicitly, so the suite exercises the production path instead of depending on fallback state.
- **Pointer to latest summary**:
  - `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_SUMMARY_2026-05-19_WIZNET_DESCRIPTOR_PATH_PARITY_HARDENING.md`

## Verification

- Wiznet/networking parity slice:
  - `./venv/bin/python -m pytest -q tests/test_wiznet.py` → `33 passed`
  - `./venv/bin/python -m pytest -q tests/test_networking_telnet.py tests/test_telnet_server.py tests/integration/test_nanny_login_parity.py tests/test_wiznet.py -k 'network or telnet or paging or reconnect or ansi or prompt or idle or break_connect or show_string or newbie or login'` → `46 passed, 1 skipped`
  - `./venv/bin/ruff check mud/wiznet.py tests/test_wiznet.py` → clean
- Full-suite recertification:
  - `./venv/bin/python -m pytest -q --maxfail=1`
  - `4560 passed, 4 skipped`

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.18 |
| Cross-file invariants enforced | **8/8 ✅ ENFORCED** |
| Audit-bound ROM C files | 40/40 audited (100%) |
| N/A ROM C files | 3/3 (`recycle.c`, `mem.c`, `imc.c`) |
| Full suite | ✅ green (`4560 passed, 4 skipped`) |
| Warnings | ✅ zero |
| Current focus | choose the next real deferred, user-visible parity slice now that `board.c` and the concrete `wiznet` descriptor-path bug are both closed |

## Next Intended Task

1. Re-scan the remaining deferred, user-visible surfaces after removing the resolved `wiznet` false positive.
2. Prefer a bounded behavioral slice over the intentionally divergent asyncio transport architecture.
3. If no concrete user-visible parity gap remains, switch from parity hunting to stability/invariant enforcement work.
