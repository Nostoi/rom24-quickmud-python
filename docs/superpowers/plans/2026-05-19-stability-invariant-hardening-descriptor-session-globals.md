# Stability / Invariant Hardening — Descriptor and Session Globals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden global descriptor/session/registry state so networking-adjacent tests and live flows remain deterministic without reopening closed ROM-parity gaps.

**Architecture:** Treat the asyncio transport as an accepted divergence, but enforce ROM-visible boundary contracts with deterministic cleanup and isolation. Start from failing state-leak reproductions, then add the narrowest reset/cleanup hooks needed in descriptor/session registries, disconnect paths, and test fixtures. If a new cross-file contract is discovered, capture it as a new `INV-NNN` with one enforcement test.

**Tech Stack:** Python 3.13, pytest, asyncio streams/tasks, QuickMUD networking/session modules, cross-file invariant tracker docs

---

## File map

- `mud/net/connection.py` — lightweight descriptor lifecycle, reconnect/break-connect handling, `descriptor_list`
- `mud/net/session.py` — session ownership and connection teardown behavior
- `mud/net/telnet_server.py` — server-side telnet accept/close path and writer cleanup
- `mud/wiznet.py` — descriptor-backed message fanout path already hardened; likely consumer of any descriptor invariant
- `mud/models/character.py` — `character_registry` interactions if descriptor/session teardown reveals registry leaks
- `tests/test_wiznet.py` — descriptor-path message delivery regressions
- `tests/test_telnet_server.py` — telnet lifecycle and reconnect cleanup regressions
- `tests/test_networking_telnet.py` — prompt/paging/networking subset ordering checks
- `tests/integration/test_nanny_login_parity.py` — login/reconnect/newbie duplicate descriptor behavior
- `tests/integration/conftest.py` or `tests/conftest.py` — shared cleanup fixtures if global-state reset belongs in test harness
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — add `INV-NNN` only if a new cross-module contract is confirmed
- `docs/sessions/SESSION_STATUS.md` — update after landing
- `docs/sessions/SESSION_SUMMARY_*.md` — record what was hardened and why

### Task 1: Reproduce and pin the state-leak boundary

**Files:**
- Modify: `tests/test_wiznet.py`
- Modify: `tests/test_telnet_server.py`
- Modify: `tests/test_networking_telnet.py`
- Modify: `tests/integration/test_nanny_login_parity.py`

- [ ] **Step 1: Write or tighten the failing ordering reproductions**

Add deterministic tests that prove global-state leakage across mixed networking subsets if cleanup is missing. Keep the assertions on observable behavior, not internal implementation.

```python
def test_wiznet_ignores_stale_descriptor_entries():
    immortal = make_player("Imm", level=60)
    stale = make_descriptor(character=make_player("OldImm", level=60))
    descriptor_list.append(stale)
    remove_live_character(stale.character)

    wiznet("hello", None, None, WiznetFlag.WIZ_LOGINS, 0, 0)

    assert "hello" in immortal.messages
    assert stale.character.messages == []
```

```python
@pytest.mark.asyncio
async def test_break_connect_suite_leaves_no_open_writers():
    reader, writer = await open_client_pair(server)
    try:
        await perform_break_connect_flow(reader, writer)
    finally:
        await close_writer(writer)

    assert no_live_test_descriptors()
```

- [ ] **Step 2: Run the narrow reproductions**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_wiznet.py tests/test_telnet_server.py tests/test_networking_telnet.py tests/integration/test_nanny_login_parity.py -k 'wiznet or reconnect or break_connect or paging or prompt or idle'
```

Expected: at least one failure or order-sensitive failure that identifies the leaking global surface.

- [ ] **Step 3: Record the exact leaking globals before touching implementation**

Capture whether the offender is one or more of:

```text
mud.net.connection.descriptor_list
mud.models.character.character_registry
per-session pending output / mailbox state
open asyncio StreamWriter instances
```

Write the finding into the session summary before implementing the fix so the next reader can see the root cause clearly.

### Task 2: Fix production cleanup at the true ownership boundary

**Files:**
- Modify: `mud/net/connection.py`
- Modify: `mud/net/session.py`
- Modify: `mud/net/telnet_server.py`
- Modify: `mud/models/character.py` (only if registry cleanup is the actual root cause)

- [ ] **Step 1: Write the minimal failing production-path test first**

Prefer a regression that hits the ownership boundary directly:

```python
def test_disconnect_removes_descriptor_from_global_list():
    descriptor = make_descriptor(character=immortal_player())
    descriptor_list.append(descriptor)

    close_descriptor(descriptor)

    assert descriptor not in descriptor_list
```

or, if the leak is session-owned:

```python
def test_session_close_clears_pending_delivery_state():
    session = make_connected_session(player)
    enqueue_prompt(session, "> ")

    session.close()

    assert session.pending_output == []
