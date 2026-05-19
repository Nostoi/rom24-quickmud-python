# Session Summary — 2026-05-19 — wiznet descriptor-path parity hardening

## What landed

Closed a real `act_wiz.c` parity regression in the production `wiznet` descriptor path and hardened the corresponding tests.

- `mud/wiznet.py` now enforces ROM `src/act_wiz.c:171-194` gating on the descriptor path:
  - recipient must not be NPC
  - recipient must be immortal/admin
  - then normal `WIZ_ON` / flag / trust checks apply
- `tests/test_wiznet.py` now registers descriptor-backed listeners explicitly and includes a stale-descriptor regression so mixed networking subsets no longer hide or distort the production path.

## Root cause

Order-dependent networking tests left a non-empty global `descriptor_list`. That forced `wiznet()` onto the descriptor path, which exposed a missing ROM gate in production code: the fallback character-registry path filtered mortals/NPCs, but the descriptor path did not.

## Files changed

- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/wiznet.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_wiznet.py`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ACT_WIZ_C_AUDIT.md`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_STATUS.md`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/pyproject.toml`
- `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/CHANGELOG.md`

## Verification

- `./venv/bin/python -m pytest -q tests/test_wiznet.py` → `33 passed`
- `./venv/bin/python -m pytest -q tests/test_networking_telnet.py tests/test_telnet_server.py tests/integration/test_nanny_login_parity.py tests/test_wiznet.py -k 'network or telnet or paging or reconnect or ansi or prompt or idle or break_connect or show_string or newbie or login'` → `46 passed, 1 skipped`
- `./venv/bin/ruff check mud/wiznet.py tests/test_wiznet.py` → clean
- `./venv/bin/python -m pytest -q --maxfail=1` → `4560 passed, 4 skipped`

## Result

- The concrete `wiznet` false-positive from the deferred networking scan is resolved.
- The remaining `comm.c` deferment is still the intentional asyncio transport architecture, not a newly confirmed small parity bug.
