# Session Summary — 2026-05-03 — Pre-existing failure sweep + `log` trust parity correction

## Scope

Close the four documented pre-existing failure groups:

- `tests/test_logging_admin.py`
- `tests/test_commands.py`
- `tests/test_account_auth.py` (targeted known failures)
- `tests/test_scripted_session.py`

Then run the broader clean-baseline verification the repo expects, excluding only:

- `tests/test_skill_combat_rom_parity.py`
- `tests/integration/test_mob_ai.py`

## Landed

### Targeted pre-existing failures closed

Three logical fix groups were shipped first:

| Commit | Description |
|--------|-------------|
| `74110c0` | admin logging parity |
| `ca649c0` | command/scripted-session parity |
| `b858989` | legacy auth schema compatibility |

Those changes eliminated all 16 documented pre-existing failures (`7 + 6 + 2 + 1`).

### Follow-up parity correction discovered by broader verification

Broader verification exposed a contradiction between the admin logging tests and the audited ROM command table:

- ROM `src/interp.c:336` registers `log` at `L1`.
- `tests/integration/test_interp_trust.py` correctly asserts `MAX_LEVEL - 1`.
- The earlier admin-logging fix had lowered `log` to `LEVEL_HERO`, which made the targeted file pass but violated ROM trust parity.

Corrective changes:

- `mud/commands/dispatcher.py` — restore `Command("log", ...)` to `MAX_LEVEL - 1`, matching ROM `src/interp.c:336`.
- `tests/test_logging_admin.py` — make the helper admin use ROM-valid trust (`MAX_LEVEL - 1`) instead of `LEVEL_HERO`.
- `pyproject.toml` — bump version `2.8.10` → `2.8.11`.
- `CHANGELOG.md` — add `2.8.11` entry.

## Verification

### Targeted suites

```sh
python3 -m pytest tests/test_logging_admin.py tests/test_commands.py tests/test_account_auth.py tests/test_scripted_session.py -v --timeout=15
```

Result before the broader sweep:

- `96 passed`

### Trust-parity regression check

```sh
python3 -m pytest tests/test_logging_admin.py tests/integration/test_interp_trust.py -v --timeout=15
```

Result after restoring ROM trust:

- `64 passed`

### Broader clean-baseline verification

Attempted:

```sh
python3 -m pytest -q --timeout=15 \
  --ignore=tests/test_skill_combat_rom_parity.py \
  --ignore=tests/integration/test_mob_ai.py
```

Observed results:

1. **First true verification issue**: `tests/integration/test_interp_trust.py::test_interp_001_command_trust_matches_rom[log-59]` failed until the `log` trust correction above landed.
2. **Next blocker after that fix**: fail-fast rerun reached `2016 passed, 9 skipped` before stopping at `tests/test_account_auth.py::test_new_character_creation_sequence`, but the stop was **sandbox-only**:
   - `PermissionError: [Errno 1] error while attempting to bind on address ('127.0.0.1', 0): operation not permitted`
   - failure site: `mud/net/telnet_server.py:create_server()` via `asyncio.start_server(...)`
3. Required unsandboxed rerun was attempted, but the Codex approval system rejected the escalation because of a **usage-limit/auto-review quota**, not because of repo behavior.

Conclusion:

- The broader suite is **not yet re-certified green in this environment**.
- The remaining blocker in this session is **environmental verification**, not a demonstrated code regression.

### Lint

```sh
ruff check .
```

Current result:

- fails with **2023 pre-existing violations**, heavily concentrated in `.claude/skills/` and older test files
- not a meaningful clean gate for this branch yet

## Repo hygiene / cleanup

Two test-generated file mutations were reverted before handoff:

- `data/areas/area.lst` — removed transient `test.json`
- `log/orphaned_helps.txt` — removed appended test noise

## Next recommended task

1. Re-run the broader pytest baseline **outside sandbox restrictions**:
   ```sh
   python3 -m pytest -q --timeout=15 \
     --ignore=tests/test_skill_combat_rom_parity.py \
     --ignore=tests/integration/test_mob_ai.py
   ```
2. If that full run is green, treat `2.8.11` as the new clean handoff point and move to the remaining non-green suite item:
   - `tests/integration/test_mob_ai.py::TestScavengerBehavior::test_scavenger_prefers_valuable_items`
3. If the full run finds another real failure, take the first failing test as the next parity/TDD task.