```

- [ ] **Step 2: Run the single regression**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_telnet_server.py::test_disconnect_removes_descriptor_from_global_list
```

Expected: FAIL on the current leak.

- [ ] **Step 3: Implement the smallest owner-side cleanup**

Use the real owner of the leaked state. Examples:

```python
if descriptor in descriptor_list:
    descriptor_list.remove(descriptor)
```

```python
if self.writer is not None and not self.writer.is_closing():
    self.writer.close()
```

```python
if character in character_registry and should_extract(character):
    character_registry.remove(character)
```

Do not add broad “reset everything everywhere” calls in production code if one disconnect/close path is supposed to own cleanup.

- [ ] **Step 4: Re-run the targeted subset**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_wiznet.py tests/test_telnet_server.py tests/test_networking_telnet.py tests/integration/test_nanny_login_parity.py -k 'wiznet or reconnect or break_connect or paging or prompt or idle'
```

Expected: PASS.

### Task 3: Add fixture-level isolation only for test-owned leftovers

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/integration/conftest.py`

- [ ] **Step 1: Add a failing test that proves suite-order dependence remains after the production fix**

If the targeted subset still only fails in mixed ordering, add a harness-level regression:

```python
def test_networking_fixture_starts_with_clean_descriptor_state():
    assert descriptor_list == []
```

- [ ] **Step 2: Run the harness-level regression in the mixed subset**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_wiznet.py tests/test_telnet_server.py tests/test_networking_telnet.py -k 'clean_descriptor_state or wiznet or telnet'
```

Expected: FAIL only if test-owned state still leaks.

- [ ] **Step 3: Add the narrowest autouse cleanup fixture**

Only if production ownership cleanup is insufficient, add explicit test harness cleanup:

```python
@pytest.fixture(autouse=True)
def clear_descriptor_state():
    descriptor_list.clear()
    yield
    descriptor_list.clear()
```

If registry state also leaks:

```python
@pytest.fixture(autouse=True)
def clear_character_registry():
    character_registry.clear()
    yield
    character_registry.clear()
```

Keep fixture scope as narrow as possible; prefer test module scope over global scope unless the leak is suite-wide.

- [ ] **Step 4: Re-run the mixed subset and then the full suite**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_wiznet.py tests/test_telnet_server.py tests/test_networking_telnet.py tests/integration/test_nanny_login_parity.py
./venv/bin/python -m pytest -q --maxfail=1
```

Expected: subset passes consistently; full suite remains green.

### Task 4: Capture the contract as an invariant if it crosses modules

**Files:**
- Modify: `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`
- Modify: `docs/sessions/SESSION_STATUS.md`
- Create: `docs/sessions/SESSION_SUMMARY_YYYY-MM-DD_<topic>.md`

- [ ] **Step 1: Decide whether the fix is a new invariant or just a local cleanup**

Add a new invariant only if the bug requires coordination between multiple modules, for example:

```text
descriptor/session teardown must remove stale descriptor-path recipients before cross-module message fanout
```

- [ ] **Step 2: If needed, add the tracker row with one enforcement test**

Follow the existing table format exactly:

```markdown
| INV-009 | DESCRIPTOR-STATE-ISOLATION | ROM single-threaded descriptor sweep never leaves stale recipients between pulses | `mud/net/connection.py` teardown + `mud/wiznet.py` descriptor iteration | `tests/test_wiznet.py::test_wiznet_ignores_stale_descriptor_entries` | ✅ ENFORCED |
```

- [ ] **Step 3: Update session handoff docs with exact verification commands**

Include:

```bash
./venv/bin/python -m pytest -q tests/test_wiznet.py tests/test_telnet_server.py tests/test_networking_telnet.py tests/integration/test_nanny_login_parity.py
./venv/bin/python -m pytest -q --maxfail=1
```

- [ ] **Step 4: Commit the slice cleanly**

Run:

```bash
git add mud/net/connection.py mud/net/session.py mud/net/telnet_server.py tests/test_wiznet.py tests/test_telnet_server.py tests/test_networking_telnet.py tests/integration/test_nanny_login_parity.py docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md docs/sessions/SESSION_STATUS.md docs/sessions/SESSION_SUMMARY_*.md pyproject.toml CHANGELOG.md
git commit -m "fix: harden descriptor and session state isolation"
```

Expected: one bounded commit containing the enforcement tests, the minimal cleanup, and the session/docs updates.

## Self-review

- Spec coverage: this plan covers reproduction, owner-side cleanup, harness cleanup only if still needed, and invariant documentation for the next agent.
- Placeholder scan: all tasks name exact files, commands, and candidate code paths; no `TODO`/`TBD` placeholders remain.
- Type consistency: `descriptor_list`, `character_registry`, `StreamWriter`, `WiznetFlag`, and session teardown terminology match the current codebase vocabulary.

## Execution Handoff

Plan complete and saved to `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/superpowers/plans/2026-05-19-stability-invariant-hardening-descriptor-session-globals.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
